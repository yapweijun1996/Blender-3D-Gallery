import {
  BoxGeometry, BufferAttribute, BufferGeometry, Color, DirectionalLight, DoubleSide, Fog,
  HemisphereLight, InstancedMesh, Matrix4, Mesh, MeshBasicMaterial, MeshStandardMaterial,
  PerspectiveCamera, PointLight, Scene, Vector3, WebGLRenderer,
} from "three";
import { tunnelMarkings } from "./geometry.js";

const COLORS = {
  road: 0x353b41, walls: 0x777c7b, ceiling: 0x484f57, terrain: 0x687758,
  cover: 0x79846a, portals: 0x999d91,
};

function surfaceMesh({ position, indices }, material) {
  const buffer = new BufferGeometry();
  buffer.setAttribute("position", new BufferAttribute(position, 3));
  buffer.setIndex(new BufferAttribute(indices, 1));
  buffer.computeVertexNormals();
  return new Mesh(buffer, material);
}

export function createTunnelScene(stage, profile, geometry, car) {
  const renderer = new WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  const geometries = new Set(), materials = new Set();
  const addMesh = mesh => {
    scene.add(mesh);
    geometries.add(mesh.geometry);
    materials.add(mesh.material);
  };
  const scene = new Scene();
  scene.background = new Color(0xa7c4d3);
  scene.fog = new Fog(0xa7c4d3, 80, 200);
  const hemisphere = new HemisphereLight(0xe3edf4, 0x827962, 2.1);
  const sun = new DirectionalLight(0xffe8c7, 2.0);
  const headlight = new PointLight(0xffe3b0, 38, 19, 2);
  sun.position.set(-20, 42, 17);
  scene.add(hemisphere, sun, headlight, car);
  for (const surface of geometry.surfaces) {
    addMesh(surfaceMesh(surface, new MeshStandardMaterial({ color: COLORS[surface.id], roughness: .92, side: DoubleSide })));
  }
  addMesh(surfaceMesh(tunnelMarkings(profile, geometry.sections), new MeshBasicMaterial({ color: 0xece7cf, side: DoubleSide })));

  const covered = geometry.sections.filter(({ s }) => s >= geometry.coveredFrom && s <= geometry.coveredTo);
  const fixtures = covered.filter((_, index) => index % 11 === 3);
  const lighting = new InstancedMesh(new BoxGeometry(1.5, .075, .25), new MeshBasicMaterial({ color: 0xffe5b4 }), fixtures.length);
  const transform = new Matrix4();
  fixtures.forEach((section, index) => {
    transform.makeRotationY(Math.atan2(section.tx, section.tz));
    transform.setPosition(section.x, section.y + geometry.clearance - .065, section.z);
    lighting.setMatrixAt(index, transform);
  });
  addMesh(lighting);

  // A lintel highlights each break between the open approach and the covered section.
  for (const section of [covered[0], covered.at(-1)]) {
    const lintel = new Mesh(new BoxGeometry(profile.width + .9, .42, .62), new MeshStandardMaterial({ color: 0xb1afa0 }));
    lintel.position.set(section.x, .2, section.z);
    lintel.rotation.y = Math.atan2(section.tx, section.tz);
    addMesh(lintel);
  }

  const camera = new PerspectiveCamera(57, 1, .07, 210);
  const eye = new Vector3(), look = new Vector3();
  const coarse = matchMedia("(pointer: coarse)").matches;
  renderer.setPixelRatio(Math.min(devicePixelRatio, coarse ? 1.35 : 1.6));
  renderer.domElement.setAttribute("aria-hidden", "true");
  stage.prepend(renderer.domElement);
  const resize = () => {
    const { width, height } = stage.getBoundingClientRect();
    if (width === 0 || height === 0) return;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  };
  const observer = new ResizeObserver(resize);
  observer.observe(stage);
  resize();

  return {
    draw(state, along, restHeight, dt, snap) {
      const { x, y, z } = state.position;
      const dx = Math.sin(state.heading), dz = Math.cos(state.heading);
      const coveredWeight = Math.max(0, Math.min(1, (along - geometry.coveredFrom + 3) / 11, (geometry.coveredTo - along + 4) / 11));
      hemisphere.intensity = 2.1 - 1.01 * coveredWeight;
      sun.intensity = 2 * (1 - coveredWeight);
      headlight.position.set(x + 4 * dx, y + .75, z + 4 * dz);
      headlight.intensity = 38 * coveredWeight;
      car.position.set(x, y - restHeight, z);
      const { x: qx, y: qy, z: qz, w } = state.quaternion;
      car.quaternion.set(qx, qy, qz, w);
      eye.set(x - 5.3 * dx, y + 2.1, z - 5.3 * dz);
      look.set(x + 10 * dx, y + .36, z + 10 * dz);
      camera.position.lerp(eye, snap ? 1 : 1 - Math.exp(-10 * dt));
      camera.lookAt(look);
      renderer.render(scene, camera);
    },
    dispose() {
      observer.disconnect();
      for (const buffer of geometries) buffer.dispose();
      for (const material of materials) material.dispose();
      lighting.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    },
  };
}
