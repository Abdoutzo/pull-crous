"""
Persist runtime state to disk so we can:
  - avoid duplicate alerts across restarts
  - keep a daily list of newly found listings for end-of-day summary
"""
import json
import os
from config import STATE_FILE


def _default_payload() -> dict:
    return {
        "seen_ids": [],
        "daily_date": "",
        "daily_ids": [],
        "daily_items": [],
        "last_summary_date": "",
    }


def _normalize_payload(raw: object) -> dict:
    # Backward compatibility: old format was a plain JSON list of seen IDs.
    if isinstance(raw, list):
        payload = _default_payload()
        payload["seen_ids"] = [str(item) for item in raw if item is not None]
        return payload

    if not isinstance(raw, dict):
        return _default_payload()

    payload = _default_payload()
    payload["seen_ids"] = [str(item) for item in raw.get("seen_ids", []) if item is not None]
    payload["daily_date"] = str(raw.get("daily_date", "") or "")
    payload["daily_ids"] = [str(item) for item in raw.get("daily_ids", []) if item is not None]
    payload["daily_items"] = [item for item in raw.get("daily_items", []) if isinstance(item, dict)]
    payload["last_summary_date"] = str(raw.get("last_summary_date", "") or "")
    return payload


def load_runtime_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                payload = _normalize_payload(json.load(f))
        except Exception:
            payload = _default_payload()
    else:
        payload = _default_payload()

    return {
        "seen_ids": set(payload["seen_ids"]),
        "daily_date": payload["daily_date"],
        "daily_ids": set(payload["daily_ids"]),
        "daily_items": payload["daily_items"],
        "last_summary_date": payload["last_summary_date"],
    }


def save_runtime_state(state_data: dict):
    payload = _default_payload()
    payload["seen_ids"] = sorted(str(item) for item in state_data.get("seen_ids", set()) if item is not None)
    payload["daily_date"] = str(state_data.get("daily_date", "") or "")
    payload["daily_ids"] = sorted(str(item) for item in state_data.get("daily_ids", set()) if item is not None)
    payload["daily_items"] = [item for item in state_data.get("daily_items", []) if isinstance(item, dict)]
    payload["last_summary_date"] = str(state_data.get("last_summary_date", "") or "")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def load_seen_ids() -> set:
    return load_runtime_state()["seen_ids"]


def save_seen_ids(seen_ids: set):
    state_data = load_runtime_state()
    state_data["seen_ids"] = set(str(item) for item in seen_ids if item is not None)
    save_runtime_state(state_data)
