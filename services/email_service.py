from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any


class EmailService:
    def __init__(self) -> None:
        self._host = os.getenv("SMTP_HOST", "")
        self._port = int(os.getenv("SMTP_PORT", "587"))
        self._username = os.getenv("SMTP_USERNAME", "")
        self._password = os.getenv("SMTP_PASSWORD", "")
        self._from_email = os.getenv("SMTP_FROM", self._username)
        self._use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}

    def is_configured(self) -> bool:
        return bool(self._host and self._port and self._username and self._password and self._from_email)

    def send_email(self, to_email: str, subject: str, body: str) -> dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "error": "Email is not configured. Set SMTP_HOST/SMTP_PORT/SMTP_USERNAME/SMTP_PASSWORD/SMTP_FROM."}

        to_addr = str(to_email).strip()
        if not to_addr or "@" not in to_addr:
            return {"ok": False, "error": "Invalid recipient email."}

        msg = EmailMessage()
        msg["From"] = self._from_email
        msg["To"] = to_addr
        msg["Subject"] = str(subject or "")
        msg.set_content(str(body or ""))

        try:
            with smtplib.SMTP(self._host, self._port, timeout=20) as server:
                server.ehlo()
                if self._use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(self._username, self._password)
                server.send_message(msg)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
