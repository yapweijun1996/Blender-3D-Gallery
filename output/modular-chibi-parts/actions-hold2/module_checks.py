"""Use the existing two garment gates, with the three new clips and half-frame sampling."""
import sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
PROCEDURE=PARTS/'body-fix/act'
MODULES={'bob':PARTS/'hair-fit-astra/round2/hair_bob_v2.glb',
         'spiky':PARTS/'studio-modules/hair-spiky/hair_spiky_v1.glb',
         'sidepart':PARTS/'studio-modules/hair-sidepart/round3/hair_sidepart_v3.glb',
         'sneakers':PARTS/'shoes-sol/round3/shoes_sneaker_v3.glb'}
def run():
    from types import ModuleType
    source=(PROCEDURE/'motion_check.py').read_text()
    # Keep both of the upstream geometric tests intact; change only the sample clock.
    old='for f in range(first,last+1):\n                scene.frame_set(f)'
    new='for tick in range(2*first,2*last+1):\n                f=tick/2\n                scene.frame_set(tick//2,subframe=(tick%2)*.5)'
    assert source.count(old)==1
    mod=ModuleType('hold2_garment_gates')
    mod.__file__=str(PROCEDURE/'motion_check.py')
    exec(compile(source.replace(old,new),mod.__file__,'exec'),mod.__dict__)
    mod.LEGACY=()
    mod.ADDED=NAMES
    mod.FPS=FPS
    import runpy
    sys.modules['motion_check']=mod
    for label,path in MODULES.items():
        out=HERE/'checks'/label
        sys.argv=['Blender','--',str(MASTER),str(FIXED),str(path),str(out),str(BANK)]
        mod.garment_check()
        runpy.run_path(str(PROCEDURE/'motion_check_tri.py'),run_name='__main__')

if __name__=='__main__':run()
