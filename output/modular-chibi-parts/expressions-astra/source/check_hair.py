"""Run the bob's two supplied checkers against each reimported expression."""
from pathlib import Path
import sys,json,hashlib,runpy,tempfile
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from face import *
from bpy.app.handlers import persistent

@persistent
def checker_preview(scene,*_):
    # Checker screenshots aren't deliverables. Use CPU for its throwaway renders.
    if scene.camera and scene.camera.name=="c" and scene.render.engine=="BLENDER_WORKBENCH":
        scene.render.engine="CYCLES"
        scene.cycles.device="CPU"
        scene.cycles.samples=1
        scene.render.resolution_percentage=8

def main():
    out=ROOT/"body_expressions.glb"
    motion=ROOT.parents[2]/"models/tripo-chibi-motion/motion.glb"
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    reports={}
    checksums={}
    for name in NAMES:
        body=open_body(out)
        for key in list(body.data.shape_keys.key_blocks)[1:]:
            key.value=float(key.name=="expr_"+name)
        path=WORK/(name+".blend")
        bpy.context.preferences.filepaths.save_version=0
        bpy.context.preferences.filepaths.file_preview_type="NONE"
        bpy.ops.wm.save_as_mainfile(filepath=str(path))
        reports[name]={}
        for method,script in (("vertices","motion_check.py"),("triangles","motion_check_tri.py")):
            source=HAIR.parent/script
            checksums[script]=sha(source)
            if checker_preview not in bpy.app.handlers.frame_change_pre:
                bpy.app.handlers.frame_change_pre.append(checker_preview)
            with tempfile.TemporaryDirectory(dir=WORK) as folder:
                old=sys.argv
                try:
                    sys.argv=[str(source),"--",str(path),str(motion),str(HAIR),folder]
                    runpy.run_path(str(source),run_name="__main__")
                finally:
                    sys.argv=old
                result=json.loads((Path(folder)/"motion_check.json").read_text())
                assert set(result)==set(("rest","walk","run","wave","jump","idle","nod","dance"))
                assert all(count==0 and dist>0 for count,dist in result.values()),(name,method,result)
                reports[name][method]=result
                print("CHECKER_COMPLETE",name,method,result,flush=True)
    (ROOT/"checks/hair.json").write_text(json.dumps({
        "body_sha256":sha(out),"hair_sha256":sha(HAIR),"motion_sha256":sha(motion),
        "supplied_checker_sha256":checksums,"units":"[maximum count, minimum signed distance in metres]",
        "vertices":"rest and 12 sampled frames per clip","triangles":"rest and every third integer frame per clip",
        "reports":reports},indent=2)+"\n")
main()
