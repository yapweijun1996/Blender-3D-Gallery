import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { Box3, Raycaster, Vector3 } from 'three';
import { readGlb } from '../../models/mall-floor-tile/glb.mjs';
import {
  assembleEscalatorTerminals,
  escalatorTerminalPaths,
} from '../../mall-modules-preview/escalator-terminal.js';
import { createEscalatorRoute } from '../../mall-modules-preview/escalator-passenger-route.js';

const load = (path) => readGlb(fileURLToPath(new URL('../../' + path, import.meta.url)));
const assets = Object.fromEntries(
  await Promise.all(
    Object.entries(escalatorTerminalPaths).map(async ([key, path]) => [key, await load(path)]),
  ),
);
const avatar = await load('models/gjh-mall-visitor/exports/gjh-mall-visitor.glb');
const v = (x = 0, y = 0, z = 0) => new Vector3(x, y, z);
const near = (a, b, tolerance, label) =>
  assert.ok(Math.abs(a - b) <= tolerance, label + ': ' + a + ' vs ' + b);
const down = v(0, -1, 0);
const rounded = (x) => +x.toFixed(8);
const touch = 0.000002;

function install(direction = 'up') {
  const { group, machine } = assembleEscalatorTerminals(
    Object.fromEntries(Object.entries(assets).map(([key, gltf]) => [key, gltf.scene])),
  );
  group.updateMatrixWorld(true);
  const route = createEscalatorRoute(
    {
      machine,
      clips: assets.escalator.animations,
      avatar: avatar.scene,
      avatarClips: avatar.animations,
    },
    direction,
  );
  const shoes = ['LeftFoot', 'RightFoot'].map((name) => {
    const meshes = [];
    route.visual.getObjectByName(name).traverse((object) => {
      if (object.isMesh) meshes.push(object);
    });
    assert.ok(meshes.length);
    return meshes;
  });
  return { group, machine, route, shoes };
}

function sole(meshes) {
  const point = v(),
    pole = v(0, Infinity, 0),
    bounds = new Box3();
  for (const mesh of meshes) {
    const positions = mesh.geometry.attributes.position;
    for (let i = 0; i < positions.count; i++) {
      mesh.getVertexPosition(i, point).applyMatrix4(mesh.matrixWorld);
      bounds.expandByPoint(point);
      if (point.y < pole.y) pole.copy(point);
    }
  }
  return { pole, bounds };
}

function terrain(group, machine) {
  const parts = [],
    ray = new Raycaster();
  const add = (root, label, moving = false) =>
    root.traverse((mesh) => {
      if (!mesh.isMesh) return;
      mesh.geometry.computeBoundingBox();
      parts.push({
        mesh,
        label,
        moving,
        box: mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld),
      });
    });
  for (const terminal of group.children.filter((node) => node.userData.terminal)) {
    const level = terminal.userData.terminal;
    for (const module of terminal.children) {
      if (module.userData.role === 'centre') add(module, level + ' tile');
      if (module.userData.moduleId === 'escalatorTransition2m') add(module, level + ' profile');
    }
  }
  for (const level of ['Lower', 'Upper'])
    for (const prefix of ['LANDING', 'COMB']) {
      const name = prefix + '_' + level;
      add(machine.getObjectByName(name), name);
    }
  machine.traverse((node) => {
    if (/^STEP_BODY_\d+$/.test(node.name)) add(node, node.name, true);
  });
  assert.equal(parts.filter((p) => p.moving).length, 58);
  const byMesh = new Map(parts.map((p) => [p.mesh, p]));
  function update() {
    for (const p of parts)
      if (p.moving) p.box.copy(p.mesh.geometry.boundingBox).applyMatrix4(p.mesh.matrixWorld);
  }
  function probe(point, ignore) {
    const from = point.y + 0.33;
    const boundsMatch = ({ box: b, label }) =>
      label !== ignore &&
      b.min.x <= point.x + 1e-6 &&
      b.max.x >= point.x - 1e-6 &&
      b.min.z <= point.z + 1e-6 &&
      b.max.z >= point.z - 1e-6 &&
      b.min.y <= from &&
      b.max.y >= point.y - 0.5;
    ray.set(v(point.x, from, point.z), down);
    ray.far = 0.83;
    const hit = ray.intersectObjects(
      parts.filter(boundsMatch).map((p) => p.mesh),
      false,
    )[0];
    return (
      hit && {
        object: hit.object,
        label: byMesh.get(hit.object).label,
        gap: point.y - hit.point.y,
        y: hit.point.y,
      }
    );
  }
  return { update, probe };
}

