"""
Persist seen listing IDs to disk so we don't re-alert after restarts.
"""
import json
import os
from config import STATE_FILE


def load_seen_ids() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen_ids(seen_ids: set):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen_ids), f)
