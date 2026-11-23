"""Independently compare the shipped GLB's skinned body to the Blender pose cache."""
import hashlib
import json
from pathlib import Path

import numpy as np

from glb_io import Glb

HERE = Path(__file__).resolve().parent
BODY = HERE.parent / "body_female.glb"
MOTION = HERE.parent / "motion_female.glb"
AXES = np.array((1, -1, 1))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slerp(a, b, mix):
    dot = np.einsum("vi,vi->v", a, b)
    b = np.where(dot[:, None] < 0, -b, b)
    theta = np.arccos(np.clip(abs(dot), 0, 1))
    fast = theta < 1.e-4
    denom = np.where(fast, 1, np.sin(theta))
    u = np.where(fast, 1 - mix, np.sin((1 - mix) * theta) / denom)
    v = np.where(fast, mix, np.sin(mix * theta) / denom)
    value = a * u[:, None] + b * v[:, None]
    return value / np.linalg.norm(value, axis=1)[:, None]


def transform(translation, rotation, scale):
    x, y, z, w = rotation.T
    out = np.zeros((len(translation), 4, 4))
    out[:, 0, :3] = np.column_stack((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)))
    out[:, 1, :3] = np.column_stack((2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)))
    out[:, 2, :3] = np.column_stack((2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)))
    out[:, :, :3] *= scale[:, None, :]
    out[:, :3, 3] = translation
    out[:, 3, 3] = 1
    return out


def sample(library, animation, frames):
    keys = ("translation", "rotation", "scale")
    defaults = ((0., 0., 0.), (0., 0., 0., 1.), (1., 1., 1.))
    nodes = library.doc["nodes"]
    values = {key: np.array([[n.get(key, default) for n in nodes]] * len(frames))
              for key, default in zip(keys, defaults, strict=True)}
    if animation is not None:
        times = frames / 30
        for channel in animation["channels"]:
            kind, node = channel["target"]["path"], channel["target"]["node"]
            sampler = animation["samplers"][channel["sampler"]]
            assert sampler.get("interpolation", "LINEAR") == "LINEAR"
            t = library.accessor(sampler["input"])[:, 0].astype(np.float64)
            data = library.accessor(sampler["output"]).astype(np.float64)
            hi = np.searchsorted(t, times, side="right")
            lo = np.clip(hi - 1, 0, len(t) - 1)
            hi = np.clip(hi, 0, len(t) - 1)
            mix = np.clip((times - t[lo]) / np.maximum(1.e-12, t[hi] - t[lo]), 0, 1)
            values[kind][:, node] = (slerp(data[lo], data[hi], mix) if kind == "rotation" else
                data[lo] * (1 - mix[:, None]) + data[hi] * mix[:, None])
    batch = len(frames)
    matrices = transform(*(values[key].reshape(batch * len(nodes), -1) for key in keys))
    matrices = matrices.reshape(batch, len(nodes), 4, 4)

    def visit(parent):
        for child in nodes[parent].get("children", []):
            matrices[:, child] = matrices[:, parent] @ matrices[:, child]
            visit(child)

    for root in library.doc["scenes"][library.doc.get("scene", 0)]["nodes"]:
        visit(root)
    return matrices


def main():
    body, motion = Glb(BODY), Glb(MOTION)
    skin, = body.doc["skins"]
    inverse = body.accessor(skin["inverseBindMatrices"]).reshape(-1, 4, 4).transpose(0, 2, 1)
    primitive, = body.doc["meshes"][0]["primitives"]
    a = primitive["attributes"]
    pos = body.accessor(a["POSITION"])
    joints = body.accessor(a["JOINTS_0"])
    weights = body.accessor(a["WEIGHTS_0"])
    point = np.column_stack((pos, np.ones(len(pos))))
    expected = pos[:, [0, 2, 1]] * AXES
    cache, = (HERE / ".runtime").glob("poses-*.npz")
    with np.load(cache) as raw:
        labels, frames, observed = raw["labels"], raw["frames"], raw["points"]
    master_pos = observed[0]
    lookup = []
    for part in np.array_split(expected, 100):
        lookup.extend(np.linalg.norm(part[:, None] - master_pos[None, :], axis=-1).argmin(axis=1))
    lookup = np.asarray(lookup)
    reverse = np.concatenate([np.linalg.norm(part[:, None] - expected[None, :], axis=-1).min(axis=1)
                              for part in np.array_split(master_pos, 100)])
    rest_mm = np.linalg.norm(expected - master_pos[lookup], axis=1).max() * 1000
    by_name = {node["name"]: i for i, node in enumerate(motion.doc["nodes"])}
    to_motion = [by_name[body.doc["nodes"][i]["name"]] for i in skin["joints"]]
    local = np.einsum("vkij,vj->vki", inverse[joints], point) * weights[:, :, None]
    animations = {a["name"]: a for a in motion.doc["animations"]}
    assert set(labels) == set(animations) | {"rest"}
    results = {}
    for name in dict.fromkeys(labels.tolist()):
        ids = np.flatnonzero(labels == name)
        greatest = 0.
        worst_frame = 0.
        for group in np.array_split(ids, max(1, len(ids) // 15)):
            worlds = sample(motion, animations.get(name), frames[group])[:, to_motion]
            mesh = np.einsum("fvkij,vkj->fvi", worlds[:, joints, :3, :], local)
            mesh = mesh[..., [0, 2, 1]] * AXES
            delta = np.linalg.norm(mesh - observed[group][:, lookup], axis=-1).max(axis=1) * 1000
            if delta.max() > greatest:
                greatest, worst_frame = float(delta.max()), float(frames[group[delta.argmax()]])
        results[name] = dict(samples=len(ids), max_position_delta_mm=greatest, frame=worst_frame)
        print(name, results[name], flush=True)
    assert rest_mm < .002
    assert max(clip["max_position_delta_mm"] for clip in results.values()) < .002
    report = dict(body_sha256=digest(BODY), motion_sha256=digest(MOTION),
                  maximum_exported_to_master_rest_delta_mm=float(rest_mm),
                  unmatched_master_rest_indices=np.flatnonzero(reverse > .000002).tolist(),
                  clips=results)
    (HERE / "input-audit.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
