"""
section_schemas.py — Focused Pydantic schemas for per-section extraction.

Each schema exposes ONLY the fields relevant to its section type (~5-15 fields),
replacing the monolithic 90-field BelinoIBExtractionSchema sent to every chunk.
This implements Pillar 3 of the context engineering upgrade: Precision Tool Definitions.

Sections:
  1.  StudyMetadataExtraction
  2.  PopulationExtraction
  3.  DosingExtraction
  4.  SafetyExtraction
  5.  EfficacyExtraction
  6.  PKExtraction
  7.  EligibilityExtraction
  8.  TreatmentMgmtExtraction
  9.  MOAExtraction
  10. PreclinicalExtraction
  11. GenotoxicityExtraction
  12. CarcinogenicityExtraction
  13. ReproductiveToxExtraction
  14. DrugInteractionsExtraction
  15. ContraindicationsExtraction
  16. SpecialPopExtraction
  17. FormulationExtraction
  18. RelationshipsExtraction  (shared, cross-section)
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Shared helper
# ─────────────────────────────────────────────────────────────────────────────

class SemanticTriple(BaseModel):
    """Subject → Predicate → Object relationship triple."""
    subject: str = Field(..., description="Source entity, e.g. 'Belinostat'")
    predicate: str = Field(..., description="Relationship verb, e.g. 'INHIBITS', 'CAUSES', 'METABOLIZED_BY'")
    object: str = Field(..., description="Target entity, e.g. 'HDAC1', 'Thrombocytopenia'")
    confidence: Optional[str] = Field(None, description="'High', 'Medium', or 'Inferred'")


class AdverseEventItem(BaseModel):
    """Single adverse event row from a safety table."""
    adverse_event_preferred_term: str = Field(..., description="MedDRA preferred term, e.g. 'Thrombocytopenia'")
    adverse_event_patient_count: Optional[int] = Field(None, description="n (integer count)")
    adverse_event_percentage: Optional[str] = Field(None, description="All-grade %, e.g. '47.3%'")
    treatment_emergent_ae_flag: bool = Field(False, description="True if from a TEAE table")
    serious_adverse_event_flag: bool = Field(False, description="True if from an SAE table")
    grade_3_4_ae_frequency: Optional[Dict[str, Any]] = Field(
        None, description="e.g. {'count': 9, 'percentage': '7.0%'}"
    )
    ae_related_discontinuation_count: Optional[int] = Field(
        None, description="Patients who stopped treatment due to this AE"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Study Metadata
# ─────────────────────────────────────────────────────────────────────────────

class StudyMetadataExtraction(BaseModel):
    """Focused schema: Clinical Study Design / Drug Overview sections."""
    study_identifiers: List[str] = Field(
        default_factory=list,
        description="All study IDs mentioned, e.g. ['CLN-19', 'TT20', 'SPI-BEL-103']"
    )
    study_phase: Optional[str] = Field(None, description="e.g. 'Phase 2', 'Phase 1/2'")
    study_design: Optional[str] = Field(None, description="e.g. 'Open-label, single-arm, multicenter'")
    sponsor_information: Optional[str] = Field(None, description="Sponsor name, e.g. 'Spectrum Pharmaceuticals'")
    study_status: Optional[str] = Field(None, description="'Completed', 'Ongoing', 'Terminated'")
    study_start_date: Optional[str] = Field(None, description="DD-MMM-YYYY format, e.g. '04-May-2009'")
    study_end_date: Optional[str] = Field(None, description="DD-MMM-YYYY format, e.g. '27-Oct-2014'")
    participating_countries: List[str] = Field(
        default_factory=list,
        description="Country list, e.g. ['US', 'UK', 'Germany', 'France']"
    )
    study_group_classification: Optional[str] = Field(
        None, description="Pool group per Table 2, e.g. 'Group 1 – Pivotal monotherapy'"
    )
    semantic_relationships: List[SemanticTriple] = Field(
        default_factory=list,
        description="SPO triples discovered in this section"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. Population Characteristics
# ─────────────────────────────────────────────────────────────────────────────

class PopulationExtraction(BaseModel):
    """Focused schema: Patient population / demographics sections."""
    sample_size_n: Optional[int] = Field(None, description="Total N treated (integer), e.g. 129")
    disease_indication: Optional[str] = Field(None, description="e.g. 'Peripheral T-Cell Lymphoma'")
    disease_subtype: Optional[str] = Field(None, description="e.g. 'PTCL-NOS', 'AITL', 'ALCL ALK-'")
    population_treatment_status: Optional[str] = Field(
        None, description="e.g. 'Relapsed or refractory', 'Treatment-naïve'"
    )
    population_category: Optional[str] = Field(
        None, description="e.g. 'Hematologic malignancy', 'Solid tumor'"
    )
    median_age: Optional[str] = Field(None, description="e.g. '63.0 years'")
    age_range: Optional[str] = Field(None, description="e.g. '29-81'")
    gender_distribution: Optional[Dict[str, str]] = Field(
        None, description="e.g. {'male': '53.5%', 'female': '46.5%'}"
    )
    ecog_performance_status: Optional[str] = Field(
        None, description="ECOG 0-1 percentage, e.g. '78.3%'"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Dosing & Administration
# ─────────────────────────────────────────────────────────────────────────────

class DosingExtraction(BaseModel):
    """Focused schema: Dosing Regimen / Administration sections."""
    route_of_administration: Optional[str] = Field(None, description="'IV', 'Oral', 'PO'")
    dose_level: Optional[str] = Field(None, description="Numeric dose, e.g. '1000'")
    dose_unit: Optional[str] = Field(None, description="e.g. 'mg/m²', 'mg'")
    dosing_schedule: Optional[str] = Field(None, description="e.g. 'Days 1-5 of a 21-day cycle'")
    cycle_length: Optional[str] = Field(None, description="e.g. '21 days', '28 days'")
    infusion_duration: Optional[str] = Field(None, description="e.g. '30 minutes', '3 hours'")
    combination_therapy_drugs: List[str] = Field(
        default_factory=list,
        description="Other agents given concurrently, e.g. ['carboplatin', 'etoposide']"
    )
    dose_escalation_method: Optional[str] = Field(None, description="e.g. '3+3 design'")
    treatment_exposure_duration: Optional[Dict[str, str]] = Field(
        None, description="e.g. {'median': '4.2 months', 'range': '0.1-28.3'}"
    )
    number_of_treatment_cycles: Optional[Dict[str, str]] = Field(
        None, description="e.g. {'median': '2', 'range': '1-16'}"
    )
    total_patients_exposed: Optional[int] = Field(None, description="Integer count of exposed patients")
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Safety & Adverse Events
# ─────────────────────────────────────────────────────────────────────────────

class SafetyExtraction(BaseModel):
    """Focused schema: Safety / TEAE / SAE / AE table sections."""
    adverse_events: List[AdverseEventItem] = Field(
        default_factory=list,
        description="One entry per AE row extracted from safety tables"
    )
    death_count: Optional[int] = Field(None, description="Total treatment-related deaths")
    qtc_interval_change: Optional[str] = Field(None, description="Mean QTc change, e.g. '8.3 msec increase'")
    cardiac_safety_interpretation: Optional[str] = Field(
        None, description="Narrative cardiac safety summary"
    )
    hepatotoxicity_warning: Optional[str] = Field(
        None, description="Verbatim hepatotoxicity warning text from the document"
    )
    lft_monitoring_requirements: Optional[str] = Field(
        None, description="LFT monitoring instructions, e.g. 'Monitor before each cycle'"
    )
    grade_3_4_overall_rate: Optional[str] = Field(
        None, description="% of all patients with any Grade 3-4 event"
    )
    serious_adverse_event_rate: Optional[str] = Field(
        None, description="% of patients with any SAE"
    )
    discontinuation_due_to_ae_rate: Optional[str] = Field(
        None, description="% of patients who discontinued due to AEs"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Efficacy Outcomes
# ─────────────────────────────────────────────────────────────────────────────

class EfficacyExtraction(BaseModel):
    """Focused schema: Efficacy Outcomes / Response Rate sections."""
    objective_response_rate: Optional[str] = Field(None, description="ORR %, e.g. '25.8%'")
    complete_response_count: Optional[int] = Field(None, description="Number of CR patients")
    complete_response_rate: Optional[str] = Field(None, description="CR %, e.g. '10.8%'")
    partial_response_count: Optional[int] = Field(None, description="Number of PR patients")
    partial_response_rate: Optional[str] = Field(None, description="PR %, e.g. '15.0%'")
    stable_disease_rate: Optional[str] = Field(None, description="SD %, e.g. '15.5%'")
    median_time_to_response: Optional[str] = Field(None, description="e.g. '5.6 weeks'")
    median_duration_of_response: Optional[str] = Field(None, description="e.g. '13.6 months'")
    median_pfs: Optional[str] = Field(None, description="Median PFS, e.g. '1.6 months'")
    median_os: Optional[str] = Field(None, description="Median OS, e.g. '7.9 months'")
    subgroup_efficacy_comparison: Optional[Dict[str, str]] = Field(
        None, description="e.g. {'PTCL-NOS': '28%', 'AITL': '46%'}"
    )
    confidence_intervals_efficacy: Optional[Dict[str, str]] = Field(
        None, description="e.g. {'ORR_CI': '18.5-34.2%'}"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Pharmacokinetics  (per-species / per-dose rows)
# ─────────────────────────────────────────────────────────────────────────────

class PKDataPoint(BaseModel):
    """One PK row: tied to a specific species, gender, dose, and study."""
    species: str = Field(..., description="'Human', 'Rat', 'Dog', 'Mouse', 'Monkey'")
    gender: Optional[str] = Field(None, description="'Male', 'Female', 'Both', 'Mixed'")
    dose_level: Optional[str] = Field(None, description="e.g. '1000 mg/m\u00b2', '50 mg/kg'")
    route: Optional[str] = Field(None, description="'IV', 'PO', 'SC'")
    study_id: Optional[str] = Field(None, description="e.g. 'CLN-19', 'SPI-BEL-103', 'Rat 28-day'")
    cmax: Optional[str] = Field(None, description="Peak concentration with units, e.g. '4.5 \u03bcg/mL'")
    auc: Optional[str] = Field(None, description="AUC with units, e.g. '21057-31358 h\u00b7ng/mL'")
    t_half: Optional[str] = Field(None, description="Elimination t\u00bd, e.g. '1.1 hours'")
    clearance: Optional[str] = Field(None, description="CL with units, e.g. '1240 mL/min'")
    vd: Optional[str] = Field(None, description="Volume of distribution, e.g. '102 L'")
    tmax: Optional[str] = Field(None, description="Time to peak, e.g. 'End of infusion'")
    protein_binding: Optional[str] = Field(None, description="e.g. '94%'")
    metabolism: Optional[str] = Field(None, description="e.g. 'UGT1A1 glucuronidation'")
    notes: Optional[str] = Field(None, description="Any additional context or caveats")


class PKExtraction(BaseModel):
    """Focused schema: PK - captures per-species and per-dose rows."""
    pk_data_points: List[PKDataPoint] = Field(
        default_factory=list,
        description="One row per unique (species, dose, study) combination in this chunk"
    )
    plasma_protein_binding: Optional[str] = Field(None, description="Overall protein binding, e.g. '94% in humans'")
    metabolism_pathway: Optional[str] = Field(None, description="e.g. 'UGT1A1 glucuronidation'")
    pk_linearity: Optional[str] = Field(None, description="'Dose-proportional', 'Non-linear'")
    renal_excretion: Optional[str] = Field(None, description="% excreted renally, e.g. '~40% in 24h'")
    alt_baseline: Optional[str] = Field(None, description="ALT at baseline, e.g. '35 U/L'")
    ast_baseline: Optional[str] = Field(None, description="AST at baseline, e.g. '30 U/L'")
    bilirubin_baseline: Optional[str] = Field(None, description="TBIL at baseline, e.g. '0.8 mg/dL'")
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)



# ─────────────────────────────────────────────────────────────────────────────
# 7. Eligibility Criteria
# ─────────────────────────────────────────────────────────────────────────────

class EligibilityExtraction(BaseModel):
    """Focused schema: Eligibility / Inclusion-Exclusion sections."""
    eligibility_anc_threshold: Optional[str] = Field(
        None, description="ANC minimum, e.g. '≥1.0 × 10⁹/L'"
    )
    eligibility_platelet_threshold: Optional[str] = Field(
        None, description="Platelet minimum, e.g. '≥50 × 10⁹/L'"
    )
    eligibility_creatinine_clearance: Optional[str] = Field(
        None, description="CrCl minimum, e.g. '≥30 mL/min'"
    )
    eligibility_bilirubin_threshold: Optional[str] = Field(
        None, description="Bilirubin maximum, e.g. '≤1.5 × ULN'"
    )
    eligibility_alt_ast_threshold: Optional[str] = Field(
        None, description="ALT/AST maximum, e.g. '≤2.5 × ULN'"
    )
    hepatic_impairment_exclusion: Optional[str] = Field(
        None, description="Hepatic exclusion rule, e.g. 'Bilirubin >1.5 × ULN excluded'"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Treatment Management
# ─────────────────────────────────────────────────────────────────────────────

class TreatmentMgmtExtraction(BaseModel):
    """Focused schema: Dose Modifications / Treatment Management sections."""
    toxicity_stopping_criteria: Optional[str] = Field(
        None, description="When to permanently stop, e.g. 'Grade 4 hepatotoxicity'"
    )
    dose_reduction_schedule: List[str] = Field(
        default_factory=list,
        description="Ordered dose levels, e.g. ['1000 mg/m²', '750 mg/m²', '500 mg/m²']"
    )
    dose_modification_rules: Optional[str] = Field(
        None, description="Verbatim rules for when/how to reduce dose"
    )
    treatment_delay_rules: Optional[str] = Field(
        None, description="Conditions that require delaying next cycle"
    )
    treatment_discontinuation_rules: Optional[str] = Field(
        None, description="Conditions requiring permanent discontinuation"
    )
    supportive_care_requirements: List[str] = Field(
        default_factory=list,
        description="Required supportive care, e.g. ['Antiemetics', 'G-CSF']"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Mechanism of Action
# ─────────────────────────────────────────────────────────────────────────────

class MOAExtraction(BaseModel):
    """Focused schema: Mechanism of Action sections."""
    mechanism_description: Optional[str] = Field(None, description="e.g. 'Pan-HDAC inhibitor'")
    molecular_targets: List[str] = Field(
        default_factory=list,
        description="e.g. ['HDAC1', 'HDAC2', 'HDAC3', 'HDAC6']"
    )
    cellular_effects: Optional[str] = Field(
        None, description="Description of downstream cellular effects"
    )
    drug_class: Optional[str] = Field(None, description="e.g. 'Hydroxamic acid HDAC inhibitor'")
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Preclinical Toxicology  (per-species x gender x dose rows)
# ─────────────────────────────────────────────────────────────────────────────

class AnimalStudyEntry(BaseModel):
    """One row of animal study data: specific species, gender, dose, findings."""
    species: str = Field(..., description="'Rat', 'Dog', 'Mouse', 'Monkey', 'Rabbit'")
    gender: Optional[str] = Field(None, description="'Male', 'Female', 'Both'")
    study_type: Optional[str] = Field(None, description="'Single-dose', 'Repeat-dose (28-day)', 'Repeat-dose (13-week)', 'PK', 'Carcinogenicity'")
    dose_level: Optional[str] = Field(None, description="e.g. '50 mg/kg/day', '10 mg/m2'")
    route: Optional[str] = Field(None, description="'IV', 'PO', 'IP'")
    duration: Optional[str] = Field(None, description="e.g. '28 days', '13 weeks', 'Single dose'")
    cmax: Optional[str] = Field(None, description="Cmax in this species/dose, e.g. '12.3 ug/mL'")
    auc: Optional[str] = Field(None, description="AUC in this species/dose, e.g. '45.2 h*ug/mL'")
    t_half: Optional[str] = Field(None, description="t1/2 in this species, e.g. '0.8 hours'")
    noael: Optional[str] = Field(None, description="NOAEL for this species/study, e.g. '10 mg/kg/day'")
    loael: Optional[str] = Field(None, description="LOAEL if stated, e.g. '30 mg/kg/day'")
    target_organs: List[str] = Field(default_factory=list, description="Organs with findings, e.g. ['Thymus', 'Testis', 'Liver']")
    adverse_findings: List[str] = Field(default_factory=list, description="Specific findings, e.g. ['Thymic atrophy', 'Decreased RBC', 'GI ulceration']")
    mortality: Optional[str] = Field(None, description="Deaths at this dose, e.g. '2/10 at 80 mg/kg'")
    reversibility: Optional[str] = Field(None, description="'Reversible', 'Partially reversible', 'Irreversible'")
    study_id_reference: Optional[str] = Field(None, description="Internal study reference code if mentioned")


class PreclinicalExtraction(BaseModel):
    """Deep schema: Nonclinical Toxicology - structured animal study data matrix."""
    animal_studies: List[AnimalStudyEntry] = Field(
        default_factory=list,
        description="One entry per unique (species, dose, study_type) combination"
    )
    toxicity_species: List[str] = Field(default_factory=list, description="All species tested: ['Rat', 'Dog', 'Mouse']")
    overall_target_organs: List[str] = Field(default_factory=list, description="Organs consistently affected across species")
    toxicology_summary: Optional[str] = Field(None, description="1-3 sentence overall toxicology conclusion")
    genotoxicity_in_vitro: Optional[str] = Field(None, description="In vitro results, e.g. 'Ames test negative'")
    genotoxicity_in_vivo: Optional[str] = Field(None, description="In vivo results, e.g. 'Micronucleus negative'")
    genotoxicity_conclusion: Optional[str] = Field(None, description="'Genotoxic', 'Non-genotoxic'")
    carcinogenicity_studies_conducted: Optional[bool] = Field(None, description="Were carcinogenicity studies done?")
    carcinogenicity_results: Optional[str] = Field(None, description="Carcinogenicity findings or rationale for absence")
    reproductive_toxicity_studies: Optional[bool] = Field(None, description="Were repro tox studies done?")
    reproductive_warnings: Optional[str] = Field(None, description="Fertility/reproductive warnings")
    developmental_toxicity_warnings: Optional[str] = Field(None, description="Teratogenic or embryotoxic warnings")
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# NEW: Clinical Studies Matrix (per-study x patient-group rows)
# ─────────────────────────────────────────────────────────────────────────────

class ClinicalStudyEntry(BaseModel):
    """One row: data from a specific clinical study and patient subgroup."""
    study_id: str = Field(..., description="e.g. 'CLN-19', 'TT20', 'SPI-BEL-103'")
    study_phase: Optional[str] = Field(None, description="'Phase 1', 'Phase 2', 'Phase 1/2'")
    patient_group: Optional[str] = Field(None, description="e.g. 'PTCL overall', 'PTCL-NOS', 'AITL', 'ALCL ALK-', 'Overall'")
    n_patients: Optional[int] = Field(None, description="Sample size for this group")
    indication: Optional[str] = Field(None, description="e.g. 'PTCL', 'CTCL', 'AML', 'MDS'")
    dose_level: Optional[str] = Field(None, description="e.g. '1000 mg/m2'")
    gender: Optional[str] = Field(None, description="'Male', 'Female', 'Both'")
    orr: Optional[str] = Field(None, description="ORR %, e.g. '25.8%'")
    cr_rate: Optional[str] = Field(None, description="CR %, e.g. '10.8%'")
    pr_rate: Optional[str] = Field(None, description="PR %, e.g. '15.0%'")
    median_pfs: Optional[str] = Field(None, description="Median PFS, e.g. '1.6 months'")
    median_os: Optional[str] = Field(None, description="Median OS, e.g. '7.9 months'")
    median_dor: Optional[str] = Field(None, description="Median duration of response, e.g. '13.6 months'")
    pk_cmax: Optional[str] = Field(None, description="Cmax in this study/group")
    pk_auc: Optional[str] = Field(None, description="AUC in this study/group")
    pk_t_half: Optional[str] = Field(None, description="t1/2 in this study/group")
    grade_3_4_rate: Optional[str] = Field(None, description="% patients with any Grade 3-4 AE")
    top_aes: List[str] = Field(default_factory=list, description="Top AEs, e.g. ['Thrombocytopenia 47%', 'Nausea 52%']")
    discontinuation_rate: Optional[str] = Field(None, description="% who stopped due to AE")
    notes: Optional[str] = Field(None, description="Key notes, e.g. 'UGT1A1*28 subgroup analysis'")


class ClinicalStudiesExtraction(BaseModel):
    """Deep schema: Clinical studies - per-study and per-patient-group matrix."""
    clinical_studies: List[ClinicalStudyEntry] = Field(
        default_factory=list,
        description="One entry per unique (study_id, patient_group) combination"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)



# ─────────────────────────────────────────────────────────────────────────────
# 11. Genotoxicity
# ─────────────────────────────────────────────────────────────────────────────

class GenotoxicityExtraction(BaseModel):
    """Focused schema: Genotoxicity sections."""
    genotoxicity_in_vitro: Optional[str] = Field(
        None, description="In vitro assay results, e.g. 'Ames test negative'"
    )
    genotoxicity_in_vivo: Optional[str] = Field(
        None, description="In vivo assay results, e.g. 'Rat micronucleus assay negative'"
    )
    genotoxicity_conclusion: Optional[str] = Field(
        None, description="'Genotoxic', 'Non-genotoxic', or study-specific conclusion"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Carcinogenicity
# ─────────────────────────────────────────────────────────────────────────────

class CarcinogenicityExtraction(BaseModel):
    """Focused schema: Carcinogenicity sections."""
    carcinogenicity_studies_conducted: bool = Field(
        False, description="Were formal carcinogenicity studies conducted?"
    )
    carcinogenicity_results: Optional[str] = Field(
        None, description="Study results or rationale for not conducting studies"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 13. Reproductive Toxicity
# ─────────────────────────────────────────────────────────────────────────────

class ReproductiveToxExtraction(BaseModel):
    """Focused schema: Reproductive & Developmental Toxicity sections."""
    reproductive_toxicity_studies: bool = Field(False, description="Were studies conducted?")
    reproductive_warnings: Optional[str] = Field(None, description="Fertility/reproductive warnings")
    developmental_toxicity_warnings: Optional[str] = Field(
        None, description="Teratogenic or embryotoxic warnings"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 14. Drug Interactions
# ─────────────────────────────────────────────────────────────────────────────

class DrugInteractionsExtraction(BaseModel):
    """Focused schema: Drug Interactions sections."""
    drug_interaction_studies: List[str] = Field(
        default_factory=list,
        description="DDI study descriptions, e.g. ['Warfarin DDI study', 'CYP3A4 substrate study']"
    )
    interacting_drugs: List[str] = Field(
        default_factory=list,
        description="Drugs with identified interactions, e.g. ['Warfarin', 'Strong CYP3A4 inhibitors']"
    )
    cyp_enzyme_interactions: Optional[str] = Field(None, description="CYP enzyme details")
    interaction_mechanism: Optional[str] = Field(None, description="Mechanism of the interaction")
    clinical_significance: Optional[str] = Field(None, description="Clinical significance description")
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 15. Contraindications
# ─────────────────────────────────────────────────────────────────────────────

class ContraindicationsExtraction(BaseModel):
    """Focused schema: Contraindications sections."""
    contraindications: List[str] = Field(
        default_factory=list,
        description="e.g. ['Severe hepatic impairment', 'Known hypersensitivity to belinostat']"
    )
    contraindication_rationale: Optional[str] = Field(
        None, description="Rationale or basis for each contraindication"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 16. Special Populations
# ─────────────────────────────────────────────────────────────────────────────

class SpecialPopExtraction(BaseModel):
    """Focused schema: Special Populations sections."""
    pediatric_use: Optional[str] = Field(None, description="Pediatric use guidance or data")
    geriatric_use: Optional[str] = Field(None, description="Geriatric use guidance or data")
    hepatic_impairment_guidance: Optional[str] = Field(
        None, description="Dosing guidance for hepatic impairment"
    )
    renal_impairment_guidance: Optional[str] = Field(
        None, description="Dosing guidance for renal impairment"
    )
    pregnancy_category: Optional[str] = Field(None, description="Pregnancy category or risk summary")
    lactation_guidance: Optional[str] = Field(None, description="Breastfeeding guidance")
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 17. Formulation & Stability
# ─────────────────────────────────────────────────────────────────────────────

class FormulationExtraction(BaseModel):
    """Focused schema: Formulation & Stability sections."""
    formulation_type: Optional[str] = Field(
        None, description="e.g. 'Lyophilized powder for injection'"
    )
    excipients: List[str] = Field(
        default_factory=list, description="List of inactive ingredients"
    )
    shelf_life: Optional[str] = Field(None, description="e.g. '36 months'")
    storage_conditions: Optional[str] = Field(None, description="e.g. '20-25°C (68-77°F)'")
    reconstitution_instructions: Optional[str] = Field(
        None, description="How to reconstitute the formulation"
    )
    stability_after_reconstitution: Optional[str] = Field(
        None, description="e.g. '12 hours at room temperature'"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# 18. Relationships-only (for Cardiac Safety, Hepatotoxicity, Monitoring chunks)
# ─────────────────────────────────────────────────────────────────────────────

class RelationshipsOnlyExtraction(BaseModel):
    """
    Minimal schema for sections with no dedicated category schema (e.g. Cardiac Safety,
    Monitoring and Warnings, Deaths and SAEs). Extracts AEs + relationships only.
    """
    adverse_events: List[AdverseEventItem] = Field(default_factory=list)
    key_findings: Optional[str] = Field(
        None, description="1-3 sentence summary of the key finding in this section"
    )
    semantic_relationships: List[SemanticTriple] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Schema Registry — map section_name → Pydantic model + tool name
# ─────────────────────────────────────────────────────────────────────────────

SECTION_SCHEMA_MAP: Dict[str, Dict] = {
    "Drug Overview":                    {"model": StudyMetadataExtraction,      "tool": "extract_study_metadata"},
    "Clinical Study Design":            {"model": ClinicalStudiesExtraction,    "tool": "extract_clinical_studies"},
    "Mechanism of Action":              {"model": MOAExtraction,                "tool": "extract_moa"},
    "Pharmacokinetics":                 {"model": PKExtraction,                 "tool": "extract_pk"},
    "Efficacy Outcomes":                {"model": ClinicalStudiesExtraction,    "tool": "extract_clinical_studies"},
    "Safety and Adverse Events":        {"model": SafetyExtraction,             "tool": "extract_safety"},
    "Hepatotoxicity":                   {"model": SafetyExtraction,             "tool": "extract_safety"},
    "Cardiac Safety":                   {"model": RelationshipsOnlyExtraction,  "tool": "extract_findings"},
    "Deaths and Serious Adverse Events":{"model": SafetyExtraction,             "tool": "extract_safety"},
    "Monitoring and Warnings":          {"model": RelationshipsOnlyExtraction,  "tool": "extract_findings"},
    "Dosing Regimen":                   {"model": DosingExtraction,             "tool": "extract_dosing"},
    "Dose Modifications":               {"model": TreatmentMgmtExtraction,      "tool": "extract_treatment_mgmt"},
    "Special Populations - Hepatic":    {"model": SpecialPopExtraction,         "tool": "extract_special_pop"},
    "Special Populations – Hepatic":    {"model": SpecialPopExtraction,         "tool": "extract_special_pop"},
    "Nonclinical Toxicology":           {"model": PreclinicalExtraction,        "tool": "extract_preclinical"},
    "Other":                            {"model": RelationshipsOnlyExtraction,  "tool": "extract_findings"},
}

# Additional section types not in ALLOWED_SECTIONS but may appear via LLM router
SECTION_SCHEMA_MAP.update({
    "Eligibility Criteria":             {"model": EligibilityExtraction,        "tool": "extract_eligibility"},
    "Treatment Management":             {"model": TreatmentMgmtExtraction,      "tool": "extract_treatment_mgmt"},
    "Genotoxicity":                     {"model": GenotoxicityExtraction,       "tool": "extract_genotoxicity"},
    "Carcinogenicity":                  {"model": CarcinogenicityExtraction,    "tool": "extract_carcinogenicity"},
    "Reproductive Toxicity":            {"model": ReproductiveToxExtraction,    "tool": "extract_repro_tox"},
    "Drug Interactions":                {"model": DrugInteractionsExtraction,   "tool": "extract_ddi"},
    "Contraindications":                {"model": ContraindicationsExtraction,  "tool": "extract_contraindications"},
    "Special Populations":              {"model": SpecialPopExtraction,         "tool": "extract_special_pop"},
    "Formulation and Stability":        {"model": FormulationExtraction,        "tool": "extract_formulation"},
    "Population Characteristics":       {"model": ClinicalStudiesExtraction,    "tool": "extract_clinical_studies"},
})


def get_schema_for_section(section_name: str) -> Dict:
    """
    Returns {'model': PydanticModel, 'tool': str} for the given section.
    Falls back to RelationshipsOnlyExtraction if section is not in the map.
    """
    return SECTION_SCHEMA_MAP.get(
        section_name,
        {"model": RelationshipsOnlyExtraction, "tool": "extract_findings"}
    )
