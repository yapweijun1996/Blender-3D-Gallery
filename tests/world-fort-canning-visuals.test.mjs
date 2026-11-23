import assert from "node:assert/strict";
import test from "node:test";

import { Group, Matrix4, MeshLambertMaterial, Raycaster, Vector3 } from "three";
import profile from "../scripts/world/fort-canning-integration.json" with { type: "json" };
import { createFortCanningMergeGeometry } from "../src/world/tunnel-integration/merge-geometry.js";
import { createFortCanningVisuals } from "../src/world/tunnel-integration/visuals.js";

const geometry = createFortCanningMergeGeometry(profile);
const down = new Vector3(0, -1, 0);
const near = (value, expected, margin = .001) => assert.ok(Math.abs(value - expected) <= margin, value + " vs " + expected);
const hitGround = (group, x, z) => new Raycaster(new Vector3(x, 10, z), down).intersectObject(group)[0];

test("the exterior meets the apron while the open cut has visible below-grade asphalt", t => {
  const material = new MeshLambertMaterial();
  const visuals = createFortCanningVisuals(geometry, material);
  t.after(() => { visuals.dispose(); material.dispose(); });
  visuals.group.updateMatrixWorld(true);

  const { minX, maxX, minZ, maxZ } = geometry.bounds;
  const x = (minX + maxX) / 2, z = (minZ + maxZ) / 2;
  const exterior = visuals.group.getObjectByName("exterior-ground");
  const apron = visuals.group.getObjectByName("apron-and-cover");
  assert.equal(exterior.material, material);
  assert.equal(apron.material, material);
  for (const [px, pz] of [[minX - 1, z], [maxX + 1, z], [x, minZ - 1], [x, maxZ + 1]]) {
    const hit = hitGround(visuals.group, px, pz);
    assert.equal(hit.object, exterior);
    near(hit.point.y, 0);
  }
  for (const [px, pz] of [[minX + 1, z], [maxX - 1, z], [x, minZ + 1], [x, maxZ - 1]]) {
    const hit = hitGround(visuals.group, px, pz);
    assert.equal(hit.object, apron);
    near(hit.point.y, 0);
  }

  const ramp = geometry.alignment.link.find(({ s }) => s > 35);
  const exposed = hitGround(visuals.group, ramp.x, ramp.z);
  assert.equal(exposed.object.name, "road");
  assert.ok(exposed.point.y < -.2);
  near(exposed.point.y, ramp.y + .03);
  const underCover = geometry.alignment.link.find(({ s }) => s > 250);
  const sealed = hitGround(visuals.group, underCover.x, underCover.z);
  assert.equal(sealed.object, apron);
  near(sealed.point.y, 0);
});

test("the level paint fits between tile parks and junctions with one batched walkway and tunnel lighting", t => {
  const material = new MeshLambertMaterial();
  const visuals = createFortCanningVisuals(geometry, material);
  t.after(() => { visuals.dispose(); material.dispose(); });
  const { group } = visuals;
  const road = group.getObjectByName("road");
  const markings = group.getObjectByName("lane-markings");
  near(road.position.y, .03);
  near(markings.geometry.attributes.position.getY(0) + markings.position.y, .031);
  assert.ok(.01 < road.position.y && road.position.y < .032);
  const walkways = geometry.surfaces.filter(({ id }) => id === "footway");
  const footway = group.getObjectByName("footway");
  assert.equal(footway.geometry.index.count, walkways.reduce((sum, { indices }) => sum + indices.length, 0));

  const lamps = group.getObjectByName("roof-lighting");
  assert.ok(lamps.isInstancedMesh && lamps.count > 20);
  const matrix = new Matrix4(), position = new Vector3();
  let previous = 0;
  for (let i = 0; i < lamps.count; i++) {
    lamps.getMatrixAt(i, matrix);
    position.setFromMatrixPosition(matrix);
    const row = geometry.alignment.link.find(({ x, z }) => Math.hypot(x - position.x, z - position.z) < .001);
    assert.ok(row.s > previous && row.s >= geometry.coveredFrom + 3 && row.s <= geometry.coveredTo - 3);
    near(position.y, row.y + geometry.clearance - .065);
    previous = row.s;
  }
});

test("dispose removes the scene group and releases only the resources it owns", () => {
  const ground = new MeshLambertMaterial();
  const scene = new Group();
  const visuals = createFortCanningVisuals(geometry, ground);
  scene.add(visuals.group);
  const meshes = [...visuals.group.children];
  let groundDisposals = 0, geometryDisposals = 0, materialDisposals = 0;
  ground.addEventListener("dispose", () => groundDisposals++);
  for (const mesh of meshes) {
    mesh.geometry.addEventListener("dispose", () => geometryDisposals++);
    if (mesh.material !== ground) mesh.material.addEventListener("dispose", () => materialDisposals++);
  }
  visuals.dispose();
  visuals.dispose();
  assert.equal(scene.children.length, 0);
  assert.equal(geometryDisposals, meshes.length);
  assert.equal(materialDisposals, meshes.filter(mesh => mesh.material !== ground).length);
  assert.equal(groundDisposals, 0);
  ground.dispose();
});
