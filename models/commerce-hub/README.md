# Commerce hub

Seven isometric miniatures (centre shopping bags, shop, warehouse, delivery, payment, analytics, automation)
used by the Commerce Network demo (`?page=commerce-hub`, `src/commerce-hub/`).

- Source: `source/build_<module>.py` with shared `source/common.py`. Written by Codex CLI `gpt-6.2-sol`,
  reviewed and run in Blender 5.1.2 through the Blender MCP with
  `exec(compile(open(path).read(), path, "exec"))`.
- Outputs: `blend/`, `exports/` (GLB), `reports/` (metrics), `previews/` (gallery thumbnails, made with
  `cwebp -q 80 -resize 640 0` from the renders). `renders/` is regenerated and not tracked.
- The composition anchor images are private and not tracked; `reports/` keeps their hashes.
- Budgets are enforced by `validate.mjs` (part of `npm run validate:assets`).
- Review history and open differences: `REVIEW.md`.

## Demo rendering

The demo merges opaque static surfaces across modules by finish, keeps glass, glow helpers and moving parts
separate, bakes one real-time shadow pass and uses the lighting recorded in `metadata/`. Connection lines are
generated in the browser. Browser check: `npm run build && npm run test:commerce`.

The citrus mark and the square code are original decoration; no real payment brand is shown and the code
encodes nothing.
