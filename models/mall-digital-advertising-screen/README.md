# Mall Digital Advertising Screen · V2.1 P0 437

Original landscape wall-mounted digital panel in metres: 1.28 × 0.755 × 0.085 m, with a 1.20 × 0.675 m (16:9) image. Static emissive artwork only. No live CMS, video, touch, network or electrical functionality.

17 named independent mesh modules include the bezel bars, screen, rear housing, service panel, mounts, fasteners and ventilation grilles. The rear wall-plane centre is the anchor, not the floor. Source front is Blender -Y, exported front is glTF +Z. Nothing is behind the Y=0 wall plane.

## Editing and reproduction

Open sources/mall-digital-advertising-screen.blend in Blender 4.0.2. The MODEL_DigitalPanel scene contains the model; select MODULE_ScreenContent. Its material node REPLACE_SCREEN_IMAGE uses the packed image REPLACEABLE_ScreenArtwork.

For artwork replacement, load a new 16:9 PNG into that node and pack it. The independent housing is unchanged. The original sources/screen-artwork.png is included. Alternatively edit text/shapes in the EDITABLE_Artwork scene, render that scene to a 1024 × 576 PNG, switch back to the model scene, reload the screen image and pack it. No external texture paths are needed to open the delivered source.

Run Blender --background --threads 2 --python-exit-code 1 --python generate.py -- --skip-render to regenerate from scratch. **This replaces hand edits.** To export an edited delivered source instead, use -- --export-source --skip-render; it reopens the source without regeneration. Run render_views.py then python3 prepare_previews.py for six PNG/WebP views. Context wall is not exported.

Run Blender inspect_sources.py, then Node validate.mjs and verify_source_edit.mjs. The edit proof changes actual screen pixels and emission, saves/reopens/re-exports a temporary fixture, and verifies all 17 meshes and transforms remain identical. Run the focused unit test, full npm test, npm run build, the strict browser script and npm run test:library.

## Existing assets reviewed

The existing mall-advertising-lightbox is a 1.16 × 2.31 × 0.58 m freestanding portrait poster with mesh campaign graphics and weighted foot. The existing mall-directory-kiosk is a freestanding portrait directory with a pedestal and map. Their actual generators and metadata were inspected. This wall-mounted landscape device with replaceable packed image is not a duplicate registration.

Original rights retained; downloads disabled. Physical Android/iOS NOT TESTED. Prepared initial-base only; final merged-base integration PENDING.
