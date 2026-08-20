"""لایه persistence ساده (SQLite) برای تراکنش‌های خام import‌شده و تاریخچه تصمیم‌های اعتباری.

سرویس اصلی قبل از این کاملاً stateless بود (هر request از صفر پردازش می‌شد).
این ماژول دو چیز اضافه می‌کند:
1. ذخیره idempotent تراکنش‌های خام (import تکراری همان داده رکورد تکراری نمی‌سازد).
2. تاریخچه تصمیم‌های اعتباری هر مرچنت، برای audit/بازبینی بعدی.

مسیر دیتابیس با متغیر محیطی ``VAMGAR_DB_PATH`` قابل تنظیم است (پیش‌فرض: ``vamgar.db``).
"""

import hashlib
import os
import sqlite3
from datetime import datetime, timezone

from src.vamgar.schemas import CreditDecision, Transaction


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
            created_at TEXT NOT NULL
        )
        """
    )
    return conn


def _dedupe_key(tx: Transaction) -> str:
    """کلید یکتای هر تراکنش برای idempotent بودن import (بدون شناسه خارجی)."""
    raw = f"{tx.merchant_id}|{tx.timestamp.isoformat()}|{tx.amount}|{tx.source.value}"
    return hashlib.sha256(raw.encode()).hexdigest()


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


def save_decision(decision: CreditDecision) -> None:
    """یک تصمیم اعتباری را در تاریخچه مرچنت ثبت می‌کند."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO decisions "
            "(merchant_id, risk_score, recommended_credit_limit, repayment_model, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                decision.merchant_id,
                decision.risk_score,
                decision.recommended_credit_limit,
                decision.repayment_model,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_decision_history(merchant_id: str, limit: int = 50) -> list[dict]:
    """آخرین تصمیم‌های اعتباری یک مرچنت را (جدیدترین اول) برمی‌گرداند."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT merchant_id, risk_score, recommended_credit_limit, repayment_model, created_at "
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
            }
            for r in rows
        ]
    finally:
        conn.close()
