import { localize, t } from '../i18n/index.js';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import shopperUrl from '../../models/mall-shopper/exports/mall-shopper.glb?url';

// The cart GLB is independently reusable; the character, controls and obstacle
// below are a bounded gallery demonstration, not a general physics engine.
export default async function createCartDemo({ model, scene, container, signal, invalidate }) {
  const response = await fetch(shopperUrl, { signal });
  if (!response.ok) throw new Error('Unable to load the shopping cart demonstration character');
  const bytes = await response.arrayBuffer();
  const shopper = (await new GLTFLoader().parseAsync(bytes, THREE.LoaderUtils.extractUrlBase(new URL(shopperUrl, document.baseURI).href)));
  if (signal.aborted) {
    shopper.scene.traverse(node => { node.geometry?.dispose(); if (node.material) [].concat(node.material).forEach(m => m.dispose()); });
    throw new DOMException('Viewer closed', 'AbortError');
  }
  const required = name => {
    const node = model.getObjectByName(name);
    if (!node) throw new Error(`Cart rig is missing ${name}`);
    return node;
  };
  const wheels = ['FrontLeft', 'FrontRight', 'RearLeft', 'RearRight'].map(name => required(`Wheel_${name}`));
  const steering = ['FrontLeft', 'FrontRight'].map(name => required(`Steer_${name}`));
  const item = required('BasketItem');
  const itemHome = item.position.clone();
  item.visible = false;

  const group = new THREE.Group();
  const vehicle = new THREE.Group();
  scene.add(group); group.add(vehicle); vehicle.add(model);
  const character = shopper.scene;
  character.position.set(0, 0, -0.75);
  character.traverse(node => {
    if (/^(ShoppingBag|Bag|ToolGrip|OccupationTool)/.test(node.name)) node.visible = false;
  });
  vehicle.add(character);
  const obstacle = new THREE.Mesh(new THREE.BoxGeometry(.8, .5, .25), new THREE.MeshStandardMaterial({ color: 0xa2643f, roughness: .8 }));
  obstacle.position.set(0, .25, 2.1); group.add(obstacle);
  const obstacleBounds = new THREE.Box3().setFromObject(obstacle);
  const mixer = new THREE.AnimationMixer(character);
  const walk = shopper.animations.find(clip => clip.name === 'WalkInPlace');
  const action = walk ? mixer.clipAction(walk) : null;
  const arms = ['Left', 'Right'].map(side => ({
    shoulder: character.getObjectByName(`${side}Shoulder`),
    elbow: character.getObjectByName(`${side}Elbow`),
    hand: character.getObjectByName(`${side}Hand`),
    x: side === 'Left' ? -.22 : .22,
  }));
  if (arms.some(a => !a.shoulder || !a.elbow || !a.hand)) throw new Error('Shopper hand rig is unavailable');
  const rest = arms.map(a => [a.shoulder.quaternion.clone(), a.elbow.quaternion.clone()]);
  const steerRest = steering.map(o => o.rotation.y);
  let grabbed = false, speed = 0, targetSpeed = 0, angle = 0, state = 'Idle';
  let itemState = 'absent', itemProgress = 0;
  let active = true;
  const toolbar = document.createElement('div');
  toolbar.className = 'cart-demo';
  toolbar.setAttribute('role', 'group');
  localize(toolbar, 'cart.demo', undefined, 'aria-label');
  const title = document.createElement('strong'); localize(title, 'cart.controls');
  const status = document.createElement('p'); status.className = 'cart-demo-status'; status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  const buttons = document.createElement('div'); buttons.className = 'cart-demo-buttons';
  const button = (id, label, callback) => {
    const b = document.createElement('button'); b.type = 'button'; localize(b, label); b.dataset.cartAction = id;
    b.addEventListener('click', () => { callback(); renderStatus(); invalidate(); }); buttons.append(b); return b;
  };
  const say = value => { state = value; };
  const grab = button('grab', 'cart.grab', () => { grabbed = true; say('Grab'); });
  const push = button('push', 'cart.push', () => { targetSpeed = .42; action?.play(); say(angle ? 'Turn' : 'Push'); });
  button('left', 'clip.turnLeft', () => { angle = -.55; say('Turn'); });
  button('straight', 'cart.straight', () => { angle = 0; say(targetSpeed ? 'Push' : 'Idle'); });
  button('right', 'clip.turnRight', () => { angle = .55; say('Turn'); });
  const stop = button('stop', 'cart.stop', () => { targetSpeed = 0; say('Stop'); });
  const release = button('release', 'cart.release', () => { targetSpeed = 0; grabbed = false; say('Release'); });
  const add = button('add', 'cart.add', () => { itemState = 'adding'; itemProgress = 0; item.visible = true; say('Add Item'); });
  const remove = button('remove', 'cart.remove', () => { itemState = 'removing'; itemProgress = 0; say('Remove Item'); });
  const resetButton = button('reset', 'cart.reset', () => reset());
  toolbar.append(title, status, buttons); container.insertAdjacentElement('afterend', toolbar);
  const stateKeys = {
    Idle: 'clip.idle', Grab: 'cart.grab', Push: 'cart.push', Turn: 'cart.turn', Stop: 'cart.stop',
    Release: 'cart.release', 'Add Item': 'cart.addState', 'Remove Item': 'cart.removeState',
  };
  function renderStatus() {
    const stateKey = stateKeys[state];
    localize(status, state === 'Collision' ? 'cart.collision' : 'cart.state',
      stateKey && (() => ({ state: t(stateKey) })));
    toolbar.dataset.state = state; toolbar.dataset.item = itemState;
    grab.disabled = grabbed; push.disabled = !grabbed || state === 'Collision';
    stop.disabled = !speed && !targetSpeed; release.disabled = !grabbed;
    add.disabled = itemState !== 'absent'; remove.disabled = itemState !== 'present';
    resetButton.disabled = false;
  }
  function poseHands() {
    // The source character is a rigid joint hierarchy, so use a small CCD solve
    // in the demo to bring each hand to the cart's handle without changing its GLB.
    for (let i = 0; i < arms.length; i++) {
      const a = arms[i]; a.shoulder.quaternion.copy(rest[i][0]); a.elbow.quaternion.copy(rest[i][1]);
      if (!grabbed) continue;
      const target = vehicle.localToWorld(new THREE.Vector3(a.x, .98, -.47));
      for (let pass = 0; pass < 16; pass++) for (const joint of [a.elbow, a.shoulder]) {
        group.updateMatrixWorld(true);
        const origin = joint.getWorldPosition(new THREE.Vector3());
        const hand = a.hand.getWorldPosition(new THREE.Vector3());
        const from = hand.sub(origin).normalize(), to = target.clone().sub(origin).normalize();
        if (from.lengthSq() < .9 || to.lengthSq() < .9) continue;
        const worldDelta = new THREE.Quaternion().setFromUnitVectors(from, to);
        const parentWorld = joint.parent.getWorldQuaternion(new THREE.Quaternion());
        const localDelta = parentWorld.clone().invert().multiply(worldDelta).multiply(parentWorld);
        joint.quaternion.premultiply(localDelta).normalize();
      }
    }
    group.updateMatrixWorld(true);
  }
  function reset() {
    grabbed = false; speed = targetSpeed = angle = 0; state = 'Idle'; itemState = 'absent'; itemProgress = 0;
    vehicle.position.set(0,0,0); vehicle.rotation.set(0,0,0);
    wheels.forEach(w => { w.rotation.x = 0; }); steering.forEach((w,i) => { w.rotation.y = steerRest[i]; });
    item.position.copy(itemHome); item.visible = false; action?.stop(); poseHands(); renderStatus();
  }
  function update(dt) {
    if (!active) return false;
    dt = Math.min(dt, .05);
    const delta = Math.min(Math.abs(targetSpeed-speed), dt * .8);
    speed += Math.sign(targetSpeed-speed) * delta;
    steering.forEach((wheel, i) => { wheel.rotation.y = steerRest[i] + angle; });
    if (Math.abs(speed) > .0001) {
      const before = vehicle.position.clone(), yaw = vehicle.rotation.y;
      vehicle.rotation.y += speed * Math.tan(angle) * dt / .8;
      vehicle.position.x += Math.sin(vehicle.rotation.y) * speed * dt;
      vehicle.position.z += Math.cos(vehicle.rotation.y) * speed * dt;
      group.updateMatrixWorld(true);
      const cartBounds = new THREE.Box3().setFromObject(model);
      if (cartBounds.intersectsBox(obstacleBounds)) {
        vehicle.position.copy(before); vehicle.rotation.y = yaw;
        speed = targetSpeed = 0; action?.stop(); say('Collision'); renderStatus();
      } else {
        wheels.forEach(w => { w.rotation.x += speed * dt / .079; });
        if (action) mixer.update(dt);
      }
    } else if (!targetSpeed) { if (speed) { speed = 0; renderStatus(); } action?.stop(); }
    if (itemState === 'adding' || itemState === 'removing') {
      itemProgress = Math.min(1, itemProgress + dt / .6);
      const t = itemProgress * itemProgress * (3 - 2 * itemProgress);
      item.position.y = itemHome.y + .48 * (itemState === 'adding' ? 1-t : t);
      if (itemProgress === 1) { itemState = itemState === 'adding' ? 'present' : 'absent'; item.visible = itemState === 'present'; renderStatus(); }
    }
    poseHands();
    toolbar.dataset.speed = speed.toFixed(3);
    toolbar.dataset.position = vehicle.position.z.toFixed(3);
    toolbar.dataset.heading = vehicle.rotation.y.toFixed(3);
    toolbar.dataset.steering = angle.toFixed(3);
    toolbar.dataset.wheel = wheels[0].rotation.x.toFixed(3);
    toolbar.dataset.wheels = wheels.map(wheel => wheel.rotation.x.toFixed(3)).join(',');
    toolbar.dataset.frontSteering = steering.map((wheel, i) => (wheel.rotation.y - steerRest[i]).toFixed(3)).join(',');
    toolbar.dataset.itemHeight = item.position.y.toFixed(3);
    toolbar.dataset.itemVisible = String(item.visible);
    if (grabbed) toolbar.dataset.handGap = Math.max(...arms.map(a => a.hand.getWorldPosition(new THREE.Vector3()).distanceTo(vehicle.localToWorld(new THREE.Vector3(a.x, .98, -.47))))).toFixed(4);
    else delete toolbar.dataset.handGap;
    return Math.abs(speed) > .0001 || targetSpeed !== 0 || itemState === 'adding' || itemState === 'removing';
  }
  function dispose() {
    active = false; action?.stop(); mixer.stopAllAction(); toolbar.remove();
    obstacle.geometry.dispose(); obstacle.material.dispose();
    character.traverse(node => { node.geometry?.dispose(); if (node.material) [].concat(node.material).forEach(m => m.dispose()); });
    group.remove(vehicle); scene.remove(group);
  }
  reset();
  return { group, update, reset, dispose };
}
