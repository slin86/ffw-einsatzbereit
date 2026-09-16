"""Outgoing mail. Falls back to logging if no SMTP host is configured."""

import logging
import smtplib
from email.message import EmailMessage

from einsatzbereit.config import get_settings

log = logging.getLogger(__name__)


def send_mail(to: str, subject: str, body: str) -> None:
    s = get_settings()
    if not s.smtp_host:
        log.warning("SMTP not configured – mail to %s not sent. Subject: %s", to, subject)
        log.info("Mail body:\n%s", body)
        return
    msg = EmailMessage()
    msg["From"] = s.smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            if s.smtp_starttls:
                smtp.starttls()
            if s.smtp_username:
                smtp.login(s.smtp_username, s.smtp_password)
            smtp.send_message(msg)
    except (OSError, smtplib.SMTPException):
        log.exception("Failed to send mail to %s", to)
