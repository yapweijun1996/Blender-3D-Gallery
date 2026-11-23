import { existsSync, readFileSync } from 'node:fs';

export const items = ['shoes-boots','bottom-skirt','bottom-shorts','shoes-sandals','shoes-slipons','shoes-hightop'];
const load = (path) => JSON.parse(readFileSync(path,'utf8'));
export function status(item, round) {
  const name = `${item}-r${round}`;
  const gatePath = `qa/${name}.gate.json`;
  const validatorPath = `qa/${name}.validator.json`;
  if (!existsSync(gatePath) || !existsSync(validatorPath)) return null;
  const gate = load(gatePath);
  const validator = load(validatorPath);
  if (gate.sha256 !== validator.sha256 || gate.triangles !== validator.triangles) throw Error(name+' mismatched gate');
  const clips = Object.values(gate.clips);
  if (clips.length !== 15 || clips.some(c=>!c.samples)) throw Error(name+' incomplete motion bank');
  const inside = Math.max(...clips.map(c=>c.peak_inside));
  const pairs = Math.max(...clips.map(c=>c.peak_pairs));
  const min = Math.min(...clips.map(c=>c.min_signed_m));
  const layer = Math.max(...clips.flatMap(c=>Object.values(c.layer_peaks)));
  const textureLimit = validator.textures.every(x=>Array.isArray(x) && x.every(d=>d>0 && d<=1024));
  const staticPass = gate.triangles <= (item.startsWith('shoes-') ? 3500 : 6000)
    && gate.bytes <= 1.5 * 2**20 && textureLimit && validator.errors === 0 && validator.warnings === 0
    && validator.joints === 65;
  const solePass = !item.startsWith('shoes-') || (
    Object.values(gate.rest_sole_mm).every(z=>Math.abs(z+6.5)<.5)
  );
  const pass = staticPass && solePass && inside===0 && pairs===0 && min>=.0005 && layer===0;
  return {item, round, name, sha256:gate.sha256, triangles:gate.triangles,
    bytes:gate.bytes, inside, pairs, min, layer, solePass, staticPass, pass};
}
