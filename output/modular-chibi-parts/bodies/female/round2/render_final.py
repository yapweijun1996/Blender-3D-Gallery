"""Render the reimported round-two garments and all requested outfit combinations."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT.parent)]
import render as studio
from common import arguments
from verify import asset_path

studio.OUT = ROOT / "renders"
studio.HERE = ROOT
studio.ASSETS = ROOT / ".runtime" / "modules"
setup_scene = studio.setup


def setup():
    scene, camera = setup_scene()
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 2
    return scene, camera


studio.setup = setup
studio.ASSETS.mkdir(exist_ok=True)
for slug in ("tshirt", "dress", "jeans", "hair-bob", "hair-spiky", "sneakers"):
    alias = studio.ASSETS / f"female-{slug}.glb"
    if not alias.is_symlink():
        alias.symlink_to(asset_path(slug))
studio.OUTFITS = {
    "bob-casual": ("hair-bob", "tshirt", "jeans", "sneakers"),
    "bob-dress": ("hair-bob", "dress", "sneakers"),
    "spiky-casual": ("hair-spiky", "tshirt", "jeans", "sneakers"),
}

if __name__ == "__main__":
    studio.main()
