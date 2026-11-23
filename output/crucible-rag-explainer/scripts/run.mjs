// One MCP session per run: create the scene from recipe.json, inspect, look, and optionally render a job.
// Usage: node run.mjs look 0,4,8          -> looks/look-<t>.png
//        node run.mjs job '<settings json>' <outdir>
import fs from 'node:fs';
import { connect, dir } from './mcp.mjs';

const [mode, arg, outDir] = process.argv.slice(2);
const recipe = JSON.parse(fs.readFileSync(dir + '/recipe.json'));
const m = await connect();
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
try {
  const created = await m.data('scene_create', { recipe }, 300000);
  const sessionId = created.sessionId;
  const ins = await m.data('scene_inspect', { sessionId });
  const revision = ins.revision ?? created.revision;
  const diag = ins.diagnostics ?? [];
  console.log('revision', revision, 'diagnostics', JSON.stringify(diag).slice(0, 2500));
  if (ins.bounds) console.log('bounds', JSON.stringify(ins.bounds).slice(0, 400));

  if (mode === 'look') {
    fs.mkdirSync(dir + '/looks', { recursive: true });
    for (const t of arg.split(',').map(Number)) {
      const r = await m.image('scene_look', { sessionId, motionTime: t, width: 1024, height: 576 }, `${dir}/looks/look-${t}.png`);
      console.log('look', t, r.images, r.text.slice(0, 300).replace(/\n/g, ' '));
    }
  }

  if (mode === 'job') {
    const settings = JSON.parse(arg);
    await m.image('scene_look', { sessionId, motionTime: 0, width: 512, height: 288 }, `${dir}/pre-job-look.png`);
    const sub = await m.data('scene_render_submit', { sessionId, expectedRevision: revision, settings }, 300000);
    console.log('submit', JSON.stringify(sub).slice(0, 1200));
    const jobId = sub.jobId;
    const t0 = Date.now();
    let st;
    for (;;) {
      await sleep(8000);
      st = await m.data('scene_render_status', { jobId });
      console.log(`[${((Date.now() - t0) / 1000).toFixed(0)}s]`, JSON.stringify(st).slice(0, 300));
      if (['completed', 'failed', 'cancelled', 'interrupted'].includes(st.state ?? st.status)) break;
    }
    const res = await m.data('scene_render_result', { jobId, response_format: 'detailed' }, 300000);
    fs.writeFileSync(`${dir}/job-result.json`, JSON.stringify(res, null, 1));
    console.log('result', JSON.stringify(res).slice(0, 2500));
    fs.mkdirSync(outDir, { recursive: true });
    const paths = JSON.stringify(res).match(/"(\/[^"]+\.(?:png|mp4))"/g) ?? [];
    for (const p of [...new Set(paths.map((s) => JSON.parse(s)))]) {
      if (fs.existsSync(p)) { fs.copyFileSync(p, `${outDir}/${p.split('/').pop()}`); console.log('copied', p); }
    }
    await m.data('scene_render_release', { jobId });
  }

  if (mode === 'export') {
    const rr = await m.data('scene_export_recipe', { sessionId });
    fs.writeFileSync(arg, JSON.stringify(rr.recipe ?? rr, null, 1) + '\n');
    console.log('exported recipe to', arg);
  }
} finally { await m.close(); }
