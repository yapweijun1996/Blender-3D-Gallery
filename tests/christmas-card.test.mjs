import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { greeting } from '../src/christmas-card/config.js';

const layouts = [
  [{ left: 0, top: 0, width: 390, height: 844 }, { left: 16, top: 126, width: 358, height: 622 }],
  [{ left: 0, top: 0, width: 1440, height: 900 }, { left: 340, top: 154, width: 760, height: 694 }],
  [{ left: 0, top: 0, width: 1366, height: 657 }, { left: 303, top: 115, width: 760, height: 490 }],
];

test('Christmas greeting is bilingual and the GLB contains the opening clip', () => {
  for (const lang of ['en', 'zh']) {
    assert.ok(greeting[lang].recipient && greeting[lang].sender);
    assert.ok(greeting[lang].lines.length >= 2 && greeting[lang].lines.every(Boolean));
  }
  const bytes = readFileSync('models/christmas-envelope/envelope.glb');
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.ok(bytes.length < 1_500_000);
  const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
  const clip = gltf.animations.find(a => a.name === 'Open');
  assert.ok(clip);
  const names = new Set(clip.channels.map(c => gltf.nodes[c.target.node].name));
  for (const name of ['Flap', 'Seal', 'Letter']) assert.ok(names.has(name), name);
  const flap = gltf.nodes.find(node => node.name === 'Flap');
  assert.ok(gltf.meshes[flap.mesh].primitives.some(p => gltf.materials[p.material].name === 'WarmLining'));
  assert.ok(Number.isFinite(gltf.nodes.find(node => node.name === 'Envelope').extras.burstTime));
});

test('card worker holds upgrades until the visitor approves them', async () => {
  const { runInNewContext } = await import('node:vm');
  const template = readFileSync('src/christmas-card/sw-template.js', 'utf8').replace('__VERSION__', '"test"').replace('__FILES__', '["christmas-card/index.html"]');
  async function install(active) {
    const handlers = {}, cache = { put: async () => {} };
    let skipped = 0, promise;
    const self = { registration: {scope:'https://example.test/site/christmas-card/', active}, addEventListener: (name, fn) => {handlers[name] = fn}, skipWaiting: async () => {skipped++} };
    runInNewContext(template, {self, URL, caches:{open:async()=>cache,delete:async()=>{}}, fetch:async()=>({ok:true})});
    handlers.install({waitUntil: value => {promise = value}});
    return {handlers, promise, skipped: () => skipped};
  }
  const initial = await install(null);
  await initial.promise;
  assert.equal(initial.skipped(), 0);
  const update = await install({});
  let done = false;
  update.promise.then(() => {done = true});
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(done, false);
  update.handlers.message({data:{type:'ACTIVATE'}});
  await update.promise;
  assert.equal(update.skipped(), 1);
});

test('the playback step stays bounded after a stalled or reactivated frame', async () => {
  const { frameDelta } = await import('../src/christmas-card/motion.js');
  assert.equal(frameDelta(1500, null), 0);
  assert.equal(frameDelta(1500, 1484), .016);
  assert.equal(frameDelta(1500, 400), 1 / 30);
});

test('warm-up releases playback when compileAsync stays pending and ignores its late completion', {timeout:1000}, async () => {
  const { warmWithinBudget } = await import('../src/christmas-card/warmup.js');
  let completeCompile, draws = 0;
  const renderer = { compileAsync: () => new Promise(resolve => { completeCompile = resolve; }) };
  await warmWithinBudget(renderer, null, null, () => { draws++; }, 35);
  completeCompile();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(draws, 0);
});

