import { spawn } from 'node:child_process';
import { createWriteStream, mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const here = dirname(fileURLToPath(import.meta.url));
export const root = resolve(here, '../../..');
export const work = join(here, '.work');
export const names = ['hair-bob', 'hair-spiky', 'hair-sidepart', 'shoes-sneakers',
  'top-tshirt', 'bottom-jeans', 'top-dress'];
export const source = name => join(root, 'models/chibi-dressup/modules', name + '.glb');

const scratch = process.env.NPC_LEGACY_CHECKERS ?? '/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular';
const blender = process.env.NPC_BLENDER ?? join(scratch, 'B/Blender.app/Contents/MacOS/Blender');
const guard = process.env.NPC_GUARD ?? join(scratch, 'guard.dylib');

export function launch(script, args, log) {
  mkdirSync(dirname(log), { recursive: true });
  mkdirSync(work, { recursive: true });
  const env = { ...process.env, NPC_LEGACY_CHECKERS: scratch,
    DYLD_INSERT_LIBRARIES: guard, TMPDIR: work, BLENDER_USER_RESOURCES: join(work, 'blender-user'), PYTHONDONTWRITEBYTECODE: '1' };
  const child = spawn(blender, ['-b', '-noaudio', '--disable-autoexec', '-t',
    process.env.NPC_THREADS ?? '2', '--python-exit-code', '1',
    '--python', join(here, script), '--', ...args], { cwd: here, env });
  const stream = createWriteStream(log);
  child.stdout.pipe(stream, { end: false });
  child.stderr.pipe(stream, { end: false });
  return new Promise((done, reject) => {
    child.on('error', reject);
    child.on('close', code => stream.end(() => {
      if (code === 0) done();
      else reject(new Error(`${script} ${args.join(' ')} exited ${code}. See ${log}`));
    }));
  });
}

export async function pool(jobs) {
  const concurrency = Number(process.env.NPC_JOBS ?? 4);
  const errors = [];
  await Promise.all(Array.from({ length: concurrency }, async () => {
    while (jobs.length) {
      try { await jobs.shift()(); } catch (err) { errors.push(err); console.error(err.message); }
    }
  }));
  if (errors.length) throw new AggregateError(errors, 'Blender jobs failed');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [mode, ...selected] = process.argv.slice(2);
  const modules = selected.length ? selected : names;
  if (!modules.every(name => names.includes(name))) throw new Error('Unknown module');
  if (mode === 'check' || mode === 'baseline') {
    const baseline = mode === 'baseline';
    const jobs = modules.flatMap(name => ['legacy', 'actions'].flatMap(family =>
      ['vertices', 'triangles'].map(metric => async () => {
        const dir = join(work, mode, name, family, metric);
        const asset = baseline ? source(name) : join(here, 'npc-' + name + '.glb');
        await launch('check_motion.py', [family, metric, asset, dir], join(dir, 'blender.log'));
        console.log(mode, name, family, metric);
      })));
    await pool(jobs);
  } else if (mode === 'build') {
    await launch('build_npc.py', modules, join(work, 'build.log'));
  } else if (mode === 'guard') {
    await launch('motion_collapse.py', modules, join(work, 'guard.log'));
  } else if (mode === 'fit') {
    await launch('fit_motion.py', modules, join(work, 'fit.log'));
  } else if (mode === 'audit') {
    await launch('audit_geometry.py', modules, join(work, 'audit.log'));
  } else if (mode === 'render') {
    await launch('render_outfits.py', [], join(work, 'render.log'));
  } else {
    throw new Error('Expected build, guard, fit, baseline, check, audit or render');
  }
}
