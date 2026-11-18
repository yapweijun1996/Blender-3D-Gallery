# GJH Modular Chibi: Tripo to Blender to Mixamo skeleton to GJH Virtual Mall

Status: working plan v0.2, 2026-11-18 (Section 8 holds measured results). Nothing in this document is a shipped
feature. Sections marked "Verified" were observed in this repository session;
everything else is a proposal to be proven by the MVP.

Related documents: `docs/chibi-framework-design.md` (procedural framework
proposal), `docs/chibi-character-standard.md`, `docs/chibi-mall-visitor-modular-build-plan.md`.
This document covers the Tripo-based route only. The procedural Blender route
stays an alternative when Tripo parts do not pass the gates below.

## 1. Principle

One Base Body + one skeleton + many replaceable modules. A garment, hairstyle
or shoe is never a full character. Every module declares the skeleton it was
skinned to, so animation is authored once.

## 2. Standard (from the GJH clothing specification v1.0)

All values are relative to total height H = 1.00 (about 3 heads).

| Item | Value |
| --- | --- |
| Head height | 0.33 H |
| Shoulder width | 0.44 H |
| Arm length (shoulder to fingertip) | 0.38 H in the spec; the accepted Base Body measures about 0.31 H (owner accepted, 2026-11-18) |
| Waist width | 0.26 H |
| Hip width | 0.32 H |
| Leg length | 0.50 H |
| Foot length | 0.18 H |
| Pose | T-pose, arms horizontal (90 degrees), legs slightly apart |
| Origin | (0, 0, 0) at the floor between the feet, +Y up in glTF, facing +Z |

Skeleton (Mixamo/glTF compatible): Hips, Spine, Spine1, Spine2, Neck, Head,
LeftArm/LeftForeArm/LeftHand, RightArm/RightForeArm/RightHand, LeftUpLeg/
LeftLeg/LeftFoot, RightUpLeg/RightLeg/RightFoot (Mixamo names carry the
`mixamorig:` prefix; fingers optional).

Attachment points (bone sockets, empties with fixed local transforms):

| Socket | Parent bone | Used by |
| --- | --- | --- |
| Head_Attach | Head | glasses, hats, headphones |
| Back_Attach | Spine2 | backpack, wings |
| Chest_Attach | Spine2 | lanyard, badge |
| Waist_Attach | Hips | belt, pouch |

Module classes and the region they cover:

| Module | Covers | Bound to | Compatible with |
| --- | --- | --- | --- |
| Hair | skull | Head | any face |
| Top | torso and sleeves | Spine..UpperArm | all bottoms |
| Bottom | waist to ankle | Hips, UpLeg, Leg | all tops |
| Skirt | waist to thigh | Hips, UpLeg | all tops |
| Dress | torso plus skirt | Spine, Hips, UpLeg | stands alone (replaces top and bottom) |
| Shoes | feet | Foot (and toe) | all |
| Accessory | per socket | attachment point | by socket |

Naming: `top_hoodie_v1.glb`, `bottom_pants_v1.glb`, `skirt_pleated_v1.glb`,
`dress_maid_v1.glb`, `shoes_sneaker_v1.glb`, `acc_glasses_v1.glb`.

Different body types (slim, chubby, 2.5 or 3.5 heads) are NOT assumed
compatible. Each body type needs its own fit rules and its own module set.

## 3. Pipeline

### Stage 0: reference sheets (done for part of the set)

- `output/modular-chibi-parts/white-bg/` holds 21 single-subject 1024 px
  images split from the three reference sheets: 13 shoe pairs, 2 tops,
  3 bottoms, 3 hairstyles. A transparent variant is kept for compositing.
- Still needed for a complete first set: Base Body in strict front and side
  T-pose, glasses, backpack, and garments drawn in T-pose shape on the Base
  Body. Codex CLI is used to generate these (see Section 6).

### Stage 1: Tripo (Image-to-3D)

Verified findings (one test, task `f8b341f6`, 2026-11-18):

