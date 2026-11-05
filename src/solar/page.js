import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import "./style.css";
import { solarSceneAssets as buildSolarSceneAssets } from "./assets.js";

// URL imports remain lazy: the browser fetches each GLB only when the scene loads.
const demoUrls = import.meta.glob('/models/solar-demo/*.glb', {
  eager: true, query: '?url', import: 'default',
});
export function solarSceneAssets(assets) {
  return buildSolarSceneAssets(assets).map(asset => {
    const url = demoUrls[`/models/solar-demo/${asset.id}.glb`];
    if (!url) throw new Error(`Missing optimized solar model: ${asset.id}`);
    return { ...asset, file: url };
  });
}

/** Independent GLBs remain authoritative. This scene only owns display transforms. */
export async function mountSolar(root, assets, signal) {
  root.innerHTML = `<section class="solar-heading"><div><p class="eyebrow">AN ATLAS IN MOTION</p><h1>Solar System<span class="period">.</span></h1></div><p>NASA models and original asteroids · One connected view</p></section>
  <div class="solar-toolbar"><label>Time speed <select id="solar-speed"><option value="0">Paused</option><option value="1">1 day / second</option><option value="10" selected>10 days / second</option><option value="100">100 days / second</option></select></label><label>Scale <select id="solar-scale"><option value="presentation">Presentation</option><option value="realistic">Realistic ratios</option></select></label><label>Explore <select id="solar-select"><option value="">Choose a body</option></select></label><button id="solar-overview" type="button">Overview ↺</button></div>
  <p class="solar-note" id="solar-scale-note">Presentation mode enlarges bodies and compresses distances. Planetary orbits illustrate relative periods; small-body paths and all positions are illustrative.</p>
  <div class="solar-layout"><div class="solar-canvas" id="solar-canvas"><p role="status" id="solar-status">Loading 17 independent models…</p></div><aside class="solar-info" aria-live="polite"><p class="eyebrow">FIELD NOTES</p><h2 id="solar-name">Our planetary neighborhood</h2><p id="solar-facts">Drag to orbit · Scroll or pinch to zoom. Select a body to inspect it.</p><p id="solar-accuracy">Planet dimensions, periods and tilts use NASA reference fact sheets. Models include NASA resources and original procedural asteroids; select a body for credits and limitations.</p><a id="solar-model-link" hidden>Open individual model ↗</a><p class="solar-small">Sun illumination and star positions are illustrative. The asteroid belt and comet trajectory are illustrative, not actual positions. This demo is available online; it is not part of the prepared offline Game pack.</p></aside></div>`;
  const $ = (s) => root.querySelector(s),
    container = $("#solar-canvas"),
    status = $("#solar-status");
  const overviewInfo = ["#solar-name", "#solar-facts", "#solar-accuracy"]
    .map((selector) => $(selector).textContent);
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true });
  } catch {
    status.textContent =
      "WebGL is unavailable. Open Gallery to view the model previews.";
    return {
      dispose() {
        root.replaceChildren();
      },
    };
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setClearColor(0x101717);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.domElement.setAttribute("role", "img");
  renderer.domElement.setAttribute(
    "aria-label",
    "Solar system. Use the Explore selector to choose and focus each body.",
  );
  container.append(renderer.domElement);
  const scene = new THREE.Scene(),
    camera = new THREE.PerspectiveCamera(45, 1, 0.001, 20000),
    controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.maxDistance = 1500;
  controls.minDistance = 0.0001;
  scene.add(new THREE.HemisphereLight(0xc7d9ed, 0x222a31, 1.15));
  const sunlight = new THREE.PointLight(0xffefcf, 2.4, 0, 0);
  scene.add(sunlight);
  const loaded = new Map(),
    bodies = new Map(),
    disposables = new Set(),
    unreleasedImages = new Set();
  let orbitLines,
    belt,
    needsRender = true;
  const invalidate = () => {
    needsRender = true;
  };
  controls.addEventListener("change", invalidate);
  let disposed = false,
    frame = 0,
    days = 0,
    last = 0,
    selected = "",
    mode = "presentation",
    ready = false;
  if (matchMedia("(prefers-reduced-motion: reduce)").matches)
    $("#solar-speed").value = "0";
  const disposeObject = (o) =>
    o.traverse((child) => {
      child.geometry?.dispose();
      for (const m of child.material ? [].concat(child.material) : []) {
        for (const v of Object.values(m))
          if (v?.isTexture) {
            v.dispose();
            v.image?.close?.();
          }
        m.dispose();
      }
    });
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    controls.removeEventListener("change", invalidate);
    controls.dispose();
    for (const m of loaded.values()) disposeObject(m);
    for (const o of disposables) disposeObject(o);
    for (const im of unreleasedImages) im.close?.();
    renderer.dispose();
    renderer.domElement.remove();
    signal.removeEventListener("abort", dispose);
    root.replaceChildren();
  };
  const resize = () => {
    const w = container.clientWidth,
      h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    needsRender = true;
    if (!selected) overview();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
  signal.addEventListener("abort", dispose, { once: true });
  renderer.domElement.addEventListener("webglcontextlost", (e) => {
    e.preventDefault();
    $("#solar-speed").value = "0";
    status.textContent =
      "The 3D view was interrupted. Return to Gallery, then reopen Solar System.";
  });
  function overview() {
    needsRender = true;
    selected = "";
    $("#solar-select").value = "";
    ["#solar-name", "#solar-facts", "#solar-accuracy"].forEach((selector, index) => {
      $(selector).textContent = overviewInfo[index];
    });
    $("#solar-model-link").hidden = true;
    controls.target.set(0, 0, 0);
    const d = camera.aspect < 1 ? 165 : 115;
    camera.position.set(0, d * 0.8, d * 0.68);
    camera.near = 0.001;
    camera.far = 20000;
    camera.updateProjectionMatrix();
    controls.update();
  }
  function updateInfo(id) {
    const a = assets.find((a) => a.solarId === id),
      f = a.details.scientific_properties;
    $("#solar-name").textContent = a.name;
    $("#solar-facts").textContent = f
      ? `Diameter ${f.diameter_km.toLocaleString()} km · ${f.orbital_period_days === null ? "No heliocentric orbital period" : `Orbit ${f.orbital_period_days.toLocaleString()} days${id === "moon" ? " around Earth" : ""}`} · Axial tilt ${f.axial_tilt_degrees}°`
      : "Illustrative orbit and scale; physical properties are not modeled.";
    $("#solar-accuracy").textContent = [a.details.accuracy_notes, ...(a.details.attribution ?? []).map((item) => item.credit)].filter(Boolean).join(" ");
    const link = $("#solar-model-link");
    link.hidden = false;
    link.href = `?model=${a.id}`;
  }
  function focus(id) {
    const entry = bodies.get(id);
    if (!entry) return;
    needsRender = true;
    selected = id;
    $("#solar-select").value = id;
    updateInfo(id);
    scene.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(entry.model),
      center = box.getCenter(new THREE.Vector3()),
      radius = Math.max(box.getSize(new THREE.Vector3()).length() / 2, 1e-7);
    const direction = new THREE.Vector3(
      -center.z,
      0.6 * Math.max(center.length(), 1),
      center.x,
    ).normalize();
    if (id === "sun") direction.set(0.7, 0.6, 1).normalize();
    const vf = THREE.MathUtils.degToRad(camera.fov / 2),
      hf = Math.atan(Math.tan(vf) * camera.aspect);
    camera.position
      .copy(center)
      .addScaledVector(direction, (radius / Math.sin(Math.min(vf, hf))) * 1.12);
    controls.target.copy(center);
    controls.minDistance = radius * 1.05;
    camera.near = radius / 100;
    camera.far = 20000;
    camera.updateProjectionMatrix();
    controls.update();
  }
  const loader = new GLTFLoader();
  try {
    // Load sequentially to bound decode peaks. Downsample only the demo's GPU maps.
    for (const a of assets) {
      if (disposed) break;
      const gltf = await loader.loadAsync(a.file);
      if (disposed) {
        disposeObject(gltf.scene);
        break;
      }
      const model = gltf.scene;
      loaded.set(a.solarId, model);
      const textureSet = new Set();
      model.traverse((o) => {
        for (const m of o.material ? [].concat(o.material) : []) {
          for (const t of Object.values(m)) if (t?.isTexture) textureSet.add(t);
        }
      });
      for (const texture of textureSet) {
        if (texture.image?.width > 1024) {
          const original = texture.image;
          const image = await createImageBitmap(original, {
            resizeWidth: 1024,
            resizeHeight: Math.round((original.height * 1024) / original.width),
            resizeQuality: "high",
            imageOrientation: "none",
          });
          if (disposed) {
            image.close();
            break;
          }
          texture.image = image;
          texture.needsUpdate = true;
          unreleasedImages.add(image);
        }
      }
      if (disposed) break;
      const orbit = new THREE.Group(),
        tilt = new THREE.Group();
      orbit.add(tilt);
      tilt.add(model);
      scene.add(orbit);
      tilt.rotation.z = THREE.MathUtils.degToRad(
        a.details.scientific_properties?.axial_tilt_degrees ?? 25,
      );
      bodies.set(a.solarId, {
        model,
        orbit,
        tilt,
        asset: a,
        index: bodies.size,
      });
      const option = document.createElement("option");
      option.value = a.solarId;
      option.textContent = a.name;
      $("#solar-select").append(option);
      status.textContent = `Loading models ${bodies.size} / ${assets.length}…`;
    }
    if (disposed) return { dispose };
    const stars = new Float32Array(1600 * 3);
    let seed = 771;
    const random = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };
    for (let i = 0; i < 1600; i++) {
      const d = new THREE.Vector3(
        random() - 0.5,
        random() - 0.5,
        random() - 0.5,
      )
        .normalize()
        .multiplyScalar(450 + random() * 100);
      stars.set(d.toArray(), i * 3);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute("position", new THREE.BufferAttribute(stars, 3));
    const sky = new THREE.Points(
      starGeo,
      new THREE.PointsMaterial({
        color: 0xb7c4d1,
        size: 0.28,
        sizeAttenuation: true,
      }),
    );
    scene.add(sky);
    disposables.add(sky);
    const mesh = loaded.get("asteroid-01").getObjectByProperty("isMesh", true);
    mesh.updateWorldMatrix(true, false);
    const beltGeo = mesh.geometry.clone().applyMatrix4(mesh.matrixWorld);
    belt = new THREE.InstancedMesh(beltGeo, mesh.material.clone(), 240);
    const dummy = new THREE.Object3D();
    for (let i = 0; i < 240; i++) {
      const a = random() * Math.PI * 2,
        r = 20 + random() * 3;
      dummy.position.set(
        Math.cos(a) * r,
        (random() - 0.5) * 0.7,
        Math.sin(a) * r,
      );
      dummy.rotation.set(random() * 6, random() * 6, random() * 6);
      dummy.scale.setScalar(0.035 + random() * 0.06);
      dummy.updateMatrix();
      belt.setMatrixAt(i, dummy.matrix);
    }
    scene.add(belt);
    disposables.add(belt);
    orbitLines = new THREE.Group();
    scene.add(orbitLines);
    disposables.add(orbitLines);
    const tailPositions = new Float32Array(160 * 3);
    const tailGeo = new THREE.BufferGeometry();
    tailGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(tailPositions, 3),
    );
    const tail = new THREE.Points(
      tailGeo,
      new THREE.PointsMaterial({
        color: 0x9dcde0,
        transparent: true,
        opacity: 0.55,
        size: 0.1,
        depthWrite: false,
      }),
    );
    scene.add(tail);
    disposables.add(tail);
    function scales() {
      needsRender = true;
      for (const child of [...orbitLines.children]) {
        disposeObject(child);
        orbitLines.remove(child);
      }
      for (const [id, e] of bodies) {
        const f = e.asset.details.scientific_properties;
        const planetIndex = [
          "mercury",
          "venus",
          "earth",
          "mars",
          "jupiter",
          "saturn",
          "uranus",
          "neptune",
          "pluto",
        ].indexOf(id);
        e.radius =
          mode === "realistic"
            ? f
              ? (f.diameter_km / 2 / 149600000) * 2
              : 1e-7
            : id === "sun"
              ? 2.7
              : id === "jupiter"
                ? 1.35
                : id === "saturn"
                  ? 1.05
                  : id === "uranus"
                    ? 0.72
                    : id === "neptune"
                      ? 0.7
                      : id === "earth"
                        ? 0.52
                        : id === "moon"
                          ? 0.18
                          : id === "pluto"
                            ? 0.24
                            : 0.35;
        e.model.scale.setScalar(e.radius * (e.asset.modelScale ?? 1));
        e.distance =
          mode === "realistic"
            ? f
              ? (f.semi_major_axis_million_km / 149.6) * 2
              : 5.2
            : planetIndex >= 0
              ? [6, 9, 12, 15, 26, 34, 42, 50, 57][planetIndex]
              : id === "moon"
                ? 1.1
                : id.startsWith("asteroid")
                  ? 20 + (e.index - 11) * 0.6
                  : 64;
        if (id === "sun") e.distance = 0;
        if (id === "moon") continue;
        const points = Array.from(
          { length: 193 },
          (_, i) =>
            new THREE.Vector3(
              Math.cos((i / 192) * Math.PI * 2) * e.distance,
              0,
              Math.sin((i / 192) * Math.PI * 2) * e.distance,
            ),
        );
        const geo = new THREE.BufferGeometry().setFromPoints(points);
        orbitLines.add(
          new THREE.Line(
            geo,
            new THREE.LineBasicMaterial({
              color: 0x3a4d4c,
              transparent: true,
              opacity: 0.5,
            }),
          ),
        );
      }
      belt.visible = mode === "presentation";
      sky.visible = !selected;
      updatePositions();
      if (selected) focus(selected);
      else overview();
    }
    function updatePositions() {
      for (const [id, e] of bodies) {
        const f = e.asset.details.scientific_properties,
          period = f?.orbital_period_days ?? (id === "comet" ? 1900 : 1600),
          angle =
            ((days / (period ?? 1)) * Math.PI * 2 + e.index * 0.91) %
            (Math.PI * 2);
        e.orbit.position.set(
          Math.cos(angle) * e.distance,
          0,
          Math.sin(angle) * e.distance,
        );
        if (id === "sun") e.orbit.position.set(0, 0, 0);
        if (id === "moon")
          e.orbit.position.add(bodies.get("earth").orbit.position);
        if (f)
          e.model.rotation.y =
            (((days * 24) / Math.abs(f.rotation_period_hours)) * Math.PI * 2) %
            (Math.PI * 2);
      }
      const c = bodies.get("comet");
      const direction = c.orbit.position.clone().normalize(),
        side = new THREE.Vector3(-direction.z, 0, direction.x);
      for (let i = 0; i < 160; i++) {
        const t = i / 160,
          len = mode === "presentation" ? 7 : 1e-5;
        const p = c.orbit.position
          .clone()
          .addScaledVector(direction, t * len)
          .addScaledVector(side, Math.sin(i * 2.4) * t * t * len * 0.12);
        p.y += Math.cos(i * 1.8) * t * len * 0.04;
        tailPositions.set(p.toArray(), i * 3);
      }
      tailGeo.attributes.position.needsUpdate = true;
      tail.material.size = mode === "presentation" ? 0.1 : 1e-7;
    }
    $("#solar-scale").onchange = () => {
      mode = $("#solar-scale").value;
      $("#solar-scale-note").textContent =
        mode === "realistic"
          ? "Realistic ratios: planets use one shared distance and radius scale. Planets are very small; use Explore to focus. Small bodies, circular orbits and phases are illustrative."
          : "Presentation mode enlarges bodies and compresses distances. Planetary orbits illustrate relative periods; small-body paths and all positions are illustrative.";
      scales();
    };
    $("#solar-select").onchange = () => {
      if ($("#solar-select").value) focus($("#solar-select").value);
      else overview();
    };
    $("#solar-overview").onclick = overview;
    const raycaster = new THREE.Raycaster();
    let start;
    renderer.domElement.addEventListener("pointerdown", (e) => {
      start = [e.clientX, e.clientY];
    });
    renderer.domElement.addEventListener("pointerup", (e) => {
      if (!start || Math.hypot(e.clientX - start[0], e.clientY - start[1]) > 6)
        return;
      const r = renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(
        new THREE.Vector2(
          ((e.clientX - r.left) / r.width) * 2 - 1,
          (-(e.clientY - r.top) / r.height) * 2 + 1,
        ),
        camera,
      );
      const hits = raycaster.intersectObjects([...loaded.values()], true);
      if (hits[0])
        for (const [id, en] of bodies) {
          let o = hits[0].object;
          while (o) {
            if (o === en.model) {
              focus(id);
              return;
            }
            o = o.parent;
          }
        }
    });
    scales();
    resize();
    ready = true;
    status.textContent = "";
    const render = (now) => {
      if (disposed) return;
      const dt = last ? Math.min((now - last) / 1000, 0.05) : 0;
      last = now;
      const speed = document.hidden ? 0 : Number($("#solar-speed").value);
      const advancing = speed !== 0 && dt > 0;
      if (advancing) {
        const old = selected
          ? bodies.get(selected).orbit.position.clone()
          : null;
        days += dt * speed;
        updatePositions();
        if (old) {
          const delta = bodies.get(selected).orbit.position.clone().sub(old);
          camera.position.add(delta);
          controls.target.add(delta);
        }
      }
      sky.visible = !selected;
      orbitLines.visible = !selected;
      belt.visible = mode === "presentation" && !selected;
      const cameraChanged = controls.update();
      // A paused atlas needs a new frame only after input, resize or a view change.
      if (!document.hidden && (advancing || needsRender || cameraChanged)) {
        renderer.render(scene, camera);
        needsRender = false;
      }
      frame = requestAnimationFrame(render);
    };
    frame = requestAnimationFrame(render);
  } catch (error) {
    if (!disposed) {
      status.textContent =
        "The solar scene could not load. Return to Gallery and reopen it to retry.";
      console.error(error);
    }
  }
  return {
    dispose,
    getState: () => ({
      ready,
      days,
      selected,
      mode,
      bodies: bodies.size,
      rendererCount: container.querySelectorAll("canvas").length,
    }),
  };
}
