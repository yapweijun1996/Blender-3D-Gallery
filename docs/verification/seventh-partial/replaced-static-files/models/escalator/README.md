# Escalator V1 ID004

Original Blender procedural asset in metres. The lower landing floor datum is
the root origin. Blender is Z-up with -Y front; the GLB is exported Y-up with
glTF +Z front.

The model is a static, complete visual assembly: independently named treads
and risers, lower/upper landings, comb plates aligned to the tread groove
direction, side guards, sloped truss, under-return enclosure, separate
maintenance panel, and continuous-looking rounded handrail paths. It does not
claim a circulating step chain, operating handrail, safety certification, or
gallery interactivity. Mechanism status is **NEEDS REVIEW**.

Fixed admission budgets: 70,000 triangles, 6,000,000 GLB bytes, 220 mesh
primitives. The generator uses no textures or external models.

Generation: `blender-local.sh --background --threads 2 --python-exit-code 1 --python generate.py`

Verification records actual Blender, GLB validator, browser, and build outcomes
under `MALL_QA_DIR`; Android, iOS, and Safari are explicitly not tested by the
local browser check.
