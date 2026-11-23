"""Build, gate and render new female garments in a single serial Blender job."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy
import numpy as np

import bake
import construct
import contacts
import fit_module as fit
import skirt_envelope
import render
from cache import load_scene
from common import BODY, HERE, arguments
from gate_module import LIMITS, SHIPPED, gate, layers_for

FRAMING = dict(hoodie=(.691, .79), jacket=(.510, .67), shorts=(.351, .48),
               skirt=(.365, .52), boots=(.074, .38))


def render_item(path):
    item = path.stem
    render.CUSTOM.update({item: path, **SHIPPED})
    render.FRAMING[item] = FRAMING[item]
    original = render.setup

    def setup():
        scene, camera = original()
        scene.render.threads_mode = "FIXED"
        scene.render.threads = 2
        scene.cycles.samples = 8
        return scene, camera

    render.setup = setup
    try:
        render.render_set([item, *layers_for(item)], render.ANGLES, item, item)
    finally:
        render.setup = original


def run_item(item, data, body):
    names = data[0]
    layers = {layer: fit.Module(SHIPPED[layer], names) for layer in layers_for(item)}
    attempts = HERE / "attempts" / item
    attempts.mkdir(parents=True, exist_ok=True)
    best = None
    history = []
    for number in range(1, 4):
        directory = attempts / str(number)
        directory.mkdir(exist_ok=True)
        path = directory / f"{item}.glb"
        gate_path = path.with_suffix(".gate.json")
        validator_path = path.with_suffix(".validator.json")
        if not (path.exists() and gate_path.exists() and validator_path.exists()):
            print("ROUND", item, number, flush=True)
            vents = None
            if number == 3 and item in {"hoodie", "jacket"}:
                previous = attempts / "2" / f"{item}.glb"
                prior = json.loads(previous.with_suffix(".gate.json").read_text())
                vents = contacts.underarm(previous, prior, data)
            seed, surface, faces, weights, direction, graph, colors = construct.construct(item, body, number, vents)
            assert len(faces) <= LIMITS[item], (item, len(faces))
            if item == "skirt":
                seed = skirt_envelope.clamp(seed, weights, direction, data)
            points, history_bake, unsafe = bake.bake(item, number, seed, surface, direction, faces, weights, graph, data)
            maximum_adjustment = float(np.linalg.norm(points - seed, axis=1).max() * 1000)
            vent_faces = 0
            if number == 3 and item in {"hoodie", "jacket", "shorts"}:
                points, faces, weights, colors, vent_faces = contacts.finish_vents(
                    item, points, surface, faces, weights, colors, unsafe)
            construct.write(path, points, faces, weights, colors, names, item)
            gate_report = gate(path, gate_path, data, layers)
            validate = subprocess.run(["node", str(HERE / "validate.cjs"), str(path)], cwd=HERE)
            if not validator_path.exists():
                raise RuntimeError(f"Khronos validator did not produce a report: {validate.returncode}")
            gate_report["bake"] = dict(samples=len(data[3]), margin_mm=bake.MARGIN * 1000,
                                       maximum_clearance_adjustment_mm=maximum_adjustment, vent_faces=vent_faces,
                                       iterations=history_bake)
        else:
            gate_report = json.loads(gate_path.read_text())
        validator = json.loads(validator_path.read_text())
        assert validator["sha256"] == gate_report["sha256"] == fit.sha(path)
        errors, warnings = (validator["issues"][key] for key in ("numErrors", "numWarnings"))
        gate_report["validator"] = dict(errors=errors, warnings=warnings)
        gate_report["round"] = number
        gate_report["pass"] = gate_report["geometry_and_budget_pass"] and errors == warnings == 0
        gate_path.write_text(json.dumps(gate_report, separators=(",", ":"), allow_nan=False) + "\n")
        clips = tuple(gate_report["clips"].values())
        layer_peaks = {name: max(row["peak_layer_pairs"][name] for row in clips) for name in layers}
        row = dict(item=item, triangles=gate_report["asset"]["triangles"],
                   mib=gate_report["asset"]["bytes"] / 2**20, peak_inside=max(r["peak_inside"] for r in clips),
                   peak_pairs=max(r["peak_pairs"] for r in clips), min_signed_mm=min(r["min_signed_mm"] for r in clips),
                   round=number, passed=gate_report["pass"], layers=layer_peaks,
                   issues=gate_report["issues"] + (["Khronos validation"] if errors or warnings else []))
        metric = (not row["passed"], bool(errors or warnings),
                  row["peak_pairs"] + 4 * row["peak_inside"] + sum(layer_peaks.values()) +
                  8 * max(0, .5 - row["min_signed_mm"]))
        history.append(row)
        if best is None or metric < best[0]:
            best = metric, path, row
        if row["passed"]:
            break
    _, path, row = best
    row = dict(row, rounds=len(history))
    final = HERE / path.name
    for suffix in (".glb", ".gate.json", ".validator.json"):
        shutil.copyfile(path.with_suffix(suffix), final.with_suffix(suffix))
    return final, row, history


def save_results(results):
    (HERE / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    lines = [
        "# Female modular wardrobe 3", "",
        "New surfaces start from the exported female body. The motion gate uses the female master",
        "and the 14-clip bank at 30 fps with 0.5-frame steps, authored endpoints, and rest.",
        "Clearance is the signed nearest-triangle distance. Each garment uses flat PBR materials.",
        "The retained GLB is checked against the other compatible shipped slots.", "",
        "| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed mm | Rounds | Result |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item, entry in results.items():
        row = entry["retained"]
        verdict = "PASS" if row["passed"] else "FAIL"
        lines.append(f"| {item} | {row['triangles']:,} | {row['mib']:.3f} | {row['peak_inside']} | "
                     f"{row['peak_pairs']} | {row['min_signed_mm']:.4f} | {row['rounds']} | {verdict} |")
    lines.extend(["", "## Files and findings", ""])
    for item, entry in results.items():
        row = entry["retained"]
        layer = ", ".join(f"{key} {value}" for key, value in row["layers"].items())
        issues = f" Gate findings are {', '.join(row['issues'])}." if row["issues"] else ""
        lines.append(f"- **{item}.** Retained round {row['round']}. Peak layer pairs were {layer}.{issues} "
                     f"[GLB]({item}.glb) · [gate]({item}.gate.json) · [Khronos]({item}.validator.json) · "
                     f"[six views](renders/{item}/views.json)")
    lines.extend(["", "[All round summaries](results.json)", "",
                  "Reproduce with `./run.sh wardrobe.py`. The launcher uses two threads.", ""])
    (HERE / "NOTES.md").write_text("\n".join(lines))


def main():
    jobs = arguments() or list(LIMITS)
    result_path = HERE / "results.json"
    results = json.loads(result_path.read_text()) if result_path.exists() else {}
    data = load_scene()
    body = fit.Module(BODY, data[0])
    print("SAMPLES", len(data[3]), flush=True)
    for item in jobs:
        path, row, history = run_item(item, data, body)
        results[item] = dict(retained=row, attempts=history)
        save_results(results)
        render_item(path)
    print("COMPLETE", jobs, flush=True)


if __name__ == "__main__":
    main()
