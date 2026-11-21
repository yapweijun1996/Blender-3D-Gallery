// Fetch the OpenStreetMap data along the Marina Bay to Johor Bahru route in chunks (Overpass "around" the route polyline),
// then merge everything with the Marina Bay extract into output/osm/combined.json for scripts/world/build-tiles.mjs.
// Usage: node scripts/world/fetch-corridor.mjs [--chunk-km 2.5] [--radius 450] [--only 0,1,2] [--merge-only]
// The data is ODbL (OpenStreetMap contributors). Requests are spaced out to respect the public Overpass server.
import fs from "node:fs";
import { parseArgs } from "node:util";

const { values } = parseArgs({ options: { "chunk-km": { type: "string", default: "2.5" }, radius: { type: "string", default: "450" }, only: { type: "string" }, "merge-only": { type: "boolean", default: false } } });
const route = JSON.parse(fs.readFileSync(new URL("../../models/drive/route-mbs-jb.json", import.meta.url), "utf8"));
const outDir = new URL("../../output/osm/corridor/", import.meta.url);
fs.mkdirSync(outDir, { recursive: true });
const ENDPOINT = "https://overpass-api.de/api/interpreter";

// Split the route (lon, lat points) into chunks of about chunk-km, sharing their end points.
const toMetres = ([lon, lat], [lon0, lat0]) => [(lon - lon0) * 111320 * Math.cos(lat0 * Math.PI / 180), (lat - lat0) * 110574];
const chunks = [];
let current = [route.coordinates[0]], length = 0;
for (let i = 1; i < route.coordinates.length; i++) {
  const [dx, dz] = toMetres(route.coordinates[i], route.coordinates[i - 1]);
  length += Math.hypot(dx, dz);
  current.push(route.coordinates[i]);
  if (length >= Number(values["chunk-km"]) * 1000 || i === route.coordinates.length - 1) { chunks.push(current); current = [route.coordinates[i]]; length = 0; }
}

function query(points, radius) {
  const line = points.map(([lon, lat]) => `${lat.toFixed(5)},${lon.toFixed(5)}`).join(",");
  const around = `(around:${radius},${line})`;
  return `[out:json][timeout:180];(way["highway"]${around};way["building"]${around};way["natural"~"^(water|bay)$"]${around};way["leisure"~"^(park|garden)$"]${around};way["waterway"="riverbank"]${around};`
    + `node["highway"~"^(traffic_signals|crossing|bus_stop)$"]${around};node["natural"="tree"]${around};node["railway"="subway_entrance"]${around};);out geom;`;
}

const wanted = values.only ? new Set(values.only.split(",").map(Number)) : null;
if (!values["merge-only"]) {
  for (let index = 0; index < chunks.length; index++) {
    if (wanted && !wanted.has(index)) continue;
    const file = new URL(`chunk-${String(index).padStart(2, "0")}.json`, outDir);
    if (fs.existsSync(file)) { console.log(`chunk ${index}: already fetched`); continue; }
    // The public server is often busy: an HTTP error or an empty answer is retried with a growing pause.
    let done = false;
    for (let attempt = 1; attempt <= 5 && !done; attempt++) {
      const started = Date.now();
      try {
        const response = await fetch(ENDPOINT, { method: "POST", headers: { "User-Agent": "blender-gallery-open-world/0.1 (open source gallery study)", Accept: "application/json", "Content-Type": "application/x-www-form-urlencoded" }, body: `data=${encodeURIComponent(query(chunks[index], Number(values.radius)))}` });
        const text = response.ok ? await response.text() : "";
        const count = response.ok ? (JSON.parse(text).elements?.length ?? 0) : 0;
        if (count > 0) { fs.writeFileSync(file, text); console.log(`chunk ${index}/${chunks.length - 1}: ${(text.length / 1e6).toFixed(2)} MB, ${count} elements in ${((Date.now() - started) / 1000).toFixed(1)} s`); done = true; break; }
        console.error(`chunk ${index}: attempt ${attempt} ${response.ok ? "returned no elements" : `HTTP ${response.status}`}`);
      } catch (error) { console.error(`chunk ${index}: attempt ${attempt} failed: ${error.message}`); }
      await new Promise(resolve => setTimeout(resolve, 20000 * attempt));
    }
    if (!done) process.exitCode = 1;
    await new Promise(resolve => setTimeout(resolve, 12000));
  }
}

// Merge the chunks and the Marina Bay extract, one element per type and id.
const merged = new Map();
const add = elements => { for (const element of elements) merged.set(`${element.type}/${element.id}`, element); };
add(JSON.parse(fs.readFileSync(new URL("../../output/osm/marina_bay.json", import.meta.url), "utf8")).elements);
for (const name of fs.readdirSync(outDir).filter(name => name.endsWith(".json")).sort()) add(JSON.parse(fs.readFileSync(new URL(name, outDir), "utf8")).elements);
fs.writeFileSync(new URL("../../output/osm/combined.json", import.meta.url), JSON.stringify({ version: 0.6, generator: "fetch-corridor.mjs", osm3s: { copyright: "The data included in this document is from www.openstreetmap.org. The data is made available under ODbL." }, elements: [...merged.values()] }));
console.log(`${chunks.length} chunks of the route; merged ${merged.size} elements`);
