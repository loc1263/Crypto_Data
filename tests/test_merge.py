"""Tests de core/merge.py — fusión de fuentes por índice y columnas de export."""

import numpy as np
import pandas as pd

from core.merge import build_export_columns, merge_all_sources


def _idx(labels: list[str]) -> pd.Index:
    return pd.Index(labels, name="Fecha")


def test_merge_all_sources_ffills_only_the_flagged_source():
    ohlcv = pd.DataFrame(
        {"Close": [100.0, 101.0, 102.0]},
        index=_idx(["2026-01-01 00:00", "2026-01-01 01:00", "2026-01-01 02:00"]),
    )
    # Funding solo tiene la primera hora -> debe forward-fillearse a las otras dos.
    funding = pd.DataFrame({"Funding_Rate": [0.0001]}, index=_idx(["2026-01-01 00:00"]))
    # OI solo tiene la hora del medio -> NO debe forward-fillearse (ffill=False para oi).
    oi = pd.DataFrame({"OI_Amount": [500.0]}, index=_idx(["2026-01-01 01:00"]))

    out = merge_all_sources(ohlcv, funding=funding, oi=oi)

    assert out["Funding_Rate"].tolist() == [0.0001, 0.0001, 0.0001]
    assert np.isnan(out["OI_Amount"].iloc[0])
    assert out["OI_Amount"].iloc[1] == 500.0
    assert np.isnan(out["OI_Amount"].iloc[2])


def test_merge_all_sources_skips_none_and_empty_sources():
    ohlcv = pd.DataFrame({"Close": [100.0, 101.0]}, index=_idx(["a", "b"]))
    out = merge_all_sources(ohlcv, funding=None, oi=pd.DataFrame(), ls_ratio=None, fut_taker=None)

    assert list(out.columns) == ["Close"]
    assert len(out) == 2


def test_build_export_columns_filters_and_orders_canonically():
    # Columnas en orden "desordenado" a propósito; build_export_columns debe
    # devolverlas en el orden canónico de EXPORT_COLUMNS_* y descartar las
    # que no pertenecen a ninguna lista conocida.
    df = pd.DataFrame({
        "OB_Spread": [1.0],
        "UNKNOWN_COLUMN": [999],
        "RSI14": [55.0],
        "Close": [100.0],
    })
    cols = build_export_columns(df)
    assert cols == ["Close", "RSI14", "OB_Spread"]
    assert "UNKNOWN_COLUMN" not in cols
