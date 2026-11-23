# Hair redesign and module review

Status: **REWORK** for close matching to the supplied reference. The hair is a separate editable mesh and a separately exported module; the exact source, export and image hashes are in `run-007/manifest.json`.

Independent visual review of the six source views and four views re-imported from the final character GLB found no visible export damage. The front hair retains a rounded chibi appearance and leaves the eyes clear; the tall narrow tuft and elongated side points were shortened. In candidate 006, dark gaps opened on both sides; restoring coverage in candidate 007 removed them. Earlier candidate images remain under the numbered folders.

The rear locks remain more regular, symmetric, rounded and layered than the reference's irregular swept locks. The top lacks the reference's short, wide raised tufts. Those reference-matching criteria remain open; do not describe this candidate as a complete match.

The module and full character GLBs passed Khronos validation with zero errors and warnings. The character contains a hair node with `extras.partSlot = Hair`, nine joints and five draft clips. In the Blender re-import swap test, the original hair could be hidden and the standalone mesh aligned to the head at rest and one combined head rotation, with maximum geometric deviation below 0.000001 m. Reports: `module-validation.json`, `rigged-validation.json`, `hair-module-test.json`, and `character-swap-test.json`.

The 62,860-triangle hair and 105,482-triangle character exceed the reference's proposed low-poly budget. The documented Three.js attachment transform and visibility switch also passed a Node GLTFLoader smoke test (`three-swap-test.json`); browser rendering, complete animation playback, other head poses and renderer-specific appearance were not tested. Previous sit/rig limitations remain.
