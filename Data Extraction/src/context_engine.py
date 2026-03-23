import os
import json
import re
import asyncio
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from openai import AsyncAzureOpenAI
from sklearn.metrics.pairwise import cosine_similarity

from config import Config
from .extraction_scratchpad import ExtractionScratchpad

# ==============================================================================
# 1. SEMANTIC CHUNKER
# ==============================================================================
class SemanticChunker:
    """
    Splits text into semantic chunks based on embedding similarity.
    Better than fixed-size chunking for preserving context.
    """

    def __init__(self):
        Config.validate()
        self.client = AsyncAzureOpenAI(
            api_key=Config.AZURE_OPENAI_KEY,
            api_version="2024-02-01", 
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
        )
        self.embedding_model = "text-embedding-3-small" 
        self.similarity_threshold = 0.75 
        self.min_chunk_size = 500  
        self.target_chunk_size = 2000 

    async def create_semantic_chunks(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        raw_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not raw_paragraphs: return []

        try:
            embeddings = await self._get_embeddings_batch(raw_paragraphs)
        except Exception as e:
            print(f"Embedding failed: {e}. Fallback to simple chunking.")
            return self._simple_chunking(text, metadata)

        chunks = []
        current_chunk_text = raw_paragraphs[0]
        current_chunk_embedding = embeddings[0]
        current_chunk_indices = [0]
        
        for i in range(1, len(raw_paragraphs)):
            para_text = raw_paragraphs[i]
            para_embedding = embeddings[i]
            sim = cosine_similarity([current_chunk_embedding], [para_embedding])[0][0]
            
            is_dissimilar = sim < self.similarity_threshold
            is_too_big = len(current_chunk_text) > self.target_chunk_size
            
            if (is_dissimilar and len(current_chunk_text) > self.min_chunk_size) or is_too_big:
                chunks.append({
                    "content": current_chunk_text,
                    "metadata": {
                        **(metadata or {}),
                        "chunk_index": len(chunks),
                        "source_paragraphs": current_chunk_indices,
                        "semantic_size": len(current_chunk_text)
                    },
                    "embedding": current_chunk_embedding 
                })
                current_chunk_text = para_text
                current_chunk_embedding = para_embedding
                current_chunk_indices = [i]
            else:
                current_chunk_text += "\n\n" + para_text
                current_chunk_embedding = np.mean([current_chunk_embedding, para_embedding], axis=0)
                current_chunk_indices.append(i)
        
        if current_chunk_text:
             chunks.append({
                "content": current_chunk_text,
                "metadata": {
                    **(metadata or {}),
                    "chunk_index": len(chunks),
                    "source_paragraphs": current_chunk_indices,
                    "semantic_size": len(current_chunk_text)
                },
                "embedding": current_chunk_embedding
            })
        return chunks

    async def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        all_embeddings = []
        batch_size = 5 
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                response = await self.client.embeddings.create(input=batch, model=self.embedding_model)
                all_embeddings.extend([data.embedding for data in response.data])
                await asyncio.sleep(0.5) 
            except Exception as e:
                print(f"Error embedding batch {i}: {e}")
                await asyncio.sleep(2)
                try:
                    response = await self.client.embeddings.create(input=batch, model=self.embedding_model)
                    all_embeddings.extend([data.embedding for data in response.data])
                except Exception as retry_e:
                     print(f"Retry failed for batch {i}: {retry_e}")
                     raise retry_e
        return all_embeddings

    def _simple_chunking(self, text: str, metadata: Dict) -> List[Dict]:
        chunks = []
        start = 0
        chunk_size = self.target_chunk_size
        overlap = 200
        while start < len(text):
            end = start + chunk_size
            chunks.append({
                "content": text[start:end],
                "metadata": {**(metadata or {}), "method": "fallback_simple"}
            })
            start += (chunk_size - overlap)
        return chunks

# ==============================================================================
# 2. CONTEXT CLASSIFIER
# ==============================================================================
class ContextClassifier:
    """Classifies semantic chunks into clinical sections."""
    ALLOWED_SECTIONS = [
        "Drug Overview", "Mechanism of Action", "Nonclinical Toxicology", "Pharmacokinetics",
        "Clinical Study Design", "Efficacy Outcomes", "Safety and Adverse Events",
        "Hepatotoxicity", "Special Populations – Hepatic", "Dose Modifications",
        "Dosing Regimen", "Cardiac Safety", "Deaths and Serious Adverse Events",
        "Monitoring and Warnings", "Population Characteristics", "Eligibility Criteria", 
        "Drug Interactions", "Formulation and Stability", "Genotoxicity", 
        "Carcinogenicity", "Reproductive Toxicity", "Contraindications", "Other"
    ]

    _LLM_ROUTER_PROMPT = f"""You are a clinical document section classifier.
Given a text chunk from a pharmaceutical Investigator Brochure (IB), classify it into EXACTLY ONE of these section types:

{chr(10).join(f'  - {s}' for s in ALLOWED_SECTIONS)}

RULES:
- Return ONLY the section name as a plain string, nothing else.
- Use "Other" ONLY if the content clearly does not fit any category.
- Prefer specific categories over "Other".
- For liver-related AE data, prefer "Hepatotoxicity" over "Safety and Adverse Events".
- For death data, prefer "Deaths and Serious Adverse Events".
- For QTc/cardiac data, prefer "Cardiac Safety".
"""

    def __init__(self):
        Config.validate()
        self._llm_client: Optional[AsyncAzureOpenAI] = None
        self._llm_deployment: Optional[str] = None

    def _get_llm_client(self) -> AsyncAzureOpenAI:
        if self._llm_client is None:
            self._llm_client = AsyncAzureOpenAI(
                azure_endpoint=Config.AZURE_OPENAI_ENDPOINT,
                api_key=Config.AZURE_OPENAI_KEY,
                api_version=Config.AZURE_OPENAI_API_VERSION
            )
            self._llm_deployment = getattr(Config, "AZURE_OPENAI_MINI_DEPLOYMENT", Config.AZURE_OPENAI_DEPLOYMENT_NAME)
        return self._llm_client

    async def classify_blocks(self, markdown_text: str) -> List[Dict[str, Any]]:
        from .schema.context import SchemaContextInjector
        chunker = SemanticChunker()
        print("   -> Creating Semantic Chunks...")
        chunks = await chunker.create_semantic_chunks(markdown_text)

        categorized_chunks = []
        other_chunk_indices = []

        for idx, chunk in enumerate(chunks):
            text_content = chunk["content"]
            section_name = "Other"
            match = re.search(r'^(#{1,6})\s+(.*)', text_content, re.MULTILINE)
            if match:
                section_name = self._classify_header_title(match.group(2).strip())
            else:
                section_name = self._classify_content_keywords(text_content)

            schema_context = SchemaContextInjector.get_context_for_section(section_name)
            metadata = chunk.get("metadata", {})
            metadata["chunk_index"] = idx

            categorized_chunks.append({
                "section": section_name,
                "content": text_content,
                "schema_context": schema_context,
                "metadata": metadata,
            })
            if section_name == "Other":
                other_chunk_indices.append(idx)

        if other_chunk_indices:
            print(f"   -> LLM Router: classifying {len(other_chunk_indices)} ambiguous 'Other' chunks...")
            llm_tasks = [self._classify_with_llm(categorized_chunks[i]["content"], chunk_idx=i) for i in other_chunk_indices]
            llm_results = await asyncio.gather(*llm_tasks, return_exceptions=True)

            reclassified = 0
            for list_pos, chunk_idx in enumerate(other_chunk_indices):
                result = llm_results[list_pos]
                if isinstance(result, str) and result in self.ALLOWED_SECTIONS and result != "Other":
                    categorized_chunks[chunk_idx]["section"] = result
                    categorized_chunks[chunk_idx]["schema_context"] = SchemaContextInjector.get_context_for_section(result)
                    reclassified += 1
            print(f"   -> LLM Router: reclassified {reclassified}/{len(other_chunk_indices)} chunks")

        print(f"   -> Created {len(categorized_chunks)} semantically enriched chunks.")
        return categorized_chunks

    async def _classify_with_llm(self, chunk_text: str, chunk_idx: int = -1) -> str:
        try:
            client = self._get_llm_client()
            snippet = chunk_text[:600].strip()
            response = await client.chat.completions.create(
                model=self._llm_deployment,
                messages=[
                    {"role": "system", "content": self._LLM_ROUTER_PROMPT},
                    {"role": "user", "content": f"Classify this IB chunk:\n\n{snippet}"}
                ],
                temperature=0.0, max_tokens=20
            )
            result = response.choices[0].message.content.strip()
            if result in self.ALLOWED_SECTIONS: return result
            
            result_lower = result.lower()
            for section in self.ALLOWED_SECTIONS:
                if section.lower() in result_lower or result_lower in section.lower():
                    return section
            return "Other"
        except Exception as e:
            print(f"   -> LLM Router error (chunk {chunk_idx}): {e}")
            return "Other"

    def _classify_header_title(self, title: str) -> str:
        t = title.lower()
        rules = {
            "hepatotoxicity": "Hepatotoxicity", "liver injury": "Hepatotoxicity", "dili": "Hepatotoxicity", "liver": "Hepatotoxicity",
            "cardiac": "Cardiac Safety", "qtc": "Cardiac Safety", "ecg": "Cardiac Safety",
            "deaths": "Deaths and Serious Adverse Events", "mortality": "Deaths and Serious Adverse Events", "fatal": "Deaths and Serious Adverse Events", "serious adverse": "Deaths and Serious Adverse Events",
            "warning": "Monitoring and Warnings", "precaution": "Monitoring and Warnings",
            "adverse event": "Safety and Adverse Events", "adverse reaction": "Safety and Adverse Events", "safety": "Safety and Adverse Events", "tolerability": "Safety and Adverse Events",
            "efficacy": "Efficacy Outcomes", "response rate": "Efficacy Outcomes", "clinical response": "Efficacy Outcomes", "clinical outcome": "Efficacy Outcomes", "progression": "Efficacy Outcomes", "survival": "Efficacy Outcomes", "overall response": "Efficacy Outcomes",
            "pharmacokinetics": "Pharmacokinetics", "pk parameters": "Pharmacokinetics", "pharmacokinetic": "Pharmacokinetics", "absorption": "Pharmacokinetics", "distribution": "Pharmacokinetics", "elimination": "Pharmacokinetics", "metabolism": "Pharmacokinetics", "excretion": "Pharmacokinetics",
            "mechanism of action": "Mechanism of Action", "mechanism": "Mechanism of Action", "pharmacodynamics": "Mechanism of Action",
            "nonclinical": "Nonclinical Toxicology", "non-clinical": "Nonclinical Toxicology", "preclinical": "Nonclinical Toxicology", "animal": "Nonclinical Toxicology", "animal study": "Nonclinical Toxicology", "in vivo": "Nonclinical Toxicology", "in vitro": "Nonclinical Toxicology", "toxicology": "Nonclinical Toxicology", "repeat dose": "Nonclinical Toxicology", "single dose toxicity": "Nonclinical Toxicology",
            "genotoxicity": "Genotoxicity", "mutagenicity": "Genotoxicity", "carcinogenicity": "Carcinogenicity", "reproductive": "Reproductive Toxicity", "teratogen": "Reproductive Toxicity", "embryo": "Reproductive Toxicity",
            "dosing regimen": "Dosing Regimen", "dose regimen": "Dosing Regimen", "administration": "Dosing Regimen", "recommended dose": "Dosing Regimen", "dose escalation": "Dosing Regimen", "dose level": "Dosing Regimen",
            "dose modification": "Dose Modifications", "dose reduction": "Dose Modifications", "dose interruption": "Dose Modifications",
            "study design": "Clinical Study Design", "study overview": "Clinical Study Design", "clinical study": "Clinical Study Design", "clinical trial": "Clinical Study Design",
            "eligibility": "Eligibility Criteria", "inclusion criteria": "Eligibility Criteria", "exclusion criteria": "Eligibility Criteria",
            "population characteristic": "Population Characteristics", "baseline characteristic": "Population Characteristics", "demographic": "Population Characteristics", "patient characteristic": "Population Characteristics",
            "hepatic impairment": "Special Populations – Hepatic", "renal impairment": "Special Populations", "special population": "Special Populations", "pediatric": "Special Populations", "geriatric": "Special Populations",
            "drug overview": "Drug Overview", "overview": "Drug Overview", "background": "Drug Overview", "introduction": "Drug Overview",
            "drug interaction": "Drug Interactions", "drug-drug interaction": "Drug Interactions", "cyp": "Drug Interactions",
            "formulation": "Formulation and Stability", "stability": "Formulation and Stability", "pharmaceutical": "Formulation and Stability", "reconstitution": "Formulation and Stability",
            "contraindication": "Contraindications",
        }
        for key, sec in rules.items():
            if key in t: return sec
        return "Other"

    def _classify_content_keywords(self, text: str) -> str:
        text_lower = text.lower()[:800]
        if "hepatotoxicity" in text_lower or "hepatic failure" in text_lower or "liver failure" in text_lower: return "Hepatotoxicity"
        if "qtc" in text_lower or "qt prolongation" in text_lower or "cardiac arrhythmia" in text_lower: return "Cardiac Safety"
        if "death" in text_lower and ("patient" in text_lower or "fatal" in text_lower): return "Deaths and Serious Adverse Events"
        if "dose reduction" in text_lower or "dose modification" in text_lower or "dose interrupt" in text_lower: return "Dose Modifications"
        if any(k in text_lower for k in ["auc", "cmax", "half-life", "clearance", "bioavailability", "elimination"]): return "Pharmacokinetics"
        if any(k in text_lower for k in ["hdac", "histone deacetylase", "tubulin", "mechanism of action"]): return "Mechanism of Action"
        if any(k in text_lower for k in ["rat ", "mouse ", "mice ", "dog ", "monkey ", "in vivo", "in vitro", "animal study", "repeat dose", "single dose toxicit"]): return "Nonclinical Toxicology"
        if "genotoxic" in text_lower or "mutagenic" in text_lower or "ames test" in text_lower: return "Genotoxicity"
        if "carcinogen" in text_lower: return "Carcinogenicity"
        if "reproductive" in text_lower or "teratogen" in text_lower or "embryo" in text_lower: return "Reproductive Toxicity"
        if any(k in text_lower for k in ["inclusion criteria", "exclusion criteria", "eligibility"]): return "Eligibility Criteria"
        if any(k in text_lower for k in ["age ", "male", "female", "ecog", "baseline", "median age"]): return "Population Characteristics"
        if any(k in text_lower for k in ["lyophilized", "reconstitut", "excipient", "shelf life", "storage condition"]): return "Formulation and Stability"
        if any(k in text_lower for k in ["cyp3a", "cyp2c", "ugt1a1", "warfarin", "drug interaction"]): return "Drug Interactions"
        if any(k in text_lower for k in ["mg/m2", "mg/m²", "infusion", "intravenous", "days 1-5", "21-day cycle"]): return "Dosing Regimen"
        if any(k in text_lower for k in ["adverse", "teae", "side effect", "toxicity"]): return "Safety and Adverse Events"
        if any(k in text_lower for k in ["orr", "response rate", "complete response", "partial response", "progression-free"]): return "Efficacy Outcomes"
        return "Other"


# ==============================================================================
# 3. CONTEXT STORE
# ==============================================================================
class ContextStore:
    """Lightweight in-memory index over classified chunks for Just-In-Time retrieval."""
    
    _TABLE_REF_PATTERN = re.compile(r'table\s*(\d+[\-\.]\d+|\d+)', re.IGNORECASE)
    _SECTION_REF_PATTERN = re.compile(r'section\s*(\d+[\.\d]+)', re.IGNORECASE)
    _FIGURE_REF_PATTERN = re.compile(r'figure\s*(\d+[\-\.]\d+|\d+)', re.IGNORECASE)

    def __init__(self, classified_chunks: List[Dict[str, Any]]):
        self._chunks = classified_chunks
        self._section_index: Dict[str, List[int]] = {}   
        self._reference_index: Dict[str, int] = {}       
        self._build_indexes()

    def _build_indexes(self):
        for idx, chunk in enumerate(self._chunks):
            section = chunk.get("section", "Other")
            if section not in self._section_index:
                self._section_index[section] = []
            self._section_index[section].append(idx)
            self._index_references(chunk.get("content", ""), idx)

    def _index_references(self, content: str, chunk_idx: int):
        header_match = re.findall(r'^#{1,6}\s+(?:Table\s+([\d\.\-]+)|Section\s+([\d\.]+)|\s*([\d\.]+)\s+)',
                                   content, re.MULTILINE | re.IGNORECASE)
        for match in header_match:
            table_num, section_num, general_num = match
            if table_num:
                key = f"table {table_num}".lower()
                if key not in self._reference_index:
                    self._reference_index[key] = chunk_idx
            if section_num:
                key = f"section {section_num}".lower()
                if key not in self._reference_index:
                    self._reference_index[key] = chunk_idx

    def search_by_section(self, section_type: str) -> List[Dict[str, Any]]:
        indices = self._section_index.get(section_type, [])
        return [self._chunks[i] for i in indices]

    def search_by_keyword(self, keyword: str, max_results: int = 5) -> List[Dict[str, Any]]:
        keyword_lower = keyword.lower()
        scored: List[tuple[int, int]] = []
        for idx, chunk in enumerate(self._chunks):
            count = chunk.get("content", "").lower().count(keyword_lower)
            if count > 0: scored.append((idx, count))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [self._chunks[i] for i, _ in scored[:max_results]]

    def get_adjacent_chunks(self, chunk_index: int, window: int = 1) -> List[Dict[str, Any]]:
        results = []
        for offset in range(-window, window + 1):
            if offset == 0: continue
            idx = chunk_index + offset
            if 0 <= idx < len(self._chunks): results.append(self._chunks[idx])
        return results

    def retrieve_by_reference(self, reference_string: str) -> Optional[Dict[str, Any]]:
        key = reference_string.strip().lower()
        if key in self._reference_index: return self._chunks[self._reference_index[key]]
        key_nospace = re.sub(r'\s+', '', key)
        for ref_key, idx in self._reference_index.items():
            if re.sub(r'\s+', '', ref_key) == key_nospace: return self._chunks[idx]
        results = self.search_by_keyword(reference_string, max_results=1)
        return results[0] if results else None

    def get_all_sections(self) -> List[str]:
        return list(self._section_index.keys())

    def get_context_summary(self) -> str:
        lines = [f"Document Index ({len(self._chunks)} chunks, {len(self._section_index)} sections):"]
        for section, indices in sorted(self._section_index.items(), key=lambda x: x[1][0]):
            idx_range = f"idx {min(indices)}-{max(indices)}" if len(indices) > 1 else f"idx {indices[0]}"
            lines.append(f"  - {section}: {len(indices)} chunk(s) ({idx_range})")
        if self._reference_index:
            lines.append(f"\nResolved References ({len(self._reference_index)}):")
            for ref, idx in sorted(self._reference_index.items()):
                lines.append(f"  - '{ref}' → chunk {idx}")
        return "\n".join(lines)

    def get_chunk_by_index(self, idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= idx < len(self._chunks): return self._chunks[idx]
        return None

    def __len__(self) -> int:
        return len(self._chunks)


# ==============================================================================
# 4. CONTEXT COMPACTOR
# ==============================================================================
_COMPACTION_PROMPT = """You are a precise clinical data summarizer.

Your task is to produce a DENSE, HIGH-FIDELITY summary of a completed IB extraction.
This summary will be used as <document_prior_context> for a subsequent comparison extraction.

INSTRUCTIONS:
1. PRESERVE: All confirmed numeric values (ORR, PFS, OS, t½, AUC, protein binding, NOAEL)
2. PRESERVE: All confirmed safety signals (hepatotoxicity, QTc findings, key AEs with rates)
3. PRESERVE: Study IDs, groups, and pivotal study designation
4. PRESERVE: Mechanism of action, metabolism pathway, molecular targets
5. PRESERVE: Key eligibility thresholds (ANC, platelets, CrCl, bilirubin)
6. PRESERVE: Dose reduction schedule and critical stopping criteria
7. DISCARD: Duplicate or redundant tool outputs
8. DISCARD: Null/empty field lists
9. DISCARD: Verbose narratives (replace with ≤15-word summaries)
10. DISCARD: Superseded values (if a field was overridden, keep final value only)

OUTPUT FORMAT:
Return a JSON object with these keys:
{
  "document_summary": "1-sentence summary of the document",
  "drug": "name and class",
  "pivotal_study": "study ID and key design",
  "efficacy_facts": {"ORR": "X%", "CR": "X%", "PR": "X%", "PFS": "X mo", "OS": "X mo", "DOR": "X mo"},
  "safety_facts": {"top_aes": [...], "grade_3_4_aes": [...], "hepatotoxicity": "...", "qtc": "..."},
  "pk_facts": {"t_half": "...", "protein_binding": "...", "metabolism": "...", "auc": "..."},
  "dose_facts": {"dose": "...", "schedule": "...", "reductions": [...]},
  "eligibility_thresholds": {"anc": "...", "platelets": "...", "bilirubin": "...", "alt_ast": "..."},
  "key_relationships": ["Belinostat INHIBITS HDAC1", "Belinostat METABOLIZED_BY UGT1A1", ...],
  "source_document": "document identifier",
  "extraction_version": "pipeline version"
}
"""

class ContextCompactor:
    """Produces a dense, structured summary of a completed extraction."""
    def __init__(self, client: AsyncAzureOpenAI, deployment_name: str):
        self.client = client
        self.deployment_name = getattr(Config, "AZURE_OPENAI_MINI_DEPLOYMENT", deployment_name)

    async def compact(self, scratchpad: ExtractionScratchpad, extracted_data: Dict[str, Any], source_document: str = "Unknown IB", pipeline_version: str = "2.0") -> Dict[str, Any]:
        facts = scratchpad.get_established_facts()
        confirmed = scratchpad.get_confirmed_values()
        
        digest = {
            "established_facts": facts,
            "confirmed_values": confirmed,
            "top_adverse_events": scratchpad._state.get("running_ae_list", [])[:20],
            "sections_processed": scratchpad._state.get("sections_processed", []),
            "efficacy_outcomes": extracted_data.get("efficacy_outcomes", {}),
            "pharmacokinetics": {k: v for k, v in extracted_data.get("pharmacokinetics", {}).items() if v and k in ("auc_value", "cmax_value", "elimination_half_life", "plasma_protein_binding", "clearance_total", "metabolism_pathway", "pk_species")},
            "eligibility_criteria": extracted_data.get("eligibility_criteria", {}),
            "treatment_management": {k: v for k, v in extracted_data.get("treatment_management", {}).items() if v and k in ("dose_reduction_schedule", "toxicity_stopping_criteria", "treatment_delay_rules")},
            "mechanism_of_action": extracted_data.get("mechanism_of_action", {}),
            "source_document": source_document,
        }

        user_message = f"Please compact the following IB extraction into a dense summary:\n\n<extraction_digest>\n{json.dumps(digest, indent=2, default=str)[:8000]}\n</extraction_digest>\n\nDocument: {source_document}"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": _COMPACTION_PROMPT}, {"role": "user", "content": user_message}],
                response_format={"type": "json_object"},
                temperature=0.0, max_tokens=1500
            )
            compacted = json.loads(response.choices[0].message.content)
            compacted["source_document"] = source_document
            compacted["extraction_version"] = pipeline_version
            return compacted
        except Exception as e:
            print(f"[ContextCompactor] Compaction failed: {e}. Returning scratchpad facts only.")
            return {"document_summary": f"Extraction from {source_document}", "drug": f"{facts.get('drug_name')} ({facts.get('drug_class')})", "pivotal_study": facts.get("pivotal_study"), "efficacy_facts": confirmed, "source_document": source_document, "extraction_version": pipeline_version, "compaction_fallback": True}

    def save(self, compacted: Dict[str, Any], output_path: str):
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(compacted, f, indent=2, ensure_ascii=True)
            print(f"[ContextCompactor] Saved compacted context -> {output_path}")
        except Exception as e: print(f"[ContextCompactor] Warning: could not save to {output_path}: {e}")

    @staticmethod
    def load(input_path: str) -> Optional[str]:
        if not os.path.exists(input_path): return None
        try:
            with open(input_path, "r", encoding="utf-8") as f: data = json.load(f)
            source = data.get("source_document", "previous IB version")
            lines = [f"[PRIOR DOCUMENT: {source}]"]
            if data.get("drug"): lines.append(f"Drug: {data['drug']}")
            if data.get("pivotal_study"): lines.append(f"Pivotal study: {data['pivotal_study']}")
            if data.get("efficacy_facts"): lines.append(f"Efficacy: ORR={data['efficacy_facts'].get('ORR','?')}, PFS={data['efficacy_facts'].get('PFS','?')}, OS={data['efficacy_facts'].get('OS','?')}")
            if data.get("pk_facts"): lines.append(f"PK: t½={data['pk_facts'].get('t_half','?')}, Protein binding={data['pk_facts'].get('protein_binding','?')}")
            if data.get("key_relationships"): lines.append("Key relationships: " + "; ".join(data["key_relationships"][:5]))
            return "\n".join(lines)
        except Exception as e:
            print(f"[ContextCompactor] Warning: could not load from {input_path}: {e}")
            return None
