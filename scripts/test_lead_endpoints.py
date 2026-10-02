import requests
import json

urls = [
    'https://app.leamss.com/api/public-atlas/lead',
    'https://api.leamss.com/api/public-atlas/lead'
]

payload = {
    'name': 'Live Verification Lead',
    'email': 'verify_test@leamss.com',
    'phone': '+61400111222',
    'country_of_interest': 'AU',
    'atlas_code': '111111',
    'atlas_title': 'Chief Executive or Managing Director',
    'source': 'public_atlas'
}

for u in urls:
    try:
        opt = requests.options(u, headers={'Origin': 'https://leamss.com', 'Access-Control-Request-Method': 'POST'})
        cors_origin = opt.headers.get('access-control-allow-origin')
        print(f"OPTIONS {u} -> Status: {opt.status_code}, CORS: {cors_origin}")
        
        res = requests.post(u, json=payload, headers={'Origin': 'https://leamss.com', 'Content-Type': 'application/json'})
        print(f"POST {u} -> Status: {res.status_code}, Response: {res.text}\n")
    except Exception as e:
        print(f"Error testing {u}: {e}\n")
