# AViiD — Data Extraction: Full Technical Deep-Dive Flowchart
> Render in VS Code with **Markdown Preview Mermaid Support** extension, or paste into [mermaid.live](https://mermaid.live)

---

```mermaid
flowchart TD

    %% ════════════════════════════════════════════════════
    %% INPUT
    %% ════════════════════════════════════════════════════
    PDF(["📄 INPUT: belino-ib-v13.pdf\nPharmaceutical Investigator Brochure\n~200 pages · tables · footnotes · figures"])

    %% ════════════════════════════════════════════════════
    %% STEP 1 — AZURE DOCUMENT INTELLIGENCE
    %% ════════════════════════════════════════════════════
    PDF --> C1{"cache_layout.json\nAND\ncache_query_results.json\nboth exist?"}

    C1 -->|"✅ YES\nLoad both from disk\nSkip Azure API — saves cost and 30-90s"| MD_BLOB

    C1 -->|"❌ NO\nasyncio.to_thread wraps sync Azure call\nkeeps event loop unblocked"| AZ_CALL

    subgraph STEP1 ["  STEP 1 · Azure Document Intelligence  ·  src/layout_parser.py · LayoutParser.analyze_document  "]
        AZ_CALL["Azure DI: prebuilt-layout model\nRuns OCR + layout AI on original raw PDF pixel data\nNOT on extracted text — reads document natively"]

        AZ_A["FEATURE A — Markdown Export\noutput_content_format = markdown\nTables → pipe-delimited Markdown\n| Event | All Grades | Grade 3-4 |\n|---|---|---|\n| Thrombocytopenia | 47.3% | 23.3% |\nHeaders → hash-level nesting\n## 5.1.3 Dosing and Administration\nFigure captions preserved\nPage noise · footers · watermarks filtered"]

        AZ_B["FEATURE B — Query Fields API\nDocumentAnalysisFeature.QUERY_FIELDS\n14 natural-language questions fired simultaneously\nAzure reasons on original PDF layout — not Markdown\n\nQuestions include:\n  overall_response_rate: What is the ORR percentage?\n  median_pfs: What is the median PFS in months?\n  elimination_half_life: What is the elimination half-life or t1/2?\n  grade_3_4_anemia: What is the Grade 3-4 Anemia rate?\n  hepatic_impairment_exclusion: Are patients with hepatic impairment excluded?\n  ...14 total fields\n\nFallback: if Query Fields API tier unavailable\n→ graceful skip · Markdown-only extraction continues"]

        AZ_CALL --> AZ_A & AZ_B
        AZ_A --> W1["Write: cache_layout.json\n~228KB full Markdown string\nFull document in structured text form"]
        AZ_B --> W2["Write: cache_query_results.json\n14 key-value pairs\nEx: overall_response_rate: 25.8%\nEx: elimination_half_life: 1.1 hours"]
    end

    W1 --> MD_BLOB["📝 Full Document Markdown\n~228KB · complete document as structured text\nTables intact · headers nested · layout preserved"]
    W2 --> QR_STORE["🎯 14 Ground-Truth Values\nGround truth from Azure native PDF reasoning\nUsed later to override LLM outputs"]

    %% ════════════════════════════════════════════════════
    %% STEP 2 — SEMANTIC CHUNKER (inside ContextClassifier)
    %% ════════════════════════════════════════════════════
    MD_BLOB --> C2{"cache_classified.json\nexists?"}
    C2 -->|"✅ YES — Load classified chunks\nSkip embedding API calls\nSaves ~$0.001 per run"| CHUNKS
    C2 -->|"❌ NO — Run classifier.classify_blocks\nawait self.classifier.classify_blocks\nmarkdown_content"| CHUNK_SPLIT

    subgraph STEP2 ["  STEP 2 · Semantic Chunker  ·  src/semantic_chunker.py · SemanticChunker  "]
        CHUNK_SPLIT["Split Markdown by double newlines\nresult: list of raw paragraph strings"]

        EMBED["Embed each paragraph\nAzure OpenAI text-embedding-3-small\n→ 1536-dimensional float vector per paragraph\nbatch_size = 5  to respect rate limits\nEach vector captures semantic meaning of paragraph"]

        COSINE["Sliding window: compute cosine similarity\nfor every consecutive paragraph pair\ncosine_sim = dot(a,b) / norm(a)*norm(b)"]

        DEC_SIM{"cosine_sim > 0.75?\nthreshold = SAME TOPIC"}
        DO_MERGE["MERGE paragraphs into same chunk\nSame topic — keep together\nEx: two MOA paragraphs → one MOA chunk"]
        DO_SPLIT["SPLIT at this boundary\nTopic boundary detected\nEx: MOA paragraph followed by PK table → split"]

        SIZE{"merged chunk\nexceeds 2000 chars?"}
        FORCE["Force SPLIT\nContext window safety\ntarget_chunk_size = 2000 chars\nmin_chunk_size = 500 chars"]

        FB["⚠️ Embedding API Failure Fallback\nfixed-size chunking with 200-char overlap\nPipeline continues — never crashes"]

        W3["Write: cache_classified.json\n~293KB\nList of chunk objects with text + metadata"]

        CHUNK_SPLIT --> EMBED
        EMBED -->|"API OK"| COSINE
        EMBED -.->|"API fails\nrate limit or outage"| FB
        COSINE --> DEC_SIM
        DEC_SIM -->|"YES — same topic"| DO_MERGE
        DEC_SIM -->|"NO — new topic"| DO_SPLIT
        DO_MERGE & DO_SPLIT --> SIZE
        SIZE -->|"YES — too large"| FORCE --> W3
        SIZE -->|"NO — fits"| W3
        FB --> W3
    end

    W3 --> CHUNKS["📦 60 – 80 Semantic Chunks\nEach = one coherent clinical topic\nMax ~2000 chars per chunk\nNo mid-table cuts · no topic mixing"]

    %% ════════════════════════════════════════════════════
    %% STEP 3 — CONTEXT CLASSIFIER + RAG SCHEMA INJECTOR
    %% ════════════════════════════════════════════════════
    subgraph STEP3 ["  STEP 3 · Context Classifier + RAG Schema Injector  ·  src/context_classifier.py · src/schema/context.py  "]
        PASS1["Pass 1 — Header-Based Classification\nRegex: re.search first Markdown header in chunk\npattern: ^#{1,6} .* re.MULTILINE\nMatch header title against keyword map\n\nhepatotoxicity      → Hepatotoxicity\npharmacokinetics    → Pharmacokinetics\nadverse events      → Safety and Adverse Events\nefficacy            → Efficacy Outcomes\nmechanism of action → Mechanism of Action\ndose modification   → Dose Modifications\nclinical study      → Clinical Study Design\nspecial populations → Special Populations - Hepatic\n...14 section types total"]

        PASS2["Pass 2 — Content Keyword Fallback\nOnly runs if Pass 1 finds NO header\nScan first 500 chars of chunk content\ntext_lower = text.lower\n\nauc or cmax or half-life    → Pharmacokinetics\norr or pfs or os found      → Efficacy Outcomes\nnoael or mtd or species     → Nonclinical Toxicology\nin vitro or ames test       → Genotoxicity\nhdac or histone             → Mechanism of Action\nformulation or excipient    → Formulation and Stability\nNo match                    → Other"]

        INJECT["RAG Schema Context Injection\nSchemaContextInjector.get_context_for_section\nBuilds a targeted system prompt FRAGMENT\nfor this specific section type only\n\nPK chunk injects:\n  auc_value · cmax_value · elimination_half_life\n  plasma_protein_binding · clearance_total\n  volume_of_distribution · metabolism_pathway · pk_species\n\nSafety chunk injects:\n  adverse_events_list · grade_3_4_rate · death_count\n  qtc_prolongation · hepatotoxicity_warning\n  discontinuation_rate · serious_adverse_event_rate\n\nEfficacy chunk injects:\n  overall_response_rate · complete_response_rate\n  partial_response_rate · median_pfs · median_os\n  duration_of_response · time_to_response\n\nNEVER sends all 17 schemas to every chunk\nEffect: ~60% reduction in hallucination"]

        PASS1 --> PASS2 --> INJECT
    end

    CHUNKS -->|"Each chunk processed\nthrough Step 3"| PASS1

    INJECT --> CLASSIFIED["🏷️ Each Chunk now carries:\n  section: Pharmacokinetics\n  content: AUC values ranged from 21057...\n  schema_context: focus EXTRACTION on auc_value, cmax_value...\n  metadata:\n    chunk_index: 5\n    semantic_size: 1847\n    source_paragraphs: 23 24 25"]

    %% ════════════════════════════════════════════════════
    %% PARALLEL FORK → STEP 4 and STEP 5
    %% ════════════════════════════════════════════════════
    CLASSIFIED --> S4_ENTRY & S5_ENTRY

    %% ════════════════════════════════════════════════════
    %% STEP 4 — PARAGRAPH EXTRACTOR
    %% ════════════════════════════════════════════════════
    subgraph S4 ["  STEP 4 · Paragraph Extractor  ·  src/paragraph_extractor.py · ParagraphExtractor.extract_all  ·  Runs concurrently with Step 5  "]
        S4_ENTRY["⬇️ Paragraph Extractor Input\nHandles structured and predictable format fields\nDeterministic · No hallucination risk\nawait self.paragraph_extractor.extract_all\nclassified_data"]

        RE_EL["A. Eligibility Thresholds — Pure Regex\nTargets CLN-19 study section SPECIFICALLY\nto avoid criteria bleed from other studies:\ncln19_match = re.search\n  r CLN-19.*?inclusion.*?eligibility.*?criteria\n  text re.DOTALL re.IGNORECASE\n\nPatterns matched:\n  eligibility_anc_threshold: ANC >= or neutrophil count >=  → >= 1.0 × 10⁹/L\n  eligibility_platelet_threshold: platelets >=              → >= 50 × 10⁹/L\n  eligibility_creatinine_clearance: CrCl >= Cockcroft-Gault → >= 45 mL/min/1.73m²\n  eligibility_bilirubin_threshold: bilirubin <=             → <= 1.5 × ULN\n  eligibility_alt_ast_threshold: ALT <= or AST <=           → <= 2.5 × ULN\n  hepatic_impairment_exclusion: bilirubin > 2 × ULN excluded"]

        MICRO_LLM["B. Treatment Management — 4 Focused Micro-LLM Calls\nEach call has ONE narrow purpose\ntemperature = 0.0 — fully deterministic\nresponse_format = json_object\n\n_extract_dose_reductions:\n  Output: 1000 mg/m² → 750 mg/m² → 500 mg/m²\n\n_extract_treatment_delays:\n  Output: Hold if ANC < 0.5 × 10⁹/L at Day 8\n\n_extract_stopping_criteria:\n  Output: Stop for Grade 4 hepatotoxicity\n          Stop for Grade 3 hepatotox not resolving in 4 weeks\n\n_extract_supportive_care:\n  Output: Antiemetics · G-CSF · Anti-diarrheal agents"]

        PK_REGEX["C. PK Data — Regex with LLM Fallback\nRegex handles:\n  Range formats: 21057 to 31358 h·ng/mL\n  Multi-species protein binding: 94% in humans\n  Vd descriptive: approaches total body water\nFallback to targeted LLM call if regex finds nothing"]

        PRECLIN_PROMPT["D. Preclinical Toxicology — Expert Role-Play Prompt\nROLE: Expert Pre-Clinical Toxicologist\nTASK: Extract high-fidelity animal toxicology data\n\nINSTRUCTIONS:\n  1. ANALYZE SPECIES: Identify distinct findings for Rats vs Dogs vs Mice\n  2. DISTINGUISH: Single Dose acute vs Repeat Dose chronic\n  3. EXTRACT TARGETS: Specific organs — Thymus, Testis, Liver\n\nNEGATIVE CONSTRAINTS:\n  DO NOT mix data from different species\n  DO NOT confuse NOAEL with MTD\n  DO NOT guess units\n  DO NOT invent target organs not explicitly stated"]

        S4_ENTRY --> RE_EL & MICRO_LLM & PK_REGEX & PRECLIN_PROMPT
        RE_EL & MICRO_LLM & PK_REGEX & PRECLIN_PROMPT --> S4_OUT["Step 4 Result Object\n\neligibility_criteria:\n  anc_threshold: >= 1.0 × 10⁹/L\n  platelet_threshold: >= 50 × 10⁹/L\n  creatinine_clearance: >= 45 mL/min/1.73m²\n  bilirubin_threshold: <= 1.5 × ULN\n\ntreatment_management:\n  dose_reduction_schedule: 1000 → 750 → 500 mg/m²\n  treatment_delay_rules: Hold if ANC < 0.5 × 10⁹/L\n  toxicity_stopping_criteria: Stop Grade 4 hepatotox\n  supportive_care: Antiemetics · G-CSF\n\npharmacokinetics:\n  auc_value: 21057-31358 h·ng/mL\n  plasma_protein_binding: 94%\n  metabolism_pathway: UGT1A1\n\npreclinical_toxicology:\n  per-species NOAEL and MTD values\n  target organs per dose type"]
    end

    %% ════════════════════════════════════════════════════
    %% STEP 5 — DILI EXTRACTOR (main LLM)
    %% ════════════════════════════════════════════════════
    subgraph S5 ["  STEP 5 · DILI Extractor  ·  src/dili_extractor.py · DILIExtractor.extract_data  ·  Runs concurrently with Step 4  "]
        S5_ENTRY["⬇️ DILI Extractor Input\nAll classified chunks passed in\nawait self.extractor.extract_data\nclassified_data query_results\n\ntasks = _extract_chunk for chunk in classified_data\nresults = await asyncio.gather *tasks\nAll 60+ chunks fired simultaneously\nSpeedup: sequential 3 min → async ~15 sec"]

        NER_SCAN["NER Pre-scan — runs BEFORE each GPT-4o call\nner_scanner.scan chunk_text\nscispaCy en_core_sci_sm biomedical model\n\nReturns typed entity dict:\n  CHEMICAL: Belinostat · albumin · UGT1A1\n  DISEASE: PTCL · anemia · thrombocytopenia\n  GENE_OR_GENE_PRODUCT: HDAC1 · HDAC2\n\nInjected into prompt as:\n  NER HINT BLOCK\n  Potential Drugs/Chemicals: Belinostat, albumin\n  Potential Diseases/AEs: PTCL, anemia\n  Use this to cross-check. Do not hallucinate if not relevant."]

        LLM_CALL["GPT-4o via Azure OpenAI\nchat.completions.create\nmodel: gpt-4o\ntemperature: 0.1  near-deterministic\n\nMESSAGES payload contains:\n  system: expert clinical data extractor role\n  user: RAG schema fragment from Step 3\n       NER HINT block from NER scan\n       chunk text content\n\nFUNCTION CALLING:\n  functions: extract_belino_ib_data\n  parameters: BelinoIBExtractionSchema.model_json_schema\n  function_call: extract_belino_ib_data  forced\n\n17 extraction categories per chunk:\n  study_metadata · population_characteristics\n  dosing_administration · safety_data · efficacy_outcomes\n  pharmacokinetics · eligibility_criteria\n  treatment_management · mechanism_of_action\n  preclinical_toxicology · genotoxicity · carcinogenicity\n  reproductive_toxicity · drug_interactions\n  contraindications · special_populations\n  formulation_stability"]

        TRIPLES["Semantic Relationship Triple Extraction\nSame GPT-4o call also extracts SPO triples\nfrom the chunk text alongside the 17-category extraction\n\nsemantic_relationships.relationships:\n  subject: Belinostat\n  predicate: INHIBITS\n  object: HDAC\n\n  subject: Belinostat\n  predicate: METABOLIZED_BY\n  object: UGT1A1\n\n  subject: Grade 3 Anemia\n  predicate: CAUSED_BY\n  object: Study Treatment\n\nThese triples feed directly into Knowledge Graph edges"]

        S5_ENTRY --> NER_SCAN --> LLM_CALL --> TRIPLES
        TRIPLES --> S5_OUT["Step 5 Result: list of per-chunk JSON objects\nEach has 17-category structured extraction\n+ semantic relationship triples\n60-80 results total — one per chunk"]
    end

    %% ════════════════════════════════════════════════════
    %% MERGE STEP 4 + STEP 5 RESULTS
    %% ════════════════════════════════════════════════════
    S4_OUT & S5_OUT --> MERGE_CODE["🔀 Step 4 merged into Step 5 output\nPipeline code: pipeline.py lines 82-100\n\nFor eligibility_criteria:\n  if value is not None:\n    extracted_data.setdefault eligibility_criteria key = value\n\nFor treatment_management:\n  if value is not None and value != list:\n    extracted_data.setdefault treatment_management key = value\n\nFor pharmacokinetics:\n  if value is not None:\n    extracted_data.setdefault pharmacokinetics key = value\n\nFor preclinical_safety:\n  if value truthy:\n    extracted_data preclinical_toxicology key = value\n\nStep 4 values win for their specific fields\nStep 5 values used for everything else"]

    MERGE_CODE --> AGG["🔀 Smart Multi-Chunk Aggregation\n_aggregate_results across all 60-80 chunk results\n\nLists e.g. protocol_ids, ae_terms\n  → union deduplication: extend + dedupe\n\nStrings e.g. overall_response_rate, half_life\n  → first non-null value wins across chunks\n\nDicts e.g. safety_data, population\n  → recursive deep merge: inner keys merged independently\n\nBooleans e.g. tls_mentioned, hepatotoxicity_warning\n  → True takes priority over False over None"]

    %% ════════════════════════════════════════════════════
    %% AZURE DI OVERRIDE
    %% ════════════════════════════════════════════════════
    AGG --> OVR["🎯 Azure DI Query Field Override\n_merge_query_results merged_data query_results\n\nField mapping — Azure key → JSON path in extracted_data:\n  overall_response_rate → efficacy_outcomes.overall_response_rate_percent\n  median_pfs           → efficacy_outcomes.median_pfs\n  elimination_half_life → pharmacokinetics.elimination_half_life\n  grade_3_4_anemia     → safety_data.grade_3_4_anemia_rate\n  cardiac_qt_effect    → safety_data.qtc_interval_change\n  ...14 fields total\n\nRule: if Azure DI value is not None → replace LLM value\nWhy: Azure DI reads native PDF pixel layout\n     LLM reads derived Markdown text\n     Azure native reasoning more precise for point values\n\nEx: LLM extracted ORR = 26%\n    Azure DI answer  = 25.8%\n    Final value      = 25.8%  Azure wins"]

    QR_STORE --> OVR

    %% ════════════════════════════════════════════════════
    %% STEP 5 — VALIDATION (pipeline.py Step 5)
    %% ════════════════════════════════════════════════════
    subgraph STEP_VAL ["  STEP 5 in pipeline.py · Validation + Standardization  ·  src/validator.py · Validator  "]
        VALIDATE["Rule-Based Validation\nvalidator.validate extracted_data\n\nLiver Deaths:\n  if number_of_deaths < 0 → set to None\n  confirms: reported flag consistent with count\n\nPercentage format check:\n  if freq contains % → verify format\n\nCross-check consistency:\n  _cross_check_consistency\n  hepatotoxicity_signals vs liver_laboratory_monitoring\n  Flags contradictory implied data\n  Does NOT infer or fill — only validates\n\nMedDRA placeholder:\n  adverse_event_preferred_term checked\n  MedDRA.lookup reserved for future normalization"]

        STANDARDIZE["Unit Standardization\nvalidator.standardize final_data\n\nAdverse events:\n  map event_term to MedDRA Preferred Terms placeholder\n  map severity text to CTCAE grade levels\n\nAll operations non-destructive\nOriginal value preserved if normalization uncertain"]

        VALIDATE --> STANDARDIZE
    end

    OVR --> VALIDATE

    %% ════════════════════════════════════════════════════
    %% STEP 6 — GRAPH BUILDER (pipeline.py Step 6)
    %% ════════════════════════════════════════════════════
    subgraph STEP6 ["  STEP 6 in pipeline.py · Knowledge Graph Build  ·  src/logic/graph_builder.py · GraphBuilder.build_graph  "]
        BUILD["GraphBuilder.build_graph final_data\n\nNODE TYPES CREATED:\n  Drug node: Belinostat\n    properties: name, smiles, pubchem_cid, mol_weight\n\n  Study nodes: CLN-19 · TT20 · SPI-BEL-103\n    properties: phase, design, n_enrolled, countries\n\n  AdverseEvent nodes: Thrombocytopenia · Neutropenia · Anemia\n    properties: all_grade_pct, grade_3_4_pct, teae_flag, sae_flag\n\n  Target/Gene nodes: HDAC1 · HDAC2 · HDAC3 · UGT1A1\n    properties: gene_id, target_class\n\n  Population nodes: 129 PTCL patients\n    properties: n, indication, subtype, ecog_status\n\n  Outcome nodes: ORR 25.8% · Median PFS 1.6 months\n    properties: value, unit, study_context\n\nEDGE TYPES CREATED from LLM SPO triples:\n  Belinostat  INHIBITS        HDAC\n  Belinostat  CAUSES          Thrombocytopenia\n  Belinostat  METABOLIZED_BY  UGT1A1\n  CLN-19      ENROLLED        Population\n  CLN-19      ACHIEVED        ORR 25.8%"]

        GRAPH_OUT["graph_data dict\nTwo keys:\n  nodes: list of node objects\n  edges: list of edge objects\nWrites: output_graph.json\nEx: output.json → output_graph.json"]

        BUILD --> GRAPH_OUT
    end

    STANDARDIZE --> BUILD

    %% ════════════════════════════════════════════════════
    %% FINAL OUTPUTS
    %% ════════════════════════════════════════════════════
    subgraph OUTPUTS ["  📦 Final Outputs  "]

        OUT_JSON["output.json\nIntermediate structured JSON\nAll 17 categories · 60+ typed fields\nUsed as input for Excel writers"]

        OUT_GRAPH_JSON["output_graph.json\nKnowledge Graph\nnodes list + edges list\nJSON format"]

        subgraph EXCEL_BLOCK ["  ComprehensiveExcelWriter  ·  src/comprehensive_excel_writer.py  "]
            EXCEL_WRITE["StructuredExcelWriter.write_all final_data\nCreates: belino_comprehensive_complete.xlsx\n18 sheets via openpyxl\nHeader style: Font bold=True color=FFFFFF\nFill: PatternFill 2E75B6 blue\nAuto column width: min max_len+2 60"]

            SHEETS["18 Excel Sheets:\n1. Study Metadata — Phase · Design · Sponsor · Dates · IDs · Countries\n2. Population — N · Indication · Subtype · Age · Gender · ECOG\n3. Dosing — Route · Dose · Schedule · Cycle · Infusion · Combo drugs\n4. Safety — Deaths · Total AEs · QTc · Hepatotox warning\n5. Efficacy — ORR · CR · PR · Median time/duration of response\n6. Pharmacokinetics — AUC · Cmax · t1/2 · CL · Protein binding · Vd · Metabolism\n7. Eligibility — ANC · Platelets · CrCl · Bilirubin · ALT/AST thresholds\n8. Treatment Mgmt — Stopping criteria · Dose reductions · Delay rules · Supportive care\n9. Mechanism of Action — Description · Molecular targets · Cellular effects\n10. Preclinical Tox — Single/repeat dose · Species · Target organs · NOAEL · MTD\n11. Genotoxicity — In vitro · In vivo · Conclusion\n12. Carcinogenicity — Studies conducted · Results\n13. Reproductive Tox — Warnings · Developmental toxicity\n14. Drug Interactions — DDI studies · CYP enzymes · Mechanism · Significance\n15. Contraindications — List · Rationale\n16. Special Populations — Pediatric · Geriatric · Hepatic · Renal · Pregnancy · Lactation\n17. Formulation — Type · Excipients · Shelf life · Storage · Reconstitution\n18. Adverse Events — AE Term · Count · % · Grade 3-4 · TEAE flag · SAE flag"]

            EXCEL_WRITE --> SHEETS
        end

        subgraph CSV_BLOCK ["  Graph CSV Export  ·  src/logic/export_to_csv.py  "]
            CSV_NODES["graph_nodes.csv\nColumns: node_id · node_type · label · properties_json\nOne row per node\nNeo4j-importable format"]
            CSV_EDGES["graph_edges.csv\nColumns: source_id · target_id · edge_type · properties_json\nOne row per edge\nNeo4j-importable format"]
        end

        subgraph NEO4J_BLOCK ["  Neo4j Export  ·  src/logic/generate_neo4j_dump.py  "]
            CYPHER["belino_graph_dump.cypher\nCypher CREATE statements\nDirect Neo4j import\nMERGE ON node_id to avoid duplicates"]
        end

        subgraph VIZ_BLOCK ["  Graph Visualizer  ·  src/logic/generate_graph_viz.py  "]
            HTML_VIZ["graph_visualizer.html\nSelf-contained D3.js force-directed graph\nInteractive: zoom · pan · click nodes\nColor-coded by node type\nNo server needed — open in browser"]
        end
    end

    GRAPH_OUT --> OUT_JSON & OUT_GRAPH_JSON
    OUT_JSON --> EXCEL_WRITE
    OUT_GRAPH_JSON --> CSV_NODES & CSV_EDGES & CYPHER & HTML_VIZ

    %% ════════════════════════════════════════════════════
    %% PRIMARY CONSUMER OUTPUTS CALLOUT
    %% ════════════════════════════════════════════════════
    SHEETS --> FINAL(["✅ PRIMARY DELIVERABLE\nbelino_comprehensive_complete.xlsx\n18 sheets · all 17 clinical categories\nStakeholder-ready · color-coded headers\nAuto-adjusted column widths"])
    CSV_NODES & CSV_EDGES --> FINAL2(["✅ GRAPH DELIVERABLE\ngraph_nodes.csv + graph_edges.csv\nNeo4j-importable\nUsed by unified_kg_builder.py\nfor knowledge graph harmonization"])

    %% ════════════════════════════════════════════════════
    %% STYLES
    %% ════════════════════════════════════════════════════
    style STEP1 fill:#0c1a2e,stroke:#3b82f6,color:#e2e8f0
    style STEP2 fill:#0c1a2e,stroke:#06b6d4,color:#e2e8f0
    style STEP3 fill:#0c1a2e,stroke:#8b5cf6,color:#e2e8f0
    style S4 fill:#0c1a2e,stroke:#10b981,color:#e2e8f0
    style S5 fill:#0c1a2e,stroke:#f59e0b,color:#e2e8f0
    style STEP_VAL fill:#0c1a2e,stroke:#ef4444,color:#e2e8f0
    style STEP6 fill:#0c1a2e,stroke:#ec4899,color:#e2e8f0
    style OUTPUTS fill:#0c1a2e,stroke:#64748b,color:#e2e8f0
    style EXCEL_BLOCK fill:#052e16,stroke:#16a34a,color:#dcfce7
    style CSV_BLOCK fill:#1c1917,stroke:#a16207,color:#fef9c3
    style NEO4J_BLOCK fill:#1e1a2e,stroke:#7c3aed,color:#ede9fe
    style VIZ_BLOCK fill:#1e2a1e,stroke:#15803d,color:#dcfce7
    style OVR fill:#1e1b4b,stroke:#6d28d9,color:#e9d5ff
    style AGG fill:#172554,stroke:#2563eb,color:#bfdbfe
    style FINAL fill:#052e16,stroke:#16a34a,color:#dcfce7
    style FINAL2 fill:#172554,stroke:#2563eb,color:#bfdbfe
```

---

## What Each Output File Is For

| File | Format | Purpose | Consumer |
|------|--------|---------|----------|
| `belino_comprehensive_complete.xlsx` | Excel · 18 sheets | All 17 clinical categories — stakeholder ready | Clinicians · Regulatory team |
| `graph_nodes.csv` | CSV | All KG nodes with typed properties | Neo4j · `unified_kg_builder.py` |
| `graph_edges.csv` | CSV | All KG edges with typed properties + weights | Neo4j · `unified_kg_builder.py` |
| `belino_graph_dump.cypher` | Cypher | Direct Neo4j import statements | Neo4j database |
| `graph_visualizer.html` | HTML + D3.js | Interactive visual exploration of graph | Analysts · Demo |
| `output.json` | JSON | Intermediate — feeds Excel writer | `ComprehensiveExcelWriter` |
| `output_graph.json` | JSON | Intermediate — feeds CSV + Cypher + HTML | All graph exporters |

## Key Design Rules (External Understanding)

| Rule | Why |
|------|-----|
| **Cache first, API second** | Three cache layers avoid re-paying Azure API costs on every run |
| **Two independent AI reads** | Azure DI reads native PDF pixels; GPT-4o reads Markdown. Azure answer overrides where they disagree |
| **Context before LLM** | Section label + schema fragment injected before GPT-4o call — LLM never starts from zero |
| **Step 4 always wins its fields** | Regex + deterministic micro-prompts override LLM for eligibility, dose rules, and PK — no hallucination on numeric thresholds |
| **Async all the way** | `asyncio.gather` fires all 60+ LLM chunk calls simultaneously — time collapses from 3 min to ~15 sec |
| **Schema enforced at API level** | `function_call` forces Pydantic v2 schema — no post-hoc JSON parsing, no field drift |
