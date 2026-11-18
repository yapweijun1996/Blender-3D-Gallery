import assert from 'node:assert/strict';
import { mkdir, readFile } from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';
import { launchOptions } from '../../scripts/browser-test-utils.mjs';

const output = process.env.TRIPO_QA_DIR;
const sourcePath = process.env.TRIPO_SOURCE_SAMPLES;
assert.ok(output && sourcePath, 'Set TRIPO_QA_DIR and TRIPO_SOURCE_SAMPLES first');
const source = JSON.parse(await readFile(sourcePath, 'utf8'));
assert.deepEqual(source.samples.map(sample => sample.frame), [1, 15, 29, 43, 57]);
assert.equal(source.source_action, 'Armature|walk.001');
assert.equal(source.vertices, 19811);
assert.equal(source.surface_vertices, 19809);
await mkdir(output, { recursive: true });

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Tripo Walk QA</title>
<script type="importmap">{"imports":{"three":"/three/build/three.module.js"}}</script></head>
<body style="margin:0"><script type="module">
import * as THREE from 'three';
import { GLTFLoader } from '/three/examples/jsm/loaders/GLTFLoader.js';

const gltf = await new GLTFLoader().loadAsync('/character.glb');
const scene = new THREE.Scene();
scene.background = new THREE.Color('#353535');
scene.add(gltf.scene, new THREE.HemisphereLight(0xffffff, 0x888899, 2));
const light = new THREE.DirectionalLight(0xffffff, 2);
light.position.set(3, 5, 4);
scene.add(light);
const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100);
const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(600, 600);
document.body.append(renderer.domElement);

const meshes = [];
gltf.scene.traverse(node => { if (node.isSkinnedMesh) meshes.push(node); });
if (meshes.length !== 1 || gltf.animations.length !== 1 || gltf.animations[0].name !== 'walk') {
  throw new Error('Expected one textured skinned mesh and one walk clip');
}
const [mesh] = meshes;
if (!mesh.material.map) throw new Error('The source texture was not loaded');
const mixer = new THREE.AnimationMixer(gltf.scene);
const [clip] = gltf.animations;
const action = mixer.clipAction(clip).setLoop(THREE.LoopOnce, 1);
action.clampWhenFinished = true;
window.samplePose = (time) => {
  action.reset().play();
  mixer.setTime(time);
  scene.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(mesh, true);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3()).length();
  camera.position.copy(center).add(new THREE.Vector3(1.3, 0.6, 2).normalize().multiplyScalar(size * 1.5));
  camera.lookAt(center);
  renderer.render(scene, camera);

  const position = new THREE.Vector3();
  const vertices = Array.from({ length: mesh.geometry.attributes.position.count }, (_, index) => {
    mesh.getVertexPosition(index, position).applyMatrix4(mesh.matrixWorld);
    // Convert glTF Y-up world coordinates back to Blender's Z-up coordinates.
    return [position.x, -position.z, position.y];
  });
  return {
    bounds: [box.min.x, -box.max.z, box.min.y, box.max.x, -box.min.z, box.max.y],
    drawCalls: renderer.info.render.calls,
    vertices,
  };
};
window.clipDuration = clip.duration;
</script></body></html>`;

function maxVertexError(sourceVertices, exportedVertices) {
  const cellSize = 0.001;
  const cell = point => point.map(value => Math.floor(value / cellSize));
  const buckets = new Map();
  for (const point of exportedVertices) {
    const key = cell(point).join(',');
    if (!buckets.has(key)) buckets.set(key, []);
    buckets.get(key).push(point);
  }
  let maximum = 0;
  for (const point of sourceVertices) {
    const [cx, cy, cz] = cell(point);
    let nearest = Infinity;
    for (let x = cx - 1; x <= cx + 1; x++) {
      for (let y = cy - 1; y <= cy + 1; y++) {
        for (let z = cz - 1; z <= cz + 1; z++) {
          for (const candidate of buckets.get(`${x},${y},${z}`) ?? []) {
            nearest = Math.min(nearest, Math.hypot(...point.map((value, i) => value - candidate[i])));
          }
        }
      }
    }
    maximum = Math.max(maximum, nearest);
  }
  return maximum;
}

const browser = await chromium.launch(launchOptions);
try {
  const page = await browser.newPage({ viewport: { width: 600, height: 600 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => errors.push(request.url()));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  await page.route('http://tripo.test/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/') return route.fulfill({ contentType: 'text/html', body: html });
    if (url.pathname === '/favicon.ico') return route.fulfill({ status: 204 });
    if (url.pathname === '/character.glb') {
      const body = await readFile(new URL('./character.glb', import.meta.url));
      return route.fulfill({ body, contentType: 'model/gltf-binary' });
    }
    if (/^\/three\/[\w/.-]+\.js$/.test(url.pathname)) {
      const module = new URL(`../../node_modules${url.pathname}`, import.meta.url);
      return route.fulfill({ body: await readFile(module), contentType: 'text/javascript' });
    }
    return route.abort();
  });

  await page.goto('http://tripo.test/');
  await page.waitForFunction(() => typeof window.samplePose === 'function');
  const duration = await page.evaluate(() => window.clipDuration);
  assert.ok(Math.abs(duration - 57 / source.fps) < 1e-6, `Unexpected duration ${duration}`);
  const results = [];
  for (const { frame, bounds, vertices } of source.samples) {
    assert.equal(vertices.length, source.surface_vertices);
    const pose = await page.evaluate(time => window.samplePose(time), frame / source.fps);
    const vertexError = maxVertexError(vertices, pose.vertices);
    const boundsError = Math.max(...bounds.map((value, index) => Math.abs(value - pose.bounds[index])));
    assert.ok(vertexError < 0.0001, `Walk frame ${frame} vertex error ${vertexError}`);
    assert.ok(boundsError < 0.0001, `Walk frame ${frame} bounds error ${boundsError}`);
    assert.ok(pose.drawCalls > 0, `Walk frame ${frame} did not render`);
    await page.locator('canvas').screenshot({ path: path.join(output, `walk-${frame}.png`) });
    results.push({ frame, maxVertexError: vertexError, maxBoundsError: boundsError });
  }
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ browser: browser.version(), duration, results }, null, 2));
} finally {
  await browser.close();
}
