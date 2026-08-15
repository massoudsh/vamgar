import pytest

from src.vamgar.importers import CSVImportError, parse_csv_transactions
from src.vamgar.schemas import TransactionSource


def test_parses_valid_csv_with_standard_headers():
    csv_text = (
        "date,amount\n"
        "2026-01-01T10:00:00,-1000000\n"
        "2026-01-02T10:00:00,200000\n"
    )

    transactions = parse_csv_transactions(csv_text, "m1", TransactionSource.POS)

    assert len(transactions) == 2
    assert transactions[0].amount == -1_000_000
    assert transactions[0].merchant_id == "m1"
    assert transactions[0].source == TransactionSource.POS


def test_accepts_persian_and_alternate_column_names():
    csv_text = "تاریخ,مبلغ\n2026-01-01T10:00:00,500000\n"

    transactions = parse_csv_transactions(csv_text, "m2", TransactionSource.PSP)

    assert len(transactions) == 1
    assert transactions[0].amount == 500_000


def test_skips_blank_rows():
    csv_text = "date,amount\n2026-01-01T10:00:00,500000\n,\n2026-01-02T10:00:00,300000\n"

    transactions = parse_csv_transactions(csv_text, "m1", TransactionSource.POS)

    assert len(transactions) == 2


def test_missing_amount_column_raises_import_error():
    csv_text = "date,total\n2026-01-01T10:00:00,500000\n"

    with pytest.raises(CSVImportError):
        parse_csv_transactions(csv_text, "m1", TransactionSource.POS)


def test_invalid_amount_value_raises_import_error():
    csv_text = "date,amount\n2026-01-01T10:00:00,not-a-number\n"

    with pytest.raises(CSVImportError):
        parse_csv_transactions(csv_text, "m1", TransactionSource.POS)


def test_empty_csv_raises_import_error():
    with pytest.raises(CSVImportError):
        parse_csv_transactions("date,amount\n", "m1", TransactionSource.POS)
