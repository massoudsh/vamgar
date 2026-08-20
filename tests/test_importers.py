import io
from datetime import datetime

import pytest
from openpyxl import Workbook

from src.vamgar.importers import (
    CSVImportError,
    XLSXImportError,
    parse_csv_transactions,
    parse_xlsx_transactions,
)
from src.vamgar.schemas import TransactionSource


def _xlsx_bytes(header: list[str], rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(header)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


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


def test_parses_valid_xlsx_with_real_date_and_number_cells():
    content = _xlsx_bytes(
        ["date", "amount"],
        [[datetime(2026, 1, 1, 10, 0, 0), -1_000_000], [datetime(2026, 1, 2, 10, 0, 0), 200_000]],
    )

    transactions = parse_xlsx_transactions(content, "m1", TransactionSource.POS)

    assert len(transactions) == 2
    assert transactions[0].amount == -1_000_000
    assert transactions[0].timestamp == datetime(2026, 1, 1, 10, 0, 0)


def test_parses_xlsx_with_string_date_and_amount_cells():
    content = _xlsx_bytes(["date", "amount"], [["2026-01-01T10:00:00", "500000"]])

    transactions = parse_xlsx_transactions(content, "m1", TransactionSource.PSP)

    assert len(transactions) == 1
    assert transactions[0].amount == 500_000


def test_xlsx_skips_blank_rows():
    content = _xlsx_bytes(
        ["date", "amount"],
        [[datetime(2026, 1, 1), 500_000], [None, None], [datetime(2026, 1, 2), 300_000]],
    )

    transactions = parse_xlsx_transactions(content, "m1", TransactionSource.POS)

    assert len(transactions) == 2


def test_xlsx_missing_amount_column_raises_import_error():
    content = _xlsx_bytes(["date", "total"], [[datetime(2026, 1, 1), 500_000]])

    with pytest.raises(XLSXImportError):
        parse_xlsx_transactions(content, "m1", TransactionSource.POS)


def test_xlsx_invalid_amount_value_raises_import_error():
    content = _xlsx_bytes(["date", "amount"], [[datetime(2026, 1, 1), "not-a-number"]])

    with pytest.raises(XLSXImportError):
        parse_xlsx_transactions(content, "m1", TransactionSource.POS)


def test_empty_xlsx_raises_import_error():
    content = _xlsx_bytes(["date", "amount"], [])

    with pytest.raises(XLSXImportError):
        parse_xlsx_transactions(content, "m1", TransactionSource.POS)