- Image-to-3D with the P2 model costs 110 credits and gives a good, stylistically
  faithful full character.
- `tripo mesh smartsegment --seg-type model` (55 credits) splits it into 9
  parts, but the parts are open shells (face mask, hollow jacket) and the skin
  of the neck, limbs and hands is merged into other parts. There is no separate
  base body, and a waving pose is not a T-pose.
- Therefore, do not rely on segmenting one finished character into modules.

Adopted approach:

1. Generate the Base Body once from the front T-pose reference. Gate: symmetric,
   five separated fingers, visible gap between legs, no glasses, no loose cloth.
2. Generate every garment, hairstyle, shoe pair and accessory as its own model
   from its own reference image, one task each, never in a batch.
3. Keep seeds, task ids and prompts in each module's `metadata.json`.

Budget: about 110 credits per model. 21 parts is roughly 2,300 credits, so
build the MVP set first (Section 5) and review before spending more.

### Stage 2: Blender master

1. Import the Base Body. Retopologise or decimate to 5k to 10k triangles.
   Normalise scale to H = 1.00, origin at the floor, facing +Z, T-pose.
2. Save `master/GJH_Chibi_Master.blend`. This file is the single reference.
3. For each module: import, align to the master body by landmarks
   (shoulder, waist, ankle), scale-match to the spec widths, remove interior
   or hidden geometry, bake or merge textures to a shared 512 to 1024 px
   atlas where possible, then check the triangle budget.
4. Hide body regions covered by the module with a named body-mask vertex group
   so the runtime can hide them instead of showing poke-through.

### Stage 3: skeleton and animation

