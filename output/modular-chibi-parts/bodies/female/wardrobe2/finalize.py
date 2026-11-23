"""Assemble the per-item evidence and final delivery table."""
import json
from pathlib import Path

from review_delivery import HERE, VIEWS, atomic_copy, digest, inspect

STATE = HERE / "results.json"
NOTES = HERE / "NOTES.md"


def witness_text(report):
    explanations = []
    clips = report["clips"]
    if "Posed body clearance" in report["issues"]:
        clip, row = min(clips.items(), key=lambda item: item[1]["min_signed_mm"])
        frame = min(row["frames"], key=lambda f: f["min_signed_mm"])["frame"]
        explanations.append(f"Minimum body clearance {row['min_signed_mm']:.4f} mm in `{clip}` at frame {frame:g}.")
        clip, row = max(clips.items(), key=lambda item: item[1]["peak_pairs"])
        if row["peak_pairs"]:
            frame = max(row["frames"], key=lambda f: f["pairs"])["frame"]
            explanations.append(f"Peak body overlap {row['peak_pairs']} pairs in `{clip}` at frame {frame:g}.")
    layers = [(pairs, layer, clip) for clip, row in clips.items()
              for layer, pairs in row["peak_layer_pairs"].items()]
    if layers and (peak := max(layers))[0] > 0:
        pairs, layer, clip = peak
        explanations.append(f"Peak layering overlap {pairs} pairs with {layer} in `{clip}`.")
    if "Rest sole floor contact" in report["issues"]:
        floor = report["floor_reference_mm"]
        left, right = [report["floor_mm"][side] for side in ("left", "right")]
        explanations.append(f"Sole heights {left:.3f} and {right:.3f} mm versus the {floor:.3f} mm plane.")
    if "Khronos validator" in report["issues"]:
        v = report["khronos"]
        explanations.append(f"Khronos found {v['errors']} errors and {v['warnings']} warnings.")
    if "Asset budget" in report["issues"] or "Texture decode" in report["issues"]:
        explanations.append("The asset format or size budget failed.")
    return " ".join(explanations)


def finish():
    state = json.loads(STATE.read_text())
    reviews_path = HERE / "reviews.json"
    reviews = json.loads(reviews_path.read_text()) if reviews_path.exists() else {}
    columns = ["| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed mm | Rounds used | Result |",
               "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    detail = []
    for label, row in state.items():
        if "views" not in row:
            columns.append(f"| {label} | — | — | — | — | — | {row['rounds']} | {row['status']} |")
            detail.append(f"- **{label}.** " + ". ".join(row["issues"]))
            continue
        candidate, gate, validation, images = inspect(label, row)
        best_glb = HERE / (label + ".glb")
        visual = reviews.get(label)
        observed_status = row["status"]
        if visual:
            assert visual["sha256"] == gate["sha256"]
            observed_status = visual["status"]
            row["visual"] = visual["visual"]
        assert observed_status in {"PASS", "FAIL"}
        if observed_status == "PASS":
            assert gate["technical_pass"] and digest(best_glb) == gate["sha256"]
        else:
            assert row["rounds"] == 3
            atomic_copy(candidate, best_glb)
        assert digest(best_glb) == gate["sha256"]
        gate_path = HERE / (label + ".gate.json")
        validator_path = HERE / (label + ".validator.json")
        root_gate = dict(gate, delivery_status=observed_status,
                         selected_round=row["selected_round"], rounds_used=row["rounds"],
                         visual_review=row.get("visual"))
        pending_gate = gate_path.with_suffix(".json.pending")
        pending_gate.write_text(json.dumps(root_gate, separators=(",", ":"), allow_nan=False) + "\n")
        pending_gate.replace(gate_path)
        atomic_copy(candidate.with_suffix(".validator.json"), validator_path)
        assert digest(validator_path) == digest(candidate.with_suffix(".validator.json"))
        row.update(status=observed_status, delivery_gate=gate_path.name, delivery_validator=validator_path.name,
                   delivery_glb=best_glb.name)
        columns.append(f"| {label} | {row['triangles']:,} | {row['bytes'] / 2**20:.3f} | "
                       f"{row['peak_inside']} | {row['peak_pairs']} | {row['min_signed_mm']:.4f} | "
                       f"{row['rounds']} | {observed_status} |")
        links = [f"[{'GLB' if observed_status == 'PASS' else 'fitted candidate'}]({best_glb.name})",
                 f"[gate for all frames]({gate_path.name})", f"[Khronos]({validator_path.name})",
                 f"[render manifest]({row['views']})",
                 *(f"[{name}]({images[name].relative_to(HERE)})" for name in VIEWS)]
        if label == "bottom-skirt":
            links.append(f"[walk, run and sit-down]({Path(row['views']).parent / 'motion.png'})")
        note = witness_text(gate)
        review = row.get("visual")
        if review:
            note += (" " if note else "") + review.rstrip(".") + "."
        detail.append(f"- **{label}.** Round {row['selected_round']} retained. {note} " + " · ".join(links))
    notes = [
        "# Female modular wardrobe 2",
        "",
        "The gate covers rest and 1,827 animation samples from the supplied 14-clip motion bank. "
        "It uses 30 fps, checks integer and half frames, and includes exact authored endpoints. "
        "The signed clearance follows the supplied nearest-triangle normal metric.",
        "",
        "The shipped sneaker sole defines the common rest floor at −5.959 mm relative to the barefoot body origin. "
        "Both shoes must reach that plane within 0.5 mm. The renders use the same plane.",
        "",
        "Layer tests use the shipped T-shirt, jeans and sneakers verified by hash. Shoes replace sneakers. "
        "Bottoms replace jeans. The garment peak columns report contacts with the body. Each gate JSON also reports layering by clip.",
        "",
        "Each named GLB is the exact candidate used for its gate and renders. A FAIL GLB is an inspection candidate retained "
        "after the three-round limit. The matching gate declares its delivery status. Peaks and clearance describe the "
        "retained GLB. Rounds used counts all attempts for the item.",
        "",
        "The female folder supplied the original fitter, launcher and notes. The sibling male folder supplied the three "
        "same-named gate, layer and batch entry points, which were adapted here to the female assets and sequential queue.",
        "",
        *columns, "", "## Files and findings", "", *detail, "",
        "[Round results](results.json) · [Input motion audit](input-audit.json) · "
        "[Body surface audit](surface-audit.json) · [Original tool notes](NOTES.original.md)",
        "",
        "Reproduce sequential fitting with `node batch_fit.mjs` in this directory. "
        "The Blender launcher is fixed at two threads.",
        "",
    ]
    pending = NOTES.with_suffix(".md.pending")
    pending.write_text("\n".join(notes))
    pending.replace(NOTES)
    pending = STATE.with_suffix(".json.pending")
    pending.write_text(json.dumps(state, indent=2) + "\n")
    pending.replace(STATE)


if __name__ == "__main__":
    finish()
