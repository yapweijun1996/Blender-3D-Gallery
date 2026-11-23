# Loh Hei / Yee Sang Platter

An original Lunar New Year tabletop study inspired by the shared tossing of yee sang (yusheng) in Singapore and Malaysia. Separated piles distinguish layered carrot, cucumber, radish, pickled ginger, citrus, crisp pieces and coral fish slices; two chopstick pairs and two sauce dishes frame a painted porcelain platter. This scene is a stylized interpretation, not a recipe, an origin claim or instructions for a custom.

- `loh-hei-yee-sang-platter.blend`: editable procedural mesh groups, their authored Blender NLA tracks and studio.
- `exports/loh-hei-yee-sang-platter.glb`: self-contained glTF model with +Y up and one nonlooping `LOH_HEI_TOSS` clip, 0 to 50/24 seconds. Twenty-one ingredient groups lift, turn and settle into the platter, and two chopstick pairs lift and return. The tabletop, serving dish, sauce dishes and rests do not move. No physics engine, camera, light, texture or audio is embedded; no autoplay is required.
- `previews/studio.webp`: real Blender render of the separated opening pose; no third-party imagery or brands. Public redistribution terms are not specified, so the Gallery download control is disabled.

Brief cultural context (background only, no imported content): [Singapore National Heritage Board: Chinese New Year](https://www.roots.gov.sg/ich-landing/ich/chinese-new-year) and [Tourism Malaysia: Chinese New Year delicacies](https://www.tourism.gov.my/media/view/chinese-new-year-delicacies-yee-sang-nian-gao) describe shared festive tossing. Recipe versions and family traditions vary.

## Reproduce and check

From the repository root with Blender 5.3, WebP tools and the locked Node dependencies:

```sh
blender -b --python-exit-code 1 --python models/loh-hei-yee-sang-platter/generate.py
cwebp -quiet -resize 512 512 -q 84 models/loh-hei-yee-sang-platter/previews/studio.png -o models/loh-hei-yee-sang-platter/previews/studio.webp
node models/loh-hei-yee-sang-platter/verify.mjs
blender -b models/loh-hei-yee-sang-platter/loh-hei-yee-sang-platter.blend --python-exit-code 1 --python models/loh-hei-yee-sang-platter/verify_blender.py -- models/loh-hei-yee-sang-platter/exports/loh-hei-yee-sang-platter.glb
```

Optional `-- --mixed-review` also renders the final frame to a local PNG. The uncompressed renders and Blender backup are local derivatives, not Gallery assets. The Blender verifier checks source and reimported motion, stationary parts and sampled bounds; the Node verifier checks embedded resources, exact channel targets, range and checksums.
