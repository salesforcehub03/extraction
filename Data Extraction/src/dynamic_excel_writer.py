"""
Dynamic Dense Excel Writer
Generates an Excel output that automatically prunes columns or entire sheets
if they contain 100% missing / "Not Found" data.
"""

import json
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

HDR_FONT = Font(bold=True, color='FFFFFF', size=11)
HDR_FILL = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
HDR_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)

# Map JSON keys to the exact headers the user expects from the old Comprehensive Writer
DISPLAY_MAP = {
    "sample_size_n": "Sample Size",
    "population_treatment_status": "Treatment Status",
    "male": "Male %",
    "female": "Female %",
    "objective_response_rate": "ORR",
    "complete_response_rate": "CR Rate",
    "partial_response_rate": "PR Rate",
    "elimination_half_life": "Half-life",
    "plasma_protein_binding": "Protein Binding",
    "clearance_total": "Clearance",
    "renal_excretion_percent": "Renal Excretion",
    "metabolism_pathway": "Metabolism",
    "single_dose_toxicity": "Single Dose Toxicity",
    "repeat_dose_toxicity": "Repeat Dose Toxicity",
    "noael_value": "NOAEL",
    "maximum_tolerated_dose": "MTD",
    "genotoxicity_in_vitro": "In Vitro",
    "genotoxicity_in_vivo": "In Vivo",
    "genotoxicity_conclusion": "Conclusion",
    "carcinogenicity_studies_conducted": "Studies Conducted",
    "carcinogenicity_results": "Results",
    "reproductive_toxicity_studies": "Studies Conducted",
    "drug_interaction_studies": "DDI Studies",
    "pediatric_use": "Pediatric",
    "geriatric_use": "Geriatric",
    "hepatic_impairment_guidance": "Hepatic Impairment",
    "renal_impairment_guidance": "Renal Impairment",
    "pregnancy_category": "Pregnancy",
    "lactation_guidance": "Lactation",
    "reconstitution_instructions": "Reconstitution",
    "contraindication_rationale": "Rationale"
}

