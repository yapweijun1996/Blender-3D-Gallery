import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { greeting } from '../src/christmas-card/config.js';

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

test('model layers remain separated and framing fits the complete opening', async () => {
  const THREE = await import('three');
  const { GLTFLoader } = await import('three/addons/loaders/GLTFLoader.js');
  const { frameEnvelope } = await import('../src/christmas-card/framing.js');
  const bytes = readFileSync('models/christmas-envelope/envelope.glb');
  const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
  const root = gltf.scene, mixer = new THREE.AnimationMixer(root), action = mixer.clipAction(gltf.animations[0]);
  action.setLoop(THREE.LoopOnce, 1); action.clampWhenFinished=true; action.play();
  root.updateMatrixWorld(true);
  const ray = new THREE.Raycaster(new THREE.Vector3(1.37, 0, 5), new THREE.Vector3(0, 0, -1));
  const hits = ray.intersectObject(root, true);
  const foldBack = hits.filter(hit => hit.object.name === 'PocketRight').at(-1).point.z;
  const borderFront = hits.find(hit => hit.object.name === 'LetterBorder').point.z;
  assert.ok(foldBack - borderFront > .004, `Letter border must clear the fold, got ${foldBack-borderFront}`);
  let latestLetterStart = 0;
  for (let i=0; i<=112; i++) {
    const time = Math.min(i/24, action.getClip().duration-.0001);
    mixer.setTime(time); root.updateMatrixWorld(true);
    const flap=root.getObjectByName('Flap');
    const joinedEdge=flap.localToWorld(new THREE.Vector3(0,0,.083));
    assert.ok(Math.abs(joinedEdge.y-1.05)<.001, `Flap edge detached at ${time}s: ${joinedEdge.y}`);
    const box = new THREE.Box3().setFromObject(root), size=box.getSize(new THREE.Vector3());
    for (const [w,h] of [[358,600],[760,680]]) {
      const fit=frameEnvelope(w,h,3.2,{width:size.x,height:size.y+.08,minY:box.min.y-.04,maxY:box.max.y+.04});
      assert.ok(size.x*fit.scale<=w*.961 && size.y*fit.scale<h, `Clipped at ${time}s`);
      if (i===0 || i===34) {
        if (w===358) assert.ok(3.2*fit.scale>=390*.85);
        else assert.ok(2.1*fit.scale>=900*.45);
      }
    }
    if(root.getObjectByName('Letter').position.y<.001) latestLetterStart=time;
  }
  assert.ok(latestLetterStart>2.8, 'letter should remain down until after the burst');
  mixer.setTime(64/24); root.updateMatrixWorld(true);
  assert.ok(root.getObjectByName('Flap').rotation.x < -3, 'flap is open when the burst begins');
});
