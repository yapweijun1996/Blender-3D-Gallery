// Generates the Crucible scene recipe for a 28 s "What is RAG?" explainer.
// Story: question -> embed + search knowledge base -> top-3 chunks -> augmented prompt -> LLM -> grounded answer.
import fs from 'node:fs';
import { dir } from './mcp.mjs';

const DURATION = 28;
const TINY = [0.001, 0.001, 0.001];
// While the camera is on the answer, the filled prompt is put back (off screen) for the final recap shot.
const RESET = 22;
const ONE = [1, 1, 1];
const geometries = [
  { id: 'card', type: 'box', bevel: 0.02 },
  { id: 'slab', type: 'box', bevel: 0 },
  { id: 'cyl', type: 'cylinder', segments: 48 },
  { id: 'ball', type: 'sphere', segments: 32, rings: 16 },
  { id: 'core', type: 'icoSphere', subdivisions: 2 },
  { id: 'ring', type: 'torus', tubeRadius: 0.04, segments: 96, sides: 12 },
  { id: 'arrowHead', type: 'cone', radiusTop: 0, radiusBottom: 1, segments: 24 },
];
const materials = [
  { id: 'floor', color: [0.05, 0.06, 0.09], roughness: 0.85 },
  { id: 'track', color: [0.16, 0.2, 0.3], roughness: 0.6 },
  { id: 'title', tag: 'unlit', color: [0.97, 0.97, 1] },
  { id: 'accent', tag: 'unlit', color: [0.25, 0.82, 1] },
  { id: 'subtle', tag: 'unlit', color: [0.72, 0.76, 0.86] },
  { id: 'ink', tag: 'unlit', color: [0.06, 0.07, 0.12] },
  { id: 'green', tag: 'unlit', color: [0.02, 0.42, 0.18] },
  { id: 'paper', color: [0.8, 0.82, 0.88], roughness: 0.6 },
  { id: 'backdrop', color: [0, 0, 0], emissiveColor: [0.02, 0.035, 0.08], emission: 1, roughness: 1 },
  { id: 'person', color: [0.28, 0.5, 0.95], roughness: 0.5 },
  { id: 'shelf', color: [0.22, 0.25, 0.33], roughness: 0.7 },
  { id: 'doc', color: [0.72, 0.75, 0.82], roughness: 0.6 },
  { id: 'query', color: [0.2, 0.8, 1], emissiveColor: [0.2, 0.8, 1], emission: 1.6, roughness: 0.3 },
  { id: 'llm', color: [0.5, 0.32, 1], emissiveColor: [0.55, 0.35, 1], emission: 0.35, roughness: 0.35 },
  { id: 'ringMat', color: [0.6, 0.45, 1], emissiveColor: [0.6, 0.45, 1], emission: 0.7, roughness: 0.3 },
];
const nodes = [];
const tracks = [];
let textCount = 0;

function node(id, geometry, material, translation, scale = ONE, extra = {}) {
  nodes.push({ id, geometry, material, translation, scale, ...extra });
  return id;
}
// Text costs about 640 preflight vertices per character per curve segment (scene budget 250k), so keep it short.
function text(id, str, { size = 0.3, depth = 0.04, align = 'center', material = 'title', at, parent, scale = ONE, curveSegments = 1 }) {
  const g = `t${textCount++}`;
  geometries.push({ id: g, type: 'text', text: str, size, depth, align, curveSegments });
  return node(id, g, material, at, scale, { castShadow: false, ...(parent ? { parent } : {}) });
}
const track = (kind, id, property, keys, interpolation = 'SMOOTH') =>
  tracks.push({ kind, ...(id ? { id } : {}), property, interpolation, keyframes: keys.map(([time, value]) => ({ time, value })) });
// Pop a node in (and optionally out) by scale, so it is invisible outside its window.
function pop(id, inAt, outAt, full = ONE) {
  const keys = inAt < 0 ? [[0, full]] : [[0, TINY], [inAt, TINY], [inAt + 0.45, full]];
  if (outAt != null) keys.push([outAt, full], [outAt + 0.45, TINY]);
  keys.push([DURATION, keys.at(-1)[1]]);
  track('node', id, 'scale', keys);
}

// Stage floor and the flow arrows between stations (station centres on X).
const X = { user: -10, retrieve: -4.5, augment: 0.5, generate: 5.5, answer: 10.5 };
node('floor', 'slab', 'floor', [0, -0.05, 7], [44, 0.1, 25]);
node('backdrop', 'slab', 'backdrop', [0, 8, -6], [90, 40, 0.2], { castShadow: false });
for (const [i, [a, b]] of [[-8.6, -6.6], [-2.2, -1.4], [2.6, 3.9], [7.1, 8.3]].entries()) {
  node(`track-${i}`, 'slab', 'track', [(a + b) / 2, 0.02, 1.4], [b - a, 0.04, 0.12]);
  node(`arrow-${i}`, 'arrowHead', 'accent', [b + 0.15, 0.06, 1.4], [0.16, 0.32, 0.16], { rotation: [0, 0, -0.7071068, 0.7071068] });
}

