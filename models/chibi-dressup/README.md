# Modular Chibi Dress-Up

The gallery route is `?page=chibi-dressup`. It fetches the body, wardrobe, and clips when opened. The wardrobe manifest reserves hair, top, bottom, shoes, and hat slots. A selected module can be removed with the same control. The browser stores the wardrobe, body clip, and each hand gesture independently. Reduced-motion mode starts with playback paused.

- `base_body.glb` and `hand_gestures.glb` are byte-for-byte copies from `output/modular-chibi-parts/hand-gestures-astra/`. The repaired 65-joint rig is the target skeleton.
- `motion-clips.glb` comes from `models/tripo-chibi-motion/motion.glb`. Regenerate it with `node models/chibi-dressup/extract-motion.mjs`. It preserves the armature channels and omits the display mesh and textures. The runtime transfers rest-relative rotations and uses only vertical root travel, so Walk stays in frame.
- The manifest records each module's source relative to `output/modular-chibi-parts/`, size and SHA-256. Run `node scripts/sync-chibi-dressup-modules.mjs` to refresh the four listed modules. The script resets a new or changed binary to `pending` and retains a verified status for unchanged bytes. The status records fit review. Both supplied tops have documented garment/body intersections during motion.
- To add items, place their self-contained skinned GLBs in `modules/` and update the manifest. Their skin must contain the same unique joint names as the body. The runtime remaps vertex joint indices by name and uses the body skeleton for deformation.

Run the browser smoke test after building with `node scripts/test-chibi-dressup-browser.mjs`. Set `CHIBI_DRESSUP_OFFLINE=1` in an environment that blocks loopback listeners or Chromium child processes. Playwright then serves the build files from disk through request interception and uses software WebGL.
