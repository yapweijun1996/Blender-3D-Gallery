"""Measure garment/body triangle crossings and report the body-only baseline."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("motion_check.py")))["check"](triangle=True)
