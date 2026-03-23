# Validation & Professional Output - Deep Dive

## Overview

The final stage of the pipeline transforms the "Raw JSON" into a standardized, polished product. This involves two sub-steps: **Standardization** (making the data uniform) and **Structured Writing** (creating the Excel workbook).

---

## 1. The Validator: Data Grooming

**File:** [`src/validator.py`](file:///d:/AViiD/Team%201/src/validator.py)

AI extraction can be messy. Two chunks might report the same percentage differently (e.g., "25.6%" vs "25.6 percent"). The Validator fixes this.

### Standardization Rules

1.  **Percentage Normalization**:
    Ensures all percentage fields end with `%`.
    - `25.6` → `25.6%`
    - `25.6 percent` → `25.6%`

2.  **Date Consolidation**:
    Standardizes date ranges for study periods.
    - `14-Apr-2009 to 11-Apr-2013` → `14-Apr-2009 - 11-Apr-2013`

3.  **Null Handling**:
    If a field is found across multiple chunks and one is "null" while the other is "N/A", the validator converts both to Python `None` for clean Excel output.

---

## 2. Multi-Sheet Excel Generation

**File:** [`src/csv_writer.py`](file:///d:/AViiD/Team%201/src/csv_writer.py)

Instead of a single, massive CSV file with 50+ columns (which is impossible for humans to read), the system creates a **Structured Excel Workbook**.

### Why Excel over CSV?
- **Readability**: Sheets act as tabs (Efficacy, Safety, PK).
- **Data Types**: Preserves column headers and data alignment.
- **Portability**: One file contains the entire trial history.

### How the Writer Works (`StructuredExcelWriter`)

It uses the `openpyxl` library to map the JSON schema to Excel spreadsheets.

#### 2.1 Mapping JSON to Sheets
Each top-level key in our JSON extraction is assigned a dedicated sheet:

| Sheet Name | Data Source | Row Strategy |
| :--- | :--- | :--- |
| **Study Metadata** | `study_metadata` | Key-Value pairs (Field/Value) |
| **Efficacy** | `efficacy_outcomes` | Vertical metrics list |
| **Pharmacokinetics**| `pharmacokinetics` | Vertical parameter list |
| **Demographics** | `baseline_demographics`| Grid/Table (N, Age, Gender) |
| **Detailed Safety** | `detailed_safety_tables` | Flattened list of all events |

#### 2.2 Table Flattening Logic
The "Detailed Safety" sheet is the most complex. The JSON is deeply nested:
`Group -> Table Type -> Event List -> Event N/%`.

**The Writer flattens this into a flat grid:**
```csv
Study ID | Table Type | Event Term | All Grades % | Grade 3-4 %
CLN-19   | TEAE       | Nausea     | 42.6%        | 0.8%
CLN-19   | SAE        | Pneumonia  | 7.8%         | 1.6%
```

---

## 3. The Final Result

By the time the pipeline finishing running, you have two assets:

1.  **`belino_full_clinical_data.json`**:
    Perfect for developers or databases. It contains every nested detail and raw extraction metadata.

2.  **`belino_full_clinical_data.xlsx`** (11 Sheets):
    Perfect for Medical Reviewers. It presents the drug's safety and efficacy profile in a format that looks like it was manually compiled by a clinical data manager.

---

## Summary of the Full System Logic

| Stage | Goal | Tool |
| :--- | :--- | :--- |
| **1. Parsing** | Read the PDF accurately | Azure Document Intelligence |
| **2. Filtering** | Only keep relevant medical sections | Python Regex & Heuristics |
| **3. Extracting**| Find the data points at scale | Gemini 2.0 Flash (37x Parallel) |
| **4. Finishing** | Verify and format for humans | Structured Validator & Excel Writer |

---

**This concludes the in-depth system explanation. Ready to process another document or make more tweaks?**
