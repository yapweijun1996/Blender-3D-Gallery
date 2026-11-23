# Merlion Park, Singapore

**Merlion.** The main sculpture stands 8.6 m high at the centre of its stone plinth. The model includes the open lion jaw and nozzle, swept and fluted mane, overlapping scallop scales, rolled breast fin, pierced tail curl, and blue and pale wave bands. The 2 m Merlion Cub faces back toward the plaza from a separate basin. `water_jet` is a separate mesh with its pivot at the nozzle.

**Park.** The 60 × 40 m module depicts the granite plaza, stepped seawall, benches, shade trees, lamp posts, and pile-supported viewing pier with stainless-steel rails. The real pier has an L-shaped plan. The requested semicircular stone platform and low parapet are at the statue landing. The shoreline and pier approach are shortened to fit the footprint. The Cub is about 14.5 m from the main statue in this module, compacted to fit the plaza. Small architectural and sculptural details are reconstructed from photographs.

Both GLBs use metres, Y-up and +Z toward the bay. Their base origins are at ground level. The park origin is centred on the footprint, and the sculpture origin is centred on the main plinth. To combine the modules, place the sculpture origin at `(-5, 2.336, -3)` in the park's glTF coordinates. The static jet ends near the sculpture's local ground datum in the standalone asset. Its nozzle pivot allows vertical scaling for a lower bay waterline when the assets are combined.

## Build and verification

From this directory, run Blender 5.1.2 headless with `-b -noaudio -t 2 --python-exit-code 1` and `--python build.py`. Run the same Blender command with `--python render.py` to import the GLBs and render their six orthographic views in Cycles CPU with two render threads. Run `node validate.mjs` to check the files with the repository's glTF Validator and write `models.json`. Each PNG embeds the SHA-256 of the GLB it depicts.

The author and a separate reviewer inspected all six views against the references. The export preserves the major landmarks and silhouettes. The muzzle, mane relief, wave bands, and plaza landscaping retain low-poly simplifications.

## References

- [Singapore Tourism Board landmark dimensions and history](https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/marina-bay/merlion-park/) and [National Heritage Board Cub dimensions](https://www.roots.gov.sg/Collection-Landing/listing/1181148)
- [Antara Koh construction record and deck dimensions](https://www.antarakoh.com.sg/projects-singapore-merlion-marine-bay.php), [URA waterfront design](https://www.ura.gov.sg/-/media/Corporate/Resources/Publications/Annual-Reports/PDFs/AnnualReport_2002-2003.pdf), and [aerial footage](https://www.storyblocks.com/video/stock/singapore-may-2017-aerial-view-of-tourists-visiting-the-popular-merlion-statue-iconic-landmark-in-singapore-353008809)
- [Sculpture profile photograph](https://wednesdayschildisfullofwoeblog.wordpress.com/2020/03/09/statues-statues-everywhere-singapore/) and [Red Dot Design Museum fin close-up](https://museum.red-dot.sg/pages/red-dot-marina-bay-art-and-design-guide)
