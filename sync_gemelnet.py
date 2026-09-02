import os
import requests
import json

SUPABASE_URL = "https://geamksanxntfeyzlqdrs.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# 1. Fetch all funds with a track_id from Supabase
res = requests.get(f"{SUPABASE_URL}/rest/v1/funds?select=id,track_id,name&track_id=not.is.null", headers=headers)
funds = res.json()

if not funds or not isinstance(funds, list):
    print("No funds with track_id found or error fetching funds.")
    exit(0)

print(f"Found {len(funds)} funds with track_id.")

# 2. Query data.gov.il GemelNet API (Active 2024+ datastore resource)
GEMELNET_API = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_ID = "a30dcbea-a1d2-482c-ae29-8f781f5025fb"

for fund in funds:
    track_id = str(fund.get('track_id', '')).strip()
    if not track_id:
        continue

    params = {
        "resource_id": RESOURCE_ID,
        "q": track_id,
        "limit": 20
    }

    try:
        api_res = requests.get(GEMELNET_API, params=params, timeout=15).json()
        records = api_res.get("result", {}).get("records", [])

        matching = [
            r for r in records 
            if str(r.get("FUND_ID", "")).strip() == track_id 
            or str(r.get("SHM_KUPA", "")).strip() == track_id 
            or str(r.get("KUPA_ID", "")).strip() == track_id
        ]
        
        if matching:
            latest = matching[0]
            monthly_return = float(latest.get("TSUA_HODSHIT", 0))
            period = str(latest.get("REPORT_PERIOD", ""))

            update_payload = {
                "gemelnet_return_monthly": monthly_return,
                "gemelnet_period": period
            }
            patch_res = requests.patch(f"{SUPABASE_URL}/rest/v1/funds?id=eq.{fund['id']}", headers=headers, json=update_payload)
            print(f"Updated {fund['name']} (Track {track_id}): Return {monthly_return}%, Period {period}")
        else:
            print(f"No GemelNet record found for track {track_id}")
    except Exception as e:
        print(f"Error fetching GemelNet for {track_id}: {e}")
