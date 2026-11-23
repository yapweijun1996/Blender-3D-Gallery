import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { assembleBakeryShop, bakeryPaths } from './bakery-shop.js';
import { assembleComputerShop, computerPaths } from './computer-shop.js';
import { assemblePharmacyBeauty, beautyPaths } from './pharmacy-beauty.js';
import { assembleHomeFurnishings, furnishingPaths } from './home-furnishings.js';
import { assembleRoom, roomArrival, roomAssetPaths } from './room-layout.js';
import { shopfrontBays } from './shopfront-layout.js';
import { batchStaticMeshes } from './batch-static.js';
import { arrival, assembleCorridor, corridorAssetPaths } from './corridor-layout.js';
import { shellLayout } from './shell-layout.js';
import { assembleCornerTileFloor, assembleFinishedFloorEdge, cornerFloorPath, floorEdgePaths } from './floor-edge.js';
import { assembleFloorTransition, floorTransitionPaths } from './floor-transition.js';
import { assembleCornerFloor, assembleWallCeiling, assembleWalledFloor, wallCornerPath, wallRunPath } from './wall-run.js';

import { createCollisionWorld } from '../docs/verification/mall-corridor/collision.js';
import { createVisitor } from '../docs/verification/mall-corridor/visitor.js';

const root = new URL('../', import.meta.url);
const asset = (path) => new URL(path, root).href;
const modules = [
  { id:'floor', number:'001', name:'Floor tile', detail:'1.2 m repeat module', kicker:'001 / THE FOUNDATION', subtitle:'Warm terrazzo floor, made to repeat.', path:corridorAssetPaths.floor, thumb:'models/mall-floor-tile/previews/mall-floor-tile-module.webp' },
  { id:'cornerTile', number:'C3', name:'Corner floor tile', detail:'1.2 m outside corner', kicker:'CORNER / THE FOUNDATION', subtitle:'A terrazzo corner tile with two inset border strips.', path:corridorAssetPaths.cornerTile, thumb:'models/mall-floor-corner-tile/previews/mall-floor-corner-tile.jpg' },
  { id:'mitredTrim', number:'C4', name:'Mitred floor trim', detail:'90° outside corner pair', kicker:'CORNER / THE MITRE', subtitle:'Two edge strips meeting in a 45° joint.', path:corridorAssetPaths.mitredTrim, thumb:'models/mall-floor-mitred-trim/previews/mall-floor-mitred-trim.jpg' },
  { id:'floorCorner', number:'C1', name:'Floor corner trim', detail:'60 mm outside corner cap', kicker:'CORNER / THE FLOOR EDGE', subtitle:'A square cap joining two straight edge strips.', path:'models/mall-floor-corner-trim/exports/mall-floor-corner-trim.glb', thumb:'models/mall-floor-corner-trim/previews/mall-floor-corner-trim.jpg' },
  { id:'wall', number:'003', name:'Solid wall', detail:'1.2 m repeat module', kicker:'003 / THE ENCLOSURE', subtitle:'A solid wall with warm panels and dark skirting.', path:corridorAssetPaths.wall, thumb:'models/mall-solid-wall/previews/mall-solid-wall.jpg' },
  { id:'wallCorner', number:'C2', name:'Wall corner', detail:'90° · 1.2 m arms', kicker:'CORNER / THE WALL', subtitle:'A right-angle corner connecting the solid wall modules.', path:corridorAssetPaths.wallCorner, thumb:'models/mall-wall-corner/previews/mall-wall-corner.jpg' },
  { id:'railing', number:'004', name:'Glass railing', detail:'2 m post-centred bay', kicker:'004 / THE EDGE', subtitle:'A glazed bay with posts, infill and handrail.', path:corridorAssetPaths.railing, thumb:'models/mall-glass-railing/previews/mall-glass-railing-2m.webp' },
  { id:'ceiling', number:'005', name:'Ceiling panel', detail:'1.2 m suspended cassette', kicker:'005 / ABOVE', subtitle:'A repeating ceiling cassette with recessed panels.', path:corridorAssetPaths.ceiling, thumb:'models/mall-ceiling-panel/previews/mall-ceiling-panel-module.webp' },
  { id:'column', number:'006', name:'Structural column', detail:'0.6 m × 3 m', kicker:'006 / THE SUPPORT', subtitle:'An ivory-clad square column, grounded at floor level.', path:corridorAssetPaths.column, thumb:'models/mall-structural-column/previews/mall-structural-column.webp' },
];
// Extra scene context is loaded only for the corridor, not individual views.
const furnishings = Object.entries(corridorAssetPaths)
  .filter(([id]) => !modules.some(item => item.id === id))
  .map(([id, path]) => ({ id, path }));