- One skeleton is authored once on the Base Body and reused by every module.
- The Tripo CLI already produces Mixamo-compatible rigs: `tripo anim rig`
  gives `mixamorig:*` bones and `tripo anim retarget` applies Mixamo-style
  presets. Verified in this repository (`models/tripo-chibi-motion`: 7 clips,
  Tripo's official preset run included). Uploading to mixamo.com requires an
  interactive Adobe login, so it is not part of the automated path; if the owner
  prefers Mixamo, export the cleaned Base Body FBX and download clips by hand.
- Skin weights for each module are transferred from the Base Body (Data
  Transfer, nearest face interpolated), then fixed by hand at shoulders,
  elbows, hips and knees. Rigid items (shoes, glasses, backpack) are parented
  to a bone or socket instead of skinned.
- Required clips for the MVP: Idle, Walk, Wave. Next: Run, Sit.

### Stage 4: GLB export and QA

- Separate files: `master/base_body.glb` (mesh, skeleton, morph targets),
  `modules/<class>/<id>.glb` (mesh plus skin referencing the same bone
  names), `animations/<clip>.glb` (armature only).
- Gates per module: glTF 2.0 validator with zero errors, bone names identical
  to the skeleton file, triangle budget met, no NaN weights, at most 4
  influences per vertex, textures at most 1024 px.
- Combined gate: every module combination (top x bottom x shoes x hair) is
  rendered in the rest pose and in Walk and Wave and inspected for poke-through.
  Because combinations grow quickly, test the full cartesian product for the
  MVP set and a sampled set afterwards.
- Keep `source` information (reference image, Tripo task id, seed, Blender
  file) next to every module. Tripo output licence for redistribution is
  unspecified; record that and do not infer one.

### Stage 5: GJH Virtual Mall (runtime)

- Load the skeleton and body once; load module GLBs and bind their
  `SkinnedMesh` objects to the shared skeleton by bone name. Cloning a
  character should use three.js `SkeletonUtils.clone()`.
- Configuration is a small JSON, for example
  `{ "body": "base_v1", "hair": "hair_bob_v1", "top": "top_hoodie_v1",
  "bottom": "bottom_cargo_v1", "shoes": "shoes_sneaker_v1", "acc": [] }`,
  stored in localStorage or IndexedDB and restored on reload. Multiplayer syncs
  this configuration and the current clip, never mesh data.
- Gallery integration: keep it a reusable module of the gallery's asset
  library, not bound to one Mall page. Gallery cards stay light and load 3D only
  when needed, with loading, error and accessibility fallbacks.

## 4. Budgets and acceptance

| Item | Initial target |
| --- | --- |
| Base Body | 5,000 to 10,000 triangles |
| Hair | 1,000 to 3,000 |
| Outfit (top or bottom) | 2,000 to 6,000 |
| Accessory | 200 to 1,500 |
| Whole character | 20,000 or fewer |
| Textures | 512 to 1024 px, shared atlas where possible |
| Animation | Idle, Walk, Run, Wave, Sit |
| Output | GLB / glTF 2.0 |

These are starting targets, not limits imposed by Tripo or Mixamo.

Acceptance: no poke-through for any combination, Walk and Run show no bone
mismatch, two instances animate independently, frame rate is stable on a
mid-range phone, and the avatar configuration survives a reload. Each item
needs evidence (render, test output, device capture) before it is claimed.

## 5. MVP scope

1 Base Body, 3 hairstyles (bob, spiky, twin tails), 2 tops (hoodie, T-shirt),
2 bottoms (cargo pants, shorts), 2 shoe pairs (high-top, boots), 1 pair of
glasses, 1 backpack, clips Idle, Walk, Wave. About 12 Tripo generations
(roughly 1,300 credits), run in this order and reviewed after each class:
Base Body, one top, one shoe pair, one hairstyle, then the rest.

## 6. Image generation with Codex CLI

Missing reference images (Base Body front and side T-pose, glasses, backpack,
and garments in T-pose shape) are generated by `codex exec` with the existing
reference sheets attached, saved to `output/modular-chibi-parts/generated/`.
Generated images are inputs only and must pass the same gate as Tripo output
before being used.

## 7. Risks

- Tripo parts may arrive as shells or with baked-in shadows; budget a
  Blender cleanup pass for every part.
- Tripo may refuse an exact T-pose or return different proportions; the body
  must be checked against Section 2 before anything is fitted to it.
- Auto skin weights at shoulders and hips are the usual failure point.
- Hair volume can intersect the hood or the backpack; define allowed
  combinations per module in its metadata.
- Redistribution terms for Tripo output, and for AI-generated reference
  images, must be confirmed before publication.

## 8. Measured results (2026-11-18)

Verified in this repository session with Blender 5.1.2 headless and the Tripo CLI.
Credits: base body 110 (task f2ac8276), Mixamo rig 25 (eee65d27), hoodie 110
(34a980eb); balance 400 before the hair task.

| Item | Result |
| --- | --- |
| Base Body | `output/modular-chibi-parts/master/base_body.glb`: 1 mesh, 1 skin, 65 joints, 5,206 triangles, height 1.0, no animation |
| Orientation | Tripo output faces glTF +X with origin at the body centre; rotated to +Z, feet at z=0. Left bones at +X, nose at -Y in Blender, T-pose arm angle -2 degrees |
| Symmetry | left-right mirror mean error 0.0001 |
| Arm length | about 0.31 H, shorter than the 0.38 H in the spec; accepted by the owner |
| Rig | 65 `mixamorig:*` bones with fingers, max 4 influences, 0 unweighted vertices; names identical to `models/tripo-chibi-motion/motion.glb`, whose clips retarget (wave, jump, run, walk checked on 2 frames each) |
| Blender 5 | an imported action needs `armature.animation_data.action_slot = action.slots[0]` or the pose stays T |
| Hoodie (Tripo) | 5,096 triangles, a real hollow garment; Tripo-normalised size and facing +X, not yet fitted |
| Hands | 482 triangles per hand; separate fingers (7 to 8 slice loops); palms face forward with the thumb down; 70 vertices blend two fingers (more than 0.2 weight) |

Hand repair (palms down, finger spacing, weight cleanup) was delegated to Codex
`gpt-6.2-astra` and is not verified. Garment fitting, hair, shoes, glTF
validation and runtime tests are not done.
