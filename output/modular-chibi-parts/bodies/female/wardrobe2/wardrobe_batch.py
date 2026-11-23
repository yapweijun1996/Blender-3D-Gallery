"""Run and record up to three fitting rounds per wardrobe item in task order."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import BODY, HERE, REPO, arguments
import fit_module as fit
from fit_outfit_layer import bake
from gate_module import LIMITS, SHIPPED, gate, layers_for
import render
import render_wardrobe

ITEMS = tuple(LIMITS)
NOTES = HERE / "NOTES.md"
STATE = HERE / "results.json"
REVIEWS = HERE / "reviews.json"


def decisions():
    return json.loads(REVIEWS.read_text()) if REVIEWS.exists() else {}


def write_json(path, data):
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    pending.replace(path)


def validate(path):
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required for the local Khronos validator")
    env = dict(os.environ)
    env.pop("DYLD_INSERT_LIBRARIES", None)
    subprocess.run([node, str(HERE / "validate.cjs"), str(path)], env=env, check=False)
    result = json.loads(path.with_suffix(".validator.json").read_text())
    assert result["sha256"] == fit.sha(path)
    return {"errors": result["issues"]["numErrors"], "warnings": result["issues"]["numWarnings"],
            "validator_version": result["validatorVersion"]}


def metrics(report):
    clips = tuple(report["clips"].values())
    return dict(triangles=report["asset"]["triangles"], bytes=report["asset"]["bytes"],
                peak_inside=max(r["peak_inside"] for r in clips),
                peak_pairs=max(r["peak_pairs"] for r in clips),
                min_signed_mm=min(r["min_signed_mm"] for r in clips),
                peak_layer_pairs=max((p for r in clips for p in r["peak_layer_pairs"].values()), default=0))


def ranking(row):
    return (
        len(row["issues"]),
        5 * row["peak_inside"] + row["peak_pairs"] + row["peak_layer_pairs"],
        -row["min_signed_mm"],
    )


def report_text(state):
    body = [
        "# Female modular wardrobe 2",
        "",
        "The bake uses the female master and the supplied 14-clip motion GLB. Gates use "
        "rest plus 1,827 animation samples at 30 fps, including integer frames, half frames "
        "and authored endpoints. Signed distance follows the existing tool's oriented nearest-triangle metric.",
        "",
        "Layering uses the shipped assets, identified by their hashes. Bottoms replace jeans and "
        "are checked with the T-shirt and sneakers. Shoes replace sneakers and are checked with "
        "the T-shirt and jeans. Hair is checked with all three shipped items.",
        "",
        "The shipped sneaker sole defines the common shod floor, 5.959 mm below the bare-body "
        "origin. Both shoes must touch that plane within 0.5 mm. Renders show the same plane.",
        "",
        "| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed mm | Rounds used | Result |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in ITEMS:
        row = state.get(item)
        if row and "triangles" in row:
            body.append(f"| {item} | {row['triangles']:,} | {row['bytes'] / 2**20:.3f} | "
                f"{row['peak_inside']} | {row['peak_pairs']} | {row['min_signed_mm']:.4f} | "
                f"{row['rounds']} | {row['status']} |")
        else:
            body.append(f"| {item} | — | — | — | — | — | {row['rounds'] if row else 0} | "
                f"{row['status'] if row else 'Pending'} |")
    body.extend(["", "## Evidence", ""])
    for label, row in state.items():
        links = [f"[gate]({row['gate']})", f"[Khronos]({row['validator']})"] if "gate" in row else []
        if row.get("views"):
            links.append(f"[six views]({row['views']})")
        if "candidate" in row:
            links.insert(0, f"[{'GLB' if row['status'] == 'PASS' else 'candidate'}]({row['candidate']})")
        if label == "bottom-skirt" and row.get("views"):
            links.append(f"[walk, run and sit-down]({Path(row['views']).parent / 'motion.png'})")
        material = "; ".join(row["issues"]) if row["issues"] else row.get("visual", "Numbers passed. Visual review pending.")
        detail = f" Peak layer pairs {row['peak_layer_pairs']}." if "peak_layer_pairs" in row else ""
        body.append(f"- **{label}** · {material}.{detail} " + " · ".join(links))
    body.extend(["", "See [original tool notes](NOTES.original.md) and [round results](results.json).",
                 "", "Run `node batch_fit.mjs` from this directory to resume the sequential batch.", ""])
    NOTES.write_text("\n".join(body))


def record(state):
    write_json(STATE, state)
    report_text(state)


def process(label, data, state):
    source = REPO / "models/chibi-dressup/modules" / (label + ".glb")
    assets = {name: fit.Module(SHIPPED[name], data[0]) for name in layers_for(label)}
    outcomes = []
    previous_gate = previous_path = None
    visual = decisions().get(label, {})
    for number in range(1, 4):
        directory = HERE / "attempts" / label / str(number)
        directory.mkdir(parents=True, exist_ok=True)
        candidate = directory / (label + ".glb")
        evidence = candidate.with_suffix(".gate.json")
        print("ROUND", label, number, flush=True)
        if not candidate.exists() or not candidate.with_suffix(".fit.json").exists():
            if label == "shoes-boots" and number == 1:
                fit.fit(source, candidate, 5, data, LIMITS[label])
            else:
                fit_report = bake(label, source, candidate, data, assets, number, previous_gate, previous_path)
                write_json(candidate.with_suffix(".fit.json"), fit_report)
        if evidence.exists() and (old := json.loads(evidence.read_text())).get("sha256") == fit.sha(candidate) and "khronos" in old:
            measured = old
        else:
            measured = gate(candidate, evidence, data, assets)
            validation = validate(candidate)
            measured["khronos"] = validation
            if validation["errors"] or validation["warnings"]:
                measured["issues"].append("Khronos validator")
            measured["technical_pass"] = not measured["issues"]
            write_json(evidence, measured)
        visually_rejected = visual.get("status") == "FAIL" and visual.get("sha256") == measured["sha256"]
        accepted_technical = measured["technical_pass"] and not visually_rejected
        problems = list(measured["issues"])
        if visually_rejected:
            problems.append("Visual review")
        row = dict(metrics(measured), rounds=number, issues=problems,
                   gate=str(evidence.relative_to(HERE)),
                   candidate=str(candidate.relative_to(HERE)),
                   validator=str(candidate.with_suffix(".validator.json").relative_to(HERE)))
        outcomes.append(row)
        state[label] = dict(row, status="Awaiting visual review" if accepted_technical else "In progress",
                            rounds_evidence=outcomes)
        record(state)
        if accepted_technical:
            break
        previous_gate, previous_path = measured, candidate

    winner = min(outcomes, key=ranking)
    status = "FAIL" if winner["issues"] else "Awaiting visual review"
    candidate = HERE / winner["candidate"]
    render.OUT = HERE / "renders"
    render_wardrobe.render_item(candidate)
    state[label] = dict(winner, status=status, rounds=number, selected_round=winner["rounds"],
                       rounds_evidence=outcomes, views=f"renders/{label}/views.json")
    record(state)
    print("ITEM", label, status, winner, flush=True)


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    selected = arguments() or ITEMS
    assert all(label in ITEMS for label in selected)
    queue = []
    reviews = decisions()
    for label in selected:
        current = state.get(label, {})
        previous_review = reviews.get(label, {})
        review_requires_round = previous_review.get("status") == "FAIL" and current.get("rounds", 3) < 3
        if (current.get("status") in {"PASS", "FAIL", "Awaiting visual review"} and
                current.get("views") and not review_requires_round):
            continue
        queue.append(label)
    if not queue:
        print("No fitting rounds remain for the selected items.", flush=True)
        return
    record(state)
    data = fit.cache_scene()
    for label in queue:
        try:
            process(label, data, state)
        except Exception as error:
            traceback.print_exc()
            item = state.setdefault(label, {"rounds": 0, "issues": []})
            item["status"] = "Execution error"
            item["issues"].append(str(error))
            record(state)


if __name__ == "__main__":
    main()
