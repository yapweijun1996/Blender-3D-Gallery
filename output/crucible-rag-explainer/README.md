# What is RAG? (Crucible explainer)

A 28-second animated explainer of Retrieval-Augmented Generation (RAG), authored as one procedural scene in Crucible 0.21.0 (`@codepawlhq/crucible`, MIT) through its MCP server. It does not use a Blender scene or imported models.

- [MP4](rag-explainer.mp4)
- [Contact sheet from the final MP4](contact-sheet.png)
- [Poster frame at 27.5 s](poster.png)
- [Scene recipe](rag-explainer.recipe.json) (`crucible.scene`, schema 1, including `motion`)
- [Generator and MCP client scripts](scripts/)

## Story

| Time | Station | What happens |
|---|---|---|
| 0–3 s | Title | "What is RAG? Retrieval-Augmented Generation" over the whole pipeline |
| 4–7 s | Question | A user asks "What is our refund policy?" and the question becomes a glowing query orb |
| 7–11 s | 1. Retrieve | The query turns into a vector, the knowledge base of 12 chunks is searched, and the top 3 chunks (#6, #7 and #11) light up |
| 11–16 s | 2. Augment | The question and the 3 retrieved chunks are placed on one prompt card |
| 16–20 s | 3. Generate | The prompt goes into the LLM, which pulses while it generates |
| 20–24 s | Answer | "Refunds within 30 days of purchase." with "Source: #7" |
| 24–28 s | Recap | "Retrieve -> Augment -> Generate" over the full pipeline |

## Render

| Setting | Value |
|---|---|
| Render job | `kind: video`, 1280×720, 24 fps, `duration: 28`, `motion: { start: 0 }`, `quality: realtime-high`, `encoder: cpu` |
| Backend | `gpu` (ANGLE Metal on Apple M4), libx264 |
| Measured | 672 frames, 28.000 s, 6,016,378 bytes, 55.7 s wall time, 210 MiB peak, `fallbacks: []` |
| Scene | 67 parts, 63,616 triangles, 18 materials, 45 motion tracks with 411 keys |
| SHA-256 | `0cbe1bdc0d6e1aabc09dea75216922c58b121eae4b1fc663b15e4e2561210f46` |

The numbers above come from `scene_render_result` and `ffprobe`. Legibility, framing and story order were judged by eye from `scene_look` previews, a draft stills job, a 3-second draft video slice and eight frames taken from the final MP4.

## Known limits

- The video has no audio track.
- All on-screen text is English. Crucible's built-in text font is DejaVu Sans with printable ASCII only, and the MCP server cannot load another font.
- Each text character costs about 640 preflight vertices per curve segment, and the scene budget is 250,000. The labels therefore use `curveSegments: 1` and short wording.
- The motion schema has no visibility track, so objects appear and disappear by scaling to 0.001.
- `scene_inspect` reports a `subject-out-of-frame` warning for the base camera. This is expected: the close-up shots frame one station at a time.
- The dark backdrop gradient shows slight H.264 banding.

## Reproduce

1. Put the scripts in a folder and install the packages there: `npm install @codepawlhq/crucible@0.21.0 @modelcontextprotocol/sdk`. Chrome and ffmpeg are expected at `/Applications/Google Chrome.app` and `/opt/homebrew/bin/ffmpeg`.
2. Run `node build-recipe.mjs` to write `recipe.json` next to the scripts.
3. Run `node run.mjs look 0,10,17.6,28` to save preview frames.
4. Run `node run.mjs job '{"kind":"video","width":1280,"height":720,"fps":24,"duration":28,"motion":{"start":0},"quality":"realtime-high","encoder":"cpu"}' final` to render the MP4.

Each run starts its own MCP server and creates the scene from the recipe. One run covers `scene_create`, `scene_inspect`, `scene_look`, `scene_render_submit`, status polling, `scene_render_result` and `scene_render_release`.
