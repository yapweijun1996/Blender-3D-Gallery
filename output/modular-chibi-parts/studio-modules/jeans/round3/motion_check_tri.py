"""Check garment/body triangle intersections on every corrected half frame."""

from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("motion_check.py")))["run"](triangles=True)
