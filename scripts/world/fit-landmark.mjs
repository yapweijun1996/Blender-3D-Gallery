// Fits a landmark GLB onto its OSM footprint: finds the yaw and offset that put most ground-level model vertices inside the mapped outlines.
// Usage: node scripts/world/fit-landmark.mjs <model.glb> <name-regex> [maxY=4]   (prints { x, z, yaw } for models/world landmarks)
import fs from "node:fs";
import { Matrix4, Quaternion, Vector3 } from "three";

const [glbPath, pattern, maxYArgument] = process.argv.slice(2);
const maxY = Number(maxYArgument ?? 4);
const matcher = new RegExp(pattern, "i");
const tilesDir = new URL("../../models/world/tiles/", import.meta.url);

function modelPoints(path) {
  const buffer = fs.readFileSync(path);
  const jsonLength = buffer.readUInt32LE(12);
  const json = JSON.parse(buffer.subarray(20, 20 + jsonLength).toString());
  const binStart = 20 + jsonLength + 8;
  const bin = buffer.subarray(binStart);
  const points = [];
  const walk = (index, parent) => {
    const node = json.nodes[index];
    const local = new Matrix4();
    if (node.matrix) local.fromArray(node.matrix);
    else local.compose(new Vector3(...(node.translation ?? [0, 0, 0])), new Quaternion(...(node.rotation ?? [0, 0, 0, 1])), new Vector3(...(node.scale ?? [1, 1, 1])));
    const world = parent.clone().multiply(local);
    if (node.mesh !== undefined) {
      for (const primitive of json.meshes[node.mesh].primitives) {
        const accessor = json.accessors[primitive.attributes.POSITION], view = json.bufferViews[accessor.bufferView];
        const stride = view.byteStride ?? 12, base = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0), vector = new Vector3();
        for (let i = 0; i < accessor.count; i++) {
          const at = base + i * stride;
          vector.set(bin.readFloatLE(at), bin.readFloatLE(at + 4), bin.readFloatLE(at + 8)).applyMatrix4(world);
          points.push([vector.x, vector.y, vector.z]);
        }
      }
    }
    for (const child of node.children ?? []) walk(child, world);
  };
  for (const root of json.scenes[json.scene ?? 0].nodes) walk(root, new Matrix4());
  return points;
}

const polygons = [];
for (const file of fs.readdirSync(tilesDir).filter(name => name !== "index.json")) {
  const tile = JSON.parse(fs.readFileSync(new URL(file, tilesDir)));
  for (const building of tile.buildings) if (matcher.test(building.name ?? "")) polygons.push(building.geometry.map(([x, z]) => [x + tile.x * 250, z + tile.z * 250]));
}
if (!polygons.length) { console.error("no OSM outlines match"); process.exit(1); }
const inside = (x, z, ring) => {
  let result = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    if ((ring[i][1] > z) !== (ring[j][1] > z) && x < (ring[j][0] - ring[i][0]) * (z - ring[i][1]) / (ring[j][1] - ring[i][1]) + ring[i][0]) result = !result;
  }
  return result;
};
const flat = polygons.flat();
const target = [flat.reduce((s, p) => s + p[0], 0) / flat.length, flat.reduce((s, p) => s + p[1], 0) / flat.length];
const ground = modelPoints(glbPath).filter(p => p[1] <= maxY);
const centre = [ground.reduce((s, p) => s + p[0], 0) / ground.length, ground.reduce((s, p) => s + p[2], 0) / ground.length];
let best = { score: -1 };
for (let yawDegrees = 0; yawDegrees < 360; yawDegrees += 2) {
  const yaw = yawDegrees * Math.PI / 180, c = Math.cos(yaw), s = Math.sin(yaw);
  for (let dx = -40; dx <= 40; dx += 8) for (let dz = -40; dz <= 40; dz += 8) {
    let hits = 0;
    for (const p of ground) {
      const lx = p[0] - centre[0], lz = p[2] - centre[1];
      // Rotation about Y by yaw: x' = x cos + z sin, z' = -x sin + z cos.
      const x = target[0] + dx + lx * c + lz * s, z = target[1] + dz - lx * s + lz * c;
      if (polygons.some(ring => inside(x, z, ring))) hits++;
    }
    const score = hits / ground.length;
    if (score > best.score) best = { score, yaw, dx, dz };
  }
}
const { yaw, dx, dz } = best, c = Math.cos(yaw), s = Math.sin(yaw);
// Model origin lands at target + offset minus the rotated model centre.
const x = target[0] + dx - (centre[0] * c + centre[1] * s), z = target[1] + dz - (-centre[0] * s + centre[1] * c);
console.log(JSON.stringify({ x: +x.toFixed(1), z: +z.toFixed(1), yaw: +yaw.toFixed(3), overlap: +best.score.toFixed(2), outlines: polygons.length, groundVertices: ground.length }));
