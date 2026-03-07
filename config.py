import os
from dotenv import load_dotenv

load_dotenv()

# --- CROUS API ---
TOOL_ID = 42
POLL_INTERVAL = 60  # seconds between each full scan of IDF accommodations


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


# --- SMTP email transport ---
# Supported values for SMTP_SECURITY: "starttls", "ssl", "none"
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = _read_int_env("SMTP_PORT", 587)
SMTP_SECURITY = os.getenv("SMTP_SECURITY", "starttls").strip().lower()
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = "CROUS Bot"

# --- Recipients ---
# Comma-separated list of emails in RECIPIENT_EMAIL env var
# e.g. RECIPIENT_EMAIL=you@gmail.com,friend@gmail.com


def load_recipients() -> list:
    """Load recipient emails from RECIPIENT_EMAIL env var (comma-separated)."""
    value = os.getenv("RECIPIENT_EMAIL", "")
    return [e.strip() for e in value.split(",") if e.strip()]


# --- State file (persists seen listing IDs across restarts) ---
STATE_FILE = "seen_ids.json"
