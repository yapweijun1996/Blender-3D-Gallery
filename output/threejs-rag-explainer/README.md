# What is RAG? (three.js explainer)

A 28-second animated explainer of Retrieval-Augmented Generation, built with three.js r170 (MIT, vendored in `vendor/`). The whole animation is a pure function of time, so frames are reproducible.

- [MP4](rag-three.mp4) — 1280×720, 24 fps, 672 frames, 28.0 s, 7.6 MB, H.264, no audio
- [Contact sheet](contact-sheet.png)
- `index.html` — interactive preview with play/pause and a time slider (serve this folder over HTTP, for example `python3 -m http.server`)
- `scene.js` — scene, storyboard, camera path and captions
- `render.mjs` — steps the scene to exact times in headless Chrome and pipes the frames to ffmpeg

## Story

question → embed and search the knowledge base → top-3 chunks → augmented prompt (question + context) → LLM generates → grounded answer with a source. Captions under the picture narrate each step.

## Reproduce

```bash
npm i playwright-core          # in any folder, then: PW_FROM=<that folder>
PW_FROM=<folder> node render.mjs video rag-three.mp4 24 0 28
PW_FROM=<folder> node render.mjs stills 0,10,20 /tmp/stills
```

Needs Google Chrome at `/Applications/Google Chrome.app` and `ffmpeg` on PATH. SHA-256 of the committed MP4: `a8cf3f1ccf4871880f35b9759e3f40830d7583d49737d59e8bd52536877f9a17`.

## Verified vs judged

Measured with ffprobe: size, frame count, duration, fps, codec. Legibility, composition and story order were judged by eye from preview stills and frames extracted from the final MP4. The page logged one 404 (a favicon request); no script errors.

## Limits

- No audio. Text is English (canvas text could carry any language if you want a localized version).
- Dust particles use a fixed pseudo-random seed set for the starfield only; it does not affect timing.
