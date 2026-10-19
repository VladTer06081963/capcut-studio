"""pytest bootstrap.

This project ships a top-level `py/` package, which collides with the legacy
`py` shim that pytest registers in `sys.modules`. Drop the shim and put the
project root first on `sys.path` so `from py.render import ...` resolves to
the project package. (`python3 -m unittest discover -s tests` needs none of this.)
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)

for _name in [n for n in sys.modules if n == "py" or n.startswith("py.")]:
    del sys.modules[_name]
if ROOT in sys.path:
    sys.path.remove(ROOT)
sys.path.insert(0, ROOT)