// Title, then recap at the end.
text('title', 'What is RAG?', { size: 0.95, at: [0, 5.6, 0] });
text('subtitle', 'Retrieval-Augmented Generation', { size: 0.42, material: 'accent', at: [0, 4.75, 0] });
pop('title', -1, 3.2); pop('subtitle', -1, 3.2);
text('recap', 'Retrieve  ->  Augment  ->  Generate', { size: 0.62, material: 'accent', at: [0, 5.5, 0] });
pop('recap', 24.6, null);

// Station headings (always shown so the wide shot reads as a pipeline).
const heading = (key, h, sub) => {
  text(`${key}-head`, h, { size: 0.42, material: 'accent', at: [X[key], 3.55, 0] });
  text(`${key}-sub`, sub, { size: 0.2, material: 'subtle', at: [X[key], 3.12, 0] });
};
heading('user', 'QUESTION', 'user asks');
heading('retrieve', '1. RETRIEVE', 'search knowledge base');
heading('augment', '2. AUGMENT', 'question + context');
heading('generate', '3. GENERATE', 'LLM writes the answer');
heading('answer', 'ANSWER', 'with its source');

// User and speech bubble.
node('person-body', 'cyl', 'person', [X.user, 0.45, 0], [0.34, 0.9, 0.34]);
node('person-head', 'ball', 'person', [X.user, 1.18, 0], [0.27, 0.27, 0.27]);
node('bubble', 'card', 'paper', [X.user, 2.15, 0.1], ONE);
nodes.at(-1).scale = [2.9, 0.95, 0.06];
// Text under a scaled card would inherit its scale, so the bubble text is a sibling and pops on the same keys.
text('bubble-text', 'What is our\nrefund policy?', { size: 0.3, material: 'ink', at: [X.user, 2.26, 0.18] });
track('node', 'bubble', 'scale', [[0, [0.001, 0.001, 0.001]], [4.3, [0.001, 0.001, 0.001]], [4.8, [2.9, 0.95, 0.06]], [DURATION, [2.9, 0.95, 0.06]]]);
pop('bubble-text', 4.4, null);

// Knowledge base: shelf with 12 document chunks; three are the top-k matches.
node('shelf', 'card', 'shelf', [X.retrieve, 1.5, -0.45], [3.7, 2.7, 0.15]);
const cols = [-1.2, -0.4, 0.4, 1.2], rows = [2.35, 1.5, 0.65];
const hits = { 6: 'hit-a', 7: 'hit-b', 11: 'hit-c' };
let n = 0;
for (const y of rows) for (const dx of cols) {
  n += 1;
  const mat = hits[n] ?? 'doc';
  if (hits[n]) materials.push({ id: mat, color: [0.72, 0.75, 0.82], emissiveColor: [1, 0.5, 0.1], emission: 0, roughness: 0.6 });
  const id = `doc-${n}`;
  node(id, 'card', mat, [X.retrieve + dx, y, -0.3], [0.62, 0.74, 0.05]);
  text(`${id}-label`, `#${n}`, { size: 0.16, material: 'ink', depth: 0.02, at: [X.retrieve + dx, y + 0.18, -0.25] });
}

// Query orb: leaves the bubble, becomes an embedding, scans the shelf.
node('orb', 'ball', 'query', [X.user + 1.6, 2.15, 0.3], TINY);
track('node', 'orb', 'scale', [[0, TINY], [5.6, TINY], [6.0, [0.2, 0.2, 0.2]], [11.0, [0.2, 0.2, 0.2]], [12.6, [0.13, 0.13, 0.13]],
  [15.8, [0.13, 0.13, 0.13]], [17.4, TINY], [RESET, TINY], [RESET + 0.1, [0.13, 0.13, 0.13]], [DURATION, [0.13, 0.13, 0.13]]]);
track('node', 'orb', 'translation', [[0, [-8.4, 2.15, 0.3]], [6.0, [-8.4, 2.15, 0.3]], [7.2, [-7.3, 1.7, 0.8]],
  [8.6, [-4.5, 1.5, 0.9]], [9.1, [-5.7, 1.5, 0.9]], [9.6, [-3.3, 1.5, 0.9]], [10.1, [-4.5, 1.5, 0.9]], [11.0, [-4.5, 1.6, 0.9]],
  [12.6, [X.augment + 1.95, 2.02, 0.22]], [15.8, [X.augment + 1.95, 2.02, 0.22]], [17.4, [X.generate, 1.6, 0]], [RESET, [X.generate, 1.6, 0]], [RESET + 0.1, [X.augment + 1.95, 2.02, 0.22]], [DURATION, [X.augment + 1.95, 2.02, 0.22]]]);