test('warm-up flushes and retires an unsignaled fence at the same deadline', {timeout:1000}, async () => {
  const { warmWithinBudget } = await import('../src/christmas-card/warmup.js');
  const calls = [], fence = {};
  const gl = {
    SYNC_GPU_COMMANDS_COMPLETE: 1,
    TIMEOUT_EXPIRED: 2,
    fenceSync(...args) { assert.deepEqual(args, [1, 0]); calls.push('fence'); return fence; },
    flush() { calls.push('flush'); },
    clientWaitSync(...args) { assert.deepEqual(args, [fence, 0, 0]); calls.push('poll'); return this.TIMEOUT_EXPIRED; },
    deleteSync(value) { assert.equal(value, fence); calls.push('delete'); },
  };
  const renderer = { compileAsync: async () => { calls.push('compile'); }, getContext: () => gl };
  await warmWithinBudget(renderer, null, null, () => calls.push('draw'), 180);
  assert.deepEqual(calls.slice(0, 5), ['compile', 'draw', 'fence', 'flush', 'poll']);
  assert.equal(calls.at(-1), 'delete');
  await new Promise(resolve => setTimeout(resolve, 24));
  assert.equal(calls.at(-1), 'delete', 'no further polling after the deadline');
});

test('the small off-screen envelope grows, loops once, and holds its address side in view', async () => {
  const THREE = await import('three');
  const { frameEnvelope } = await import('../src/christmas-card/framing.js');
  const { createEntranceFlight, entranceDuration, loopStart, loopEnd, poseEntrance } = await import('../src/christmas-card/motion.js');
  const { scene: root } = await loadModel();
  for (const [viewport, stage] of layouts) {
    const camera = new THREE.PerspectiveCamera();
    frameEnvelope(camera, viewport, stage);
    const flight = createEntranceFlight(root, camera, viewport.width);
    poseEntrance(root, 0, flight);
    const first = projectedBounds(root, camera, THREE);
    assert.ok(first.max.x < -1 && first.max.x > -1 - 6 / viewport.width, 'model starts just outside the viewport');
    assert.ok(root.position.z < -flight.distance, 'model starts at a distance');
    assert.ok(root.rotation.y > Math.PI / 2, 'address side faces the viewer on entry');
    let crossedLeft = false, fullyEntered = false;
    let addressTime = 0;
    for (let t = 0; t <= entranceDuration; t += 1 / 120) {
      poseEntrance(root, t, flight);
      const { min, max } = projectedBounds(root, camera, THREE);
      crossedLeft ||= min.x < -1 && max.x > -1;
      fullyEntered ||= min.x >= -1;
      if (fullyEntered) assert.ok(min.x >= -1, `Entrance re-crosses the left edge at ${t}s`);
      if (max.x > -1) assert.ok(min.y > -1 && max.y < 1 && max.x < 1, `Entrance clips at ${t}s`);
      if (fullyEntered && Math.cos(root.rotation.y) < -.85 && max.x - min.x > (first.max.x - first.min.x) * 1.5) addressTime += 1 / 120;
    }
    assert.ok(crossedLeft && fullyEntered, 'envelope crosses the left edge and enters completely');
    assert.ok(addressTime > 1, 'visible address side has time to be read');
    const angles = [];
    for (let i = 0; i <= 80; i++) {
      poseEntrance(root, loopStart + (loopEnd - loopStart) * i / 80, flight);
      angles.push(root.position.clone().project(camera));
    }
    const center = new THREE.Box3().setFromPoints(angles).getCenter(new THREE.Vector3());
    let sweep = 0;
    for (let i = 1; i < angles.length; i++) {
      const a = angles[i - 1].clone().sub(center), b = angles[i].clone().sub(center);
      sweep += Math.atan2(a.x * b.y - a.y * b.x, a.x * b.x + a.y * b.y);
    }
    assert.ok(Math.abs(Math.abs(sweep) - 2 * Math.PI) < .02, 'one complete loop in screen space');
    poseEntrance(root, 2.89, flight);
    assert.ok(root.position.x > .04, 'the landing has a small overshoot');
    poseEntrance(root, entranceDuration, flight);
    const settled = projectedBounds(root, camera, THREE);
    assert.ok(first.max.x - first.min.x < (settled.max.x - settled.min.x) * .42);
    assert.ok(root.position.length() < .0001 && root.rotation.y === 0, 'the seal side settles at idle');
  }
});

