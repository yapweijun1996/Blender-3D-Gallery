# Hawker Tray Return Counterweight Cover

An original, unbranded Singapore hawker-centre-inspired tray-return bay cutaway in teal and stainless steel. Inspect the two captured guide channels, steel cover, pulley and exposed moving counterweight. The staged empty sample tray is fixed. This is a fictional 3D demonstration, not operational, installation, hygiene or engineering guidance. The asset does not copy a stall, vendor, or actual implementation.

The [NEA GeBIZ tender NEA000ETQ26000038](https://www.gebiz.gov.sg/ptn/opportunity/opportunityDetails.xhtml?opportunity_id=1000000000000522168&code=NEA000ETQ26000038&origin=rss&status=RELEASED&type=TQ) documents the fixture class (a sliding cover frame and counterweight fitted to hawker-centre tray return racks). The [NEA overview](https://www.nea.gov.sg/our-services/hawker-management/overview/) explains the setting only. All geometry, lettering, scene motion and imagery here are original. No external asset or texture.

- Blender 4.3.2; SI model scale; floor origin, Blender −Y front/+Z up, glTF +Z front/+Y up. Stage and lights are not exported.
- Reproduce in a clean new output directory: `blender -b --python-exit-code 9 --python generate.py -- --output /tmp/new-tray-cover`. `--skip-render` reproduces only the native scene and GLB. `--review /tmp/new-review` is optional.
- One `TRAY_RETURN_COVER_LIFT` clip, 0–2.20 s. The cover rises and weight descends the same modeled distance; two vertical cable runs keep their combined length, across an actual static fractional-turn line over the pulley. The in-Viewer reset and reduced-motion choices act only on this scene.
- Validation: `node verify.mjs`; `blender -b --python-exit-code 9 --python verify_blender.py` reads the saved source and re-imports the exact GLB. Numeric clearances apply only to the fictional model.
