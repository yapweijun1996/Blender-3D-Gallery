# Mall Water Dispenser

Original Shopping Mall list 009 public corridor drinking fixture. The cabinet, recessed bottle bay, drip grate, spout, cold/ambient controls, and service panel are separate editable parts. The service panel has one authored 2.5-second open/close clip.

Fixed budgets: under 12,000 triangles, 80 mesh primitives, and 1 MB GLB. Geometry is authored in metres with Blender `+Z` up / `-Y` front and exported glTF `+Y` up / `+Z` front.

From the repository root, after the Blender 4.0.2 wrapper is available:

```sh
/srv/agent-workstation/workspaces/blender-mall-four-20261112/blender-local.sh --background --threads 2 --python-exit-code 1 --python models/mall-water-dispenser/generate.py
/srv/agent-workstation/workspaces/blender-mall-four-20261112/blender-local.sh --background --threads 2 --python-exit-code 1 --python models/mall-water-dispenser/inspect_sources.py
/home/ai-agent/.local/bin/node models/mall-water-dispenser/validate.mjs
/home/ai-agent/.local/bin/node models/mall-water-dispenser/verify_source_edit.mjs
/home/ai-agent/.local/bin/node --test tests/mall-water-dispenser.test.mjs
```

The asset is illustrative only: it does not claim live water, plumbing, refrigeration, hot-water, safety, hygiene, accessibility, certification, or engineering behavior.

## Local evidence (2026-11-14)
PASS: 3,252 triangles; 177,716-byte GLB; 27 mesh parts; 7 materials; one 2.5-second ServicePanelOpenClose clip. Khronos zero errors/warnings. Source geometry/material edit saved/reopened/re-exported without modifying canonical source. Five rendered views inspected. Focused two unit tests and build passed. Chromium gallery checks passed at 1440/768/390 widths, plus isolated Three.js animation pixel change/exact reset. Physical Android/iOS not tested. Gallery animation controls are not claimed.

Preserves all 483 catalog entries from main47ef999f, adds one. This is original Shopping Mall list item009, not an inferred ID in the separate 500-model master list. Existing drink-dispenser is a catering twin-juice-tank prop.

Release: NEEDS REVIEW, not deployed. Local checks do not claim remote CI. No PR21 changes made. Evidence is in reports/. Generated Python cache and temporary edits are not release files.

## Corrections retained in audit
Initial generated source was not run successfully by the Codex sandbox. Review replaced a solid cabinet with open modular side/back shells, corrected Blender4.0 render engine and real open-pose preview, and fixed a stale Blender-reference after reopen. Initial validation failed because draft expectations used Blender axis ordering for glTF world bounds and guessed node names. The validator now requires actual designed 0.74m width, 1.48m height, 0.7075m closed depth at 1mm tolerance, proper +Y-up floor and the exact 0.12m rear panel translation; budgets and assertions were not relaxed. The first additive catalog integration duplicated a collection; duplicate validation caught it, and only the new entry was applied to latest main. No failed candidate was published.
