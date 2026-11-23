import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { gunzipSync } from "node:zlib";

import { cross } from "../../src/world/network/geometry.js";
import { createTunnelGeometry } from "../../src/world/tunnel-prototype/geometry.js";
import { createFortCanningMergeAlignment } from "../../src/world/tunnel-integration/merge-alignment.js";
import { corridorBounds, scanCorridorCrossings } from "./fort-canning-crossings.mjs";
import profile from "./fort-canning-integration.json" with { type: "json" };

const alignment = createFortCanningMergeAlignment(profile);
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-7, `${a} ≠ ${b}`);
const atOffset = ({ x, z, rx, rz }, offset) => [x + rx * offset, z + rz * offset];
const { elements } = JSON.parse(gunzipSync(readFileSync(new URL("./fixtures/marina-bay-2026-11-20.json.gz", import.meta.url))));
const ways = new Map(elements.filter(({ type }) => type === "way").map(way => [way.id, way]));
const routeIds = new Set([...profile.simulation.chain.map(({ edgeId }) => edgeId), "654224115:0"]);

function tilesUnder(path, width) {
  const [minX, maxX, minZ, maxZ] = corridorBounds(path, width).map(metres => Math.floor(metres / profile.tileSize));
  const tiles = [];
  for (let x = minX; x <= maxX; x++) {
    for (let z = minZ; z <= maxZ; z++) {
      tiles.push(JSON.parse(readFileSync(new URL(`../../models/world/tiles/${x}_${z}.json`, import.meta.url), "utf8")));
    }
  }
  return tiles;
}

function roadTriangles(sections, width) {
  const row = sections.map(sample => [atOffset(sample, -width / 2).map(Math.fround), atOffset(sample, width / 2).map(Math.fround)]);
  return row.slice(1).flatMap(([left, right], index) => {
    const [beforeLeft, beforeRight] = row[index];
    return [[beforeLeft, beforeRight, left], [beforeRight, right, left]];
  });
}

function includesPoint(triangle, point) {
  const sign = Math.sign(cross(...triangle));
  return sign !== 0 && triangle.every((a, index) => sign * cross(a, triangle[(index + 1) % 3], point) >= 0);
}

function interiorIntersects(a, b) {
  const epsilon = 1e-7;
  for (const polygon of [a, b]) {
    for (const [index, [x, z]] of polygon.entries()) {
      const [nx, nz] = polygon[(index + 1) % polygon.length];
      const span = Math.hypot(nx - x, nz - z);
      const project = ([px, pz]) => ((nz - z) * (px - x) - (nx - x) * (pz - z)) / span;
      const first = a.map(project), second = b.map(project);
      if (Math.max(...first) - Math.min(...second) <= epsilon || Math.max(...second) - Math.min(...first) <= epsilon) return false;
    }
  }
  return true;
}

test("3+2 approaches share all five real lane centers and one divider at the level merge", () => {
  const { link, penang, downstream, widths, seam } = alignment;
  assert.deepEqual(widths, { link: 10.2, penang: 6.8, downstream: 17 });
  const a = link.at(-1), b = penang.at(-1), c = downstream[0];
  for (const sample of [a, b, c]) {
    assert.equal(sample.y, 0);
    assert.equal(sample.tx, seam.tx);
    assert.equal(sample.tz, seam.tz);
    near(Math.hypot(sample.tx, sample.tz), 1);
  }
  const compare = (x, y) => x.forEach((value, index) => near(value, y[index]));
  const divider = [seam.divider.x, seam.divider.z];
  compare(atOffset(a, widths.link / 2), divider);
  compare(atOffset(b, -widths.penang / 2), divider);
  assert.deepEqual(atOffset(a, widths.link / 2).map(Math.fround), atOffset(b, -widths.penang / 2).map(Math.fround));
  compare(atOffset(a, -widths.link / 2), atOffset(c, -widths.downstream / 2));
  compare(atOffset(b, widths.penang / 2), atOffset(c, widths.downstream / 2));
  for (const [index, [sample, offset]] of [[a, -3.4], [a, 0], [a, 3.4], [b, -1.7], [b, 1.7]].entries()) {
    compare(atOffset(sample, offset), atOffset(c, (index - 2) * profile.laneWidth));
  }
});

test("full-width mitered ribbons keep the two feeds disjoint until their shared seam", () => {
  const names = ["link", "penang", "downstream"];
  const roads = names.map(name => roadTriangles(alignment[name], alignment.widths[name]));
  for (let i = 0; i < roads.length; i++) {
    for (let j = i + 1; j < roads.length; j++) {
      assert.ok(!roads[i].some(a => roads[j].some(b => interiorIntersects(a, b))), `${names[i]} overlaps ${names[j]}`);
    }
  }
});

test("the centered footway and Fort Canning Road stay over the actual roof and the side footway clears the cut", () => {
  const { sections, coveredFrom, coveredTo } = createTunnelGeometry(alignment.profile);
  assert.equal(coveredFrom, alignment.profile.simulation.roof.start);
  assert.equal(coveredTo, alignment.profile.simulation.roof.end);
  const width = profile.width;
  const overlaps = scanCorridorCrossings({ path: sections, tiles: tilesUnder(sections, width), ways, width, routeIds,
    length: profile.length, roof: { start: coveredFrom, end: coveredTo } });
  for (const id of ["646730739:0", "774912614:0"]) {
    const crossing = overlaps.find(({ edgeId }) => edgeId === id);
    assert.equal(crossing?.roofCovered, true, id);
    assert.deepEqual(crossing.openCut, []);
  }
  assert.ok(!overlaps.some(({ edgeId }) => edgeId === "1552288080:0"));
  assert.deepEqual(overlaps.filter(({ openCut }) => openCut.length).map(({ edgeId }) => edgeId), ["719635727"]);
  for (const road of [alignment.penang, alignment.downstream]) {
    const width = road === alignment.penang ? alignment.widths.penang : alignment.widths.downstream;
    const tiles = tilesUnder(road, width);
    const atGrade = scanCorridorCrossings({ path: road, tiles, ways, width, routeIds, length: road.at(-1).s,
      roof: { start: 0, end: 0 } });
    const conflicting = atGrade.filter(({ edgeId, kind, end }) => kind !== "park" && !(edgeId === "21940400:5" && end < .15));
    assert.deepEqual(conflicting, [], "only existing park fill and the incoming seam may share grade");
    const triangles = roadTriangles(road, width);
    for (const tile of tiles) {
      for (const { point } of tile.trees) {
        const world = [point[0] + tile.x * profile.tileSize, point[1] + tile.z * profile.tileSize];
        assert.ok(!triangles.some(triangle => includesPoint(triangle, world)),
          `mapped tree remains outside road at ${world}`);
      }
    }
  }
});

test("all original Link tile seams remain at their mapped positions and the exit grade follows actual plan distance", () => {
  assert.deepEqual(alignment.profile.fragments.map(fragment => fragment.tile), profile.fragments.map(fragment => fragment.tile));
  for (const fragment of alignment.profile.fragments.slice(1)) {
    assert.ok([fragment.points[0].x, fragment.points[0].z].some(value => value % profile.tileSize === 0));
  }
  for (let index = 1; index < alignment.link.length; index++) {
    const a = alignment.link[index - 1], b = alignment.link[index];
    const run = Math.hypot(a.x - b.x, a.z - b.z);
    assert.ok(run > 0 && b.s > a.s);
    assert.ok(Math.abs(a.y - b.y) / run < profile.maxGrade + 1e-6);
  }
});
