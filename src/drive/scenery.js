import { Group } from "three";
import { cloneModel, instanceModel } from "./kit.js";
import { findRoad, sample } from "./route.js";

const ROAD_HALF = 5.5;
const AHEAD = 480, BEHIND = 160, REFRESH = 30; // metres of route kept in the scene around the car
const rng = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;
const pick = (random, list) => list[Math.floor(random() * list.length)];

export function zoneAt(route, distance) {
  const bukit = findRoad(route, "Pan-Island Expressway") ?? findRoad(route, "Bukit Timah Expressway") ?? 1e9;
  const woodlands = findRoad(route, "Woodlands Crossing") ?? 1e9;
  const causeway = findRoad(route, "Causeway") ?? 1e9;
  const ciq = findRoad(route, "JB CIQ") ?? 1e9;
  const rochor = findRoad(route, "Rochor Road") ?? 1e9;
  const whitley = findRoad(route, "Whitley Road") ?? 1e9;
  if (distance < 1500) return "bay";
  if (distance >= rochor && distance < whitley) return "shophouse";
  if (distance < bukit) return "city";
  if (distance < woodlands) return "expressway";
  if (distance < causeway) return "checkpoint";
  if (distance < ciq) return "water";
  return "johor";
}

/** Distance from a point to the nearest route sample (grid, so placement checks stay cheap). */
function proximity(route) {
  const cell = 40, grid = new Map();
  for (const p of route.points) {
    const key = `${Math.floor(p.x / cell)},${Math.floor(p.z / cell)}`;
    (grid.get(key) ?? grid.set(key, []).get(key)).push(p);
  }
  return (x, z, limit) => {
    const cx = Math.floor(x / cell), cz = Math.floor(z / cell), reach = Math.ceil(limit / cell);
    let best = Infinity;
    for (let i = -reach; i <= reach; i++) for (let j = -reach; j <= reach; j++)
      for (const p of grid.get(`${cx + i},${cz + j}`) ?? []) best = Math.min(best, Math.hypot(p.x - x, p.z - z));
    return best;
  };
}

/** A set of placements sorted by route distance, drawn only inside a window around the car. */
function streamed(model, placements) {
  placements.sort((a, b) => a.s - b.s);
  let capacity = 1;
  for (let i = 0, j = 0; i < placements.length; i++) {
    while (placements[j].s < placements[i].s - (AHEAD + BEHIND)) j++;
    capacity = Math.max(capacity, i - j + 1);
  }
  const filler = Array.from({ length: capacity }, () => ({ x: 0, z: 0 }));
  const instanced = instanceModel(model, filler);
  let last = -1e9;
  return {
    meshes: instanced.meshes,
    update(s, force = false) {
      if (!force && Math.abs(s - last) < REFRESH) return;
      last = s;
      let low = 0, high = placements.length;
      while (low < high) { const middle = (low + high) >> 1; if (placements[middle].s < s - BEHIND) low = middle + 1; else high = middle; }
      let end = low;
      while (end < placements.length && placements[end].s <= s + AHEAD) end++;
      instanced.write(placements.slice(low, end));
    },
  };
}

