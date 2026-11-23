import { TextureLoader } from 'three';

const targets = ['happy', 'surprised', 'sad'];

/** Preload the three external maps. Create one controller per loaded character. */
export async function createExpressionController(
  root,
  textureDirectory = new URL('./textures/', import.meta.url),
  loader = new TextureLoader()
) {
  const body = root.getObjectByName('Base_Body');
  if (!body?.isSkinnedMesh || !body.material?.isMeshStandardMaterial ||
      !body.material.map || !targets.every(name => Number.isInteger(body.morphTargetDictionary?.['expr_' + name]))) {
    throw new Error('Expected Base_Body from body_expressions.glb.');
  }

  const baseMaterial = body.material;
  const baseMap = baseMaterial.map;
  const maps = new Map([['neutral', baseMap]]);
  const directory = new URL(textureDirectory, import.meta.url);
  const results = await Promise.allSettled(targets.map(async name => {
    const map = await loader.loadAsync(new URL(name + '.png', directory).href);
    map.flipY = false;
    map.colorSpace = baseMap.colorSpace;
    map.wrapS = baseMap.wrapS;
    map.wrapT = baseMap.wrapT;
    map.minFilter = baseMap.minFilter;
    map.magFilter = baseMap.magFilter;
    map.anisotropy = baseMap.anisotropy;
    maps.set(name, map);
  }));
  const failure = results.find(result => result.status === 'rejected');
  function releaseMaps() {
    for (const name of targets) maps.get(name)?.dispose();
  }
  if (failure) {
    releaseMaps();
    throw failure.reason;
  }

  const material = baseMaterial.clone();
  body.material = material;
  let disposed = false;
  function applyExpression(name) {
    if (disposed) throw new Error('Expression controller has been disposed.');
    if (!maps.has(name)) throw new RangeError('Unknown expression ' + name);
    for (const target of targets) {
      body.morphTargetInfluences[body.morphTargetDictionary['expr_' + target]] = Number(name === target);
    }
    material.map = maps.get(name);
  }
  applyExpression('neutral');

  return {
    applyExpression,
    dispose() {
      if (disposed) return;
      applyExpression('neutral');
      body.material = baseMaterial;
      releaseMaps();
      material.dispose();
      disposed = true;
    }
  };
}
