# AViiD — Pipeline Presentation Slides
> **Audience:** Product Manager · **Drug:** Belinostat (IB v13) · **Date:** March 2026

---

## Slide 1 — Title

**Title:** AViiD – Automated Investigator Brochure Data Extraction Pipeline  
**Subtitle:** Context Engineering + Azure AI + GPT-4o → Structured Clinical Knowledge Graph  
**Tags:** Context Engineering · Semantic Chunking · RAG Schema Injection · Knowledge Graph · GPT-4o · Azure OpenAI  
**Bottom line:** Belinostat (IB v13) · March 2026

---

## Slide 2 — The Problem

**Title:** Manual IB Extraction is Slow, Error-Prone & Unscalable

**Pointers:**
- Pharmaceutical IB documents = 100–300 pages of dense, unstructured clinical data
- Manual process: human expert reads PDF → fills Excel → 2–5 days per document
- Values buried in complex tables, footnotes, multi-level nested rows → high miss rate
- Not scalable across a drug portfolio of 50+ compounds
- Must extract: **17 categories / 60+ unique fields** per IB

```mermaid
flowchart LR
    A["📄 PDF\n200 pages"] -->|Manual Read| B["👤 Human Expert\n2–5 days/doc"]
    B -->|Manual Fill| C["📊 Excel Sheet"]
    A -->|"❌ Complexity"| D["Tables\nFootnotes\nNested Rows"]
    D -->|Leads to| E["Miss Rate\nErrors\nIncomplete Data"]
    B -->|"❌ Bottleneck"| F["Non-Scalable\n50+ IB docs"]
```

| Metric | Value |
|--------|-------|
| Pages per IB | 300+ |
| Categories to extract | 17 |
| Unique fields | 60+ |
| AViiD runtime | **~15 seconds** (vs. days manually) |

---

## Slide 3 — Data Sources

**Title:** What Data Are We Feeding the Pipeline?

**Pointers:**
- Three distinct data source types: clinical document, transcriptomics, chemical identity

```mermaid
flowchart TD
    S1["📄 SOURCE 1\nIB PDF\nbelino-ib v13"]
    S2["🧬 SOURCE 2\nTranscriptomics\nL1000 / LINCS"]
    S3["🔬 SOURCE 3\nChemical DB\nPubChem / DrugBank"]

    S1 -->|"PK params · Efficacy · Safety/AEs\nDosing · Eligibility · Preclinical tox\nDrug interactions"| P1["AViiD Pipeline\nSteps 1–6"]
    S2 -->|"Signature IDs · Gene targets\nCell lines · Tissue types\nlogFC + p-values (top 20 genes)"| P2["unified_kg_builder\nHarmonization"]
    S3 -->|"SMILES · Mol weight\nPubChem CID · Formula\nPerturbationID"| P3["Enrichment Layer\nDrug node props"]

    P1 --> KG["🕸️ Unified Knowledge Graph JSON"]
    P2 --> KG
    P3 --> KG
```

---

## Slide 4 — Pipeline Architecture

**Title:** 6-Step AI Pipeline — End-to-End in ~15 Seconds

**Pointers:**
- Entire pipeline runs **async** (`asyncio.gather`) — all 60+ LLM calls in parallel
- Three-level JSON cache avoids re-calling Azure APIs on re-runs
- Azure DI Query Field results **override** LLM values post-extraction (ground truth)

```mermaid
flowchart TD
    PDF["📄 PDF Input\nbelino-ib-v13.pdf"]

    PDF --> S1["STEP 1 · Azure Document Intelligence\nlayout_parser.py\n→ Markdown + 14 Query Field answers"]
    S1 --> S2["STEP 2 · Semantic Chunker\nsemantic_chunker.py\n→ ~60 coherent topic chunks\nembedding cosine sim · threshold 0.75"]
    S2 --> S3["STEP 3 · Context Classifier + RAG Injector\ncontext_classifier.py · schema/context.py\n→ 14 section labels + focused schema per chunk"]
    S3 --> S4["STEP 4 · Paragraph Extractor\nparagraph_extractor.py\nRegex + targeted micro-prompts"]
    S3 --> S5["STEP 5 · DILI Extractor\ndili_extractor.py\nGPT-4o · asyncio · function_call\n17 categories extracted concurrently"]
    S4 --> S6["STEP 6 · Validator + Graph Builder\nvalidator.py · graph_builder.py\nPydantic validation · Neo4j Cypher · D3.js"]
    S5 --> S6

    style S3 fill:#1e1b4b,stroke:#6d28d9,color:#e9d5ff
    style S5 fill:#172554,stroke:#2563eb,color:#bfdbfe
```

