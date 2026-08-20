import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """هر تست دیتابیس sqlite جدا و موقت می‌گیرد تا vamgar.db واقعی پروژه دست‌نخورده بماند."""
    monkeypatch.setenv("VAMGAR_DB_PATH", str(tmp_path / "test-vamgar.db"))
    monkeypatch.delenv("VAMGAR_API_KEYS", raising=False)
