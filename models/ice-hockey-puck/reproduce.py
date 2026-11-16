"""Two independent factory-reset builds; restore the delivery files afterwards."""
from pathlib import Path
import subprocess,json,struct,hashlib,tempfile
HERE=Path(__file__).resolve().parent

def signature(blob):
    n=struct.unpack_from('<I',blob,12)[0];j=json.loads(blob[20:20+n]);data=blob[28+n:]
    result=[]
    for mesh in j['meshes']:
        for p in mesh['primitives']:
            a=j['accessors'][p['attributes']['POSITION']];v=j['bufferViews'][a['bufferView']];offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',12)
            pts=sorted(tuple(round(x,6) for x in struct.unpack_from('<fff',data,offset+i*stride)) for i in range(a['count']))
            ix=j['accessors'][p['indices']]
            result.append({'material':j['materials'][p['material']]['name'],'vertices':a['count'],'triangles':ix['count']//3,'positions_sha256':hashlib.sha256(json.dumps(pts).encode()).hexdigest()})
    return sorted(result,key=lambda p:p['material'])
paths=[p for base in ['sources','exports'] for p in (HERE/base).rglob('*') if p.is_file()]+[HERE/'reports/source-geometry.json']
backup={p:p.read_bytes() for p in paths};runs=[]
try:
    for i in range(2):
        cmd=['blender','-noaudio','-t','1','--background','--python-exit-code','1','--python',str(HERE/'generate.py'),'--','--skip-render']
        with tempfile.TemporaryFile(mode='w+') as log:
            r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        if r.returncode:raise RuntimeError(f'Build {i+1} failed: {r.returncode}')
        blob=(HERE/'exports/optimized.glb').read_bytes();runs.append({'sha256':hashlib.sha256(blob).hexdigest(),'primitives':signature(blob)})
    same=runs[0]['primitives']==runs[1]['primitives']
    report={'result':'PASS' if same else 'FAIL','method':'Two independent factory-reset --skip-render builds, per-primitive vertex/triangle counts and sorted vertex positions rounded to one micrometre. -noaudio is used; the generator flushes and exits directly after synchronous background writes to avoid the host PulseAudio teardown hang. Delivery source, textures, GLB and source report restored in finally.','geometry_identical':same,'byte_identical':runs[0]['sha256']==runs[1]['sha256'],'runs':runs,'delivery_restored':True}
finally:
    for p,b in backup.items():p.write_bytes(b)
delivery=(HERE/'exports/optimized.glb').read_bytes()
report['delivery_glb_sha256']=hashlib.sha256(delivery).hexdigest()
report['delivery_geometry_matches_runs']=signature(delivery)==runs[0]['primitives']
report['restored_files_verified']=all(p.read_bytes()==blob for p,blob in backup.items())
assert report['delivery_geometry_matches_runs'] and report['restored_files_verified']
(HERE/'reports/reproducibility.json').write_text(json.dumps(report,indent=2)+'\n')
assert same,report
print(HERE.name,report['result'])
