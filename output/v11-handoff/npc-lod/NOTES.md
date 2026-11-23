# GJH Virtual Mall v11 NPC wardrobe

Seven pending wardrobe entries use the supplied neutral body and 65 Mixamo joints. The rest-pose comparisons show all three requested outfits in six matched orthographic views. The source outfit is on the left in each pair.

The input at `models/chibi-dressup/base_body.glb` measured 1,278,176 bytes with a 1024 × 1024 embedded texture and 9,512 triangles. The render and outfit budget use these original bytes with the three existing body morph targets at neutral weight. The seven NPC modules are expression-free. The manifest lists the seven new modules and their SHA-256 receipts. Its dress entry excludes the bottom slot.

[Manifest](npc-manifest.json) · [Triangle and byte tables](evidence/budget-summary.md) · [Asset audit](evidence/asset-report.json) · [Per-clip table](evidence/motion-summary.md) · [Raw checker results](evidence/motion/) · [Six views](renders/)

## Geometry and textures

- The edge-collapse pass minimizes quadric error with extra cost for skin-weight changes. It only collapses along compatible feature edges at UV seams, material borders and true mesh boundaries. Endpoint anchoring and face-orientation checks preserve the dimensional fit and chart layout. Welded component counts, edge incidence, boundary components and Euler characteristic were checked again after GLB reimport.
- The garments use a local one-ring weight blend near the shoulders, armpits, hips or knees where applicable. Weights are trimmed to four influences and renormalized. Motion-aware edge collapse checks the shoes and garments against the corrected posed body. Jeans and dress received further local clearance offsets. The hair and shoes met the fit criteria at the collapsed positions. The guarded T-shirt stayed within the source residue on every clip. A separate shoe-shell constraint keeps the inner lining behind the exterior. Reimport confirmed zero nonadjacent lining-to-shell pairs in the rest pose.
- Textured wardrobe modules use 512 × 512 images in their original material channels and UVs. Bob uses one resized JPEG. Spiky hair, jeans and T-shirt use resized JPEGs for their color, normal and packed metallic/roughness maps. The dress uses a PNG normal map and two JPEGs. The side-part uses vertex color and the sneaker pair uses solid materials. The six-view comparison was used to check texture recognizability, seam appearance, and silhouette at the supplied resolution.

## Render comparisons

- [Front](renders/01-front.png)
- [Front three-quarter](renders/02-front-three-quarter.png)
- [Right](renders/03-right.png)
- [Rear three-quarter](renders/04-rear-three-quarter.png)
- [Rear](renders/05-rear.png)
- [Left](renders/06-left.png)

## Motion verification

The verification wrapper executes the supplied seven-clip dense and triangle checkers and the two added-action checkers. It removes their Workbench preview sections while retaining the measurements and original frame loops. The legacy dense checker visits each integer frame and the legacy triangle checker samples a stride of three. The added-action checkers visit every integer frame of all eleven clips. The summary reports the maximum count from either checker family and the full-precision minimum signed distance from the all-integer run. Each raw report records the input, checker and candidate GLB hashes. The render files come from Cycles CPU. The render receipt pins all six images to their exported GLB inputs. [Render receipt](renders/render-receipt.json)

T-shirt acceptance uses the tighter of 21 vertices and the matching full-detail clip count, full-detail triangle-overlap peaks by clip, and a maximum penetration of 1.4 mm. Dress acceptance requires at least 0.5 mm of signed clearance. The shoe and hair checks use the same master body as the garment checks. Measurements cover module-to-body contact at the sampled frames.

## Reproduce

Run from this directory using the existing Node installation, local `gltf-validator` package, Blender 5.1.2 and guard library. The default paths match the supplied location. Override `NPC_LEGACY_CHECKERS`, `NPC_BLENDER` and `NPC_GUARD` if those files have moved. `NPC_JOBS` and `NPC_THREADS` control checker concurrency and per-process Blender threads. Intermediates are written to `.work/`.

```sh
node run.mjs build
node run.mjs guard bottom-jeans top-dress top-tshirt shoes-sneakers
node run.mjs fit bottom-jeans top-dress
node pack_npc.mjs decimated hair-bob hair-spiky hair-sidepart
node pack_npc.mjs guarded shoes-sneakers top-tshirt
node pack_npc.mjs fitted bottom-jeans top-dress
node run.mjs baseline
node run.mjs check
node run.mjs audit
node verify_npc.mjs
NPC_THREADS=5 node run.mjs render
```

Khronos validation and all structural and motion acceptance checks run against the final packed GLBs. The handoff manifest remains `pending` for integration review.
