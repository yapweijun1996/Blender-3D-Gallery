import { t } from "../i18n/index.js";
import * as THREE from 'three';
export const cleanHeader = value => String(value).replace(/[\u0000-\u001f\u007f]/g, '').trim().slice(0,32);

export function shelfRowIds(manifest = {}) {
  const names = manifest.runtime_nodes?.shelves ?? ['shelf_1','shelf_2','shelf_3'];
  if (![2,3].includes(names.length) || new Set(names).size !== names.length) throw new Error('Invalid shelf controls manifest');
  return names.length === 2 ? ['all', 'lower', 'upper'] : ['all', 'lower', 'middle', 'upper'];
}

export const shelfRowLabels = manifest =>
  shelfRowIds(manifest).map(id => t(`shelf.row.${id}`, {}, 'en'));

/** Materials and title overlays are owned by this mounted instance, never by the export. */
export function createShelfParts(model, makeCanvas = () => document.createElement('canvas'), manifest = {}) {
  const meshes = name => {
    const found = [];
    model.getObjectByName(name)?.traverse(object => { if (object.isMesh) found.push(object); });
    if (!found.length) throw new Error(`Missing shelf part: ${name}`);
    return found;
  };
  const shelfNames = manifest.runtime_nodes?.shelves ?? ['shelf_1', 'shelf_2', 'shelf_3'];
  const ledNames = manifest.runtime_nodes?.leds ?? ['LED_1', 'LED_2', 'LED_3', 'LED_header', 'LED_base'];
  shelfRowIds(manifest);
  if (!ledNames.length) throw new Error('Invalid shelf controls manifest');
  const shelves = shelfNames.map(meshes), leds = ledNames.flatMap(meshes);
  const surfaces = (manifest.runtime_header_surfaces ?? []).map(surface => {
    const anchor = model.getObjectByName(surface.anchor);
    if (!anchor || !Number.isFinite(surface.width_m) || surface.width_m <= 0 || !Number.isFinite(surface.height_m) || surface.height_m <= 0) {
      throw new Error('Invalid header surface anchor or dimensions');
    }
    return { anchor, width: surface.width_m, height: surface.height_m };
  });
  // M056's established front-facing panel remains unchanged. New shapes require explicit anchors.
  if (!surfaces.length && manifest.model_id && manifest.model_id !== 'GJH-M056') throw new Error('Missing oriented header surfaces');
  const legacyHeader = surfaces.length ? null : meshes('brand_header_panel')[0];
  const originals = new Map();
  for (const mesh of new Set([...shelves.flat(), ...leds])) {
    originals.set(mesh, mesh.material);
    const clones = [].concat(mesh.material).map(material => material.clone());
    mesh.material = Array.isArray(mesh.material) ? clones : clones[0];
  }
  let overlays = [], disposed = false;
  const restore = (mesh, on) => [].concat(mesh.material).forEach((material, index) => {
    const original = [].concat(originals.get(mesh))[index];
    material.emissive?.copy(original.emissive);
    material.emissiveIntensity = on ? original.emissiveIntensity : 0;
  });
  const clearTitle = () => {
    const materials = new Set();
    for (const overlay of overlays) {
      overlay.removeFromParent(); overlay.geometry.dispose(); materials.add(overlay.material);
    }
    const textures = new Set([...materials].map(material => material.map));
    textures.forEach(texture => texture.dispose()); materials.forEach(material => material.dispose());
    overlays = [];
  };
  return {
    select(row) {
      if (disposed) return;
      shelves.forEach((list, index) => list.forEach(mesh => {
        restore(mesh, true);
        if (index + 1 === row) [].concat(mesh.material).forEach(material => {
          material.emissive?.setHex(0x8a6729); material.emissiveIntensity = .65;
        });
      }));
    },
    light(on) { if (!disposed) leds.forEach(mesh => restore(mesh, on)); },
    title(value) {
      if (disposed) return;
      clearTitle();
      const text = cleanHeader(value); if (!text) return;

      const canvas = makeCanvas();
      canvas.width = surfaces.length ? Math.max(128,Math.round(256 * surfaces[0].width / surfaces[0].height)) : 1024;
      canvas.height = 256;
      const ctx = canvas.getContext('2d'); if (!ctx) throw new Error('Label canvas unavailable');
      ctx.fillStyle = '#183a30'; ctx.fillRect(0,0,canvas.width,canvas.height);
      ctx.fillStyle = '#ead5a3'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      if (surfaces.length) {
        // A narrow corner plaque uses its real aspect ratio, never squashed 4:1 artwork.
        // Keep the complete text, balanced onto two lines when words permit.
        const words = text.split(/\s+/); let lines = [text]; ctx.font = '600 96px sans-serif';
        if (canvas.width / canvas.height < 2 && words.length > 1) {
          let best = Infinity;
          for (let split = 1; split < words.length; split++) {
            const candidate = [words.slice(0,split).join(' '),words.slice(split).join(' ')];
            const width = Math.max(...candidate.map(line => ctx.measureText(line).width));
            if (width < best) { best = width; lines = candidate; }
          }
        }
        let size = 96;
        while (size > 8) {
          ctx.font = '600 ' + size + 'px sans-serif';
          if (Math.max(...lines.map(line => ctx.measureText(line).width)) <= canvas.width * .92 && lines.length * size * 1.2 <= canvas.height * .8) break;
          size -= 2;
        }
        ctx.font = '600 ' + size + 'px sans-serif';
        lines.forEach((line,index) => ctx.fillText(line,canvas.width/2,canvas.height/2 + (index-(lines.length-1)/2)*size*1.2));
      } else {
        // Preserve the shipped M056 label layout.
        let size = 96;
        do { ctx.font = '600 ' + size + 'px sans-serif'; size -= 2; } while (ctx.measureText(text).width > 950 && size > 26);
        ctx.fillText(text,512,128);
      }
      const texture = new THREE.CanvasTexture(canvas); texture.colorSpace = THREE.SRGBColorSpace;
      const material = new THREE.MeshBasicMaterial({ map: texture, toneMapped: false });
      model.updateMatrixWorld(true);
      const attach = (parent, width, height, position) => {
        const overlay = new THREE.Mesh(new THREE.PlaneGeometry(width,height), material);
        overlay.name = overlays.length ? `RUNTIME_ReplaceableHeader_${overlays.length + 1}` : 'RUNTIME_ReplaceableHeader';
        overlay.position.copy(position); parent.add(overlay); overlays.push(overlay);
      };
      if (surfaces.length) {
        // Anchor local +Z is the visible outward normal, +Y is up, in every LOD.
        for (const surface of surfaces) attach(surface.anchor, surface.width, surface.height, new THREE.Vector3(0,0,.002));
      } else {
        const box = new THREE.Box3().setFromObject(legacyHeader), dimensions = box.getSize(new THREE.Vector3()), position = box.getCenter(new THREE.Vector3());
        position.z = box.max.z + .004;
        attach(model, dimensions.x * .97, dimensions.y * .9, model.worldToLocal(position));
      }
    },
    dispose() {
      if (disposed) return; disposed = true; clearTitle();
      for (const [mesh, original] of originals) {
        [].concat(mesh.material).forEach(material => material.dispose()); mesh.material = original;
      }
      originals.clear();
    },
  };
}
