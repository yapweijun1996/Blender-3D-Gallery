import { TextureLoader } from "three";
import { EXPRESSIONS } from "./config.js";

const targets = EXPRESSIONS.filter(name => name !== "neutral");

/**
 * Face expressions for the body: three morph targets plus a colour map per expression.
 * The neutral map is embedded in the body; the other maps load on first use.
 */
export function createExpressionController(root, urls, loader = new TextureLoader()) {
  let body;
  root.traverse(node => {
    if (node.isSkinnedMesh && node.morphTargetDictionary) body = node;
  });
  if (!body?.material?.map || !targets.every(name => Number.isInteger(body.morphTargetDictionary["expr_" + name])))
    throw new Error("Body has no expression morph targets");
  const baseMaterial = body.material;
  const baseMap = baseMaterial.map;
  const material = baseMaterial.clone();
  body.material = material;
  const maps = new Map([["neutral", baseMap]]);
  const pending = new Map();
  let current = "neutral", requested = "neutral", disposed = false;

  function load(name) {
    if (maps.has(name)) return Promise.resolve(maps.get(name));
    if (!pending.has(name)) {
      pending.set(name, loader.loadAsync(urls[name]).then(map => {
        map.flipY = false;
        map.colorSpace = baseMap.colorSpace;
        map.wrapS = baseMap.wrapS;
        map.wrapT = baseMap.wrapT;
        map.minFilter = baseMap.minFilter;
        map.magFilter = baseMap.magFilter;
        map.anisotropy = baseMap.anisotropy;
        if (disposed) map.dispose(); else maps.set(name, map);
        return map;
      }).finally(() => pending.delete(name)));
    }
    return pending.get(name);
  }

  function apply(name) {
    for (const target of targets)
      body.morphTargetInfluences[body.morphTargetDictionary["expr_" + target]] = Number(name === target);
    material.map = maps.get(name);
    current = name;
  }

  return {
    /** Resolves once the expression is on screen; a later call wins over a slower earlier one. */
    async set(name) {
      if (disposed || !EXPRESSIONS.includes(name)) throw new RangeError("Unknown expression " + name);
      requested = name;
      await load(name);
      if (!disposed && requested === name) apply(name);
    },
    get current() { return current; },
    dispose() {
      if (disposed) return;
      disposed = true;
      body.material = baseMaterial;
      for (const [name, map] of maps) if (name !== "neutral") map.dispose();
      material.dispose();
    },
  };
}
