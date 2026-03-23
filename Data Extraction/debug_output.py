import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('output_v2.json', encoding='utf-8') as f:
    d = json.load(f)

# Print actual values for low-coverage sections
def print_section(label, sec):
    print(f'\n=== {label} ===')
    if isinstance(sec, dict):
        for k, v in sec.items():
            if k == 'semantic_relationships':
                continue
            print(f'  {k}: {repr(v)[:120]}')
    else:
        print(f'  {repr(sec)[:200]}')

print_section('STUDY METADATA', d.get('study_metadata', {}))
print_section('POPULATION CHARACTERISTICS', d.get('population_characteristics', {}))
print_section('EFFICACY OUTCOMES', d.get('efficacy_outcomes', {}))
print_section('PHARMACOKINETICS (top-level)', {k: v for k, v in d.get('pharmacokinetics', {}).items() if k not in ['pk_data_points', 'semantic_relationships']})
print_section('CLINICAL STUDIES DATA', d.get('clinical_studies_data', {}))
print_section('DOSING ADMIN', {k: v for k, v in d.get('dosing_administration', {}).items() if k != 'semantic_relationships'})
print_section('ELIGIBILITY', d.get('eligibility_criteria', {}))
print_section('SPECIAL POPS', d.get('special_populations', {}))

# Check clinical_studies
csd = d.get('clinical_studies_data', {})
cs = csd.get('clinical_studies', [])
print(f'\n=== CLINICAL STUDY ROWS ({len(cs)} found) ===')
for r in cs[:3]:
    print(f'  {r}')

# Check if clinical study data ended up in study_metadata
sm = d.get('study_metadata', {})
print(f'\n=== STUDY_METADATA clinical_studies? {sm.get("clinical_studies")} ===')
