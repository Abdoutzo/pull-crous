"""
Sends email notifications via SMTP or the Resend HTTPS API.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import List, Tuple

import httpx

from config import (
    EMAIL_PROVIDER,
    RESEND_API_BASE_URL,
    RESEND_API_KEY,
    RESEND_FROM_EMAIL,
    RESEND_REPLY_TO,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SECURITY,
    SMTP_USERNAME,
    SENDER_EMAIL,
    SENDER_NAME,
    get_current_poll_interval,
    load_recipients,
)


def _extract_listing(item: dict) -> dict:
    residence = item.get("residence", {})
    name = item.get("label", residence.get("label", "N/A"))
    address = residence.get("address", "N/A")
    listing_url = item.get("url", "https://trouverunlogement.lescrous.fr/")

    occupation_modes = item.get("occupationModes", [])
    rents = []
    mode_types = []
    for mode in occupation_modes:
        mode_types.append(mode.get("type", ""))
        rent = mode.get("rent", {})
        if rent.get("min"):
            rents.append(rent["min"] / 100)
        if rent.get("max"):
            rents.append(rent["max"] / 100)
    rent_str = f"{min(rents):.0f}-{max(rents):.0f} EUR/month" if rents else "N/A"
    modes_str = ", ".join(mode_types) if mode_types else "N/A"

    area = item.get("area", {})
    area_str = f"{area.get('min', '?')}-{area.get('max', '?')} m2"

    return {
        "name": name,
        "address": address,
        "rent": rent_str,
        "area": area_str,
        "type": modes_str,
        "url": listing_url,
    }


def _select_email_provider() -> str:
    provider = EMAIL_PROVIDER
    if provider == "auto":
        if RESEND_API_KEY and RESEND_FROM_EMAIL:
            return "resend"
        return "smtp"
    if provider in {"smtp", "resend"}:
        return provider

    logging.warning("Unknown EMAIL_PROVIDER='%s'. Falling back to auto detection.", provider)
    if RESEND_API_KEY and RESEND_FROM_EMAIL:
        return "resend"
    return "smtp"


def _build_email_message(
    recipients: List[str],
    subject: str,
    text_body: str,
    html_body: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg


def _build_batch_html(items: List[dict]) -> str:
    interval_minutes = max(1, get_current_poll_interval() // 60)
    if not items:
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
            <h2 style="color: #e63946;">CROUS update ({interval_minutes} min)</h2>
            <p><strong>Pas de logement dispo.</strong></p>
            <p style="color: #888; font-size: 12px;">Sent by your CROUS scraper bot.</p>
        </body>
        </html>
        """

    rows = []
    for item in items:
        listing = _extract_listing(item)
        rows.append(
            (
                "<tr>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['name']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['rent']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['area']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['type']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['address']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'><a href='{listing['url']}'>Open</a></td>"
                "</tr>"
            )
        )

    rows_html = "\n".join(rows)
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #e63946;">CROUS: {len(items)} new listing(s) in the last {interval_minutes} minutes</h2>
        <table style="border-collapse: collapse; width: 100%; font-size: 14px;">
            <thead>
                <tr style="background: #f6f6f6;">
                    <th style="padding: 8px; text-align: left;">Residence</th>
                    <th style="padding: 8px; text-align: left;">Rent</th>
                    <th style="padding: 8px; text-align: left;">Area</th>
                    <th style="padding: 8px; text-align: left;">Type</th>
                    <th style="padding: 8px; text-align: left;">Address</th>
                    <th style="padding: 8px; text-align: left;">Link</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <p style="color: #888; font-size: 12px; margin-top: 16px;">
            Sent by your CROUS scraper bot.
        </p>
    </body>
    </html>
    """


def _build_alert_content(items: List[dict]) -> Tuple[str, str, str]:
    interval_minutes = max(1, get_current_poll_interval() // 60)
    if items:
        subject = f"CROUS alert: {len(items)} new listing(s)"
        lines = [f"New CROUS listings detected in the last {interval_minutes} minutes:", ""]
        for item in items:
            listing = _extract_listing(item)
            lines.append(f"- {listing['name']} ({listing['rent']})")
            lines.append(f"  {listing['url']}")
        text_body = "\n".join(lines)
    else:
        subject = "CROUS update: pas de logement dispo"
        text_body = f"Pas de logement dispo sur les {interval_minutes} dernieres minutes."

    html_body = _build_batch_html(items)
    return subject, text_body, html_body


def _build_daily_summary_html(items: List[dict], summary_date: str) -> str:
    rows = []
    for item in items:
        listing = _extract_listing(item)
        first_seen_at = item.get("first_seen_at", "N/A")
        rows.append(
            (
                "<tr>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['name']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['rent']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['area']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['type']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{listing['address']}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'>{first_seen_at}</td>"
                f"<td style='padding:8px; border-bottom:1px solid #eee;'><a href='{listing['url']}'>Open</a></td>"
                "</tr>"
            )
        )

    rows_html = "\n".join(rows)
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #1d3557;">CROUS synthese du {summary_date}: {len(items)} nouveau(x) logement(s)</h2>
        <table style="border-collapse: collapse; width: 100%; font-size: 14px;">
            <thead>
                <tr style="background: #f6f6f6;">
                    <th style="padding: 8px; text-align: left;">Residence</th>
                    <th style="padding: 8px; text-align: left;">Rent</th>
                    <th style="padding: 8px; text-align: left;">Area</th>
                    <th style="padding: 8px; text-align: left;">Type</th>
                    <th style="padding: 8px; text-align: left;">Address</th>
                    <th style="padding: 8px; text-align: left;">First seen</th>
                    <th style="padding: 8px; text-align: left;">Link</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <p style="color: #888; font-size: 12px; margin-top: 16px;">
            Sent by your CROUS scraper bot.
        </p>
    </body>
    </html>
    """


