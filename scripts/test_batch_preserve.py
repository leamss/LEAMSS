import io, time, sys
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
    ['Amit Kumar',  '15/06/1994', 'Bachelor of Engineering', '8', '261313'],  # ACS
    ['Raj Verma',   '01/01/1990', 'Diploma',                 '7', '351311'],  # TRA
], columns=['Name', 'Date of Birth', 'Qualification', 'Work Experience - Total', 'ANZSCO Code'])
buf = io.BytesIO(); df.to_csv(buf, index=False); buf.seek(0)
bid = s.post(f'{API}/bulk-assessments/validate', headers=H,
             files={'file': ('c.csv', buf, 'text/csv')}).json()['batch_id']
print('batch', bid)

rows = s.get(f'{API}/bulk-assessments/{bid}', headers=H).json()['rows']
raj = next(r for r in rows if r['parsed']['name'] == 'Raj Verma')

# --- Individually edit Raj: custom Translation item + custom skill fee + custom package ---
edit_payload = {
    'anzsco_code': '351311',
    'cost_estimator': {
        'currency': 'INR',
        'items': [
            {'category': 'Government Fees', 'label': 'Visa Fee', 'amount': 4640, 'currency': 'AUD'},
            {'category': 'Skill Assessment', 'label': 'TRA — Skill Assessment', 'amount': 12345, 'currency': 'INR'},
            {'category': 'Translation', 'label': 'NAATI Document Translation', 'amount': 3000, 'currency': 'INR'},
        ],
        'service_packages': [
            {'key': 'smart', 'name': 'LEAMSS Smart Package', 'show': True,
             'professional_fee': 90000, 'discount': 10000, 'gst': 14400, 'total': 94400, 'currency': 'INR'},
        ],
        'total_by_currency': {'AUD': 4640, 'INR': 15345},
        'notes': 'Individually edited',
    },
}
r = s.patch(f'{API}/bulk-assessments/row/{raj["id"]}', headers=H, json=edit_payload)
r.raise_for_status()
raj_after = r.json()['row']
ce = raj_after['cost_estimator']
print('\n--- Raj after INDIVIDUAL edit ---')
print('  items:', [(i['category'], i['label'], i['amount']) for i in ce['items']])
translation_present = any(i['category'] == 'Translation' for i in ce['items'])
skill = next((i for i in ce['items'] if i['category'] == 'Skill Assessment'), None)
print('  Translation item present:', translation_present, '| skill fee:', skill['amount'])

# --- Now apply batch defaults with a DIFFERENT TRA fee (99999) ---
tpl = s.get(f'{API}/bulk-assessments/{bid}/cost-defaults-template', headers=H).json()
skill_fees = {}
for a in tpl['authorities']:
    amt = 99999 if a['key'] == 'tra' else (a['amount'] or 50000)
    skill_fees[a['key']] = {'authority_name': a['authority_name'], 'amount': amt, 'currency': 'INR'}
payload = {
    'common_items': tpl['common_items'],
    'service_packages': tpl['service_packages'],
    'skill_fees': skill_fees,
    'fallback_skill_fee': {'amount': 60000, 'currency': 'INR'},
    'save_to_master': True, 'regenerate': True,
}
r = s.put(f'{API}/bulk-assessments/{bid}/cost-defaults', headers=H, json=payload)
print('\nPUT ->', r.json())

for _ in range(60):
    b = s.get(f'{API}/bulk-assessments/{bid}', headers=H).json()
    if b['batch']['status'] != 'generating':
        break
    time.sleep(2)
rows = b['rows']

print('\n--- AFTER BATCH APPLY ---')
raj = next(r for r in rows if r['parsed']['name'] == 'Raj Verma')
amit = next(r for r in rows if r['parsed']['name'] == 'Amit Kumar')
rce = raj['cost_override'] or raj['cost_estimator']
print('Raj (edited) items:', [(i['category'], i['label'], i['amount']) for i in rce['items']])
raj_skill = next((i for i in rce['items'] if i['category'] == 'Skill Assessment'), None)
raj_trans = next((i for i in rce['items'] if i['category'] == 'Translation'), None)
raj_smart = next((p for p in rce['service_packages'] if p['key'] == 'smart'), None)
print('  -> Translation preserved:', raj_trans is not None and raj_trans['amount'] == 3000)
print('  -> Package preserved (fee 90000):', raj_smart and raj_smart['professional_fee'] == 90000)
print('  -> Skill fee UPDATED to 99999:', raj_skill and raj_skill['amount'] == 99999)

ace = amit['cost_estimator']
amit_skill = next((i for i in ace['items'] if i['category'] == 'Skill Assessment'), None)
print('Amit (not edited) skill fee:', amit_skill['amount'], '(should be ACS batch fee)')

RESULT = (raj_trans and raj_trans['amount'] == 3000 and
          raj_smart and raj_smart['professional_fee'] == 90000 and
          raj_skill and raj_skill['amount'] == 99999)
print('\nPRESERVE-EDITS-ONLY-UPDATE-SKILL:', 'PASS' if RESULT else 'FAIL')