---

## Slide 5 — PDF to Structured Data: Full Extraction Flow

**Title:** How We Extract from PDF — Step by Step

```mermaid
flowchart TD
    PDF["📄 belino-ib-v13.pdf"]

    PDF --> DI["Azure Document Intelligence\nprebuilt-layout model\n· OCR on original page pixels\n· Tables → Markdown col/col syntax\n· Headers → nested ## levels"]

    DI --> MD["📝 Markdown ~228KB\ncache_layout.json"]
    DI --> QR["🎯 Query Results dict\n14 NL questions answered\ncache_query_results.json"]

    MD --> SC["Semantic Chunker\n1. Split by double newline → raw paragraphs\n2. Embed each → 1536-dim vector\n3. Sliding window cosine similarity\n   · sim > 0.75 → MERGE same topic\n   · sim < 0.75 → SPLIT new topic\n   · chunk > 2000 chars → force split\nOutput: ~60-80 chunks\ncache_classified.json"]

    SC --> CC["Context Classifier\nPass 1: Regex scan first Markdown header → keyword match → section label\nPass 2: If no header → scan first 500 chars for domain keywords\nOutput: 1 of 14 labels per chunk\nPK · Safety · Efficacy · Hepatotoxicity · MOA · ..."]

    CC --> RAG["RAG Schema Injector\nPK chunk → inject: auc_value, cmax_value, elimination_half_life ...\nSafety chunk → inject: adverse_events_list, grade_3_4_rate, death_count ...\nNever sends all 17 schemas at once"]

    RAG --> NER["NER Pre-scan · scispaCy\nCHEMICAL: Belinostat, UGT1A1\nDISEASE: PTCL, Anemia\n→ appended as NER HINT block into prompt"]

    NER --> LLM["GPT-4o · All chunks concurrent\nasyncio.gather · temperature=0.1\nfunction_call = extract_belino_ib_data\nPydantic v2 schema enforced"]

    LLM --> AGG["Smart Aggregation\nLists → union dedup\nStrings → first non-null\nBooleans → True > False > None"]

    AGG --> OVR["Azure DI Override\n14 key fields replaced with\nground-truth Query Field answers\ne.g. ORR: LLM 26% → Azure 25.8%"]

    QR --> OVR

    OVR --> OUT["📦 belino_comprehensive.json\n17 categories · 60+ fields · typed"]
```

---

## Slide 6 — Context Engineering Deep Dive

**Title:** 6 Layers That Eliminate Hallucination (~60% reduction)

> Context engineering = precisely crafting what the LLM sees at each step

```mermaid
flowchart TD
    CHUNK["Incoming Chunk"]

    CHUNK --> L2{"L2 · Semantic Chunking\nIs chunk topically coherent?"}
    L2 -->|No| SPLIT["SPLIT further"]
    L2 -->|Yes| L3["L3 · RAG Schema Injection ⭐\nClassify section type\nInject ONLY relevant schema fields"]

    L3 --> L4["L4 · NER Hint Injection\nscispaCy detects entities\nAppend as pre-prompt hint"]

    L4 --> LLM["GPT-4o Call"]

    LLM --> L5{"L5 · Function Calling\nOutput matches Pydantic schema?"}
    L5 -->|No| RETRY["Retry / log error"]
    L5 -->|Yes| L6{"L6 · Query Field Override\nAzure DI disagrees?"}
    L6 -->|Yes| AZ["Use Azure DI value\nground truth from raw PDF"]
    L6 -->|No| FINAL["✅ Final extracted value"]
    AZ --> FINAL
```

