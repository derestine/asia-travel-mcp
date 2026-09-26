"""SQLite persistence for holds and bookings created through the MCP tools."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BookingStore:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._db = sqlite3.connect(db_path)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS holds (
                id TEXT PRIMARY KEY,
                product_code TEXT NOT NULL,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                travelers INTEGER NOT NULL,
                total REAL NOT NULL,
                currency TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                contact_email TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_hold_ref TEXT NOT NULL,
                payment_url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'awaiting_payment',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bookings (
                ref TEXT PRIMARY KEY,
                hold_id TEXT NOT NULL,
                product_code TEXT NOT NULL,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                travelers INTEGER NOT NULL,
                total REAL NOT NULL,
                currency TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                contact_email TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_booking_ref TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'CONFIRMED',
                created_at TEXT NOT NULL,
                cancelled_at TEXT
            );
            """
        )
        self._db.commit()

    # ── holds ──
    def create_hold(self, *, product_code, title, date, travelers, total, currency,
                    contact_name, contact_email, provider, provider_hold_ref,
                    payment_url, ttl_minutes) -> dict:
        hold_id = "hold_" + uuid.uuid4().hex[:12]
        created = datetime.now(timezone.utc)
        row = {
            "id": hold_id, "product_code": product_code, "title": title, "date": date,
            "travelers": travelers, "total": total, "currency": currency,
            "contact_name": contact_name, "contact_email": contact_email,
            "provider": provider, "provider_hold_ref": provider_hold_ref,
            "payment_url": payment_url, "status": "awaiting_payment",
            "created_at": created.isoformat(),
            "expires_at": (created + timedelta(minutes=ttl_minutes)).isoformat(),
        }
        self._db.execute(
            "INSERT INTO holds VALUES (:id,:product_code,:title,:date,:travelers,:total,"
            ":currency,:contact_name,:contact_email,:provider,:provider_hold_ref,"
            ":payment_url,:status,:created_at,:expires_at)", row)
        self._db.commit()
        return row

    def get_hold(self, hold_id: str) -> dict | None:
        r = self._db.execute("SELECT * FROM holds WHERE id=?", (hold_id,)).fetchone()
        return dict(r) if r else None

    def mark_hold_confirmed(self, hold_id: str) -> None:
        self._db.execute("UPDATE holds SET status='confirmed' WHERE id=?", (hold_id,))
        self._db.commit()

    # ── bookings ──
    def create_booking(self, hold: dict, provider_booking_ref: str) -> dict:
        ref = "ATB-" + uuid.uuid4().hex[:8].upper()
        row = {
            "ref": ref, "hold_id": hold["id"], "product_code": hold["product_code"],
            "title": hold["title"], "date": hold["date"], "travelers": hold["travelers"],
            "total": hold["total"], "currency": hold["currency"],
            "contact_name": hold["contact_name"], "contact_email": hold["contact_email"],
            "provider": hold["provider"], "provider_booking_ref": provider_booking_ref,
            "status": "CONFIRMED", "created_at": _now(), "cancelled_at": None,
        }
        self._db.execute(
            "INSERT INTO bookings VALUES (:ref,:hold_id,:product_code,:title,:date,"
            ":travelers,:total,:currency,:contact_name,:contact_email,:provider,"
            ":provider_booking_ref,:status,:created_at,:cancelled_at)", row)
        self._db.commit()
        return row

    def get_booking(self, ref: str) -> dict | None:
        r = self._db.execute("SELECT * FROM bookings WHERE ref=?", (ref,)).fetchone()
        return dict(r) if r else None

    def mark_booking_cancelled(self, ref: str) -> None:
        self._db.execute(
            "UPDATE bookings SET status='CANCELLED', cancelled_at=? WHERE ref=?",
            (_now(), ref))
        self._db.commit()

    def close(self) -> None:
        self._db.close()
