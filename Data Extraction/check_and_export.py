"""
Quick coverage check + Excel export for output_v2.json
Run with: python check_and_export.py
"""
import json, sys, os
sys.path.insert(0, 'src')

with open('output_v2.json', encoding='utf-8') as f:
    data = json.load(f)

print('=== DATA COVERAGE ===')
for top_key, top_val in data.items():
    if isinstance(top_val, dict):
        nulls = sum(1 for v in top_val.values() if v is None or v == [] or v == '')
        total = len(top_val)
        pct = int(100*(total-nulls)/total) if total else 0
        bar = '#' * (pct//10) + '.' * (10-pct//10)
        print(f'[{bar}] {pct:3d}%  {top_key}: {total-nulls}/{total} fields')
    elif isinstance(top_val, list):
        print(f'[list]       {top_key}: {len(top_val)} items')
    else:
        val_str = str(top_val)[:60] if top_val else '<null>'
        print(f'             {top_key}: {val_str}')

print()
print('=== SPOT CHECKS ===')
print('Population n:', data.get('population_characteristics', {}).get('sample_size_n'))
print('Disease:', data.get('population_characteristics', {}).get('disease_indication'))
print('ORR:', data.get('efficacy_outcomes', {}).get('objective_response_rate') or
              data.get('efficacy_outcomes', {}).get('overall_response_rate_percent'))
print('AE count:', len(data.get('adverse_events') or data.get('safety_data', {}).get('adverse_events', [])))
print('Animal species:', data.get('preclinical_toxicology', {}).get('toxicity_species'))
print('Formulation type:', data.get('formulation_stability', {}).get('formulation_type'))
print('DDI drugs:', data.get('drug_interactions', {}).get('interacting_drugs'))
print('Eligibility ANC:', data.get('eligibility_criteria', {}).get('anc_threshold'))

# Export Excel - rename in case file is locked
output_excel = 'output_v2_consolidated_new.xlsx'
from consolidated_excel_writer import ConsolidatedExcelWriter
writer = ConsolidatedExcelWriter('output_v2.json')
# Override output filename
import openpyxl
from pathlib import Path
writer.json_path = Path('output_v2.json')

# Monkey-patch to use new filename
original_write = writer.write_excel
def write_excel_patched():
    result = original_write()
    return result

result = writer.write_excel()
print()
print('Excel:', result)
