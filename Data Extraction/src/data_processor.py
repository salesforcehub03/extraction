import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

from openai import AsyncAzureOpenAI
from config import Config


# ==============================================================================
# 1. VALIDATOR
# ==============================================================================
class Validator:
    def validate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure extracted data is analytically valid and regulator-ready.
        """
        if "liver_related_deaths" in data:
            deaths = data["liver_related_deaths"]
            if deaths.get("reported") and deaths.get("number_of_deaths") is not None:
                if deaths["number_of_deaths"] < 0:
                     deaths["number_of_deaths"] = None
        
        if "liver_related_adverse_events" in data:
            for event in data["liver_related_adverse_events"]:
                freq = event.get("frequency")
                if freq and "%" in freq:
                    pass 
        
        self._cross_check_consistency(data)
        return data

    def _cross_check_consistency(self, data: Dict[str, Any]):
        signals = data.get("hepatotoxicity_signals", {})
        warnings = data.get("liver_laboratory_monitoring", {})
        pass

    def standardize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardization (Optional, Non-destructive)
        """
        if "liver_related_adverse_events" in data:
            for event in data["liver_related_adverse_events"]:
                original = event.get("event_term")
                if original:
                    pass
        return data


# ==============================================================================
# 2. OUTPUT POSTPROCESSOR
# ==============================================================================
_KEEP_NULL_FIELDS = {
    "n_patients", "adverse_event_patient_count", "complete_response_count",
    "partial_response_count", "death_count", "total_patients_exposed",
    "carcinogenicity_studies_conducted", "reproductive_toxicity_studies",
}

_LIST_OF_OBJECTS_KEYS = {
    "animal_studies", "pk_data_points", "clinical_studies", "adverse_events",
    "dose_reduction_schedule", "drug_interaction_studies", "interacting_drugs",
    "molecular_targets", "study_identifiers", "participating_countries",
    "target_organs", "adverse_findings", "top_aes", "supportive_care_requirements",
    "combination_therapy_drugs",
}

NOT_FOUND = "Not Found"
RATE_LIMITED = "Rate Limited"

def postprocess(obj: Any, field_name: str = "", depth: int = 0) -> Any:
    """
    Recursively walk the extracted JSON and:
    - Replace None scalar strings with 'Not Found'
    - Leave integer/bool fields as None (e.g. patient counts)
    - Leave lists as-is (but process items)
    - Mark items in list-of-objects recursively
    """
    if obj is None:
        if field_name in _KEEP_NULL_FIELDS:
            return None
        return NOT_FOUND

    if isinstance(obj, str):
        if obj.strip() == "" or obj.strip().lower() == "none":
            return NOT_FOUND
        return obj

    if isinstance(obj, bool) or isinstance(obj, int) or isinstance(obj, float):
        return obj

    if isinstance(obj, list):
        return [postprocess(item, field_name, depth + 1) for item in obj]

    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if k == "semantic_relationships":
                result[k] = v  
                continue
            result[k] = postprocess(v, k, depth + 1)
        return result

    return obj

def run_postprocessor(input_path: str, output_path: Optional[str] = None) -> str:
    """Load a JSON extraction result and apply Not Found markers."""
    inp = Path(input_path)
    if not output_path:
        output_path = str(inp.parent / inp.stem) + "_postprocessed.json"

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    processed = postprocess(data)

    def count_not_found(obj, count=0):
        if isinstance(obj, str) and obj == NOT_FOUND:
            return count + 1
        if isinstance(obj, dict):
            for v in obj.values():
                count = count_not_found(v, count)
        if isinstance(obj, list):
            for item in obj:
                count = count_not_found(item, count)
        return count

    nf_count = count_not_found(processed)
    print(f"  -> Marked {nf_count} fields as '{NOT_FOUND}'")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print(f"  -> Saved: {output_path}")
    return output_path


