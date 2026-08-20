"""قرارداد مشترک برای اتصال زنده به منابع داده واقعی (کارت‌خوان/PSP/مارکت‌پلیس).

این ماژول عمداً پیاده‌سازی واقعی هیچ vendor را ندارد: هر ارائه‌دهنده (POS/PSP/
مارکت‌پلیس) مستندات API، احراز هویت و فرمت پاسخ خاص خودش را دارد که بدون
مستندات رسمی و credential واقعی آن نمی‌توان به‌درستی و امن پیاده‌سازی کرد.

این کلاس فقط قرارداد (interface) یکسانی تعریف می‌کند تا هر پیاده‌سازی
vendor-specific آینده (``connectors/pos_x.py``, ``connectors/psp_y.py``, ...)
همین شکل را دنبال کند و مستقیم در پایپ‌لاین ``cashflow``/``engine`` قابل‌استفاده باشد.
"""

from abc import ABC, abstractmethod
from datetime import date

from src.vamgar.schemas import Transaction


class TransactionConnector(ABC):
    """پایه انتزاعی هر اتصال زنده به منبع تراکنش خارجی."""

    @abstractmethod
    def fetch_transactions(
        self, merchant_id: str, since: date, until: date
    ) -> list[Transaction]:
        """تراکنش‌های خام یک مرچنت را در بازه [since, until] از API واقعی می‌گیرد.

        پیاده‌سازی هر vendor باید:
        - احراز هویت خودش (API key/OAuth) را مدیریت کند.
        - pagination/rate limit سمت vendor را رعایت کند.
        - خروجی را به مدل ``Transaction`` این پروژه map کند (نه ساختار خام vendor).
        """
        raise NotImplementedError
