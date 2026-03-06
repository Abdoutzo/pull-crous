import os
from dotenv import load_dotenv

load_dotenv()

# --- CROUS API ---
TOOL_ID = 42
POLL_INTERVAL = 60  # seconds between each full scan of IDF accommodations

# --- Brevo ---
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_NAME = "CROUS Bot"

# --- Recipients ---
# Add one email per line in recipients.txt
# Falls back to RECIPIENT_EMAIL in .env if the file doesn't exist
RECIPIENTS_FILE = "recipients.txt"


def load_recipients() -> list:
    """Load recipient emails from recipients.txt, one per line."""
    if os.path.exists(RECIPIENTS_FILE):
        with open(RECIPIENTS_FILE, "r", encoding="utf-8") as f:
            emails = [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
        if emails:
            return emails

    # Fallback to single RECIPIENT_EMAIL from .env
    fallback = os.getenv("RECIPIENT_EMAIL")
    if fallback:
        return [fallback]

    return []


# --- State file (persists seen listing IDs across restarts) ---
STATE_FILE = "seen_ids.json"