text('embed', 'vector [0.12, -0.83, ...]', { size: 0.17, material: 'accent', at: [-7.2, 0.95, 0.8] });
pop('embed', 6.7, 9.4);
text('match', 'top-3 matches', { size: 0.2, material: 'subtle', at: [X.retrieve, 0.1, 0.9] });
pop('match', 9.6, 11.2);

// Matches glow, then fly into the prompt card's context row, then into the LLM.
const slots = { 'hit-a': [-0.35, 0.95], 'hit-b': [0.5, 0.95], 'hit-c': [1.35, 0.95] };
for (const [num, mat] of Object.entries(hits)) {
  const id = `doc-${num}`;
  const d = nodes.find((v) => v.id === id).translation;
  const [sx, sy] = slots[mat];
  const slot = [X.augment + sx, sy, 0.16];
  const into = [X.generate, 1.6, 0];
  track('material', mat, 'emission', [[0, 0], [9.4, 0], [9.9, 1.4], [12.6, 0.6], [17.4, 0.6], [DURATION, 0.6]]);
  track('material', mat, 'color', [[0, [0.72, 0.75, 0.82]], [9.4, [0.72, 0.75, 0.82]], [9.9, [1, 0.62, 0.25]], [DURATION, [1, 0.62, 0.25]]]);
  track('node', id, 'translation', [[0, d], [10.2, d], [10.8, [d[0], d[1], 0.4]], [12.6, slot], [15.8, slot], [17.4, into], [RESET, into], [RESET + 0.1, slot], [DURATION, slot]]);
  track('node', id, 'scale', [[0, [0.62, 0.74, 0.05]], [11.0, [0.62, 0.74, 0.05]], [12.6, [0.5, 0.6, 0.05]], [15.8, [0.5, 0.6, 0.05]], [17.4, TINY], [RESET, TINY], [RESET + 0.1, [0.5, 0.6, 0.05]], [DURATION, [0.5, 0.6, 0.05]]]);
  const lbl = `${id}-label`, lt = [d[0], d[1] + 0.18, -0.25];
  const lslot = [slot[0], slot[1] + 0.15, slot[2] + 0.04], linto = into;
  track('node', lbl, 'translation', [[0, lt], [10.2, lt], [10.8, [lt[0], lt[1], 0.45]], [12.6, lslot], [15.8, lslot], [17.4, linto], [RESET, linto], [RESET + 0.1, lslot], [DURATION, lslot]]);
  track('node', lbl, 'scale', [[0, ONE], [11.0, ONE], [12.6, [0.8, 0.8, 0.8]], [15.8, [0.8, 0.8, 0.8]], [17.4, TINY], [RESET, TINY], [RESET + 0.1, [0.8, 0.8, 0.8]], [DURATION, [0.8, 0.8, 0.8]]]);
}

// Prompt card (augmentation). Card and its texts shrink into the LLM together.
const PC = [X.augment + 0.5, 1.6, 0];
node('prompt', 'card', 'paper', PC, [3.4, 2.4, 0.06]);
const promptTexts = [
  text('prompt-head', 'PROMPT', { size: 0.3, material: 'ink', at: [PC[0], 2.42, 0.06] }),
  text('prompt-q', 'Question:', { size: 0.2, material: 'ink', align: 'left', at: [PC[0] - 1.5, 1.95, 0.06] }),
  text('prompt-qt', 'refund policy?', { size: 0.2, material: 'ink', align: 'left', at: [PC[0] - 0.4, 1.95, 0.06] }),
  text('prompt-c', 'Context:', { size: 0.2, material: 'ink', align: 'left', at: [PC[0] - 1.5, 1.5, 0.06] }),
];
track('node', 'prompt', 'translation', [[0, PC], [15.8, PC], [17.4, [X.generate, 1.6, 0]], [RESET, [X.generate, 1.6, 0]], [RESET + 0.1, PC], [DURATION, PC]]);
track('node', 'prompt', 'scale', [[0, [3.4, 2.4, 0.06]], [15.8, [3.4, 2.4, 0.06]], [17.4, TINY], [RESET, TINY], [RESET + 0.1, [3.4, 2.4, 0.06]], [DURATION, [3.4, 2.4, 0.06]]]);
for (const id of promptTexts) {
  const t = nodes.find((v) => v.id === id).translation;
  track('node', id, 'translation', [[0, t], [15.8, t], [17.4, [X.generate, 1.6, 0]], [RESET, [X.generate, 1.6, 0]], [RESET + 0.1, t], [DURATION, t]]);
  const appear = id === 'prompt-qt' ? [[0, TINY], [12.3, TINY], [12.8, ONE]] : [[0, ONE]];
  track('node', id, 'scale', [...appear, [15.8, ONE], [17.4, TINY], [RESET, TINY], [RESET + 0.1, ONE], [DURATION, ONE]]);
}

