import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { greeting } from '../src/christmas-card/config.js';
import { codePointCount, decryptGreeting, encodeGreeting, fragmentLimit, greetingLimits, passwordLimit, readGreetingFragment } from '../src/christmas-card/greeting-link.js';

const layouts = [
  [{ left: 0, top: 0, width: 390, height: 844 }, { left: 16, top: 126, width: 358, height: 622 }],
  [{ left: 0, top: 0, width: 1440, height: 900 }, { left: 340, top: 154, width: 760, height: 694 }],
  [{ left: 0, top: 0, width: 1366, height: 657 }, { left: 303, top: 115, width: 760, height: 490 }],
];

const sharedGreeting = {to:'小美 🧑‍🎄',msg:'圣诞快乐 🎄\n\nLove + joy & peace = 🌟 #2026',from:'阿林 💛',lang:'zh'};
const decodeGreeting = fragment => readGreetingFragment(fragment).greeting;
const fragmentFromBytes = bytes => '#e=' + Buffer.from(bytes).toString('base64url');

test('encrypted links round-trip Chinese, emoji, newlines and URL metacharacters without readable fields', async () => {
  for (const password of ['', '雪🧤 a separate phrase']) {
    const fragment = await encodeGreeting(sharedGreeting, password);
    assert.match(fragment, /^#e=[\w-]+$/);
    const link = readGreetingFragment(fragment);
    assert.equal(link.passwordRequired, Boolean(password));
    assert.equal(link.headerLength - 14, password ? 16 : 32, 'protected links carry a salt instead of a key');
    assert.deepEqual(await decryptGreeting(link, password), sharedGreeting);
    const bytes = Buffer.from(link.packet);
    for (const value of [sharedGreeting.to,sharedGreeting.msg,sharedGreeting.from,'"lang"',password].filter(Boolean)) {
      assert.equal(bytes.includes(value), false);
      assert.equal(fragment.includes(encodeURIComponent(value)), false);
    }
    const second = readGreetingFragment(await encodeGreeting(sharedGreeting, password));
    assert.notDeepEqual(second.packet.subarray(2,14), link.packet.subarray(2,14), 'fresh IV');
    assert.notDeepEqual(second.packet.subarray(14,link.headerLength), link.packet.subarray(14,link.headerLength), 'fresh key or salt');
  }
});

test('encrypted links reject tampering, garbage, and wrong passwords', async () => {
  const fragment = await encodeGreeting(sharedGreeting);
  const {packet} = readGreetingFragment(fragment);
  for (const index of [2, 14, packet.length - 1]) {
    const modified = packet.slice();
    modified[index] ^= 1;
    await assert.rejects(decryptGreeting(readGreetingFragment(fragmentFromBytes(modified))), {name:'OperationError'});
  }
  const unknown = packet.slice();
  unknown[0]++;
  for (const invalid of ['#broken', '#e=', '#e=ab!c', '#e=A', '#e=AQ', fragment+'=', fragment+'&to=Injected',
    fragmentFromBytes(unknown), '#e='+'a'.repeat(fragmentLimit)]) {
    assert.throws(() => readGreetingFragment(invalid));
  }
  const password = 'correct horse 🎄';
  const protectedLink = readGreetingFragment(await encodeGreeting(sharedGreeting, password));
  await assert.rejects(decryptGreeting(protectedLink));
  await assert.rejects(decryptGreeting(protectedLink, 'wrong horse 🎄'), {name:'OperationError'});
  await assert.rejects(encodeGreeting(sharedGreeting, 'x'.repeat(passwordLimit+1)));
  const damaged = protectedLink.packet.slice();
  damaged[damaged.length - 1] ^= 1;
  await assert.rejects(decryptGreeting(readGreetingFragment(fragmentFromBytes(damaged)), password), {name:'OperationError'});
  assert.deepEqual(await decryptGreeting(protectedLink, password), sharedGreeting);
});

test('old plain links still decode Chinese, emoji, newlines and URL metacharacters', () => {
  assert.deepEqual(decodeGreeting('#'+new URLSearchParams(sharedGreeting)), sharedGreeting);
  assert.deepEqual(decodeGreeting('#lang=en'),{to:'',msg:'',from:'',lang:'en'});
});

test('greeting fragments enforce decoded code-point, line, and raw length limits', async () => {
  const {to,msg,from,lines}=greetingLimits;
  const oversized = {to:'🎅'.repeat(to+1),msg:'🌟'.repeat(msg+1),from:'送'.repeat(from+1),lang:'en'};
  const fragment = new URLSearchParams(oversized);
  const limited = decodeGreeting('#'+fragment);
  assert.deepEqual(await decryptGreeting(readGreetingFragment(await encodeGreeting(oversized))), limited);
  assert.equal(codePointCount(limited.to),to);
  assert.equal(codePointCount(limited.msg),msg);
  assert.equal(codePointCount(limited.from),from);
  assert.equal(limited.to,'🎅'.repeat(40));
  assert.equal(decodeGreeting('#msg=一%0A二%0A三%0A四%0A五%0A六%0A七').msg.split('\n').length,lines);
  assert.throws(() => decodeGreeting('#to='+'a'.repeat(fragmentLimit)));
  assert.equal(decodeGreeting('#to='+'a'.repeat(fragmentLimit-3)).to,'a'.repeat(to));
});

test('greeting fragments remove controls and tolerate broken escapes and unknown fields', () => {
  assert.deepEqual(decodeGreeting('#to=A%00%09%1FB%E2%80%AE%0AC&msg=X%0D%0AY%E2%80%A8Z%ZZ%&from=%E2%81%A7ok&lang=fr'),
    {to:'AB C',msg:'X\nY\nZ%ZZ%',from:'ok',lang:undefined});
  assert.equal(decodeGreeting('#msg=%E0%A4%A').msg,'�%A');
  assert.equal(decodeGreeting('#x=ignored&msg=%3Cimg+onerror%3Dx%3E&msg=duplicate').msg,'<img onerror=x>');
});

test('address wrapping keeps whole emoji and breaks a name with no spaces', async () => {
  const {wrapAddress}=await import('../src/christmas-card/fit-copy.js');
  assert.deepEqual(wrapAddress('one two three', codePointCount, 7),['one two','three']);
  const name='最长'.repeat(20);
  const wrapped=wrapAddress(name,codePointCount,15);
  assert.deepEqual(wrapped.map(codePointCount),[15,15,10]);
  assert.equal(wrapped.join(''),name);
  assert.deepEqual(wrapAddress('🧑‍🎄🧑‍🎄', codePointCount, 3),['🧑‍🎄','🧑‍🎄']);
});

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
  for (const name of ['Flap', 'Letter', 'RibbonBow', 'RibbonPocketBand']) assert.ok(names.has(name), name);
  assert.ok(!names.has('Seal'), 'there is no seal shrink track');
  const seal = gltf.nodes.find(node => node.name === 'Seal');
  assert.equal(seal.children.filter(i => /^SealShard[1-5]$/.test(gltf.nodes[i].name)).length, 5);
  assert.equal(seal.extras.crackRays.length, 10);
  const flap = gltf.nodes.find(node => node.name === 'Flap');
  assert.ok(gltf.meshes[flap.mesh].primitives.some(p => gltf.materials[p.material].name === 'WarmLining'));
  const bow = gltf.nodes.findIndex(node => node.name === 'RibbonBow');
  const envelope = gltf.nodes.find(node => node.name === 'Envelope');
  const pocketBand = gltf.nodes.findIndex(node => node.name === 'RibbonPocketBand');
  assert.ok([bow, pocketBand].every(node => envelope.children.includes(node)), 'both ribbons can fall independently of the flap');
  const vertexAccessor = gltf.meshes[gltf.nodes[bow].mesh].primitives[0].attributes.POSITION;
  const {min,max} = gltf.accessors[vertexAccessor];
  assert.ok(max[0]-min[0]>3, 'the horizontal band crosses the envelope');
  const { burstTime, sealBreakTime } = envelope.extras;
  assert.ok(0 < sealBreakTime && sealBreakTime < burstTime);
  assert.ok(gltf.meshes.find(mesh => mesh.name === 'LetterPaper').primitives[0].attributes.TEXCOORD_0 !== undefined);
});

