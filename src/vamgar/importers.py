"""تبدیل داده خام export شده (CSV) منابع بیرونی به مدل ``Transaction``.

اولین قدم عملی به‌سمت اتصال منابع داده واقعی (کارت‌خوان/PSP/مارکت‌پلیس):
اکثر این منابع در عمل یا API زنده می‌دهند یا export دوره‌ای CSV/Excel. این
ماژول فرمت رایج CSV (ستون تاریخ + ستون مبلغ، با چند نام‌گذاری متداول) را
می‌پذیرد و به لیستی از ``Transaction`` معتبر تبدیل می‌کند تا مستقیم وارد
پایپ‌لاین ``cashflow``/``engine`` شود.
"""

import csv
import io
from datetime import datetime

from src.vamgar.schemas import Transaction, TransactionSource

# نام‌های رایج ستون تاریخ/مبلغ در exportهای مختلف کارت‌خوان/PSP/مارکت‌پلیس.
_DATE_KEYS = ("date", "timestamp", "تاریخ")
_AMOUNT_KEYS = ("amount", "مبلغ")


class CSVImportError(ValueError):
    """CSV ورودی ساختار قابل‌قبول ندارد (ستون گمشده یا مقدار نامعتبر)."""


def _find_key(fieldnames: list[str], candidates: tuple[str, ...]) -> str:
    lowered = {f.strip().lower(): f for f in fieldnames}
    for c in candidates:
        if c in lowered:
            return lowered[c]
    raise CSVImportError(
        f"هیچ‌کدام از ستون‌های مورد انتظار {candidates} در هدر CSV پیدا نشد: {fieldnames}"
    )


def parse_csv_transactions(
    csv_text: str, merchant_id: str, source: TransactionSource
) -> list[Transaction]:
    """متن CSV (با هدر) را به لیست ``Transaction`` تبدیل می‌کند.

    ستون تاریخ باید ISO 8601 قابل‌پارس باشد (``date`` یا ``timestamp``)،
    ستون مبلغ باید عدد باشد (``amount``؛ منفی = خروج پول). خط‌های خالی
    رد می‌شوند. اگر هیچ ردیف معتبری وجود نداشته باشد یا ساختار هدر ناقص
    باشد، ``CSVImportError`` می‌دهد.
    """
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise CSVImportError("CSV ورودی هدر ندارد یا خالی است")

    date_key = _find_key(reader.fieldnames, _DATE_KEYS)
    amount_key = _find_key(reader.fieldnames, _AMOUNT_KEYS)

    transactions: list[Transaction] = []
    for row_num, row in enumerate(reader, start=2):  # ردیف ۱ هدر است
        if not row.get(date_key) and not row.get(amount_key):
            continue  # خط کاملاً خالی
        try:
            timestamp = datetime.fromisoformat(row[date_key].strip())
        except (KeyError, ValueError, AttributeError) as exc:
            raise CSVImportError(f"ردیف {row_num}: تاریخ نامعتبر '{row.get(date_key)}'") from exc
        try:
            amount = float(row[amount_key].strip())
        except (KeyError, ValueError, AttributeError) as exc:
            raise CSVImportError(f"ردیف {row_num}: مبلغ نامعتبر '{row.get(amount_key)}'") from exc

        transactions.append(
            Transaction(merchant_id=merchant_id, timestamp=timestamp, amount=amount, source=source)
        )

    if not transactions:
        raise CSVImportError("هیچ ردیف معتبری در CSV پیدا نشد")

    return transactions
