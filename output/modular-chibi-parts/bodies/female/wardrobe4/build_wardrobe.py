"""Build one round at a time so visual inspection can drive the next revision."""
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bake
import construct
import fit_module as fit
import garments
import render
import polish
import numpy as np
from cache import load_scene
from common import BODY, HERE, arguments
from gate_module import SHIPPED, gate, layers_for

FRAMING = {"hoodie": (.527, .65), "jacket": (.520, .65),
           "skirt": (.359, .49), "shorts": (.353, .49)}


def render_item(item, path, folder, number):
    render.CUSTOM.update({item: path, **SHIPPED})
    render.FRAMING[item] = FRAMING[item]
    render.OUT = folder
    layers = [name for name in layers_for(item) if name != "boots"]
    if number == 1 and item == "hoodie":
        checks = {}
    elif item in {"hoodie", "jacket"}:
        poses = (("walk", 34.5), ("wave", 24.), ("dance", 38.5))
        checks = {f"{pose}-{view}": (pose, frame, view) for view in ("front", "front-right") for pose, frame in poses}
    else:
        poses = (("walk", 57.5), ("run", 12.), ("sit_down", 27.5))
        checks = {f"{pose}-{view}": (pose, frame, view) for view in ("front", "front-right") for pose, frame in poses}
    images = render.render_set([item, *layers], render.ANGLES, item, "renders", motion_views=checks)
    sheet = folder / "renders/six-view.png"
    render.sheet([images[:3], images[3:6]], sheet)
    motion = sheet.with_name("motion-six-view.png")
    if checks:
        render.sheet([images[6:9], images[9:12]], motion)
    manifest = sheet.with_name("views.json")
    record = json.loads(manifest.read_text())
    record["sheet_sha256"] = fit.sha(sheet)
    if checks:
        record["motion_sheet_sha256"] = fit.sha(motion)
    manifest.write_text(json.dumps(record, indent=2) + "\n")


def witness_vertices(report):
    frames = [frame for clip in report["clips"].values() for frame in clip["frames"]]
    body = [frame["vertex"] for frame in frames if frame["min_signed_mm"] < .5]
    tubes = [frame["tube_vertex"] for frame in frames if frame.get("tube_min_signed_mm", 2.) < 1.5]
    return body, tubes


def stabilize_export(path, report, data, layers):
    bad, leg = witness_vertices(report)
    mesh = fit.Module(path, data[0])
    vertices = np.unique(mesh.unweld[bad + leg])
    if not 0 < len(vertices) <= 24 or any(clip["peak_pairs"] for clip in report["clips"].values()):
        return report
    legs = np.unique(mesh.unweld[leg])
    weights = mesh.welded(mesh.weights)
    moved = mesh.points
    if len(legs):
        moved = polish.solve(moved, mesh.faces, weights, data, legs, .00185, robust=True)
    body_only = np.setdiff1d(vertices, legs)
    if len(body_only):
        moved = polish.solve(moved, mesh.faces, weights, data, body_only, .00135, robust=True)
    if np.array_equal(moved, mesh.points):
        return report
    normal = fit.gltf_axes(construct.normals(moved, mesh.faces)).astype(np.float32)
    xyz = fit.gltf_axes(moved).astype(np.float32)
    for attrs, indices in mesh.parts:
        used = mesh.unweld[indices]
        values = xyz[used]
        mesh.glb.accessor(attrs["POSITION"])[:] = values
        mesh.glb.accessor(attrs["NORMAL"])[:] = normal[used]
        mesh.glb.doc["accessors"][attrs["POSITION"]].update(min=values.min(axis=0).tolist(),
                                                         max=values.max(axis=0).tolist())
    checkpoint = path.read_bytes()
    mesh.glb.write(path)
    output = path.with_suffix(".gate.json")
    result = gate(path, output, data, layers)
    if not result["geometry_and_budget_pass"]:
        old_failures = sum(map(len, witness_vertices(report)))
        new_failures = sum(map(len, witness_vertices(result)))
        newly_bad = set(result["issues"]) - set(report["issues"])
        if newly_bad or new_failures >= old_failures:
            path.write_bytes(checkpoint)
            return report
    result["export_stabilization"] = dict(checked_vertices=len(vertices), posed_probe_mm=.075)
    return result


def main():
    item, number, *flags = arguments()
    number = int(number)
    assert 1 <= number <= 3
    folder = HERE / "attempts" / item / str(number)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{item}.glb"
    if "--render-only" not in flags:
        data = load_scene()
        names = data[0]
        layers = {name: fit.Module(SHIPPED[name], names) for name in layers_for(item)}
        target = path.with_suffix(".gate.json")
        if "--stabilize" in flags:
            previous = json.loads(target.read_text())
            history = previous["bake"]
            if item == "shorts" and "tube_vertex" not in previous["clips"]["rest"]["frames"][0]:
                previous = gate(path, target, data, layers)
            report = stabilize_export(path, previous, data, layers)
        else:
            body = fit.Module(BODY, names)
            if item in {"hoodie", "jacket"}:
                seed, faces, weights, colors = garments.top(item, body, number, layers, data)
            else:
                seed, faces, weights, colors = garments.bottom(item, body, number, data)
            graph = fit.adjacency(faces, len(seed))
            points, weights, history = bake.bake(item, number, seed, faces, weights, graph, data, layers)
            construct.write(path, points, faces, weights, colors, names, item)
            report = gate(path, target, data, layers)
            clearance_issues = {"Posed body clearance", "Shorts leg tube clearance"}
            if item in {"skirt", "shorts"} and number == 3 and set(report["issues"]) & clearance_issues:
                report = stabilize_export(path, report, data, layers)
                if set(report["issues"]) & clearance_issues and "export_stabilization" in report:
                    report = stabilize_export(path, report, data, layers)
        subprocess.run(["node", str(HERE / "validate.cjs"), str(path)], check=False)
        validator = json.loads(path.with_suffix(".validator.json").read_text())
        assert validator["sha256"] == report["sha256"]
        issues = validator["issues"]
        report.update(round=number, bake=history, validator={key: issues[key] for key in ("numErrors", "numWarnings")})
        report["pass"] = report["geometry_and_budget_pass"] and issues["numErrors"] == issues["numWarnings"] == 0
        if item == "shorts" and number == 3:
            report["pattern_reference"] = dict(file="round3/female-jeans-v3.glb",
                                               sha256=fit.sha(SHIPPED["jeans"]),
                                               purpose="Female fit topology and skin weights")
        target.write_text(json.dumps(report, separators=(",", ":"), allow_nan=False) + "\n")
    render_item(item, path, folder, number)


if __name__ == "__main__":
    main()
