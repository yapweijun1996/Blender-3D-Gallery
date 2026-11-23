"""Serve a snapshot of the selected GLB for a real-browser WebGL smoke test.

Example: python3 browser_probe.py --output /absolute/path/to/report-directory
Open the printed localhost URL in Chrome, wait for `Probe complete`, then
inspect the browser console and both PNGs. No Blender or source asset is edited.
The Three.js package must exist under THREE_DIR or the given --three path.
"""
import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parents[3]
DEFAULT_GLB = BASE / 'exports/gjh-reference-visitor-rigged.glb'
HTML = r'''<!doctype html><html><head><meta charset="UTF-8"><link rel="icon" href="data:,"><title>GJH GLB QA</title><style>html,body{margin:0;background:#aaa8ae}#status{position:fixed;left:8px;top:8px;font:13px sans-serif;background:white;padding:4px}</style><script type="importmap">{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script><script>window.qaMessages=[];for(const name of ['warn','error']){const original=console[name];console[name]=function(...args){window.qaMessages.push({type:name,text:args.map(String).join(' ')});original.apply(console,args)}}window.addEventListener('error',e=>window.qaMessages.push({type:'error',text:e.message}));window.addEventListener('unhandledrejection',e=>window.qaMessages.push({type:'error',text:String(e.reason)}));</script></head><body><div id="status">Loading</div><script type="module">
import * as THREE from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';const status=document.getElementById('status');
try{
 const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(1);renderer.setSize(750,900);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;renderer.domElement.setAttribute('role','img');renderer.domElement.setAttribute('aria-label','Visitor render');document.body.appendChild(renderer.domElement);
 const scene=new THREE.Scene();scene.background=new THREE.Color(0xaaa8ae);scene.add(new THREE.HemisphereLight(0xffffff,0xc0b8d0,2));const key=new THREE.DirectionalLight(0xffffff,2.3);key.position.set(-3,5,4);scene.add(key);const fill=new THREE.DirectionalLight(0xffffff,.8);fill.position.set(4,2,3);scene.add(fill);
 const cam=new THREE.OrthographicCamera(-.6125,.6125,.735,-.735,.01,100);const target=new THREE.Vector3(0,.65,0);
 window.setView=angle=>{let a=angle*Math.PI/180;cam.position.set(4*Math.sin(a),.65,4*Math.cos(a));cam.lookAt(target);cam.updateProjectionMatrix();renderer.render(scene,cam);return angle;};
 const gltf=await new GLTFLoader().loadAsync('/character.glb');scene.add(gltf.scene);gltf.scene.updateMatrixWorld(true);
 let meshCount=0,faceMats=[];gltf.scene.traverse(o=>{if(o.isMesh){meshCount++;if(o.name.toLowerCase().includes('head')||o.name.toLowerCase().includes('face')||o.name.toLowerCase().includes('eye'))faceMats.push({name:o.name,materials:(Array.isArray(o.material)?o.material:[o.material]).map(m=>({name:m.name,transparent:m.transparent,opacity:m.opacity,alphaTest:m.alphaTest,depthWrite:m.depthWrite,side:m.side}))})}});
 for(const [name,angle] of [['front',0],['quarter',32]]){window.setView(angle);const blob=await new Promise(r=>renderer.domElement.toBlob(r,'image/png'));const response=await fetch('/save/'+name,{method:'POST',body:blob});if(!response.ok)throw Error('Capture failed: '+name);}
 window.qaResult={status:'Loaded',meshCount,animations:gltf.animations.map(a=>a.name),three:THREE.REVISION,webgl:renderer.capabilities.isWebGL2?'WebGL2':'WebGL',faceMats,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,userAgent:navigator.userAgent,canvas:[renderer.domElement.width,renderer.domElement.height],messages:window.qaMessages};
 const response=await fetch('/save/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(window.qaResult)});if(!response.ok)throw Error('Report write failed');status.textContent='Probe complete';
}catch(e){status.textContent='ERROR '+e.message;console.error(e);window.qaResult={status:'ERROR',message:e.message};}
</script></body></html>'''

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

parser=argparse.ArgumentParser()
parser.add_argument('--character',type=Path,default=DEFAULT_GLB)
parser.add_argument('--three',type=Path,default=Path(os.environ.get('THREE_DIR','/tmp/gjh-hair-three/node_modules/three')))
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
source=args.character.resolve();three=args.three.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
if not (three/'build/three.module.js').exists() or not (three/'examples/jsm/loaders/GLTFLoader.js').exists():
    raise SystemExit('Three.js package missing; set THREE_DIR or --three')
if not source.is_file():raise SystemExit('Character GLB missing')
with tempfile.TemporaryDirectory(prefix='gjh-browser-snapshot-') as tmp:
    root=Path(tmp);source_hash=digest(source);shutil.copy2(source,root/'character.glb')
    if digest(root/'character.glb')!=source_hash:raise SystemExit('GLB snapshot hash mismatch')
    os.symlink(three,root/'three');(root/'index.html').write_text(HTML)
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self,*a,**kw):super().__init__(*a,directory=str(root),**kw)
        def do_POST(self):
            if self.path not in ('/save/front','/save/quarter','/save/report'):
                self.send_error(404);return
            size=int(self.headers.get('Content-Length','0'))
            if not (0<size<5_000_000):self.send_error(400);return
            data=self.rfile.read(size);name=self.path.rsplit('/',1)[-1]
            if name in ('front','quarter'):
                if not data.startswith(b'\x89PNG\r\n\x1a\n'):self.send_error(400);return
                (out/(name+'.png')).write_bytes(data)
            else:
                report=json.loads(data)
                report.update({'source':str(source),'source_sha256_at_start':source_hash,
                               'source_sha256_at_finish':digest(source),'snapshot_sha256':digest(root/'character.glb'),
                               'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                               'capture_method':'WebGL canvas PNG from actual Chrome','visual_review':'PENDING',
                               'limitations':['Static default pose at two angles; no animation or material parity assurance.','Canvas capture in the browser; no physical-device testing.']})
                for name in ('front','quarter'):
                    image=out/(name+'.png');report[name+'_sha256']=digest(image) if image.exists() else None
                (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
            self.send_response(204);self.end_headers()
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    print('http://127.0.0.1:%d/'%server.server_address[1],flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
