"""Bind visual review outcomes to the rendered GLBs and stage retained candidates."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ORDER = ("hoodie", "skirt", "jacket", "shorts")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def record(item, number, verdict, observation):
    folder = HERE / "attempts" / item / str(number)
    asset = folder / f"{item}.glb"
    gate = read(asset.with_suffix(".gate.json"))
    checks = read(asset.with_suffix(".validator.json"))
    views = read(folder / "renders/views.json")
    assert digest(asset) == gate["sha256"] == checks["sha256"] == views["module_sha256"][item]
    sheet = folder / "renders/six-view.png"
    assert digest(sheet) == views["sheet_sha256"]
    for image in views["images"].values():
        assert digest(HERE / image["file"]) == image["sha256"]
    motion_hash = views.get("motion_sheet_sha256")
    if motion_hash:
        assert digest(sheet.with_name("motion-six-view.png")) == motion_hash
    review = dict(item=item, round=number, sha256=gate["sha256"], rest_sheet_sha256=views["sheet_sha256"],
                  motion_sheet_sha256=motion_hash, visual_pass=verdict == "PASS",
                  reviewer="Codex self-review", observation=observation)
    write(folder / "review.json", review)


def promote(item, number):
    folder = HERE / "attempts" / item / str(number)
    candidate = folder / f"{item}.glb"
    gate = read(candidate.with_suffix(".gate.json"))
    validator = read(candidate.with_suffix(".validator.json"))
    review = read(folder / "review.json")
    views = read(folder / "renders/views.json")
    assert digest(candidate) == gate["sha256"] == validator["sha256"] == review["sha256"]
    assert gate["sha256"] == views["module_sha256"][item]
    target = HERE / "renders" / item
    target.mkdir(parents=True, exist_ok=True)
    for image in views["images"].values():
        image_path = HERE / image["file"]
        assert digest(image_path) == image["sha256"]
        destination = target / image_path.name
        shutil.copyfile(image_path, destination)
        image["file"] = str(destination.relative_to(HERE))
    for key, name in (("sheet_sha256", "six-view.png"), ("motion_sheet_sha256", "motion-six-view.png")):
        if key in views:
            sheet = folder / "renders" / name
            assert digest(sheet) == views[key]
            shutil.copyfile(sheet, target / name)
    write(target / "views.json", views)
    shutil.copyfile(candidate, HERE / candidate.name)
    shutil.copyfile(candidate.with_suffix(".validator.json"), HERE / f"{item}.validator.json")
    gate["review"] = review
    gate["delivery_pass"] = gate["pass"] and review["visual_pass"]
    write(HERE / f"{item}.gate.json", gate)
    notes()


def notes():
    header = [
        "# Female wardrobe 4", "",
        "The gate covers rest and 1,827 animation samples from the supplied motion bank at 30 fps,",
        "including integer and half frames and exact authored endpoints. It uses signed nearest-triangle",
        "distance, with negative distances denoting inside vertices. The pair counts report garment–body",
        "triangle overlap. Layer counts are reported separately in each gate JSON.", "",
        "The retained GLBs, Khronos reports and render manifests identify the same bytes. A PASS requires",
        "both the gate and the six-view self-review to pass. Rounds counts the reviewed attempts, and a",
        "FAIL denotes a candidate retained for inspection.", "",
        "| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed mm | Rounds | Result | Six-view self-review |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    rows, evidence = [], []
    for item in ORDER:
        path = HERE / f"{item}.gate.json"
        if not path.is_file():
            continue
        report = read(path)
        review = report["review"]
        clips = list(report["clips"].values())
        inside = max(clip["peak_inside"] for clip in clips)
        pairs = max(clip["peak_pairs"] for clip in clips)
        signed = min(clip["min_signed_mm"] for clip in clips)
        rounds = sum(1 for _ in (HERE / "attempts" / item).glob("*/review.json"))
        asset = report["asset"]
        status = "PASS" if report["delivery_pass"] else "FAIL"
        rows.append(f"| {item} | {asset['triangles']:,} | {asset['bytes'] / 2**20:.3f} | {inside} | {pairs} | "
                    f"{signed:.4f} | {rounds} | {status} | {review['observation']} |")
        layer_peaks = ", ".join(f"{name} {max(c['peak_layer_pairs'][name] for c in clips)}"
                                for name in report["layers"])
        errors, warnings = (report["validator"][key] for key in ("numErrors", "numWarnings"))
        worst = min((frame["min_signed_mm"], name, frame["frame"]) for name, clip in report["clips"].items()
                    for frame in clip["frames"])
        issues = ", ".join(report["issues"])
        detail = f" Gate findings are {issues}." if issues else " The numerical gate passed."
        features = report.get("features", {})
        if "cowl_rest_rear_thickness_mm" in features:
            detail += (f" Rear hood thickness is {features['cowl_rest_rear_thickness_mm']:.1f} mm. "
                       f"The conservative head clearance bound is {features['cowl_head_separation_lower_bound_mm']:.3f} mm.")
        if "leg_tube_min_signed_mm" in features:
            detail += f" The leg tube minimum signed distance is {features['leg_tube_min_signed_mm']:.4f} mm."
        if "export_stabilization" in report:
            detail += " This round's exported positions were checked and locally stabilized before review."
        if "pattern_reference" in report:
            detail += " The pattern uses the shipped female jeans for topology and weights, with a new body-fitted cut and cuff flare."
        motion = f" · [motion sheet](renders/{item}/motion-six-view.png)" if review["motion_sheet_sha256"] else ""
        evidence.append(f"- **{item}.** Retained round {review['round']}. The limiting frame was {worst[2]:g} in "
                        f"`{worst[1]}`. Peak layer pairs were {layer_peaks}. Khronos reported {errors} errors "
                        f"and {warnings} warnings.{detail} [GLB]({item}.glb) · [frame gate]({item}.gate.json) · "
                        f"[Khronos]({item}.validator.json) · [six views](renders/{item}/six-view.png){motion} · "
                        f"[render manifest](renders/{item}/views.json)")
    tail = ["", "## Reproduce", "",
            "Run `./run.sh build_wardrobe.py -- <item> <round>` from this directory. The launcher uses two threads.",
            "With `--render-only` the command reimports and renders the existing candidate. Each item is built and",
            "visually reviewed in order. Earlier GLBs, reports, review records and renders are in `attempts/`.", ""]
    (HERE / "NOTES.md").write_text("\n".join(header + rows + ["", "## Files and findings", ""] + evidence + tail))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("item", choices=ORDER)
    parser.add_argument("round", type=int, choices=(1, 2, 3))
    parser.add_argument("visual", choices=("PASS", "FAIL"))
    parser.add_argument("observation")
    parser.add_argument("--retain", action="store_true")
    args = parser.parse_args()
    record(args.item, args.round, args.visual, args.observation)
    if args.retain:
        promote(args.item, args.round)


if __name__ == "__main__":
    main()
