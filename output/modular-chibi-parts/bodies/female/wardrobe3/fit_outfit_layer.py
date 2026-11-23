"""Apply slot-specific registration and bake rest-space contact offsets."""
import time

import numpy as np
from mathutils.bvhtree import BVHTree

import fit_module as fit
from gate_module import SHIPPED, pose

smoothstep = fit.GEOMETRY["smoothstep"]
limit_delta = fit.SOURCE["limit_delta"]


def frame_selection(rows, previous, label):
    fast = {"walk", "run", "jump", "dance", "sit_down", "stand_up"}
    stride = 5 if label in ("bottom-skirt", "bottom-shorts") else 6
    indices = {0}
    for clip in {entry[0] for entry in rows}:
        candidates = [i for i, entry in enumerate(rows) if entry[0] == clip]
        indices.update(candidates[::stride if clip in fast else 16])
        indices.add(candidates[-1])
        if previous:
            details = previous["clips"][clip]["frames"]
            def risk(row):
                return row["pairs"] + 4 * row["inside"] + 2 * sum(row["layer_pairs"].values()) + (
                    4 * max(0., .9 - row["min_signed_mm"]))
            ranked = sorted(range(len(details)), key=lambda k: risk(details[k]), reverse=True)
            for k in ranked[:16]:
                if risk(details[k]) > 0:
                    indices.add(candidates[k])
    return sorted(indices)


def sole_reference(names):
    return float(fit.Module(SHIPPED["sneakers"], names).source_points[:, 2].min())


class Registration:
    def __init__(self, label, module, neutral, female, rest, round_number, previous):
        self.label, self.module = label, module
        self.round_number = round_number
        self.ground = sole_reference(module.names)
        seed, weights = fit.seed_shape(module, neutral, female, rest)
        self.initial_seed = seed.copy()
        self.sole = []
        if label.startswith("shoes"):
            family = label.split("-")[1]
            if round_number > 1 or label != "shoes-boots":
                seed = self.shoe_seed(seed, female, family)
            for sign in (1, -1):
                side = np.flatnonzero(sign * module.points[:, 0] > 0)
                lowest = float(seed[side, 2].min())
                self.sole.append((side, lowest))
        elif label.startswith("bottom") and round_number > 1:
            seed = self.bottom_seed(seed, female)
        self.seed = self.floor(seed)
        self.weights = weights
        self.points = self.seed.copy()
        if previous is not None and round_number > 1:
            # Continue from the previous baked shape unless the item needs a
            # different registration to resolve heel, cuff, or waistband contact.
            old = fit.Module(previous, module.names)
            old_points = module.welded(old.source_points).astype(np.float32)
            drift = old_points - self.initial_seed
            mix = .55 if label.startswith("shoes") else (.75 if round_number == 2 else .5)
            self.points = self.floor(self.seed + mix * limit_delta(drift, .024))
            self.weights = old.weights
        if label.startswith("shoes") and round_number > 1:
            self.weights = self.ankle_weights(self.seed, self.weights, female, rest)

    def shoe_seed(self, seed, female, family):
        p = seed.copy()
        for sign, side in ((1, "Left"), (-1, "Right")):
            take = sign * self.module.points[:, 0] > 0
            foot = self.module.names.index("mixamorig:" + side + "Foot")
            center = female[3][foot]
            medial = np.maximum(0, sign * (center[0] - p[:, 0]))
            # Recover the narrower female shoe last where the opposite heel
            # passes very close in walk. Leave the lateral wall in place.
            relief = min(.013, (.0065 if family in ("sandals", "slipons") else .0095) +
                         .0030 * (self.round_number - 1))
            p[take, 0] += sign * relief * smoothstep(.007, .056, medial[take]) * (
                1 - smoothstep(.093, .16, p[take, 2]))
            collar = .110 if family in ("boots", "hightop") else .109
            high = p[take, 2].max()
            if high > collar:
                ramp = smoothstep(.060, high, p[take, 2])
                p[take, 2] -= (high - collar) * ramp
        return p

    def ankle_weights(self, points, weights, female, tree):
        _, hit, _, triangles = fit.nearest(tree, points)
        vertices = female[1][triangles]
        mapping = np.einsum("vi,vib->vb", fit.barycentric(female[0][vertices], hit), female[2][vertices])
        original = self.module.welded(weights)
        # Rigid tread retains its foot or toe attachment. Near the opening the
        # female ankle field moves the leather with the same bending as skin.
        band = smoothstep(.025, .055, points[:, 2]) * (1 - .35 * smoothstep(.105, .145, points[:, 2]))
        blend = (band * (.42 if self.round_number == 2 else .70))[:, None]
        changed = fit.limit_weights((1 - blend) * original + blend * mapping)
        delta = (changed - original)[self.module.unweld]
        return fit.limit_weights(np.maximum(0, weights + delta)).astype(np.float32)

    def bottom_seed(self, seed, female):
        p = seed.copy()
        waist = smoothstep(.370, .429, p[:, 2])
        p[:, 2] -= (.010 if self.round_number == 2 else .017) * waist
        if self.label == "bottom-skirt":
            hips = self.module.names.index("mixamorig:Hips")
            axis = female[3][hips, :2]
            radial = fit.normalized(p[:, :2] - axis)
            hem = 1 - smoothstep(.30, .39, p[:, 2])
            p[:, :2] += (.0035 if self.round_number == 2 else .006) * hem[:, None] * radial
            p[:, 2] += (.004 if self.round_number == 2 else .011) * hem
        return p

    def floor(self, points):
        if not self.sole:
            return points
        p = points.copy()
        for side, lowest in self.sole:
            # Compress or deepen the lowest tread without shifting the ankle.
            # The loaded female sneaker sets the common shod floor in bind.
            z = p[side, 2]
            current = float(z.min())
            influence = 1 - smoothstep(lowest + .0003, .010, z)
            p[side, 2] = np.maximum(self.ground, z + (self.ground - current) * influence)
            contact = side[np.argmin(z)]
            p[contact, 2] = self.ground
        return p

    def finish(self, current, step, multiplier):
        p = self.seed + limit_delta(current + multiplier * step - self.seed, fit.CAP)
        p = fit.protect_style(self.module, current, p)
        return self.floor(p)


