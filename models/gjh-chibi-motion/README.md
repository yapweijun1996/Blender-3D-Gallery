# GJH Chibi Motion Studio

Open `?page=chibi-motion` from Interactive Demos. Select Idle, Wave, Nod or Walk, drag to orbit, or pause and scrub the clip. Scrubbing pauses playback. Reduced-motion visitors start paused.

The character was generated from the owner's GJH character reference using Tripo P2. The Tripo biped rig and in-place walk are the inputs to the Blender authoring script. Idle animates the spine and head, Wave raises the left arm with a two-beat forearm gesture, and Nod uses two head dips. All four clips are embedded in one textured GLB. Walk includes vertical root compensation sampled at 60 Hz from the lower shoe. This addresses floor height only.

To rebuild from the original Tripo walk GLB, use Blender 5.1:

```sh
blender -b --python-exit-code 1 --python models/gjh-chibi-motion/author.py -- /path/to/walk.glb models/gjh-chibi-motion/visitor.glb
node models/gjh-chibi-motion/check-motion.mjs
```

The check samples 180 poses using the exported skin in Three.js. The poster shows the original generated character in its resting pose.

## What the walk test measures

The original retargeted walk dipped below the floor. Across 56 Blender frames, the lowest shoe vertex reached about −44 mm on the left and −39 mm on the right. At the frame with the highest supporting sole, the lower of the two shoes was still about 17 mm below the floor. A single height offset would leave a changing gap or penetration during the stride.

[The authoring script](author.py) measures vertices weighted predominantly to foot and toe bones on the evaluated mesh. For each sample it adjusts the armature root vertically by the signed distance to the floor. It preserves horizontal root motion and converts Blender's vertical Z coordinate to glTF's vertical Y translation. Inspect the existing root channels before adding a translation track.

[The consumer check](check-motion.mjs) loads the exported GLB, checks the four clip names and plays Walk with Three.js. At each of 180 evenly spaced poses it evaluates every skinned vertex in world coordinates. On this upright character the shoe is the lowest point. The maximum absolute distance from that point to the floor was **1.20 mm** against a **4 mm** project tolerance. A pose with an airborne phase, trailing clothing or a prop below the shoes needs a different contact mask. Horizontal foot sliding requires tracking a planted foot across its stance phase.

## Repeating the browser check

1. Start at Interactive Demos and launch Chibi Motion Studio from its card. Select each of the four clips.
2. Pause each clip, drag the timeline to a distinct pose, then resume. Check that the character and the displayed time move together.
3. Orbit to inspect the shoulder and sleeve during Wave. Inspect knees, shorts and alternating shoe contact during Walk.
4. Check controls at a narrow viewport, then navigate back to the demo index and confirm the character canvas is gone.

The reference run used Blender 5.1.2 and Three.js 0.187.0. The desktop browser and narrow viewport checks cover playback and navigation. A physical-device performance benchmark and a horizontal foot-slip measurement are separate checks.
