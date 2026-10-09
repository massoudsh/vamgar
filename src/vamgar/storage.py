"""لایه persistence ساده (SQLite) برای تراکنش‌های خام import‌شده و تاریخچه تصمیم‌های اعتباری.

سرویس اصلی قبل از این کاملاً stateless بود (هر request از صفر پردازش می‌شد).
این ماژول دو چیز اضافه می‌کند:
1. ذخیره idempotent تراکنش‌های خام (import تکراری همان داده رکورد تکراری نمی‌سازد).
2. تاریخچه تصمیم‌های اعتباری هر مرچنت، برای audit/بازبینی بعدی — شامل
   hash ورودی، endpoint منبع، و نسخه موتور (immutable audit trail).

مسیر دیتابیس با متغیر محیطی ``VAMGAR_DB_PATH`` قابل تنظیم است (پیش‌فرض: ``vamgar.db``).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from src.vamgar.schemas import CreditDecision, Transaction

# نسخه‌ی منطقی موتور امتیازدهی — با تغییر فرمول در engine.py باید bump شود.
ENGINE_VERSION = "1.1.0"


def _db_path() -> str:
    return os.environ.get("VAMGAR_DB_PATH", "vamgar.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            dedupe_key TEXT PRIMARY KEY,
            merchant_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            amount REAL NOT NULL,
            source TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            merchant_id TEXT NOT NULL,
            risk_score REAL NOT NULL,
            recommended_credit_limit REAL NOT NULL,
            repayment_model TEXT NOT NULL,
            created_at TEXT NOT NULL,
            request_id TEXT,
            source_endpoint TEXT,
            input_hash TEXT,
            engine_version TEXT,
            decision_json TEXT
        )
        """
    )
    _migrate_decisions(conn)
    return conn


def _migrate_decisions(conn: sqlite3.Connection) -> None:
    """ستون‌های audit را روی دیتابیس‌های قدیمی اضافه می‌کند (idempotent)."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(decisions)").fetchall()}
    for name, decl in (
        ("request_id", "TEXT"),
        ("source_endpoint", "TEXT"),
        ("input_hash", "TEXT"),
        ("engine_version", "TEXT"),
        ("decision_json", "TEXT"),
    ):
        if name not in cols:
            conn.execute(f"ALTER TABLE decisions ADD COLUMN {name} {decl}")
    conn.commit()


def _dedupe_key(tx: Transaction) -> str:
    """کلید یکتای هر تراکنش برای idempotent بودن import (بدون شناسه خارجی)."""
    raw = f"{tx.merchant_id}|{tx.timestamp.isoformat()}|{tx.amount}|{tx.source.value}"
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_input(payload: Any) -> str:
    """SHA-256 پایدار از payload ورودی (برای audit بدون ذخیرهٔ خام حساس)."""
    canonical = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_transactions(transactions: list[Transaction]) -> int:
    """تراکنش‌ها را idempotent ذخیره می‌کند؛ تعداد رکورد واقعاً جدید (غیرتکراری) را برمی‌گرداند."""
    if not transactions:
        return 0
    conn = _connect()
    try:
        before = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO transactions (dedupe_key, merchant_id, timestamp, amount, source) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (_dedupe_key(tx), tx.merchant_id, tx.timestamp.isoformat(), tx.amount, tx.source.value)
                for tx in transactions
            ],
        )
        conn.commit()
        return conn.total_changes - before
    finally:
        conn.close()


def save_decision(
    decision: CreditDecision,
    *,
    source_endpoint: str = "unknown",
    input_payload: Any = None,
    request_id: str | None = None,
) -> str:
    """یک تصمیم اعتباری را با متادیتای audit در تاریخچه مرچنت ثبت می‌کند.

    Returns:
        request_id اختصاص‌داده‌شده به این تصمیم (برای پیگیری).
    """
    rid = request_id or str(uuid.uuid4())
    input_hash = hash_input(input_payload) if input_payload is not None else None
    created_at = datetime.now(timezone.utc).isoformat()
    decision_json = decision.model_dump_json()

    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO decisions "
            "(merchant_id, risk_score, recommended_credit_limit, repayment_model, created_at, "
            " request_id, source_endpoint, input_hash, engine_version, decision_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                decision.merchant_id,
                decision.risk_score,
                decision.recommended_credit_limit,
                decision.repayment_model,
                created_at,
                rid,
                source_endpoint,
                input_hash,
                ENGINE_VERSION,
                decision_json,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return rid


def get_decision_history(merchant_id: str, limit: int = 50) -> list[dict]:
    """آخرین تصمیم‌های اعتباری یک مرچنت را (جدیدترین اول) برمی‌گرداند."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT merchant_id, risk_score, recommended_credit_limit, repayment_model, created_at, "
            "request_id, source_endpoint, input_hash, engine_version "
            "FROM decisions WHERE merchant_id = ? ORDER BY id DESC LIMIT ?",
            (merchant_id, limit),
        ).fetchall()
        return [
            {
                "merchant_id": r[0],
                "risk_score": r[1],
                "recommended_credit_limit": r[2],
                "repayment_model": r[3],
                "created_at": r[4],
                "request_id": r[5],
                "source_endpoint": r[6],
                "input_hash": r[7],
                "engine_version": r[8],
            }
            for r in rows
        ]
    finally:
        conn.close()
