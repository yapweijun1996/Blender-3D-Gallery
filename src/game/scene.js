import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TABLE } from "./table.js";
export async function createGameScene(container, assets, signal, progress) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setClearColor(0x172421);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.setAttribute("role", "img");
  renderer.domElement.setAttribute(
    "aria-label",
    "3D billiards table. Use the angle and power controls, then Shoot.",
  );
  container.append(renderer.domElement);
  const scene = new THREE.Scene(),
    camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 20);
  const center = new THREE.Vector3(0, TABLE.bedHeight, 0);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enabled = false;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x35443b, 2));
  const key = new THREE.DirectionalLight(0xfff7e7, 2.4);
  key.position.set(-2, 5, 2);
  scene.add(key);
  const balls = new Map();
  let cue,
    disposed = false,
    inspect = false,
    portrait = false;
  const disposeObject = (obj) =>
    obj.traverse((o) => {
      o.geometry?.dispose();
      for (const m of Array.isArray(o.material) ? o.material : [o.material]) {
        if (!m) continue;
        for (const t of Object.values(m)) if (t?.isTexture) t.dispose();
        m.dispose();
      }
    });
  const resize = () => {
    if (disposed) return;
    const w = container.clientWidth,
      h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    const a = w / h;
    portrait = a < 1;
    const height = portrait
      ? Math.max(2.82, 1.62 / a)
      : Math.max(1.62, 2.82 / a);
    camera.left = (-height * a) / 2;
    camera.right = (height * a) / 2;
    camera.top = height / 2;
    camera.bottom = -height / 2;
    camera.updateProjectionMatrix();
    if (!inspect) {
      camera.position.set(0, 4, 0);
      camera.up.set(portrait ? 1 : 0, 0, portrait ? 0 : -1);
      camera.lookAt(center);
    }
    render();
  };
  const render = () => {
    if (!disposed) renderer.render(scene, camera);
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    observer.disconnect();
    controls.dispose();
    disposeObject(scene);
    renderer.dispose();
    renderer.domElement.remove();
    signal.removeEventListener("abort", dispose);
  };
  signal.addEventListener("abort", dispose, { once: true });
  renderer.domElement.addEventListener("webglcontextlost", (e) => {
    e.preventDefault();
    container.dispatchEvent(new CustomEvent("game-context-lost"));
  });
  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute(
    "position",
    new THREE.BufferAttribute(new Float32Array(6), 3),
  );
  const line = new THREE.Line(
    lineGeometry,
    new THREE.LineBasicMaterial({
      color: 0xd6e9b9,
      transparent: true,
      opacity: 0.8,
    }),
  );
  line.frustumCulled = false;
  scene.add(line);
  controls.addEventListener("change", render);
  const ghost = new THREE.Mesh(
    new THREE.RingGeometry(TABLE.radius - 0.001, TABLE.radius, 48),
    new THREE.MeshBasicMaterial({ color: 0xd6e9b9, side: THREE.DoubleSide }),
  );
  ghost.rotation.x = -Math.PI / 2;
  scene.add(ghost);
  try {
    const ids = [
      "pool-table",
      "cue-stick-01",
      "cue-ball",
      ...Array.from(
        { length: 15 },
        (_, i) => `ball-${String(i + 1).padStart(2, "0")}`,
      ),
    ];
    let done = 0,
      index = 0;
    await Promise.all(
      Array.from({ length: 4 }, async () => {
        while (index < ids.length) {
          const id = ids[index++],
            asset = assets.find((a) => a.id === id);
          if (!asset) throw new Error("Missing " + id);
          const gltf = await new GLTFLoader().loadAsync(asset.file);
          if (disposed || signal.aborted) {
            disposeObject(gltf.scene);
            throw new DOMException("Canceled", "AbortError");
          }
          const obj = gltf.scene;
          scene.add(obj);
          if (id === "cue-stick-01") cue = obj;
          else if (id !== "pool-table")
            balls.set(id === "cue-ball" ? 0 : Number(id.slice(-2)), obj);
          progress(++done, ids.length);
        }
      }),
    );
    resize();
  } catch (e) {
    dispose();
    throw e;
  }
  const raycaster = new THREE.Raycaster(),
    plane = new THREE.Plane(
      new THREE.Vector3(0, 1, 0),
      -(TABLE.bedHeight + TABLE.radius),
    );
  return {
    canvas: renderer.domElement,
    render,
    dispose,
    point(clientX, clientY) {
      const rect = renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(
        new THREE.Vector2(
          ((clientX - rect.left) / rect.width) * 2 - 1,
          (-(clientY - rect.top) / rect.height) * 2 + 1,
        ),
        camera,
      );
      const p = new THREE.Vector3();
      return raycaster.ray.intersectPlane(plane, p) ? { x: p.x, z: p.z } : null;
    },
    setInspection(value) {
      inspect = value;
      controls.enabled = value;
      controls.enablePan = false;
      controls.target.copy(center);
      if (value) {
        camera.up.set(0, 1, 0);
        camera.position.set(2.5, 3.8, 2.5);
        camera.lookAt(center);
      } else {
        camera.zoom = 1;
        resize();
      }
      render();
    },
    inspectKey(key) {
      if (!inspect) return false;
      const step = Math.PI / 18;
      if (key === "ArrowLeft") controls.rotateLeft(step);
      else if (key === "ArrowRight") controls.rotateLeft(-step);
      else if (key === "ArrowUp") controls.rotateUp(step);
      else if (key === "ArrowDown") controls.rotateUp(-step);
      else if (["+", "="].includes(key)) camera.zoom = Math.min(3, camera.zoom * 1.15);
      else if (["-", "_"].includes(key)) camera.zoom = Math.max(0.7, camera.zoom / 1.15);
      else return false;
      camera.updateProjectionMatrix();
      render();
      return true;
    },
    setQuality(value) {
      const cap = value === "performance" ? 1 : 1.5;
      renderer.setPixelRatio(Math.min(devicePixelRatio, cap));
      resize();
    },
    update(state, angle, power, candidate) {
      const y = TABLE.bedHeight + TABLE.radius;
      for (const b of state.balls) {
        const obj = balls.get(b.id);
        obj.visible = !b.pocketed;
        if (b.id === 0 && state.phase === "placing" && candidate) {
          obj.visible = true;
          obj.position.set(candidate.x, y, candidate.z);
        } else obj.position.set(b.x, y, b.z);
        obj.quaternion.fromArray(b.q);
      }
      const cb = state.balls[0],
        aim = state.phase === "aiming" && !inspect,
        dx = Math.cos(angle),
        dz = Math.sin(angle);
      cue.visible = aim;
      line.visible = ghost.visible = aim;
      if (aim) {
        cue.position.set(
          cb.x - dx * (0.735 + TABLE.radius + 0.03 + power * 0.06),
          y + 0.005,
          cb.z - dz * (0.735 + TABLE.radius + 0.03 + power * 0.06),
        );
        cue.rotation.y = -angle;
        let distance = 0.65;
        for (const b of state.balls) {
          if (!b.id || b.pocketed) continue;
          const x = b.x - cb.x,
            z = b.z - cb.z,
            t = x * dx + z * dz,
            perp = x * x + z * z - t * t;
          if (t > 0 && perp < (TABLE.radius * 2) ** 2) {
            const hit = t - Math.sqrt((TABLE.radius * 2) ** 2 - perp);
            if (hit > 0) distance = Math.min(distance, hit);
          }
        }
        for (const [position, direction, bound] of [
          [cb.x, dx, TABLE.halfLength - TABLE.radius],
          [cb.z, dz, TABLE.halfWidth - TABLE.radius],
        ])
          if (Math.abs(direction) > 1e-8) {
            const t = ((direction > 0 ? bound : -bound) - position) / direction;
            if (t > 0) distance = Math.min(distance, t);
          }
        const positions = line.geometry.attributes.position;
        positions.setXYZ(0, cb.x, y + 0.002, cb.z);
        positions.setXYZ(
          1,
          cb.x + dx * distance,
          y + 0.002,
          cb.z + dz * distance,
        );
        positions.needsUpdate = true;
        ghost.position.set(
          cb.x + dx * distance,
          y + 0.002,
          cb.z + dz * distance,
        );
      }
      if (inspect) controls.update();
      render();
    },
  };
}