test('the greeting reveal fits within 5.5 animation seconds including the Replay fade', async () => {
  const { handoverDuration, revealInterval, revealFade, starApproachTime } = await import('../src/christmas-card/letter.js');
  const { maxFrameDelta } = await import('../src/christmas-card/motion.js');
  const { animations } = await loadModel();
  const css = readFileSync('christmas-card/card.css', 'utf8');
  assert.equal(Number(css.match(/animation:reveal-ink (\S+)s/)[1]), revealFade);
  assert.match(css, /\[data-reveal\]:not\(\.letter-star,\[data-pending\]\)/, 'the arrival star is visible on its first frame');
  assert.ok(starApproachTime >= 4 * maxFrameDelta && starApproachTime < handoverDuration);
  for (const {lines} of Object.values(greeting)) {
    const lastReveal = (lines.length + 3) * revealInterval;
    const worst = animations[0].duration + handoverDuration + lastReveal + revealFade + 4 * maxFrameDelta;
    assert.ok(worst <= 5.5, `Replay is fully visible by ${worst}s at the maximum frame step`);
    assert.ok(revealInterval < .5);
  }
});

function audioHarness() {
  const parameter = () => ({value: 1, setValueAtTime(value) { this.value = value; }, exponentialRampToValueAtTime() {}});
  const node = () => ({connect(target) { return target; }, disconnect() {}});
  const gains = [], contexts = [], events = [];
  const session = {type: 'auto'};
  const probe = {started: 0, stopped: 0, transport: null, time: 0};
  probe.resume = context => { context.changeState('running'); return Promise.resolve(); };
  return {
    gains, contexts, events, session, probe,
    options: {
      audioSession: () => session,
      now: () => probe.time,
      schedule(run) { probe.transport = run; return 1; },
      cancel() { probe.transport = null; },
      createContext() {
        events.push(session.type);
        const context = {
          state: 'suspended', currentTime: 0, sampleRate: 48000, destination: node(),
          createGain() { const gain = parameter(); gains.push(gain); return {...node(), gain}; },
          createDynamicsCompressor() {
            return {...node(), threshold: parameter(), knee: parameter(), ratio: parameter(), attack: parameter(), release: parameter()};
          },
          createWaveShaper: node,
          createOscillator() {
            return {...node(), frequency: parameter(), start() { probe.started++; },
              stop(at) { if (at === context.currentTime) probe.stopped++; }};
          },
          createBuffer: (_channels, length) => ({length}),
          createBufferSource() {
            return {...node(), start() { events.push(`buffer:${this.buffer.length}`); }};
          },
          changeState(state) { this.state = state; this.onstatechange?.(); },
          resume() { events.push(`resume:${this.state}`); return probe.resume(this); },
          suspend() { this.changeState('suspended'); return Promise.resolve(); },
          close() { this.changeState('closed'); return Promise.resolve(); },
        };
        contexts.push(context);
        return context;
      },
    },
  };
}