| Layer | Technique | What it solves |
|-------|-----------|----------------|
| **L1** | Azure DI → Markdown | Tables preserved as `\|col\|col\|` — LLM reads structure not flat text |
| **L2** | Embedding cosine similarity chunking | No mid-table cuts; related paragraphs stay together |
| **L3** | RAG Schema Injection ⭐ | PK chunk → only PK fields; Safety → only AE fields; never all 17 |
| **L4** | scispaCy NER hints | Primes LLM: "look for Belinostat, HDAC1, PTCL in this chunk" |
| **L5** | OpenAI function_call + Pydantic v2 | Enforces exact JSON schema; no field name drift |
| **L6** | Azure DI Query Field override | Two AI systems cross-validate; Azure PDF-native answer wins |

---

## Slide 7 — Storage, Harmonization & Analysis

**Title:** How Data is Stored and Analyzed

```mermaid
flowchart LR
    subgraph STORAGE ["💾 Storage Layer"]
        J1["belino_comprehensive.json\n17 categories · 60+ fields"]
        J2["cache_layout.json\nMarkdown 228KB"]
        J3["cache_classified.json\nChunks + labels 293KB"]
        X1["belino_comprehensive.xlsx\nStakeholder Excel"]
        C1["graph_nodes.csv\ngraph_edges.csv\nNeo4j-importable"]
        Q1["belino_graph_dump.cypher\nNeo4j Cypher statements"]
    end

    subgraph ANALYSIS ["🔍 Analysis Layer — unified_kg_builder.py"]
        L1["Load Sources\n· belino_comprehensive_consolidated.xlsx\n· meta_sigSearch...xls\n· sig_Fri_Feb_13...xls"]
        L2["Clean\nNaN/inf → null · whitespace strip\nSHA-256 stable node IDs"]
        L3["Build Nodes\nDrug · Signature · Gene\nTarget · AE · CellLine · Tissue"]
        L4["Build Edges\nDeterministic rules from source columns"]
        L5["Second Pass Enrichment\nlogFC + p-value on gene edges\nMol weight + CID on Drug nodes"]
        L6["Validate & Export\nOrphan edge check\nbelino_refined_kb.json"]
    end

    STORAGE --> ANALYSIS
    L1 --> L2 --> L3 --> L4 --> L5 --> L6
```

**Key design decisions:**
- All ID matching: **strict exact-string only** — prefer dropping a connection over guessing wrong
- Top 20 genes per signature by absolute logFC (quality over quantity)
- In-memory graph (~70 nodes) — Neo4j migration path for scale > 100K nodes

---

## Slide 8 — Knowledge Graph: Meaningful Nodes & Edges

**Title:** How Meaningful Relationships Are Formed

```mermaid
flowchart LR
    subgraph SOURCES ["Data Sources → Edge Rules"]
        M1["Metadata file\nPerturbagen column"]
        M2["Metadata file\nCellLine column"]
        M3["Metadata file\nTissue column"]
        M4["Metadata file\nGeneTargets col\nHDAC1|HDAC2|HDAC3"]
        M5["Consolidated Safety\nAdverse Events sheet"]
        M6["Signature gene data\nlogFC · p-value"]
        M7["LLM-extracted triples\nfrom DILIExtractor"]
    end

    subgraph GRAPH ["Knowledge Graph Edges"]
        E1["Drug ──tested_in──→ Signature"]
        E2["Signature ──observed_in──→ CellLine"]
        E3["CellLine ──derived_from──→ Tissue"]
        E4["Drug ──targets──→ HDAC1 / HDAC2 / HDAC3\n(pipe-split → N edges)"]
        E5["Drug ──causes──→ AdverseEvent\n{frequency: 23.3%, grade: '3/4'}"]
        E6["Signature ──associated_with──→ Gene\n{logFC: 2.3, p_value: 0.0012}"]
        E7["Belinostat ──INHIBITS──→ HDAC\nBelinostat ──METABOLIZED_BY──→ UGT1A1\nBelinostat ──CAUSES──→ Thrombocytopenia"]
    end

    M1 --> E1
    M2 --> E2
    M3 --> E3
    M4 --> E4
    M5 --> E5
    M6 --> E6
    M7 --> E7
```

