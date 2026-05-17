# CROUS IDF Scraper

I was looking for a student room in Paris and quickly realized the CROUS website is kind of a joke to navigate. The map search only shows rooms that are "actively listed" — meaning most of the time it's just empty and you think nothing's available. But turns out there's a whole database of rooms sitting behind the scenes with IDs from 1 to 3132, each with their own page, and some of them quietly flip to available without ever showing up on the map.

So I built this. It hits every single room's API endpoint directly, filters down to Ile-de-France, and polls continuously:
- Weekdays: every 5 minutes
- Weekend: quiet mode (no scan emails)
- Emails only between 08:00 and 18:00 (Europe/Paris)

Zero paid services. Just Python and a standard SMTP account.

## The trick

The official map search endpoint (`/api/fr/search?bounds=...`) is basically useless — it only returns rooms that CROUS decides to surface, which outside of peak season is nothing. But there's a direct JSON endpoint nobody talks about:

```
GET https://trouverunlogement.lescrous.fr/api/fr/tools/42/accommodations/{id}
```

Call it with any ID from 1 to 3132 and you get back full room details including a dead-simple `"available": true/false` field. No auth needed, no scraping HTML, just clean JSON. So we call all of them.

## How it runs

```
build_csv.py   ->  hits all 3132 IDs once, dumps everything to all_accommodations.csv
filter_idf.py  ->  keeps only IDF (Paris + suburbs + Clichy), saves idf_accommodations.csv
main.py        ->  polls on a weekday schedule and sends one email per scan window
```

When a room drops, the email tells you the name and full address of the residence, rent in euros (the API stores it in cents for some reason, we convert it), room size in m2, whether it's solo, couple or coloc, and what equipment is included.

## Setup

```bash
git clone https://github.com/Abdoutzo/pull-crous
cd pull-crous

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# open .env and fill your SMTP credentials
```

Minimal setup (Gmail):
1. Set `SENDER_EMAIL`
2. Set `RECIPIENT_EMAIL`
3. Set `EMAIL_APP_PASSWORD` (Google App Password)

Advanced setup (optional): override `SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USERNAME`, `SMTP_PASSWORD`.

## Running it

First time only, build the database:

```bash
python3 build_csv.py    # ~15 min, hits all 3132 IDs
python3 filter_idf.py   # instant, keeps only IDF rooms
```

Then run the bot:

```bash
python3 main.py
```

It'll scan all ~420 IDF rooms and send one email per scan window:
- Monday to Friday: every 5 minutes
- Saturday + Sunday: no email
- Hours: 08:00 to 18:00 (Europe/Paris)

You can also just leave it running on your machine — keep the terminal open and don't close the laptop. If you close the lid on a MacBook it will sleep even if plugged in and the script stops. To avoid that go to System Settings -> Battery -> Options and enable "Prevent automatic sleeping when the display is off".

## Recommended deployment

The reliable production setup is Railway, not GitHub Actions. Railway keeps one worker alive and lets `main.py` run as a normal long-lived loop, which is much more dependable than GitHub's scheduled runner cadence for a 5-minute monitor.

Current Railway entrypoint:

```bash
python main.py
```

Recommended Railway env vars:

```bash
STATE_FILE=/data/seen_ids.json
LOG_FILE=/data/crous.log
ENABLE_FILE_LOGGING=true
```

If you mount a Railway volume at `/data`, the bot keeps its seen IDs and daily summary state across restarts/deploys.

GitHub Actions is still useful as a free backup and for manual SMTP tests.

Important GitHub note: scheduled workflows in public repos are automatically disabled after 60 days without repository activity. If the monitor suddenly stops, push a small commit (or re-enable the workflow in the Actions tab) to wake it back up.
For an immediate manual email test outside business hours, open the Actions tab, run `CROUS Monitor`, and set `force_email_window=true`.
For a strict SMTP check, keep `require_email_success=true` so the manual run fails if GitHub cannot actually send the email.

## Environment variables

| Variable | What it is |
|---|---|
| `EMAIL_APP_PASSWORD` | App password (recommended for Gmail) |
| `SENDER_EMAIL` | Sender email shown in outgoing alerts |
| `RECIPIENT_EMAIL` | Who gets the alerts — separate multiple emails with commas |
| `SMTP_HOST` | Optional manual SMTP host override |
| `SMTP_PORT` | Optional manual SMTP port override |
| `SMTP_SECURITY` | Optional: `starttls`, `ssl`, or `none` |
| `SMTP_USERNAME` | Optional manual SMTP username override |
| `SMTP_PASSWORD` | Optional manual SMTP password override |
| `STATE_FILE` | Optional path for persisted monitor state (`seen_ids`, daily summary state) |
| `LOG_FILE` | Optional path for file logs |
| `ENABLE_FILE_LOGGING` | Optional: `true`/`false` to keep a log file in addition to stdout |
| `FORCE_EMAIL_WINDOW` | Manual-test override to bypass the 08:00-18:00 / weekday restriction |
| `REQUIRE_EMAIL_SUCCESS` | Manual-test guard to fail the run if SMTP delivery fails |

For multiple recipients just comma-separate them: `you@gmail.com,friend@gmail.com,other@gmail.com`

## Files

```
crous_scrapper/
├── main.py          - the loop that runs forever
├── scraper.py       - polls each IDF room's API endpoint
├── notifier.py      - builds and sends the email via SMTP
├── state.py         - remembers which rooms we've already alerted on
├── config.py        - loads everything from .env
├── build_csv.py     - one-time: crawls all 3132 IDs into a CSV
├── filter_idf.py    - one-time: filters that CSV down to IDF only
├── requirements.txt
├── .env.example
├── .gitignore
├── Procfile         - for Railway
└── railway.json     - for Railway
```

## A few things worth knowing

- `toolId=42` is the identifier for the 2025-2026 academic year, if it stops working next year that's probably why
- The CSV is built once and stays static, re-run `build_csv.py` and `filter_idf.py` if you want fresh data
- Requests are throttled on purpose, don't lower it below 30s or you'll probably get rate-limited
- `seen_ids.json` keeps track of what's been alerted so you don't get spammed after a restart
- For exact 5-minute uptime, prefer Railway over GitHub scheduled workflows
