# World network test fixture

`marina-bay-2026-11-20.json.gz` is a losslessly compressed copy of the
Overpass `out geom` Marina Bay extract used by the original network tests. Its
OSM base timestamp is `2026-11-20T12:18:15Z`; its original attribution and
metadata remain inside the JSON. OpenStreetMap data is © OpenStreetMap
contributors and is available under the [ODbL](https://opendatacommons.org/licenses/odbl/).

The uncompressed JSON SHA-256 is
`297a9877428e2cf9714cf414f414f07586d383d1bd17dfec7fd2749a9bfaa998`.
The archive was produced with `gzip -n -9` so it does not contain a filename or
timestamp. The tests decompress it locally and pass it explicitly to the tile
builder; they do not download map data or read `output/osm/`.

This frozen test input is separate from the extract used to regenerate the
production map. Updating it requires reviewing the changed source data and
expected graph and feature counts, then rerunning `npm run test:world`.

## Fort Canning Link and Penang Road junction

`fort-canning-penang-junction-2026-11-23.json` records the public road
connections at OSM signal 408999681 and the first downstream fork. It
extends `fort-canning-penang-exit-2026-11-23.json` at the same coordinates.
The selected OSM elements are © OpenStreetMap contributors and available
under the [ODbL](https://opendatacommons.org/licenses/odbl/).

The request list records the official API URLs, raw response SHA-256
digests and the ordered element IDs used from each response. To recreate the
selection from those responses, retain `type`, `id`, `version`, `timestamp`,
`lat`, `lon`, `nodes`, `members` and `tags` in that order when present. Sort
tag keys and sort the elements by type and numeric ID. Relation requests
with `restrictionsOnly` retain elements with `type=restriction` in their
tags. Deduplicate by element type and ID. Each `elementsSha256` covers the
UTF-8 bytes of `JSON.stringify` on its selected array. The test checks
those digests and uses the pinned data offline.

The Penang Road through movement and both Penang Lane turns use public
way `75551640`. The fixture retains the private spur `774912613` and OSM
restriction `12351517` as evidence. The public overlay omits that spur.
At the fork, the source confirms the left branch to Clemenceau Avenue and
the through branch on Penang Road. The right-turn indications on approach
lanes 4 and 5 have no matching incident public way in this data. Lane
numbers start at zero from the left. Outgoing lane connectivity and
signal timing remain unverified.

The public overlay covers `-7_-7`, `-8_-7` and `-8_-8`. Run the offline movement, signal approach and tile seam checks.

```sh
node --test scripts/world/fort-canning-junction.test.mjs
```
