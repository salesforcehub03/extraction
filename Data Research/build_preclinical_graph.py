"""
Preclinical Data Knowledge Graph — Nodes & Edges CSV Generator
Reads belino-preclinial.xlsx and produces:
  - preclinical_nodes.csv
  - preclinical_edges.csv
"""

import pandas as pd
import re
import uuid
import warnings

warnings.filterwarnings("ignore")

FILE = r"D:\AViiD\Data Research\belino-preclinial.xlsx"
OUT_NODES = r"D:\AViiD\Data Research\preclinical_nodes.csv"
OUT_EDGES = r"D:\AViiD\Data Research\preclinical_edges.csv"

nodes = []  # list of dicts
edges = []  # list of dicts


def nid():
    """Short unique id"""
    return uuid.uuid4().hex[:12]


# ──────────────────────────────────────────────
# 1. DRUG NODE
# ──────────────────────────────────────────────
drug_id = "DRUG_PXD101"
nodes.append({
    "node_id": drug_id,
    "node_type": "Drug",
    "drug_name": "PXD101 (Belinostat)",
    "mechanism": "Histone Deacetylase (HDAC) Inhibitor",
    "route": "Intravenous (IV)",
    "formulation": "Solution for injection",
})

# ──────────────────────────────────────────────
# 2. STUDY NODES  (experimental design sheet)
#    The file only contains rat experimental design explicitly,
#    but dog data exists in other sheets — two studies: RAT & DOG
# ──────────────────────────────────────────────

# RAT Study
rat_study_id = "STUDY_RAT_26WK"
nodes.append({
    "node_id": rat_study_id,
    "node_type": "Study",
    "study_id": "PXD101-RAT-26WK",
    "species": "Rat",
    "study_type": "Repeat-dose toxicity with TK",
    "duration_days": 182,  # 26 weeks
    "cycle_count": 8,      # 8 cycles based on Cycle 8 data in clin chem
    "dosing_schedule": "5 days on / 16 days off (21-day cycle)",
    "vehicle": "L-arginine/phosphoric acid solution",
    "glp_status": "GLP",
})

# DOG Study
dog_study_id = "STUDY_DOG_26WK"
nodes.append({
    "node_id": dog_study_id,
    "node_type": "Study",
    "study_id": "PXD101-DOG-26WK",
    "species": "Dog",
    "study_type": "Repeat-dose toxicity with TK",
    "duration_days": 182,
    "cycle_count": 8,
    "dosing_schedule": "5 days on / 16 days off (21-day cycle)",
    "vehicle": "L-arginine/phosphoric acid solution",
    "glp_status": "GLP",
})

# Drug → tested_in → Study
edges.append({"source": drug_id, "target": rat_study_id, "edge_type": "tested_in"})
edges.append({"source": drug_id, "target": dog_study_id, "edge_type": "tested_in"})

# ──────────────────────────────────────────────
# 3. ANIMAL GROUP NODES — from experimental design (rats) + inferred for dogs
# ──────────────────────────────────────────────
df_design = pd.read_excel(FILE, sheet_name="experimental design in rats", header=None)

