# Mall Retail Pop-Up Cart

V2.1 P0 item **440**, one independent logical model. Four separate caster modules, open rear storage, timber counter, jade enclosure, canvas canopy and editable original LOCAL FINDS sign. Blender metre units, floor-centred origin, front −Y; glTF +Y up / +Z front.

Source: `sources/mall-retail-pop-up-cart.blend`. Generate with Blender 4.0.2 background `--python generate.py`; re-export saved edits with `--python generate.py -- --export-source`. Multi-angle renders: `render_previews.py`. Validation: `inspect_sources.py`, `node validate.mjs` and `scripts/test-mall-retail-pop-up-cart.mjs` from repo root.

13 independent modules; four wheel modules and sign remain individually editable. No runtime driving, vendor simulation, animations or physical certification is claimed. Geometry and lettering are original; bundled Blender Bfont. Export helpers reuse this project's tray-station implementation. Owner-project reuse authorized; public redistribution unspecified, downloads disabled.

See [verification](verification.md) for measured results and native-mobile limitations.
