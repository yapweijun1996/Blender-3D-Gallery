# Game security and reliability review

Review scope: this repository's local Game, catalog, current assets and build path. This is not a penetration test or a certification of future third-party models.

## Asset and content boundaries

- Game model identities come from the build-time catalog. The catalog validates IDs and requires model and thumbnail paths under `models/` without `..`. The site does not execute Blender scripts or code from model metadata.
- The 39 current catalog GLBs were inspected: none declares a core `images[].uri` or `buffers[].uri`. The 18 Game GLBs contain no image or texture entries. Each current GLB passed the existing Khronos validation gate with zero errors and warnings.
- `scripts/catalog.mjs` now rejects non-`data:` core image and buffer URIs while loading the catalog, including in development. Unit fixtures exercise absolute, protocol-relative, relative, file and blob references, malformed types and embedded/data resources. This guard addresses those two core fields; it does not claim to validate every glTF extension or impose a complete resource-size limit.
- Catalog loading accepts self-contained `data:` URIs, but the existing glTF Validator reports `DATA_URI_GLB` warnings and the build rejects warnings. The change does not weaken that existing production-build policy.
- Game's HTML template is static; changing status and saved-state text is assigned as text, not evaluated as HTML. Initial model and WebGL failures have a recovery path; failed or corrupt assets must not enable play.
- Original billiards assets retain their source and generator. Their README states that redistribution terms have not been selected. The owner must settle any required licensing before a release or redistribution decision; this task does not change or publish the models.

## Storage and dependencies

The browser stores validated stable match checkpoints locally in IndexedDB and coordinates ownership with Web Locks or a lease fallback. There is no account, backend or intended frontend secret. Storage failure is surfaced to the player and does not silently promise a save.

`npm ci` reported zero known vulnerabilities in the installed dependency tree during this local audit. That result is time-specific and is not a full source, supply-chain or third-party license audit. No dependency was added for these changes.

## Remaining limits

The review did not establish an explicit CSP, exhaustive protection for extension-defined resource references, limits for every future asset, real-device storage eviction behavior, or a complete accessibility/security certification. Do not accept new third-party assets without validating provenance, rights, resource references and size. Release and deployment remain outside this task's authorization.
