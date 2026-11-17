# GJH Chibi Motion Studio

Open `?page=chibi-motion` from Interactive Demos. Select Idle, Wave, Nod or Walk, drag to orbit, or pause and scrub the clip. Scrubbing pauses playback. Reduced-motion visitors start paused.

The character was generated from the owner's GJH character reference using Tripo P2. The Tripo biped rig and in-place walk are the inputs to the Blender authoring script. Idle animates the spine and head, Wave raises the left arm with a two-beat forearm gesture, and Nod uses two head dips. All four clips are embedded in one textured GLB. Walk includes vertical root compensation sampled at 60 Hz from the lower shoe. This addresses floor height only.

To rebuild from the original Tripo walk GLB, use Blender 5.1:

```sh
blender -b --python-exit-code 1 --python models/gjh-chibi-motion/author.py -- /path/to/walk.glb models/gjh-chibi-motion/visitor.glb
node models/gjh-chibi-motion/check-motion.mjs
```

The check samples 180 poses using the exported skin in Three.js. The poster shows the original generated character in its resting pose.
