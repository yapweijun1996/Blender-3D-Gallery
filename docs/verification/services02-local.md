# Service and heritage batch 02

17 original independent assets: 417–420 and 441–453. All local PASS; all overall NEEDS REVIEW for untested physical Android/iOS and Safari/WebKit. No deployment, push or PR from producer.

51 exported-GLB studio views inspected. Final 51 Gallery cases comprise 48 unchanged cases plus 3 final door cases; all actual GLB hashes bound. Six animated assets / seven clips, independently expected raw endpoints, Mixer poses, fixed components and clearance. Browser animation images differ open and reset exactly. Source proofs save/reopen a copied .blend with both mesh and roughness edits; canonical sources unchanged.

## Corrections and retained failures
Initial visual inspection found floating fixtures, coplanar shelf/jamb faces and disconnected lattice joins; geometry corrected before acceptance. Generic non-branded labels added. 451 label reduced to fit pedestal. Initial export helper omitted animation, caught by unchanged structural assertion; saved sources re-exported with animation enabled. 441 open leaf intersected jamb, caught by original clearance assertion; forward hinge brackets and thinner leaf/rails preserve original width/height assertions and add nine sweep non-intersection samples. A resulting glass/rail coincident face was separated before final render/browser proofs. Original snapshots and failure logs retained. No budget increases or weakened assertions.

## Portable checks
```sh
node scripts/validate-services02.mjs
blender --background --threads 2 --python-exit-code 1 --python scripts/inspect-services02.py
node scripts/test-services02-source-edit.mjs
node scripts/test-services02-animation.mjs
npm test
npm run build
MALL_QA_DIR=output/services02-browser node scripts/test-services02-browser.mjs
MALL_QA_DIR=output/services02-animation node scripts/test-services02-animation-browser.mjs
```
Run source/structural checks in an isolated fixture if preserving shipped reports. Browser scripts accept MALL_QA_DIR without changing assertions.

See services02-local.json for every asset status, metrics and evidence.

Original build logs are preserved byte-for-byte in the adjacent `.log.raw.gz` files. Display `.log` copies only trim trailing whitespace from the Vite reporter line so diff checks remain clean.