**Why edges are meaningful — not just data dumps:**
- Edges carry **quantitative properties** — not just "Drug causes AE" but *how often* (23.3%) and *what grade* (3/4)
- Gene edges weighted by statistical significance: logFC + p-value — only real associations survive
- All triples are **SPARQL/Cypher queryable** in Neo4j
  - Example: *"Which genes are associated with Belinostat signatures in liver tissue?"*
- Node IDs are deterministic (SHA-256) → multiple pipeline runs produce identical, mergeable graphs

---

## Slide 9 — TxGemma Integration Plan

**Title:** TxGemma — AI-Grounded Toxicity Prediction Layer

**What is TxGemma:**
- Google DeepMind's therapeutics-domain LLM — trained on molecular biology, clinical safety literature, and Therapeutics Data Commons (TDC) benchmarks
- Two variants: `txgemma-2b-predict` (property prediction) · `txgemma-9b-it` (chat / multi-turn reasoning)

```mermaid
flowchart TD
    JSON["📦 belino_comprehensive.json\nAViiD pipeline output\n60+ structured clinical fields"]

    JSON --> UC1["USE CASE 1 · DILI Risk from SMILES\nInput: Belinostat SMILES string\nModel: txgemma-2b-predict\nOutput: DILI risk Low/Med/High\n+ structural hepatotoxicity features"]

    JSON --> UC2["USE CASE 2 · Chunk Pre-Scoring\nInput: IB text chunk + section label\nModel: txgemma-2b-predict\nOutput: DILI relevance score 0–10\nScore > 6 → specialized hepatotox extractor\nScore < 3 → skip GPT-4o call → cost reduction"]

    JSON --> UC3["USE CASE 3 · AE Severity Analysis\nInput: Safety section clinical text\nModel: txgemma-9b-it\nOutput: DILI level · hepatotox signals\nsafety score 1–10 · monitoring plan"]

    JSON --> UC4["USE CASE 4 · DDI Reasoning Chat\nInput: Belinostat + co-medication\nModel: txgemma-9b-it multi-turn\nOutput: DDI risk · PK mechanism\nmonitoring recommendations"]

    UC1 & UC2 & UC3 & UC4 --> OUT["🎯 Outputs\nDILI risk classification\nPer-chunk DILI routing score\nMonitoring recommendations\nDDI reasoning from PK pathway\n→ Future: grounded DILI chatbot"]
```

**Model parameters:**

| Parameter | Value | Why |
|-----------|-------|-----|
| `torch_dtype` | `bfloat16` | Memory-efficient on GPU |
| `device_map` | `auto` | Auto-uses available GPU |
| `do_sample` | `False` | Deterministic — clinical use |
| `temperature` | `1.0` (greedy with do_sample=False) | No randomness in predictions |
| `max_new_tokens` | 80 (scoring) · 400 (full analysis) | Task-adjusted |
| `quantization` | 4-bit NF4 via `bitsandbytes` | Fits 2B on free T4 GPU (~4GB VRAM) |
| `quant compute dtype` | `bfloat16` | Accuracy-memory balance |

**Prompt engineering technique:**
- Uses **Gemma chat template**: `<start_of_turn>user ... <end_of_turn><start_of_turn>model`
- Role-play prompting: *"You are a clinical safety analyst reviewing an Investigator Brochure"*
- Structured output format: `Score: X/10 | Reason: [one sentence]` for chunk scoring tasks

**Hardware tiers:**

| Tier | GPU | Model | Use |
|------|-----|-------|-----|
| Free Colab | T4 (15GB VRAM) | txgemma-2b-predict | DILI scoring + property prediction |
| Colab Pro | A100 (40GB) | txgemma-9b-it | Chat, DDI reasoning, AE analysis |

**What we get:**
- ✅ DILI risk classification from molecular structure (SMILES → Low/Med/High/Severe)
- ✅ Per-chunk DILI relevance score → intelligent routing, reduced GPT-4o API cost  
- ✅ Monitoring recommendations grounded in clinical text
- ✅ Drug-drug interaction reasoning via UGT1A1 metabolism pathway
- 🔮 Future: grounded DILI chatbot — answers *"Why is Belinostat hepatotoxic?"* citing extracted knowledge graph
