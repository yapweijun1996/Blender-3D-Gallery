import { fitProductDistance, setProductView } from "./camera.js";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { createPoseController } from "./pose.js";
import "./style.css";

export async function mountProductStudio(root, asset, signal) {
  if (!asset) throw new Error("Demo packaging asset is unavailable");
  if (signal.aborted) throw new DOMException("Navigation cancelled", "AbortError");
  root.innerHTML = `<section class="product-studio">
    <header class="ps-heading"><div><p class="ps-kicker">PRODUCT PACKAGING / FIRST STUDY</p><h1>Product Studio<span>.</span></h1></div><p>One original tin. Inspect the form, lift the lid and explore its parts.</p></header>
    <div class="ps-layout"><div class="ps-stage" aria-busy="true"><p class="ps-loading" role="status">Loading the demo tin…</p></div>
    <aside class="ps-panel"><span class="ps-demo">FICTIONAL DEMO</span><h2>Food tin / 01</h2><p>An unbranded packaging concept. Not a real product, food label or manufacturing specification.</p>
    <div class="ps-actions"><button type="button" data-action="open" aria-pressed="false" disabled>Open lid</button><button type="button" data-action="explode" aria-pressed="false" disabled>Exploded view</button><button type="button" data-action="reset" disabled>Reset product &amp; camera</button></div>
    <fieldset class="ps-views" disabled><legend>Inspect a side</legend><div class="ps-view-grid"><button data-view="front">Front</button><button data-view="back">Back</button><button data-view="left">Left</button><button data-view="right">Right</button><button data-view="top">Top</button><button data-view="bottom">Bottom</button></div></fieldset>
    <p class="ps-status" aria-live="polite">Preparing controls.</p><p class="ps-note">Original Blender geometry and fictional DEMO artwork. Lid lift and exploded separation are illustrative, not a can-opening simulation. Online only; not in the offline Game pack.</p></aside></div>
    <p class="ps-hint">Drag or swipe to orbit · Scroll or pinch to zoom · Focus the 3D view and use arrow keys to orbit, + / − to zoom, Home to reset.</p>
  </section>`;
  const $ = s => root.querySelector(s), stage = $(".ps-stage"), loading = $(".ps-loading"), status = $(".ps-status");
  const local = new AbortController();
  const media = matchMedia("(prefers-reduced-motion: reduce)");
  let disposed = false, renderer, controls, observer, environment, model, poses;
  let frame = 0, dirty = true, ready = false, animation = null, mode = "closed", amount = 0;
  let targetMode = "closed", targetAmount = 0, lastTime = 0;
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(35, 1, .001, 10);
  const resources = new Set();
  const disposeObject = object => object?.traverse(child => {
    if (child.geometry && !resources.has(child.geometry)) { resources.add(child.geometry); child.geometry.dispose(); }
    for (const material of child.material ? [].concat(child.material) : []) {
      if (resources.has(material)) continue; resources.add(material);
      for (const value of Object.values(material)) if (value?.isTexture && !resources.has(value)) { resources.add(value); value.dispose(); value.image?.close?.(); }
      material.dispose();
    }
  });
  function dispose() {
    if (disposed) return;
    disposed = true; local.abort(); signal.removeEventListener("abort", dispose);
    cancelAnimationFrame(frame); frame = 0; observer?.disconnect(); controls?.dispose();
    poses?.dispose(); disposeObject(model); environment?.dispose();
    renderer?.dispose(); renderer?.domElement.remove();
    media.removeEventListener("change", reducedMotion);
  }
  signal.addEventListener("abort", dispose, { once: true });
  function invalidate() { dirty = true; if (!disposed && !document.hidden && !frame) frame = requestAnimationFrame(render); }
  function report() {
    if (!ready || disposed) return;
    const opening = targetMode === "open" && targetAmount === 1, exploding = targetMode === "exploded" && targetAmount === 1;
    $('[data-action="open"]').setAttribute("aria-pressed", String(opening));
    $('[data-action="open"]').textContent = opening ? "Close lid" : "Open lid";
    $('[data-action="explode"]').setAttribute("aria-pressed", String(exploding));
    $('[data-action="explode"]').textContent = exploding ? "Assemble product" : "Exploded view";
    status.textContent = animation ? "Moving parts…" : mode === "closed" || amount === 0 ? "Assembled · lid closed" : mode === "open" ? "Lid open · illustrative lift" : "Exploded · parts separated";
    stage.dataset.pose = animation ? "moving" : amount === 0 ? "closed" : mode;
  }
  function setPose(next, end = 1, immediate = false) {
    if (!ready || disposed) return;
    targetMode = next; targetAmount = end;
    if (next !== mode) { poses.apply("closed"); amount = 0; mode = next; }
    if (immediate || media.matches || next === "closed") { amount = next === "closed" ? 0 : end; poses.apply(next, amount); animation = null; }
    else animation = { start: amount, end, elapsed: 0 };
    lastTime = 0; report(); invalidate();
  }
  function reducedMotion() { if (media.matches && animation) setPose(targetMode, targetAmount, true); }
  media.addEventListener("change", reducedMotion);
  const center = new THREE.Vector3();
  let distance = .4, modelRadius = 0;
  function fitDistance() { return fitProductDistance(modelRadius,camera.aspect,camera.fov); }
  function view(name) {
    if (!ready || disposed) return;
    setProductView(camera,controls,center,distance,name); invalidate();
  }
  function reset() { setPose("closed", 0, true); view("front"); }
  function render(now) {
    frame = 0; if (disposed || document.hidden) return;
    if (animation) {
      animation.elapsed += lastTime ? Math.min((now-lastTime)/1000,.05) : 0;
      const p = Math.min(animation.elapsed/.45,1); amount = animation.start + (animation.end-animation.start)*p;
      poses.apply(mode, amount); dirty = true;
      if (p===1) { animation = null; report(); }
    }
    lastTime = now;
    if (dirty) { renderer.render(scene,camera); dirty = false; }
    if (animation) frame=requestAnimationFrame(render);
  }
  try {
    renderer = new THREE.WebGLRenderer({ antialias:true });
    renderer.setPixelRatio(Math.min(devicePixelRatio,1.5)); renderer.setClearColor(0xe6e8df);
    renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1;
    const canvas=renderer.domElement; canvas.tabIndex=0; canvas.setAttribute("role","img");
    canvas.setAttribute("aria-label","Fictional demo food tin. Arrow keys orbit, plus and minus zoom, Home resets. Product controls follow.");
    stage.append(canvas);
    controls = new OrbitControls(camera,canvas); controls.enableDamping=false; controls.enablePan=false;
    controls.addEventListener("change",invalidate);
    scene.add(new THREE.HemisphereLight(0xffffff,0x566356,2.2));
    const light=new THREE.DirectionalLight(0xffffff,2.4);light.position.set(.3,.5,.4);scene.add(light);
    const room=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer);
    try { environment=pmrem.fromScene(room,.04);scene.environment=environment.texture;scene.environmentIntensity=.75; } finally { room.dispose();pmrem.dispose(); }
    observer=new ResizeObserver(()=>{const w=stage.clientWidth,h=stage.clientHeight;if(w&&h){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();if(ready){const old=distance;distance=fitDistance();const offset=camera.position.clone().sub(controls.target);camera.position.copy(controls.target).add(offset.multiplyScalar(distance/old));controls.maxDistance=Math.max(modelRadius*12,distance*3);controls.update();}invalidate();}});
    observer.observe(stage);
    canvas.addEventListener("webglcontextlost",event=>{event.preventDefault();dispose();root.querySelectorAll("button").forEach(b=>b.disabled=true);$(".ps-views").disabled=true;stage.setAttribute("aria-busy","false");status.textContent="3D view interrupted. Return to Interactive Demos and reopen Product Studio.";},{signal:local.signal});
    document.addEventListener("visibilitychange",()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;lastTime=0;}else invalidate();},{signal:local.signal});
    const response=await fetch(asset.file,{signal:local.signal});const buffer=await response.arrayBuffer();
    if(!response.ok) throw new Error("Packaging model request failed: "+response.status);
    if(disposed||signal.aborted) throw new DOMException("Navigation cancelled","AbortError");
    const gltf=await new GLTFLoader().parseAsync(buffer,THREE.LoaderUtils.extractUrlBase(new URL(asset.file,document.baseURI).href));
    if(disposed||signal.aborted){disposeObject(gltf.scene);throw new DOMException("Navigation cancelled","AbortError");}
    model=gltf.scene;poses=createPoseController(gltf);scene.add(model);
    const bounds=new THREE.Box3();
    for(const state of ["closed","open","exploded"]){poses.apply(state);bounds.union(new THREE.Box3().setFromObject(model));}
    poses.apply("closed");if(bounds.isEmpty()) throw new Error("Packaging model has no visible geometry");
    bounds.getCenter(center);const radius=bounds.getSize(new THREE.Vector3()).length()/2;
    modelRadius=radius;camera.aspect=stage.clientWidth/stage.clientHeight;distance=fitDistance();
    camera.near=radius/80;camera.far=radius*80;controls.minDistance=radius*1.2;controls.maxDistance=Math.max(radius*12,distance*3);
    ready=true;$(".ps-views").disabled=false;root.querySelectorAll(".ps-actions button").forEach(b=>b.disabled=false);
    loading.remove();stage.setAttribute("aria-busy","false");
    $('[data-action="open"]').addEventListener("click",()=>setPose("open",targetMode==="open"&&targetAmount===1?0:1),{signal:local.signal});
    $('[data-action="explode"]').addEventListener("click",()=>setPose("exploded",targetMode==="exploded"&&targetAmount===1?0:1),{signal:local.signal});
    $('[data-action="reset"]').addEventListener("click",reset,{signal:local.signal});
    root.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>view(b.dataset.view),{signal:local.signal}));
    canvas.addEventListener("keydown",event=>{
      const key=event.key;if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","+","=","-","Home"].includes(key))return;
      event.preventDefault();if(key==="Home"){reset();return;}
      const offset=camera.position.clone().sub(controls.target),spherical=new THREE.Spherical().setFromVector3(offset);
      if(key==="ArrowLeft")spherical.theta-=Math.PI/18;if(key==="ArrowRight")spherical.theta+=Math.PI/18;
      if(key==="ArrowUp")spherical.phi-=Math.PI/18;if(key==="ArrowDown")spherical.phi+=Math.PI/18;
      if(key==="+"||key==="=")spherical.radius*=.85;if(key==="-")spherical.radius/= .85;
      spherical.phi=THREE.MathUtils.clamp(spherical.phi,.01,Math.PI-.01);spherical.radius=THREE.MathUtils.clamp(spherical.radius,controls.minDistance,controls.maxDistance);
      camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));controls.update();invalidate();
    },{signal:local.signal});
    reset();return { dispose };
  } catch(error) { dispose();throw error; }
}
