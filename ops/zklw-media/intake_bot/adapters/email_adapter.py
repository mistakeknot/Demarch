"""Email adapter — poll an IMAP inbox for requests, reply via SMTP.

A request email's Subject (or first body line) is the title. Each new unseen
message becomes a Request; the reply goes back to the sender via SMTP.

Uses imap-tools for reading and stdlib smtplib/email for sending, so only the
read side needs a third-party dep. Polls on an interval rather than IDLE to keep
the implementation simple and robust across providers.
"""

from __future__ import annotations

import asyncio
import email.message
import logging
import smtplib

from ..config import Config
from ..models import Channel, Request
from ..pipeline import handle

log = logging.getLogger("intake_bot.email")

_POLL_SECONDS = 60


def _send_reply(cfg: Config, to_addr: str, subject: str, body: str) -> None:
    msg = email.message.EmailMessage()
    msg["From"] = cfg.email_from or cfg.email_imap_user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    host = cfg.email_smtp_host or cfg.email_imap_host
    # Most providers: 587 STARTTLS. Adjust per provider if needed.
    with smtplib.SMTP(host, 587, timeout=20) as s:
        s.starttls()
        s.login(cfg.email_imap_user, cfg.email_imap_password)
        s.send_message(msg)


def _request_text(subject: str, body: str) -> str:
    subj = (subject or "").strip()
    if subj and subj.lower() not in ("request", "movie", "(no subject)"):
        return subj
    # Fall back to the first non-empty body line.
    for line in (body or "").splitlines():
        if line.strip():
            return line.strip()
    return subj


async def run(cfg: Config) -> None:
    from imap_tools import AND, MailBox  # lazy

    log.info("starting email adapter (poll every %ss)", _POLL_SECONDS)
    while True:
        try:
            # IMAP fetch is blocking → run it in a thread and hand the parsed
            # (sender, text) tuples back to THIS event loop to drive the async
            # pipeline. No nested event loops.
            incoming = await asyncio.to_thread(_fetch_unseen, cfg)
            for sender, text in incoming:

                async def reply(body: str, _to=sender) -> None:
                    await asyncio.to_thread(
                        _send_reply, cfg, _to, "Re: your media request", body
                    )

                req = Request(
                    channel=Channel.EMAIL,
                    user=sender,
                    text=text,
                    reply=reply,
                )
                await handle(req, cfg)
        except Exception:  # noqa: BLE001 — never let one bad poll kill the loop
            log.exception("email poll failed")
        await asyncio.sleep(_POLL_SECONDS)


def _fetch_unseen(cfg: Config) -> list[tuple[str, str]]:
    """Blocking: fetch unseen mail, mark seen, return (sender, request_text)."""
    from imap_tools import AND, MailBox

    out: list[tuple[str, str]] = []
    with MailBox(cfg.email_imap_host).login(
        cfg.email_imap_user, cfg.email_imap_password
    ) as mailbox:
        for msg in mailbox.fetch(AND(seen=False), mark_seen=True):
            text = _request_text(msg.subject, msg.text or msg.html or "")
            if text:
                out.append((msg.from_, text))
    return out
