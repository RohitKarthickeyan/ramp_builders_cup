"""A simulated inbox. No real email is sent — this is the communication bus
between the buyer agent and the vendor agents.

Each email lives in a per-vendor thread. Every agent has a "read pointer" so it
can discover messages addressed to it that it hasn't processed yet.
"""
from __future__ import annotations

from .models import Email, Offer, Thread


class Mailbox:
    def __init__(self) -> None:
        self.threads: dict[str, Thread] = {}
        # agent_id -> set of email ids it has already consumed
        self._read: dict[str, set[str]] = {}

    def ensure_thread(self, thread_id: str, vendor_id: str, subject: str) -> Thread:
        t = self.threads.get(thread_id)
        if not t:
            t = Thread(id=thread_id, vendor_id=vendor_id, subject=subject)
            self.threads[thread_id] = t
        return t

    def send(
        self,
        *,
        thread_id: str,
        vendor_id: str,
        subject: str,
        sender_id: str,
        sender_role: str,
        sender_name: str,
        to_id: str,
        to_name: str,
        body: str,
        offer: Offer | None = None,
        is_followup: bool = False,
    ) -> Email:
        thread = self.ensure_thread(thread_id, vendor_id, subject)
        email = Email(
            thread_id=thread_id,
            sender_id=sender_id,
            sender_role=sender_role,  # type: ignore[arg-type]
            sender_name=sender_name,
            to_id=to_id,
            to_name=to_name,
            subject=subject,
            body=body,
            offer=offer,
            is_followup=is_followup,
        )
        thread.emails.append(email)
        return email

    def unread_for(self, agent_id: str) -> list[Email]:
        """Emails addressed to `agent_id` that it hasn't consumed yet."""
        read = self._read.setdefault(agent_id, set())
        out: list[Email] = []
        for t in self.threads.values():
            for em in t.emails:
                if em.to_id == agent_id and em.id not in read:
                    out.append(em)
        out.sort(key=lambda e: e.ts)
        return out

    def mark_read(self, agent_id: str, email_id: str) -> None:
        self._read.setdefault(agent_id, set()).add(email_id)

    def thread_snapshot(self) -> list[dict]:
        return [
            {
                "id": t.id,
                "vendor_id": t.vendor_id,
                "subject": t.subject,
                "emails": [e.model_dump() for e in t.emails],
            }
            for t in self.threads.values()
        ]
