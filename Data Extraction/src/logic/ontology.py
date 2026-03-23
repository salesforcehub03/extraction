import re
from typing import Set, Dict, Optional, Tuple

class OntologyGrounder:
    """
    Acts as a 'Dictionary of Truth' for medical terms.
    Validates extracted terms against standard vocabularies (MedDRA-lite, HGNC-lite)
    to prevent hallucinations.
    """
    
    # 1. Targets (HGNC / Common Oncology Targets)
    KNOWN_TARGETS: Set[str] = {
        "HDAC", "HDAC1", "HDAC2", "HDAC3", "HDAC6", "HDAC10", "HDAC11",
        "VEGF", "EGFR", "HER2", "PD-1", "PD-L1", "CTLA-4", "CD20", "CD30",
        "ALK", "ROS1", "BRAF", "MEK", "PI3K", "AKT", "MTOR", "BCL-2",
        "JAK", "STAT", "BTK", "FLT3", "KIT", "RET", "MET", "FGFR"
    }

    # 2. Adverse Events (MedDRA - System Organ Class & Preferred Terms - LITE Version)
    KNOWN_AES: Set[str] = {
        # Blood & Lymphatic
        "anemia", "neutropenia", "thrombocytopenia", "leukopenia", "febrile neutropenia",
        "pancytopenia", "lymphopenia", "coagulopathy",
        # Gastrointestinal
        "nausea", "vomiting", "diarrhea", "constipation", "mucositis", "stomatitis",
        "abdominal pain", "dyspepsia", "gerd", "fecal incontinence",
        # General
        "fatigue", "pyrexia", "edema", "peripheral edema", "asthenia", "chills", "pain",
        "infusion site reaction", "weight decreased", "decreased appetite",
        # Metabolism
        "hypokalemia", "hyponatremia", "hypomagnesemia", "hyperglycemia", "hypocalcemia",
        "anorexia", "dehydration",
        # Nervous System
        "headache", "dizziness", "peripheral neuropathy", "dysgeusia", "insomnia",
        "paresthesia", "tremor",
        # Respiratory
        "dyspnea", "cough", "pneumonia", "upper respiratory tract infection",
        # Skin
        "rash", "pruritus", "alopecia", "dry skin", "erythema", "palmar-plantar erythrodysesthesia syndrome",
        # Vascular / Cardiac
        "hypertension", "hypotension", "tachycardia", "qt prolongation", "thromboembolism"
    }

    # 3. Biomarkers / Labs
    KNOWN_BIOMARKERS: Set[str] = {
        "alp", "alkaline phosphatase",
        "alt", "alanine aminotransferase",
        "ast", "aspartate aminotransferase",
        "tbil", "total bilirubin",
        "dbil", "direct bilirubin",
        "cre", "creatinine",
        "bun", "blood urea nitrogen",
        "anc", "absolute neutrophil count",
        "wbc", "white blood cell",
        "hgb", "hemoglobin",
        "plt", "platelets",
        "alb", "albumin",
        "ldh", "lactate dehydrogenase"
    }

    @classmethod
    def ground_term(cls, term: str, category: str) -> Tuple[Optional[str], float]:
        """
        Attempts to map a raw term to a canonical ontology term.
        Returns (Canonical Term, Confidence Score).
        """
        if not term:
            return None, 0.0
            
        normalized = term.strip().lower()
        
        # CATEGORY: ADVERSE EVENTS
        if category == "Adverse Event":
            # Exact match check
            if normalized in cls.KNOWN_AES:
                return normalized.title(), 1.0 # High confidence
            
            # Fuzzy / Substring check (Conservative)
            for known in cls.KNOWN_AES:
                if known in normalized: # e.g. "grade 3 anemia" -> "anemia"
                    return known.title(), 0.8
            
            return term, 0.3 # Low confidence (Keep raw but flag it)

        # CATEGORY: TARGETS
        elif category == "Target":
            # Targets are often acronyms, keep case usually but normalize for check
            upper_term = term.strip().upper()
            if upper_term in cls.KNOWN_TARGETS:
                return upper_term, 1.0
            
            return term, 0.4

        # CATEGORY: BIOMARKERS
        elif category == "Biomarker":
            if normalized in cls.KNOWN_BIOMARKERS:
                return normalized.upper(), 1.0
            return term, 0.5

        return term, 0.5
