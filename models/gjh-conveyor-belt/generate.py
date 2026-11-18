"""Build the gjh-conveyor-belt GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive


def retopology(f,source):
    for o in source.objects:
        name = o.name
        group = name.split("_")[0].split(".")[0]
        f.group = {"LEG":"Trestles","FRAME":"Frame and motor","DRIVE":"Frame and motor",
                   "BELT":"Belt and carriers","ROLLER":"Return rollers"}[group]
        if group=="ROLLER":
            source.copy(o,1,simplify=.5 if not f.level else .1)
        else:
            color = 3 if group=="BELT" else 2 if group=="DRIVE" or "Carrier" in name else 0
            source.copy(o,2 if "Carrier" in name else color,bevel=.005)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
