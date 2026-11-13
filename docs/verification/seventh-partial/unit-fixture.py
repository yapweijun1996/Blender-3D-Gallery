from pathlib import Path
import subprocess,os
R=Path(__file__).resolve().parents[3]
F=R.parent/'unit-fixture-fixed-pass'
assert not F.exists(),'Preserve prior fixture; no retry-to-green'
F.mkdir()
# Independent file copies, never hard links. Keep every source/test/evidence file.
for p in R.iterdir():
 if p.name in ['.git','node_modules','dist','output']:continue
 subprocess.run(['cp','-a','--reflink=auto',str(p),str(F/p.name)],check=True)
(F/'node_modules').symlink_to((R/'node_modules').resolve(),target_is_directory=True)
print('Unchanged unit suite running in independent fixture; source-writing validators cannot touch canonical evidence',flush=True)
raise SystemExit(subprocess.run(['npm','test'],cwd=F,env=os.environ.copy()).returncode)
