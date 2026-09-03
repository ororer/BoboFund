import requests
import json

url = "https://data.gov.il/api/3/action/datastore_search"
params = {"resource_id": "a30dcbea-a1d2-482c-ae29-8f781f5025fb", "q": "15315", "limit": 5}
data = requests.get(url, params=params).json()
records = data.get("result", {}).get("records", [])

print("--- RAW RECORD FROM GOV API ---")
if records:
    print(json.dumps(records[0], indent=2, ensure_ascii=False))
else:
    print("NO RECORDS FOUND")
