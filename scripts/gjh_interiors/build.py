"""Blender entry point. Run with -- [--model SLUG] [--geometry-only | --previews-only]."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from geometry import Fixture
from surfaces import make_surface
from previews import render_views

ROOT = HERE.parents[1]
PROGRAM = json.loads((HERE / "program.json").read_text())
FILES = {"Low":"lod1.glb", "Balanced":"balanced.glb", "Detailed":"optimized.glb"}


def export(spec, tier, builder, folder, primary):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1
    f = Fixture(spec,tier)
    builder(f)
    if not f.parts:
        raise ValueError(f"Empty fixture: {spec['slug']}")
    root = f.finish(make_surface(spec))
    root["store"] = spec["slot"]
    root["tier"] = tier
    root["origin"] = "Bottom centre of installed envelope; glTF +Z display front."
    filename = "optimized.glb" if primary else FILES[tier]
    target = folder / "exports" / filename
    target.parent.mkdir(exist_ok=True)
    if primary:
        source = folder / "sources" / (spec["slug"]+".blend")
        source.parent.mkdir(exist_ok=True)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
    bpy.ops.export_scene.gltf(filepath=str(target),export_format="GLB",export_yup=True,
                              export_animations=False,export_extras=False,export_cameras=False,
                              export_lights=False,export_tangents=False,export_image_format="AUTO")
    import struct
    raw = target.read_bytes()
    gltf = json.loads(raw[20:20+struct.unpack_from("<I",raw,12)[0]])
    tris = sum(gltf["accessors"][p["indices"]]["count"]//3 for m in gltf["meshes"] for p in m["primitives"])
    cap = spec["anchor"]["triangles_per_instance"][tier]
    print("EXPORTED",spec["slug"],tier,tris,cap,flush=True)
    if tris > cap:
        raise ValueError(f"{spec['slug']} {tier} exceeds cap: {tris}/{cap}")


def options():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",action="append")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--geometry-only",action="store_true")
    mode.add_argument("--previews-only",action="store_true")
    return parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])


def run_model(slug, builder, args=None):
    args = args or options()
    spec = next(s for s in PROGRAM["stores"] if s["slug"]==slug)
    folder = ROOT / "models" / slug
    tiers = ["Low","Balanced"] + (["Detailed"] if "order" in spec else [])
    if not args.previews_only:
        for tier in tiers:
            export(spec,tier,builder,folder,tier==tiers[-1])
    if not args.geometry_only:
        render_views(folder,spec)


def main():
    args = options()
    ordered = sorted(PROGRAM["stores"],key=lambda s:s.get("order",99))
    selected = [s for s in ordered if not args.model or s["slug"] in args.model]
    if args.model and set(args.model)!={s["slug"] for s in selected}:
        raise ValueError("Unknown model selection")
    for spec in selected:
        path = ROOT / "models" / spec["slug"] / "generate.py"
        module = importlib.util.spec_from_file_location("gjh_fixture",path)
        generator = importlib.util.module_from_spec(module)
        module.loader.exec_module(generator)
        run_model(spec["slug"],generator.build,args)


if __name__ == "__main__":
    main()
