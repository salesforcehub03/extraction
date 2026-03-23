from typing import Dict, Any, List
from src.enhanced_schemas import (
    StudyMetadata, PopulationCharacteristics, DosingAdministration, 
    SafetyData, EfficacyOutcomes, Pharmacokinetics, 
    EligibilityCriteria, TreatmentManagement, 
    MechanismOfAction, PreclinicalToxicology, Genotoxicity, 
    Carcinogenicity, ReproductiveToxicity, DrugInteractions, 
    Contraindications, SpecialPopulations, FormulationStability,
    RelationshipExtraction
)

class SchemaContextInjector:
    """
    Dynamically injects schema definitions and extraction rules based on the context.
    This acts as a 'Reranker' for system prompts - only showing relevant rules to the LLM.
    """
    
    # Map section keywords to schema classes
    SECTION_SCHEMA_MAP = {
        "metadata": [StudyMetadata],
        "population": [PopulationCharacteristics],
        "dosing": [DosingAdministration, TreatmentManagement],
        "safety": [SafetyData, Contraindications, DrugInteractions],
        "adverse": [SafetyData],
        "efficacy": [EfficacyOutcomes],
        "response": [EfficacyOutcomes],
        "pharmacokinetics": [Pharmacokinetics],
        "pk": [Pharmacokinetics],
        "eligibility": [EligibilityCriteria],
        "inclusion": [EligibilityCriteria],
        "exclusion": [EligibilityCriteria],
        "mechanism": [MechanismOfAction],
        "toxicology": [PreclinicalToxicology, Genotoxicity, Carcinogenicity, ReproductiveToxicity],
        "pre-clinical": [PreclinicalToxicology],
        "animal": [PreclinicalToxicology],
        "special": [SpecialPopulations],
        "formulation": [FormulationStability]
    }

    @staticmethod
    def get_context_for_section(section_name: str) -> str:
        """
        Returns a targeted system prompt tailored to the specific section.
        """
        section_lower = section_name.lower()
        active_schemas = []
        
        # 1. Identify relevant schemas
        for keyword, mappings in SchemaContextInjector.SECTION_SCHEMA_MAP.items():
            if keyword in section_lower:
                active_schemas.extend(mappings)
                
        # Deduplicate
        active_schemas = list(set(active_schemas))
        
        # If no specific schema found, fallback to broad extraction (Study Metadata + Safety usually safe bets)
        if not active_schemas:
             return "No specific schema context found. Extract general clinical data if present."

        # 2. Generate Prompt Context
        context_str = "Based on the section content, focus EXTRACTION on these schemas:\n"
        for schema_cls in active_schemas:
            context_str += f"- **{schema_cls.__name__}**:\n"
            # Get the docstring or description from the Pydantic model
            if schema_cls.__doc__:
                context_str += f"  {schema_cls.__doc__.strip()}\n"
            
            # List key fields (simplified reflection)
            fields = schema_cls.model_fields
            context_str += f"  Fields: {', '.join(fields.keys())}\n"
            
        return context_str

    @staticmethod
    def get_global_definitions() -> str:
        """
        Returns definitions that apply everywhere (like Study Metadata or Semantic Relationships).
        """
        return """
        GLOBAL EXTRACTION RULES:
        1. Always extract Study Metadata if found (Protocol IDs, Phase).
        2. Always look for Semantic Relationships (Cause -> Effect, Drug -> Target).
        """
