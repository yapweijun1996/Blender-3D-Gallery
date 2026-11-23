import { spawnSync } from 'node:child_process';
import { closeSync, copyFileSync, existsSync, openSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { items, status } from './status.mjs';

process.chdir(fileURLToPath(new URL('.',import.meta.url)));
const selected = process.argv.slice(2);
const queue = selected.length ? selected : items;
if (queue.some(id=>!items.includes(id))) throw Error('Unknown item');

function run(cmd,args,log) {
  const fd = log ? openSync(log,'w') : null;
  try {
    const child = spawnSync(cmd,args,{stdio:log ? ['ignore',fd,fd] : 'inherit'});
    if (child.error) throw child.error;
    if (child.status !== 0) throw Error(`${cmd} ${args.join(' ')} exited with ${child.signal ?? child.status} ${log ?? ''}`);
  } finally {
    if (fd !== null) closeSync(fd);
  }
}

for (const item of queue) {
  const shoe = item.startsWith('shoes-');
  const source = `../../../../../models/chibi-dressup/modules/${item}.glb`;
  const results = [];
  for (let round=1; round<=3; round++) {
    const name = `${item}-r${round}`;
    if (!status(item,round)) {
      if (!existsSync(name+'.glb')) {
        if (round===1) {
          run('./run.sh',['fit_module.py','--',source,name+'.glb','--slot',shoe?'shoes':'bottom',
            '--iterations','7','--external-gate'],`qa/${name}.log`);
        } else {
          const previous = results.at(-1).name;
          run('./run.sh',['refit_layers.py','--',previous+'.glb',name+'.glb',
            `qa/${previous}.gate.json`,'--mode',round===3?'conform':'radial'],`qa/${name}.log`);
        }
      }
      run('./gate.sh',[item,String(round)]);
    }
    const result = status(item,round);
    results.push(result);
    console.log(result);
    if (result.pass) {
      copyFileSync(name+'.glb',item+'.glb');
      break;
    }
  }
  const picked = results.find(r=>r.pass) ?? [...results].sort((a,b)=>
    (a.pairs+a.inside+a.layer)-(b.pairs+b.inside+b.layer) || b.min-a.min)[0];
  const candidate = picked.pass ? item+'.glb' : picked.name+'.glb';
  const gateActual = `qa/${picked.name}.gate.json`;
  copyFileSync(gateActual,`qa/${item}.gate.json`);
  copyFileSync(`qa/${picked.name}.validator.json`,`qa/${item}.validator.json`);
  writeFileSync(`qa/${item}.result.json`,JSON.stringify({picked, rounds:results},null,2)+'\n');
  if (!existsSync(`renders/${item}/manifest.json`)) {
    run('./run.sh',['render_wardrobe.py','--',candidate,item,gateActual],`qa/${item}.render.log`);
  }
}
