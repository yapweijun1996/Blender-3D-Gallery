import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

function batchSealMeshes(parent, pieces) {
  parent.updateWorldMatrix(true, true);
  const inverse = parent.matrixWorld.clone().invert();
  const toParent = new THREE.Matrix4();
  const byMaterial = new Map();
  for (const piece of pieces) piece.traverse(object => {
    if (!object.isMesh) return;
    const geometry = object.geometry.clone();
    // The seal finishes use vertex normals and the room environment. Unify the
    // curved trim and relief attributes so they can share one material batch.
    geometry.deleteAttribute('uv');
    geometry.applyMatrix4(toParent.multiplyMatrices(inverse, object.matrixWorld));
    if (!byMaterial.has(object.material)) byMaterial.set(object.material, []);
    byMaterial.get(object.material).push(geometry);
  });
  return [...byMaterial].map(([material, parts]) => {
    const geometry = mergeGeometries(parts);
    for (const part of parts) part.dispose();
    return new THREE.Mesh(geometry, material);
  });
}

function makeCracks(seal) {
  const segments = [], rays = seal.userData.crackRays;
  const centerY = -.17;
  function strip(ax, ay, bx, by, start, end, width) {
    const length = Math.hypot(bx - ax, by - ay);
    const dx = (by - ay) * width / length, dy = (ax - bx) * width / length;
    for (let i = 0; i < 5; i++) {
      const t0 = i / 5, t1 = (i + 1) / 5;
      const x0 = THREE.MathUtils.lerp(ax, bx, t0), y0 = THREE.MathUtils.lerp(ay, by, t0);
      const x1 = THREE.MathUtils.lerp(ax, bx, t1), y1 = THREE.MathUtils.lerp(ay, by, t1);
      segments.push({ time: THREE.MathUtils.lerp(start, end, t1), positions: [
        x0 + dx, y0 + dy, .176, x1 - dx, y1 - dy, .176, x0 - dx, y0 - dy, .176,
        x0 + dx, y0 + dy, .176, x1 + dx, y1 + dy, .176, x1 - dx, y1 - dy, .176,
      ] });
    }
  }
  for (let i = 0; i < rays.length; i += 2) {
    const x = rays[i], y = rays[i + 1] - centerY;
    let ax = 0, ay = centerY;
    for (let segment = 1; segment <= 5; segment++) {
      const t = segment / 5, wiggle = segment === 5 ? 0 : Math.sin(i + segment * 2.2) * .028;
      const bx = x * t - y * wiggle, by = centerY + y * t + x * wiggle;
      strip(ax, ay, bx, by, t - .2, t, .015 - t * .004);
      if (segment === 3) strip(bx, by, bx + .21 * x - .20 * y, by + .21 * y + .20 * x, t, t + .32, .008);
      ax = bx; ay = by;
    }
  }
  segments.sort((a, b) => a.time - b.time);
  const geometry = new THREE.BufferGeometry();
  const positions = segments.flatMap(segment => segment.positions);
  const uvs = segments.flatMap(() => [0,.5, 1,.5, 1,.5, 0,.5, 0,.5, 1,.5]);
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  // Bake the glow across the crack once. The draw range controls its growth.
  const pixels = new Uint8Array(64 * 4);
  for (let i = 0; i < 64; i++) {
    const across = Math.abs((i + .5) / 32 - 1);
    const core = 1 - THREE.MathUtils.smoothstep(across, .07, .30);
    const opacity = (1 - across) ** 2.3 * .48 + core * .52;
    pixels.set([255, 185 + 62 * core, 97 + 96 * core, 255 * opacity], i * 4);
  }
  const map = new THREE.DataTexture(pixels, 64, 1);
  map.colorSpace = THREE.SRGBColorSpace;
  map.minFilter = map.magFilter = THREE.LinearFilter;
  map.needsUpdate = true;
  const material = new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false,
    blending: THREE.AdditiveBlending, toneMapped: false });
  const cracks = new THREE.Mesh(geometry, material);
  cracks.name = 'SealCracks';
  cracks.renderOrder = 8;
  cracks.visible = false;
  seal.add(cracks);
  return progress => {
    const last = segments.findIndex(segment => segment.time > progress);
    const count = (last < 0 ? segments.length : last) * 6;
    geometry.setDrawRange(0, count);
    cracks.visible = count > 0;
  };
}

