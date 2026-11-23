// "What is RAG?" explainer built with three.js (r170).
// Fully deterministic: everything is a pure function of time, so render.mjs can step frames exactly.
import * as THREE from './vendor/three.module.min.js';

export const DURATION = 28;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const smooth = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const lerp = (a, b, k) => a + (b - a) * k;
const backOut = (x) => { x = clamp(x); const c = 1.70158; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
// Piecewise smooth interpolation of scalars or arrays through [time, value] keys.
function track(t, keys) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (t <= keys[i][0]) {
      const [t0, a] = keys[i - 1], [t1, b] = keys[i], k = smooth((t - t0) / (t1 - t0));
      return Array.isArray(a) ? a.map((v, j) => lerp(v, b[j], k)) : lerp(a, b, k);
    }
  }
  return keys.at(-1)[1];
}
// 0 before `start`, pops to 1 with overshoot, and back to 0 after `end` (if given).
const appear = (t, start, end = Infinity, dur = 0.5) =>
  t < start ? 0 : t < end ? backOut((t - start) / dur) : 1 - smooth((t - end) / 0.35);

const COL = { bg: 0x070b18, accent: 0x38d0ff, violet: 0x8a5cff, amber: 0xffa63a, green: 0x35d07f, paper: 0xe9edf6, ink: '#101426' };
const X = { user: -10, retrieve: -4.5, augment: 0.5, generate: 5.5, answer: 10.5 };

function textTexture(lines, { size = 64, color = '#ffffff', bg = null, pad = 28, align = 'center', weight = 700, radius = 28, minW = 0 } = {}) {
  const font = `${weight} ${size}px "Helvetica Neue", Helvetica, Arial, sans-serif`;
  const probe = document.createElement('canvas').getContext('2d');
  probe.font = font;
  const lh = size * 1.25;
  const w = Math.max(minW, Math.ceil(Math.max(...lines.map((l) => probe.measureText(l).width))) + pad * 2);
  const h = Math.ceil(lines.length * lh + pad * 2);
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d');
  if (bg) { g.fillStyle = bg; g.beginPath(); g.roundRect(0, 0, w, h, radius); g.fill(); }
  g.font = font; g.fillStyle = color; g.textBaseline = 'middle';
  g.textAlign = align;
  lines.forEach((l, i) => g.fillText(l, align === 'center' ? w / 2 : pad, pad + lh * (i + 0.5)));
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  return { tex, aspect: w / h };
}
// A plane showing text; `height` is the world height of the plane.
function label(lines, height, opts = {}) {
  const { tex, aspect } = textTexture(Array.isArray(lines) ? lines : [lines], opts);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(height * aspect, height), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, toneMapped: false }));
  return m;
}
const std = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.45, metalness: 0.1, ...extra });
const shadowOn = (o) => { o.traverse((m) => { if (m.isMesh && m.material.map == null) { m.castShadow = true; m.receiveShadow = true; } }); return o; };

