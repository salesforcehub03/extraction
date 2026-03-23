from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
from openai import AsyncAzureOpenAI
from config import Config
import json
import asyncio

# Import enhanced schemas (master schema kept for aggregation compatibility)
from .enhanced_schemas import (
    BelinoIBExtractionSchema,
    StudyMetadata,
    PopulationCharacteristics,
    DosingAdministration,
    SafetyData,
    AdverseEventDetail,
    EfficacyOutcomes,
    Pharmacokinetics,
    EligibilityCriteria,
    TreatmentManagement
)
from .schema.context import SchemaContextInjector

# ── Context Engineering: New imports (Pillars 1, 2, 3, 4) ──────────────────
from .prompt_registry import PromptRegistry
from .schema.section_schemas import get_schema_for_section
from .extraction_scratchpad import ExtractionScratchpad
from .context_engine import ContextStore
from .telemetry import TelemetryTracker

# Keep legacy schemas for backward compatibility


class StudyMetadata(BaseModel):
    protocol_ids: List[str] = Field(default_factory=list, description="List all study IDs, e.g., CLN-19, SPI-BEL-103")
    clinical_phase: Optional[str] = Field(None, description="e.g., Phase 2")
    target_indication: Optional[str] = Field(None, description="e.g., Peripheral T-Cell Lymphoma / PTCL")

class DosingRegimen(BaseModel):
    recommended_dose: Optional[str] = Field(None, description="e.g., 1000 mg/m2")
    infusion_time: Optional[str] = Field(None, description="e.g., 30 minutes")
    cycle_schedule: Optional[str] = Field(None, description="e.g., Days 1-5 of a 21-day cycle")
    route: Optional[str] = Field(None, description="IV")

class EfficacyOutcomes(BaseModel):
    overall_response_rate_percent: Optional[str] = Field(None, description="e.g., 25.8%")
    complete_response_percent: Optional[str] = None
    partial_response_percent: Optional[str] = None
    median_duration_of_response: Optional[str] = Field(None, description="e.g., 13.6 months")
    median_pfs: Optional[str] = Field(None, description="Progression Free Survival")
    median_os: Optional[str] = Field(None, description="Overall Survival")

class Pharmacokinetics(BaseModel):
    elimination_half_life: Optional[str] = Field(None, description="e.g., 1.1 hours")
    plasma_protein_binding: Optional[str] = Field(None, description="e.g., 94%")
    clearance_total: Optional[str] = Field(None, description="CL values")
    volume_of_distribution: Optional[str] = Field(None, description="Vss or Vd values")
    metabolism_pathway: Optional[str] = Field(None, description="e.g., Glucuronidation via UGT1A1")

class HematologicARs(BaseModel):
    thrombocytopenia_rate: Optional[str] = Field(None, description="Overall %")
    neutropenia_rate: Optional[str] = Field(None, description="Overall %")
    anemia_rate: Optional[str] = Field(None, description="Overall %")

class NonHematologicARs(BaseModel):
    nausea_rate: Optional[str] = Field(None, description="Overall %")
    fatigue_rate: Optional[str] = Field(None, description="Overall %")
    pyrexia_rate: Optional[str] = Field(None, description="Overall %")
    vomiting_rate: Optional[str] = Field(None, description="Overall %")

class SeriousSafetySignals(BaseModel):
    tumor_lysis_syndrome_mentioned: bool = False
    grade_3_4_toxicity_rate: Optional[str] = Field(None, description="Overall % of patients with G3/4 events")

class SafetyAdverseEvents(BaseModel):
    most_common_hematologic: HematologicARs
    most_common_non_hematologic: NonHematologicARs
    serious_safety_signals: SeriousSafetySignals

class CardiacSafety(BaseModel):
    qtc_prolongation_risk: Optional[str] = Field(None, description="Description of risk")
    mean_qtc_change: Optional[str] = Field(None, description="e.g., <10 ms")
    outliers_qtc_500ms: Optional[str] = Field(None, description="Number or % of patients with QTc > 500ms")

class LiverSafetyProfile(BaseModel):
    hepatotoxicity_warning: Optional[str] = Field(None, description="Verbatim warning")
    required_monitoring: Optional[str] = Field(None, description="Specific LFT instructions")
    hepatic_exclusion_criteria: Optional[str] = Field(None, description="Specific Bilirubin/ALT cutoffs")