test('audio waits for activation, mutes every voice, persists mute, and pauses while hidden', async () => {
  const {createCardAudio, mutePreference} = await import('../src/christmas-card/audio.js');
  const {gains, contexts, events, session, probe, options} = audioHarness();
  const preference = new Map();
  const storage = () => ({getItem: key => preference.get(key), setItem: (key, value) => preference.set(key, value)});
  const audio = createCardAudio({...options, storage});
  audio.play('sparkle');
  audio.setVisible(false);
  audio.setVisible(true);
  assert.equal(audio.status, 'waiting');
  assert.equal(contexts.length, 0);
  assert.equal(probe.started, 0);
  assert.equal(audio.activate(), true);
  assert.deepEqual(events, ['playback', 'buffer:1', 'resume:suspended']);
  const [context] = contexts;
  assert.ok(probe.started > 0 && gains[0].value > 0 && probe.transport, 'the gesture starts the music');
  assert.equal(audio.status, 'playing', 'the sound control can mute before the first clock sample');
  assert.equal(audio.diagnostics().advancing, false);
  context.currentTime = .1;
  probe.transport();
  assert.equal(audio.status, 'playing');
  audio.play('sparkle');
  const audibleVoices = probe.started;
  audio.setMuted(true);
  assert.equal(audio.status, 'muted');
  assert.equal(gains[0].value, 0, 'music and effects share the master bus');
  assert.equal(probe.stopped, audibleVoices);
  assert.equal(context.state, 'suspended');
  assert.equal(session.type, 'auto');
  assert.equal(probe.transport, null);
  assert.equal(preference.get(mutePreference), '1');
  audio.play('arrival');
  audio.testSound();
  assert.equal(probe.started, audibleVoices);
  assert.equal(createCardAudio({storage}).muted, true);
  audio.setMuted(false);
  audio.activate();
  audio.setVisible(false);
  assert.equal(context.state, 'suspended');
  assert.equal(session.type, 'auto');
  assert.equal(gains[0].value, 0);
  assert.equal(probe.transport, null);
  audio.setVisible(true);
  assert.equal(context.state, 'running');
  assert.equal(session.type, 'playback');
  assert.ok(probe.transport && gains[0].value > 0);
  const isolated = createCardAudio({storage() { throw new Error('Storage disabled'); }});
  isolated.setMuted(true);
  assert.equal(isolated.muted, true);
});

test('audio can be muted during a pending gesture resume and can be retried after suspension', async () => {
  const {createCardAudio} = await import('../src/christmas-card/audio.js');
  const {contexts, gains, probe, options} = audioHarness();
  const runResume = probe.resume;
  let finishResume;
  probe.resume = () => new Promise(resolve => { finishResume = resolve; });
  const audio = createCardAudio(options);
  audio.activate();
  assert.equal(contexts[0].state, 'suspended');
  assert.equal(audio.status, 'starting');
  audio.setMuted(true);
  finishResume();
  await Promise.resolve();
  assert.equal(audio.status, 'muted');
  assert.equal(gains[0].value, 0);

  audio.setMuted(false);
  probe.resume = runResume;
  audio.activate();
  assert.equal(audio.status, 'playing');
  contexts[0].changeState('suspended');
  assert.equal(audio.status, 'waiting');
  audio.activate();
  assert.equal(audio.status, 'playing');
  contexts[0].changeState('interrupted');
  assert.equal(audio.status, 'waiting');
});

