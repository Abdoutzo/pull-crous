# CROUS IDF Scraper

This bot monitors the CROUS accommodation API directly instead of relying on the public map, which often hides listings that are still in the backend. It keeps a local list of Ile-de-France residences, polls them on a schedule, and sends an email when a new room becomes available.

Schedule:
- Weekdays: every 5 minutes
- Weekend: quiet mode
- Email window: 08:00 to 18:00 Europe/Paris

## How it works

The public map search is not reliable enough for monitoring. This project queries the direct JSON endpoint for each accommodation ID:

```text
GET https://trouverunlogement.lescrous.fr/api/fr/tools/42/accommodations/{id}
```

That endpoint returns the room details and an `available` flag, so the bot can detect new openings without scraping HTML.

## Project flow

```text
build_csv.py   -> crawls all known IDs into all_accommodations.csv
filter_idf.py  -> keeps only Ile-de-France rows in idf_accommodations.csv
main.py        -> long-running monitor loop
```

## Local setup

```bash
git clone https://github.com/Abdoutzo/pull-crous
cd pull-crous

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env
```

For local SMTP testing, fill `.env` with:

```env
EMAIL_PROVIDER=smtp
SENDER_EMAIL=your_sender@gmail.com
RECIPIENT_EMAIL=your_recipient@example.com
EMAIL_APP_PASSWORD=your_gmail_app_password
```

Then run:

```bash
python build_csv.py
python filter_idf.py
python main.py
```

## Railway deployment

Railway is the recommended production runtime because it keeps a worker alive continuously. GitHub Actions is still useful as a backup and for manual tests, but it is not dependable enough for a 5-minute monitor on its own.

Important: Railway documents that SMTP is only available on the Pro plan and above. Free, Trial, and Hobby plans must use an HTTPS email API instead. This repo now supports Resend for that case.

Recommended Railway variables:

```env
EMAIL_PROVIDER=resend
RECIPIENT_EMAIL=your_recipient@example.com
SENDER_EMAIL=your_sender@gmail.com
RESEND_API_KEY=re_xxxxxxxxx
RESEND_FROM_EMAIL=alerts@your-verified-domain.com
RESEND_REPLY_TO=your_sender@gmail.com

STATE_FILE=/data/seen_ids.json
LOG_FILE=/data/crous.log
ENABLE_FILE_LOGGING=true
```

Recommended Railway setup:
- Service type: Worker
- Start command: `python main.py`
- Volume mount path: `/data`

Resend note:
- `RESEND_FROM_EMAIL` must use a verified sender/domain in Resend.
- The default `resend.dev` testing domain only works when sending to the email address attached to your own Resend account.

## GitHub Actions

The workflow still works for manual tests and as a lightweight backup. It now supports both SMTP and Resend depending on the repository variables and secrets you provide.

Repository variables:
- `EMAIL_PROVIDER`
- `SENDER_EMAIL`
- `RECIPIENT_EMAIL`
- `RESEND_FROM_EMAIL`
- `RESEND_REPLY_TO`

Repository secrets:
- `EMAIL_APP_PASSWORD`
- `RESEND_API_KEY`

Useful manual inputs:
- `force_email_window=true` to bypass weekday/hour restrictions
- `require_email_success=true` to fail the run if delivery fails
- `reset_state=true` to resend currently available listings once

Important GitHub note: scheduled workflows in public repositories are automatically disabled after 60 days without repository activity. If the schedule stops, re-enable the workflow or push a small commit.

## Environment variables

| Variable | Purpose |
|---|---|
| `EMAIL_PROVIDER` | `smtp`, `resend`, or `auto` |
| `RECIPIENT_EMAIL` | Comma-separated recipient list |
| `SENDER_EMAIL` | Sender identity used by SMTP and reply-to defaults |
| `EMAIL_APP_PASSWORD` | Gmail app password for local SMTP |
| `SMTP_HOST` | Optional SMTP override |
| `SMTP_PORT` | Optional SMTP override |
| `SMTP_SECURITY` | `starttls`, `ssl`, or `none` |
| `SMTP_USERNAME` | Optional SMTP override |
| `SMTP_PASSWORD` | Optional SMTP override |
| `RESEND_API_KEY` | Resend API key |
| `RESEND_FROM_EMAIL` | Verified Resend sender address |
| `RESEND_REPLY_TO` | Optional reply-to address for Resend emails |
| `RESEND_API_BASE_URL` | Optional Resend API base URL override |
| `STATE_FILE` | Path to persisted monitor state |
| `LOG_FILE` | Path to file logs |
| `ENABLE_FILE_LOGGING` | `true` or `false` |
| `FORCE_EMAIL_WINDOW` | Manual test override for weekday/hour restrictions |
| `REQUIRE_EMAIL_SUCCESS` | Fail the run when delivery fails |

## Files

```text
main.py
scraper.py
notifier.py
state.py
config.py
build_csv.py
filter_idf.py
requirements.txt
.env.example
.github/workflows/crous-monitor.yml
railway.json
```

## Notes

- `toolId=42` is tied to the current academic year and may need an update later.
- `seen_ids.json` prevents duplicate alerts after restarts.
- Re-run `build_csv.py` and `filter_idf.py` if you want a fresh local accommodation list.
- Keep the polling interval reasonable to avoid hammering the CROUS API.
