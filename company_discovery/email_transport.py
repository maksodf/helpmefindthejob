# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""Provider-neutral email transport.

Two backends ship in this module:

- ``ConsoleTransport`` writes a JSON record per send to a list (for tests)
  and to a file at ``data/email_outbox.log`` (for local development). It
  never makes a network call.
- ``SmtpTransport`` uses the stdlib ``smtplib`` and STARTTLS when the
  port is 587 (or set via env). Credentials come from environment
  variables; nothing is persisted here.

The :func:`build_transport` factory chooses the backend based on env:

  - ``HELPMEFINDTHEJOB_EMAIL_BACKEND=smtp`` and SMTP env vars present →
    SmtpTransport.
  - Otherwise → ConsoleTransport (default for dev / pilot).
"""

from __future__ import annotations

import json
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol

from company_discovery.env_compat import get_env


@dataclass
class Email:
    to: str
    subject: str
    text: str
    from_address: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EmailTransport(Protocol):
    def send(self, email: Email) -> None: ...


class ConsoleTransport:
    """Records sends in-memory and to a JSONL file. Used for dev + tests."""

    def __init__(self, outbox_path: Path | None = None) -> None:
        self.outbox: list[Email] = []
        self.outbox_path = Path(outbox_path) if outbox_path else None

    def send(self, email: Email) -> None:
        self.outbox.append(email)
        if self.outbox_path is not None:
            self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "to": email.to,
                "subject": email.subject,
                "text": email.text,
                "from": email.from_address,
                "sent_at": email.sent_at.isoformat(),
            }
            with self.outbox_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def last_for(self, to: str) -> Email | None:
        for email in reversed(self.outbox):
            if email.to.casefold() == to.casefold():
                return email
        return None


class SmtpTransport:
    """STARTTLS-by-default SMTP transport. No credentials are persisted."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        *,
        use_tls: bool = True,
    ) -> None:
        if not host:
            raise ValueError("smtp_host_required")
        if port <= 0:
            raise ValueError("smtp_port_invalid")
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    def send(self, email: Email) -> None:
        message = EmailMessage()
        message["From"] = email.from_address
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.text)

        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            smtp.ehlo()
            if self.use_tls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(message)


def build_transport(
    *,
    backend: str | None = None,
    outbox_path: Path | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_username: str | None = None,
    smtp_password: str | None = None,
    smtp_starttls: bool | None = None,
) -> EmailTransport:
    backend = (
        (
            backend
            or get_env("HELPMEFINDTHEJOB_EMAIL_BACKEND")
            or "console"
        )
        .strip()
        .casefold()
    )
    if backend == "smtp":
        host = smtp_host or get_env("HELPMEFINDTHEJOB_SMTP_HOST", "")
        port = smtp_port or int(get_env("HELPMEFINDTHEJOB_SMTP_PORT", "587"))
        username = (
            smtp_username
            if smtp_username is not None
            else get_env("HELPMEFINDTHEJOB_SMTP_USERNAME")
        )
        password = (
            smtp_password
            if smtp_password is not None
            else get_env("HELPMEFINDTHEJOB_SMTP_PASSWORD")
        )
        use_tls = (
            smtp_starttls
            if smtp_starttls is not None
            else get_env("HELPMEFINDTHEJOB_SMTP_STARTTLS", "true")
            .strip()
            .casefold()
            == "true"
        )
        return SmtpTransport(
            host=host, port=port, username=username, password=password, use_tls=use_tls
        )
    return ConsoleTransport(outbox_path=outbox_path)


def email_from_address() -> str:
    return (
        get_env("HELPMEFINDTHEJOB_EMAIL_FROM")
        or "helpmefindthejob@localhost"
    )
