import * as THREE from 'three';

export function applyPaperGrain(root) {
  const size = 64;
  const pixels = new Uint8Array(size * size * 4);
  let seed = 3;
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    const grain = Math.sin((x * 11 + y * 3) * 2 * Math.PI / size);
    const weave = Math.sin((x * 4 - y * 7) * 2 * Math.PI / size);
    const luminance = 247 + grain * 3 + weave * 2 + (seed / 2 ** 32 - .5) * 6;
    pixels.set([luminance, luminance, luminance, 255], (y * size + x) * 4);
  }
  // Bake the fibers into one neutral color lookup. The paper uses the mesh normal.
  const grain = new THREE.DataTexture(pixels, size, size);
  grain.wrapS = grain.wrapT = THREE.RepeatWrapping;
  grain.repeat.set(3, 3);
  grain.generateMipmaps = true;
  grain.minFilter = THREE.LinearMipmapLinearFilter;
  grain.magFilter = THREE.LinearFilter;
  grain.needsUpdate = true;

  const warm = new Set();
  root.traverse(object => {
    if (!object.isMesh || !object.geometry.hasAttribute('uv')) return;
    const material = object.material;
    if (material.name === 'Cream') {
      // The greeting face keeps its ivory reflectance at the turn and the landing.
      object.material = new THREE.MeshBasicMaterial({ name: 'Cream', color: 0xf9f1df, map: grain, toneMapped: false });
      return;
    }
    if (material.name !== 'WarmLining' && !material.name.startsWith('RedPaper')) return;
    material.map = grain;
    material.needsUpdate = true;
    if (material.name === 'WarmLining') {
      material.emissive.setHex(0xffbc6d);
      material.emissiveIntensity = 0;
      warm.add(material);
    }
  });
  return strength => {
    for (const material of warm) material.emissiveIntensity = strength * .12;
  };
}