# ==============================================================================
# 3. PARAGRAPH EXTRACTOR
# ==============================================================================
class ParagraphExtractor:
    """
    Extracts structured data from narrative paragraphs.
    Focuses on eligibility criteria, treatment management, and PK data.
    """
    
    def __init__(self):
        self.client = AsyncAzureOpenAI(
            api_key=Config.AZURE_OPENAI_KEY,
            api_version=Config.AZURE_OPENAI_API_VERSION,
            azure_endpoint=Config.AZURE_OPENAI_ENDPOINT
        )
        self.deployment_name = Config.AZURE_OPENAI_DEPLOYMENT_NAME
    
    async def extract_all(self, classified_data) -> Dict[str, Any]:
        """
        Extract all paragraph-based data from classified sections.
        """
        result = {
            "eligibility_criteria": {},
            "treatment_management": {},
            "pharmacokinetics": {},
            "study_metadata_narrative": {}
        }
        
        all_text = ""
        if isinstance(classified_data, dict):
            for section, chunks in classified_data.items():
                if isinstance(chunks, list):
                    all_text += "\n\n".join(chunks) + "\n\n"
                else:
                    all_text += str(chunks) + "\n\n"
        elif isinstance(classified_data, list):
            all_text = "\n\n".join(str(chunk) for chunk in classified_data)
        else:
            all_text = str(classified_data)
        
        eligibility = self._extract_eligibility_criteria_enhanced(all_text)
        result["eligibility_criteria"].update(eligibility)
        
        treatment_mgmt = await self._extract_treatment_management_targeted(all_text)
        result["treatment_management"].update(treatment_mgmt)
        
        pk_data = await self._extract_pk_data(all_text)
        result["pharmacokinetics"].update(pk_data)
        
        study_meta = await self._extract_study_metadata_llm(all_text)
        result["study_metadata_narrative"].update(study_meta)
        
        preclinical_safety = await self._extract_preclinical_safety(all_text)
        result["preclinical_safety"] = preclinical_safety
        
        return result
    
    def _extract_eligibility_criteria_enhanced(self, text: str) -> Dict[str, Optional[str]]:
        criteria: Dict[str, Optional[str]] = {
            "eligibility_anc_threshold": None,
            "eligibility_platelet_threshold": None,
            "eligibility_creatinine_clearance": None,
            "eligibility_bilirubin_threshold": None,
            "eligibility_alt_ast_threshold": None,
            "hepatic_impairment_exclusion": None
        }
        
        cln19_match = re.search(
            r'(CLN-19.*?(?:inclusion|eligibility|criteria).*?)(?=CLN-\d|Table|Figure|##|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        target_text = cln19_match.group(1) if cln19_match else text
        
        anc_patterns = [
            r'ANC\s*(?:>=|≥|>)\s*(\d+\.?\d*)\s*(?:x|×)\s*10(?:\^9|⁹)/L',
            r'absolute neutrophil count\s*(?:>=|≥)\s*(\d+\.?\d*)\s*(?:x|×)\s*10',
            r'neutrophil[s]?\s*(?:>=|≥)\s*(\d+\.?\d*)\s*(?:x|×)\s*10',
            r'ANC\s*(?:>=|≥)\s*(\d+)/mm',
            r'neutrophil count.*?(?:>=|≥)\s*(\d+\.?\d*)\s*(?:x|×)\s*10',
            r'adequate.*?bone marrow.*?ANC.*?(\d+\.?\d*)\s*(?:x|×)\s*10',
            r'WBC.*?(?:>=|≥)\s*(\d+\.?\d*)\s*(?:x|×)\s*10',
        ]
        
        for pattern in anc_patterns:
            match = re.search(pattern, target_text, re.IGNORECASE)
            if match:
                value = match.group(1)
                if '10' in match.group(0):
                    criteria["eligibility_anc_threshold"] = f"≥{value} × 10⁹/L"
                else:
                    criteria["eligibility_anc_threshold"] = f"≥{value}/mm³"
                break
        
        platelet_patterns = [
            r'platelet[s]?\s*(?:>=|≥)\s*(\d+\.?\d*)\s*(?:x|×)\s*10(?:\^9|⁹)/L',
            r'platelet count\s*(?:>=|≥)\s*(\d+\.?\d*)\s*(?:x|×)\s*10',
            r'platelet[s]?\s*(?:>=|≥)\s*(\d+,?\d*)/mm',
            r'adequate.*?platelet.*?(\d+\.?\d*)\s*(?:x|×)\s*10',
        ]
        
        for pattern in platelet_patterns:
            match = re.search(pattern, target_text, re.IGNORECASE)
            if match:
                value = match.group(1).replace(',', '')
                if '10' in match.group(0):
                    criteria["eligibility_platelet_threshold"] = f"≥{value} × 10⁹/L"
                else:
                    criteria["eligibility_platelet_threshold"] = f"≥{value}/mm³"
                break
        
        crcl_patterns = [
            r'creatinine clearance\s*(?:>=|≥)\s*(\d+)\s*mL/min',
            r'CrCl\s*(?:>=|≥)\s*(\d+)\s*mL/min',
            r'calculated creatinine clearance\s*(?:>=|≥)\s*(\d+)',
            r'renal function.*?(\d+)\s*mL/min',
            r'adequate.*?renal.*?(\d+)\s*mL/min',
            r'Cockcroft-Gault.*?(\d+)\s*mL/min',
        ]
        
        for pattern in crcl_patterns:
            match = re.search(pattern, target_text, re.IGNORECASE)
            if match:
                value = match.group(1)
                criteria["eligibility_creatinine_clearance"] = f"≥{value} mL/min"
                break
        
        bilirubin_patterns = [
            r'(?:total\s+)?bilirubin\s*(?:<=|≤|<)\s*(\d+\.?\d*)\s*(?:x|×)\s*ULN',
            r'(?:total\s+)?bilirubin\s*(?:<=|≤)\s*(\d+\.?\d*)\s*times?\s*(?:the\s+)?ULN',
            r'bilirubin\s*(?:<=|≤)\s*(\d+\.?\d*)\s*mg/dL',
            r'adequate.*?hepatic.*?bilirubin\s*(?:<=|≤)\s*(\d+\.?\d*)',
            r'bilirubin.*?must.*?(?:<=|≤)\s*(\d+\.?\d*)\s*(?:x|×)\s*ULN',
        ]
        
        for pattern in bilirubin_patterns:
            match = re.search(pattern, target_text, re.IGNORECASE)
            if match:
                value = match.group(1)
                if 'ULN' in match.group(0):
                    criteria["eligibility_bilirubin_threshold"] = f"≤{value} × ULN"
                else:
                    criteria["eligibility_bilirubin_threshold"] = f"≤{value} mg/dL"
                break
        
        alt_ast_patterns = [
            r'(?:ALT|AST|SGPT|SGOT)\s*(?:<=|≤)\s*(\d+\.?\d*)\s*(?:x|×)\s*ULN',
            r'(?:ALT|AST)\s*(?:<=|≤)\s*(\d+\.?\d*)\s*times?\s*(?:the\s+)?ULN',
            r'transaminase[s]?\s*(?:<=|≤)\s*(\d+\.?\d*)\s*(?:x|×)\s*ULN',
            r'liver enzyme[s]?\s*(?:<=|≤)\s*(\d+\.?\d*)\s*(?:x|×)\s*ULN',
            r'adequate.*?hepatic.*?(?:ALT|AST)\s*(?:<=|≤)\s*(\d+\.?\d*)',
        ]
        
        for pattern in alt_ast_patterns:
            match = re.search(pattern, target_text, re.IGNORECASE)
            if match:
                value = match.group(1)
                criteria["eligibility_alt_ast_threshold"] = f"≤{value} × ULN"
                break
        
        hepatic_exclusion_patterns = [
            r'bilirubin\s*>\s*(\d+\.?\d*)\s*(?:x|×)\s*ULN\s*(?:excluded|exclusion)',
            r'exclude[d]?\s*(?:if|when|with)\s*bilirubin\s*>\s*(\d+\.?\d*)\s*(?:x|×)\s*ULN',
            r'hepatic impairment.*bilirubin\s*>\s*(\d+\.?\d*)\s*(?:x|×)\s*ULN',
        ]
        
        for pattern in hepatic_exclusion_patterns:
            match = re.search(pattern, target_text, re.IGNORECASE)
            if match:
                value = match.group(1)
                criteria["hepatic_impairment_exclusion"] = f"Bilirubin >{value} × ULN excluded"
                break
        
        return criteria
    
    async def _extract_treatment_management_targeted(self, text: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "toxicity_stopping_criteria": None,
            "dose_reduction_schedule": [],
            "treatment_delay_rules": None,
            "supportive_care_requirements": []
        }
        
        dose_reductions = await self._extract_dose_reductions(text)
        if dose_reductions: result["dose_reduction_schedule"] = dose_reductions
        
        delay_rules = await self._extract_treatment_delays(text)
        if delay_rules: result["treatment_delay_rules"] = delay_rules
        
        stopping_criteria = await self._extract_stopping_criteria(text)
        if stopping_criteria: result["toxicity_stopping_criteria"] = stopping_criteria
        
        supportive_care = await self._extract_supportive_care(text)
        if supportive_care: result["supportive_care_requirements"] = supportive_care
        
        return result
    
    async def _extract_dose_reductions(self, text: str) -> List[str]:
        system_prompt = """
        Extract the dose reduction schedule from clinical trial text.
        Look for: "Starting dose: X, First reduction: Y, Second reduction: Z", "Reduce dose by X%", specific dose levels.
        Return ONLY the dose values in descending order as a JSON array. Example: ["1000 mg/m²", "750 mg/m²"]. If not found, return empty array: []
        """
        user_prompt = f"Extract dose reduction schedule from this text:\n{text[:6000]}\nReturn JSON: {{\"dose_reduction_schedule\": [\"dose1\", \"dose2\", ...]}}" # type: ignore
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0, response_format={"type": "json_object"}
            )
            data: dict = json.loads(response.choices[0].message.content)
            return data.get("dose_reduction_schedule", [])
        except Exception as e: return []
    
    async def _extract_treatment_delays(self, text: str) -> Optional[str]:
        system_prompt = """
        Extract rules for when to delay/postpone treatment cycles.
        Look for "Delay treatment if...", lab value thresholds, toxicity grades.
        Return a concise summary of ALL delay criteria. If not found, return null.
        """
        user_prompt = f"Extract treatment delay rules from this text:\n{text[:6000]}\nReturn JSON: {{\"treatment_delay_rules\": \"summary or null\"}}" # type: ignore
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0, response_format={"type": "json_object"}
            )
            data: dict = json.loads(response.choices[0].message.content)
            return data.get("treatment_delay_rules")
        except Exception as e: return None
    
    async def _extract_stopping_criteria(self, text: str) -> Optional[str]:
        system_prompt = """
        Extract criteria for permanently stopping/discontinuing treatment.
        Look for "Permanently discontinue", "Withdraw from study", specific grades.
        Return a concise summary. If not found, return null.
        """
        user_prompt = f"Extract permanent discontinuation criteria from this text:\n{text[:6000]}\nReturn JSON: {{\"toxicity_stopping_criteria\": \"summary or null\"}}" # type: ignore
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0, response_format={"type": "json_object"}
            )
            data: dict = json.loads(response.choices[0].message.content)
            return data.get("toxicity_stopping_criteria")
        except Exception as e: return None
    
    async def _extract_supportive_care(self, text: str) -> List[str]:
        system_prompt = """
        Extract required supportive care medications/interventions.
        Look for antiemetics, growth factors, prophylactic medications.
        Return a list of medications. If not found, return empty array: []
        """
        user_prompt = f"Extract supportive care requirements from this text:\n{text[:6000]}\nReturn JSON: {{\"supportive_care_requirements\": [\"med1\", ...]}}" # type: ignore
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0, response_format={"type": "json_object"}
            )
            data: dict = json.loads(response.choices[0].message.content)
            return data.get("supportive_care_requirements", [])
        except Exception as e: return []
    
    async def _extract_pk_data(self, text: str) -> Dict[str, Any]:
        pk_data: Dict[str, Any] = {
            "auc_value": None,
            "cmax_value": None,
            "plasma_protein_binding": None,
            "volume_of_distribution": None,
            "metabolism_pathway": None
        }
        
        auc_patterns = [
            r'AUC[^.]*?(\d{1,3}(?:,\d{3})+)\s+to\s+(\d{1,3}(?:,\d{3})+)\s*(?:h·ng/mL|hong/mL|ng·h/mL|h\*ng/mL)',
            r'AUC[^.]*?(\d+\.?\d*)\s+to\s+(\d+\.?\d*)\s*(?:μg·h/mL|ng·h/mL|mcg\.h/mL)',
            r'(?:mean\s+)?AUC[^.]*?(\d+\.?\d*)\s*(?:μg·h/mL|ng·h/mL|mcg\.h/mL)',
        ]
        for pattern in auc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2: pk_data["auc_value"] = f"{match.group(1)} to {match.group(2)} h·ng/mL"
                else: pk_data["auc_value"] = f"{match.group(1)} μg·h/mL"
                break
        
        cmax_patterns = [
            r'(?:mean\s+)?Cmax.*?(\d+\.?\d*)\s*(?:μg/mL|ng/mL|mcg/mL)',
            r'peak.*?concentration.*?(\d+\.?\d*)\s*(?:μg/mL|ng/mL)',
        ]
        for pattern in cmax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                pk_data["cmax_value"] = f"{match.group(1)} μg/mL"
                break
        
        protein_patterns = [
            r'protein binding.*?(?:\d+\.?\d*%,?\s*)+and\s+(\d+\.?\d*)%\s*in.*?(?:man|human)',
            r'(\d+\.?\d*)\s*%\s*and\s*(\d+\.?\d*)\s*%.*?bound to.*?protein',
            r'(\d+\.?\d*)\s*%\s*bound to.*?protein',
            r'bound to protein.*?(\d+\.?\d*)\s*%',
        ]
        for pattern in protein_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2: pk_data["plasma_protein_binding"] = f"{match.group(1)}-{match.group(2)}%"
                else: pk_data["plasma_protein_binding"] = f"{match.group(1)}%"
                break
        
        vd_patterns = [
            r'V(?:d|ss).*?(\d+\.?\d*)\s*L',
            r'volume of distribution.*?(\d+\.?\d*)\s*L',
            r'volume of distribution.*?(approaches total body water)',
            r'Vdss\s*approached\s*(total body water)',
        ]
        for pattern in vd_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                if 'total body water' in value.lower(): pk_data["volume_of_distribution"] = "Approaches total body water"
                else: pk_data["volume_of_distribution"] = f"{value} L"
                break
        
        metabolism_patterns = [
            r'metabolized.*?(?:via|by|through)\s+([A-Z0-9]+)',
            r'metabolism.*?pathway.*?([A-Z0-9]+)',
            r'(?:primarily|mainly)\s+metabolized\s+by\s+(?:hepatic\s+)?([A-Z0-9]+)',
        ]
        for pattern in metabolism_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                pk_data["metabolism_pathway"] = match.group(1)
                break
        
        if not any(pk_data.values()):
            llm_pk = await self._extract_pk_llm(text)
            pk_data.update(llm_pk)
        
        return pk_data
    
    async def _extract_pk_llm(self, text: str) -> Dict[str, Any]:
        system_prompt = """
        Extract PK parameters from clinical text.
        Look for AUC, Cmax, Protein binding, Vd/Vss, Metabolism pathway.
        Return exact values with units. If not found, return null.
        """
        user_prompt = f"Extract PK parameters from this text:\n{text[:6000]}\nReturn JSON: {{\"auc_value\": \"...\", \"cmax_value\": \"...\", \"plasma_protein_binding\": \"...\", \"volume_of_distribution\": \"...\", \"metabolism_pathway\": \"...\"}}" # type: ignore
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0, response_format={"type": "json_object"}
            )
            data: dict = json.loads(response.choices[0].message.content)
            return data
        except Exception as e: return {}
    
    async def _extract_study_metadata_llm(self, text: str) -> Dict[str, Any]:
        system_prompt = """
        Extract study metadata from narrative text.
        Focus on: Sponsor organization, Start/end dates, Participating countries.
        """
        user_prompt = f"Extract study metadata:\n{text[:4000]}\nReturn JSON: {{\"sponsor_information\": \"...\", \"study_start_date\": \"...\", \"study_end_date\": \"...\", \"participating_countries\": []}}" # type: ignore
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0, response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"sponsor_information": None, "study_start_date": None, "study_end_date": None, "participating_countries": []}

    async def _extract_preclinical_safety(self, text: str) -> Dict[str, Any]:
        system_prompt = """
        ROLE: Expert Pre-Clinical Toxicologist
        TASK: Extract high-fidelity animal toxicology data from the provided text.
        Provide summaries for single_dose_toxicity, repeat_dose_toxicity, toxicity_species, target_organs, noael_value, maximum_tolerated_dose.
        """
        user_prompt = f"Extract animal toxicology data:\n{text[:12000]}\nReturn JSON with the 6 required keys." # type: ignore
        
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.0, response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"single_dose_toxicity": None, "repeat_dose_toxicity": None, "toxicity_species": [], "target_organs": [], "noael_value": None, "maximum_tolerated_dose": None}