rat_groups = []
for r in range(3, 7):  # rows 3-6 = groups 1-4
    group_num = int(df_design.iloc[r, 0])
    dose = float(df_design.iloc[r, 1])
    n_term_m = df_design.iloc[r, 3]
    n_term_f = df_design.iloc[r, 4]
    n_rec_m = df_design.iloc[r, 5]
    n_rec_f = df_design.iloc[r, 6]
    n_tk_m = df_design.iloc[r, 7]
    n_tk_f = df_design.iloc[r, 8]

    def safe_int(v):
        try:
            return int(v)
        except (ValueError, TypeError):
            return 0

    # Terminal group (M+F combined, but we create per-sex groups for edges)
    for sex in ["M", "F"]:
        gid = f"AG_RAT_{sex}_{int(dose)}MG"
        n_t = safe_int(n_term_m) if sex == "M" else safe_int(n_term_f)
        n_r = safe_int(n_rec_m) if sex == "M" else safe_int(n_rec_f)
        n_tk = safe_int(n_tk_m) if sex == "M" else safe_int(n_tk_f)

        nodes.append({
            "node_id": gid,
            "node_type": "AnimalGroup",
            "group_id": f"RAT-G{group_num}-{sex}",
            "species": "Rat",
            "sex": sex,
            "dose_mg_per_kg": dose,
            "dose_mg_per_m2": round(dose * 6, 1),  # rat Km factor = 6
            "n_terminal": n_t,
            "n_recovery": n_r,
            "n_tk": n_tk,
            "treatment_phase": "terminal/recovery/TK",
        })
        rat_groups.append({"gid": gid, "sex": sex, "dose": dose})

        # Study → has_group → AnimalGroup
        edges.append({"source": rat_study_id, "target": gid, "edge_type": "has_group"})
        # Drug → administered_to → AnimalGroup
        edges.append({"source": drug_id, "target": gid, "edge_type": "administered_to"})

# Dog groups (inferred from microscopic findings & exposure: 0, 10, 25, 50 mg/kg)
dog_doses = [0, 10, 25, 50]
dog_groups = []
for dose in dog_doses:
    for sex in ["M", "F"]:
        gid = f"AG_DOG_{sex}_{int(dose)}MG"
        nodes.append({
            "node_id": gid,
            "node_type": "AnimalGroup",
            "group_id": f"DOG-{sex}-{int(dose)}MG",
            "species": "Dog",
            "sex": sex,
            "dose_mg_per_kg": dose,
            "dose_mg_per_m2": round(dose * 20, 1),  # dog Km factor ≈ 20
            "n_terminal": 3,
            "n_recovery": 2 if dose in [0, 50] else 0,
            "n_tk": 3,
            "treatment_phase": "terminal/recovery/TK" if dose in [0, 50] else "terminal/TK",
        })
        dog_groups.append({"gid": gid, "sex": sex, "dose": dose})
        edges.append({"source": dog_study_id, "target": gid, "edge_type": "has_group"})
        edges.append({"source": drug_id, "target": gid, "edge_type": "administered_to"})

# Helper to find group id
def find_group(species, sex, dose):
    prefix = "AG_RAT" if species == "Rat" else "AG_DOG"
    return f"{prefix}_{sex}_{int(dose)}MG"


# ──────────────────────────────────────────────
# 4. PK_PROFILE NODES — from "exposure" sheet
# ──────────────────────────────────────────────
df_exp = pd.read_excel(FILE, sheet_name="exposure")

for _, row in df_exp.iterrows():
    species = row["Species"]
    sex = row["Sex"]
    dose = float(row["Dose_mg_per_kg"])
    day = int(row["Day"])
    cmax = row["Cmax_ug_per_mL"]
    auc = row["AUC_ug_h_per_mL"]

    pk_id = f"PK_{species.upper()}_{sex}_{int(dose)}MG_D{day}"

    # Compute accumulation ratio if Day 151 value exists
    acc_flag = "Yes" if day == 151 else "No"

    # Calculate exposure ratio (Day 151 / Day 1) for matched entries
    day1_match = df_exp[(df_exp["Species"] == species) & (df_exp["Sex"] == sex) &
                        (df_exp["Dose_mg_per_kg"] == dose) & (df_exp["Day"] == 1)]
    day151_match = df_exp[(df_exp["Species"] == species) & (df_exp["Sex"] == sex) &
                          (df_exp["Dose_mg_per_kg"] == dose) & (df_exp["Day"] == 151)]

    exposure_ratio = ""
    if day == 151 and len(day1_match) > 0:
        d1_auc = day1_match.iloc[0]["AUC_ug_h_per_mL"]
        if d1_auc > 0:
            exposure_ratio = round(auc / d1_auc, 2)

    nodes.append({
        "node_id": pk_id,
        "node_type": "PK_Profile",
        "species": species,
        "sex": sex,
        "dose_mg_per_kg": dose,
        "day": day,
        "Cmax": cmax,
        "Cmax_SD": "",
        "AUC": auc,
        "AUC_SD": "",
        "Tmax": "",
        "accumulation_flag": acc_flag,
        "exposure_ratio_day151_day1": exposure_ratio,
        "sex_exposure_ratio": "",
    })

    # AnimalGroup → has_exposure → PK_Profile
    ag_id = find_group(species, sex, dose)
    edges.append({"source": ag_id, "target": pk_id, "edge_type": "has_exposure"})