async function loadModel() {
  const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
  const bytes = readFileSync('models/christmas-envelope/envelope.glb');
  return new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
}

function projectedBounds(root, camera, THREE) {
  const bounds = new THREE.Box3(), point = new THREE.Vector3();
  root.updateMatrixWorld(true);
  root.traverseVisible(node => {
    if (!node.isMesh) return;
    const positions = node.geometry.attributes.position;
    for (let i = 0; i < positions.count; i++) {
      point.fromBufferAttribute(positions, i).applyMatrix4(node.matrixWorld).project(camera);
      bounds.expandByPoint(point);
    }
  });
  return bounds;
}

test('opening camera eases from idle toward the flap and widens to contain the burst and letter', async () => {
  const THREE = await import('three');
  const { frameEnvelope, poseOpeningCamera } = await import('../src/christmas-card/framing.js');
  const { poseIdle, poseRecedingEnvelope } = await import('../src/christmas-card/motion.js');
  const gltf = await loadModel();
  const root = gltf.scene, mixer = new THREE.AnimationMixer(root), action = mixer.clipAction(gltf.animations[0]);
  action.setLoop(THREE.LoopOnce, 1); action.clampWhenFinished=true; action.play();
  root.updateMatrixWorld(true);
  const ray = new THREE.Raycaster(new THREE.Vector3(1.37, 0, 5), new THREE.Vector3(0, 0, -1));
  const hits = ray.intersectObject(root, true);
  const foldBack = hits.filter(hit => hit.object.name === 'PocketRight').at(-1).point.z;
  const borderFront = hits.find(hit => hit.object.name === 'LetterBorder').point.z;
  assert.ok(foldBack - borderFront > .004, `Letter border must clear the fold, got ${foldBack-borderFront}`);
  const flap = root.getObjectByName('Flap');
  const seal = root.getObjectByName('Seal');
  const letter = root.getObjectByName('Letter');
  const { burstTime } = root.getObjectByName('Envelope').userData;
  const hinge = flap.position.clone();
  for (const [viewport, stage] of layouts) {
    const { width, height } = viewport;
    const camera = new THREE.PerspectiveCamera();
    const views = frameEnvelope(camera, viewport, stage);
    const idleCamera = [...camera.matrixWorld.elements, ...camera.projectionMatrix.elements];
    const previousCamera = camera.position.clone();
    let previousPitch = camera.rotation.x, previousRoll = camera.rotation.z, previousFov = camera.fov;
    action.reset().play();
    const end = action.getClip().duration - .0001;
    let lastChange = 0, pose = [0, 1, 0];
    for (let i = 0; i <= Math.ceil(end * 30); i++) {
      const time = Math.min(i / 30, end);
      mixer.setTime(time);
      poseOpeningCamera(camera, views, time, burstTime);
      assert.ok(camera.position.distanceTo(previousCamera) < views.idle.position.z * .047, `Camera jumped at ${time}s`);
      assert.ok(Math.abs(camera.rotation.x - previousPitch) <= .006, `Camera pitch jumped at ${time}s`);
      assert.ok(Math.abs(camera.rotation.z - previousRoll) <= .0031, `Camera roll jumped at ${time}s`);
      assert.ok(Math.abs(camera.fov - previousFov) <= .67, `Camera lens jumped at ${time}s`);
      previousCamera.copy(camera.position);
      previousPitch = camera.rotation.x;
      previousRoll = camera.rotation.z;
      previousFov = camera.fov;
      const { min, max } = projectedBounds(root, camera, THREE);
      assert.ok(min.x > -1 && max.x < 1 && min.y > -1 && max.y < 1, `Model clipped at ${time}s in ${width}×${height}`);
      assert.deepEqual(flap.position.toArray(), hinge.toArray());
      if (i === 0) {
        if (width === 390) assert.ok((max.x - min.x) * width / 2 >= width * .85);
        if (width === 1440) assert.ok((max.y - min.y) * height / 2 >= height * .45);
      }
      if (i === 9) assert.ok(seal.scale.x < .4, 'the seal responds on tap');
      if (i === 15) assert.ok(flap.rotation.x < -.15, 'the flap is moving within half a second');
      if (i === Math.round(burstTime * .6 * 30)) {
        assert.ok(camera.position.z < views.idle.position.z * .77, 'close camera pushes in strongly');
        assert.ok(camera.rotation.z >= .035 && camera.rotation.z <= .055, 'close camera tilts slightly');
        assert.ok(camera.rotation.x < -views.idle.pitch - .075, 'close camera looks down into the mouth');
        if (width === 390) {
          const left = new THREE.Vector3(-1.58, 1.044, -.073).project(camera);
          const right = new THREE.Vector3(1.58, 1.044, -.073).project(camera);
          assert.ok((right.x - left.x) / 2 >= .90, 'mouth nearly fills the mobile width');
        } else {
          assert.ok((max.y - min.y) / 2 >= .69, 'close shot fills most of the desktop height');
        }
      }
      assert.ok(time - lastChange <= .5, `No visible flap, seal or letter movement for 0.5s by ${time}s`);
      if (Math.abs(flap.rotation.x - pose[0]) >= .035 || Math.abs(seal.scale.x - pose[1]) >= .04 ||
          Math.abs(letter.position.y - pose[2]) >= .025) {
        lastChange = time;
        pose = [flap.rotation.x, seal.scale.x, letter.position.y];
      }
      if (time >= burstTime) {
        const age = time - burstTime;
        const spread = .14 + 1.05 * age, depth = .14 + .25 * age;
        for (const x of [-spread, spread]) {
          for (const y of [.91 + .7 * age - .6 * age ** 2, 1.19 + 2.42 * age - .6 * age ** 2]) {
            for (const z of [.15 - depth, .15 + depth]) {
              const point = new THREE.Vector3(x, y, z).project(camera);
              assert.ok(Math.abs(point.x) < 1 && Math.abs(point.y) < 1, `Burst clips at ${time}s in ${width}×${height}`);
            }
          }
        }
      }
    }
    assert.ok(camera.position.distanceTo(views.wide.position) < .0001, 'wide shot settles before the message');
    assert.equal(camera.rotation.z, 0);
    assert.equal(camera.fov, views.wide.fov);
    assert.ok(letter.position.y > 1.2, 'fit includes the fully risen letter');
    letter.visible = false;
    for (let t = 0; t <= .8; t += .08) {
      poseRecedingEnvelope(root, t);
      const { min, max } = projectedBounds(root, camera, THREE);
      assert.ok(min.x > -1 && max.x < 1 && min.y > -1 && max.y < 1, 'receding envelope fits behind the greeting');
    }
    letter.visible = true;
    mixer.setTime(burstTime);
    const flapAtBurst = flap.rotation.x;
    assert.ok(flapAtBurst < -2.4 && letter.position.y < .001);
    mixer.setTime(burstTime + .12);
    assert.ok(flap.rotation.x < flapAtBurst - .07, 'burst overlaps the end of the flap swing');
    mixer.setTime(burstTime + .38);
    assert.ok(letter.position.y > .015, 'the letter rises during the burst');
    action.reset().play();
    mixer.setTime(0);
    poseOpeningCamera(camera, views, 0, burstTime);
    assert.deepEqual([...camera.matrixWorld.elements, ...camera.projectionMatrix.elements], idleCamera);
    for (let t = 0; t < 100; t += .2) {
      poseIdle(root, t);
      const { min, max } = projectedBounds(root, camera, THREE);
      assert.ok(min.x > -1 && max.x < 1 && min.y > -1 && max.y < 1, 'idle tilt fits');
      assert.ok((1 - min.y) * height / 2 <= stage.top + stage.height - 3, 'idle tilt clears the button row');
    }
    poseIdle(root, 0);
  }
});
