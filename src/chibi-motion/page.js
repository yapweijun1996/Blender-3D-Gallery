import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import "./style.css";

export async function mountMotion(root, asset, signal) {
  root.innerHTML = `<section class="motion-studio"><header><h1>Chibi Motion Studio</h1><p>GJH Virtual Mall Visitor</p></header>
    <div class="motion-layout"><div class="motion-stage" aria-label="3D character preview"></div>
    <fieldset disabled><legend>Animation</legend><div class="motion-clips"></div>
    <label>Timeline <input type="range" min="0" max="1000" value="0"></label>
    <output aria-label="Clip time"></output><button type="button" class="outline-button motion-play">Pause</button>
    <p>Drag to orbit. Scroll or pinch to zoom.</p></fieldset></div></section>`;
  const stage = root.querySelector(".motion-stage");
  const panel = root.querySelector("fieldset");
  const slider = panel.querySelector("input");
  const time = panel.querySelector("output");
  const play = panel.querySelector(".motion-play");
  const response = await fetch(asset.file, { signal });
  if (!response.ok) throw new Error("Character could not load");
  const gltf = await new GLTFLoader().parseAsync(await response.arrayBuffer(), "");
  const scene = gltf.scene;
  let renderer, controls, observer;
  const mixer = new THREE.AnimationMixer(scene);
  function dispose() {
    observer?.disconnect();
    controls?.dispose();
    mixer.stopAllAction();
    mixer.uncacheRoot(scene);
    scene.traverse(object => {
      object.geometry?.dispose();
      object.skeleton?.dispose();
      if (object.material) {
        for (const material of [].concat(object.material)) {
          material.map?.dispose();
          material.dispose();
        }
      }
    });
    renderer?.setAnimationLoop(null);
    renderer?.dispose();
    renderer?.forceContextLoss();
    renderer?.domElement.remove();
  }
  if (signal.aborted) return { dispose };
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0xeeeaf1);
    stage.append(renderer.domElement);
    const camera = new THREE.PerspectiveCamera(32, 1, .01, 20);
    camera.position.set(2.1, .76, .69);
    controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, .52, 0);
    controls.enablePan = false;
    controls.minDistance = 1;
    controls.maxDistance = 4;
    controls.update();
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(3, 5, 4);
    scene.add(new THREE.HemisphereLight(0xffffff, 0xffebdc, 2), light);
    const grid = new THREE.GridHelper(4, 40, 0xb9aec0, 0xd7cddd);
    grid.position.y = -.001;
    scene.add(grid);
    observer = new ResizeObserver(() => {
      const { width, height } = stage.getBoundingClientRect();
      if (!width || !height) return;
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    });
    observer.observe(stage);
    let action, previous, playing = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    function syncTime() {
      slider.value = 1000 * action.time / action.getClip().duration;
      time.value = action.time.toFixed(2) + " / " + action.getClip().duration.toFixed(2) + " s";
    }
    for (const name of ["Idle", "Wave", "Nod", "Walk"]) {
      const clip = THREE.AnimationClip.findByName(gltf.animations, name);
      if (!clip) throw new Error("Missing animation " + name);
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = name;
      button.setAttribute("aria-pressed", "false");
      panel.querySelector(".motion-clips").append(button);
      function select() {
        action?.stop();
        action = mixer.clipAction(clip).reset().play();
        mixer.update(0);
        for (const item of button.parentElement.children)
          item.setAttribute("aria-pressed", String(item === button));
        syncTime();
      }
      button.onclick = select;
      if (!action) select();
    }
    function setPlayback(value) {
      playing = value;
      play.textContent = playing ? "Pause" : "Play";
    }
    setPlayback(playing);
    play.onclick = () => setPlayback(!playing);
    slider.oninput = () => {
      setPlayback(false);
      action.time = Number(slider.value) / 1000 * (action.getClip().duration - .00001);
      mixer.update(0);
      syncTime();
    };
    panel.disabled = false;
    renderer.setAnimationLoop(now => {
      if (playing) mixer.update(Math.min((now - (previous ?? now)) / 1000, .1));
      previous = now;
      syncTime();
      renderer.render(scene, camera);
    });
  } catch (error) {
    dispose();
    throw error;
  }
  return { dispose };
}
