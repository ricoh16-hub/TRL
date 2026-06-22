import sys
import os
import traceback

# Ensure project root is on sys.path so `import src` works when run from scripts/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT, "src")
# The package layout expects `src/` to be on PYTHONPATH so imports like
# `from ui.boot import ...` resolve to `src/ui`.
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    import main
    print("imported main successfully")
except Exception:
    traceback.print_exc()
    sys.exit(1)
