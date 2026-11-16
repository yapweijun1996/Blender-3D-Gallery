#!/usr/bin/env python3
"""Package the three earlier Unity experiments as reproducible gallery assets."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
from datetime import date
from pathlib import Path

from PIL import Image


HERE = Path(__file__).resolve().parent
LICENSE = "Original asset; reuse in the owner's projects is authorized. Public redistribution terms have not been specified."
UNITY_VERSION = "6000.0.85f2"
GLTFAST_VERSION = "6.21.0"
VARIANTS = ("terra", "sol", "astra")
PROJECT_COMPONENT_TYPES = {
    5120: ("b", 1),
    5121: ("B", 1),
    5122: ("h", 2),
    5123: ("H", 2),
    5125: ("I", 4),
    5126: ("f", 4),
}
TYPE_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}


def pad4(value: bytes, fill: bytes) -> bytes:
    return value + fill * ((-len(value)) % 4)


def read_glb(path: Path) -> tuple[dict, list[tuple[int, bytes]]]:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF" or struct.unpack_from("<I", data, 4)[0] != 2:
        raise ValueError(f"Not a glTF 2.0 GLB: {path}")
    if struct.unpack_from("<I", data, 8)[0] != len(data):
        raise ValueError(f"Incorrect GLB length header: {path}")

    chunks = []
    offset = 12
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunks.append((kind, data[offset : offset + length]))
        offset += length
    if offset != len(data) or not chunks or chunks[0][0] != 0x4E4F534A:
        raise ValueError(f"Invalid GLB chunk layout: {path}")
    document = json.loads(chunks[0][1].rstrip(b" \x00").decode("utf-8"))
    if not any(kind == 0x004E4942 for kind, _ in chunks):
        raise ValueError(f"GLB has no embedded BIN chunk: {path}")
    return document, chunks


def normalize_accessor_bounds(document: dict, chunks: list[tuple[int, bytes]]) -> int:
    """Correct min/max rounding in copied GLBs without changing vertex data."""
    binary = next(payload for kind, payload in chunks if kind == 0x004E4942)
    changed = 0
    for accessor in document.get("accessors", []):
        if "min" not in accessor and "max" not in accessor:
            continue
        if accessor.get("sparse"):
            raise ValueError("Sparse accessors are not supported by this packaging step")
        view_index = accessor.get("bufferView")
        if view_index is None:
            continue
        component_type = accessor["componentType"]
        if component_type not in PROJECT_COMPONENT_TYPES:
            raise ValueError(f"Unsupported accessor component type: {component_type}")
        format_code, component_size = PROJECT_COMPONENT_TYPES[component_type]
        component_count = TYPE_COMPONENTS[accessor["type"]]
        view = document["bufferViews"][view_index]
        stride = view.get("byteStride", component_count * component_size)
        first = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        minima = [math.inf] * component_count
        maxima = [-math.inf] * component_count
        for item in range(accessor["count"]):
            for component in range(component_count):
                offset = first + item * stride + component * component_size
                value = struct.unpack_from("<" + format_code, binary, offset)[0]
                minima[component] = min(minima[component], value)
                maxima[component] = max(maxima[component], value)
        exact_min = [int(value) if format_code != "f" else value for value in minima]
        exact_max = [int(value) if format_code != "f" else value for value in maxima]
        if accessor.get("min") != exact_min or accessor.get("max") != exact_max:
            accessor["min"] = exact_min
            accessor["max"] = exact_max
            changed += 1
    return changed


def write_glb(path: Path, document: dict, chunks: list[tuple[int, bytes]]) -> None:
    encoded = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    chunks[0] = (chunks[0][0], pad4(encoded, b" "))
    output = bytearray(b"glTF" + struct.pack("<II", 2, 0))
    for kind, payload in chunks:
        output.extend(struct.pack("<II", len(payload), kind))
        output.extend(payload)
    struct.pack_into("<I", output, 8, len(output))
    path.write_bytes(output)


def measured_metrics(document: dict, path: Path) -> dict:
    triangles = 0
    for node in document.get("nodes", []):
        if "mesh" not in node:
            continue
        for primitive in document["meshes"][node["mesh"]]["primitives"]:
            if primitive.get("mode", 4) != 4:
                raise ValueError(f"Non-triangle primitive in {path}")
            accessor = document["accessors"][primitive.get("indices", primitive["attributes"]["POSITION"])]
            if accessor["count"] % 3:
                raise ValueError(f"Incomplete triangle in {path}")
            triangles += accessor["count"] // 3
    if not triangles:
        raise ValueError(f"No triangle geometry found in {path}")
    position_accessors = {
        primitive["attributes"]["POSITION"]
        for mesh in document.get("meshes", [])
        for primitive in mesh["primitives"]
    }
    return {
        "glb_bytes": path.stat().st_size,
        "triangles": triangles,
        "vertices": sum(document["accessors"][index]["count"] for index in position_accessors),
        "animations": len(document.get("animations", [])),
    }


def save_webp(source: Path, target: Path, thumbnail: bool) -> None:
    image = Image.open(source).convert("RGB")
    if thumbnail:
        for longest in (1024, 896, 768, 640, 512):
            resized = image.copy()
            if max(resized.size) > longest:
                resized.thumbnail((longest, longest), Image.Resampling.LANCZOS)
            for quality in (88, 84, 80, 76, 72, 68, 64):
                resized.save(target, "WEBP", quality=quality, method=6)
                if target.stat().st_size < 150 * 1024:
                    return
        raise ValueError(f"Could not fit thumbnail below 150 KiB: {source}")
    image.save(target, "WEBP", quality=86, method=6)


def verify_project(project: Path) -> None:
    version_file = project / "ProjectSettings" / "ProjectVersion.txt"
    version = next(
        (line.partition(":")[2].strip() for line in version_file.read_text().splitlines() if line.startswith("m_EditorVersion:")),
        None,
    )
    manifest = json.loads((project / "Packages" / "manifest.json").read_text())
    gltfast = manifest.get("dependencies", {}).get("com.unity.cloud.gltfast")
    if version != UNITY_VERSION or gltfast != GLTFAST_VERSION:
        raise ValueError(f"Unexpected Unity/glTFast version in {project}: {version} / {gltfast}")


def metadata_for(variant: str, metrics: dict) -> dict:
    asset_id = f"gjh-chibi-visitor-{variant}"
    name = f"GJH Chibi Visitor (Unity experiment, {variant})"
    description = (
        f"Earlier experimental comparison built in Unity by the {variant} AI model; it is an independent interpretation "
        "of the GJH Chibi Visitor concept with a rounded white helmet, purple happy face screen, ring headphones, hoodie and short limbs."
    )
    return {
        "id": asset_id,
        "name": name,
        "summary": f"Earlier {variant} AI-model Unity experiment and comparison for the GJH Chibi Visitor.",
        "description": description,
        "category": "Characters",
        "tags": ["GJH", "mascot", "character", "chibi", "robot", "comparison", "Unity experiment", variant],
        "status": "validated",
        "created": date(2026, 11, 16).isoformat(),
        "author": f"Yap Wei Jun project / {variant} AI model",
        "unity_version": UNITY_VERSION,
        "gltfast_version": GLTFAST_VERSION,
        "creation_method": f"Deterministic Unity geometry generated by the {variant} AI model using ChibiBuilder.cs and exported with glTFast.",
        "generator": "source/ChibiBuilder.cs",
        "paths": {
            "glb": f"exports/{asset_id}.glb",
            "source": "source/ChibiBuilder.cs",
            "preview": "previews/front.webp",
            "side_preview": "previews/side.webp",
            "back_preview": "previews/back.webp",
            "three_quarter_preview": "previews/3q.webp",
        },
        "display": {
            "previewRotationY": 0,
            "previewCameraDirection": [0, 0.15, 1],
            "units": "metres",
            "up_axis": "Unity +Y / glTF +Y",
            "origin": "feet at floor Y=0",
            "front_axis": "+Z",
        },
        "accuracy_notes": (
            "The owner's original character-sheet image was not available; this model follows the written description only. "
            "The happy-face default is exported, while the sheet's alternate expressions, outfits and accessories are not represented as selectable gallery variants. "
            "The visor projects in profile, and the fins and clothing details are simplified geometry; exact sheet fidelity is unverified."
        ),
        "attribution": [
            {"credit": f"Earlier experimental Unity geometry and previews created in the owner's project by the {variant} AI model; no third-party model is included."}
        ],
        "rights": LICENSE,
        "metrics": metrics,
    }


def write_catalog_collection(catalog_path: Path, collection: dict) -> None:
    """Replace only this collection's JSON block, preserving unrelated bytes."""
    text = catalog_path.read_text()
    marker = f'\n    {{\n      "id": "{collection["id"]}",'
    marker_index = text.find(marker)
    lines = json.dumps(collection, indent=2, ensure_ascii=False).splitlines()
    encoded = "\n".join(
        line if index == 0 else "    " + line
        for index, line in enumerate(lines)
    )
    if marker_index >= 0:
        start = text.index("{", marker_index)
        depth = 0
        in_string = False
        escaped = False
        end = None
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        if end is None:
            raise ValueError(f"Could not find the end of collection {collection['id']}")
        text = text[:start] + encoded + text[end:]
    else:
        close = text.rfind("\n  ]")
        if close < 0:
            raise ValueError("Could not find the end of catalog collections")
        appended = "\n".join("    " + line for line in lines)
        text = text[:close] + ",\n" + appended + text[close:]
    catalog_path.write_text(text)


