"""pytest bootstrap.

Ensure the project root is importable so `from capcut... import ...`
resolves to the project package when pytest is run from the repo root.
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)

if ROOT in sys.path:
    sys.path.remove(ROOT)
sys.path.insert(0, ROOT)
