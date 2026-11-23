# Esplanade – Theatres on the Bay

Load both GLBs at the same transform. Units are metres, the waterfront-facing front is **+Z**, and **+Y** is up. Both files use the centre of the terrace footprint at ground height as their origin. Mesh names identify the architectural parts and the materials use the game's names.

- **Domes** — Staggered, differently oriented Concert Hall and Theatre shells, with exported eave spans of 83.59 m and 84.82 m. The models use 3,378 individually folded champagne aluminium shades over triangular glazing, steel grid strips and perimeter eaves. The two grid directions and the shade angles differ between the roofs.
- **Base** — Curved two-level venue foyers with stone bands and recessed auditorium volumes, the glazed Concourse with steel ribs, and the Esplanade Drive approach with its entry canopy and shallow steps. Esplanade Mall has stepped stone bands, recessed shopfronts including the west-facing frontage, a horseshoe courtyard and a planted roof terrace. The waterfront has a stepped coping and railings, the kiosk canopy, forecourt gardens and reflecting pools, the Annexe, and the open-air theatre's fan-shaped seating and swept canopy.

This is a game-scale exterior reconstruction. The venue and annex placement follows the repository's OpenStreetMap snapshot. Roof sections, elevations, edge detailing and planting are estimated from the brief and public architectural references. Shade density is reduced to meet the triangle budget. The neighbouring Singtel Waterfront Theatre, the bridge span, and public interiors fall outside the modelled footprint.

## Rebuild and check

Run `build_esplanade.py` with the supplied Blender 5.1.2 headless command, `-t 2`, and `-- all`. The script exports the GLBs and reimports them for its Cycles CPU inspection views in `.review/`. Use `-- export` to regenerate the GLBs alone. Run `node validate_esplanade.cjs` from this folder to check the binary meshes and regenerate `models.json`. Both GLBs use texture-free PBR materials and contain mesh nodes only.

The six-view PNGs show the bay front, Esplanade Drive approach, waterfront approach, rear, mall side and plan.

## References

- [DP Architects project and roof-envelope design](https://www.dpa.com.sg/projects/esplanade-theatres-on-the-bay/)
- [Atelier Ten folded aluminium shading design](https://www.atelierten.com/projects/the-esplanade-theatres-on-the-bay/)
- [MERO roof steel and glazing system](https://mero.de/en/referenzen/arts-centre-singapore-the-esplanade/)
- [Esplanade visitor map](https://www.esplanade.com/visit/visitor-guide/getting-here-and-around)
- [Esplanade outdoor theatre and public spaces](https://www.esplanade.com/visit/venues-and-spaces)
- [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright) via the repository's `output/osm/marina_bay.json` snapshot.
