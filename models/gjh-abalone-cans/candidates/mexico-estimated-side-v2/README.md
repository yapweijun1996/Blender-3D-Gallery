# Mexico abalone — estimated-side candidate V2

This is an **unofficial candidate**, not verified or brand-approved packaging. The original 454 g model uses official front and back packshots, but approximately 121° of the wrap lacks side photography. V2 blends colors at the edge of that unknown sector and adds a high-contrast **ESTIMATED / SIDE / DEMO ONLY** label. The decoration and label are not product artwork. A minor transition remains visible; exact panel spacing is unverified.

- [V2 GLB](mexico-454g-estimated-side-v2.glb): 276,376 bytes; SHA-256 `4dd5e6ca4d7f91d83460fe11d6c87a79240b34b97ef63b4bcc31ebd046bd7846`.
- [Original LOD1](../../exports/lod1/gjh-can-mexico-abalone-lod1.glb): SHA-256 `52f8952ca698cc77c6aaf8f1ef5c607a31c401817e6bf6741426e17510164acb`.
- [Previous V1 candidate and comparison](../mexico-estimated-side/).
- All non-image geometry buffers and decoded known label pixels were checked unchanged; texture is 640 × 312 PNG, embedded in GLB.
- Temporary Mini Street browser preview used response interception for the model and digest. Chromium mobile portrait, landscape and desktop, and WebKit portrait passed loading without photo fallback, rotation, reset, add to basket and reload persistence. Automated camera placement; physical-device and product-packaging accuracy are unverified.
- This candidate is not registered in the Gallery catalog and does not replace the original or the V1 candidate.
- Original source image provenance, third-party artwork and redistribution limits are described in the [collection README](../../README.md) and [Mexico metadata](../../metadata/gjh-can-mexico-abalone.json).

## Reproduce

On macOS with Python 3, Pillow and the system Arial Bold font:

```sh
python3 rebuild-estimated-side-v2.py ../../exports/lod1/gjh-can-mexico-abalone-lod1.glb /tmp/mexico-454g-estimated-side-v2.glb
shasum -a 256 /tmp/mexico-454g-estimated-side-v2.glb
```

Byte-for-byte reproduction was confirmed on the author's macOS environment. Pillow, font and platform differences can change output bytes.
