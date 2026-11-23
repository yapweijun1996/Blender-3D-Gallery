import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { fasciaBaseY, shopfrontAssets, shopfrontBays, shopfrontZ } from './shopfront-layout.js';

const root = new URL('../', import.meta.url);
const asset = (path) => new URL(path, root).href;
const modules = [
  { id:'floor', number:'001', name:'Floor tile', detail:'1.2 m repeat module', kicker:'001 / THE FOUNDATION', subtitle:'Warm terrazzo floor, made to repeat.', path:'models/mall-floor-tile/exports/mall-floor-tile-module.glb', thumb:'models/mall-floor-tile/previews/mall-floor-tile-module.webp' },
  { id:'cornerTile', number:'C3', name:'Corner floor tile', detail:'1.2 m outside corner', kicker:'CORNER / THE FOUNDATION', subtitle:'A terrazzo corner tile with two inset border strips.', path:'models/mall-floor-corner-tile/exports/mall-floor-corner-tile.glb', thumb:'models/mall-floor-corner-tile/previews/mall-floor-corner-tile.jpg' },
  { id:'mitredTrim', number:'C4', name:'Mitred floor trim', detail:'90° outside corner pair', kicker:'CORNER / THE MITRE', subtitle:'Two edge strips meeting in a 45° joint.', path:'models/mall-floor-mitred-trim/exports/mall-floor-mitred-trim.glb', thumb:'models/mall-floor-mitred-trim/previews/mall-floor-mitred-trim.jpg' },
  { id:'floorCorner', number:'C1', name:'Floor corner trim', detail:'60 mm outside corner cap', kicker:'CORNER / THE FLOOR EDGE', subtitle:'A square cap joining two straight edge strips.', path:'models/mall-floor-corner-trim/exports/mall-floor-corner-trim.glb', thumb:'models/mall-floor-corner-trim/previews/mall-floor-corner-trim.jpg' },
  { id:'wall', number:'003', name:'Solid wall', detail:'1.2 m repeat module', kicker:'003 / THE ENCLOSURE', subtitle:'A solid wall with warm panels and dark skirting.', path:'models/mall-solid-wall/exports/mall-solid-wall.glb', thumb:'models/mall-solid-wall/previews/mall-solid-wall.jpg' },
  { id:'wallCorner', number:'C2', name:'Wall corner', detail:'90° · 1.2 m arms', kicker:'CORNER / THE WALL', subtitle:'A right-angle corner connecting the solid wall modules.', path:'models/mall-wall-corner/exports/mall-wall-corner.glb', thumb:'models/mall-wall-corner/previews/mall-wall-corner.jpg' },
  { id:'railing', number:'004', name:'Glass railing', detail:'2 m post-centred bay', kicker:'004 / THE EDGE', subtitle:'A glazed bay with posts, infill and handrail.', path:'models/mall-glass-railing/exports/mall-glass-railing-2m.glb', thumb:'models/mall-glass-railing/previews/mall-glass-railing-2m.webp' },
  { id:'ceiling', number:'005', name:'Ceiling panel', detail:'1.2 m suspended cassette', kicker:'005 / ABOVE', subtitle:'A repeating ceiling cassette with recessed panels.', path:'models/mall-ceiling-panel/exports/mall-ceiling-panel-module.glb', thumb:'models/mall-ceiling-panel/previews/mall-ceiling-panel-module.webp' },
  { id:'column', number:'006', name:'Structural column', detail:'0.6 m × 3 m', kicker:'006 / THE SUPPORT', subtitle:'An ivory-clad square column, grounded at floor level.', path:'models/mall-structural-column/exports/mall-structural-column.glb', thumb:'models/mall-structural-column/previews/mall-structural-column.webp' },
];
// Extra scene context is loaded only for the corridor, not individual views.
const furnishings = [
  ...shopfrontAssets,
  { id:'floorEdge', path:'models/mall-floor-edge-trim/exports/mall-floor-edge-trim.glb' },
  { id:'light', path:'models/mall-ceiling-light/exports/mall-ceiling-light-module.glb' },
  { id:'bench', path:'models/gjh-mall-furniture/exports/gjh-lounge-bench.glb' },
  { id:'planter', path:'models/gjh-mall-furniture/exports/gjh-areca-planter.glb' },
  { id:'shelf', path:'models/mall-essentials/exports/mall-display-shelf.glb' },
  { id:'directory', path:'models/mall-essentials/exports/mall-directory-kiosk.glb' },
  { id:'lightbox', path:'models/mall-essentials/exports/mall-advertising-lightbox.glb' },
];
const $ = (selector) => document.querySelector(selector);
const list = $('#module-list');
for (const item of modules) {
  const button = document.createElement('button');
  button.type = 'button'; button.className = 'module'; button.dataset.module = item.id;
  button.setAttribute('aria-pressed', 'false');
  const image = document.createElement('img'); image.src = asset(item.thumb); image.alt = ''; image.loading = 'lazy';
  const text = document.createElement('span');
  const name = document.createElement('span'); name.className = 'module-name'; name.textContent = `${item.number}  /  ${item.name}`;
  const detail = document.createElement('span'); detail.className = 'module-detail'; detail.textContent = item.detail;
  text.append(name, detail);
  const arrow = document.createElement('span'); arrow.className = 'module-arrow'; arrow.setAttribute('aria-hidden','true'); arrow.textContent = '↗';
  button.append(image, text, arrow); list.append(button);
}

