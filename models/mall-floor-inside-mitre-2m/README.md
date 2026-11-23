# 2 m mall floor inside mitre

This 90° trim finishes a concave corner where two exposed slab edges meet around an empty floor cell. The champagne cap, 1.5 mm bronze inlay and recessed fascia turn together, with four bronze fasteners facing the void. [Studio render](previews/mall-floor-inside-mitre-2m.jpg)

## Placement

Place the root at the re-entrant slab corner, at finished floor height. At zero rotation the empty quadrant is **+X/+Z** in glTF. The two arms run 2 m along those axes. The 60 mm cap occupies the void side, and the 100 mm fascia covers the existing slab depth. The straight-edge contacts are measured from the concave corner.

| Connector | Finished-floor centre in metres | Next straight trim centre | Straight trim yaw |
| --- | --- | --- | ---: |
| East | (2, 0, 0.03) | (3, 0, 0.03) | 0° |
| Positive Z | (0.03, 0, 2) | (0.03, 0, 3) | 90° |

The 45° top seam runs from (0, 0, 0) to (0.06, 0, 0.06). Positive Z is the finished face of the east arm, and positive X is the finished face of the other arm. Use the original structural floor cells for visitor support. [Compatible 2 m straight edge](../mall-floor-edge-2m/README.md)

## Editing and distance levels

Each LOD contains one welded 17-point profile that turns through a shared diagonal ring. The source provides separate vertex selections for the east arm, positive-Z arm and seam. In Blender the two buttons on each arm share a mesh. At close range each button has a recessed hexagonal socket. LOD1 simplifies the button head. LOD2 carries its two finishes in vertex colours and omits the buttons. [Editable Blender source](sources/mall-floor-inside-mitre-2m.blend)

| Export | Triangles | Material draws | Bytes |
| --- | ---: | ---: | ---: |
| [LOD0](exports/mall-floor-inside-mitre-2m.glb) | 562 | 4 | 28,400 |
| [LOD1](exports/mall-floor-inside-mitre-2m-lod1.glb) | 226 | 4 | 14,672 |
| [LOD2](exports/mall-floor-inside-mitre-2m-lod2.glb) | 98 | 1 | 7,788 |

The generator reads the genuine section faces, materials, button meshes and distant vertex colours from the project's editable straight-edge source. The new cut and studio render are owner-project work. Public download and redistribution terms are unspecified. [Source attribution and hashes](metadata.json)

## Reproduce

Run from the repository root with Blender 5.1.2 and the project's Node dependencies installed. The saved source exports independently. A fresh build reads the sibling straight-edge source and requires a new source filename.

```sh
asset=models/mall-floor-inside-mitre-2m
work=$(mktemp -d)
blender -b --factory-startup -Y --python-exit-code 1 -P "$asset/generate.py" -- --export-source --out "$work/saved"
blender -b --factory-startup -Y --python-exit-code 1 -P "$asset/generate.py" -- --build --source "$work/fresh.blend" --out "$work/fresh"
for glb in "$asset"/exports/*.glb; do
  cmp "$glb" "$work/saved/${glb##*/}"
  cmp "$glb" "$work/fresh/${glb##*/}"
done
blender -b --factory-startup -Y --python-exit-code 1 -P "$asset/verify_blender.py" -- --scratch "$work"
node "$asset/verify.mjs"
```

Both export paths reproduced all three GLBs byte for byte. An isolated saved edit extended the 17 vertices of the east end by 25 mm and moved its connector. Reimport measured 2.025000095 m and LOD1/LOD2 retained their original bytes. All three exports passed Khronos validation with zero errors and warnings. [Rebuild](reports/rebuild.json) · [Source inspection and edit](reports/source-reimport.json) · [glTF validation](reports/glb-validation.json)
