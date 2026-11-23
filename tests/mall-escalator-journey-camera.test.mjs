import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box2, PerspectiveCamera, Raycaster, Vector2, Vector3 } from 'three';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { createEscalatorRoute } from '../mall-modules-preview/escalator-passenger-route.js';
import {
  assembleEscalatorTerminals,
  descendingJourneyView,
  escalatorTerminalPaths,
  journeyView,
} from '../mall-modules-preview/escalator-terminal.js';

const load = (path) => readGlb(fileURLToPath(new URL('../' + path, import.meta.url)));
const [modules, visitor] = await Promise.all([
  Promise.all(
    Object.entries(escalatorTerminalPaths).map(async ([key, path]) => [key, await load(path)]),
  ),
  load('models/gjh-mall-visitor/exports/gjh-mall-visitor.glb'),
]);
const sources = Object.fromEntries(modules.map(([key, gltf]) => [key, gltf.scene]));
const escalatorClips = Object.fromEntries(modules).escalator.animations;

// Sample camera pixels within the projected part. The first opaque surface may
// be a shoe, torso, balustrade or tread. Transparent glass can still tint it.
function visibility(mesh, camera, surfaces) {
  const rect = new Box2();
  const point = new Vector3(),
    screen = new Vector2(),
    ray = new Raycaster();
  for (let i = 0; i < mesh.geometry.attributes.position.count; i++) {
    mesh.getVertexPosition(i, point).applyMatrix4(mesh.matrixWorld).project(camera);
    rect.expandByPoint(screen.set(point.x, point.y));
  }
  let targetPixels = 0,
    visible = 0,
    direct = 0;
  for (let iy = 0; iy < 9; iy++)
    for (let ix = 0; ix < 13; ix++) {
      screen.set(
        rect.min.x + ((ix + 0.5) / 13) * (rect.max.x - rect.min.x),
        rect.min.y + ((iy + 0.5) / 9) * (rect.max.y - rect.min.y),
      );
      ray.setFromCamera(screen, camera);
      ray.far = Infinity;
      const hit = ray.intersectObject(mesh, false)[0];
      if (!hit) continue;
      ray.far = hit.distance + 1e-5;
      targetPixels++;
      const hits = ray.intersectObjects(surfaces, false);
      if (hits[0]?.object === mesh) direct++;
      if (hits.find((hit) => !hit.object.material.transparent)?.object === mesh) visible++;
    }
  assert.ok(targetPixels > 25, 'the projected part has sufficient real triangle samples');
  return { visible: visible / targetPixels, direct: direct / targetPixels };
}

for (const [direction, view, times] of [
  ['up', journeyView, [3.73, 12, 21.8]],
  ['down', descendingJourneyView, [4.28, 12, 22.34]],
]) {
  test(
    direction + ' journey camera frames the avatar and keeps both shoes visible during the transfers',
    (t) => {
      const { group, machine } = assembleEscalatorTerminals(sources);
      group.updateMatrixWorld(true);
      const ride = createEscalatorRoute(
        {
          machine,
          clips: escalatorClips,
          avatar: visitor.scene,
          avatarClips: visitor.animations,
        },
        direction,
      );
      t.after(() => ride.dispose());
      const surfaces = [];
      group.traverse((node) => {
        if (node.isMesh) {
          node.geometry.computeBoundingBox();
          surfaces.push(node);
        }
      });
      const landmarks = ['LeftFoot_geometry', 'RightFoot_geometry', 'Rounded_face'].map((name) => {
        const part = ride.visual.getObjectByName(name);
        assert.ok(part?.isMesh, 'the native passenger has ' + name);
        return part;
      });
      let minimumVisibility = 1,
        minimumDirect = 1;
      for (const time of times) {
        ride.seek(time);
        for (const [w, h] of [
          [924, 440],
          [352, 330],
        ]) {
          const camera = new PerspectiveCamera(34, w / h, 0.01, 100);
          const target = ride.visual.localToWorld(new Vector3(...view.target));
          const directionVector = new Vector3(...view.direction).transformDirection(
            ride.visual.matrixWorld,
          );
          const vertical = (camera.fov * Math.PI) / 360,
            horizontal = Math.atan(Math.tan(vertical) * camera.aspect);
          camera.position
            .copy(target)
            .addScaledVector(directionVector, view.radius / Math.sin(Math.min(vertical, horizontal)));
          camera.lookAt(target);
          camera.updateMatrixWorld();
          const point = new Vector3();
          ride.visual.traverse((node) => {
            if (!node.isMesh) return;
            for (let i = 0; i < node.geometry.attributes.position.count; i++) {
              node.getVertexPosition(i, point).applyMatrix4(node.matrixWorld).project(camera);
              assert.ok(
                Math.abs(point.x) < 0.94 && Math.abs(point.y) < 0.94 && point.z > -1 && point.z < 1,
                'full passenger fits inside the canvas',
              );
            }
          });
          for (const part of landmarks) {
            const result = visibility(part, camera, surfaces);
            minimumVisibility = Math.min(minimumVisibility, result.visible);
            minimumDirect = Math.min(minimumDirect, result.direct);
            assert.ok(
              result.visible > 0.2,
              part.name + ' is obscured by the passenger or opaque machinery at ' + time,
            );
            if (direction === 'down')
              assert.ok(
                result.direct > 0.3,
                part.name + ' should be visible between the descending rails at ' + time,
              );
          }
        }
      }
      t.diagnostic(
        JSON.stringify({
          times,
          minimumVisibleFraction: minimumVisibility,
          minimumDirectFraction: minimumDirect,
        }),
      );
    },
  );
}
