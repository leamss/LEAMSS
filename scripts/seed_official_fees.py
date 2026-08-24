"""Populate the Skill Assessment Fee Master with official 2026 assessing-authority fees (AU).
Sources: official authority websites (VETASSESS, TRA, EA, ACS, ANMAC, AITSL, CAANZ, AMC,
APC, ADC, APS, CPA Australia, IML/AIM, ASMIRT, NAATI, ACECQA, AIMS, SPA, Dietitians,
AIQS, OCANZ, AACA). All AUD, indicative base/offshore skill-assessment fees.
Authorities without a confirmed official figure are left blank for the consultant to fill."""
import requests

API = None
for line in open('/app/frontend/.env').read().splitlines():
    if line.startswith('REACT_APP_BACKEND_URL='):
        API = line.split('=', 1)[1].strip() + '/api'

s = requests.Session()
tok = s.post(f'{API}/auth/login', json={'email': 'admin@leamss.com', 'password': 'Admin@123'}).json()['token']
H = {'Authorization': f'Bearer {tok}'}

# names from the live catalog
cur = {a['key']: a['authority_name'] for a in s.get(f'{API}/fee-master', headers=H).json()['authorities']}

FEES = {
    'vetassess':  [("Full Skills Assessment (offshore)", 1146, "AUD")],
    'tra':        [("Documentary Evidence", 1120, "AUD"),
                   ("Technical Interview (Pathway 1)", 2000, "AUD"),
                   ("Practical Assessment", 2200, "AUD")],
    'medba':      [("AMC Assessment (MCQ authorisation)", 2920, "AUD")],
    'ea':         [("Migration Skills Assessment (CDR, incl GST)", 1034, "AUD")],
    'acs':        [("General Skills Assessment", 1498, "AUD")],
    'anmac':      [("Modified Skills Assessment", 395, "AUD")],
    'aitsl':      [("Teacher Skills Assessment", 1154, "AUD")],
    'iml':        [("Migration Skills Assessment (offshore)", 788, "AUD")],
    'cpa':        [("Combined Assessment (Qual + Skilled Employment)", 625, "AUD")],  # CAANZ
    'aps':        [("Skilled Migration Assessment (offshore)", 1335, "AUD")],
    'aim':        [("Migration Skills Assessment (offshore)", 788, "AUD")],
    'asmirt':     [("Skilled Migration Assessment (offshore)", 1074, "AUD")],
    'naati':      [("Migration Skills Assessment", 500, "AUD")],
    'acecqa':     [("Migration Skills Assessment", 1100, "AUD")],
    'adc':        [("Initial Assessment", 647, "AUD")],
    'apharmc':    [("Eligibility Check", 810, "AUD"),
                   ("Skills Assessment Outcome (visa)", 300, "AUD")],
    'aims':       [("Skills Assessment (offshore)", 900, "AUD")],
    'spa':        [("Skills Assessment (MRA pathway)", 825, "AUD")],
    'cpaa':       [("Combined Assessment (offshore)", 564, "AUD")],  # CPA Australia
    'daa':        [("Skills Migration Assessment (visa)", 305, "AUD")],
    'aiqs':       [("Skills Assessment (Pathways 1-4)", 655, "AUD")],
    'ocanz':      [("Qualification Assessment (Form 1)", 447, "AUD")],
    'aaca':       [("Overseas Qualifications Assessment", 4900, "AUD")],
}

ok = 0
for key, comps in FEES.items():
    payload = {
        'authority_name': cur.get(key, key),
        'components': [{'label': l, 'amount': a, 'currency': c} for (l, a, c) in comps],
    }
    r = s.put(f'{API}/fee-master/{key}', headers=H, json=payload)
    if r.status_code == 200:
        ok += 1
        print(f"  OK  {key:<14} {r.json()['total_by_currency']}")
    else:
        print(f"  FAIL {key}: {r.status_code} {r.text[:120]}")

print(f"\nPopulated {ok}/{len(FEES)} authorities.")
d = s.get(f'{API}/fee-master', headers=H).json()
print(f"Fee Master now: {d['configured']} configured / {d['missing']} missing (of {d['total']})")
print("Still missing:", [a['key'] for a in d['authorities'] if not a['is_set']])
