import json
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "reference" / "india_districts.json"
URL = "https://raw.githubusercontent.com/open-admin-data/india-administrative-divisions/master/data/all-district.json"

def main():
    print("Downloading India district reference data...")
    response = requests.get(URL, timeout=45)
    response.raise_for_status()
    source = response.json()
    if not isinstance(source, list):
        raise ValueError("Unexpected district dataset format.")

    unique = {}
    for row in source:
        try:
            item = {
                "state": row["parent"]["name"]["en"].strip(),
                "district": row["name"]["en"].strip(),
                "latitude": float(row["geo"]["lat"]),
                "longitude": float(row["geo"]["lon"]),
            }
            if item["state"] and item["district"]:
                unique[(item["state"].casefold(), item["district"].casefold())] = item
        except (KeyError, TypeError, ValueError, AttributeError):
            continue

    districts = sorted(unique.values(), key=lambda x: (x["state"].casefold(), x["district"].casefold()))
    if not districts:
        raise ValueError("No valid district records were downloaded.")

    payload = {
        "source": URL,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "district_count": len(districts),
        "state_count": len({x["state"] for x in districts}),
        "districts": districts,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(OUTPUT)
    print("DISTRICT DATABASE READY")
    print("States / UTs:", payload["state_count"])
    print("Districts:", payload["district_count"])
    print("Saved:", OUTPUT)

if __name__ == "__main__":
    main()
