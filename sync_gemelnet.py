import os
import requests
import json

SUPABASE_URL = "https://geamksanxntfeyzlqdrs.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

if not SUPABASE_KEY:
    print("CRITICAL: SUPABASE_ANON_KEY is not defined in environment variables.")
    exit(1)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# 1. Fetch all funds for the vault
res = requests.get(f"{SUPABASE_URL}/rest/v1/funds?select=id,track_id,name,vault_id&vault_id=eq.bobo-fund", headers=headers)

if res.status_code != 200:
    print(f"ERROR: Failed to fetch funds from Supabase. Status: {res.status_code}, Body: {res.text}")
    exit(1)

all_funds = res.json()
funds = [f for f in all_funds if f.get("track_id") and str(f.get("track_id")).strip()]

print(f"Total funds found in vault: {len(all_funds)}. Funds with track_id: {len(funds)}.")

if not funds:
    print("No funds to sync. Exiting.")
    exit(0)

# 2. Query data.gov.il GemelNet API
GEMELNET_API = "https://data.gov.il/api/3/action/datastore_search"
RESOURCE_ID = "a30dcbea-a1d2-482c-ae29-8f781f5025fb"

for fund in funds:
    track_id = str(fund.get("track_id", "")).strip()
    print(f"\n--- Checking {fund.get('name')} (Track: {track_id}) ---")

    params = {
        "resource_id": RESOURCE_ID,
        "q": track_id,
        "limit": 50
    }

    try:
        api_res = requests.get(GEMELNET_API, params=params, timeout=20).json()
        records = api_res.get("result", {}).get("records", [])

        matching = [
            r for r in records
            if str(r.get("FUND_ID", "")).strip() == track_id
            or str(r.get("SHM_KUPA", "")).strip() == track_id
            or str(r.get("KUPA_ID", "")).strip() == track_id
        ]

        if matching:
            # Sort descending by REPORT_PERIOD to get the latest reported month
            matching.sort(key=lambda x: str(x.get("REPORT_PERIOD", "")), reverse=True)
            latest = matching[0]

            monthly_return = float(latest.get("TSUA_HODSHIT") or latest.get("TSUA_MITZTABERET_LETKUFA") or 0)
            period = str(latest.get("REPORT_PERIOD", "")).strip()

            update_payload = {
                "gemelnet_return_monthly": monthly_return,
                "gemelnet_period": period
            }

            patch_res = requests.patch(
                f"{SUPABASE_URL}/rest/v1/funds?id=eq.{fund['id']}",
                headers=headers,
                json=update_payload
            )

            if patch_res.status_code in [200, 204]:
                print(f" SUCCESS: Updated return to {monthly_return}% (Period: {period})")
            else:
                print(f" FAILED TO UPDATE DB: Status {patch_res.status_code}, Body: {patch_res.text}")
        else:
            print(f" No matching records found in GemelNet for track {track_id}")
    except Exception as e:
        print(f" Exception while syncing track {track_id}: {e}")
