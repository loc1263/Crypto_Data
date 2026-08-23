"""Utilidades genéricas: nombres de archivo y serialización a JSON."""

from datetime import datetime

import numpy as np
import pandas as pd


def normalize_symbol_for_filename(symbol: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in symbol)


def serialize_value(value):
    if isinstance(value, (list, dict)):
        return value
    if pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    return value
