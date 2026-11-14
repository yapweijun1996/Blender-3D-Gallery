# Escalator004 circulation: bounded rejected mechanism candidate

Reason for this isolated follow-up: implement the previously missing escalator step/handrail circulation. Base static draft is immutable commit b4d71d712881fcf43200f61070475155c1b4e118. No original source, GLB, previews, catalog, or other seven models changed. No remote action.

## Outcome

Candidate FAIL; asset remains NEEDS REVIEW. No animated Blender/GLB was generated because the rigid-step geometry failed a necessary nonintersection gate before export. A repeating path alone is not a valid mechanism.

The candidate has a3m rise,30-degree main incline,0.6m-radius smooth upper transitions,1.2m level landings,0.275m-radius concealed reversals and an inverted lower return.48 rigid steps occupy a19.141412m loop at0.398779m pitch. Each step uses a0.398m-deep horizontal tread and a rigid trailing riser. Treads remain horizontal on the upper run and rotate rigidly through reversal, rather than disappearing or passing through guards.

241 full-cycle samples check46,272 adjacent tread/riser polygon pairs. Since every step has the same1m X extrusion, positive YZ polygon overlap proves3D intersection. SAT touching/separated/positive-overlap control cases passed. This adjacent-only test is reject-only; a pass would not certify every nonadjacent component or fixed guard.

The first fixed200mm-riser candidate also collided on the straight incline because exact closed-loop pitch implies a199.3897mm rise per step. Its complete script/results/log are retained under initial-fixed-200mm-riser/. Correcting that geometric mismatch removed straight-incline collisions without changing the intersection assertion. The corrected rigid profile still intersects at flattening and reversal regions, with up to12mm positive SAT overlap. See result.json, collision-examples.json and the actually inspected rejected-profile-overlap.png diagram. This diagram is a cross-section diagnostic, not an asset render or browser screenshot.

Loop positional closure is3.58e-15m, but does not resolve collision. Handrail equal-speed scheduling must use its own loop period if its loop length differs. The report includes only an illustrative period calculation, explicitly NOT verified handrail geometry or motion evidence.

## Unmet criteria

- Nonintersecting rigid tread/riser flattening and turnaround.
- Actual comb, landing and guard swept clearances.
- Matched handrail geometry and linear-speed proof.
- Blender/GLB raw motion tracks and full-cycle exported sampling.
- Rendered extreme-pose and browser motion inspection.

A curved-riser and dual-wheel/dual-track constraint design could address these failures; this bounded test does not prove that no valid mechanism exists. It does show that directly circulating the present rectangular profile is invalid. No weak test, disappearing/scaled riser, conveyor texture, fake operation, budget increase or safety-certification claim was used. Fixed70,000triangle/6,000,000byte/220primitive budget remains unchanged; no new geometry was generated.

Run python3 models/escalator/reports/circulation-feasibility/check_rigid_chain.py. Expected exit1 records the rejected candidate. This intentional failure is not included in npm test as a false passing implementation. Existing asset suite was not rerun because only these isolated diagnostic files were added; static asset hashes were verified unchanged against the base commit.