# --- NEW: Table-Specific Extraction Schemas ---

class PooledGroup(BaseModel):
    group_id: str = Field(..., description="e.g., 'Group 1', 'Group 2'")
    group_description: Optional[str] = Field(None, description="e.g., 'Pivotal monotherapy'")
    study_ids: List[str] = Field(default_factory=list, description="Study IDs in this group")
    n_treated: Optional[int] = Field(None, description="Total N treated in this group")

class PooledAnalysisStructure(BaseModel):
    groups: List[PooledGroup] = Field(default_factory=list, description="List of pooled analysis groups from Table 2")

class StudyDetail(BaseModel):
    study_id: str
    phase: Optional[str] = None
    country: Optional[str] = None
    study_title: Optional[str] = None
    design: Optional[str] = Field(None, description="e.g., 'Open-label, single-arm'")
    dosing_regimen: Optional[str] = None
    population: Optional[str] = None
    n_enrolled: Optional[int] = None
    study_period: Optional[str] = None
    status: Optional[str] = Field(None, description="e.g., 'Completed', 'Ongoing'")

class BaselineDemographics(BaseModel):
    study_or_group_id: str = Field(..., description="Study ID or Group ID this data applies to")
    n: Optional[int] = None
    median_age: Optional[str] = None
    age_range: Optional[str] = None
    male_percent: Optional[str] = None
    female_percent: Optional[str] = None
    ecog_0_1_percent: Optional[str] = None
    disease_subtype_breakdown: Optional[Dict[str, str]] = Field(None, description="e.g., {'PTCL-NOS': '35%'}")

class AdverseEventDetail(BaseModel):
    event_term: str
    all_grades_n: Optional[int] = None
    all_grades_percent: Optional[str] = None
    grade_3_4_n: Optional[int] = None
    grade_3_4_percent: Optional[str] = None

class SafetyTableExtraction(BaseModel):
    study_or_group_id: str = Field(..., description="Study ID or Group ID")
    table_type: str = Field(..., description="'TEAEs', 'Treatment-Related AEs', 'SAEs', 'Discontinuations'")
    events: List[AdverseEventDetail] = Field(default_factory=list)

class DILIExtractionSchema(BaseModel):
    # Core fields
    study_metadata: StudyMetadata
    dosing_regimen: DosingRegimen
    efficacy_outcomes: EfficacyOutcomes
    pharmacokinetics: Pharmacokinetics
    safety_adverse_events: SafetyAdverseEvents
    cardiac_safety: CardiacSafety
    liver_safety_profile: LiverSafetyProfile
    
    # NEW: Table-specific extraction fields
    pooled_analysis_structure: Optional[PooledAnalysisStructure] = None
    study_details: List[StudyDetail] = Field(default_factory=list)
    baseline_demographics: List[BaselineDemographics] = Field(default_factory=list)
    detailed_safety_tables: List[SafetyTableExtraction] = Field(default_factory=list)

# --- Extractor Class ---