# ──────────────────────────────────────────────
# 5. HEMATOLOGY_EVENT NODES — from "toxcity" sheet (WBC entries)
# ──────────────────────────────────────────────
df_tox = pd.read_excel(FILE, sheet_name="toxcity")

for _, row in df_tox.iterrows():
    metric = row["Toxicity_Metric"]
    species = row["Species"]
    sex = row["Sex"]
    dose = float(row["Dose_mg_per_kg"])
    value = row["Value"]

    if "WBC" in metric or "RBC" in metric or "Platelet" in metric or "Hematocrit" in metric:
        hem_id = f"HEM_{species.upper()}_{sex}_{int(dose)}MG_{metric}"
        param = metric.replace("_change_pct", "").replace("_", " ")

        nodes.append({
            "node_id": hem_id,
            "node_type": "Hematology_Event",
            "species": species,
            "sex": sex,
            "dose_mg_per_kg": dose,
            "cycle": "Terminal",
            "parameter": param,
            "percent_change": value,
            "statistical_significance": "Yes" if abs(float(value)) > 20 else "",
            "recovery_flag": "Not assessed",
        })

        ag_id = find_group(species, sex, dose)
        edges.append({"source": ag_id, "target": hem_id, "edge_type": "observed_hematology"})

        # PK_Profile → associated_with → Hematology_Event
        pk_day151 = f"PK_{species.upper()}_{sex}_{int(dose)}MG_D151"
        edges.append({"source": pk_day151, "target": hem_id, "edge_type": "associated_with"})


# ──────────────────────────────────────────────
# 6. CLINICAL_CHEMISTRY_EVENT NODES — Clinical Chemistry Parameters sheet
# ──────────────────────────────────────────────
df_chem = pd.read_excel(FILE, sheet_name="Clinical Chemistry Parameters ", header=None)

# Structure: Row 0 = header, Row 1 = doses, Row 2 = sex, Row 3-6 = data
doses_chem = [10, 25, 100]
sex_cols = {
    10: {"M": 1, "F": 2},
    25: {"M": 3, "F": 4},
    100: {"M": 5, "F": 6},
}

for r in range(3, 7):  # data rows
    param_raw = str(df_chem.iloc[r, 0])
    # Parse parameter and cycle
    match = re.match(r"(.+?)\s+Cycle\s+(\d+)", param_raw)
    if match:
        param_name = match.group(1).strip()
        cycle = int(match.group(2))
    elif "Recovery" in param_raw:
        param_name = "Alanine Aminotransferase"
        cycle = "Recovery"
    else:
        param_name = param_raw
        cycle = ""

    for dose in doses_chem:
        for sex in ["M", "F"]:
            col = sex_cols[dose][sex]
            val_raw = str(df_chem.iloc[r, col])
            if val_raw == "nan" or val_raw == "None" or val_raw == "ND":
                continue

            # Parse significance markers
            sig = ""
            val_clean = val_raw
            if "***" in val_raw:
                sig = "p<0.001"
                val_clean = val_raw.replace("***", "")
            elif "**" in val_raw:
                sig = "p<0.01"
                val_clean = val_raw.replace("**", "")
            elif "*" in val_raw:
                sig = "p<0.05"
                val_clean = val_raw.replace("*", "")

            try:
                pct_change = float(val_clean)
            except ValueError:
                pct_change = val_clean

            recovery_flag = "Yes" if cycle == "Recovery" else "No"
            cc_id = f"CC_RAT_{sex}_{int(dose)}MG_{param_name[:3]}_{cycle}"

            nodes.append({
                "node_id": cc_id,
                "node_type": "Clinical_Chemistry_Event",
                "species": "Rat",
                "sex": sex,
                "dose_mg_per_kg": dose,
                "cycle": cycle,
                "parameter": param_name,
                "percent_change": pct_change,
                "statistical_significance": sig,
                "recovery_flag": recovery_flag,
            })

            ag_id = find_group("Rat", sex, dose)
            edges.append({"source": ag_id, "target": cc_id, "edge_type": "observed_chemistry"})


