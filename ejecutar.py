"""Lanzador de GENESIS. Funciona desde cualquier carpeta:

    python ejecutar.py visor
    python ejecutar.py --help
"""

import sys
from pathlib import Path

if sys.version_info < (3, 10):
    sys.exit("GENESIS necesita Python 3.10 o posterior. Tienes " + sys.version.split()[0])

sys.path.insert(0, str(Path(__file__).resolve().parent))

from genesis.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
