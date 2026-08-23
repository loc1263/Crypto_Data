"""Tests de core/config.py — carga de config.json y opciones fijas del menú."""

from core.config import RANGE_OPTIONS_MS, TIMEFRAME_OPTIONS, load_config


def test_load_config_reads_real_config_json():
    cfg = load_config()
    assert cfg["exchange"] == "binance"
    assert "DOGE/USDT" in cfg["symbols"]
    assert cfg["default_symbol"] in cfg["symbols"]


def test_timeframe_options_are_valid_binance_timeframes():
    assert set(TIMEFRAME_OPTIONS.values()) == {"5m", "15m", "1h", "4h", "1d"}


def test_range_options_ms_increase_with_key_order():
    # Cada rango (en ms) debe ser estrictamente mayor que el anterior, en el
    # mismo orden en que se listan en el menú (24h, 48h, 7d, ... 180d).
    values_ms = [ms for _, ms in RANGE_OPTIONS_MS.values()]
    assert values_ms == sorted(values_ms)
    assert len(set(values_ms)) == len(values_ms)