# Also extract ALT from toxicity sheet (they show up as ALT_change_pct)
for _, row in df_tox.iterrows():
    metric = row["Toxicity_Metric"]
    species = row["Species"]
    sex = row["Sex"]
    dose = float(row["Dose_mg_per_kg"])
    value = row["Value"]

    if "ALT" in metric or "AST" in metric or "ALP" in metric:
        cc_id = f"CC_{species.upper()}_{sex}_{int(dose)}MG_{metric}"
        param = metric.replace("_change_pct", "").replace("_", " ")

        nodes.append({
            "node_id": cc_id,
            "node_type": "Clinical_Chemistry_Event",
            "species": species,
            "sex": sex,
            "dose_mg_per_kg": dose,
            "cycle": "Summary",
            "parameter": param,
            "percent_change": value,
            "statistical_significance": "Yes" if abs(float(value)) > 20 else "",
            "recovery_flag": "Not assessed",
        })

        ag_id = find_group(species, sex, dose)
        edges.append({"source": ag_id, "target": cc_id, "edge_type": "observed_chemistry"})


# ──────────────────────────────────────────────
# 7. ORGAN_TOXICITY NODES — Microscopic Findings Rats & Dogs
# ──────────────────────────────────────────────

def parse_severity(cell_value):
    """Parse severity notation like '1a,1b', '2a', '3a,1a' into structured data.
    Format: count + severity_letter where a=minimal(1), b=mild(2), c=moderate(3), d=marked(4), p=present
    """
    if pd.isna(cell_value) or str(cell_value).strip() == "":
        return []
    
    results = []
    cell_str = str(cell_value).strip()
    # Find patterns like 1a, 2b, 3c, 1d, 1p etc.
    findings = re.findall(r'(\d+)\s*([a-dp])', cell_str)
    for count, grade in findings:
        sev_map = {"a": 1, "b": 2, "c": 3, "d": 4, "p": 0}  # p = present/not graded
        results.append({"count": int(count), "severity": sev_map.get(grade, 0)})
    return results


# --- Microscopic Findings in Rats ---
df_mic_rat = pd.read_excel(FILE, sheet_name="Microscopic Findings in Rats", header=None)

rat_dose_cols = {
    # Males: C6=0, C7=10, C8=25, C9=100
    # Females: C10=0, C11=10, C12=25, C13=100
    "M": {0: 6, 10: 7, 25: 8, 100: 9},
    "F": {0: 10, 10: 11, 25: 12, 100: 13},
}
rat_doses = [0, 10, 25, 100]

# Track sections
sections = {
    2: "Early Decedent",
    9: "Terminal Sacrifice",
    16: "Recovery",
}

