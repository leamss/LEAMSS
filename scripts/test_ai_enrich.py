import io, time, subprocess, requests
import pandas as pd

API = None
for line in open('/app/frontend/.env').read().splitlines():
    if line.startswith('REACT_APP_BACKEND_URL='):
        API = line.split('=', 1)[1].strip() + '/api'

s = requests.Session()
tok = s.post(f'{API}/auth/login', json={'email': 'admin@leamss.com', 'password': 'Admin@123'}).json()['token']
H = {'Authorization': f'Bearer {tok}'}

RESUME_URL = "http://localhost:9099/john_chef.txt"

# CSV: one row WITHOUT anzsco but WITH resume link; one row WITH anzsco (should skip AI)
df = pd.DataFrame([
    ['Rajesh Kumar', '', '', '', '', '', '', 'Married', '', RESUME_URL, ''],
    ['Amit Direct', 'a@x.com', '', '15/06/1994', 'Bachelor of Engineering', '8', 'Male', 'Single', '261313', '', ''],
], columns=['Name', 'Email', 'Mobile Number', 'Date of Birth', 'Qualification',
            'Work Experience - Total', 'Gender', 'Marital Status', 'ANZSCO Code', 'Resume Link', 'Date'])
buf = io.BytesIO(); df.to_csv(buf, index=False); buf.seek(0)
v = s.post(f'{API}/bulk-assessments/validate', headers=H, files={'file': ('t.csv', buf, 'text/csv')}).json()
bid = v['batch_id']
print(f"validate -> total {v['total']} valid {v['valid']} needs_ai {v['needs_ai']} invalid {v['invalid']}")
assert v['needs_ai'] == 1, "Rajesh (no anzsco + resume) should be needs_ai"
assert v['valid'] == 1, "Amit (has anzsco) should be valid"

# kick off AI enrich
r = s.post(f'{API}/bulk-assessments/{bid}/ai-enrich', headers=H)
print("ai-enrich ->", r.status_code, r.json())

for _ in range(40):
    b = s.get(f'{API}/bulk-assessments/{bid}', headers=H).json()['batch']
    if b['status'] != 'enriching':
        break
    time.sleep(2)
print(f"batch status {b['status']} valid {b.get('valid')} needs_ai {b.get('needs_ai')}")

rows = s.get(f'{API}/bulk-assessments/{bid}', headers=H).json()['rows']
for row in rows:
    p = row['parsed']
    print(f"\n{p['name']}: status={row['status']} code={p.get('anzsco_code')} title={p.get('occupation_title')}")
    print(f"   source={p.get('anzsco_source')} conf={p.get('ai_confidence')} filled={p.get('ai_filled_fields')}")
    print(f"   age={p.get('age')} qual={p.get('qualification')} exp={p.get('experience_total')} eng_overall={(p.get('english') or {}).get('overall')}")
    if row.get('ai_error'): print("   ai_error:", row['ai_error'])
    if p.get('ai_alternatives'): print("   alts:", [(a['code'],a.get('title')) for a in p['ai_alternatives']])

rk = next(r for r in rows if r['parsed']['name'] == 'Rajesh Kumar')
ok = (rk['status'] == 'valid' and rk['parsed'].get('anzsco_source') == 'ai'
      and rk['parsed'].get('anzsco_code') and rk['parsed'].get('age') == 36
      and rk['parsed'].get('qualification') == 'diploma'
      and rk['parsed'].get('experience_total'))
print("\nAI ENRICH (chef → code + filled age/qual/exp):", 'PASS' if ok else 'FAIL')

import asyncio, sys
sys.path.insert(0, '/app/backend')
from core.database import db
async def cl():
    await db['bulk_rows'].delete_many({'batch_id': bid}); await db['bulk_batches'].delete_one({'id': bid})
asyncio.get_event_loop().run_until_complete(cl())
print('cleaned up')
