import { existsSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { items, status } from './status.mjs';

process.chdir(fileURLToPath(new URL('.',import.meta.url)));
const read = path=>JSON.parse(readFileSync(path,'utf8'));
const fileLink = (path,label=path)=>existsSync(path) ? `[${label}](${path})` : '—';
const index = ['# Male wardrobe fitting',
  '',
  'The candidates use the Studio male master and `../body_male.glb`. The motion bank is `../round2/motion_male_fixed.glb`. Source geometry and textures come from the neutral wardrobe. The copied build notes are in [NOTES.original.md](NOTES.original.md).',
  '',
  'Each candidate was reimported into Blender for the all-pose gate. The reports include rest, source endpoints, and every integer and half frame on the 24 fps and 30 fps grids. Inside counts and signed distances follow the body surface normals. Triangle pairs are intersections at an individual pose. The final candidates were remeasured with the full, uncropped Blender body BVH. Earlier rounds retain their original gate records. Shoes were checked against the shipped T-shirt and jeans. The skirt and shorts were checked against the shipped T-shirt. Shoe sole heights are measured against the bare-foot datum. A shoe-floor target of −6.5 mm uses the shipped sneaker outsole as the height reference.',
  '',
  '| Item | Triangles | MiB | Peak inside | Peak pairs | Min signed (mm) | Rounds used | Result |',
  '| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |'];
const evidence = [];
const attempts = [];
for (const item of items) {
  const path = `qa/${item}.result.json`;
  if (!existsSync(path)) {
    const rounds = [1,2,3].map(r=>status(item,r)).filter(Boolean);
    if (!rounds.length) {
      index.push(`| ${item} | — | — | — | — | — | — | Pending |`);
      continue;
    }
    const done = rounds.at(-1);
    index.push(`| ${item} | ${done.triangles} | ${(done.bytes/2**20).toFixed(3)} | ${done.inside} | ${done.pairs} | ${(1000*done.min).toFixed(4)} | ${rounds.length} | In progress |`);
    continue;
  }
  const {picked,rounds} = read(path);
  const {triangles,bytes,inside,pairs,min,pass,name,layer,solePass,staticPass} = picked;
  const visualPath = `qa/${item}.visual.json`;
  const visual = existsSync(visualPath) ? read(visualPath) : null;
  const verdict = !pass || visual?.pass === false ? 'FAIL' : visual ? 'PASS' : 'Visual check pending';
  index.push(`| ${item} | ${triangles} | ${(bytes/2**20).toFixed(3)} | ${inside} | ${pairs} | ${(1000*min).toFixed(4)} | ${rounds.length} | ${verdict} |`);
  const asset = pass ? `${item}.glb` : `${name}.glb`;
  const folder = `renders/${item}`;
  const gate = `qa/${item}.gate.json`;
  const parts = [fileLink(asset,pass?'GLB':`Review candidate (round ${picked.round})`),fileLink(gate,'All poses'),
    fileLink(`qa/${item}.validator.json`,'Khronos'),fileLink(folder+'/six-views.png','Six views')];
  if (item==='bottom-skirt') parts.push(fileLink(folder+'/motion-views.png','Motion witnesses'));
  evidence.push(`| ${item} | ${parts.join(' · ')} | ${layer} |`);
  const failures = [];
  const clips = Object.entries(read(gate).clips);
  if (inside || pairs || min < .0005) {
    const [clip,witness] = clips.reduce((a,b)=>a[1].min_signed_m<=b[1].min_signed_m?a:b);
    failures.push(`body clearance (minimum in ${clip} at frame ${witness.minimum_frame})`);
  }
  if (layer) {
    const [clip] = clips.find(([,r])=>Object.values(r.layer_peaks).includes(layer));
    failures.push(`layering (${layer} pairs peak in ${clip})`);
  }
  if (!solePass) failures.push('sole alignment');
  if (!staticPass) {
    const validator = read(`qa/${item}.validator.json`);
    const codes = validator.report.issues.messages.filter(m=>m.severity<2).map(m=>m.code);
    failures.push(codes.length ? `Khronos validator (${codes.join(', ')})` : 'GLB budget or skeleton');
  }
  attempts.push(`- **${item}** · ${rounds.map(r=>`[R${r.round}](qa/${r.name}.gate.json) (${r.inside} inside, ${r.pairs} body pairs, ${(r.min*1000).toFixed(4)} mm, ${r.layer} layer pairs)`).join(' · ')}.`
    + (failures.length ? ` Selected candidate failed ${failures.join(', ')}.` : '')
    + (visual ? ` ${visual.notes}` : ''));
}
if (existsSync('qa/witness-replay.json')) {
  const rows = Object.values(read('qa/witness-replay.json'));
  const count = rows.reduce((sum,row)=>sum+row.witnesses,0);
  const discrepancies = rows.reduce((sum,row)=>sum+row.discrepancies.length,0);
  index.push('', `A fresh Blender session replayed ${count} witness poses and found ${discrepancies} discrepancies against the final gates. [Witness replay](qa/witness-replay.json)`);
}
index.push('', '## Files', '', '| Item | Evidence | Peak layer pairs |', '| --- | --- | ---: |',...evidence,
  '', '## Rounds', '', ...attempts, '',
  'Run `node batch_fit.mjs` to continue the ordered batch. Each item uses at most three candidate exports. The batch invokes one Blender process at a time, with two threads. Run `node report.mjs` to refresh this report.', '');
writeFileSync('NOTES.tmp', index.join('\n'));
renameSync('NOTES.tmp','NOTES.md');