def package_variant(variant: str, project: Path) -> tuple[dict, dict]:
    project = project.expanduser().resolve()
    verify_project(project)
    output = HERE / variant
    (output / "exports").mkdir(parents=True, exist_ok=True)
    (output / "previews").mkdir(parents=True, exist_ok=True)
    (output / "source").mkdir(parents=True, exist_ok=True)

    asset_id = f"gjh-chibi-visitor-{variant}"
    glb_path = output / "exports" / f"{asset_id}.glb"
    shutil.copy2(project / "Exports" / "gjh-chibi-visitor.glb", glb_path)
    document, chunks = read_glb(glb_path)
    roots = document["scenes"][document.get("scene", 0)]["nodes"]
    root_names = [document["nodes"][index].get("name") for index in roots]
    if root_names != ["GJHChibiVisitor"]:
        raise ValueError(f"Unexpected scene root in {variant}: {root_names}")
    corrected = normalize_accessor_bounds(document, chunks)
    write_glb(glb_path, document, chunks)
    document, _ = read_glb(glb_path)
    metrics = measured_metrics(document, glb_path)

    for view in ("front", "side", "back", "3q"):
        source = project / "Previews" / f"{view}.png"
        target = output / "previews" / f"{view}.webp"
        save_webp(source, target, thumbnail=(view == "front"))
    shutil.copy2(project / "Assets" / "Editor" / "ChibiBuilder.cs", output / "source" / "ChibiBuilder.cs")
    metadata = metadata_for(variant, metrics)
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
    catalog_asset = {
        "id": asset_id,
        "name": metadata["name"],
        "category": "Characters",
        "tags": metadata["tags"],
        "description": metadata["description"],
        "file": f"models/gjh-chibi-visitor/{variant}/exports/{asset_id}.glb",
        "thumbnail": f"models/gjh-chibi-visitor/{variant}/previews/front.webp",
        "metadata": f"models/gjh-chibi-visitor/{variant}/metadata.json",
        "root": "GJHChibiVisitor",
        "downloadable": False,
        "license": LICENSE,
    }
    print(
        f"{variant}: repaired {corrected} accessor bounds; {metrics['glb_bytes']} bytes, "
        f"{metrics['triangles']} triangles, {metrics['vertices']} vertices, {metrics['animations']} clips"
    )
    return catalog_asset, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for variant in VARIANTS:
        parser.add_argument(f"--{variant}-project", required=True, type=Path)
    args = parser.parse_args()
    assets = []
    for variant in VARIANTS:
        asset, _ = package_variant(variant, getattr(args, f"{variant}_project"))
        assets.append(asset)

    catalog_path = HERE.parent / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    collection = next((item for item in catalog["collections"] if item["id"] == "gjh-chibi-visitor"), None)
    if collection is None:
        collection = {"id": "gjh-chibi-visitor", "name": "GJH Chibi Visitor"}
        catalog["collections"].append(collection)
    collection["description"] = (
        "Primary Blender-built GJH Chibi Visitor, with three earlier independent experimental comparisons built in Unity by the terra, sol, and astra AI models."
    )
    primary = next(
        (asset for asset in collection.get("assets", []) if asset.get("id") == "gjh-chibi-visitor-blender"),
        None,
    )
    collection["assets"] = ([primary] if primary else []) + assets
    write_catalog_collection(catalog_path, collection)
    print(f"Registered {len(collection['assets'])} collection assets ({len(assets)} Unity experiments) in {catalog_path}")


if __name__ == "__main__":
    main()
