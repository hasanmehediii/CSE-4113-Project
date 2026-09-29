"""SMTP adapter. Development delivery goes to the local Mailpit inbox."""

import logging
import smtplib
from urllib.parse import quote
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_action_email(email: str, token: str, purpose: str):
    settings = get_settings()
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = email
    message["Subject"] = "Reset your password" if purpose == "reset" else "Verify your email"
    route = "reset-password" if purpose == "reset" else "verify-email"
    # A fragment keeps the token out of HTTP access logs and referrer URLs.
    link = f"{settings.frontend_url.rstrip('/')}/{route}#token={quote(token, safe='')}"
    message.set_content(
        f"{'Reset your password' if purpose == 'reset' else 'Verify your email'} for DubsiBhai:\n\n"
        f"{link}\n\n"
        f"Or paste this token in the application: {token}\n\n"
        "If you did not request this, ignore this email. Do not share this link or token."
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        # Do not disclose SMTP failures differently for registered email addresses.
        # Users can resend; a durable outbox is the next step for guaranteed delivery.
        logger.error("Auth email delivery failed; check SMTP availability")
