# Tripo settings, costs and experience (CLI and Studio)

Status: observed 2026-11-18 on the owner's account while building the GJH
modular chibi. Everything below was seen in a real run or on the real Studio
screen; items marked "not tried" were only read from the UI. Prices change, so
re-check before relying on them. Related: `docs/gjh-modular-chibi-tripo-pipeline.md`.

## 1. Two credit pools

| Where | Balance seen | Used by |
| --- | --- | --- |
| Tripo CLI / API key (`tripo balance`, profile `default`, region `ov`) | 180 | `tripo make`, `tripo anim rig`, `tripo mesh ...` |
| Tripo Studio web account (same login, `studio.tripo3d.ai`) | 5,735 | Studio generate, retopo, segment, texture, rig |

They are separate pools: authorising the CLI in the browser (`tripo login --region ov
--profile studio --no-wait`, enter the code at `developers.tripo3d.ai/en/cli-auth`)
returned the same key and the same 180 credits. Top up API credits at the developer
billing page (`tripo topup`); the owner pays, never the agent.

## 2. CLI (Tripo CLI 0.11.2)

| Command | Cost seen | Notes |
| --- | --- | --- |
| `tripo make IMG --dry-run --json` | 0 | only `make` and `model texture` support `--dry-run`; read `generation_credits_estimate` |
| `tripo make IMG` (P2 image to 3D) | 110 | ~5k triangles, PBR off by default, GLB with preview |
| `tripo anim rig TASK --rig-type biped --spec mixamo --out-format glb` | 25 | 65 `mixamorig:*` bones incl. fingers; no `--dry-run` |
| `tripo mesh smartsegment --seg-type model` | 55 | on a finished character gave 9 open shells, no clean body: not usable for modular parts |
| `tripo balance` / `tripo whoami` | 0 | whoami shows the masked key and profiles |
Rig specs: tripo, mixamo, actorcore, unity, unreal, vrm (biped; the last three need rig v3.0).
Rig types: biped, quadruped, hexapod, octopod, avian, serpentine, aquatic, others (v3.0).

## 3. Studio web (observed UI and prices)

Left toolbar: Image, Model, Segment, Fill Parts, Retopo, Smart UV, Texture, Edit, Upscale, PBR, Rig, Animate, App.
Top: Home, Assets, Agentic Canvas (beta), Creator Hub, DCC Bridge.

| Tool | Options seen | Cost |
| --- | --- | --- |
| Home quick generate from image | modes Best Quality / Clean Topology | 55 |
| Model (HD Model tab) | tabs HD Model / Smart Mesh; Generate Multi-Views; Generate in Parts (members, trial x1); 8K Texture (members, trial x1); Privacy (Sharing Only) | 55 |
| Geometry & Texture panel | Ultra Mesh Quality (on), AI Complete (off), Texture (on), Texture Quality 2K / 4K (default) / 8K (trial), Remove Lighting (on, "New"), PBR (on), Topology Quad / Triangle (default Triangle), Polycount 500 to 2,000,000 (default 2,000,000) | part of the 55 |
| Retopology | Quad or Triangle, Smart Mesh P1.0 toggle, Polygon Count 500 to 10,000 (default 10,000, quad polygons) | 40 |
| Segment | Custom (describe parts such as "head, body, hands") or Auto; Fill Parts is a separate tool | 40 |
| Texture generator | texture style, Remove Lighting, Resolution 2K / 4K / 8K (trial) | 20 |
| Edit (Magic Brush) | Gen Mode / Paint Mode, prompt up to 1,000 chars, Creativity Strength 0.6 | 5 per preview |
| Smart UV | shows the UV layout and Utilization (67.1% on the retopo body); warns that it removes the current texture (re-texture after saving); Unwrap UV | 20, shown as free trial x2 |
| Rig (Humanoid or Other) | "Use a T- or A-pose for best results"; Skeleton Preset: ActorCore, Mixamo, UE5 Mannequin, VRM 1.0 Humanoid, Unity Humanoid Compatible | Auto Rig 20 |
| Animate | text prompt (for example "Make the character walk"), a video tab, duration slider (default 5 s), Multi-stage Motion (new), Preset list (afraid, agree, ...) and an AI Animation tab | Generate 20 |
| Upscale, PBR | not opened | not read |
| Export | formats USD, FBX, OBJ, STL, GLB, 3MF; FBX targets Blender, Mixamo or 3ds Max; texture resolution 4k default; Save must be clicked after a retopo before Export; the file lands in Downloads, named after the task id | free |

Result of the first Studio run (base body from `generated/base-body-neutral-tpose.png`,
Best Quality, default settings): 1,925,666 triangles and 984,378 vertices, 4K texture.
That is far above the 5k to 10k budget, so a retopology pass (quad, about 5,000 polygons)
or Blender decimation is required before use. Hands looked more detailed than the CLI P2
model (separate fingers, palms down), but this was judged on a screenshot only.

## 4. Experience and rules of thumb

- Read the price before pressing Generate; the screen shows it on the button.
- Do not segment a finished character for modular parts; generate each part from its own image.
- A heavy Studio model is a source, not a deliverable: retopo or decimate, bake texture to 1024 px.
- The CLI cannot see Studio tasks and vice versa: a Studio model has to be exported and re-imported
  (`tripo anim rig` accepts a task id or a model file; the file route was not tried).
- Exporting or downloading from Studio is a file download: ask or use the owner's explicit approval.
- Output licence for redistribution is not specified in what was read; record it, do not infer it.
- Browser automation: the file input is hidden, upload with the file-upload tool, never by clicking the picker.

## 5. Studio retopo body, measured in Blender (2026-11-18)

`output/modular-chibi-parts/studio-base/studio_base_retopo.glb` (Studio Best Quality 55 credits + quad retopo 5,000 polygons 40 credits; exported GLB): 8,454 triangles, 7,620 vertices, height 0.978, arm span 0.82, feet on z=0, faces the viewer (+Z), left-right mirror error 0.0001. Hands: about 1,785 faces per hand, but the fingers touch with no gaps and the thumb points down with the palm facing forward, exactly like the CLI base body. Conclusion: the Studio route does not fix the hand problem by itself; the retopo smoothed the fingers together. The repaired-hand body in `master/` (Codex Astra repair) stays the working body.