def layer_constraints(module, result, layer_poses, layers):
    distances, _, _, _, _, positions = result
    count = np.zeros(len(distances), np.int32)
    corrections = np.zeros_like(module.points)
    faces = module.source_faces.tolist()
    polys = {name: asset.source_faces.tolist() for name, asset in layers.items()}
    for i, p in enumerate(positions):
        cloth = BVHTree.FromPolygons(p.tolist(), faces, all_triangles=True)
        low, high = p.min(axis=0), p.max(axis=0)
        for name, frames in layer_poses.items():
            layer = frames[i]
            if np.any(layer.min(axis=0) > high) or np.any(layer.max(axis=0) < low):
                continue
            other = BVHTree.FromPolygons(layer.tolist(), polys[name], all_triangles=True)
            pairs = cloth.overlap(other)
            count[i] += len(pairs)
            if not pairs:
                continue
            hit = np.unique(module.source_faces[np.asarray(pairs)[:, 0]])
            vertices = module.unweld[hit]
            # Slots stack vertically at the hem or cuff. This preserves the
            # waistband opening and shoe collar circumference during relief.
            np.minimum.at(corrections[:, 2], vertices, -.004)
    for _ in range(3):
        corrections = np.minimum(corrections, .75 * fit.average(corrections, module.graph))
    return count, corrections


def bake(label, source, output, data, layers, number, previous_gate=None, previous_path=None):
    names, neutral, female, rows, matrices = data
    module = fit.Module(source, names)
    selected = frame_selection(rows, previous_gate, label)
    subset = [rows[i] for i in selected]
    transforms = matrices[selected]
    rest = rows[0][2]
    registration = Registration(label, module, neutral, female, rest, number, previous_path)
    points, weights = registration.points, registration.weights
    layer_poses = {name: pose(asset, transforms) for name, asset in layers.items()}
    best_value, best_points, best_weights = float("inf"), points, weights
    history = []

    for iteration in range(7 if number > 1 else 6):
        started = time.monotonic()
        measurement = fit.scan(module, points, weights, subset, transforms)
        overlap, layer_step = layer_constraints(module, measurement, layer_poses, layers)
        value = fit.score(measurement) + 2 * overlap.sum()
        d, pairs = measurement[:2]
        print("BAKE", label, number, iteration, "samples", len(subset), "score", round(value, 1),
              "inside", int((d < 0).sum(axis=1).max()), "pairs", int(pairs.max()),
              "min mm", round(float(d.min() * 1000), 4), "layer", int(overlap.max()),
              "seconds", round(time.monotonic() - started, 1), flush=True)
        history.append(dict(iteration=iteration, sample_count=len(subset), score=float(value)))
        if value < best_value:
            best_value = value
            best_points, best_weights = points.copy(), weights.copy()
            adjustment = fit.clearance_step(module, measurement) + layer_step
            gain = 1.
        else:
            gain = (.52, .78, 1.25)[iteration % 3]
        if not value:
            break
        if number > 1 and iteration == 0 and label == "bottom-shorts":
            best_weights = fit.refit_contact_weights(module, best_points, best_weights, measurement, female, rest)
        weights = best_weights.copy()
        points = registration.finish(best_points, adjustment, gain)
    images = module.write(output, best_points, best_weights)
    return dict(source_sha256=fit.sha(source), output_sha256=fit.sha(output), rounds=number,
                fps=fit.FPS, clearance_margin_mm=1000 * fit.MARGIN,
                maximum_offset_mm=float(np.linalg.norm(best_points - registration.initial_seed, axis=1).max() * 1000),
                texture_images=images, training_history=history)