test('audio retries interrupted playback and rebuilds a closed context or a stalled audio clock', async () => {
  const {createCardAudio} = await import('../src/christmas-card/audio.js');
  const {contexts, events, probe, options} = audioHarness();
  const audio = createCardAudio(options);
  const runResume = probe.resume;
  probe.resume = () => Promise.reject(new Error('Audio route interrupted'));
  audio.activate();
  assert.equal(audio.status, 'starting');
  await Promise.resolve();
  assert.match(audio.diagnostics().lastResumeError, /Audio route interrupted/);
  assert.equal(audio.status, 'waiting');
  contexts[0].changeState('interrupted');
  audio.activate();
  assert.equal(events.at(-1), 'resume:interrupted');
  assert.equal(contexts.length, 1);

  audio.setVisible(false);
  contexts[0].changeState('interrupted');
  probe.resume = () => new Promise(() => {});
  audio.setVisible(true);
  assert.equal(events.at(-1), 'resume:interrupted');
  probe.time += 1300;
  probe.transport();
  assert.equal(contexts[0].state, 'closed');
  assert.equal(contexts.length, 2);
  probe.time += 1300;
  probe.transport();
  assert.equal(contexts.length, 2, 'a pending resume does not start an endless rebuild loop');

  probe.resume = runResume;
  audio.activate();
  assert.equal(contexts[1].state, 'closed');
  assert.equal(contexts.length, 3);
  assert.equal(audio.status, 'playing');
  assert.equal(audio.diagnostics().advancing, false);
  contexts[2].currentTime = .1;
  probe.transport();
  assert.equal(audio.status, 'playing');
  probe.time += 1300;
  probe.transport();
  assert.equal(contexts[2].state, 'closed', 'a running context with a frozen clock is also replaced');
  assert.equal(contexts.length, 4);
  probe.time += 1300;
  probe.transport();
  assert.equal(contexts.length, 4, 'a replacement with a frozen clock does not start another rebuild');
  assert.equal(audio.status, 'playing', 'a stalled running context can still be muted');
  await contexts[3].close();
  audio.activate();
  assert.equal(contexts.length, 5);
  assert.deepEqual(events.slice(-3), ['playback', 'buffer:1', 'resume:suspended']);
});

test('card worker only activates a complete precache and removes its own old caches', async () => {
  const { runInNewContext } = await import('node:vm');
  const template = readFileSync('src/christmas-card/sw-template.js', 'utf8')
    .replace('__BUILD__', '"latest"')
    .replace('__FILES__', '["christmas-card/index.html", "christmas-card/version.json"]');
  const scope = 'https://example.test/site/christmas-card/';
  const latest = 'christmas-card:%2Fsite%2Fchristmas-card%2F:latest';
  const legacy = 'christmas-card-_site_christmas_card_ae68edfc3497';
  const gallery = 'b3g-_site_-shell-test';
  const otherScope = 'christmas-card:%2Fother%2Fchristmas-card%2F:older';
  function worker({fail = false, mismatchedShell = false, active = {}} = {}) {
    const names = new Set([legacy, gallery, otherScope]), entries = new Map();
    const handlers = {}, events = [];
    const self = {
      registration:{scope, active},
      location:new URL(scope),
      addEventListener(name, fn) { handlers[name] = fn; },
      skipWaiting: async () => { events.push('skipWaiting'); },
      clients:{
        claim: async () => { events.push('claim'); },
        matchAll: async () => [{url:scope+'?test=1#recipient', navigate: async url => { events.push(url); }}],
      },
    };
    const caches = {
      open: async name => {
        names.add(name);
        return {
          match: async url => entries.get(url.href),
          put: async (url, response) => { entries.set(url.href, response); },
          delete: async url => { entries.delete(url.href); },
        };
      },
      keys: async () => [...names],
      match: async (url, {cacheName}) => cacheName === latest && entries.get(url.href),
      delete: async name => { names.delete(name); },
    };
    const fetch = async request => {
      const url = new URL(request.url ?? request);
      events.push(url.pathname);
      return new Response(mismatchedShell ? 'old page' : '<button data-build="latest">', {
        status: fail && url.pathname.endsWith('version.json') ? 503 : 200,
      });
    };
    runInNewContext(template, {self, URL, Response, caches, fetch});
    return {
      events, names,
      run(name) {
        let completion;
        handlers[name]({waitUntil: value => { completion = value; }});
        return completion;
      },
      respond(url, mode) {
        let response;
        handlers.fetch({request:{url, mode, method:'GET'}, respondWith: value => { response = value; }});
        return response;
      },
    };
  }

  const failed = worker({fail:true});
  await assert.rejects(failed.run('install'), /Offline resource unavailable/);
  assert.deepEqual(failed.names, new Set([legacy, gallery, otherScope]));
  assert.ok(!failed.events.includes('skipWaiting'));

  const mixed = worker({mismatchedShell:true});
  await assert.rejects(mixed.run('install'), /shell changed/);
  assert.deepEqual(mixed.names, failed.names);

  const update = worker();
  await update.run('install');
  assert.deepEqual(update.events, ['/site/christmas-card/index.html', '/site/christmas-card/version.json', 'skipWaiting']);
  const concurrent = 'christmas-card:%2Fsite%2Fchristmas-card%2F:newer';
  update.names.add(concurrent);
  await update.run('activate');
  assert.deepEqual(update.names, new Set([latest, gallery, otherScope, concurrent]));
  assert.deepEqual(update.events.slice(-2), ['claim', scope+'?test=1&christmas-card-reload=latest#recipient']);
  const redirect = await update.respond(update.events.at(-1), 'navigate');
  assert.equal(redirect.headers.get('location'), scope+'?test=1#recipient');
  assert.equal((await update.respond(scope+'uncached.png', 'no-cors')).status, 200);
  assert.equal(update.events.at(-1), '/site/christmas-card/uncached.png');

  const initial = worker({active:null});
  await initial.run('install');
  await initial.run('activate');
  assert.equal(initial.events.at(-1), 'claim', 'a first install never navigates its client');
});

