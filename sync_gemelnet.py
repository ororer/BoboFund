import os
import requests
import json

SUPABASE_URL = "https://geamksanxntfeyzlqdrs.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_KEY:
    print("CRITICAL: SUPABASE_ANON_KEY is missing.")
    exit(1)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# 1. Fetch funds from Supabase
res = requests.get(f"{SUPABASE_URL}/rest/v1/funds?select=id,track_id,name,vault_id&vault_id=eq.bobo-fund", headers=headers)
if res.status_code != 200:
    print(f"Error fetching funds: {res.status_code} {res.text}")
    exit(1)

funds = [f for f in res.json() if f.get("track_id") and str(f.get("track_id")).strip()]
print(f"Funds with track_id to sync: {len(funds)}")

# 2. Sync from data.gov.il GemelNet API
GEMELNET_API = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_ID = "a30dcbea-a1d2-482c-ae29-8f781f5025fb"

for fund in funds:
    track_id = str(fund.get("track_id")).strip()
    print(f"\nProcessing {fund.get('name')} (Track ID: {track_id})")

    params = {
        "resource_id": RESOURCE_ID,
        "q": track_id,
        "limit": 50
    }

    try:
        api_res = requests.get(GEMELNET_API, params=params, timeout=20).json()
        records = api_res.get("result", {}).get("records", [])

        # Filter strictly by FUND_ID
        matching = [r for r in records if str(r.get("FUND_ID", "")).strip() == track_id]

        if matching:
            # Sort by REPORT_PERIOD descending to get the newest month
            matching.sort(key=lambda x: str(x.get("REPORT_PERIOD", "")), reverse=True)
            latest = matching[0]

            monthly_yield = float(latest.get("MONTHLY_YIELD") or 0.0)
            period = str(latest.get("REPORT_PERIOD", "")).strip()

            update_payload = {
                "gemelnet_return_monthly": monthly_yield,
                "gemelnet_period": period
            }

            patch_res = requests.patch(
                f"{SUPABASE_URL}/rest/v1/funds?id=eq.{fund['id']}",
                headers=headers,
                json=update_payload
            )

            if patch_res.status_code in [200, 204]:
                print(f"SUCCESS: Updated {fund['name']} -> MONTHLY_YIELD: {monthly_yield}%, REPORT_PERIOD: {period}")
            else:
                print(f"DB Error on update: {patch_res.status_code} {patch_res.text}")
        else:
            print(f"No records matching FUND_ID {track_id}")
    except Exception as e:
        print(f"Error syncing track {track_id}: {e}")
