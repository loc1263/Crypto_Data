"""Tests de core/utils.py — normalización de nombres de archivo y serialización JSON."""

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from core.utils import normalize_symbol_for_filename, serialize_value


@pytest.mark.parametrize("symbol, expected", [
    ("DOGE/USDT", "DOGE_USDT"),
    ("BTC-USD", "BTC_USD"),
    ("ZEC/USDT:USDT", "ZEC_USDT_USDT"),
    ("BNBUSDT", "BNBUSDT"),
])
def test_normalize_symbol_for_filename(symbol, expected):
    assert normalize_symbol_for_filename(symbol) == expected


def test_serialize_value_nan_becomes_none():
    assert serialize_value(float("nan")) is None


def test_serialize_value_passthrough_list_and_dict():
    assert serialize_value([1, 2, 3]) == [1, 2, 3]
    assert serialize_value({"a": 1}) == {"a": 1}


def test_serialize_value_timestamp_and_datetime_to_isoformat():
    ts = pd.Timestamp("2026-08-22T12:00:00")
    assert serialize_value(ts) == ts.isoformat()
    dt = datetime(2026, 8, 22, 12, 0, 0)
    assert serialize_value(dt) == dt.isoformat()


def test_serialize_value_numpy_scalar_becomes_python_scalar():
    value = serialize_value(np.float64(3.5))
    assert value == 3.5
    assert isinstance(value, float)


def test_serialize_value_plain_value_passthrough():
    assert serialize_value(42) == 42
    assert serialize_value("hola") == "hola"
