import * as THREE from 'three';

// Runtime-only, fictional artwork. The baked GLB and its source remain the
// canonical asset; these canvases are deliberately not exportable model data.
export const LABEL_PRESETS = Object.freeze([
  { id: 'citrus-grid', name: 'Citrus Grid', ink: '#173b3d', accent: '#f4b942', paper: '#f6e7bf', caption: 'bright citrus study' },
  { id: 'berry-night', name: 'Berry Night', ink: '#f7e9dc', accent: '#d65a68', paper: '#352b47', caption: 'berry colour study' },
  { id: 'mint-signal', name: 'Mint Signal', ink: '#12372f', accent: '#8ed6b5', paper: '#d8f0df', caption: 'mint colour study' },
]);

function drawLabel(preset, canvasFactory) {
  const canvas = canvasFactory();
  canvas.width = 1024; canvas.height = 512;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Label canvas is unavailable');
  ctx.fillStyle = preset.paper; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = preset.ink; ctx.fillRect(0, 0, canvas.width, 42); ctx.fillRect(0, 470, canvas.width, 42);
  ctx.fillStyle = preset.accent;
  // Eight complete repeats, with identical paper margins on both seam edges.
  for (let x = 32; x < canvas.width; x += 128) ctx.fillRect(x, 42, 64, 428);
  ctx.fillStyle = preset.ink; ctx.fillRect(288, 146, 448, 266);
  ctx.fillStyle = preset.paper; ctx.font = '800 76px system-ui, sans-serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('DEMO', canvas.width / 2, 214);
  ctx.fillStyle = preset.paper; ctx.font = '700 24px system-ui, sans-serif';
  ctx.fillText(preset.caption.toUpperCase(), canvas.width / 2, 294);
  ctx.fillStyle = preset.paper; ctx.font = '600 18px system-ui, sans-serif';
  ctx.fillText('ORIGINAL CONCEPT / NO CLAIMS', canvas.width / 2, 376);
  return canvas;
}

export function createLabelController(model, { canvasFactory = () => document.createElement('canvas') } = {}) {
  const label = model.getObjectByName('LABEL_OriginalCitrusBand');
  if (!label?.isMesh || !label.material || Array.isArray(label.material)) throw new Error('Beverage label mesh is unavailable');
  const originalMaterial = label.material;
  const originalMap = originalMaterial.map ?? null;
  let variantMaterial = null;
  let texture = null;
  let current = 'original', disposed = false;
  const disposeVariant = () => {
    texture?.dispose(); texture = null;
    variantMaterial?.dispose(); variantMaterial = null;
  };
  const apply = id => {
    if (disposed || id === current) return;
    if (id === 'original') {
      label.material = originalMaterial; disposeVariant(); current = id; return;
    }
    const preset = LABEL_PRESETS.find(item => item.id === id);
    if (!preset) throw new Error(`Unknown label preset: ${id}`);
    const nextTexture = new THREE.CanvasTexture(drawLabel(preset, canvasFactory));
    nextTexture.colorSpace = THREE.SRGBColorSpace;
    // The GLB's cylindrical UVs are authored for GLTFLoader's flipY=false path.
    nextTexture.flipY = false; nextTexture.needsUpdate = true;
    const nextMaterial = originalMaterial.clone(); nextMaterial.map = nextTexture; nextMaterial.needsUpdate = true;
    label.material = nextMaterial; disposeVariant(); texture = nextTexture; variantMaterial = nextMaterial; current = id;
  };
  return {
    apply,
    reset: () => apply('original'),
    get current() { return current; },
    get originalMap() { return originalMap; },
    get texture() { return texture; },
    dispose() { if (disposed) return; disposed = true; label.material = originalMaterial; disposeVariant(); current = 'original'; },
  };
}