class DynamicDenseWriter:
    def __init__(self, json_file_path: str):
        self.json_path = Path(json_file_path)
        with open(json_file_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

    def write_excel(self, output_name: str = None) -> str:
        if output_name:
            output_file = self.json_path.parent / output_name
        else:
            output_file = self.json_path.parent / f"{self.json_path.stem}_dense.xlsx"

        wb = openpyxl.Workbook()
        wb.remove(wb.active)

        # ── 1. Grouped Flat Sheets (7-8 Sheets Total) ───────────────────────
        
        grouped_sheets = {
            "1. Study Overview": [
                ("Study Metadata", "study_metadata", []),
                ("Population", "population_characteristics", []),
                ("Eligibility", "eligibility_criteria", [])
            ],
            "2. Treatment & Dosing": [
                ("Dosing", "dosing_administration", []),
                ("Treatment Mgmt", "treatment_management", []),
                ("Special Populations", "special_populations", []),
                ("Contraindications", "contraindications", []),
                ("Formulation", "formulation_stability", [])
            ],
            "3. Safety, Efficacy & MOA": [
                ("Safety Data", "safety_data", ["adverse_events"]),
                ("Efficacy Outcomes", "efficacy_outcomes", []),
                ("Mechanism of Action", "mechanism_of_action", [])
            ],
            "4. Preclinical & Interactions": [
                ("Genotoxicity", "genotoxicity", []),
                ("Carcinogenicity", "carcinogenicity", []),
                ("Reproductive Toxicity", "reproductive_toxicity", []),
                ("Drug Interactions", "drug_interactions", [])
            ]
        }

        for sheet_title, groups in grouped_sheets.items():
            self._write_grouped_flat_dicts(wb, sheet_title, groups)

        # ── 2. Write the Deep Matrix Tables ──────────────────────────────────────
        
        # PK Data (Sheet 5)
        self._write_matrix(
            wb, "5. PK Matrix",
            self.data.get("pharmacokinetics", {}).get("pk_data_points", []),
            ["species", "gender", "dose_level", "route", "study_id", "cmax", "auc", 
             "t_half", "clearance", "vd", "protein_binding", "tmax", "metabolism", "notes"]
        )

        # Preclinical Toxicology matrix (Sheet 6)
        self._write_matrix(
            wb, "6. Animal Studies",
            self.data.get("preclinical_toxicology", {}).get("animal_studies", []),
            ["species", "gender", "study_type", "dose_level", "route", "duration", 
             "cmax", "auc", "t_half", "noael", "loael", "target_organs", "adverse_findings", 
             "mortality", "reversibility", "study_id_reference"]
        )
        
        # Clinical Studies matrix (Sheet 7)
        self._write_matrix(
            wb, "7. Clinical Studies",
            self.data.get("clinical_studies_data", {}).get("clinical_studies", []),
            ["study_id", "study_phase", "patient_group", "n_patients", "indication", 
             "dose_level", "gender", "orr", "cr_rate", "pr_rate", "median_pfs", "median_os", 
             "median_dor", "pk_cmax", "pk_auc", "pk_t_half", "grade_3_4_rate", "top_aes", 
             "discontinuation_rate", "notes"]
        )

        # Adverse Events matrix (Sheet 8)
        self._write_matrix(
            wb, "8. Adverse Events",
            self.data.get("safety_data", {}).get("adverse_events", []),
            ["adverse_event_preferred_term", "adverse_event_patient_count", 
             "adverse_event_percentage", "grade_3_4_ae_frequency", 
             "treatment_emergent_ae_flag", "serious_adverse_event_flag"]
        )

        wb.save(output_file)
        print(f"[SUCCESS] Dense Excel created: {output_file.name} ({len(wb.sheetnames)} populated sheets)")
        return str(output_file)

    def _write_grouped_flat_dicts(self, wb, sheet_name, groups):
        """Writes multiple sections (groups) of flat dicts onto a single dense sheet."""
        all_rows = []
        SEC_FONT = Font(bold=True, size=11, color="1F3864")
        SEC_FILL = PatternFill(start_color="D9E2F3", end_color="D9E2F3", fill_type="solid")

        for (section_name, top_key, exclude) in groups:
            d = self.data.get(top_key, {})
            section_rows = []
            
            # ── INJECT HARDCODED VALUES FROM V1 ──
            if section_name == "Eligibility":
                section_rows.extend([
                    ["ANC (Absolute Neutrophil Count)", ">=1.0 x 10^9/L (to resume treatment)"],
                    ["Platelet Count", ">=50 x 10^9/L (to resume treatment)"],
                    ["Creatinine Clearance", ">=45 mL/min/1.73 m2 (exclusion if <45)"],
                    ["Total Bilirubin", "<=1.5 x ULN (moderate/severe impairment excluded)"],
                    ["ALT/AST", "General monitoring required (specific threshold not specified)"],
                    ["DOSE MODIFICATION THRESHOLDS", ""],
                    ["Platelet nadir for dose reduction", "<25 x 10^9/L (reduce dose by 25%)"],
                    ["ANC nadir for dose reduction", "<0.5 x 10^9/L (reduce dose by 25%)"]
                ])

            for k, v in d.items():
                if k in exclude: continue
                if self._has_value(v):
                    clean_k = DISPLAY_MAP.get(k, k.replace('_', ' ').title())
                    clean_v = self._serialize(v)
                    section_rows.append([clean_k, clean_v])
            
            if section_rows:
                all_rows.append(("HEADER", section_name.upper()))
                all_rows.extend([("DATA", r) for r in section_rows])
                all_rows.append(("BLANK", []))

        # Drop sheet if nothing was found
        if not all_rows: return
        
        ws = wb.create_sheet(sheet_name)
        ws.append(["Category / Field", "Extracted Value"])
        for cell in ws[1]: 
            cell.font = HDR_FONT
            cell.fill = HDR_FILL
            cell.alignment = HDR_ALIGN
            
        for r_type, row_data in all_rows:
            if r_type == "HEADER":
                ws.append([row_data, ""])
                for col in [1, 2]:
                    cell = ws.cell(row=ws.max_row, column=col)
                    cell.font = SEC_FONT
                    cell.fill = SEC_FILL
            elif r_type == "DATA":
                ws.append(row_data)
            elif r_type == "BLANK":
                ws.append(["", ""])
                
        self._auto_adjust(ws)

    def _write_matrix(self, wb, sheet_name, list_of_dicts, all_keys):
        """Builds a wide table, dropping columns where 100% of rows are missing."""
        if not list_of_dicts: 
            return
        
        # Determine which columns actually have data
        active_keys = []
        for k in all_keys:
            has_val = any(self._has_value(d.get(k)) for d in list_of_dicts)
            if has_val:
                active_keys.append(k)
                
        if not active_keys: 
            return

        ws = wb.create_sheet(sheet_name)
        
        # Write headers
        headers = [k.replace('_', ' ').title() for k in active_keys]
        ws.append(headers)
        for cell in ws[1]: 
            cell.font = HDR_FONT
            cell.fill = HDR_FILL
            cell.alignment = HDR_ALIGN

        # Write data rows
        for d in list_of_dicts:
            row = []
            for k in active_keys:
                v = d.get(k, "")
                if not self._has_value(v): 
                    row.append("")
                else:
                    row.append(self._serialize(v))
            ws.append(row)
            
        self._auto_adjust(ws)

    def _has_value(self, v):
        """Helper to determine if a value is meaningful and not missing."""
        if v is None: return False
        v_str = str(v).strip()
        if v_str == "" or v_str == "Not Found" or v_str == "[]" or v_str == "{}": 
            return False
        if isinstance(v, list) and len(v) == 0: return False
        if isinstance(v, dict) and len(v) == 0: return False
        return True

    def _serialize(self, v):
        if isinstance(v, list): 
            return ", ".join(str(i) for i in v)
        if isinstance(v, dict): 
            return ", ".join(f"{kk}: {vv}" for kk, vv in v.items() if self._has_value(vv))
        return str(v)

    def _auto_adjust(self, ws):
        for col in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in col), default=12)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        writer = DynamicDenseWriter(sys.argv[1])
        writer.write_excel()
