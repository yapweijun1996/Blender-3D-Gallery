import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from "three";
import { DECK_THICKNESS } from "../src/world/bridges.js";
import { createPhysicsWorld } from "../src/world/physics/world.js";
import { buildTile } from "../src/world/tile-mesh.js";
import { buildTrafficGraph, createTraffic, heightOnEdge, sampleEdge } from "../src/world/traffic.js";

const ROAD_Y = 0.03;
const down = new Vector3(0, -1, 0), up = new Vector3(0, 1, 0);

function near(a, b, tolerance, label) {
  assert.ok(Number.isFinite(a) && Math.abs(a - b) <= tolerance, `${label}: ${a} vs ${b}`);
}

function intersectionDistance([a, b], [c, d]) {
  const dx = b[0] - a[0], dz = b[1] - a[1];
  const ex = d[0] - c[0], ez = d[1] - c[1];
  const determinant = dx * ez - dz * ex;
  const x = c[0] - a[0], z = c[1] - a[1];
  const t = (x * ez - z * ex) / determinant, u = (x * dz - z * dx) / determinant;
  assert.ok(t > 0 && t < 1 && u > 0 && u < 1, "the mapped centrelines cross within both roads");
  return t * Math.hypot(dx, dz);
}

async function install(t, tile) {
  const built = buildTile(tile);
  assert.equal(built.bridgeSolids.length, 1);
  const material = new MeshBasicMaterial({ side: DoubleSide });
  const mesh = new Mesh(built.ground, material);
  const physics = await createPhysicsWorld();
  physics.addStaticTrimesh(built.bridgeSolids[0]);
  physics.step(1 / 60);
  t.after(() => { physics.dispose(); material.dispose(); mesh.geometry.dispose(); });
  function visible(x, z, direction) {
    const start = new Vector3(x, -20 * direction.y, z);
    return new Raycaster(start, direction, 0, 40).intersectObject(mesh)[0]?.point.y;
  }
  return {
    solid: built.bridgeSolids[0],
    positions: built.ground.attributes.position.array,
    underside: (x, z) => visible(x, z, up),
    checkTop(x, z, trafficY) {
      const asphalt = visible(x, z, down);
      const collision = physics.supportHeight({ x, y: 20, z });
      near(asphalt, trafficY + ROAD_Y, 0.02, "visible asphalt vs traffic");
      near(collision, asphalt, 0.0002, "Rapier vs visible asphalt");
      return asphalt;
    },
  };
}

test("both mapped Kheam Hock crossings and all four PIE lanes follow the simulated bridge profile", async t => {
  const source = JSON.parse(fs.readFileSync("models/world/tiles/-19_-21.json", "utf8"));
  const lower = source.roads.find(road => road.id === "659688751:0");
  const graph = buildTrafficGraph([source]);
  const traffic = createTraffic({ graph });
  assert.equal(graph.edges.has(lower.id), false, "the lower tunnel remains closed to traffic");
  for (const id of ["159090940:0", "627656467:0"]) {
    const road = source.roads.find(item => item.id === id);
    assert.equal(road.geometry.length, 2);
    assert.equal(road.lanes, 4);
    const tile = { x: source.x, z: source.z, roads: [road] };
    const surface = await install(t, tile);
    const edge = graph.edges.get(id);
    const s = intersectionDistance(road.geometry, lower.geometry);
    const { x, z } = sampleEdge(edge, s);
    const crossingTop = surface.checkTop(x, z, heightOnEdge(edge, s));
    near(surface.underside(x, z), crossingTop - ROAD_Y - DECK_THICKNESS, 0.0002, "visible underside");
    for (let station = 0.1; station < edge.length; station += 0.2) {
      for (let lane = 0; lane < road.lanes; lane++) {
        const pose = traffic.pose({ edge: id, direction: 1, lane, s: station });
        surface.checkTop(pose.x, pose.z, pose.y);
      }
    }
    const masked = buildTile(tile, { paint: { roads: [id] } });
    const visual = buildTile({ ...tile, roads: [] }, { visualOnly: { roads: [road] } });
    assert.equal(masked.ground, null);
    assert.deepEqual(masked.bridgeSolids, [surface.solid]);
    assert.equal(visual.bridgeSolids.length, 0);
    assert.deepEqual(visual.ground.attributes.position.array, surface.positions);
    visual.ground.dispose();
  }
});