export function buildScenery(scene, route, kit) {
  const random = rng(20261120);
  const nearest = proximity(route);
  const lists = new Map();
  const add = (name, placement) => {
    if (!kit.has(name)) return;
    (lists.get(name) ?? lists.set(name, []).get(name)).push(placement);
  };
  const radius = (name, scale) => { const size = kit.get(name)?.size; return size ? Math.max(size.x, size.z) * 0.5 * scale : 0; };
  // The model front (+Z) must look at the road: a building on the left (side +1) looks to the right of travel.
  const frontYaw = (pose, side) => Math.atan2(-side * -pose.tz, -side * pose.tx);

  const mixFor = zone => ({
    bay: [["building_tower_glass", 5], ["building_condo", 3]],
    city: [["building_hdb", 4], ["building_condo", 3], ["building_tower_glass", 3], ["building_shophouse", 1]],
    shophouse: [["building_shophouse", 8], ["building_lowrise", 2]],
    expressway: [["building_hdb", 3], ["building_condo", 2]],
    checkpoint: [["building_lowrise", 5], ["building_condo", 1]],
    johor: [["building_lowrise", 4], ["building_condo", 3], ["building_tower_glass", 2], ["building_shophouse", 1]],
    water: [],
  })[zone] ?? [];
  const weighted = list => { const total = list.reduce((s, [, w]) => s + w, 0); let r = random() * total; for (const [name, w] of list) { if ((r -= w) < 0) return name; } return list[0][0]; };
  const tints = [0xf2e9d8, 0xe6d3b3, 0xd9e3e0, 0xf0d9c8, 0xdfe6ee, 0xe9dfc6];

  for (let d = 20; d < route.length - 10; d += 30) {
    const zone = zoneAt(route, d);
    // Buildings: one per side every ~30 m, further back on expressways.
    for (const side of [-1, 1]) {
      const choices = mixFor(zone);
      if (!choices.length) continue;
      if (zone === "bay" && side < 0) continue; // keep the bay side open so Marina Bay Sands is visible from the start
      const name = weighted(choices);
      const size = kit.get(name)?.size;
      if (!size) continue;
      const scale = 0.85 + random() * 0.4;
      const base = zone === "expressway" ? 70 : zone === "bay" ? 60 : zone === "shophouse" ? 20 : 28;
      const depth = (size.z * scale) / 2;
      const offset = base + depth + random() * 20;
      const pose = sample(route, d + random() * 12, side * offset);
      if (zone === "expressway" && random() < 0.5) continue;
      if (nearest(pose.x, pose.z, 90) < radius(name, scale) + ROAD_HALF + 6) continue;
      add(name, { x: pose.x, z: pose.z, yaw: frontYaw(pose, side), scale, color: pick(random, tints), s: d });
    }
  }
  // Street trees, rain trees and palms; lamps and guardrails by road type.
  for (let d = 10; d < route.length - 10; d += 14) {
    const zone = zoneAt(route, d);
    if (zone === "water") continue;
    const built = zone === "bay" || zone === "city" || zone === "johor" || zone === "shophouse";
    for (const side of [-1, 1]) {
      const pick2 = random();
      const name = zone === "expressway" || zone === "checkpoint" ? (pick2 < 0.6 ? "tree_raintree" : "tree_palm") : (pick2 < 0.7 ? "tree_street" : pick2 < 0.9 ? "tree_palm" : "tree_raintree");
      const offset = built ? ROAD_HALF + 6.2 + random() * 1.5 : ROAD_HALF + 7 + random() * 12;
      const pose = sample(route, d + random() * 8, side * offset);
      if (nearest(pose.x, pose.z, 30) < ROAD_HALF + 4.5) continue;
      add(name, { x: pose.x, z: pose.z, yaw: random() * 6.28, scale: 0.8 + random() * 0.5, s: d });
    }
  }
  for (let d = 18; d < route.length - 10; d += 36) {
    const zone = zoneAt(route, d);
    if (zone === "water") continue;
    for (const side of [-1, 1]) {
      const pose = sample(route, d + (side > 0 ? 18 : 0), side * (ROAD_HALF + 1.3));
      // The arm of the model reaches +X, so +X must point at the road.
      add("street_lamp", { x: pose.x, z: pose.z, yaw: Math.atan2(-(-side * pose.tx), -side * -pose.tz), scale: 1, s: d });
    }
  }
  for (let d = 4; d < route.length - 4; d += 4) {
    const zone = zoneAt(route, d);
    if (zone !== "expressway" && zone !== "water" && zone !== "checkpoint") continue;
    for (const side of [-1, 1]) {
      const pose = sample(route, d, side * (ROAD_HALF + 1.0));
      add("guardrail", { x: pose.x, z: pose.z, yaw: pose.heading, scale: 1, s: d });
    }
  }
  for (let d = 1600; d < route.length - 800; d += 1700) {
    const zone = zoneAt(route, d);
    if (zone !== "expressway" && zone !== "city") continue;
    const pose = sample(route, d);
    // The gantry spans along +X; +X must lie across the road.
    add("sign_gantry", { x: pose.x, z: pose.z, yaw: Math.atan2(-pose.tx, -pose.tz) + Math.PI, scale: 1, s: d });
  }
  // Bus stops on the left pavement of built-up stretches, traffic lights near zebra crossings.
  for (let d = 700; d < route.length - 500; d += 650) {
    const zone = zoneAt(route, d);
    if (zone !== "city" && zone !== "shophouse" && zone !== "johor") continue;
    const pose = sample(route, d, ROAD_HALF + 4.2);
    add("bus_stop", { x: pose.x, z: pose.z, yaw: frontYaw(pose, 1), scale: 1, s: d });
  }
  const signals = [];
  for (let d = 150; d < route.length - 100; d += 300) {
    const zone = zoneAt(route, d);
    if (zone !== "city" && zone !== "shophouse" && zone !== "johor" && zone !== "bay") continue;
    const pose = sample(route, d + 6, -(ROAD_HALF + 1.6));
    add("traffic_light", { x: pose.x, z: pose.z, yaw: frontYaw(pose, -1), scale: 1, s: d });
    // The lit lamp sits on the pole, a little over the road, and the stop line is the zebra crossing at d.
    const lamp = sample(route, d + 5.2, -(ROAD_HALF + 0.9));
    signals.push({ s: d, x: lamp.x, z: lamp.z });
  }

  const sets = [];
  for (const [name, placements] of lists) {
    const set = streamed(kit.get(name), placements);
    for (const mesh of set.meshes) scene.add(mesh);
    sets.push(set);
  }
  return { signals, update: s => sets.forEach(set => set.update(s)), forceUpdate: s => sets.forEach(set => set.update(s, true)) };
}

/** Landmarks stay as normal objects (there is one of each). Returns the barrier pivots of the checkpoint. */
export function buildLandmarkModels(scene, route, kit, stopDistance) {
  const group = new Group();
  const barriers = [];
  const place = (name, distance, lateral, yawOffset = 0, scale = 1) => {
    const model = kit.get(name);
    if (!model) return null;
    const pose = sample(route, distance, lateral);
    const copy = cloneModel(model);
    copy.position.set(pose.x, 0, pose.z);
    copy.rotation.y = pose.heading + yawOffset;
    copy.scale.setScalar(scale);
    group.add(copy);
    return copy;
  };
  // Marina Bay Sands stands on the bay side of the start, facing the road.
  const focuses = [];
  const mbs = place("landmark_mbs", 380, -300, -Math.PI / 2, 0.7);
  if (mbs) focuses.push({ x: mbs.position.x, z: mbs.position.z, y: 40, from: 0, to: 260, rising: false, weight: 0.45 });
  // Woodlands checkpoint: shift the canopy so one of its lanes is the lane the car drives in.
  const checkpoint = place("landmark_checkpoint", stopDistance + 5, 1.77);
  checkpoint?.traverse(node => { if (/^barrier_/.test(node.name)) barriers.push(node); });
  const southkey = place("landmark_southkey", route.length - 20, 150, Math.PI / 2, 1.0);
  if (southkey) focuses.push({ x: southkey.position.x, z: southkey.position.z, y: 60, from: route.length - 700, to: route.length - 60, rising: true, weight: 0.55 });
  scene.add(group);
  return { group, barriers, hasCheckpoint: Boolean(checkpoint), focuses };
}