// LLM core with two precessing rings (spin about Y on a tilted child).
node('llm-core', 'core', 'llm', [X.generate, 1.6, 0], [0.85, 0.85, 0.85]);
text('llm-label', 'LLM', { size: 0.5, material: 'ink', at: [X.generate, 1.42, 0.9] });
for (const [i, tilt] of [[0, [0.3826834, 0, 0, 0.9238795]], [1, [0, 0, 0.3826834, 0.9238795]]]) {
  nodes.push({ id: `ring-spin-${i}`, translation: [X.generate, 1.6, 0], scale: ONE });
  node(`ring-${i}`, 'ring', 'ringMat', [0, 0, 0], [1.3 + 0.18 * i, 1.3 + 0.18 * i, 1.3 + 0.18 * i], { parent: `ring-spin-${i}`, rotation: tilt });
  const keys = [];
  const turns = 7; // one turn per 4 s
  for (let k = 0; k <= turns * 8; k += 1) {
    const a = ((i ? -1 : 1) * k * Math.PI) / 4;
    keys.push([(k / (turns * 8)) * DURATION, [0, Math.sin(a / 2), 0, Math.cos(a / 2)]]);
  }
  track('node', `ring-spin-${i}`, 'rotation', keys, 'LINEAR');
}
track('material', 'llm', 'emission', [[0, 0.35], [17.2, 0.35], [17.8, 1.8], [18.4, 0.6], [19, 1.8], [19.6, 0.5], [DURATION, 0.5]]);

// Answer card.
node('answer-card', 'card', 'paper', [X.answer, 1.75, 0.1], TINY);
track('node', 'answer-card', 'scale', [[0, TINY], [19.8, TINY], [20.4, [3.6, 1.7, 0.06]], [DURATION, [3.6, 1.7, 0.06]]]);
text('answer-text', 'Refunds within\n30 days of purchase.', { size: 0.27, material: 'ink', at: [X.answer, 2.15, 0.18] });
text('answer-src', 'Source: #7', { size: 0.24, material: 'green', at: [X.answer, 1.12, 0.18] });
pop('answer-text', 20.0, null); pop('answer-src', 20.6, null);

// Camera: wide title, then follow the data through each station, then wide recap.
const cam = [
  [0, [0, 4.2, 17.5], [0, 3, 0]], [3.0, [0, 4.2, 17.5], [0, 3, 0]],
  [4.6, [-9.4, 2.4, 6.8], [-9.4, 2.0, 0]], [6.2, [-9.0, 2.3, 6.8], [-9.0, 1.9, 0]],
  [8.0, [-5.8, 2.2, 7.4], [-5.6, 1.8, 0]], [11.0, [-4.2, 2.2, 7.4], [-4.2, 1.8, 0]],
  [13.0, [0.6, 2.2, 7.0], [0.6, 1.8, 0]], [15.6, [0.9, 2.2, 7.0], [0.9, 1.8, 0]],
  [17.2, [5.5, 2.3, 7.0], [5.5, 1.8, 0]], [19.4, [5.8, 2.3, 6.8], [5.8, 1.8, 0]],
  [21.0, [10.5, 2.2, 6.6], [10.5, 1.9, 0]], [23.6, [10.5, 2.2, 6.4], [10.5, 1.9, 0]],
  [26.0, [0, 4.2, 17.5], [0, 3, 0]], [DURATION, [0, 4.2, 17.5], [0, 3, 0]],
];
track('camera', null, 'eye', cam.map(([t, e]) => [t, e]));
track('camera', null, 'target', cam.map(([t, , g]) => [t, g]));

const recipe = {
  format: 'crucible.scene',
  schemaVersion: 1,
  geometries,
  materials,
  nodes,
  camera: { eye: [0, 4.2, 17.5], target: [0, 3, 0], fov: 45 },
  environment: { setup: 'studio', ground: false, world: false, environmentIntensity: 0.35, fogDensity: 0 },
  effects: { bloom: { strength: 0.35, threshold: 1.4, radius: 0.6 }, vignette: 0.3, contrast: 1.08 },
  motion: { duration: DURATION, loop: false, tracks },
};
fs.writeFileSync(dir + '/recipe.json', JSON.stringify(recipe, null, 1));
const keys = tracks.reduce((s, t) => s + t.keyframes.length, 0);
console.log(`nodes ${nodes.length}, geometries ${geometries.length}, materials ${materials.length}, tracks ${tracks.length}, keys ${keys}`);
