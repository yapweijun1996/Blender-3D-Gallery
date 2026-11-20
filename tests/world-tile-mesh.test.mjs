import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { buildTile } from "../src/world/tile-mesh.js";

test("every map tile builds into finite geometry (crossings, buildings, roads)", () => {
  let crossings = 0, towers = 0;
  for (const file of fs.readdirSync("models/world/tiles").filter(name => name !== "index.json")) {
    const tile = JSON.parse(fs.readFileSync(`models/world/tiles/${file}`, "utf8"));
    const built = buildTile(tile);
    crossings += tile.crossings.length;
    if (built.towers) towers++;
    for (const geometry of [built.ground, built.buildings, built.towers]) {
      if (!geometry) continue;
      const position = geometry.attributes.position.array;
      assert.ok(position.length % 9 === 0, `${file}: whole triangles`);
      assert.ok(position.every(Number.isFinite), `${file}: finite positions`);
      if (geometry === built.buildings || geometry === built.towers) {
        const uv = geometry.attributes.uv;
        assert.ok(uv && uv.count === geometry.attributes.position.count && uv.array.every(Number.isFinite), `${file}: one finite UV per building vertex`);
      }
    }
  }
  assert.ok(crossings > 100);
  assert.ok(towers > 5, `${towers} tiles have towers`);
});
