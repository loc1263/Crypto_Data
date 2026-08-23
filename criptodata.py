"""
criptodata.py — Punto de entrada de línea de comandos.

La lógica del programa vive en el paquete `core/` (config, exchange,
sources, indicators, merge, exports, cli) para que agregar una fuente de
datos, un indicador o un exchange nuevo no implique tocar un único archivo
monolítico. Ver README.md para el mapa completo de módulos.
"""

from core.cli import main

if __name__ == "__main__":
    main()