export function createScene(canvas, width, height) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(width, height, false);
  renderer.setPixelRatio(1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(COL.bg);
  scene.fog = new THREE.Fog(COL.bg, 22, 60);
  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 200);

  scene.add(new THREE.HemisphereLight(0x8fb4ff, 0x141a30, 0.9));
  const sun = new THREE.DirectionalLight(0xffffff, 2.4);
  sun.position.set(-6, 12, 10);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -22, right: 22, top: 10, bottom: -10, near: 1, far: 40 });
  sun.shadow.bias = -0.0005;
  scene.add(sun);
  const glow = new THREE.PointLight(COL.violet, 0, 14);
  glow.position.set(X.generate, 2, 2.5);
  scene.add(glow);

  // Floor with a faint grid, plus drifting dust for depth.
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(80, 40), std(0x0e1426, { roughness: 0.9 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true;
  scene.add(floor);
  const grid = new THREE.GridHelper(80, 80, 0x1c2a52, 0x141d3a);
  grid.position.y = 0.01; scene.add(grid);
  const dustN = 260, dustPos = new Float32Array(dustN * 3), dustSeed = [];
  for (let i = 0; i < dustN; i++) { dustSeed.push([Math.random(), Math.random(), Math.random()]); }
  const dustGeo = new THREE.BufferGeometry();
  dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
  const dust = new THREE.Points(dustGeo, new THREE.PointsMaterial({ color: 0x6f8cff, size: 0.07, transparent: true, opacity: 0.55, depthWrite: false }));
  scene.add(dust);
  // Seeded pseudo-random so the dust is identical on every render.
  let s = 7; const rnd = () => (s = (s * 16807) % 2147483647) / 2147483647;
  dustSeed.forEach((d, i) => { d[0] = rnd(); d[1] = rnd(); d[2] = rnd(); });

  // Conveyor tracks between stations.
  const flow = new THREE.Group(); scene.add(flow);
  const seg = [[-8.4, -6.4], [-2.5, -1.2], [2.6, 3.9], [7.4, 8.9]];
  const arrows = seg.map(([a, b]) => {
    const bar = new THREE.Mesh(new THREE.BoxGeometry(b - a, 0.05, 0.14), std(0x24335f, { emissive: 0x112042 }));
    bar.position.set((a + b) / 2, 0.04, 1.6); flow.add(bar);
    const head = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.4, 20), std(COL.accent, { emissive: COL.accent, emissiveIntensity: 0.5 }));
    head.rotation.z = -Math.PI / 2; head.position.set(b + 0.12, 0.06, 1.6); flow.add(head);
    return head;
  });

  // Headings (always visible) with their subtitles.
  const heads = {};
  const addHead = (key, title, sub) => {
    const g = new THREE.Group();
    const a = label(title, 0.55, { size: 80, color: '#38d0ff' }); a.position.y = 0.3;
    const b = label(sub, 0.3, { size: 56, color: '#9aa7c7', weight: 500 }); b.position.y = -0.2;
    g.add(a, b); g.position.set(X[key], 3.7, 0); scene.add(g); heads[key] = g;
  };
  addHead('user', 'QUESTION', 'user asks');
  addHead('retrieve', '1. RETRIEVE', 'search the knowledge base');
  addHead('augment', '2. AUGMENT', 'question + context');
  addHead('generate', '3. GENERATE', 'the LLM writes the answer');
  addHead('answer', 'ANSWER', 'grounded, with a source');

  // Title and recap.
  const title = label('What is RAG?', 2.0, { size: 140, color: '#ffffff' }); title.position.set(0, 7.2, 0); scene.add(title);
  const subtitle = label('Retrieval-Augmented Generation', 0.95, { size: 90, color: '#38d0ff', weight: 500 }); subtitle.position.set(0, 5.5, 0); scene.add(subtitle);
  const recap = label('Retrieve  →  Augment  →  Generate', 1.2, { size: 100, color: '#38d0ff' }); recap.position.set(0, 6.4, 0); scene.add(recap);

  // Person with speech bubble.
  const person = new THREE.Group();
  const pBody = new THREE.Mesh(new THREE.CapsuleGeometry(0.38, 0.6, 8, 24), std(0x3c6df0));
  pBody.position.y = 0.7;
  const pHead = new THREE.Mesh(new THREE.SphereGeometry(0.3, 32, 24), std(0xf0c9a0));
  pHead.position.y = 1.6;
  person.add(pBody, pHead); person.position.set(X.user, 0, 0.6); scene.add(shadowOn(person));
  const bubble = label(['What is our', 'refund policy?'], 1.1, { size: 72, color: COL.ink, bg: '#e9edf6', pad: 36, radius: 40, weight: 700 });
  bubble.position.set(X.user, 3.0, 0.3); scene.add(bubble);

  // Knowledge base: shelf with 12 document chunks.
  const kb = new THREE.Group(); kb.position.set(X.retrieve, 0, -0.5); scene.add(kb);
  const shelf = new THREE.Mesh(new THREE.BoxGeometry(4.1, 3.0, 0.2), std(0x1c2547));
  shelf.position.set(0, 1.75, -0.2); kb.add(shelf);
  const HITS = [6, 7, 11];
  const docs = [];
  for (let n = 1; n <= 12; n++) {
    const col = (n - 1) % 4, row = Math.floor((n - 1) / 4);
    const mat = std(0xd7dcec, { emissive: COL.amber, emissiveIntensity: 0 });
    const card = new THREE.Mesh(new THREE.BoxGeometry(0.78, 0.92, 0.06), mat);
    const num = label(`#${n}`, 0.26, { size: 64, color: COL.ink, pad: 6 });
    num.position.z = 0.04; card.add(num);
    const home = new THREE.Vector3(-1.35 + col * 0.9, 2.75 - row * 1.05, 0.0);
    card.position.copy(home); kb.add(card);
    docs.push({ n, card, home, mat, hit: HITS.includes(n) });
  }
  kb.updateMatrixWorld(true);
  const scan = new THREE.Mesh(new THREE.PlaneGeometry(0.08, 3.1), new THREE.MeshBasicMaterial({ color: COL.accent, transparent: true, opacity: 0.85 }));
  scan.position.set(0, 1.75, 0.25); kb.add(scan);
  const matchLbl = label('top-3 matches', 0.4, { size: 70, color: '#ffbe5c' }); matchLbl.position.set(X.retrieve, 0.35, 0.8); scene.add(matchLbl);

  // Query orb and its embedding vector bars.
  const orb = new THREE.Mesh(new THREE.SphereGeometry(0.3, 32, 24), new THREE.MeshStandardMaterial({ color: COL.accent, emissive: COL.accent, emissiveIntensity: 1.4, roughness: 0.2 }));
  scene.add(orb);
  const orbLight = new THREE.PointLight(COL.accent, 0, 6); scene.add(orbLight);
  const trailN = 18, trail = [];
  for (let i = 0; i < trailN; i++) { const m = new THREE.Mesh(new THREE.SphereGeometry(0.11, 12, 8), new THREE.MeshBasicMaterial({ color: COL.accent, transparent: true, opacity: 0 })); scene.add(m); trail.push(m); }
  const vec = new THREE.Group(); scene.add(vec);
  const bars = [];
  const heightsV = [0.5, 1.0, 0.7, 1.5, 0.9, 1.25, 0.6, 1.1];
  heightsV.forEach((h, i) => { const b = new THREE.Mesh(new THREE.BoxGeometry(0.16, 1, 0.16), new THREE.MeshBasicMaterial({ color: COL.accent })); b.userData.h = h; b.position.x = i * 0.26; vec.add(b); bars.push(b); });
  const vecLbl = label('embedding vector', 0.34, { size: 64, color: '#38d0ff' }); vecLbl.position.set(0.9, -0.4, 0); vec.add(vecLbl);
  vec.position.set(-7.6, 0.9, 1.4);

  // Prompt card with its contents.
  const prompt = new THREE.Group(); scene.add(prompt);
  const pBack = new THREE.Mesh(new THREE.BoxGeometry(3.8, 2.7, 0.1), std(COL.paper, { roughness: 0.6 }));
  prompt.add(pBack);
  const pHeadL = label('PROMPT', 0.42, { size: 76, color: COL.ink }); pHeadL.position.set(0, 1.0, 0.07);
  const pQ = label('Question: refund policy?', 0.3, { size: 58, color: COL.ink, align: 'left', weight: 600 }); pQ.position.set(0, 0.45, 0.07);
  const pC = label('Context:', 0.3, { size: 58, color: COL.ink, align: 'left', weight: 600 }); pC.position.set(-1.15, -0.1, 0.07);
  const pQwrap = new THREE.Group(); pQwrap.add(pQ);
  prompt.add(pHeadL, pQwrap, pC);
  prompt.position.set(X.augment + 0.5, 1.9, 0);
  const slot = (i) => new THREE.Vector3(X.augment + 0.5 - 1.05 + i * 1.05, 1.9 - 0.8, 0.14);

  // LLM core with orbiting rings.
  const llm = new THREE.Group(); llm.position.set(X.generate, 1.9, 0); scene.add(llm);
  const core = new THREE.Mesh(new THREE.IcosahedronGeometry(0.95, 2), new THREE.MeshStandardMaterial({ color: 0x3a2a96, emissive: COL.violet, emissiveIntensity: 0.12, roughness: 0.3, flatShading: true }));
  llm.add(core);
  const rings = [0, 1, 2].map((i) => {
    const r = new THREE.Mesh(new THREE.TorusGeometry(1.45 + i * 0.22, 0.045, 12, 120), new THREE.MeshStandardMaterial({ color: 0xbfa8ff, emissive: COL.violet, emissiveIntensity: 0.8 }));
    llm.add(r); return r;
  });
  const llmLbl = label('LLM', 0.55, { size: 90, color: '#ffffff' }); llmLbl.position.set(0, 0, 1.0); llmLbl.material.depthTest = false; llmLbl.renderOrder = 10; llm.add(llmLbl);
  // Word particles streaming out of the LLM toward the answer.
  const WORDS = ['Refunds', 'within', '30', 'days', 'of', 'purchase.'];
  const words = WORDS.map((w) => { const m = label(w, 0.36, { size: 70, color: '#ffffff', pad: 8 }); scene.add(m); return m; });

  // Answer card.
  const ans = new THREE.Group(); ans.position.set(X.answer, 1.9, 0.2); scene.add(ans);
  const aBack = new THREE.Mesh(new THREE.BoxGeometry(4.0, 2.2, 0.1), std(COL.paper, { roughness: 0.6 }));
  const aText = label(['Refunds within', '30 days of purchase.'], 0.9, { size: 72, color: COL.ink, pad: 6 }); aText.position.set(0, 0.35, 0.07);
  const aSrc = label('Source: #7', 0.36, { size: 64, color: '#0a8a45' }); aSrc.position.set(0, -0.65, 0.07);
  const aTick = new THREE.Mesh(new THREE.CircleGeometry(0.2, 32), new THREE.MeshBasicMaterial({ color: COL.green })); aTick.position.set(1.65, 0.85, 0.07);
  ans.add(aBack, aText, aSrc, aTick);

  // Pulses travelling along the conveyors during the idle title and recap shots.
  const pulses = [0, 1, 2, 3].map(() => { const m = new THREE.Mesh(new THREE.SphereGeometry(0.1, 12, 8), new THREE.MeshBasicMaterial({ color: COL.accent })); scene.add(m); return m; });

  const camKeys = {
    eye: [[0, [0, 5.0, 20]], [3, [0, 5.0, 20]], [4.6, [-9.4, 2.7, 8.2]], [6.4, [-8.8, 2.4, 8.2]], [8.2, [-5.8, 2.4, 8.4]], [11, [-4.2, 2.4, 8.4]],
      [13, [0.8, 2.5, 8.2]], [15.6, [1.0, 2.5, 8.2]], [17.2, [5.5, 2.6, 8.2]], [19.4, [5.8, 2.6, 8.0]], [21, [10.5, 2.5, 7.6]], [23.6, [10.5, 2.5, 7.4]], [26, [0, 5.0, 20]], [28, [0, 5.0, 20]]],
    target: [[0, [0, 3.4, 0]], [3, [0, 3.4, 0]], [4.6, [-9.4, 2.1, 0]], [6.4, [-9, 2.0, 0]], [8.2, [-5.6, 2.0, 0]], [11, [-4.2, 2.0, 0]],
      [13, [0.8, 2.0, 0]], [15.6, [1.0, 2.0, 0]], [17.2, [5.5, 2.0, 0]], [19.4, [5.8, 2.0, 0]], [21, [10.5, 2.0, 0]], [23.6, [10.5, 2.0, 0]], [26, [0, 3.4, 0]], [28, [0, 3.4, 0]]],
  };
  const ONE = new THREE.Vector3(1, 1, 1);
  const setScale = (o, k) => o.scale.setScalar(Math.max(0.0001, k));
  const tmp = new THREE.Vector3();

  function render(t) {
    // Camera.
    camera.position.fromArray(track(t, camKeys.eye));
    camera.lookAt(...track(t, camKeys.target));
    camera.position.y += Math.sin(t * 0.6) * 0.04;

    // Dust drift.
    for (let i = 0; i < dustN; i++) {
      const [a, b, c] = dustSeed[i];
      dustPos[i * 3] = lerp(-24, 24, (a + t * 0.004 * (1 + c)) % 1);
      dustPos[i * 3 + 1] = 0.3 + b * 8 + Math.sin(t * 0.5 + i) * 0.15;
      dustPos[i * 3 + 2] = lerp(-6, 8, c);
    }
    dustGeo.attributes.position.needsUpdate = true;

    // Title / recap.
    const titleK = appear(t, -1, 2.8, 0.01);
    setScale(title, titleK); setScale(subtitle, appear(t, 0.2, 2.8, 0.6) || 0.0001);
    if (t < 0.2) setScale(subtitle, 1);
    setScale(recap, appear(t, 24.6));
    heads.user.children.forEach((c) => (c.material.opacity = 1));

    // Question.
    setScale(bubble, appear(t, 4.2));
    person.position.y = Math.sin(t * 2) * 0.02;
    pHead.rotation.y = Math.sin(t) * 0.2;

    // Query orb path: leaves the bubble, becomes a vector, scans the shelf, then rides into the prompt, then the LLM.
    const orbPos = track(t, [[0, [-8.7, 3.0, 0.5]], [5.8, [-8.7, 3.0, 0.5]], [7.2, [-7.5, 1.9, 1.4]], [8.4, [-4.5, 1.8, 1.0]], [11, [-4.5, 1.8, 1.0]],
      [12.6, [X.augment + 1.5, 2.9, 0.3]], [16, [X.augment + 1.5, 2.9, 0.3]], [17.4, [X.generate, 1.9, 0.6]]]);
    orb.position.fromArray(orbPos);
    const orbK = t < 5.8 ? 0 : t < 17.4 ? appear(t, 5.8, 17.2, 0.4) : 0;
    setScale(orb, orbK * (1 + Math.sin(t * 6) * 0.06));
    orbLight.position.copy(orb.position); orbLight.intensity = orbK * 6;
    trail.forEach((m, i) => {
      const tt = t - (i + 1) * 0.045;
      const p = track(tt, [[0, [-8.7, 3.0, 0.5]], [5.8, [-8.7, 3.0, 0.5]], [7.2, [-7.5, 1.9, 1.4]], [8.4, [-4.5, 1.8, 1.0]], [11, [-4.5, 1.8, 1.0]], [12.6, [X.augment + 1.5, 2.9, 0.3]], [16, [X.augment + 1.5, 2.9, 0.3]], [17.4, [X.generate, 1.9, 0.6]]]);
      m.position.fromArray(p);
      const moving = Math.hypot(...orbPos.map((v, j) => v - p[j])) > 0.05;
      m.material.opacity = orbK * (moving ? 0.55 * (1 - i / trailN) : 0);
    });
    // Embedding vector bars grow while the orb crosses to the shelf.
    const vecK = appear(t, 6.7, 9.2);
    vec.children.forEach((b, i) => { if (b.geometry.type === 'BoxGeometry') { const k = clamp(vecK * 1.4 - i * 0.05); b.scale.set(k > 0 ? 1 : 0.0001, Math.max(0.0001, b.userData.h * k * (1 + Math.sin(t * 5 + i) * 0.08)), k > 0 ? 1 : 0.0001); b.position.y = b.scale.y / 2; } });
    setScale(vecLbl, vecK);

    // Search scan across the shelf.
    const scanK = t > 8.6 && t < 10.3 ? 1 : 0;
    scan.visible = scanK > 0;
    scan.position.x = lerp(-1.9, 1.9, smooth((t - 8.6) / 1.5));

    // Documents: highlight hits, then fly into the prompt, then into the LLM, then reset for the recap.
    docs.forEach((d) => {
      d.card.position.copy(d.home); d.card.scale.copy(ONE); d.mat.emissiveIntensity = 0;
      if (!d.hit) { d.mat.opacity = 1; return; }
      const i = HITS.indexOf(d.n);
      const glowK = smooth((t - 9.6) / 0.5);
      d.mat.emissiveIntensity = glowK * (0.9 + Math.sin(t * 8) * 0.15);
      d.mat.color.set(0xd7dcec).lerp(new THREE.Color(0xffd08a), glowK);
      const homeW = tmp.copy(d.home).add(kb.position);
      const to = slot(i);
      const lift = homeW.clone().add(new THREE.Vector3(0, 0, 0.9));
      let p, k = 1;
      if (t < 10.4) p = homeW;
      else if (t < 11.2) p = homeW.clone().lerp(lift, smooth((t - 10.4) / 0.8));
      else if (t < 13) p = lift.clone().lerp(to, smooth((t - 11.2 - i * 0.15) / 1.5));
      else if (t < 16.4) p = to;
      else if (t < 17.4) { p = to.clone().lerp(new THREE.Vector3(X.generate, 1.9, 0.4), smooth((t - 16.4) / 1.0)); k = 1 - smooth((t - 16.6) / 0.8); }
      else if (t < 22) { p = new THREE.Vector3(X.generate, 1.9, 0.4); k = 0; }
      else { p = to; k = smooth((t - 22) / 0.6); }
      d.card.position.copy(d.card.parent.worldToLocal(p.clone()));
      d.card.scale.setScalar(Math.max(0.0001, (t >= 11.2 && t < 17 || t >= 22 ? 0.72 : 1) * k));
    });
    setScale(matchLbl, appear(t, 10.0, 11.5));

    // Prompt card: appears with the augment step, then collapses into the LLM; reappears for the recap.
    let pk = appear(t, 12.2, 16.6, 0.5);
    if (t >= 22) pk = smooth((t - 22) / 0.6);
    setScale(prompt, pk);
    prompt.position.set(...track(t, [[0, [X.augment + 0.5, 1.9, 0]], [16.4, [X.augment + 0.5, 1.9, 0]], [17.4, [X.generate, 1.9, 0.3]], [22, [X.generate, 1.9, 0.3]], [22.1, [X.augment + 0.5, 1.9, 0]]]));
    setScale(pQwrap, appear(t, 12.8) || 0.0001);

    // LLM: idle spin, bright while generating.
    const gen = smooth((t - 17.2) / 0.5) * (1 - smooth((t - 20.4) / 0.6));
    core.rotation.y = t * 0.6; core.rotation.x = Math.sin(t * 0.5) * 0.3;
    core.material.emissiveIntensity = 0.12 + gen * (0.55 + Math.sin(t * 14) * 0.15);
    setScale(core, 1 + gen * 0.12 * Math.sin(t * 10));
    rings.forEach((r, i) => { r.rotation.x = t * (0.7 + i * 0.35) * (i % 2 ? -1 : 1) + i; r.rotation.y = t * (0.5 + i * 0.25) + i * 2; });
    glow.intensity = gen * 40; glow.position.set(X.generate, 2.2, 2.5);

    // Words stream from the LLM to the answer card.
    words.forEach((w, i) => {
      const t0 = 18.4 + i * 0.4;
      const k = clamp((t - t0) / 1.6);
      // Each word arcs from the LLM into the answer card and is absorbed as the card pops in.
      w.position.set(lerp(X.generate + 1.4, X.answer, smooth(k)), lerp(1.9, 2.0, smooth(k)) + Math.sin(k * Math.PI) * 1.1, 0.9);
      setScale(w, t < t0 || k >= 1 ? 0 : (0.5 + 0.5 * Math.sin(k * Math.PI)) * (1 - smooth((k - 0.75) / 0.25)));
    });

    // Answer.
    setScale(ans, appear(t, 20.2));
    aTick.scale.setScalar(Math.max(0.0001, appear(t, 21.2)));
    aSrc.scale.setScalar(Math.max(0.0001, appear(t, 20.9)));
    aText.scale.setScalar(Math.max(0.0001, appear(t, 20.4)));

    // Arrow pulse and idle flow pulses.
    arrows.forEach((h, i) => { h.material.emissiveIntensity = 0.5 + 0.5 * Math.max(0, Math.sin(t * 3 - i * 0.9)); });
    const idle = t < 3.2 || t > 24.4;
    pulses.forEach((p, i) => {
      const [a, b] = seg[i], u = ((t * 0.5 + i * 0.25) % 1);
      p.position.set(lerp(a, b, u), 0.12, 1.6);
      setScale(p, idle ? 1 : 0);
    });

    renderer.render(scene, camera);
  }
  return { render, renderer };
}

// Captions shown under the video (DOM overlay; also captured by the frame renderer).
export const CAPTIONS = [
  [0.0, 3.0, 'RAG = Retrieval-Augmented Generation'],
  [3.2, 6.6, 'A user asks something the LLM was never trained on.'],
  [6.8, 10.0, '1. RETRIEVE: embed the question, then search your knowledge base.'],
  [10.2, 13.0, 'The 3 most similar chunks are selected.'],
  [13.2, 16.6, '2. AUGMENT: add those chunks to the prompt as context.'],
  [16.8, 20.0, '3. GENERATE: the LLM writes an answer from that context.'],
  [20.3, 24.0, 'The answer is grounded in your documents, with a source.'],
  [24.5, 28.0, 'Retrieve → Augment → Generate'],
];
