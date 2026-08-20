"""احراز هویت ساده API با کلید ثابت (API key) در هدر.

اگر متغیر محیطی ``VAMGAR_API_KEYS`` (کلیدهای مجاز، جدا شده با کاما) ست شده
باشد، هر endpoint (به‌جز ``/health``) باید هدر ``X-API-Key`` معتبر داشته
باشد. اگر ست نشده باشد، سرویس در حالت توسعه محلی بدون احراز هویت کار
می‌کند — **قبل از استقرار واقعی باید ست شود**.

این لایه هنوز چندمستأجری کامل (تفکیک اینکه هر کلاینت فقط به مرچنت‌های خودش
دسترسی داشته باشد) را پیاده نمی‌کند؛ آن نیاز به نگاشت مرچنت↔کلاینت روی
لایه persistence دارد (خارج از scope همین قدم).
"""

import os

from fastapi import Header, HTTPException, status


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    allowed = os.environ.get("VAMGAR_API_KEYS", "")
    allowed_keys = {k.strip() for k in allowed.split(",") if k.strip()}
    if not allowed_keys:
        return  # auth غیرفعال (VAMGAR_API_KEYS ست نشده - حالت توسعه محلی)
    if x_api_key not in allowed_keys:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key نامعتبر یا گمشده")
