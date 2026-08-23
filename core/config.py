"""Configuración del script: ruta de config.json y opciones de menú."""

import json
from pathlib import Path

# core/config.py -> parent = core/, parent.parent = CryptoData/
# (config.json vive junto a criptodata.py, en la raíz de CryptoData/)
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

# Todas las exportaciones (CSV/JSON) se guardan aquí, no en la raíz del
# proyecto, para no dejar archivos sueltos junto al código.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

TIMEFRAME_OPTIONS = {
    "1": "5m",
    "2": "15m",
    "3": "1h",
    "4": "4h",
    "5": "1d",
}

RANGE_OPTIONS_MS = {
    "1": ("24h",  24 * 60 * 60 * 1000),
    "2": ("48h",  48 * 60 * 60 * 1000),
    "3": ("7d",    7 * 24 * 60 * 60 * 1000),
    "4": ("30d",  30 * 24 * 60 * 60 * 1000),
    "5": ("60d",  60 * 24 * 60 * 60 * 1000),
    "6": ("90d",  90 * 24 * 60 * 60 * 1000),
    "7": ("180d", 180 * 24 * 60 * 60 * 1000),
}


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)
