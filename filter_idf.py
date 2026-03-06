"""
Step 2 — Run this after build_csv.py to filter down to Île-de-France only.

Keeps only accommodations in IDF departments:
    75 (Paris), 77 (Seine-et-Marne), 78 (Yvelines),
    91 (Essonne), 92 (Hauts-de-Seine), 93 (Seine-Saint-Denis),
    94 (Val-de-Marne), 95 (Val-d'Oise)

Also explicitly includes Clichy (92110) regardless of anything.

Output: idf_accommodations.csv — this is what the scraper watches.

Usage:
    python3 filter_idf.py
"""

import csv
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

INPUT_FILE = "all_accommodations.csv"
OUTPUT_FILE = "idf_accommodations.csv"

# Île-de-France postal code prefixes
IDF_POSTAL_PREFIXES = ("75", "77", "78", "91", "92", "93", "94", "95")

# Cities to always include regardless (e.g. Clichy straddles 92)
ALWAYS_INCLUDE_CITIES = {"clichy", "clichy-la-garenne"}


def is_idf(row: dict) -> bool:
    postal = row.get("residence_postal_code", "").strip()
    city = row.get("residence_city", "").strip().lower()

    if city in ALWAYS_INCLUDE_CITIES:
        return True

    if postal and postal[:2] in IDF_POSTAL_PREFIXES:
        return True

    # Fallback: sector label sometimes contains the city name
    sector = row.get("sector_label", "").strip().lower()
    if any(c in sector for c in ["paris", "clichy", "versailles", "boulogne",
                                   "saint-denis", "vincennes", "nanterre",
                                   "créteil", "cergy", "massy", "évry"]):
        return True

    return False


def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f_in:
            reader = csv.DictReader(f_in)
            rows = list(reader)
            fieldnames = reader.fieldnames
    except FileNotFoundError:
        logging.error(f"{INPUT_FILE} not found. Run build_csv.py first!")
        sys.exit(1)

    idf_rows = [r for r in rows if is_idf(r)]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(idf_rows)

    logging.info(f"Total accommodations: {len(rows)}")
    logging.info(f"IDF accommodations:   {len(idf_rows)}")
    logging.info(f"Saved to:             {OUTPUT_FILE}")

    # Print a breakdown by department
    from collections import Counter
    dept_counter = Counter(
        r.get("residence_postal_code", "??")[:2] for r in idf_rows
    )
    logging.info("Breakdown by department:")
    dept_names = {
        "75": "Paris", "77": "Seine-et-Marne", "78": "Yvelines",
        "91": "Essonne", "92": "Hauts-de-Seine (incl. Clichy)",
        "93": "Seine-Saint-Denis", "94": "Val-de-Marne", "95": "Val-d'Oise",
    }
    for dept, count in sorted(dept_counter.items()):
        name = dept_names.get(dept, dept)
        logging.info(f"  {dept} - {name}: {count}")


if __name__ == "__main__":
    main()