class DILIExtractor:
    def __init__(self):
        Config.validate()
        self.client = AsyncAzureOpenAI(
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
            api_key=Config.AZURE_OPENAI_KEY,
            api_version=Config.AZURE_OPENAI_API_VERSION
        )
        self.deployment_name = Config.AZURE_OPENAI_DEPLOYMENT_NAME
        # Optimization: Chunk config
        self.CHUNK_SIZE = 4000 # Estimate chars or tokens
        self.OVERLAP = 500
        # Lazy import of NER Scanner to handle potential missing dependency
        try:
            from .logic.ner_scanner import NERScanner
            self.ner_scanner = NERScanner()
        except ImportError:
            print("Warning: NERScanner (scispaCy) not available.")
            self.ner_scanner = None

        # ── Context Engineering: Scratchpad for cross-chunk memory (Pillar 4) ──
        self.scratchpad = ExtractionScratchpad(persist_path="scratchpad.json")
        # ContextStore is injected after classify step (set by pipeline.py)
        self.context_store: Optional[ContextStore] = None
        self.telemetry = TelemetryTracker()

    async def extract_data(
        self,
        classified_data: List[dict],
        query_results: Dict[str, Any] = None,
        context_store: Optional[ContextStore] = None
    ) -> dict:
        """
        Extract DILI-relevant data using Context-Engineered Chunking and Async Aggregation.

        Context Engineering enhancements (v2.0):
          - Pillar 1: PromptRegistry provides XML-tagged, section-specific system prompts
          - Pillar 3: Focused per-section schemas (5-15 fields) instead of 90-field monolith
          - Pillar 4: ExtractionScratchpad carries cross-chunk established facts
          - Pillar 2: ContextStore available for JIT retrieval of missing context

        Args:
            classified_data: List of chunk dicts from ContextClassifier
            query_results: Optional Azure Query Fields ground-truth values
            context_store: Optional ContextStore for JIT retrieval (Pillar 2)
        """
        if not classified_data:
            return {}

        # Attach ContextStore for JIT retrieval during extraction
        if context_store:
            self.context_store = context_store

        # Filter out "Other" chunks ONLY if they are very short (< 200 chars) to avoid noise.
        # Long "Other" chunks likely contain valuable data and should still be extracted.
        extraction_data = [
            c for c in classified_data
            if c["section"] != "Other" or len(c.get("content", "")) > 300
        ]
        skipped = len(classified_data) - len(extraction_data)

        # Batch config — tune BATCH_SIZE and BATCH_SLEEP_SECS to stay within TPM.
        # At ~1,200 tokens/chunk: BATCH_SIZE=8 → ~9,600 tokens/batch, well under S0 limit.
        # BATCH_SLEEP_SECS gives the TPM window time to reset between batches.
        BATCH_SIZE   = getattr(Config, 'EXTRACTION_BATCH_SIZE', 8)
        BATCH_SLEEP  = getattr(Config, 'EXTRACTION_BATCH_SLEEP', 3)  # seconds between batches

        total = len(extraction_data)
        print(f"   -> Processing {total} chunks in batches of {BATCH_SIZE} (sleep {BATCH_SLEEP}s between batches)...")
        print(f"   -> {skipped} trivial 'Other' chunks skipped. Prompt modules: {len(PromptRegistry.list_sections())} sections.")

        results = []
        for batch_start in range(0, total, BATCH_SIZE):
            batch = extraction_data[batch_start : batch_start + BATCH_SIZE]
            batch_num = batch_start // BATCH_SIZE + 1
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
            print(f"   -> Batch {batch_num}/{total_batches}: {len(batch)} chunks "
                  f"({[c['section'] for c in batch][:3]}...)")

            # Fire batch concurrently (within-batch parallelism is fine at this size)
            batch_results = await asyncio.gather(*[
                self._extract_chunk(chunk_item, chunk_item["section"])
                for chunk_item in batch
            ], return_exceptions=True)

            for res in batch_results:
                if isinstance(res, Exception):
                    print(f"   -> Batch exception: {res}")
                    results.append({})
                else:
                    results.append(res)

            # Sleep between batches (not after the last one)
            if batch_start + BATCH_SIZE < total:
                await asyncio.sleep(BATCH_SLEEP)

        # Update scratchpad after all chunks complete
        for result, chunk_item in zip(results, extraction_data):
            if result:
                self.scratchpad.update(result, chunk_item.get("section", "Other"))

        # Aggregate across all chunk results
        merged_data = self._aggregate_results(results)

        # Azure Query Fields override (ground truth from native PDF reasoning)
        if query_results:
            print(f"   -> Merging {len(query_results)} Azure Query Field overrides...")
            merged_data = self._merge_query_results(merged_data, query_results)

        return merged_data



    def _create_chunks(self, text_parts: List[dict]) -> List[tuple]:
        chunks = []
        for item in text_parts:
             section = item.get("section", "Unknown")
             text = item.get("content", "")
             
             start = 0
             while start < len(text):
                end = start + self.CHUNK_SIZE
                chunk = text[start:end]
                chunks.append((chunk, section))
                start += (self.CHUNK_SIZE - self.OVERLAP)
        return chunks

    async def _extract_chunk(self, chunk_data: dict, section_name: str = "Unknown") -> dict:
        """
        Extracts data from a single chunk using Context-Engineered prompts.

        Context Engineering v2.0 changes:
          1. System prompt: PromptRegistry.get_system_prompt() → XML-tagged, section-specific
             (replaces the 600-line monolithic f-string)
          2. Function schema: get_schema_for_section() → focused 5-15 field schema
             (replaces BelinoIBExtractionSchema with all 90 fields)
          3. Prior context: scratchpad.get_context_injection() → cross-chunk established facts
          4. NER hint: preserved as a lightweight validation layer
        """
        chunk_text = chunk_data.get("content", "")
        chunk_index = chunk_data.get("metadata", {}).get("chunk_index", -1)

        # ── Pillar 4: Inject scratchpad prior context ──────────────────────
        prior_context = self.scratchpad.get_context_injection(section_name)

        # ── Pillar 1: Get section-specific, XML-tagged system prompt ───────
        system_prompt = PromptRegistry.get_system_prompt(section_name, prior_context=prior_context)

        # ── Pillar 3: Get focused section schema (5-15 fields only) ────────
        schema_info = get_schema_for_section(section_name)
        focused_model = schema_info["model"]
        tool_name = schema_info["tool"]

        # NER SCANNING (Validation Layer — preserved from v1)
        ner_context = ""
        if self.ner_scanner:
           try:
               ner_results = self.ner_scanner.scan(chunk_text)
               chemicals = ", ".join(ner_results.get("CHEMICAL", [])[:10])
               diseases = ", ".join(ner_results.get("DISEASE", [])[:10])
               if chemicals or diseases:
                   ner_context = (
                       "\n<ner_validation_hint>\n"
                       "Biomedical NER model detected these entities — use for cross-checking:\n"
                       f"  Chemicals/Drugs: {chemicals}\n"
                       f"  Diseases/AEs: {diseases}\n"
                       "Do NOT hallucinate entities not present in the text.\n"
                       "</ner_validation_hint>"
                   )
           except Exception as e:
               print(f"NER Scan failed: {e}")

        # Append NER hint to system prompt if available
        if ner_context:
            system_prompt = system_prompt + ner_context

        # ── Pillar 2: JIT retrieval — detect cross-references in chunk ─────
        # If the chunk text mentions an external reference and we have a context store,
        # attempt to resolve it and append the content inline.
        jit_supplement = ""
        if self.context_store and chunk_index >= 0:
            import re
            table_refs = re.findall(r'(?:see\s+)?Table\s+(\d+[\-\.]?\d*)', chunk_text, re.IGNORECASE)
            for ref in table_refs[:2]:  # Limit to 2 refs per chunk to control token growth
                ref_str = f"Table {ref}"
                resolved = self.context_store.retrieve_by_reference(ref_str)
                if resolved and resolved.get("metadata", {}).get("chunk_index", -1) != chunk_index:
                    jit_supplement += f"\n\n[JIT RETRIEVED: {ref_str}]\n{resolved['content'][:800]}"
                    self.scratchpad.mark_reference_resolved(ref_str, f"chunk_{resolved['metadata'].get('chunk_index', '?')}")

        # Build user message
        user_content = f"""Chunk Content (Section: {section_name}):\n{chunk_text}"""
        if jit_supplement:
            user_content += f"\n\n--- Additional Context (JIT Retrieved) ---{jit_supplement}"
        user_content += "\n\nExtract all relevant clinical data fields for this section."

        # ── API Call with focused schema + retry for 429 ──────────────────
        telemetry_start = self.telemetry.start_chunk()
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    functions=[{
                        "name": tool_name,
                        "description": f"Extract {section_name} data from the Belinostat IB chunk.",
                        "parameters": focused_model.model_json_schema()
                    }],
                    function_call={"name": tool_name},
                    temperature=0.1
                )
                args = response.choices[0].message.function_call.arguments
                section_result = json.loads(args)

                # Record successful telemetry
                usage = getattr(response, 'usage', None)
                tokens = {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0
                }
                self.telemetry.end_chunk(
                    chunk_index=chunk_index,
                    section_type=section_name,
                    start_time=telemetry_start,
                    tokens=tokens,
                    retry_count=attempt
                )

                # ── Remap focused section result back to master schema keys ────
                return self._remap_to_master_schema(section_result, section_name)

            except Exception as e:
                err_str = str(e)
                # Handle rate limit (429) with linear backoff (15s, 30s, 45s, 60s...)
                if "429" in err_str or "RateLimitReached" in err_str:
                    if attempt < max_retries - 1:
                        wait_secs = (attempt + 1) * 15
                        import random
                        wait_secs += random.uniform(0, 5)  # jitter
                        print(f"   -> Rate limit hit [{section_name}], retrying in {wait_secs:.0f}s (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(wait_secs)
                        continue
                    else:
                        print(f"   -> Rate limit: max retries exhausted [{section_name}], skipping chunk.")
                        self.telemetry.end_chunk(
                            chunk_index=chunk_index, 
                            section_type=section_name, 
                            start_time=telemetry_start, 
                            tokens={}, 
                            retry_count=attempt, 
                            error="Rate Limit Max Retries"
                        )
                        return {"extraction_metadata": {"notes": "Rate Limited during extraction"}}
                # Handle content filter (400) — skip chunk, don't crash
                elif "content_filter" in err_str or "ResponsibleAIPolicyViolation" in err_str:
                    print(f"   -> Content filter triggered [{section_name}], skipping chunk.")
                    self.telemetry.end_chunk(
                        chunk_index=chunk_index, 
                        section_type=section_name, 
                        start_time=telemetry_start, 
                        tokens={}, 
                        error="Content Filter"
                    )
                    return {}
                else:
                    print(f"   -> Extraction error [{section_name}]: {e}")
                    self.telemetry.end_chunk(
                        chunk_index=chunk_index, 
                        section_type=section_name, 
                        start_time=telemetry_start, 
                        tokens={}, 
                        error=err_str
                    )
                    return {}
        return {}


    def _remap_to_master_schema(self, section_result: dict, section_name: str) -> dict:
        """
        Maps a focused section extraction result back into the top-level
        BelinoIBExtractionSchema key structure so that _aggregate_results() works correctly.
        """
        # Remove the cross-section semantic_relationships — merge separately
        relationships = section_result.pop("semantic_relationships", [])

        # Complete section → master schema key mapping
        section_key_map = {
            # Study metadata
            "Drug Overview":                      "study_metadata",
            "Clinical Study Design":              "clinical_studies_data",
            # Population
            "Population Characteristics":         "clinical_studies_data",
            # Mechanism
            "Mechanism of Action":                "mechanism_of_action",
            # PK
            "Pharmacokinetics":                   "pharmacokinetics",
            # Efficacy
            "Efficacy Outcomes":                  "clinical_studies_data",
            # Safety — all safety sub-sections merge into safety_data
            "Safety and Adverse Events":          "safety_data",
            "Hepatotoxicity":                     "safety_data",
            "Cardiac Safety":                     "safety_data",
            "Deaths and Serious Adverse Events":  "safety_data",
            "Monitoring and Warnings":            "safety_data",
            # Dosing / treatment
            "Dosing Regimen":                     "dosing_administration",
            "Dose Modifications":                 "treatment_management",
            # Preclinical
            "Nonclinical Toxicology":             "preclinical_toxicology",
            # Eligibility
            "Eligibility Criteria":               "eligibility_criteria",
            # Special populations
            "Special Populations – Hepatic":      "special_populations",
            "Special Populations":                "special_populations",
            # Drug interactions
            "Drug Interactions":                  "drug_interactions",
            # Formulation & stability
            "Formulation and Stability":          "formulation_stability",
            "Formulation":                        "formulation_stability",
            # Contraindications
            "Contraindications":                  "contraindications",
            # Genotoxicity / carcinogenicity / reproductive
            "Genotoxicity":                       "genotoxicity",
            "Carcinogenicity":                    "carcinogenicity",
            "Reproductive Toxicity":              "reproductive_toxicity",
        }

        master_key = section_key_map.get(section_name)
        if master_key:
            # Handle the newly injected Preclinical fields that belong to separate master keys
            if section_name == "Nonclinical Toxicology":
                remapped = {master_key: section_result}
                geno, carc, repro = {}, {}, {}
                
                # Pop out Genotoxicity fields
                for k in ["genotoxicity_in_vitro", "genotoxicity_in_vivo", "genotoxicity_conclusion"]:
                    if k in section_result: geno[k] = section_result.pop(k)
                if any(v is not None and v != "Not Found" for v in geno.values()):
                    remapped["genotoxicity"] = geno
                    
                # Pop out Carcinogenicity fields
                for k in ["carcinogenicity_studies_conducted", "carcinogenicity_results"]:
                    if k in section_result: carc[k] = section_result.pop(k)
                if any(v is not None and v != "Not Found" for v in carc.values()):
                    remapped["carcinogenicity"] = carc
                    
                # Pop out Repro Tox fields
                for k in ["reproductive_toxicity_studies", "reproductive_warnings", "developmental_toxicity_warnings"]:
                    if k in section_result: repro[k] = section_result.pop(k)
                if any(v is not None and v != "Not Found" for v in repro.values()):
                    remapped["reproductive_toxicity"] = repro
                    
            else:
                remapped = {master_key: section_result}
        else:
            # For truly unmapped sections ("Other"), surface fields flat
            # so whatever was extracted lands somewhere in the merged output
            remapped = section_result

        # Always attach semantic_relationships for graph builder
        if relationships:
            if isinstance(relationships, dict):
                rels = relationships.get("relationships", [])
            elif isinstance(relationships, list):
                rels = relationships
            else:
                rels = []
            if rels:
                remapped.setdefault("semantic_relationships", {"relationships": []})
                remapped["semantic_relationships"]["relationships"].extend(rels)

        return remapped


    def _aggregate_results(self, results: List[dict]) -> dict:
        """
        Merge results from multiple chunks.
        """
        # Create blank schema with all 8 categories
        merged = BelinoIBExtractionSchema().model_dump()

        for res in results:
            if not res: continue
            self._merge_dicts(merged, res)
            
        return merged

    def _merge_dicts(self, base: dict, new: dict):
        for k, v in new.items():
            if v is None: continue
            
            # Generic List handling (for protocol_ids, etc.)
            if isinstance(v, list) and isinstance(base.get(k), list):
                base_list = base[k]
                for item in v:
                    if item not in base_list:
                        base_list.append(item)
                base[k] = base_list
            
            # Dict recursion
            elif isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._merge_dicts(base[k], v)
                
            # Boolean logic: True > False > None
            elif isinstance(v, bool):
                if base.get(k) is not True: 
                    base[k] = v
            
            # String/Number: Update if base is empty or "Not Found"
            else:
                 base_val = base.get(k)
                 # Is the base empty or a placeholder?
                 base_is_empty = (base_val is None or str(base_val).strip() == "" or str(base_val).strip() == "Not Found")
                 # Is the new value a placeholder?
                 new_is_empty = (str(v).strip() == "" or str(v).strip() == "Not Found")
                 
                 if base_is_empty and not new_is_empty:
                     # Base is empty, new is real -> grab new
                     base[k] = v
                 elif base_is_empty and new_is_empty:
                     # Both placeholder/empty -> ensure base has "Not Found" rather than None
                     base[k] = v
                 elif not base_is_empty and not new_is_empty:
                     # Both real? In a simple merge, we keep the first one found, or we could append.
                     # But for now, first-chunk-wins for scalar fields is fine, so do nothing.
                     pass

    def _merge_query_results(self, base_data: dict, query_results: Dict[str, Any]) -> dict:
        """
        Merge Azure Query Fields results into the base extraction data.
        Query results take priority as they are more precise.
        """
        # Map query field names to schema paths
        field_mapping = {
            # Efficacy
            "overall_response_rate": ("efficacy_outcomes", "overall_response_rate_percent"),
            "complete_response_rate": ("efficacy_outcomes", "complete_response_percent"),
            "median_pfs": ("efficacy_outcomes", "median_pfs"),
            "median_os": ("efficacy_outcomes", "median_os"),
            
            # PK
            "elimination_half_life": ("pharmacokinetics", "elimination_half_life"),
            "plasma_protein_binding": ("pharmacokinetics", "plasma_protein_binding"),
            "clearance": ("pharmacokinetics", "clearance_total"),
            "volume_distribution": ("pharmacokinetics", "volume_of_distribution"),
            "metabolism_pathway": ("pharmacokinetics", "metabolism_pathway"),
            
            # Hepatic Safety
            "hepatic_exclusion_bilirubin": ("liver_safety_profile", "hepatic_exclusion_criteria"),
            "lft_monitoring": ("liver_safety_profile", "required_monitoring"),
            
            # Grade 3-4 Safety
            "grade_3_4_anemia": ("safety_adverse_events", "most_common_hematologic", "anemia_rate"),
            "grade_3_4_thrombocytopenia": ("safety_adverse_events", "most_common_hematologic", "thrombocytopenia_rate"),
            "grade_3_4_neutropenia": ("safety_adverse_events", "most_common_hematologic", "neutropenia_rate"),
        }
        
        for query_name, value in query_results.items():
            if not value or query_name not in field_mapping:
                continue
                
            path = field_mapping[query_name]
            
            # Navigate to the nested field and set value
            current = base_data
            for key in path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Set the final value (Query result overrides LLM)
            current[path[-1]] = value
            
        return base_data