const wrap = $('#canvas-wrap'); const status = $('#canvas-status'); const assemblyButton = $('#assembly-button');
let renderer;
try { renderer = new THREE.WebGLRenderer({ antialias:true, alpha:true }); }
catch { status.textContent = '3D view unavailable. Your browser may not support WebGL.'; }
if (renderer) {
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.12;
  renderer.domElement.setAttribute('aria-label','Interactive 3D view. Drag to rotate and scroll to zoom.');
  wrap.prepend(renderer.domElement);
  const scene = new THREE.Scene(); scene.background = new THREE.Color('#eef1eb');
  scene.add(new THREE.HemisphereLight(0xffffff, 0x858d79, 2.1));
  const sun = new THREE.DirectionalLight(0xffffff, 2.35); sun.position.set(4, 9, 7); scene.add(sun);
  const fill = new THREE.DirectionalLight(0xe4f2e9, 0.8); fill.position.set(-5, 3, -3); scene.add(fill);
  const camera = new THREE.PerspectiveCamera(34, 1, 0.02, 100);
  const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true; controls.minDistance = 1; controls.maxDistance = 30; controls.maxPolarAngle = Math.PI * .88;
  const loader = new GLTFLoader(); const cache = new Map();
  const load = (item) => {
    if (!cache.has(item.id)) cache.set(item.id, loader.loadAsync(asset(item.path)).then(gltf => gltf.scene).catch(error => { cache.delete(item.id); throw error; }));
    return cache.get(item.id);
  };
  const byId = Object.fromEntries(modules.map(item => [item.id, item]));
  let current = null; let requestId = 0; let selected = 'assembly';
  let shopSigns;
  const instance = (source, x, y, z, omit) => {
    const obj = source.clone(true); obj.position.set(x,y,z);
    if (omit) obj.getObjectByName(omit)?.removeFromParent();
    return obj;
  };
  function corridor(sources) {
    const group = new THREE.Group(); group.name = 'Mall corridor assembly';
    const facingCorridor = (object) => { object.rotation.y = Math.PI; return object; };
    const columns = [-3.6,-2.4,-1.2,0,1.2,2.4,3.6];
    for (const x of columns) for (const z of [-2.4,-1.2,0,1.2,2.4]) group.add(instance(x === 3.6 && z === 2.4 ? sources.cornerTile : sources.floor,x,-.03,z));
    for (const x of columns.filter(x => x !== 3.6)) group.add(instance(sources.floorEdge,x,0,3.03));
    for (const z of [-2.4,-1.2,0,1.2]) {
      const side = instance(sources.floorEdge,4.23,0,z); side.rotation.y = Math.PI/2; group.add(side);
    }
    group.add(instance(sources.mitredTrim,3.6,0,2.4));

    for (const { x, opening, fascia } of shopfrontBays) {
      group.add(instance(sources[opening], x, 0, shopfrontZ));
      group.add(instance(sources[fascia], x, fasciaBaseY, shopfrontZ));
      if (opening === 'door') group.add(facingCorridor(instance(sources.shelf, x, 0, -2.42)));
    }
    // The solid wall stays behind the transparent storefronts as a reusable back wall.
    for (const x of [-3.6,-2.4,-1.2,0,1.2,2.4]) group.add(instance(sources.wall,x,0,-2.94));
    group.add(instance(sources.wallCorner,4.2,0,-2.94));
    for (const z of [-1.14,.06,1.26]) {
      const side = instance(sources.wall,4.2,0,z); side.rotation.y = Math.PI/2; group.add(side);
    }

    // Fictional, replaceable shop labels; they are scene context, not model metadata.
    if (!shopSigns) {
      shopSigns = [['THE EDIT','LIFESTYLE & HOME'],['STUDIO','OBJECTS & DESIGN']].map(([title,subtitle]) => {
        const canvas = document.createElement('canvas'); canvas.width = 1024; canvas.height = 256;
        const ctx = canvas.getContext('2d'); ctx.fillStyle = '#f2eee4'; ctx.fillRect(0,0,1024,256);
        ctx.fillStyle = '#263c30'; ctx.textAlign = 'center';
        ctx.font = '600 97px Georgia'; ctx.fillText(title,512,135);
        ctx.font = '600 30px sans-serif'; ctx.fillText(subtitle,512,197);
        const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
        return new THREE.Mesh(new THREE.PlaneGeometry(1.65,.4),new THREE.MeshBasicMaterial({map:texture}));
      });
    }
    const doors = shopfrontBays.filter(({ opening }) => opening === 'door');
    for (const [index, { x }] of doors.entries()) {
      const sign = shopSigns[index].clone(); sign.position.set(x,2.69,-1.155); group.add(sign);
    }

    // Retain a cutaway in front. A light replaces one panel in each chosen cassette.
    for (const x of columns) for (const z of [-2.4,-1.2]) {
      const hasLight = z === -1.2 && [-2.4,0,2.4].includes(x);
      group.add(instance(sources.ceiling,x,3,z,hasLight ? 'PANEL_1' : null));
      if (hasLight) {
        group.add(instance(sources.light,x-.3,3.008,z+.3));
        const glow = new THREE.PointLight(0xffe5bb, 1.2, 4, 2);
        glow.position.set(x-.3,2.82,z+.3); group.add(glow);
      }
    }
    group.add(instance(sources.column,-3.6,0,0));
    group.add(instance(sources.column,3.6,0,0));
    group.add(instance(sources.railing,-1,0,2.95));
    group.add(instance(sources.railing,1,0,2.95,'MODULE_Post_Left'));
    group.add(facingCorridor(instance(sources.bench,0,0,.85)));
    group.add(instance(sources.planter,-3.25,0,1.8));
    group.add(instance(sources.planter,3.25,0,1.8));
    group.add(facingCorridor(instance(sources.directory,-3.0,0,-.25)));
    group.add(facingCorridor(instance(sources.lightbox,3.0,0,-.25)));
    return group;
  }
  function frame(object, id) {
    object.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(object); const sphere = box.getBoundingSphere(new THREE.Sphere());
    controls.target.copy(sphere.center);
    const vertical = THREE.MathUtils.degToRad(camera.fov/2); const horizontal = Math.atan(Math.tan(vertical)*camera.aspect);
    const margin = id === 'assembly' ? (camera.aspect < 1.35 ? 1.08 : .8) : 1.2;
    const distance = Math.max(sphere.radius, .25) / Math.sin(Math.min(vertical,horizontal)) * margin;
    const direction = id === 'ceiling' ? new THREE.Vector3(4,-3,5) : id === 'assembly' ? new THREE.Vector3(6,3.5,10) : new THREE.Vector3(6,4,7);
    camera.position.copy(sphere.center).add(direction.normalize().multiplyScalar(distance));
    controls.minDistance = Math.max(.2, sphere.radius * .65); controls.maxDistance = Math.max(10, sphere.radius * 12);
    camera.near = Math.max(.01, distance / 100); camera.far = distance * 20; camera.updateProjectionMatrix(); controls.update();
  }
  function resize() { const {width,height} = wrap.getBoundingClientRect(); if (!width || !height) return; renderer.setSize(width,height,false); camera.aspect=width/height; camera.updateProjectionMatrix(); if (current) frame(current, selected); }
  new ResizeObserver(resize).observe(wrap); resize();
  async function select(id) {
    selected = id; const request = ++requestId;
    const item = byId[id];
    $('#view-kicker').textContent = item ? item.kicker : 'THE ASSEMBLY';
    $('#view-title').textContent = item ? item.name : 'The corridor';
    $('#view-subtitle').textContent = item ? item.subtitle : 'A cutaway with shopfronts, lighting and corner modules.';
    assemblyButton.classList.toggle('active', id === 'assembly'); assemblyButton.setAttribute('aria-pressed', String(id === 'assembly'));
    for (const button of list.querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.module === id));
    status.textContent = 'Loading 3D model…'; status.dataset.state = 'loading';
    try {
      const needed = item ? [item] : [...modules, ...furnishings];
      const loaded = await Promise.all(needed.map(async m => [m.id, await load(m)]));
      if (request !== requestId) return;
      if (current) scene.remove(current);
      const sources = Object.fromEntries(loaded);
      current = item ? sources[id].clone(true) : corridor(sources); scene.add(current); frame(current,id);
      status.textContent = ''; status.dataset.state = 'ready'; wrap.dataset.view = id;
    } catch (error) {
      if (request !== requestId) return;
      if (current) { scene.remove(current); current = null; }
      status.textContent = 'Unable to load the 3D model. Select the view to try again.'; status.dataset.state = 'error';
      console.error('3D asset loading failed', error);
    }
  }
  assemblyButton.addEventListener('click', () => select('assembly'));
  list.addEventListener('click', event => { const button = event.target.closest('button[data-module]'); if (button) select(button.dataset.module); });
  $('#reset-button').addEventListener('click', () => { if (current) frame(current, selected); });
  renderer.setAnimationLoop(() => { controls.update(); renderer.render(scene,camera); });
  select('assembly');
}
