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

# 1) Fee Master list
r = s.get(f'{API}/fee-master', headers=H); r.raise_for_status()
d = r.json()
print(f"Fee Master: {d['total']} authorities, {d['configured']} configured, {d['missing']} missing")
tra = next((a for a in d['authorities'] if a['key'] == 'tra'), None)
acs = next((a for a in d['authorities'] if a['key'] == 'acs'), None)
print('  TRA before:', tra['authority_name'], tra['components'], 'count', tra['occupation_count'])
print('  ACS before:', acs['components'])

# 2) Save TRA multi-component (Document Evidence + Technical Interview + Practical Interview)
tra_comps = [
    {'label': 'Document Evidence', 'amount': 30000, 'currency': 'INR'},
    {'label': 'Technical Interview', 'amount': 25000, 'currency': 'INR'},
    {'label': 'Practical Assessment', 'amount': 340000, 'currency': 'INR'},
]
r = s.put(f'{API}/fee-master/tra', headers=H,
          json={'authority_name': tra['authority_name'], 'components': tra_comps})
r.raise_for_status()
print('\nSaved TRA ->', r.json()['total_by_currency'], '(sum should be 395000 INR)')

# 3) Verify persisted
r = s.get(f'{API}/fee-master', headers=H).json()
tra2 = next(a for a in r['authorities'] if a['key'] == 'tra')
print('TRA after save:', [(c['label'], c['amount']) for c in tra2['components']], 'set=', tra2['is_set'])

# 4) Generate a batch with a TRA occupation (351311 Chef) + ACS (261313)
df = pd.DataFrame([
    ['Amit Kumar', '15/06/1994', 'Bachelor of Engineering', '8', '261313'],  # ACS single-comp
    ['Raj Verma',  '01/01/1990', 'Diploma',                 '7', '351311'],  # TRA multi-comp
], columns=['Name', 'Date of Birth', 'Qualification', 'Work Experience - Total', 'ANZSCO Code'])
buf = io.BytesIO(); df.to_csv(buf, index=False); buf.seek(0)
bid = s.post(f'{API}/bulk-assessments/validate', headers=H, files={'file': ('fm.csv', buf, 'text/csv')}).json()['batch_id']
s.post(f'{API}/bulk-assessments/{bid}/generate', headers=H)
for _ in range(60):
    b = s.get(f'{API}/bulk-assessments/{bid}', headers=H).json()
    if b['batch']['status'] != 'generating':
        break
    time.sleep(2)
print('\nbatch status:', b['batch']['status'])

for row in b['rows']:
    p = row['parsed']; ce = row.get('cost_estimator') or {}
    skill = [it for it in ce.get('items', []) if it.get('category') == 'Skill Assessment']
    print(f"\n{p['name']} ({p['anzsco_code']}):")
    for sl in skill:
        print(f"    - {sl['label']} = {sl['amount']} {sl['currency']}")

raj = next(r for r in b['rows'] if r['parsed']['name'] == 'Raj Verma')
raj_skill = [it for it in raj['cost_estimator']['items'] if it['category'] == 'Skill Assessment']
tra_ok = len(raj_skill) == 3 and sum(x['amount'] for x in raj_skill) == 395000
print('\nTRA multi-component in report (3 lines, total 395000):', 'PASS' if tra_ok else 'FAIL')

# cleanup
import asyncio, sys
sys.path.insert(0, '/app/backend')
from core.database import db
async def cleanup():
    await db['bulk_rows'].delete_many({'batch_id': bid})
    await db['bulk_batches'].delete_one({'id': bid})
asyncio.get_event_loop().run_until_complete(cleanup())
print('cleaned up test batch')