test('card navigations share one offline entry and the installed launch is fragment-free', async () => {
  const {runInNewContext}=await import('node:vm');
  const source=readFileSync('src/christmas-card/sw-template.js','utf8')
    .replace('__BUILD__','"test"').replace('__FILES__','[]');
  const handlers={}, keys=[];
  runInNewContext(source,{
    URL,
    self:{registration:{scope:'https://example.test/site/christmas-card/'},location:{origin:'https://example.test'},
      addEventListener(name,run){handlers[name]=run}},
    caches:{match:async(key,{cacheName})=>{keys.push([key.href,cacheName]);return 'cached'}},
  });
  for(const suffix of ['','?card-test=1#msg=private','index.html#to=another']){
    let response;
    handlers.fetch({request:{method:'GET',mode:'navigate',url:'https://example.test/site/christmas-card/'+suffix},
      respondWith(value){response=value}});
    assert.equal(await response,'cached');
  }
  assert.deepEqual(keys,Array(3).fill(['https://example.test/site/christmas-card/index.html','christmas-card:%2Fsite%2Fchristmas-card%2F:test']));
  const manifest=JSON.parse(readFileSync('public/christmas-card/manifest.webmanifest','utf8'));
  assert.equal(manifest.start_url,'./');
});

test('the playback step stays bounded after a stalled or reactivated frame', async () => {
  const { frameDelta } = await import('../src/christmas-card/motion.js');
  assert.equal(frameDelta(1500, null), 0);
  assert.equal(frameDelta(1500, 1484), .016);
  assert.equal(frameDelta(1500, 400), 1 / 30);
});

test('software rendering caps large buffers and batches the closed seal and entrance trail', async () => {
  const THREE = await import('three');
  const { cardPixelRatio, softwareRendering } = await import('../src/christmas-card/raster.js');
  const { createEntranceTrail } = await import('../src/christmas-card/accents.js');
  const { createStardust } = await import('../src/christmas-card/magic.js');
  const { createSealEffect } = await import('../src/christmas-card/seal.js');
  const { frameEnvelope } = await import('../src/christmas-card/framing.js');
  const { createEntranceFlight } = await import('../src/christmas-card/motion.js');
  const software = softwareRendering({getContext: () => ({
    getExtension: () => ({UNMASKED_RENDERER_WEBGL: 1}),
    getParameter: () => 'ANGLE (Google, Vulkan, SwiftShader Device (Subzero))',
  })});
  assert.equal(software, true);
  const ratio = cardPixelRatio(1440, 900, 1, software);
  assert.ok(Math.floor(1440 * ratio) * Math.floor(900 * ratio) <= 860_000);
  assert.equal(cardPixelRatio(390, 844, 1, software), 1);
  assert.equal(cardPixelRatio(1440, 900, 2, false), 2);
  assert.equal(cardPixelRatio(1440, 900, 1, false), 1);

  const {scene: root} = await loadModel();
  const scene = new THREE.Scene();
  scene.add(root);
  const seal = root.getObjectByName('Seal');
  const breakTime = root.getObjectByName('Envelope').userData.sealBreakTime;
  const dust = createStardust(scene);
  const effect = createSealEffect(seal, scene, breakTime, dust);
  const assembled = seal.getObjectByName('AssembledSeal');
  assert.equal(assembled.children.length, 4);
  const drawTrail = createEntranceTrail(dust.createEntranceBatch());
  const [viewport, stage] = layouts[1];
  const camera = new THREE.PerspectiveCamera();
  frameEnvelope(camera, viewport, stage);
  drawTrail(1.66, createEntranceFlight(root, camera, viewport.width));
  const trail = scene.getObjectByName('EntranceStardust');
  assert.ok(trail.isPoints && trail.visible);
  assert.equal(trail.geometry.drawRange.count, 44);
  assert.equal(trail.material, scene.getObjectByName('Stardust').material);
  effect.update(breakTime);
  assert.equal(assembled.visible, false);
  const pieces = scene.children.filter(piece => /^SealShard\d+$/.test(piece.name));
  assert.equal(pieces.reduce((count, piece) => count + piece.children.length, 0), 12);
});

