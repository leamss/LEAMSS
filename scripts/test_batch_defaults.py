import io, time, sys
import requests
import pandas as pd

BASE = open('/app/frontend/.env').read()
API = None
for line in BASE.splitlines():
    if line.startswith('REACT_APP_BACKEND_URL='):
        API = line.split('=', 1)[1].strip() + '/api'
print('API =', API)

s = requests.Session()
r = s.post(f'{API}/auth/login', json={'email': 'admin@leamss.com', 'password': 'Admin@123'})
r.raise_for_status()
tok = r.json()['token']
H = {'Authorization': f'Bearer {tok}'}
print('logged in')

# Build a 4-row CSV spanning ACS / EA / TRA / a body likely missing a fee
df = pd.DataFrame([
    ['Amit Kumar',   '15/06/1994', 'Bachelor of Engineering', '8', '261313'],  # ACS
    ['Neha Sharma',  '20/03/1992', 'Bachelor of Engineering', '9', '233211'],  # EA
    ['Raj Verma',    '01/01/1990', 'Diploma',                 '7', '351311'],  # TRA (Chef)
    ['Sana Khan',    '10/10/1995', 'Master of Nursing',       '5', '254111'],  # AHPRA / midwife
], columns=['Name', 'Date of Birth', 'Qualification', 'Work Experience - Total', 'ANZSCO Code'])
buf = io.BytesIO(); df.to_csv(buf, index=False); buf.seek(0)

r = s.post(f'{API}/bulk-assessments/validate', headers=H,
           files={'file': ('clients.csv', buf, 'text/csv')})
r.raise_for_status()
bid = r.json()['batch_id']
print('batch', bid, 'valid', r.json()['valid'], 'invalid', r.json()['invalid'])

# template
r = s.get(f'{API}/bulk-assessments/{bid}/cost-defaults-template', headers=H); r.raise_for_status()
tpl = r.json()
print('\n--- AUTHORITIES IN BATCH ---')
for a in tpl['authorities']:
    print(f"  {a['key']:>10}  {a['authority_name'][:45]:45}  count={a['count']}  amount={a['amount']}  {a['currency']}  matched={a['matched']}")
print('common items:', [(i['category'], i.get('amount'), i.get('currency')) for i in tpl['common_items']])
print('packages:', [(p['name'], p.get('professional_fee'), p.get('discount'), p.get('gst'), p.get('total')) for p in tpl['service_packages']])

# Fill missing authority fees + tweak a package + set fallback
authorities = tpl['authorities']
skill_fees = {}
for a in authorities:
    amt = a['amount'] if a['amount'] is not None else 45000  # fill missing with 45000
    skill_fees[a['key']] = {'authority_name': a['authority_name'], 'amount': amt, 'currency': a['currency'] or 'INR'}

pkgs = tpl['service_packages']
# change Smart package: fee 120000 disc 24000 gst 17280 => total should be 113280
for p in pkgs:
    if p.get('key') == 'smart':
        p['professional_fee'] = 120000; p['discount'] = 24000; p['gst'] = 17280
        p['total'] = 120000 - 24000 + 17280

payload = {
    'common_items': tpl['common_items'],
    'service_packages': pkgs,
    'skill_fees': skill_fees,
    'fallback_skill_fee': {'amount': 60000, 'currency': 'INR'},
    'notes': 'Batch default test',
    'save_to_master': True,
    'regenerate': True,
}
r = s.put(f'{API}/bulk-assessments/{bid}/cost-defaults', headers=H, json=payload)
r.raise_for_status()
print('\nPUT cost-defaults ->', r.json())

# poll
for _ in range(60):
    r = s.get(f'{API}/bulk-assessments/{bid}', headers=H); r.raise_for_status()
    b = r.json()['batch']
    if b['status'] != 'generating':
        break
    time.sleep(2)
print('batch status:', b['status'], 'generated', b['generated'], 'failed', b['failed'])

rows = r.json()['rows']
print('\n--- PER-CLIENT COST RESULT ---')
ok = True
for row in rows:
    p = row['parsed']; ce = row.get('cost_estimator') or {}
    skill = next((it for it in ce.get('items', []) if it.get('category') == 'Skill Assessment'), None)
    print(f"\n{p['name']} ({p.get('anzsco_code')}) status={row['status']}")
    print(f"   skill: {skill.get('label') if skill else None} = {skill.get('amount') if skill else None} {skill.get('currency') if skill else ''}")
    # package math check
    for pk in ce.get('service_packages', []):
        fee = pk.get('professional_fee') or 0; disc = pk.get('discount') or 0; gst = pk.get('gst') or 0; tot = pk.get('total') or 0
        calc = max(0, fee - disc + gst)
        flag = 'OK' if abs(calc - tot) < 1 else 'MISMATCH!!'
        if flag != 'OK': ok = False
        print(f"   pkg {pk.get('key'):>10}: fee={fee} disc={disc} gst={gst} total={tot} (fee-disc+gst={calc}) {flag}")

# check fee master persisted
print('\n--- FEE MASTER OVERRIDES ---')
import asyncio
sys.path.insert(0, '/app/backend')
from core.database import db
async def show():
    async for d in db['skill_assessment_fee_overrides'].find({}, {'_id': 0}):
        print('  ', d.get('key'), d.get('authority_name'), d.get('amount'), d.get('currency'))
asyncio.get_event_loop().run_until_complete(show())

print('\nPACKAGE MATH CONSISTENT:', ok)