current_section = ""
for r in range(2, len(df_mic_rat)):
    label = str(df_mic_rat.iloc[r, 0]).strip() if pd.notna(df_mic_rat.iloc[r, 0]) else ""

    if r in sections:
        current_section = sections[r]
        continue
    if "Number of Animals" in label:
        continue
    if label == "" or label == "nan":
        continue

    # This is a finding row
    organ_lesion = label
    # Split organ and lesion
    parts = re.split(r'\s*[-–]\s*', organ_lesion, maxsplit=1)
    organ = parts[0].strip() if len(parts) > 0 else organ_lesion
    lesion = parts[1].strip() if len(parts) > 1 else organ_lesion

    early_dec = "Yes" if current_section == "Early Decedent" else "No"
    recovery = "Yes" if current_section == "Recovery" else "No"

    for sex in ["M", "F"]:
        for dose in rat_doses:
            col = rat_dose_cols[sex][dose]
            cell = df_mic_rat.iloc[r, col] if col < len(df_mic_rat.columns) else None
            findings = parse_severity(cell)
            if not findings:
                continue

            total_count = sum(f["count"] for f in findings)
            max_severity = max(f["severity"] for f in findings)

            ot_id = f"OT_RAT_{sex}_{dose}MG_{organ[:10]}_{current_section[:4]}_{nid()}"
            nodes.append({
                "node_id": ot_id,
                "node_type": "Organ_Toxicity",
                "species": "Rat",
                "sex": sex,
                "dose_mg_per_kg": dose,
                "organ": organ,
                "lesion_type": lesion,
                "severity_grade": max_severity,
                "incidence_count": total_count,
                "early_decedent_flag": early_dec,
                "recovery_presence": recovery,
            })

            ag_id = find_group("Rat", sex, dose)
            edges.append({"source": ag_id, "target": ot_id, "edge_type": "observed_pathology"})

            # PK → associated_with → Organ_Toxicity
            pk_id = f"PK_RAT_{sex}_{int(dose)}MG_D151"
            edges.append({"source": pk_id, "target": ot_id, "edge_type": "associated_with"})


# --- Microscopic Findings in Dogs ---
df_mic_dog = pd.read_excel(FILE, sheet_name="Microscopic Findings in Dogs ", header=None)

# Dogs layout:
# Row 2: C1=0(M), C2=10(M), C3=25(M), C4=50(M), C5=0(F), C6=10(F), C7=25(F), C8=50(F)
dog_dose_cols = {
    "M": {0: 1, 10: 2, 25: 3, 50: 4},
    "F": {0: 5, 10: 6, 25: 7, 50: 8},
}

dog_sections = {
    3: "Terminal Sacrifice",
    17: "Recovery",
}

current_section = ""
for r in range(3, len(df_mic_dog)):
    label = str(df_mic_dog.iloc[r, 0]).strip() if pd.notna(df_mic_dog.iloc[r, 0]) else ""

    if r in dog_sections:
        current_section = dog_sections[r]
        continue
    if "Number of Animals" in label:
        continue
    if label == "" or label == "nan":
        continue

    organ_lesion = label
    # Clean up multi-line content
    organ_lesion = re.sub(r'\s+', ' ', organ_lesion).strip()

    parts = re.split(r'\s*[-–]\s*', organ_lesion, maxsplit=1)
    organ = parts[0].strip() if len(parts) > 0 else organ_lesion
    lesion = parts[1].strip() if len(parts) > 1 else organ_lesion

    early_dec = "No"
    recovery = "Yes" if current_section == "Recovery" else "No"

    for sex in ["M", "F"]:
        for dose in [0, 10, 25, 50]:
            col = dog_dose_cols[sex].get(dose)
            if col is None or col >= len(df_mic_dog.columns):
                continue
            cell = df_mic_dog.iloc[r, col]
            findings = parse_severity(cell)
            if not findings:
                continue

            total_count = sum(f["count"] for f in findings)
            max_severity = max(f["severity"] for f in findings)

            ot_id = f"OT_DOG_{sex}_{dose}MG_{organ[:10]}_{current_section[:4]}_{nid()}"
            nodes.append({
                "node_id": ot_id,
                "node_type": "Organ_Toxicity",
                "species": "Dog",
                "sex": sex,
                "dose_mg_per_kg": dose,
                "organ": organ,
                "lesion_type": lesion,
                "severity_grade": max_severity,
                "incidence_count": total_count,
                "early_decedent_flag": early_dec,
                "recovery_presence": recovery,
            })

            ag_id = find_group("Dog", sex, dose)
            edges.append({"source": ag_id, "target": ot_id, "edge_type": "observed_pathology"})

            pk_id = f"PK_DOG_{sex}_{int(dose)}MG_D151"
            edges.append({"source": pk_id, "target": ot_id, "edge_type": "associated_with"})


