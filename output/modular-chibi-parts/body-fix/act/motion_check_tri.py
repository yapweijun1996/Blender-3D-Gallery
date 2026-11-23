"""Run the triangle-overlap variant of motion_check.py with the same arguments."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from motion_check import garment_check
garment_check(triangles=True)
