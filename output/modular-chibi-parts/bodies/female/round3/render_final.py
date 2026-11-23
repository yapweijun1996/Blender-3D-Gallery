"""Capture the final jeans from the same six rest cameras used in round two."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import render as studio
from verify import staged_assets

setup_scene = studio.setup


def setup():
    scene, camera = setup_scene()
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    return scene, camera


studio.setup = setup
studio.OUT = ROOT / "renders"
studio.HERE = ROOT
studio.ASSETS = staged_assets(("jeans",))
studio.render_set(["jeans"], studio.ANGLES, "jeans", "jeans")
