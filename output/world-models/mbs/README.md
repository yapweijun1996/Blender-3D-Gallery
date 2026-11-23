# Marina Bay Sands

Two game-ready exterior models of the original Marina Bay Sands in Singapore.

| Asset | Modeled features |
|---|---|
| `mbs_towers.glb` | Three 55-storey hotel towers, each with a near-vertical bay wing and a curved garden wing. Includes splayed atria, glazed hotel links, planted east terraces, silver spandrels and projecting glass fins. The silver SkyPark hull carries the 150 m bay-facing infinity pool, landscaped beds, rooftop venues and the north observation deck. |
| `mbs_podium.glb` | Distinct theatre, casino and southern Expo roof forms behind The Shoppes' continuous curved glass-and-steel canopy. Includes Event Plaza stair terraces, the bay promenade, the faceted northern Crystal Pavilion and footbridge, and the Bayfront Avenue porte-cochère and glazed Tower 3 entrance. |

The ArtScience Museum is a separate asset. This model covers the hotel and requested waterfront architecture.

## Scale and placement

Both GLBs are in metres, with +Y up, +Z toward Marina Bay and −X toward the north end. Each model has its own ground-plane origin at the center of its footprint bounds. With the towers at `(0, 0, 0)`, place the podium at `(17.275, 0, 118.448)` in the same coordinate system for the modeled arrangement.

The hull measures **340 × 38 m** in plan. The public deck is at **200 m** and the hull reaches **67.2 m** past the nearest edge of Tower 3 at roof height. The pool surround spans **150 m**, with about **149 m** of inset water surface. The steepest base curve is on Tower 1's garden wing at approximately **26°**.

The pool follows the bay-facing long edge and runs toward Tower 1. Published SkyPark area descriptions differ, and Safdie Architects' project page gives **2.5 acres**. This reconstruction uses the requested linear dimensions and the photographed silhouette. The podium plan, landscaping and rooftop venues are photo-based exterior approximations. Glass uses opaque PBR shading with reflected color, and the tower curtain wall uses one embedded 1024 × 1024 JPEG. The podium is texture-free.

## Rebuild and review

Run `build_mbs.py` with the supplied headless Blender 5.1.2 command and the two-thread limit, then run `node validate_mbs.cjs` from this directory. `models.json` records measured GLB byte counts, triangle counts, bounds, part names, material names, hashes and repository glTF Validator results.

Run `render_review.py` through the same Blender command with FFmpeg on PATH to generate the PNG contact sheets from the exported GLBs. Use `-- mbs_towers` or `-- mbs_podium` after either Python script name to run one asset at a time. Each contact sheet was rendered in Cycles CPU at 720 × 480 pixels per view, 12 samples with denoising, and two Blender threads. Both sheets read left to right, top to bottom.

| Top row |  |  |
|---|---|---|
| Bayfront | Aerial from the bay | North end |
| **Bottom row** | | |
| Landward | Plan | South end |

## Quality checks

Both exports passed the repository's glTF Validator with zero errors and zero warnings. The author and an independent reviewer inspected both six-view sheets against the official photographs and engineering drawings. The sheets show the three tower silhouettes and their splayed bases, the north cantilever, the bay-edge pool, the podium roof sequence, the waterfront pavilion and the north arrival canopy. Close-up differences include foliage density, rooftop venue detailing, roof seams and the pane and railing assemblies.

| Contact sheet | SHA-256 |
|---|---|
| [Tower review](mbs_towers_contact.png) | `29f29c83f837f50ed16181261535a02bcbdea54aeb7bc2ca5ef9c9546e2c1167` |
| [Podium review](mbs_podium_contact.png) | `9b97ac18888feb6d254d537c679f0ffc25fcb893aba8967c33472463fc85c136` |

## Architectural references

- [Safdie Architects' Hotel and SkyPark project](https://www.safdiearchitects.com/projects/marina-bay-sands-hotel-and-skypark)
- [Moshe Safdie's CTBUH case study](https://global.ctbuh.org/resources/papers/download/26-case-study-marina-bay-sands-singapore.pdf)
- [Arup Journal, Marina Bay Sands engineering and site plans](https://www.arup.com/globalassets/downloads/arup-journal/the-arup-journal-2012-issue-1.pdf)
- [Marina Bay Sands waterfront reference photograph](https://www.marinabaysands.com/content/dam/singapore/marinabaysands/master/main/home/2021-masthead-1920x654_2.jpg)
- [Safdie Architects' Crystal Pavilions project](https://www.safdiearchitects.com/projects/marina-bay-sands-crystal-pavilions)
- [Marina Bay Sands directions and entrances](https://www.marinabaysands.com/company-information/directions-to-marina-bay-sands.html)
