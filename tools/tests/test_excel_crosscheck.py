"""Unit tests for the cached-value conversion in tools/excel_crosscheck.py.
Author: Claude Code (AI agent) — scaffold; see ATTRIBUTION.md
"""
import datetime as dt
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from harness import common as C  # noqa: E402
from harness import compare as CMP  # noqa: E402
from tools import excel_crosscheck as X  # noqa: E402


def test_blank_and_bool():
    assert X.excel_cell(None, False) is None
    assert X.excel_cell("", False) is None
    assert X.excel_cell(True, False) == "TRUE"


def test_dates_from_datetime_and_serial():
    assert X.excel_cell(dt.datetime(2028, 3, 12), True) == dt.date(2028, 3, 12)
    assert X.excel_cell(46824, True) == dt.date(2028, 3, 12)


def test_error_text_becomes_error_value():
    v = X.excel_cell("#N/A", False)
    assert isinstance(v, C.ErrorValue) and v.code == "#N/A"


def test_numbers_compare_with_oracle_values():
    assert CMP.diff_kind(2414.95, X.excel_cell(2414.95, False)) is None
    assert CMP.diff_kind(2414.95, X.excel_cell(2414.96, False)) == "numeric"
    assert CMP.diff_kind("REFER", X.excel_cell("REFER", False)) is None