export function createSealEffect(seal, scene, breakTime, dust) {
  const drawCracks = makeCracks(seal);
  const shards = seal.children.filter(piece => /^SealShard\d+$/.test(piece.name));
  const assembled = new THREE.Group();
  assembled.name = 'AssembledSeal';
  assembled.add(...batchSealMeshes(seal, shards));
  // Draw the assembled and flying versions with the same shader variants.
  for (const mesh of assembled.children) {
    mesh.material = mesh.material.clone();
    mesh.material.transparent = true;
  }
  seal.add(assembled);
  const pieces = shards.map((piece, i) => {
    const meshes = batchSealMeshes(piece, [piece]);
    piece.clear();
    piece.add(...meshes);
    piece.visible = false;
    const materials = meshes.map(mesh => {
      const material = mesh.material.clone();
      material.transparent = true;
      mesh.material = material;
      return material;
    });
    const position = piece.position.clone(), rotation = piece.quaternion.clone();
    const sign = Math.sign(position.x);
    // Give the lowest pieces enough lift to clear the bottom of the close shot.
    const lift = Math.max(.46, .31 + (position.y + .17) * 1.9);
    return { piece, position, rotation, materials,
      velocity: new THREE.Vector3(sign * (.30 + Math.abs(position.x) * 2.6), lift, .39 + i % 3 * .16),
      spin: new THREE.Euler(2.2 + .64 * i, sign * (2.9 + i * .4), sign * (1.2 + i * .7)),
      start: new THREE.Vector3(), facing: new THREE.Quaternion(), sparks: 0,
    };
  });
  const turn = new THREE.Quaternion(), angles = new THREE.Euler();
  let separated = false, crackProgress = 0;
  return {
    update(time) {
      crackProgress = time < breakTime ? THREE.MathUtils.smoothstep(time, .012, breakTime - .012) * 1.15 : 0;
      drawCracks(crackProgress);
      if (time < breakTime) return;
      if (!separated) {
        separated = true;
        assembled.visible = false;
        for (const entry of pieces) {
          scene.attach(entry.piece);
          entry.start.copy(entry.piece.position);
          entry.facing.copy(entry.piece.quaternion);
        }
      }
      const age = time - breakTime;
      for (const entry of pieces) {
        const { piece, velocity, spin, materials } = entry;
        piece.position.copy(entry.start).addScaledVector(velocity, age);
        piece.position.y -= .79 * age ** 2;
        angles.set(spin.x * age, spin.y * age, spin.z * age);
        piece.quaternion.copy(entry.facing).multiply(turn.setFromEuler(angles));
        const sparks = age >= .42 ? 2 : age >= .19 ? 1 : 0;
        while (entry.sparks < sparks) {
          dust.scatter(piece.position);
          entry.sparks++;
        }
        const opacity = 1 - THREE.MathUtils.smoothstep(age, .20, .98);
        for (const material of materials) {
          material.opacity = opacity;
          material.depthWrite = opacity === 1;
        }
        piece.visible = opacity > 0;
      }
    },
    reset() {
      drawCracks(0);
      crackProgress = 0;
      assembled.visible = true;
      for (const entry of pieces) {
        seal.add(entry.piece);
        entry.piece.position.copy(entry.position);
        entry.piece.quaternion.copy(entry.rotation);
        entry.piece.visible = false;
        entry.sparks = 0;
        for (const material of entry.materials) { material.opacity = 1; material.depthWrite = true; }
      }
      separated = false;
    },
    measure() { return { separated, visible: separated ? pieces.filter(({ piece }) => piece.visible).length : pieces.length,
      progress: crackProgress }; },
  };
}
