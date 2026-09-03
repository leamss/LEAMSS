import io, time
import requests
import pandas as pd

API = None
for line in open('/app/frontend/.env').read().splitlines():
    if line.startswith('REACT_APP_BACKEND_URL='):
        API = line.split('=', 1)[1].strip() + '/api'

s = requests.Session()
tok = s.post(f'{API}/auth/login', json={'email': 'admin@leamss.com', 'password': 'Admin@123'}).json()['token']
H = {'Authorization': f'Bearer {tok}'}

df = pd.DataFrame([
    ['Single Sam',   '15/06/1994', 'Bachelor of Engineering', '8', 'Single',  '261313'],
    ['Married Meena', '15/06/1994', 'Bachelor of Engineering', '8', 'Married', '261313'],
], columns=['Name', 'Date of Birth', 'Qualification', 'Work Experience - Total', 'Marital Status', 'ANZSCO Code'])
buf = io.BytesIO(); df.to_csv(buf, index=False); buf.seek(0)
bid = s.post(f'{API}/bulk-assessments/validate', headers=H, files={'file': ('pf.csv', buf, 'text/csv')}).json()['batch_id']
s.post(f'{API}/bulk-assessments/{bid}/generate', headers=H)
for _ in range(40):
    b = s.get(f'{API}/bulk-assessments/{bid}', headers=H).json()
    if b['batch']['status'] != 'generating': break
    time.sleep(2)

def pts(name):
    r = s.get(f'{API}/bulk-assessments/{bid}', headers=H).json()
    row = next(x for x in r['rows'] if x['parsed']['name'] == name)
    return row, (row.get('points') or {}).get('189')

sam, sam_base = pts('Single Sam')
meena, meena_base = pts('Married Meena')
print(f"DRAFT: Single Sam 189={sam_base} | Married Meena 189={meena_base}")
print(f"  -> Single gets +10 auto vs Married-no-partner: diff = {sam_base - meena_base} (expect 10)")

# Edit Meena: skilled partner (+10) + STEM (+10) + NAATI (+5)
def edit(row_id, **kw):
    r = s.patch(f'{API}/bulk-assessments/row/{row_id}', headers=H, json=kw)
    r.raise_for_status()
    return (r.json()['row'].get('points') or {}).get('189')

p_none = edit(meena['id'], partner_skill='none')
print(f"\nMeena partner=none: 189={p_none}")
p_skilled = edit(meena['id'], partner_skill='skilled')
print(f"Meena partner=skilled: 189={p_skilled}  (expect +10 over none => {p_none+10})")
p_eng = edit(meena['id'], partner_skill='english_only')
print(f"Meena partner=english_only: 189={p_eng}  (expect +5 over none => {p_none+5})")
p_pr = edit(meena['id'], partner_skill='pr_citizen')
print(f"Meena partner=pr_citizen: 189={p_pr}  (expect +10 over none => {p_none+10})")

# bonus factors on Sam (single, base includes +10 partner)
b_stem = edit(sam['id'], au_extras={'specialist_education_stem_au': True})
print(f"\nSam +STEM: 189={b_stem}  (expect +10 over {sam_base} => {sam_base+10})")
b_all = edit(sam['id'], au_extras={'specialist_education_stem_au': True, 'naati_accredited': True, 'australian_study_2_years': True})
print(f"Sam +STEM+NAATI+Study: 189={b_all}  (expect +10+5+5 over {sam_base} => {sam_base+20})")
b_off = edit(sam['id'], au_extras={'specialist_education_stem_au': False, 'naati_accredited': False, 'australian_study_2_years': False})
print(f"Sam all bonus OFF: 189={b_off}  (expect back to {sam_base})")

ok = (sam_base - meena_base == 10
      and p_skilled == p_none + 10
      and p_eng == p_none + 5
      and p_pr == p_none + 10
      and b_stem == sam_base + 10
      and b_all == sam_base + 20
      and b_off == sam_base)
print('\nALL PARTNER + BONUS CHECKS:', 'PASS' if ok else 'FAIL')

import asyncio, sys
sys.path.insert(0, '/app/backend')
from core.database import db
async def cleanup():
    await db['bulk_rows'].delete_many({'batch_id': bid}); await db['bulk_batches'].delete_one({'id': bid})
asyncio.get_event_loop().run_until_complete(cleanup())
print('cleaned up')
