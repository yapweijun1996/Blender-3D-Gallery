const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const dir = __dirname;
const scratch = '/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular';
const work = path.join(dir, '.runtime');
fs.mkdirSync(work, { recursive: true });

const [script, ...args] = process.argv.slice(2);
if (!script) throw new Error('Specify a Blender Python script.');
const blender = spawn(process.env.BLENDER || path.join(scratch, 'B/Blender.app/Contents/MacOS/Blender'), [
    '-b', '-noaudio', '-t', process.env.BLENDER_THREADS || '6', '--python-exit-code', '1',
    '--python', path.resolve(dir, script), '--', ...args,
], {
    cwd: dir,
    env: {
        ...process.env,
        DYLD_INSERT_LIBRARIES: process.env.DYLD_INSERT_LIBRARIES || path.join(scratch, 'guard.dylib'),
        TMPDIR: work + '/',
        XDG_CACHE_HOME: work,
        PYTHONDONTWRITEBYTECODE: '1',
        VECLIB_MAXIMUM_THREADS: '2',
        OPENBLAS_NUM_THREADS: '2',
    },
    stdio: 'inherit',
});
blender.on('error', error => { console.error(error); process.exitCode = 1; });
blender.on('exit', (code, signal) => { if (signal) console.error(signal); process.exitCode = code ?? 1; });