def _build_daily_summary_content(items: List[dict], summary_date: str) -> Tuple[str, str, str]:
    subject = f"CROUS synthese du jour: {len(items)} logement(s) ({summary_date})"

    lines = [f"Synthese CROUS du {summary_date}", ""]
    for item in items:
        listing = _extract_listing(item)
        lines.append(f"- {listing['name']} ({listing['rent']})")
        lines.append(f"  {listing['url']}")

    text_body = "\n".join(lines)
    html_body = _build_daily_summary_html(items, summary_date)
    return subject, text_body, html_body


def _missing_smtp_config() -> bool:
    required = {
        "SMTP_HOST": SMTP_HOST,
        "SMTP_PORT": SMTP_PORT,
        "SMTP_USERNAME": SMTP_USERNAME,
        "SMTP_PASSWORD": SMTP_PASSWORD,
        "SENDER_EMAIL": SENDER_EMAIL,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        logging.error(
            "SMTP config missing: %s. Set them in .env or GitHub Secrets.",
            ", ".join(missing),
        )
        return True
    return False


def _missing_resend_config() -> bool:
    required = {
        "RESEND_API_KEY": RESEND_API_KEY,
        "RESEND_FROM_EMAIL": RESEND_FROM_EMAIL,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        logging.error(
            "Resend config missing: %s. Set them in .env, Railway variables, or GitHub Secrets.",
            ", ".join(missing),
        )
        return True
    return False


def _open_smtp():
    security = SMTP_SECURITY
    if security not in {"starttls", "ssl", "none"}:
        logging.warning("Unknown SMTP_SECURITY='%s'. Falling back to starttls.", security)
        security = "starttls"

    if security == "ssl":
        return smtplib.SMTP_SSL(
            SMTP_HOST,
            SMTP_PORT,
            timeout=30,
            context=ssl.create_default_context(),
        )

    client = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
    if security == "starttls":
        client.starttls(context=ssl.create_default_context())
    return client


def _send_via_smtp(
    recipients: List[str],
    subject: str,
    text_body: str,
    html_body: str,
    success_log: str,
) -> bool:
    if _missing_smtp_config():
        return False

    msg = _build_email_message(recipients, subject, text_body, html_body)
    try:
        with _open_smtp() as client:
            client.login(SMTP_USERNAME, SMTP_PASSWORD)
            client.send_message(msg)
        logging.info("%s", success_log)
        return True
    except Exception as exc:
        logging.error("Unexpected SMTP error while sending email: %s", exc)
        return False


def _send_via_resend(
    recipients: List[str],
    subject: str,
    text_body: str,
    html_body: str,
    success_log: str,
) -> bool:
    if _missing_resend_config():
        return False

    payload = {
        "from": f"{SENDER_NAME} <{RESEND_FROM_EMAIL}>",
        "to": recipients,
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }
    if RESEND_REPLY_TO:
        payload["reply_to"] = RESEND_REPLY_TO

    base_url = RESEND_API_BASE_URL.rstrip("/")
    try:
        response = httpx.post(
            f"{base_url}/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "User-Agent": "pull-crous/1.0",
            },
            json=payload,
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        logging.error("Unexpected Resend HTTP error while sending email: %s", exc)
        return False

    if not response.is_success:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = response.text.strip() or "<empty response body>"
        logging.error(
            "Resend API error (%s) while sending email: %s",
            response.status_code,
            error_payload,
        )
        return False

    email_id = None
    try:
        email_id = response.json().get("id")
    except ValueError:
        email_id = None

    if email_id:
        logging.info("%s via Resend (id=%s)", success_log, email_id)
    else:
        logging.info("%s via Resend", success_log)
    return True


def _send_email(
    recipients: List[str],
    subject: str,
    text_body: str,
    html_body: str,
    success_log: str,
) -> bool:
    provider = _select_email_provider()
    if provider == "resend":
        return _send_via_resend(recipients, subject, text_body, html_body, success_log)
    return _send_via_smtp(recipients, subject, text_body, html_body, success_log)


def send_alerts(items: List[dict]) -> bool:
    recipients = load_recipients()
    if not recipients:
        logging.error("No recipients configured. Set RECIPIENT_EMAIL in .env.")
        return False

    subject, text_body, html_body = _build_alert_content(items)
    if items:
        success_log = (
            f"Batch email sent for {len(items)} new listing(s) -> {', '.join(recipients)}"
        )
    else:
        success_log = f"Status email sent (pas de logement dispo) -> {', '.join(recipients)}"

    return _send_email(recipients, subject, text_body, html_body, success_log)


def send_daily_summary(items: List[dict], summary_date: str) -> bool:
    if not items:
        logging.info("Daily summary skipped: no new listings found on %s.", summary_date)
        return True

    recipients = load_recipients()
    if not recipients:
        logging.error("No recipients configured. Set RECIPIENT_EMAIL in .env.")
        return False

    subject, text_body, html_body = _build_daily_summary_content(items, summary_date)
    success_log = (
        f"Daily summary email sent for {len(items)} listing(s) -> {', '.join(recipients)}"
    )
    return _send_email(recipients, subject, text_body, html_body, success_log)


def send_alert(item: dict) -> bool:
    # Backward-compatible wrapper.
    return send_alerts([item])
