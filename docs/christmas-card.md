# Christmas card

`christmas-card/` is an independent Vite entry. Edit the recipient, message lines and sender for both languages in `src/christmas-card/config.js`. The model can be rebuilt using the instructions in `models/christmas-envelope/README.md`. No new dependencies or external resources are used.

The card has a service worker scoped to its own path. Its build-time cache contains its HTML, manifest, icons and the Vite dependency closure including the GLB; upgrade installation waits until the visitor chooses Update now, even when old tabs close. A browser may terminate a long-pending installation; check for updates again if that happens. The gallery worker excludes card navigations and card clients from its update coordination, while its existing gallery scope and caches remain separate. A previously installed older gallery worker may still route the first card navigation to the gallery until that gallery worker is updated through the gallery's own update flow. Offline support requires one successful online card visit and completed worker installation.

The deployment selector discovers the GLB through the literal model import. Its cache key is calculated from committed Git-index entries; untracked changes cannot be verified as deployment inputs until added to the index. Publication remains a separate authorized action.

The orthographic camera fits the exported model’s animated bounds on every frame. The seal breaks first; after the flap opens a star and snow burst appears at the mouth, followed by the rising letter. The HTML greeting takes over the letter face as it approaches the viewer, with the envelope behind it. Metallic trim uses a locally generated Three.js room environment, with no external texture.
