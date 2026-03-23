"""
Enhanced Pydantic schemas for comprehensive Belino-IB data extraction.
Covers all 60+ required fields across 8 categories.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Category 1: Study Metadata (9 fields)
# ============================================================================

class StudyMetadata(BaseModel):
    """Study-level metadata and identifiers"""
    study_identifiers: List[str] = Field(
        default_factory=list,
        description="List all study IDs, e.g., CLN-19, SPI-BEL-103, TT20"
    )
    study_phase: Optional[str] = Field(
        None,
        description="Clinical trial phase, e.g., 'Phase 2', 'Phase 1/2'"
    )
    study_design: Optional[str] = Field(
        None,
        description="Study design description, e.g., 'Open-label, single-arm'"
    )
    sponsor_information: Optional[str] = Field(
        None,
        description="Sponsor name/organization, e.g., 'Spectrum Pharmaceuticals'"
    )
    study_status: Optional[str] = Field(
        None,
        description="Current status, e.g., 'Completed', 'Ongoing'"
    )
    study_start_date: Optional[str] = Field(
        None,
        description="Study start date, format: DD-MMM-YYYY, e.g., '04-May-2009'"
    )
    study_end_date: Optional[str] = Field(
        None,
        description="Study end date, format: DD-MMM-YYYY, e.g., '27-Oct-2014'"
    )
    participating_countries: List[str] = Field(
        default_factory=list,
        description="Countries where study conducted, e.g., ['US', 'UK', 'Germany']"
    )
    study_group_classification: Optional[str] = Field(
        None,
        description="Pooled analysis group, e.g., 'Group 1', 'Pivotal monotherapy'"
    )


# ============================================================================
# Category 2: Population Characteristics (9 fields)
# ============================================================================

class PopulationCharacteristics(BaseModel):
    """Patient population demographics and characteristics"""
    sample_size_n: Optional[int] = Field(
        None,
        description="Total number of patients enrolled/treated"
    )
    disease_indication: Optional[str] = Field(
        None,
        description="Primary disease/indication, e.g., 'Peripheral T-Cell Lymphoma'"
    )
    disease_subtype: Optional[str] = Field(
        None,
        description="Specific disease subtype, e.g., 'PTCL-NOS', 'AITL'"
    )
    population_treatment_status: Optional[str] = Field(
        None,
        description="Prior treatment status, e.g., 'Relapsed or refractory', 'Treatment-naïve'"
    )
    population_category: Optional[str] = Field(
        None,
        description="Tumor type category, e.g., 'Hematologic malignancy', 'Solid tumor'"
    )
    median_age: Optional[str] = Field(
        None,
        description="Median age of patients, e.g., '63.0 years'"
    )
    age_range: Optional[str] = Field(
        None,
        description="Age range of patients, e.g., '29-81'"
    )
    gender_distribution: Optional[Dict[str, str]] = Field(
        None,
        description="Male/Female percentages, e.g., {'male': '53.5%', 'female': '46.5%'}"
    )
    ecog_performance_status: Optional[str] = Field(
        None,
        description="ECOG 0-1 percentage, e.g., '78.3%'"
    )


# ============================================================================
# Category 3: Dosing & Administration (13 fields)
# ============================================================================

class DosingAdministration(BaseModel):
    """Dosing regimen and administration details"""
    route_of_administration: Optional[str] = Field(
        None,
        description="Route, e.g., 'IV', 'Oral', 'PO'"
    )
    dose_level: Optional[str] = Field(
        None,
        description="Dose amount, e.g., '1000'"
    )
    dose_unit: Optional[str] = Field(
        None,
        description="Unit of dose, e.g., 'mg/m²', 'mg'"
    )
    dosing_schedule: Optional[str] = Field(
        None,
        description="When doses are given, e.g., 'Days 1-5'"
    )
    cycle_length: Optional[str] = Field(
        None,
        description="Length of treatment cycle, e.g., '21 days'"
    )
    infusion_duration: Optional[str] = Field(
        None,
        description="Duration of infusion, e.g., '30 minutes'"
    )
    combination_therapy_drugs: List[str] = Field(
        default_factory=list,
        description="Other drugs in combination, e.g., ['carboplatin', 'paclitaxel']"
    )
    dose_escalation_method: Optional[str] = Field(
        None,
        description="Method used for dose escalation, e.g., '3+3 design'"
    )
    dose_modification_rules: Optional[str] = Field(
        None,
        description="Rules for dose adjustments, e.g., 'Reduce to 750 mg/m² for Grade 3 toxicity'"
    )
    treatment_discontinuation_rules: Optional[str] = Field(
        None,
        description="When to stop treatment, e.g., 'Discontinue for Grade 4 hepatotoxicity'"
    )
    treatment_exposure_duration: Optional[Dict[str, str]] = Field(
        None,
        description="Duration of treatment exposure, e.g., {'median': '4.2 months', 'range': '0.1-28.3'}"
    )
    number_of_treatment_cycles: Optional[Dict[str, str]] = Field(
        None,
        description="Number of cycles received, e.g., {'median': '2', 'range': '1-16'}"
    )
    total_patients_exposed: Optional[int] = Field(
        None,
        description="Total patients who received drug"
    )


# ============================================================================
# Category 4: Safety & Adverse Events (12 fields + list)
# ============================================================================

class AdverseEventDetail(BaseModel):
    """Individual adverse event with counts and percentages"""
    adverse_event_preferred_term: str = Field(
        ...,
        description="AE name (MedDRA term), e.g., 'Thrombocytopenia', 'Nausea'"
    )
    adverse_event_patient_count: Optional[int] = Field(
        None,
        description="Number of patients with this AE"
    )
    adverse_event_percentage: Optional[str] = Field(
        None,
        description="Percentage of patients with this AE, e.g., '10.9%'"
    )
    treatment_emergent_ae_flag: bool = Field(
        False,
        description="Is this a treatment-emergent AE (TEAE)?"
    )
    serious_adverse_event_flag: bool = Field(
        False,
        description="Is this a serious AE (SAE)?"
    )
    grade_3_4_ae_frequency: Optional[Dict[str, Any]] = Field(
        None,
        description="Grade 3/4 occurrence, e.g., {'count': 9, 'percentage': '7.0%'}"
    )
    ae_related_discontinuation_count: Optional[int] = Field(
        None,
        description="Patients who discontinued due to this AE"
    )


class SafetyData(BaseModel):
    """Overall safety and adverse event data"""
    adverse_events: List[AdverseEventDetail] = Field(
        default_factory=list,
        description="List of all adverse events with details"
    )
    death_count: Optional[int] = Field(
        None,
        description="Number of deaths"
    )
    qtc_interval_change: Optional[str] = Field(
        None,
        description="Mean QTc change, e.g., '8.3 msec increase'"
    )
    cardiac_safety_interpretation: Optional[str] = Field(
        None,
        description="Narrative cardiac safety summary, e.g., 'No clinically significant QTc prolongation'"
    )
    hepatotoxicity_warning: Optional[str] = Field(
        None,
        description="Liver safety warning text, e.g., 'Can cause fatal hepatotoxicity'"
    )
    lft_monitoring_requirements: Optional[str] = Field(
        None,
        description="LFT monitoring instructions, e.g., 'Monitor before each cycle'"
    )


# ============================================================================
# Category 5: Efficacy Outcomes (13 fields)
# ============================================================================

class EfficacyOutcomes(BaseModel):
    """Efficacy and response data"""
    objective_response_rate: Optional[str] = Field(
        None,
        description="ORR percentage, e.g., '25.8%'"
    )
    complete_response_count: Optional[int] = Field(
        None,
        description="Number of CR patients"
    )
    complete_response_rate: Optional[str] = Field(
        None,
        description="CR percentage, e.g., '10.8%'"
    )
    partial_response_count: Optional[int] = Field(
        None,
        description="Number of PR patients"
    )
    partial_response_rate: Optional[str] = Field(
        None,
        description="PR percentage, e.g., '15.0%'"
    )
    stable_disease_mention: bool = Field(
        False,
        description="Is stable disease (SD) mentioned?"
    )


# ============================================================================
# Category 5b: Clinical Studies (Deep Matrix)
# ============================================================================

class ClinicalStudyDetail(BaseModel):
    """Deep schema representation of a specific clinical study subgroup."""
    study_id: str = Field(..., description="e.g. 'CLN-19', 'TT20', 'SPI-BEL-103'")
    study_phase: Optional[str] = Field(None, description="'Phase 1', 'Phase 2', 'Phase 1/2'")
    patient_group: Optional[str] = Field(None, description="e.g. 'PTCL overall', 'PTCL-NOS'")
    n_patients: Optional[int] = Field(None, description="Sample size for this group")
    indication: Optional[str] = Field(None, description="e.g. 'PTCL', 'CTCL', 'AML'")
    dose_level: Optional[str] = Field(None, description="e.g. '1000 mg/m2'")
    gender: Optional[str] = Field(None, description="'Male', 'Female', 'Both'")
    orr: Optional[str] = Field(None, description="ORR %, e.g. '25.8%'")
    cr_rate: Optional[str] = Field(None, description="CR %, e.g. '10.8%'")
    pr_rate: Optional[str] = Field(None, description="PR %, e.g. '15.0%'")
    median_pfs: Optional[str] = Field(None, description="Median PFS, e.g. '1.6 months'")
    median_os: Optional[str] = Field(None, description="Median OS, e.g. '7.9 months'")
    median_dor: Optional[str] = Field(None, description="Median duration of response")
    pk_cmax: Optional[str] = Field(None, description="Cmax in this study/group")
    pk_auc: Optional[str] = Field(None, description="AUC in this study/group")
    pk_t_half: Optional[str] = Field(None, description="t1/2 in this study/group")
    grade_3_4_rate: Optional[str] = Field(None, description="% patients with any Grade 3-4 AE")
    top_aes: List[str] = Field(default_factory=list, description="Top AEs")
    discontinuation_rate: Optional[str] = Field(None, description="% who stopped due to AE")
    notes: Optional[str] = Field(None, description="Key notes")

class ClinicalStudiesData(BaseModel):
    """Matrix of clinical study outcomes across patient groups."""
    clinical_studies: List[ClinicalStudyDetail] = Field(
        default_factory=list,
        description="List of all clinical study outcomes by subgroups"
    )
    stable_disease_rate: Optional[str] = Field(
        None,
        description="SD percentage, e.g., '15.5%'"
    )
    median_time_to_response: Optional[str] = Field(
        None,
        description="Time to achieve response, e.g., '5.6 weeks'"
    )
    median_duration_of_response: Optional[str] = Field(
        None,
        description="How long response lasts, e.g., '13.6 months'"
    )
    median_pfs: Optional[str] = Field(
        None,
        description="Median progression-free survival, e.g., '1.6 months'"
    )
    median_os: Optional[str] = Field(
        None,
        description="Median overall survival, e.g., '7.9 months'"
    )
    subgroup_efficacy_comparison: Optional[Dict[str, str]] = Field(
        None,
        description="Efficacy by subgroup, e.g., {'PTCL-NOS': '28%', 'AITL': '46%'}"
    )
    confidence_intervals_efficacy: Optional[Dict[str, str]] = Field(
        None,
        description="95% CI for efficacy metrics, e.g., {'ORR_CI': '18.5-34.2%'}"
    )


# ============================================================================
# Category 6: Pharmacokinetics (9 fields)
# ============================================================================

class Pharmacokinetics(BaseModel):
    """Pharmacokinetic parameters and clinical chemistry biomarkers"""
    pk_objectives_narrative: Optional[str] = Field(
        None,
        description="PK study objectives, e.g., 'Evaluate AUC and Cmax at steady state'"
    )
    auc_value: Optional[str] = Field(
        None,
        description="Area under curve, e.g., '12.3 μg·h/mL'"
    )
    cmax_value: Optional[str] = Field(
        None,
        description="Maximum concentration, e.g., '4.5 μg/mL'"
    )
    elimination_half_life: Optional[str] = Field(
        None,
        description="t½, e.g., '1.1 hours'"
    )
    plasma_protein_binding: Optional[str] = Field(
        None,
        description="Protein binding percentage, e.g., '94%'"
    )
    clearance_total: Optional[str] = Field(
        None,
        description="Total clearance, e.g., '1240 mL/min'"
    )
    volume_of_distribution: Optional[str] = Field(
        None,
        description="Vd or Vss, e.g., '102 L'"
    )
    metabolism_pathway: Optional[str] = Field(
        None,
        description="Primary metabolic pathway, e.g., 'Glucuronidation via UGT1A1'"
    )
    pk_species: Optional[str] = Field(
        None,
        description="Species for PK data, e.g., 'Human', 'Rat'"
    )
    
    # Clinical Chemistry Biomarkers
    alp_alkaline_phosphatase: Optional[str] = Field(
        None,
        description="ALP - Alkaline Phosphatase levels with units, e.g., '120 U/L'"
    )
    tc_total_cholesterol: Optional[str] = Field(
        None,
        description="TC - Total Cholesterol levels with units, e.g., '180 mg/dL'"
    )
    tg_triglycerides: Optional[str] = Field(
        None,
        description="TG - Triglycerides levels with units, e.g., '150 mg/dL'"
    )
    pl_phospholipids: Optional[str] = Field(
        None,
        description="PL - Phospholipids levels with units"
    )
    tbil_total_bilirubin: Optional[str] = Field(
        None,
        description="TBIL - Total Bilirubin levels with units, e.g., '0.8 mg/dL'"
    )
    dbil_direct_bilirubin: Optional[str] = Field(
        None,
        description="DBIL - Direct Bilirubin levels with units, e.g., '0.2 mg/dL'"
    )
    glc_glucose: Optional[str] = Field(
        None,
        description="GLC - Glucose levels with units, e.g., '95 mg/dL'"
    )
    bun_blood_urea_nitrogen: Optional[str] = Field(
        None,
        description="BUN - Blood Urea Nitrogen levels with units, e.g., '18 mg/dL'"
    )
    cre_creatinine: Optional[str] = Field(
        None,
        description="CRE - Creatinine levels with units, e.g., '1.0 mg/dL'"
    )
    na_sodium: Optional[str] = Field(
        None,
        description="Na - Sodium levels with units, e.g., '140 mEq/L'"
    )
    alt_alanine_aminotransferase: Optional[str] = Field(
        None,
        description="ALT - Alanine Aminotransferase levels with units, e.g., '35 U/L'"
    )
    ast_aspartate_aminotransferase: Optional[str] = Field(
        None,
        description="AST - Aspartate Aminotransferase levels with units, e.g., '30 U/L'"
    )
    ldh_lactate_dehydrogenase: Optional[str] = Field(
        None,
        description="LDH - Lactate Dehydrogenase levels with units, e.g., '200 U/L'"
    )
    gtp_gamma_glutamyl_transpeptidase: Optional[str] = Field(
        None,
        description="GTP/GGT - Gamma-Glutamyl Transpeptidase levels with units, e.g., '40 U/L'"
    )



# ============================================================================
# Category 7: Eligibility Criteria (6 fields)
# ============================================================================

class EligibilityCriteria(BaseModel):
    """Patient eligibility criteria and lab thresholds"""
    eligibility_anc_threshold: Optional[str] = Field(
        None,
        description="Absolute neutrophil count minimum, e.g., '≥1.0 × 10⁹/L'"
    )
    eligibility_platelet_threshold: Optional[str] = Field(
        None,
        description="Platelet count minimum, e.g., '≥50 × 10⁹/L'"
    )
    eligibility_creatinine_clearance: Optional[str] = Field(
        None,
        description="CrCl minimum, e.g., '≥30 mL/min'"
    )
    eligibility_bilirubin_threshold: Optional[str] = Field(
        None,
        description="Bilirubin maximum, e.g., '≤1.5 × ULN'"
    )
    eligibility_alt_ast_threshold: Optional[str] = Field(
        None,
        description="ALT/AST maximum, e.g., '≤2.5 × ULN'"
    )
    hepatic_impairment_exclusion: Optional[str] = Field(
        None,
        description="Hepatic exclusion criteria, e.g., 'Bilirubin >1.5 × ULN excluded'"
    )


# ============================================================================
# Category 8: Treatment Management (4 fields)
# ============================================================================

class TreatmentManagement(BaseModel):
    """Treatment management rules and criteria"""
    toxicity_stopping_criteria: Optional[str] = Field(
        None,
        description="When to stop for toxicity, e.g., '≥33% Grade 4 hematologic toxicity'"
    )
    dose_reduction_schedule: List[str] = Field(
        default_factory=list,
        description="Dose reduction steps, e.g., ['1000 mg/m²', '750 mg/m²', '500 mg/m²']"
    )
    treatment_delay_rules: Optional[str] = Field(
        None,
        description="When to delay treatment, e.g., 'Delay if ANC <1.0 or platelets <50'"
    )
    supportive_care_requirements: List[str] = Field(
        default_factory=list,
        description="Required supportive care, e.g., ['Antiemetics', 'Growth factors']"
    )


# ============================================================================
# Category 9: Mechanism of Action (3 fields)
# ============================================================================

class MechanismOfAction(BaseModel):
    """Drug mechanism of action and molecular targets"""
    mechanism_description: Optional[str] = Field(
        None,
        description="Description of mechanism, e.g., 'HDAC inhibitor'"
    )
    molecular_targets: List[str] = Field(
        default_factory=list,
        description="Molecular targets, e.g., ['HDAC1', 'HDAC2', 'HDAC3']"
    )
    cellular_effects: Optional[str] = Field(
        None,
        description="Cellular/molecular effects description"
    )


# ============================================================================
# Category 10: Pre-Clinical Toxicology (7 fields)
# ============================================================================

class PreclinicalToxicology(BaseModel):
    """Pre-clinical toxicology study results"""
    single_dose_toxicity: Optional[str] = Field(
        None,
        description="Single-dose toxicity findings"
    )
    repeat_dose_toxicity: Optional[str] = Field(
        None,
        description="Repeat-dose toxicity findings"
    )
    toxicity_species: List[str] = Field(
        default_factory=list,
        description="Species tested, e.g., ['Rat', 'Dog']"
    )
    target_organs: List[str] = Field(
        default_factory=list,
        description="Target organs for toxicity, e.g., ['Liver', 'Bone marrow']"
    )
    noael_value: Optional[str] = Field(
        None,
        description="No Observed Adverse Effect Level with units"
    )
    maximum_tolerated_dose: Optional[str] = Field(
        None,
        description="MTD with units"
    )
    toxicology_summary: Optional[str] = Field(
        None,
        description="Overall toxicology summary"
    )


# ============================================================================
# Category 11: Genotoxicity (3 fields)
# ============================================================================

class Genotoxicity(BaseModel):
    """Genotoxicity study results"""
    genotoxicity_in_vitro: Optional[str] = Field(
        None,
        description="In vitro genotoxicity results"
    )
    genotoxicity_in_vivo: Optional[str] = Field(
        None,
        description="In vivo genotoxicity results, e.g., 'Rat bone marrow micronucleus'"
    )
    genotoxicity_conclusion: Optional[str] = Field(
        None,
        description="Overall conclusion: 'Positive', 'Negative', or description"
    )


# ============================================================================
# Category 12: Carcinogenicity (2 fields)
# ============================================================================

class Carcinogenicity(BaseModel):
    """Carcinogenicity study information"""
    carcinogenicity_studies_conducted: bool = Field(
        False,
        description="Were carcinogenicity studies conducted?"
    )
    carcinogenicity_results: Optional[str] = Field(
        None,
        description="Results or rationale for not conducting"
    )


# ============================================================================
# Category 13: Reproductive Toxicity (3 fields)
# ============================================================================

class ReproductiveToxicity(BaseModel):
    """Reproductive and developmental toxicity"""
    reproductive_toxicity_studies: bool = Field(
        False,
        description="Were reproductive toxicity studies conducted?"
    )
    reproductive_warnings: Optional[str] = Field(
        None,
        description="Reproductive toxicity warnings"
    )
    developmental_toxicity_warnings: Optional[str] = Field(
        None,
        description="Developmental toxicity warnings"
    )


# ============================================================================
# Category 14: Drug Interactions (5 fields)
# ============================================================================

class DrugInteractions(BaseModel):
    """Drug-drug interaction information"""
    drug_interaction_studies: List[str] = Field(
        default_factory=list,
        description="List of DDI study names or descriptions"
    )
    interacting_drugs: List[str] = Field(
        default_factory=list,
        description="Drugs with known interactions, e.g., ['Warfarin']"
    )
    cyp_enzyme_interactions: Optional[str] = Field(
        None,
        description="CYP enzyme interaction information"
    )
    interaction_mechanism: Optional[str] = Field(
        None,
        description="Mechanism of drug interactions"
    )
    clinical_significance: Optional[str] = Field(
        None,
        description="Clinical significance of interactions"
    )


# ============================================================================
# Category 15: Contraindications (2 fields)
# ============================================================================

class Contraindications(BaseModel):
    """Contraindications for drug use"""
    contraindications: List[str] = Field(
        default_factory=list,
        description="List of contraindications"
    )
    contraindication_rationale: Optional[str] = Field(
        None,
        description="Rationale for contraindications"
    )


# ============================================================================
# Category 16: Special Populations (6 fields)
# ============================================================================

class SpecialPopulations(BaseModel):
    """Special population considerations"""
    pediatric_use: Optional[str] = Field(
        None,
        description="Pediatric use guidance"
    )
    geriatric_use: Optional[str] = Field(
        None,
        description="Geriatric use guidance"
    )
    hepatic_impairment_guidance: Optional[str] = Field(
        None,
        description="Hepatic impairment dosing/guidance"
    )
    renal_impairment_guidance: Optional[str] = Field(
        None,
        description="Renal impairment dosing/guidance"
    )
    pregnancy_category: Optional[str] = Field(
        None,
        description="Pregnancy category or guidance"
    )
    lactation_guidance: Optional[str] = Field(
        None,
        description="Lactation/breastfeeding guidance"
    )


# ============================================================================
# Category 17: Formulation & Stability (6 fields)
# ============================================================================

class FormulationStability(BaseModel):
    """Drug formulation and stability information"""
    formulation_type: Optional[str] = Field(
        None,
        description="Formulation type, e.g., 'Lyophilized powder'"
    )
    excipients: List[str] = Field(
        default_factory=list,
        description="List of excipients"
    )
    shelf_life: Optional[str] = Field(
        None,
        description="Shelf life, e.g., '36 months'"
    )
    storage_conditions: Optional[str] = Field(
        None,
        description="Storage conditions, e.g., '20-25°C'"
    )
    reconstitution_instructions: Optional[str] = Field(
        None,
        description="How to reconstitute the drug"
    )
    stability_after_reconstitution: Optional[str] = Field(
        None,
        description="Stability after reconstitution"
    )



# ============================================================================
# Category 18: Semantic Relationships (Harmonization)
# ============================================================================

class RelationshipExtraction(BaseModel):
    """
    Represents a dynamic semantic relationship between two entities.
    Used for graph harmonization and discovering new edge types.
    """
    subject: str = Field(
        ...,
        description="The source entity name, e.g., 'Belinostat', 'Grade 3 Anemia'"
    )
    predicate: str = Field(
        ...,
        description="The relationship type, e.g., 'inhibits', 'associated_with', 'causes', 'treats', 'metabolized_by'"
    )
    object: str = Field(
        ...,
        description="The target entity name, e.g., 'HDAC', 'Peripheral T-Cell Lymphoma', 'UGT1A1'"
    )
    confidence: Optional[str] = Field(
        None,
        description="Qualitative confidence, e.g., 'High', 'Medium', 'Inferred'"
    )

class SemanticRelationships(BaseModel):
    """Collection of extracted semantic relationships"""
    relationships: List[RelationshipExtraction] = Field(
        default_factory=list,
        description="List of extracted semantic triples (Subject -> Predicate -> Object)"
    )


# ============================================================================
# Main Extraction Schema
# ============================================================================

class BelinoIBExtractionSchema(BaseModel):
    """
    Comprehensive extraction schema for Belino-IB document.
    Covers all 60+ required fields across 18 categories + Semantic Relationships.
    """
    
    # Category 1: Study Metadata
    study_metadata: StudyMetadata = Field(
        default_factory=StudyMetadata,
        description="Study-level metadata and identifiers"
    )
    
    # Category 2: Population Characteristics
    population_characteristics: PopulationCharacteristics = Field(
        default_factory=PopulationCharacteristics,
        description="Patient population demographics"
    )
    
    # Category 3: Dosing & Administration
    dosing_administration: DosingAdministration = Field(
        default_factory=DosingAdministration,
        description="Dosing regimen and administration details"
    )
    
    # Category 4: Safety & Adverse Events
    safety_data: SafetyData = Field(
        default_factory=SafetyData,
        description="Safety and adverse event data"
    )
    
    # Category 5: Efficacy Outcomes
    efficacy_outcomes: EfficacyOutcomes = Field(
        default_factory=EfficacyOutcomes,
        description="Efficacy and response data"
    )
    
    # Category 5b: Clinical Studies
    clinical_studies_data: ClinicalStudiesData = Field(
        default_factory=ClinicalStudiesData,
        description="Deep matrix of clinical study outcomes"
    )
    
    # Category 6: Pharmacokinetics
    pharmacokinetics: Pharmacokinetics = Field(
        default_factory=Pharmacokinetics,
        description="Pharmacokinetic parameters"
    )
    
    # Category 7: Eligibility Criteria
    eligibility_criteria: EligibilityCriteria = Field(
        default_factory=EligibilityCriteria,
        description="Patient eligibility criteria"
    )
    
    # Category 8: Treatment Management
    treatment_management: TreatmentManagement = Field(
        default_factory=TreatmentManagement,
        description="Treatment management rules"
    )
    
    # Category 9: Mechanism of Action
    mechanism_of_action: MechanismOfAction = Field(
        default_factory=MechanismOfAction,
        description="Drug mechanism of action"
    )
    
    # Category 10: Pre-Clinical Toxicology
    preclinical_toxicology: PreclinicalToxicology = Field(
        default_factory=PreclinicalToxicology,
        description="Pre-clinical toxicology data"
    )
    
    # Category 11: Genotoxicity
    genotoxicity: Genotoxicity = Field(
        default_factory=Genotoxicity,
        description="Genotoxicity study results"
    )
    
    # Category 12: Carcinogenicity
    carcinogenicity: Carcinogenicity = Field(
        default_factory=Carcinogenicity,
        description="Carcinogenicity information"
    )
    
    # Category 13: Reproductive Toxicity
    reproductive_toxicity: ReproductiveToxicity = Field(
        default_factory=ReproductiveToxicity,
        description="Reproductive toxicity data"
    )
    
    # Category 14: Drug Interactions
    drug_interactions: DrugInteractions = Field(
        default_factory=DrugInteractions,
        description="Drug-drug interactions"
    )
    
    # Category 15: Contraindications
    contraindications: Contraindications = Field(
        default_factory=Contraindications,
        description="Contraindications for use"
    )
    
    # Category 16: Special Populations
    special_populations: SpecialPopulations = Field(
        default_factory=SpecialPopulations,
        description="Special population guidance"
    )
    
    # Category 17: Formulation & Stability
    formulation_stability: FormulationStability = Field(
        default_factory=FormulationStability,
        description="Formulation and stability information"
    )
    
    # Category 18: Semantic Relationships (Harmonization)
    semantic_relationships: SemanticRelationships = Field(
        default_factory=SemanticRelationships,
        description="Extracted dynamic relationships between entities (Subject -> Predicate -> Object)"
    )

    # Metadata
    extraction_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Extraction confidence scores, missing fields, etc."
    )
