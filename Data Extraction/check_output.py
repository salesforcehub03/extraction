import sys, json
sys.stdout.reconfigure(encoding='utf-8')
with open('output_v2.json', encoding='utf-8') as f:
    d = json.load(f)

print('=== CLINICAL STUDIES ROWS ===')
cs = d.get('clinical_studies', [])
print(f'Total rows: {len(cs)}')
for r in cs[:6]:
    print(f"  {r.get('study_id')} | {r.get('patient_group')} | N={r.get('n_patients')} | ORR={r.get('orr')} | CR={r.get('cr_rate')} | PFS={r.get('median_pfs')}")

print()
print('=== ANIMAL STUDY ROWS ===')
tox = d.get('preclinical_toxicology', {})
studies = tox.get('animal_studies', [])
print(f'Total rows: {len(studies)}')
for r in studies[:6]:
    print(f"  {r.get('species')} | {r.get('gender')} | {r.get('study_type')} | Dose={r.get('dose_level')} | NOAEL={r.get('noael')} | Organs={r.get('target_organs')}")

print()
print('=== PK DATA POINT ROWS ===')
pk = d.get('pharmacokinetics', {})
pk_pts = pk.get('pk_data_points', [])
print(f'Total rows: {len(pk_pts)}')
for r in pk_pts[:6]:
    print(f"  {r.get('species')} | dose={r.get('dose_level')} | Cmax={r.get('cmax')} | AUC={r.get('auc')} | t1/2={r.get('t_half')}")