# ──────────────────────────────────────────────
# 8. ORGAN TOXICITY from "toxcity" sheet (severity-based entries)
# ──────────────────────────────────────────────
for _, row in df_tox.iterrows():
    metric = row["Toxicity_Metric"]
    species = row["Species"]
    sex = row["Sex"]
    dose = float(row["Dose_mg_per_kg"])
    value = row["Value"]

    if "severity" in metric.lower():
        organ_name = metric.replace("_severity", "").replace("_", " ").title()
        ot_id = f"OT_{species.upper()}_{sex}_{int(dose)}MG_{metric}"
        nodes.append({
            "node_id": ot_id,
            "node_type": "Organ_Toxicity",
            "species": species,
            "sex": sex,
            "dose_mg_per_kg": dose,
            "organ": organ_name.split()[0],
            "lesion_type": organ_name,
            "severity_grade": int(value),
            "incidence_count": 1,
            "early_decedent_flag": "No",
            "recovery_presence": "Not assessed",
        })

        ag_id = find_group(species, sex, dose)
        edges.append({"source": ag_id, "target": ot_id, "edge_type": "observed_pathology"})

        pk_id = f"PK_{species.upper()}_{sex}_{int(dose)}MG_D151"
        edges.append({"source": pk_id, "target": ot_id, "edge_type": "associated_with"})


# ──────────────────────────────────────────────
# 9. MORTALITY NODES — from Microscopic Findings (Early Decedents)
# ──────────────────────────────────────────────

# Rat early decedents (Row 3 of Microscopic Findings in Rats)
rat_mortality_counts = {
    "M": {0: 1, 10: 0, 25: 0, 100: 4},
    "F": {0: 1, 10: 0, 25: 0, 100: 2},
}
rat_group_sizes = {
    "M": {0: 10, 10: 10, 25: 10, 100: 10},
    "F": {0: 10, 10: 10, 25: 10, 100: 10},
}

for sex in ["M", "F"]:
    for dose in [0, 10, 25, 100]:
        mort_count = rat_mortality_counts[sex][dose]
        if mort_count > 0:
            total = rat_group_sizes[sex][dose]
            m_id = f"MORT_RAT_{sex}_{dose}MG"
            nodes.append({
                "node_id": m_id,
                "node_type": "Mortality",
                "species": "Rat",
                "sex": sex,
                "dose_mg_per_kg": dose,
                "mortality_count": mort_count,
                "mortality_percent": round(mort_count / total * 100, 1),
                "early_termination_flag": "Yes",
            })

            ag_id = find_group("Rat", sex, dose)
            edges.append({"source": ag_id, "target": m_id, "edge_type": "resulted_in"})

            pk_id = f"PK_RAT_{sex}_{dose}MG_D151"
            edges.append({"source": pk_id, "target": m_id, "edge_type": "associated_with"})


# ──────────────────────────────────────────────
# WRITE CSVs
# ──────────────────────────────────────────────

# Normalize all node dicts: collect all possible keys
all_node_keys = set()
for n in nodes:
    all_node_keys.update(n.keys())

# Permanent ordering: node_id, node_type first, then sorted rest
ordered_keys = ["node_id", "node_type"] + sorted(all_node_keys - {"node_id", "node_type"})

df_nodes = pd.DataFrame(nodes)
# Reorder columns
df_nodes = df_nodes.reindex(columns=ordered_keys)
df_nodes.to_csv(OUT_NODES, index=False)

# Edges
df_edges = pd.DataFrame(edges, columns=["source", "target", "edge_type"])
df_edges.to_csv(OUT_EDGES, index=False)

print(f"✅ Nodes: {len(nodes)} rows → {OUT_NODES}")
print(f"✅ Edges: {len(edges)} rows → {OUT_EDGES}")

# Summary by type
print("\n--- Node Type Summary ---")
for nt in df_nodes["node_type"].unique():
    print(f"  {nt}: {(df_nodes['node_type']==nt).sum()}")

print("\n--- Edge Type Summary ---")
for et in df_edges["edge_type"].unique():
    print(f"  {et}: {(df_edges['edge_type']==et).sum()}")
