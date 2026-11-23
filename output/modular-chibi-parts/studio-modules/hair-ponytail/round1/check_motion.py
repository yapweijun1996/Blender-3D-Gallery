"""Exercise the supplied measurement kernels at every integer and half-frame."""
import bpy,json,hashlib,sys,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
from fit_hair import GLB,MASTER,PARTS
SCRATCH=Path(os.environ.get('HAIR_CHECKER_DIR','/private/tmp/claude-501/-Users-yapweijun--claude-spares-spare-Iu3lC0/26a84d71-25c7-41e6-b903-49317aeebb05/scratchpad/modular'))
MOTION=PARTS/'body-fix/motion_fixed.glb'
BANKS={'shared':(MOTION,('walk','run','wave','jump','idle','nod','dance')),
       'act':(PARTS/'actions-fix/actions_fixed.glb',('sit_down','sit_idle','stand_up','hold_item')),
       'act2':(PARTS/'actions-hold2/hold_actions.glb',('hold_box','hold_bag','take_item'))}
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def save(f,v):f.write_text(json.dumps(v,indent=2)+'\n')
def shared(tri,out):
    source=SCRATCH/('motion_check_tri.py' if tri else 'motion_check_dense.py')
    setup=source.read_text().split('arm.animation_data_create();res={}',1)[0]
    scope={'__file__':str(source),'__name__':'provided_checker'}
    sys.argv=['checker','--',str(MASTER),str(MOTION),str(GLB),str(out)]
    exec(compile(setup,str(source),'exec'),scope)
    arm,sc,src=map(scope.get,('arm','sc','src'))
    acts={s.action.name:s.action for t in src.animation_data.nla_tracks for s in t.strips if s.action}
    if src.animation_data.action:acts[src.animation_data.action.name]=src.animation_data.action
    assert not arm.animation_data_create().nla_tracks
    arm.animation_data.use_nla=False
    stem='motion_check_tri' if tri else 'motion_check'
    arm.animation_data.action=None;sc.frame_set(1)
    res={'rest':scope['measure']()};detail={}
    for name in BANKS['shared'][1]:
        a=acts[name];arm.animation_data.action=a;arm.animation_data.action_slot=a.slots[0]
        first,last=map(int,a.frame_range);frames=[]
        for step in range(2*first,2*last+1):
            sc.frame_set(step//2,subframe=.5*(step%2))
            count,dist=scope['measure']()
            frames.append(dict(frame=step/2,count=count,min_signed_m=dist))
        detail[name]=frames;res[name]=(max(f['count'] for f in frames),min(f['min_signed_m'] for f in frames))
        print(name,stem,res[name],flush=True)
    save(out/(stem+'.json'),res);save(out/(stem+'_frames.json'),detail)
    return [source]
def extra(bank,tri,out):
    path=PARTS/'body-fix'/bank/'motion_check.py'
    src=path.read_text()
    # Preserve the measurement kernel and the bank's FPS, binder and import.
    # The shared bank already ran through its supplied dedicated checker.
    changes=[('inputs={Path(motion).resolve():LEGACY}','inputs={}'),
             ('for f in range(first,last+1):','for step in range(2*first,2*last+1):\n                f=step/2'),
             ('scene.frame_set(f)','scene.frame_set(step//2,subframe=.5*(step%2))')]
    for old,new in changes:
        assert src.count(old)==1,old
        src=src.replace(old,new)
    sys.modules.pop('chibi',None);sys.path.insert(0,str(path.parent))
    scope={'__file__':str(path),'__name__':'motion_check'}
    sys.argv=['checker','--',str(MASTER),str(MOTION),str(GLB),str(out),str(BANKS[bank][0])]
    exec(compile(src,str(path),'exec'),scope)
    if tri:
        import types
        shim=types.ModuleType('motion_check');shim.garment_check=scope['garment_check']
        sys.modules['motion_check']=shim
        entry=path.with_name('motion_check_tri.py')
        exec(compile(entry.read_text(),str(entry),'exec'),{'__file__':str(entry),'__name__':'__main__'})
    else:scope['garment_check']()
    sys.path.pop(0)
    return ([path,path.with_name('motion_check_tri.py')] if tri else [path])+[path.with_name('chibi.py')]
def main():
    args=sys.argv[sys.argv.index('--')+1:]
    for group in args or BANKS.keys():
        bank,_,only=group.partition('/')
        out=HERE/'checks'/bank;out.mkdir(exist_ok=True,parents=True)
        for tri in [False,True]:
            if only and only!=('tri' if tri else 'vertex'):continue
            files=shared(tri,out) if bank=='shared' else extra(bank,tri,out)
            stem='motion_check_tri' if tri else 'motion_check'
            frames=json.loads((out/(stem+'_frames.json')).read_text())
            assert set(frames)==set(BANKS[bank][1])
            for name,rows in frames.items():
                assert len(rows)>1 and all(abs(v['frame']-u['frame']-.5)<1e-8 for u,v in zip(rows,rows[1:]))
            save(out/(stem+'_provenance.json'),dict(glb_sha256=sha(GLB),master_sha256=sha(MASTER),clips_sha256=sha(BANKS[bank][0]),scripts={f.name:sha(f) for f in files},driver_sha256=sha(Path(__file__)),step_frames=.5))
if __name__=='__main__':main()

