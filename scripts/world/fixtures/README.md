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
