"""
Test de core/exports/basic.py — solo la parte pura (`_export_basic_csv`):
enriquece con add_market_metrics y escribe a CSV. No cubre las funciones
`exportar_*` públicas porque descargan datos reales de Binance (requieren
red); ver mejoras_pendientes.md para mockear `sources/` a futuro.
"""

import pandas as pd
import pytest

from core.exports.basic import _BASIC_EXPORT_COLUMNS, _export_basic_csv


def test_export_basic_csv_writes_enriched_columns(tmp_path):
    raw_data = pd.DataFrame(
        {
            "Open": [100.0, 110.0],
            "High": [105.0, 115.0],
            "Low": [95.0, 108.0],
            "Close": [102.0, 112.0],
            "Volume": [10.0, 20.0],
        },
        index=pd.Index(["2026-08-20", "2026-08-21"], name="Fecha"),
    )
    out_file = tmp_path / "out.csv"

    ruta = _export_basic_csv(raw_data, out_file)

    assert ruta == str(out_file.resolve())
    written = pd.read_csv(out_file, index_col="Fecha")
    for col in _BASIC_EXPORT_COLUMNS:
        assert col in written.columns
    assert written["Variacion_%"].iloc[0] == pytest.approx((102.0 - 100.0) / 100.0 * 100)
