"""Verify reports and images, and publish a visually accepted wardrobe GLB."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
from shutil import copyfile

from PIL import Image, ImageDraw
from glb_io import Glb

HERE = Path(__file__).resolve().parent
VIEWS = ("front", "front-left", "left", "back", "right", "front-right")
COUNTS = {
    "rest": 1, "walk": 142, "run": 76, "wave": 161, "jump": 126, "idle": 221,
    "nod": 141, "dance": 161, "sit_down": 73, "sit_idle": 181, "stand_up": 61,
    "hold_item": 121, "hold_box": 121, "hold_bag": 121, "take_item": 121,
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_copy(source, target):
    temp = target.with_name("." + target.name + ".pending")
    copyfile(source, temp)
    temp.replace(target)


def inspect(label, row):
    p = HERE / row["candidate"]
    report = json.loads((HERE / row["gate"]).read_text())
    validator = json.loads((HERE / row["validator"]).read_text())
    view_path = HERE / row["views"]
    views = json.loads(view_path.read_text())
    assert digest(p) == report["sha256"] == validator["sha256"] == views["module_sha256"][label]
    assert digest(HERE.parent / "body_female.glb") == report["body_sha256"] == views["body_sha256"]
    assert digest(HERE.parent / "motion_female.glb") == report["motion_sha256"]
    assert digest(HERE.parent / "master_female.blend") == report["master_sha256"]
    for layer, evidence in report["layers"].items():
        assert digest(HERE.parent / evidence["file"]) == evidence["sha256"], layer

    assert set(report["clips"]) == set(COUNTS)
    for name, values in report["clips"].items():
        samples = values["frames"]
        assert len(samples) == values["samples"] == COUNTS[name]
        actual = [s["frame"] for s in samples]
        expected = {actual[0], actual[-1]} | {i / 2 for i in range(round(actual[-1] * 2) + 1)
                                            if actual[0] <= i / 2 <= actual[-1]}
        assert actual == sorted(expected), name
        assert values["peak_inside"] == max(s["inside"] for s in samples)
        assert values["peak_pairs"] == max(s["pairs"] for s in samples)
        assert values["min_signed_mm"] == min(s["min_signed_mm"] for s in samples)
        for layer, pairs in values["peak_layer_pairs"].items():
            assert pairs == max(s["layer_pairs"][layer] for s in samples)

    glb = Glb(p)
    triangles = sum(glb.doc["accessors"][pr["indices"]]["count"] // 3
                    for m in glb.doc["meshes"] for pr in m["primitives"])
    sizes = []
    for img in glb.doc.get("images", []):
        with Image.open(BytesIO(glb.payload(img["bufferView"]))) as decoded:
            sizes.append(list(decoded.size))
            decoded.verify()
    assert triangles == report["asset"]["triangles"] == row["triangles"]
    assert sizes == report["asset"]["texture_dimensions"]
    assert p.stat().st_size == report["asset"]["bytes"] == row["bytes"]
    assert set(views["images"]) == set(VIEWS)
    images = {}
    for name in VIEWS:
        view = views["images"][name]
        image_file = HERE / view["file"]
        assert digest(image_file) == view["sha256"]
        with Image.open(image_file) as image:
            assert image.size == (400, 400)
            image.verify()
        images[name] = image_file

    if label == "bottom-skirt":
        motion = json.loads(view_path.with_name("motion-views.json").read_text())
        assert motion["motion_sha256"] == report["motion_sha256"]
        assert len(motion["views"]) == 3
        for group in motion["views"]:
            assert len(group) == 3
            for view in group:
                image = view_path.with_name(view["image"])
                assert digest(image) == view["sha256"]
    return p, report, validator, images


def sheet(label, images):
    size = 320
    canvas = Image.new("RGB", (3 * size, 2 * (size + 24)), "#161922")
    draw = ImageDraw.Draw(canvas)
    for i, (name, path) in enumerate(images.items()):
        x, y = i % 3 * size, i // 3 * (size + 24)
        with Image.open(path) as image:
            canvas.paste(image.resize((size, size), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 10, y + size + 5), name, fill="white")
    canvas.save(HERE / ".runtime" / (label + "-review.png"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("items", nargs="*")
    parser.add_argument("--sheet", action="store_true")
    parser.add_argument("--approve")
    parser.add_argument("--reject")
    args = parser.parse_args()
    if args.approve and args.reject:
        parser.error("Specify a single visual decision")
    if (args.approve or args.reject) and len(args.items) != 1:
        parser.error("A visual decision must name one item")
    state = json.loads((HERE / "results.json").read_text())
    for label in args.items or state:
        row = state[label]
        candidate, report, validator, images = inspect(label, row)
        if args.sheet:
            sheet(label, images)
        if args.approve:
            assert report["technical_pass"] and validator["issues"]["numErrors"] == 0 and validator["issues"]["numWarnings"] == 0
            atomic_copy(candidate, HERE / (label + ".glb"))
        if args.approve or args.reject:
            reviews = HERE / "reviews.json"
            decisions = json.loads(reviews.read_text()) if reviews.exists() else {}
            decisions[label] = {
                "sha256": report["sha256"],
                "visual": args.approve or args.reject,
                "status": "PASS" if args.approve else "FAIL",
            }
            reviews.write_text(json.dumps(decisions, indent=2) + "\n")
        print(label, row["status"], report["issues"], digest(candidate))


if __name__ == "__main__":
    main()