function sideClearance(machine, visual) {
  const sides = [];
  for (const label of ['SKIRT', 'GUARD', 'HANDRAIL', 'HANDRAIL_MaterialSeam'])
    for (const side of ['L', 'R']) {
      machine.getObjectByName(label + '_' + side).traverse((mesh) => {
        if (mesh.isMesh) sides.push([mesh, side]);
      });
    }
  const visitorMeshes = [];
  visual.traverse((mesh) => {
    if (mesh.isMesh) visitorMeshes.push(mesh);
  });
  for (const mesh of [...visitorMeshes, ...sides.map((s) => s[0])]) mesh.geometry.computeBoundingBox();
  const b = new Box3(),
    projected = new Box3();
  return () => {
    projected.makeEmpty();
    for (const mesh of visitorMeshes)
      projected.union(b.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld));
    let clearance = Infinity;
    for (const [mesh, side] of sides) {
      b.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld);
      clearance = Math.min(clearance, side === 'R' ? b.min.x - projected.max.x : projected.min.x - b.max.x);
    }
    return clearance;
  };
}

// Confirm the front/back of the actual posed shoe over a short transition. Each
// vertical line intersects shoe triangles and the real surface directly below.
function finishUnderShoe(shoe, pose, surface) {
  const ray = new Raycaster(),
    upper = pose.bounds.max.y + 0.02,
    lower = pose.bounds.min.y - 0.06;
  const samples = [];
  for (const fraction of [0.07, 0.23, 0.5, 0.77, 0.93]) {
    const z = pose.bounds.min.z + (pose.bounds.max.z - pose.bounds.min.z) * fraction;
    const point = v(pose.pole.x, lower, z);
    ray.set(point, v(0, 1, 0));
    ray.far = upper - lower;
    const hit = ray.intersectObjects(shoe, false)[0];
    if (!hit) continue;
    const contact = surface.probe(hit.point);
    assert.ok(contact, 'missing surface directly under near-edge shoe');
    assert.ok(contact.gap >= -2e-6, 'shoe triangles penetrate ' + contact.label);
    samples.push({ label: contact.label, y: contact.y, gap: contact.gap });
  }
  return samples;
}

function undersideAt(meshes, x, z, lowestY) {
  const ray = new Raycaster(v(x, lowestY - 0.04, z), v(0, 1, 0), 0, 0.26);
  return ray.intersectObjects(meshes, false)[0]?.point;
}

function movingNodes(machine) {
  const nodes = [];
  machine.traverse((node) => {
    if (/^STEP_\d+$|^HANDRAIL_MaterialSeam_[LR]$/.test(node.name)) nodes.push(node);
  });
  assert.equal(nodes.length, 60);
  return nodes;
}
function matrices(nodes) {
  return nodes.flatMap((node) => node.matrixWorld.toArray());
}
function difference(a, b) {
  assert.equal(a.length, b.length);
  return a.reduce((max, value, index) => Math.max(max, Math.abs(value - b[index])), 0);
}

export {
  assets,
  v,
  near,
  rounded,
  touch,
  install,
  sole,
  terrain,
  sideClearance,
  finishUnderShoe,
  undersideAt,
  movingNodes,
  matrices,
  difference,
};