test('warm-up releases playback when compileAsync stays pending and ignores its late completion', {timeout:1000}, async () => {
  const { warmWithinBudget } = await import('../src/christmas-card/warmup.js');
  let completeCompile, draws = 0;
  const renderer = {extensions:{has:()=>true}, compileAsync: () => new Promise(resolve => { completeCompile = resolve; }) };
  await warmWithinBudget(renderer, null, null, [() => { draws++; }], 35);
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
  const renderer = {extensions:{has:()=>true}, compileAsync: async () => { calls.push('compile'); }, getContext: () => gl };
  await warmWithinBudget(renderer, null, null, [() => calls.push('draw')], 180);
  assert.deepEqual(calls.slice(0, 5), ['compile', 'draw', 'fence', 'flush', 'poll']);
  assert.equal(calls.at(-1), 'delete');
  await new Promise(resolve => setTimeout(resolve, 24));
  assert.equal(calls.at(-1), 'delete', 'no further polling after the deadline');
});

test('warm-up submits draws on successive frames without parallel shader compilation', {timeout:1000}, async t => {
  const { warmWithinBudget } = await import('../src/christmas-card/warmup.js');
  const calls = [];
  globalThis.requestAnimationFrame = run => setImmediate(() => { calls.push('frame'); run(); });
  globalThis.cancelAnimationFrame = clearImmediate;
  t.after(() => { delete globalThis.requestAnimationFrame; delete globalThis.cancelAnimationFrame; });
  const renderer = {
    extensions: {has: name => {
      assert.equal(name, 'KHR_parallel_shader_compile');
      return false;
    }},
    compileAsync: () => assert.fail('Unsupported parallel compilation'),
    getContext: () => ({fenceSync: () => { calls.push('fence'); return null; }}),
  };
  await warmWithinBudget(renderer, null, null, [() => calls.push('address'), () => calls.push('burst')]);
  assert.deepEqual(calls, ['address', 'frame', 'burst', 'fence']);
  globalThis.requestAnimationFrame = () => 17;
  globalThis.cancelAnimationFrame = id => calls.push(id);
  await warmWithinBudget(renderer, null, null, [() => calls.push('address'), () => assert.fail('No next frame')], 35);
  assert.deepEqual(calls.slice(-2), ['address', 17], 'The same deadline cancels a pending draw');
});

