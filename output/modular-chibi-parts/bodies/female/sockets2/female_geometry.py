"""Anatomical pad selection from the original female socket fit."""
import numpy as np

N = 'mixamorig:'


def pads(stage, side):
    """Fixed terminal pulp patches, selected once on the undeformed female mesh."""
    p = stage.rest
    f = np.array(stage.faces)
    xyz = p[f]
    n = np.cross(xyz[:,1]-xyz[:,0], xyz[:,2]-xyz[:,0])
    n /= np.maximum(1e-18, np.linalg.norm(n, axis=1, keepdims=True))
    sets = {}
    for digit, terminal in [('Thumb', '3'), ('Index', '4')]:
        name = N + side + 'Hand' + digit
        bone = stage.arm.matrix_world @ stage.arm.data.bones[name + terminal].matrix_local
        distal, volar = np.array(bone.col[1][:3]), np.array(bone.col[2][:3])
        direction = distal + .65 * volar
        direction /= np.linalg.norm(direction)
        named = np.char.startswith(stage.labels, name)
        tip = (p[named] @ distal).max()
        # Require the terminal segment and the exposed palmar/distal side.
        candidate = (named[f].sum(1) >= 2) & ((xyz @ distal).min(1) >= tip-.017)
        support = (xyz[candidate] @ direction).max()
        selected = candidate & ((xyz @ direction).min(1) >= support-.0035) & (n @ direction > .25)
        sets[digit] = [tuple(face) for face in f[selected]]
        if not sets[digit]:
            raise ValueError(f'No pulp triangles for {name}')
    return sets
