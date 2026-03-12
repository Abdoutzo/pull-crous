"""
Main polling loop - entry point of the CROUS scraper.

Flow:
  1. Load IDF accommodation IDs from idf_accommodations.csv
  2. Every poll interval, hit each ID's direct API endpoint
  3. Alert for newly seen available IDs
  4. Send one end-of-day summary before 18:00 for all new IDs found that day
"""
import logging
import os
import sys
import time
from typing import List

from config import (
    current_local_time,
    get_current_poll_interval,
    is_daily_summary_window,
    is_weekend,
    is_within_email_window,
)
from notifier import send_alerts, send_daily_summary
from scraper import fetch_available_accommodations, load_idf_ids
from state import load_runtime_state, save_runtime_state


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crous.log"),
    ],
)
# Silence per-request HTTP logs.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def _snapshot_listing(item: dict, first_seen_at: str) -> dict:
    return {
        "id": item.get("id"),
        "label": item.get("label"),
        "url": item.get("url"),
        "area": item.get("area", {}),
        "occupationModes": item.get("occupationModes", []),
        "residence": item.get("residence", {}),
        "first_seen_at": first_seen_at,
    }


def _reset_daily_if_needed(state_data: dict, today: str):
    if state_data.get("daily_date") != today:
        state_data["daily_date"] = today
        state_data["daily_ids"] = set()
        state_data["daily_items"] = []


def _maybe_send_daily_summary(state_data: dict, now) -> dict:
    today = now.date().isoformat()
    if state_data.get("last_summary_date") == today:
        return state_data
    if not is_daily_summary_window(now):
        return state_data

    daily_items = state_data.get("daily_items", [])
    if not daily_items:
        logging.info("No new listings found on %s. Daily summary not sent.", today)
        state_data["last_summary_date"] = today
        return state_data

    if send_daily_summary(daily_items, today):
        state_data["last_summary_date"] = today
    else:
        logging.warning("Failed to send daily summary for %s; will retry next scan.", today)
    return state_data


def check(idf_rows: List[dict], state_data: dict) -> dict:
    now = current_local_time()
    today = now.date().isoformat()
    _reset_daily_if_needed(state_data, today)

    if is_weekend(now):
        logging.info("Weekend mode active: skipping scan and emails.")
        save_runtime_state(state_data)
        return state_data

    if not is_within_email_window(now):
        logging.info("Outside email window (08:00-18:00 Europe/Paris): skipping scan and emails.")
        save_runtime_state(state_data)
        return state_data

    available = fetch_available_accommodations(idf_rows)

    if not available:
        logging.info("Nothing available right now. Patience...")
        if not send_alerts([]):
            logging.warning("Failed to send status email; will retry next scan.")
        state_data = _maybe_send_daily_summary(state_data, now)
        save_runtime_state(state_data)
        return state_data

    seen_ids = state_data.get("seen_ids", set())
    daily_ids = state_data.get("daily_ids", set())
    daily_items = state_data.get("daily_items", [])

    new_listings = [item for item in available if str(item.get("id")) not in seen_ids]

    if new_listings:
        logging.info("%d new listing(s) found in this scan.", len(new_listings))
        if send_alerts(new_listings):
            first_seen_at = now.isoformat()
            for item in new_listings:
                listing_id = item.get("id")
                if listing_id is None:
                    continue

                listing_id = str(listing_id)
                seen_ids.add(listing_id)
                if listing_id not in daily_ids:
                    daily_ids.add(listing_id)
                    daily_items.append(_snapshot_listing(item, first_seen_at))
        else:
            logging.warning(
                "Batch alert send failed; all %d listing(s) will be retried next scan.",
                len(new_listings),
            )
    else:
        logging.info("%d available but all already seen - sending status email.", len(available))
        if not send_alerts([]):
            logging.warning("Failed to send status email; will retry next scan.")

    state_data["seen_ids"] = seen_ids
    state_data["daily_ids"] = daily_ids
    state_data["daily_items"] = daily_items
    state_data = _maybe_send_daily_summary(state_data, now)
    save_runtime_state(state_data)
    return state_data


def main():
    logging.info("=== CROUS IDF Scraper started ===")

    idf_rows = load_idf_ids()
    if not idf_rows:
        logging.error("No IDF rows loaded. Run build_csv.py then filter_idf.py first!")
        sys.exit(1)

    logging.info("Watching %d IDF accommodations.", len(idf_rows))

    if os.getenv("RESET_STATE", "").lower() == "true":
        logging.info("RESET_STATE=true - clearing seen IDs and daily summary state.")
        state_data = {
            "seen_ids": set(),
            "daily_date": "",
            "daily_ids": set(),
            "daily_items": [],
            "last_summary_date": "",
        }
        save_runtime_state(state_data)
    else:
        state_data = load_runtime_state()
        logging.info(
            "Loaded state: %d seen IDs, %d daily listing(s) for %s.",
            len(state_data.get("seen_ids", set())),
            len(state_data.get("daily_items", [])),
            state_data.get("daily_date", "N/A"),
        )

    run_once = os.getenv("RUN_ONCE", "").lower() == "true"
    if run_once:
        logging.info("RUN_ONCE=true - running a single scan and exiting.")
        try:
            check(idf_rows, state_data)
        except Exception as exc:
            logging.error("Unhandled error during single scan: %s", exc, exc_info=True)
        return

    while True:
        try:
            state_data = check(idf_rows, state_data)
        except KeyboardInterrupt:
            logging.info("Stopped by user. Bye!")
            break
        except Exception as exc:
            logging.error("Unhandled error: %s", exc, exc_info=True)

        poll_interval = get_current_poll_interval(current_local_time())
        logging.info("Next scan in %ss...\n", poll_interval)
        time.sleep(poll_interval)


if __name__ == "__main__":
    main()