test('the small off-screen envelope grows, loops once, and holds its address side in view', async () => {
  const THREE = await import('three');
  const { frameEnvelope, poseLandingCamera, setCameraPose } = await import('../src/christmas-card/framing.js');
  const { createEntranceFlight, entranceDuration, loopStart, loopEnd, poseEntrance } = await import('../src/christmas-card/motion.js');
  const { createBoundsRecorder } = await import('../src/christmas-card/recording.js');
  const recordBounds = createBoundsRecorder();
  const { scene: root } = await loadModel();
  for (const [viewport, stage] of layouts) {
    const camera = new THREE.PerspectiveCamera();
    const views = frameEnvelope(camera, viewport, stage);
    setCameraPose(camera, views.entrance);
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
      setCameraPose(camera, views.entrance);
      const prior = root.position.clone().project(camera);
      poseLandingCamera(camera, views, root.position, t);
      const after = root.position.clone().project(camera);
      assert.ok(Math.hypot(prior.x-after.x, prior.y-after.y) < 1e-8, 'landing keeps the original screen path');
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
    setCameraPose(camera, views.entrance);
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
    const sample = recordBounds(root, camera, viewport);
    assert.ok(Math.abs(sample.left - (settled.min.x + 1)*viewport.width/2) < 1e-8);
    assert.ok(Math.abs(sample.right - (settled.max.x + 1)*viewport.width/2) < 1e-8);
    assert.ok(Math.abs(sample.top - (1 - settled.max.y)*viewport.height/2) < 1e-8);
    assert.ok(Math.abs(sample.bottom - (1 - settled.min.y)*viewport.height/2) < 1e-8);
    assert.ok(first.max.x - first.min.x < (settled.max.x - settled.min.x) * .42);
    assert.ok(root.position.length() < .0001 && root.rotation.y === 0, 'the seal side settles at idle');
    setCameraPose(camera, views.idle);
    const idle = projectedBounds(root, camera, THREE);
    if (viewport.width === 390) assert.ok(idle.max.x-idle.min.x <= (settled.max.x-settled.min.x)*.83, 'mobile rest is visibly smaller');
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
  const { createLetterFlight, handoverDuration } = await import('../src/christmas-card/letter.js');
  const { createMouthLight, createStardust, particleLimit } = await import('../src/christmas-card/magic.js');
  const { createRibbonEffect } = await import('../src/christmas-card/ribbon.js');
  const { createSealEffect } = await import('../src/christmas-card/seal.js');
  const gltf = await loadModel();
  const root = gltf.scene, mixer = new THREE.AnimationMixer(root), action = mixer.clipAction(gltf.animations[0]);
  const scene = new THREE.Scene();
  scene.add(root);
  action.setLoop(THREE.LoopOnce, 1); action.clampWhenFinished=true; action.play();
  root.updateMatrixWorld(true);
  const ray = new THREE.Raycaster(new THREE.Vector3(1.37, 0, 5), new THREE.Vector3(0, 0, -1));
  const hits = ray.intersectObject(root, true);
  const foldBack = hits.filter(hit => hit.object.name === 'PocketRight').at(-1).point.z;
  const borderFront = hits.find(hit => hit.object.name === 'LetterBorder').point.z;
  assert.ok(foldBack - borderFront > .004, `Letter border must clear the fold, got ${foldBack-borderFront}`);
  const flap = root.getObjectByName('Flap');
  const seal = root.getObjectByName('Seal');
  const bow = root.getObjectByName('RibbonBow');
  const pocketBand = root.getObjectByName('RibbonPocketBand');
  const ribbons = [bow, pocketBand];
  const updateRibbons = createRibbonEffect(root);
  const shards = seal.children.filter(part => /^SealShard\d+$/.test(part.name));
  const bowBox = new THREE.Box3(), bandBox = new THREE.Box3(), shardBox = new THREE.Box3();
  assert.ok(bowBox.setFromObject(bow,true).min.z>0 && bandBox.setFromObject(pocketBand,true).min.z>0,
    'both ribbons sit on the front, with the address side clear');
  const letter = root.getObjectByName('Letter');
  const { burstTime, sealBreakTime } = root.getObjectByName('Envelope').userData;
  for (const ribbon of ribbons) {
    const [start, end] = ribbon.userData.releaseFade;
    assert.ok(start > sealBreakTime && end > start && end < burstTime, `${ribbon.name} fades between the seal break and burst`);
    updateRibbons((start + end) / 2);
    assert.ok(ribbon.visible && Math.abs(ribbon.material.opacity - .5) < 1e-8, `${ribbon.name} fades while still visible`);
  }
  updateRibbons(0);
  const dust = createStardust(scene);
  const mouthLight = createMouthLight(scene);
  let scattered = 0;
  const sealEffect = createSealEffect(seal, scene, sealBreakTime, {
    scatter(origin) { scattered++; dust.scatter(origin); },
  });
  const letterFlight = createLetterFlight(letter, scene);
  const hinge = flap.position.clone();
  for (const [viewport, stage] of layouts) {
    const { width, height } = viewport;
    const camera = new THREE.PerspectiveCamera();
    const views = frameEnvelope(camera, viewport, stage);
    const idleCamera = [...camera.matrixWorld.elements, ...camera.projectionMatrix.elements];
    const previousCamera = camera.position.clone();
    let previousPitch = camera.rotation.x, previousRoll = camera.rotation.z, previousFov = camera.fov;
    action.reset().play();
    sealEffect.reset();
    dust.clear();
    scattered = 0;
    const end = action.getClip().duration - .0001;
    let lastChange = 0, pose = [0, 0, 0], burst = false;
    for (let i = 0; i <= Math.ceil(end * 30); i++) {
      const time = Math.min(i / 30, end);
      mixer.setTime(time);
      sealEffect.update(time);
      updateRibbons(time);
      if (!burst && time >= burstTime) {
        burst = true;
        dust.mouth(root.localToWorld(new THREE.Vector3(0, 1.055, .26)));
      }
      dust.update(1 / 30);
      const closeAmount = poseOpeningCamera(camera, views, time, burstTime);
      mouthLight(root, THREE.MathUtils.smoothstep(-flap.rotation.x, .24, 1.75), closeAmount);
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
      const effects = projectedBounds(scene, camera, THREE);
      assert.ok(effects.min.x > -1 && effects.max.x < 1 && effects.min.y > -1 && effects.max.y < 1,
        `Glow or seal clipped at ${time}s in ${width}×${height}`);
      const letterBounds = projectedBounds(letter, camera, THREE);
      assert.ok((1 - letterBounds.max.y) * height / 2 > stage.top,
        `Rising letter must stay below the header at ${time}s in ${width}×${height}`);
      bowBox.setFromObject(bow, true);
      bandBox.setFromObject(pocketBand, true);
      for (const shard of shards.filter(part => part.visible)) {
        shard.updateWorldMatrix(true, true);
        shardBox.setFromObject(shard,true);
        assert.ok(!bowBox.intersectsBox(shardBox) && !bandBox.intersectsBox(shardBox), `Ribbon and ${shard.name} intersect at ${time}s`);
      }
      assert.deepEqual(flap.position.toArray(), hinge.toArray());
      if (i === 0) {
        if (width === 390) assert.ok((max.x - min.x) / 2 >= .67 && (max.x - min.x) / 2 <= .75);
        if (width === 1440) assert.ok((max.y - min.y) * height / 2 >= height * .45);
      }
      const sealState = sealEffect.measure();
      if (i === 9) assert.ok(sealState.progress > .5 && !sealState.separated, 'golden cracks spread ahead of the break');
      if (i === 16) assert.ok(sealState.separated && sealState.visible === 5, 'all five real shards detach');
      if (i === 21) assert.ok(flap.rotation.x < -.15, 'the flap follows the seal break');
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
      if (Math.abs(flap.rotation.x - pose[0]) >= .035 || Math.abs(sealState.progress - pose[1]) >= .04 ||
          Math.abs(letter.position.y - pose[2]) >= .025) {
        lastChange = time;
        pose = [flap.rotation.x, sealState.progress, letter.position.y];
      }
      const motes = dust.measure(camera, viewport);
      assert.ok(motes.length <= particleLimit);
      for (const {x, y, radius} of motes) {
        assert.ok(x-radius >= 0 && x+radius < width && y-radius >= 0 && y+radius < height,
          `Stardust clips at ${time}s in ${width}×${height}`);
      }
    }
    assert.ok(camera.position.distanceTo(views.wide.position) < .0001, 'wide shot settles before the message');
    assert.equal(camera.rotation.z, 0);
    assert.equal(camera.fov, views.wide.fov);
    assert.ok(letter.position.y > 2.1, 'fit includes the fully extracted letter');
    assert.ok(ribbons.every(ribbon => !ribbon.visible), 'Both pieces finish fading before the letter lifts clear');
    assert.equal(sealEffect.measure().visible, 0);
    assert.equal(scattered, 10, 'each shard dissolves into two groups of stardust');
    const before = letterFlight.project(camera, viewport);
    letterFlight.begin();
    const distance = (a, b) => Math.max(...Object.keys(a).map(edge => Math.abs(a[edge] - b[edge])));
    let previous = letterFlight.pose(camera, viewport, stage, 0);
    assert.ok(distance(before, previous) < .001, 'the same paper starts its flight in its last lifted position');
    for (let t = 1 / 30; t < handoverDuration; t += 1 / 30) {
      poseRecedingEnvelope(root, t);
      const rect = letterFlight.pose(camera, viewport, stage, t);
      assert.ok(rect.left > 0 && rect.top > 0 && rect.right < width && rect.bottom < height, 'the flying paper stays visible');
      assert.ok(rect.top > stage.top, 'the flying paper clears the header');
      assert.ok(distance(previous, rect) < 21, 'the flying edges advance continuously');
      previous = rect;
      const { min, max } = projectedBounds(root, camera, THREE);
      assert.ok(min.x > -1 && max.x < 1 && min.y > -1 && max.y < 1, 'receding envelope fits behind the greeting');
    }
    const landing = letterFlight.pose(camera, viewport, stage, handoverDuration);
    assert.ok(distance(previous, landing) < .25, 'the last flying frame aligns with the readable paper');
    assert.ok(distance(landing, letterFlight.project(camera, viewport)) < .001, 'the paper remains in place under the HTML');
    for (let t=0;t<=handoverDuration;t+=1/30) {
      const custom=letterFlight.pose(camera, viewport, stage, t, 446);
      assert.ok(custom.top>stage.top&&custom.bottom<stage.top+stage.height,'the taller custom paper clears the controls');
    }
    assert.ok(ribbons.every(ribbon => !ribbon.visible), 'The pieces stay hidden through the handover');
    action.stop();
    updateRibbons(0);
    for (const ribbon of ribbons) {
      assert.ok(ribbon.visible && ribbon.material.opacity === 1, `${ribbon.name} restores for Replay`);
      assert.deepEqual(ribbon.quaternion.toArray(), [0, 0, 0, 1]);
    }
    letterFlight.reset();
    sealEffect.reset();
    poseIdle(root, 0);
    action.reset().play();
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
