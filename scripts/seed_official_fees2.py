"""Second batch — remaining niche AU assessing authorities with confirmed official fees.
cmba (Chinese Medicine, bundled with AHPRA registration — no fixed skills-assessment fee) and
isnsw (Surveyors NSW — no published figure) are intentionally left blank for manual entry."""
import requests

API = None
for line in open('/app/frontend/.env').read().splitlines():
    if line.startswith('REACT_APP_BACKEND_URL='):
        API = line.split('=', 1)[1].strip() + '/api'

s = requests.Session()
tok = s.post(f'{API}/auth/login', json={'email': 'admin@leamss.com', 'password': 'Admin@123'}).json()['token']
H = {'Authorization': f'Bearer {tok}'}
cur = {a['key']: a['authority_name'] for a in s.get(f'{API}/fee-master', headers=H).json()['authorities']}

FEES = {
    'communityworkaustralia': [("Skills Assessment (general skilled visa)", 965, "AUD")],
    'amsa':   [("Assessment of Overseas Qualifications (migration)", 472, "AUD")],
    'casa':   [("Skills Assessment for Migration (Fee Code 24.8)", 100, "AUD")],
    'aopa':   [("Stage 1 — Skilled Migration Application + Eligibility Review", 802, "AUD"),
               ("Stage 2 — Portfolio of Evidence", 1447.60, "AUD")],
    'anzsnm': [("Overseas Qualification Skills Assessment", 550, "AUD")],
    'ccea':   [("Stage 1 — Desktop Audit (Form A)", 884, "AUD")],
    'aoac':   [("Stage 1 — Initial Assessment", 565.50, "AUD")],
}

for key, comps in FEES.items():
    payload = {'authority_name': cur.get(key, key),
               'components': [{'label': l, 'amount': a, 'currency': c} for (l, a, c) in comps]}
    r = s.put(f'{API}/fee-master/{key}', headers=H, json=payload)
    print(('OK  ' if r.status_code == 200 else f'FAIL {r.status_code} ') + key,
          r.json().get('total_by_currency') if r.status_code == 200 else r.text[:100])

d = s.get(f'{API}/fee-master', headers=H).json()
print(f"\nFee Master: {d['configured']} configured / {d['missing']} missing (of {d['total']})")
print("Still missing (manual entry):", [a['key'] for a in d['authorities'] if not a['is_set']])
