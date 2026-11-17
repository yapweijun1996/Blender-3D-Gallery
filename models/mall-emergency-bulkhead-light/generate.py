"""Rebuild this wall fixture using the shared geometry and delivery scripts."""
from functools import partial
from pathlib import Path
import runpy
import sys

asset_dir = Path(__file__).resolve().parent
scripts = asset_dir.parents[1] / "scripts"
sys.path.insert(0, str(scripts))
from mall_lighting_delivery import deliver

geometry = runpy.run_path(str(scripts / "mall-wall-lights.py"))
slug = asset_dir.name
x, y, z = geometry["VIEWS"][slug]
deliver(asset_dir, geometry["SLUGS"][slug], partial(geometry["build"], slug), (x, z, -y))
