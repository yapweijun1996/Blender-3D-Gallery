"""Build the gjh-hawker-stall-exhaust-hood GJH interior master in Blender 5.x."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "gjh_interiors"))
from build import run_model

from library import derive


def retopology(f,source):
    for o in source.objects:
        name = o.name
        group = name.split("_")[0]
        f.group = {"HOUSING":"Copper canopy","DUCT":"Exhaust collar","FILTER":"Removable filter banks"}[group]
        color = 3 if group=="HOUSING" else 0 if group=="DUCT" else 1
        if "Baffle" in name:
            color = 2
        source.copy(o,color,1 if group=="HOUSING" else 0, .003 if group!="FILTER" else 0)


def build(f):
    derive(f,retopology)


if __name__ == "__main__":
    run_model(Path(__file__).resolve().parent.name, build)
