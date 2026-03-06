"""
Step 1 — Run this ONCE to build the full accommodations database.

Hits /api/fr/tools/42/accommodations/{id} for every ID from 1 to MAX_ID,
saves everything to all_accommodations.csv.

Takes a few minutes (we throttle to be polite). Run it once, then use
filter_idf.py to get only the Paris/IDF ones.

Usage:
    python3 build_csv.py
"""

import httpx
import csv
import time
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

BASE_URL = "https://trouverunlogement.lescrous.fr/api/fr/tools/42/accommodations/{id}"
MAX_ID = 3132
OUTPUT_FILE = "all_accommodations.csv"
DELAY = 0.3  # seconds between requests — be polite, don't hammer their API

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://trouverunlogement.lescrous.fr/",
}

FIELDNAMES = [
    "id",
    "label",
    "available",
    "residence_label",
    "residence_address",
    "residence_city",
    "residence_postal_code",
    "sector_label",
    "lat",
    "lon",
    "area_min",
    "area_max",
    "rent_min",
    "rent_max",
    "occupation_type",
    "adapted_pmr",
    "high_demand",
    "low_stock",
    "url",
]


def extract_city_and_postal(address: str):
    """Try to extract city and postal code from address string like '35 rue X 75001 PARIS'"""
    parts = address.strip().split()
    postal = ""
    city = ""
    for i, part in enumerate(parts):
        if part.isdigit() and len(part) == 5:
            postal = part
            city = " ".join(parts[i + 1:])
            break
    return postal, city


def parse_accommodation(data: dict) -> dict:
    residence = data.get("residence", {})
    address = residence.get("address", "")
    postal, city = extract_city_and_postal(address)
    location = residence.get("location", {})

    occupation_modes = data.get("occupationModes", [])
    rents = [m.get("rent", {}) for m in occupation_modes if m.get("rent")]
    rent_min = min((r.get("min", 0) for r in rents), default=0) / 100  # cents → euros
    rent_max = max((r.get("max", 0) for r in rents), default=0) / 100
    occupation_types = ", ".join(m.get("type", "") for m in occupation_modes)

    area = data.get("area", {})

    return {
        "id": data.get("id"),
        "label": data.get("label", ""),
        "available": data.get("available", False),
        "residence_label": residence.get("label", ""),
        "residence_address": address,
        "residence_city": city,
        "residence_postal_code": postal,
        "sector_label": residence.get("sector", {}).get("label", ""),
        "lat": location.get("lat", ""),
        "lon": location.get("lon", ""),
        "area_min": area.get("min", ""),
        "area_max": area.get("max", ""),
        "rent_min": rent_min,
        "rent_max": rent_max,
        "occupation_type": occupation_types,
        "adapted_pmr": data.get("adaptedPmr", False),
        "high_demand": data.get("highDemand", False),
        "low_stock": data.get("lowStock", False),
        "url": f"https://trouverunlogement.lescrous.fr/tools/42/accommodations/{data.get('id')}",
    }


def main():
    logging.info(f"Starting full CSV build — scanning IDs 1 to {MAX_ID}")
    logging.info(f"Output: {OUTPUT_FILE}")
    logging.info(f"Estimated time: ~{round(MAX_ID * DELAY / 60, 1)} minutes")

    found = 0
    errors = 0

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        with httpx.Client(timeout=10, headers=HEADERS, follow_redirects=True) as client:
            for acc_id in range(1, MAX_ID + 1):
                url = BASE_URL.format(id=acc_id)
                try:
                    r = client.get(url)
                    if r.status_code == 404:
                        # ID doesn't exist, skip silently
                        continue
                    r.raise_for_status()
                    data = r.json()
                    row = parse_accommodation(data)
                    writer.writerow(row)
                    found += 1

                    if found % 100 == 0:
                        logging.info(f"Progress: {acc_id}/{MAX_ID} — {found} saved so far")

                except httpx.HTTPStatusError as e:
                    logging.warning(f"ID {acc_id}: HTTP {e.response.status_code}")
                    errors += 1
                except Exception as e:
                    logging.warning(f"ID {acc_id}: {e}")
                    errors += 1

                time.sleep(DELAY)

    logging.info(f"Done! {found} accommodations saved to {OUTPUT_FILE} ({errors} errors)")


if __name__ == "__main__":
    main()
