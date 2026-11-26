import { MathUtils } from 'three';

export function createRibbonEffect(envelope) {
  const pieces = [];
  for (const name of ['RibbonBow', 'RibbonPocketBand']) {
    const ribbon = envelope.getObjectByName(name);
    const fade = ribbon?.userData.releaseFade;
    if (!ribbon?.isMesh || !Array.isArray(fade) || fade.length !== 2) continue;
    const material = ribbon.material.clone();
    // Use the same shader from warm-up through the fade.
    material.transparent = true;
    ribbon.material = material;
    pieces.push({ ribbon, material, fade });
  }
  return time => {
    for (const { ribbon, material, fade } of pieces) {
      const opacity = 1 - MathUtils.smoothstep(time, fade[0], fade[1]);
      material.opacity = opacity;
      material.depthWrite = opacity === 1;
      ribbon.visible = opacity > 0;
    }
  };
}