const transitionAssets = Object.entries(floorTransitionPaths).map(([id, path]) => ({ id, path }));
const cornerFloorAssets = [
  { id: 'floor2m', path: floorTransitionPaths.floor2m },
  { id: 'cornerFloor2m', path: cornerFloorPath },
];
const wallAssets = [...transitionAssets, { id: 'wall2m', path: wallRunPath }];
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
const transitionButton = $('#transition-button');
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
  function furnishedShop(id, name, subtitle, fixtures, assemble) {
    return {
      name, subtitle, showroom: true,
      inputs: Object.entries({ ...roomAssetPaths, ...fixtures }).map(([id, path]) => ({ id, path })),
      build: sources => shopScene(sources, id, assemble),
    };
  }
  const assemblies = {
    assembly: {
      name: 'The corridor', subtitle: 'A cutaway with shopfronts, lighting and corner modules.',
      inputs: [...modules, ...furnishings], build: corridor,
    },
    'floor-transition': {
      name: 'Floor grid transition', subtitle: 'Five 1.2 m bays meet three 2 m bays along a six-metre joint.',
      inputs: transitionAssets, build: assembleFloorTransition,
    },
    'corner-floor': {
      name: 'Outside floor corner', subtitle: 'Champagne and terrazzo bands follow the two outside edges of a four-tile floor.',
      inputs: cornerFloorAssets, build: assembleCornerTileFloor,
    },
    'finished-edge': {
      name: 'Finished floor edge', subtitle: 'Two straight profiles join the mitred return and cover the full depth of both exposed edges.',
      inputs: [...cornerFloorAssets, ...Object.entries(floorEdgePaths).map(([id, path]) => ({ id, path }))],
      build: assembleFinishedFloorEdge,
    },
    'wall-run': {
      name: 'Straight wall run', subtitle: 'Three 2 m walls stand on the finished floor, with their stone faces toward the aisle.',
      inputs: wallAssets,
      build: assembleWalledFloor,
    },
    'wall-ceiling': {
      name: 'Wall and ceiling', subtitle: 'Five ceiling cassettes sit at the 2.8 m wall head. The front stays open for inspection.',
      inputs: [...wallAssets, byId.ceiling],
      build: sources => assembleWalledFloor(sources).add(assembleWallCeiling(sources.ceiling)),
    },
    'enclosed-shop': {
      name: 'Enclosed shop', subtitle: 'Open the doors to walk inside the six-metre shop. Show the ceiling to inspect the closed shell.',
      inputs: Object.entries(roomAssetPaths).map(([id, path]) => ({ id, path })),
      build: sources => shopScene(sources, 'enclosed-shop', assembleRoom),
    },
    'bakery-shop': furnishedShop('bakery-shop', 'Bakery shop',
      'Inspect the serving tongs and toast trays, or walk around the glazed pastry cabinet.',
      bakeryPaths, assembleBakeryShop),
    'computer-shop': furnishedShop('computer-shop', 'Computer shop',
      'Walk around the demo table, inspect the tethered laptop or browse the electronics shelf.',
      computerPaths, assembleComputerShop),
    'pharmacy-beauty': furnishedShop('pharmacy-beauty', 'Pharmacy and beauty shop',
      'Inspect the shade samples, browse the shelves or walk up to the service counter.',
      beautyPaths, assemblePharmacyBeauty),
    'home-furnishings': furnishedShop('home-furnishings', 'Home furnishings shop',
      'Walk through the furnished displays or inspect the room from above.',
      furnishingPaths, assembleHomeFurnishings),
    'wall-corner': {
      name: 'Right-angle wall corner', subtitle: 'The inside finishes turn from the rear wall onto the return along the right edge.',
      inputs: [...wallAssets, { id: 'wallCorner2m', path: wallCornerPath }],
      build: assembleCornerFloor,
    },
  };
  let current = null; let requestId = 0; let selected = 'assembly';
  const walkableScenes = new Map();
  let shopSigns, visitor, visitorRequest;
  const activeWalkScene = () => {
    const state = walkableScenes.get(selected);
    return state && state.group === current ? state : null;
  };
  const walkTools = $('#walk-tools');
  const doorButton = $('#doors');
  const walkButton = $('#walk');
  const message = $('#walk-message');
  function corridor(sources) {
    if (walkableScenes.has('assembly')) return walkableScenes.get('assembly').group;
    const { group, poseDoors } = assembleCorridor(sources);
    const world = createCollisionWorld(group);
    batchStaticMeshes(group);

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
    for (const placement of shellLayout.ceiling) {
      const { x, z, omit } = placement;
      if (omit) {
        const glow = new THREE.PointLight(0xffe5bb, 1.2, 4, 2);
        glow.position.set(x-.3,2.82,z+.3); group.add(glow);
      }
    }
    walkableScenes.set('assembly', { group, poseDoors, world, spawn: arrival, doorAngle: 0 });
    return group;
  }

  function shopScene(sources, id, assemble) {
    if (walkableScenes.has(id)) return walkableScenes.get(id).group;
    const room = assemble(sources);
    const world = createCollisionWorld(room.group);
    room.batchStatic();
    walkableScenes.set(id, { ...room, world, spawn: roomArrival, doorAngle: 0 });
    return room.group;
  }

  let inspection = null;
  const inspectButton = $('#inspect-fixture');
  inspectButton.addEventListener('click', () => {
    const focus = activeWalkScene()?.inspection;
    if (!focus) return;
    if (visitor?.state.walking) visitor.setWalking(false);
    inspection = focus;
    frame(focus.object, selected, focus);
  });
  const roofButton = $('#shop-roof');
  function showWalkControls() {
    const active = activeWalkScene();
    walkTools.hidden = !active;
    if (!active) return;
    doorButton.textContent = active.doorAngle ? 'Close doors' : 'Open doors';
    doorButton.setAttribute('aria-pressed', String(Boolean(active.doorAngle)));
    inspectButton.hidden = !active.inspection;
    if (active.inspection) inspectButton.textContent = active.inspection.label;
    roofButton.hidden = !active.roof;
    if (active.roof) {
      roofButton.setAttribute('aria-pressed', String(active.roof.visible));
      roofButton.textContent = active.roof.visible ? 'Hide ceiling' : 'Show ceiling';
    }
    if (visitor && visitor.visual.parent !== active.group) {
      visitor.setEnvironment(active.group, active.world, active.spawn);
    }
  }
  roofButton.addEventListener('click', () => {
    const room = activeWalkScene();
    if (!room?.roof) return;
    room.setRoofVisible(!room.roof.visible);
    showWalkControls();
    if (visitor?.state.walking) renderer.domElement.focus({ preventScroll: true });
  });

  function inspectAssembly() {
    inspection = null;
    camera.fov = 34;
    camera.updateProjectionMatrix();
    if (current) frame(current, selected);
  }
  renderer.domElement.addEventListener('focus', () => {
    if (visitor?.state.walking) wrap.scrollIntoView({ block: 'nearest' });
  });
  doorButton.addEventListener('click', () => {
    const active = activeWalkScene();
    if (!active) return;
    const { doorAngle, world, poseDoors } = active;
    const next = doorAngle === 0 ? 90 : 0;
    visitor?.clearInput();
    if (visitor?.state.walking) renderer.domElement.focus({ preventScroll: true });
    if (visitor && !world.doorTransition(doorAngle, next, visitor.visual.position, poseDoors)) {
      message.textContent = 'The doorway was occupied. Doors stayed ' + (doorAngle ? 'open.' : 'closed.');
      return;
    }
    if (!visitor) { poseDoors(next); world.refresh(); }
    active.doorAngle = next;
    showWalkControls();
    message.textContent = next ? 'Shop doors open.' : 'Shop doors closed.';
  });
  // Keep the visitor GLB off the initial orbit view and share one controller
  // across the corridor and shop, including an assembly change during loading.
  walkButton.onclick = async () => {
    const active = activeWalkScene();
    if (!active || visitorRequest) return;
    const request = requestId;
    walkButton.disabled = true;
    message.textContent = 'Loading visitor…';
    try {
      visitorRequest = createVisitor({ scene: active.group, world: active.world,
        camera, controls, canvas: renderer.domElement, spawn: active.spawn, onInspect: inspectAssembly,
        onMessage: text => { message.textContent = text; } });
      visitor = await visitorRequest;
      $('#reset-visitor').hidden = false;
      message.textContent = '';
      showWalkControls();
      if (request === requestId && active === activeWalkScene() && !inspection) visitor.setWalking(true);
    } catch (error) {
      message.textContent = 'Unable to load the visitor. Select Walk visitor to retry.';
      console.error('Visitor loading failed', error);
    } finally {
      walkButton.disabled = false;
      visitorRequest = null;
    }
  };
  wrap.inspectVisitor = () => ({ angle: activeWalkScene()?.doorAngle ?? 0, visitor: visitor?.state ?? null, drawCalls: renderer.info.render.calls });

  function frame(object, id, focus = null) {
    object.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(object); const sphere = box.getBoundingSphere(new THREE.Sphere());
    if (focus) object.localToWorld(sphere.center.fromArray(focus.target));
    controls.target.copy(sphere.center);
    const vertical = THREE.MathUtils.degToRad(camera.fov/2); const horizontal = Math.atan(Math.tan(vertical)*camera.aspect);
    let margin = 1.2;
    if (assemblies[id]) margin = id === 'assembly' ? (camera.aspect < 1.35 ? 1.08 : .8) : .94;
    // Bring the display furniture forward while keeping the entrance in frame.
    if (assemblies[id]?.showroom) margin = .67;
    const radius = focus ? focus.radius : Math.max(sphere.radius, .25) * margin;
    const distance = radius / Math.sin(Math.min(vertical,horizontal));
    const direction = new THREE.Vector3(6,4,7);
    if (id === 'ceiling') direction.set(4,-3,5);
    if (id === 'assembly') direction.set(6,3.5,10);
    if (assemblies[id]?.showroom) direction.set(1.2,7.6,5.2);
    if (id === 'enclosed-shop') direction.set(2.3,4.8,7);
    if (id === 'finished-edge') direction.set(3.7,2.6,5.1);
    if (id === 'corner-floor') direction.set(3.5,5.3,5.2);
    if (id === 'floor-transition') direction.set(1.2,5.5,5.1);
    if (id === 'wall-run' || id === 'wall-ceiling') direction.set(2.3,2.6,6);
    if (id === 'wall-corner') direction.set(-3.1,2.8,5.4);
    if (focus) direction.fromArray(focus.direction).transformDirection(object.matrixWorld);
    camera.position.copy(sphere.center).add(direction.normalize().multiplyScalar(distance));
    controls.minDistance = Math.max(.2, sphere.radius * .65); controls.maxDistance = Math.max(10, sphere.radius * 12);
    camera.near = Math.max(.01, distance / 100); camera.far = distance * 20; camera.updateProjectionMatrix(); controls.update();
  }
  function resize() { const {width,height} = wrap.getBoundingClientRect(); if (!width || !height) return; renderer.setSize(width,height,false); camera.aspect=width/height; camera.updateProjectionMatrix(); if (current && !visitor?.state.walking) frame(inspection?.object ?? current, selected, inspection); }
  new ResizeObserver(resize).observe(wrap); resize();
  async function select(id) {
    inspection = null;
    if (visitor?.state.walking) visitor.setWalking(false);
    walkTools.hidden = true;
    message.textContent = '';
    selected = id; const request = ++requestId;
    const item = byId[id], view = item ?? assemblies[id];
    const gridView = !item && id !== 'assembly';
    $('#view-kicker').textContent = view.kicker ?? 'THE ASSEMBLY';
    $('#view-title').textContent = view.name;
    $('#view-subtitle').textContent = view.subtitle;
    assemblyButton.classList.toggle('active', id === 'assembly'); assemblyButton.setAttribute('aria-pressed', String(id === 'assembly'));
    transitionButton.classList.toggle('active', gridView); transitionButton.setAttribute('aria-pressed', String(gridView));
    $('#grid-option').hidden = !gridView;
    if (gridView) $('#grid-layout').value = id;
    for (const button of list.querySelectorAll('button')) button.setAttribute('aria-pressed', String(button.dataset.module === id));
    status.textContent = 'Loading 3D model…'; status.dataset.state = 'loading';
    try {
      const needed = item ? [item] : view.inputs;
      const loaded = await Promise.all(needed.map(async m => [m.id, await load(m)]));
      if (request !== requestId) return;
      if (current) scene.remove(current);
      const sources = Object.fromEntries(loaded);
      current = item ? sources[id].clone(true) : view.build(sources);
      scene.add(current); frame(current,id);
      status.textContent = ''; status.dataset.state = 'ready'; wrap.dataset.view = id; showWalkControls();
    } catch (error) {
      if (request !== requestId) return;
      if (current) { scene.remove(current); current = null; }
      status.textContent = 'Unable to load the 3D model. Select the view to try again.'; status.dataset.state = 'error';
      console.error('3D asset loading failed', error);
    }
  }
  assemblyButton.addEventListener('click', () => select('assembly'));
  transitionButton.addEventListener('click', () => select('floor-transition'));
  $('#grid-layout').addEventListener('change', event => select(event.target.value));
  list.addEventListener('click', event => { const button = event.target.closest('button[data-module]'); if (button) select(button.dataset.module); });
  $('#reset-button').addEventListener('click', () => { if (visitor?.state.walking) visitor.setWalking(false); else inspectAssembly(); });
  let lastFrame;
  renderer.setAnimationLoop(now => {
    const dt = lastFrame === undefined ? 0 : (now - lastFrame) / 1000;
    lastFrame = now;
    if (visitor && current === visitor.visual.parent) {
      visitor.visual.visible = !inspection || !controls.enabled;
      visitor.update(dt);
    }
    if (controls.enabled) controls.update();
    renderer.render(scene,camera);
  });
  const requested = new URLSearchParams(location.search).get('view');
  select(Object.hasOwn(assemblies, requested) ? requested : 'assembly');
}
