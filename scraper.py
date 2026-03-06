"""
Core scraper — reads idf_accommodations.csv and polls each ID via the
direct JSON API endpoint. No more search bounds, no more guessing.
We hit each room individually and check data["available"] == True.
"""

import csv
import httpx
import logging
from typing import List
from config import TOOL_ID

BASE_URL = "https://trouverunlogement.lescrous.fr/api/fr/tools/{tool_id}/accommodations/{acc_id}"
CSV_FILE = "idf_accommodations.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://trouverunlogement.lescrous.fr/",
}


def load_idf_ids() -> List[dict]:
    """Load all IDF accommodation rows from CSV."""
    try:
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        logging.error(
            f"{CSV_FILE} not found. Run build_csv.py then filter_idf.py first!"
        )
        return []


def fetch_available_accommodations(idf_rows: List[dict]) -> List[dict]:
    """
    Given a list of CSV rows, check each one and return only
    the ones that are currently available.
    """
    available = []
    total = len(idf_rows)

    with httpx.Client(timeout=10, headers=HEADERS, follow_redirects=True) as client:
        for i, row in enumerate(idf_rows):
            acc_id = row.get("id")
            if not acc_id:
                continue

            url = BASE_URL.format(tool_id=TOOL_ID, acc_id=acc_id)
            try:
                r = client.get(url)
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                data = r.json()

                if data.get("available"):
                    data["url"] = (
                        f"https://trouverunlogement.lescrous.fr/tools/{TOOL_ID}/accommodations/{acc_id}"
                    )
                    available.append(data)

            except Exception as e:
                logging.warning(f"ID {acc_id}: {e}")

            if (i + 1) % 50 == 0:
                logging.info(f"Checked {i + 1}/{total} IDF accommodations...")

    logging.info(f"Scan complete: {len(available)} available out of {total} IDF rooms checked.")
    return available
