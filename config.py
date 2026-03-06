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
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# --- State file (persists seen listing IDs across restarts) ---
STATE_FILE = "seen_ids.json"
