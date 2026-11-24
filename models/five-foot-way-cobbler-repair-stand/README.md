# Five-Foot-Way Cobbler Repair Stand

An original static exhibit inspired by Singapore's five-foot-way cobblers. The iron shoe-shaped last sits on a separately modeled foot, stem and physically bored saddle. The loose sole has 24 raised mesh tread blocks and a recessed field. The small parked mallet is context, not part of a working simulation. The arrangement and proportions are original, not a named artifact or repair guide. Blender +Z is up; Gallery +Y is up and +Z is front.

## Heritage context

- [National Heritage Board, Heritage Along Footpaths](https://www.roots.gov.sg/-/media/Roots/Images/resources/e-books/nhb_ebook_heritage_along_footpaths.pdf): Singapore five-foot-way trades.
- [National Library Board, Time-forgotten Trades](https://biblioasia.nlb.gov.sg/all-sections/vol-9-issue-4-jan-march-2014-forgotten-trades-singapore/): Singapore street cobblers and shoe lasts.
- [City of Kingston Civic Artifact Collection, shoe last](https://www.kingstonciviccollection.ca/explore-collection/browse/87-0601-45): general metal shoe-form reference only, not a Singapore attribution or replica.

## Reproduce and check

Run from this directory with Blender 4.3.2:

```sh
blender -b --python-exit-code 4 --python generate.py -- --output ./generated
blender -b --python-exit-code 4 --python verify_blender.py -- ./generated
node verify.mjs ./generated/exports/five-foot-way-cobbler-repair-stand.glb
```

Use `--skip-render` if only the editable blend and static GLB are needed. The model uses original baked vertex colour, without external imagery or animation.