test("a sloping asymmetric bend keeps the original strip borders and traffic height through the corner", async t => {
  const road = {
    id: "bend", from: 1, to: 2, oneway: true, lanes: 2, bridge: true, layer: 1, width: 10,
    edgeStart: 10, edgeLength: 180, geometry: [[5, 8], [28, 8], [32, 29], [53, 41]],
  };
  const tile = { x: 0, z: 0, roads: [road] };
  const graph = buildTrafficGraph([tile]);
  const edge = graph.edges.get(road.id);
  const surface = await install(t, tile);
  for (let s = 0.05; s < edge.length - 0.05; s += 0.1) {
    const { x, z } = sampleEdge(edge, s);
    surface.checkTop(x, z, heightOnEdge(edge, s));
  }
  // The tangent of the first bend is measured from its two original neighbours (5,8) and (32,29).
  const length = Math.hypot(27, 21), nx = -21 / length, nz = 27 / length;
  for (const sign of [-1, 1]) {
    for (const inset of [-0.02, 0.02]) {
      const radius = (road.width / 2 + inset) * sign;
      const underside = surface.underside(28 + nx * radius, 8 + nz * radius);
      assert.equal(Number.isFinite(underside), inset < 0, "the original parapet line bounds the road");
    }
  }
});

test("Rapier resolves the mapped centreline of 39961203:0 on a twisting panel", async t => {
  const source = JSON.parse(fs.readFileSync("models/world/tiles/0_-3.json", "utf8"));
  const road = source.roads.find(item => item.id === "39961203:0");
  const tile = { x: source.x, z: source.z, roads: [road] };
  const edge = buildTrafficGraph([tile]).edges.get(road.id);
  const [a, b] = edge.points;
  const s = Math.hypot(b[0] - a[0], b[1] - a[1]) / 4;
  const { x, z } = sampleEdge(edge, s);
  const surface = await install(t, tile);
  surface.checkTop(x, z, heightOnEdge(edge, s));
});

test("tile join and original pier stations survive ramp refinement; a level deck gains no panels", async t => {
  const road = {
    id: "join", from: 1, to: 2, oneway: true, bridge: true, layer: 1, width: 8, edgeLength: 500,
  };
  const before = { x: 0, z: 0, roads: [{ ...road, edgeStart: 12, geometry: [[235, 80], [250, 80]] }] };
  const after = { x: 1, z: 0, roads: [{ ...road, edgeStart: 27, geometry: [[0, 80], [21, 80]] }] };
  const edge = buildTrafficGraph([before, after]).edges.get(road.id);
  const tiles = await Promise.all([install(t, before), install(t, after)]);
  function joinVertices(solid) {
    const positions = [];
    for (let i = 0; i < solid.vertices.length; i += 3) {
      if (solid.vertices[i] === 250) positions.push(solid.vertices.slice(i, i + 3).join(","));
    }
    return [...new Set(positions)].sort();
  }
  const join = joinVertices(tiles[0].solid);
  assert.equal(join.length, 4, "two edges of the asphalt and two parapet tops");
  assert.deepEqual(joinVertices(tiles[1].solid), join);
  for (const [i, offset] of [[0, -0.05], [1, 0.05]]) {
    tiles[i].checkTop(250 + offset, 80, heightOnEdge(edge, 15 + offset));
  }
  const flat = buildTile({ x: 0, z: 0, roads: [{ ...road, edgeStart: 200, geometry: [[0, 0], [50, 0], [50, 50]] }] });
  assert.equal(flat.bridgeSolids[0].indices.length / 3, 12, "two original flat top/parapet panels");
  assert.equal(flat.ground.attributes.position.count / 3, 40, "two original sections and two four-sided piers");
  const baseCorners = new Set();
  const positions = flat.ground.attributes.position;
  for (let i = 0; i < positions.count; i++) {
    if (positions.getY(i) === 0) baseCorners.add([positions.getX(i).toFixed(1), positions.getZ(i).toFixed(1)].join(","));
  }
  const expectedCorners = new Set();
  for (const z of [0, 50]) {
    for (const dx of [-0.9, 0.9]) for (const dz of [-0.9, 0.9]) expectedCorners.add([(50 + dx).toFixed(1), (z + dz).toFixed(1)].join(","));
  }
  assert.deepEqual(baseCorners, expectedCorners);
  flat.ground.dispose();
});

test("a rounded source endpoint on Dunearn Road retains nondegenerate Float32 faces", t => {
  const source = JSON.parse(fs.readFileSync("models/world/tiles/-12_-16.json", "utf8"));
  const road = source.roads.find(item => item.id === "914919686:0");
  const { ground } = buildTile({ x: source.x, z: source.z, roads: [road] });
  t.after(() => ground.dispose());
  const normals = ground.getAttribute("normal");
  for (let i = 0; i < normals.count; i += 3) {
    assert.ok(Math.hypot(normals.getX(i), normals.getY(i), normals.getZ(i)) > 0.99,
      "a station nearly coincident with a mapped vertex must not collapse the rendered triangle");
  }
});
