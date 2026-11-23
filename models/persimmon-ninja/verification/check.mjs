// From the repository root: node models/persimmon-ninja/verification/check.mjs
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { chromium } from 'playwright';
import { launchOptions, serveBuild } from '../../../scripts/browser-test-utils.mjs';

const here = new URL('.', import.meta.url);
const root = new URL('../../../', here);
const asset = 'models/persimmon-ninja/exports/persimmon-ninja.glb';
const bytes = await readFile(new URL(asset, root));
const sha256 = createHash('sha256').update(bytes).digest('hex');
const validated = await validator.validateBytes(new Uint8Array(bytes));
const server = await serveBuild(fileURLToPath(root));
const errors = [];
let browser;
try {
  browser = await chromium.launch(launchOptions);
  const page = await browser.newPage({ viewport: { width: 1440, height: 448 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.route(server.url + 'qa', route => route.fulfill({
    contentType: 'text/html',
    body: '<style>body{margin:0}canvas{display:block}</style><link rel="icon" href="data:,"><script type="importmap">' +
      JSON.stringify({ imports: { three: './node_modules/three/build/three.module.js', 'three/addons/': './node_modules/three/examples/jsm/' } }) + '</script>',
  }));
  await page.goto(server.url + 'qa');
  const observed = await page.evaluate(async file => {
    const THREE = await import('three');
    const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
    const response = await fetch(file);
    if (!response.ok) throw new Error('GLB fetch: ' + response.status);
    const data = await response.arrayBuffer();
    const digest = await crypto.subtle.digest('SHA-256', data);
    const hash = [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, '0')).join('');
    const { scene: character, animations } = await new GLTFLoader().parseAsync(data, '');
    character.updateMatrixWorld(true);
    const bounds = new THREE.Box3().setFromObject(character, true);
    const center = bounds.getCenter(new THREE.Vector3());
    const height = bounds.max.y - bounds.min.y;
    const bones = new Set(), morphDeltas = {}, neutralInfluences = {};
    const position = new THREE.Vector3(), base = new THREE.Vector3(), delta = new THREE.Vector3();
    let meshes = 0, skinnedMeshes = 0, badWeights = 0, badJoints = 0, skinnedVertices = 0, bestWeightedVertex;
    character.traverse(o => {
      if (!o.isMesh) return;
      meshes++;
      for (const [name, index] of Object.entries(o.morphTargetDictionary ?? {})) {
        neutralInfluences[name] = Math.max(neutralInfluences[name] ?? 0, Math.abs(o.morphTargetInfluences[index]));
        const attribute = o.geometry.morphAttributes.position[index];
        let max = 0;
        for (let v = 0; v < attribute.count; v++) {
          delta.fromBufferAttribute(attribute, v);
          if (!o.geometry.morphTargetsRelative) delta.sub(base.fromBufferAttribute(o.geometry.attributes.position, v));
          max = Math.max(max, delta.length());
        }
        morphDeltas[name] = Math.max(morphDeltas[name] ?? 0, max);
      }
      if (!o.isSkinnedMesh) return;
      skinnedMeshes++;
      const { skeleton } = o;
      for (const bone of skeleton.bones) bones.add(bone.name);
      const w = o.geometry.attributes.skinWeight, j = o.geometry.attributes.skinIndex;
      skinnedVertices += w.count;
      for (let v = 0; v < w.count; v++) {
        let total = 0;
        for (let k = 0; k < w.itemSize; k++) {
          const weight = w.getComponent(v, k), joint = j.getComponent(v, k);
          total += weight;
          if (!Number.isFinite(weight) || weight < 0) badWeights++;
          if (weight > 0 && (!Number.isInteger(joint) || !skeleton.bones[joint])) badJoints++;
          if (weight > .99 && !bestWeightedVertex && skeleton.bones[joint]?.parent?.isBone) {
            bestWeightedVertex = { object: o, bone: skeleton.bones[joint], vertex: v };
          }
        }
        if (Math.abs(total - 1) > .001) badWeights++;
      }
    });
    let posedDisplacement = 0;
    if (bestWeightedVertex) {
      const { object, bone, vertex } = bestWeightedVertex;
      base.copy(object.getVertexPosition(vertex, position));
      bone.position.x += .01;
      character.updateMatrixWorld(true);
      posedDisplacement = object.getVertexPosition(vertex, position).distanceTo(base);
      bone.position.x -= .01;
      character.updateMatrixWorld(true);
    }

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf3eeeb);
    scene.add(character, new THREE.HemisphereLight(0xfff4ed, 0xdfd4cc, 1.55));
    const key = new THREE.DirectionalLight(0xfff6e9, 2);
    key.position.set(-2, 3, 4);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xe2ecff, 1.0);
    fill.position.set(2, 1, -3);
    scene.add(fill);
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    const width = 360, panelHeight = 448;
    renderer.setSize(width * 4, panelHeight);
    document.body.appendChild(renderer.domElement);
    renderer.setScissorTest(true);
    const halfY = height * .56;
    const halfX = halfY * width / panelHeight;
    const camera = new THREE.OrthographicCamera(-halfX, halfX, halfY, -halfY, .01, height * 20);
    const angles = [0, 35, 90, 180];
    for (const [i, degrees] of angles.entries()) {
      const rad = THREE.MathUtils.degToRad(degrees);
      camera.position.copy(center).add(new THREE.Vector3(Math.sin(rad) * 3, .08, Math.cos(rad) * 3).multiplyScalar(height));
      camera.lookAt(center);
      renderer.setViewport(i * width, 0, width, panelHeight);
      renderer.setScissor(i * width, 0, width, panelHeight);
      renderer.render(scene, camera);
    }
    window.renderExpressions = () => {
      const names = ['neutral', 'smile', 'surprised', 'blink'];
      const focus = center.clone();
      focus.y = bounds.min.y + height * .73;
      const half = height * .29;
      const faceCamera = new THREE.OrthographicCamera(-half*width/panelHeight, half*width/panelHeight, half, -half, .01, height*20);
      faceCamera.position.copy(focus).add(new THREE.Vector3(.17, .03, 3).multiplyScalar(height));
      faceCamera.lookAt(focus);
      for (const [i, name] of names.entries()) {
        character.traverse(o => {
          if (!o.morphTargetInfluences) return;
          o.morphTargetInfluences.fill(0);
          const index = o.morphTargetDictionary[name];
          if (index !== undefined) o.morphTargetInfluences[index] = 1;
        });
        renderer.setViewport(i * width, 0, width, panelHeight);
        renderer.setScissor(i * width, 0, width, panelHeight);
        renderer.render(scene, faceCamera);
      }
      return names;
    };
    const idle = animations.find(c => c.name === 'Lookout Idle');
    const mixer = new THREE.AnimationMixer(character);
    let maxIdleRotationRadians = 0;
    if (idle) {
      mixer.clipAction(idle).play();
      const joints = [];
      character.traverse(o => { if (o.isBone) joints.push(o); });
      mixer.setTime(0);
      character.updateMatrixWorld(true);
      const start = joints.map(b => b.quaternion.clone());
      for (const t of [.2,.4,.6,.8]) {
        mixer.setTime(t * idle.duration);
        character.updateMatrixWorld(true);
        for (const [i, bone] of joints.entries()) {
          maxIdleRotationRadians = Math.max(maxIdleRotationRadians, bone.quaternion.angleTo(start[i]));
        }
      }
      mixer.stopAllAction();
    }
    return { hash, height, feetY: bounds.min.y, meshes, skinnedMeshes, skinnedVertices, bones: [...bones],
      badWeights, badJoints, posedDisplacement, morphDeltas, neutralInfluences, maxIdleRotationRadians,
      clips: animations.map(a => ({ name: a.name, seconds: a.duration })), angles,
      drawCallsInLastView: renderer.info.render.calls };
  }, server.url + asset);
  await page.locator('canvas').screenshot({ path: fileURLToPath(new URL('three-views.png', here)) });
  observed.facePanels = await page.evaluate(() => window.renderExpressions());
  await page.locator('canvas').screenshot({ path: fileURLToPath(new URL('three-expressions.png', here)) });
  const { info, issues } = validated;
  const checks = {
    exactFile: observed.hash === sha256,
    validatorClean: issues.numErrors === 0 && issues.numWarnings === 0,
    actualGeometry: Number.isFinite(observed.height) && observed.height > 0 && info.totalTriangleCount > 0,
    triangleBudget: info.totalTriangleCount <= 40000,
    drawBudget: info.drawCallCount <= 20,
    namedJoints: observed.bones.length > 0 && observed.bones.length <= 20,
    deformingSkin: observed.skinnedVertices > 0 && observed.badWeights === 0 && observed.badJoints === 0 && observed.posedDisplacement > 0.001,
    expressions: ['smile', 'surprised', 'blink'].every(name => observed.neutralInfluences[name] === 0 && observed.morphDeltas[name] > .001),
    idlePlayback: observed.maxIdleRotationRadians > .001,
    browserClean: errors.length === 0,
  };
  const report = { asset, sha256, bytes: bytes.length, triangles: info.totalTriangleCount, drawCalls: info.drawCallCount,
    validator: { errors: issues.numErrors, warnings: issues.numWarnings, infos: issues.numInfos, messages: issues.messages },
    three: observed, browserErrors: errors, checks };
  await writeFile(new URL('report.json', here), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({ sha256, triangles: report.triangles, drawCalls: report.drawCalls, checks }));
  if (Object.values(checks).some(ok => !ok)) process.exitCode = 1;
} finally {
  await browser?.close();
  await server.close();
}
