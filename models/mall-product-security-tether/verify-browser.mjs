// Show the three delivered files under the same light and camera, plus the secured laptop on its original display table.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const base=dirname(fileURLToPath(import.meta.url));
const req=createRequire(resolve('package.json'));
const three=resolve(dirname(req.resolve('three')),'..');
const {chromium}=req('playwright');
const {launchOptions}=await import(pathToFileURL(resolve('scripts/browser-test-utils.mjs')));
const evidence=JSON.parse(await fs.readFile(resolve(base,'reports/geometry.json')));
const browser=await chromium.launch(launchOptions);
try {
  const page=await browser.newPage({viewport:{width:900,height:670},deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://127.0.0.1:18323/**',async route=>{
    const p=new URL(route.request().url()).pathname;
    if(p==='/') return route.fulfill({contentType:'text/html',body:`<!doctype html><meta charset=utf-8><style>*{box-sizing:border-box}body{margin:0;display:flex;align-content:start;flex-wrap:wrap;background:#e7e1dc;color:#413c37;font:15px system-ui}figure{margin:0}canvas{display:block}figcaption{padding:5px 12px}</style><script type=importmap>{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>`});
    if(p.startsWith('/three/')&&p.endsWith('.js')) {
      const file=resolve(three,p.slice(7));assert.ok(file.startsWith(three+'/'));
      return route.fulfill({path:file,contentType:'text/javascript'});
    }
    const assembly={'/table':'models/tv-demo-table/exports/optimized.glb','/laptop':'models/laptop/exports/optimized.glb'};
    if(assembly[p])return route.fulfill({path:resolve(assembly[p]),contentType:'model/gltf-binary'});
    const entry=evidence.levels.find(v=>'/'+v.file===p);
    if(entry)return route.fulfill({path:resolve(base,entry.file),contentType:'model/gltf-binary'});
    return route.fulfill({status:404,body:''});
  });
  await page.goto('http://127.0.0.1:18323/');
  const results=await page.evaluate(async levels=>{
    const T=await import('three');
    const {GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');
    const {RoomEnvironment}=await import('three/addons/environments/RoomEnvironment.js');
    const render=new T.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});
    render.setClearColor(0,0);
    const pmrem=new T.PMREMGenerator(render),room=new RoomEnvironment(),env=pmrem.fromScene(room,.04);
    const scene=new T.Scene();
    scene.environment=env.texture;
    scene.environmentIntensity=.75;
    scene.add(new T.HemisphereLight(0xfff9f2,0xb4b5bd,1.8));
    const key=new T.DirectionalLight(0xfff3de,2);
    key.position.set(3,6,4);
    scene.add(key);
    function shot(object,w,h,scale,pos,target,label){
      scene.add(object);
      render.setSize(w,h);
      const camera=new T.OrthographicCamera(-scale*w/h/2,scale*w/h/2,scale/2,-scale/2,.01,20);
      camera.position.fromArray(pos);
      camera.lookAt(new T.Vector3(...target));
      render.render(scene,camera);
      const gl=render.getContext(),pixels=new Uint8Array(w*h*4);
      gl.readPixels(0,0,w,h,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
      const mask=new Uint8Array(w*h);
      let filled=0;
      for(let i=0;i<mask.length;i++){mask[i]=pixels[4*i+3]>127?1:0;filled+=mask[i];}
      const figure=document.createElement('figure'),caption=document.createElement('figcaption'),image=document.createElement('canvas');
      image.width=w;image.height=h;
      image.getContext('2d').drawImage(render.domElement,0,0);
      caption.textContent=label;
      figure.append(image,caption);
      document.body.append(figure);
      scene.remove(object);
      return {mask,filled,draws:render.info.render.calls,triangles:render.info.render.triangles};
    }
    const stats=[];
    let primary,firstMask;
    for(const row of levels){
      const response=await fetch('/'+row.file),bytes=await response.arrayBuffer();
      const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
      const object=(await new GLTFLoader().parseAsync(bytes,'')).scene;
      const view=shot(object,300,235,.160,[.011,.210,.24],[-.072,.013,.004],row.level);
      if(!firstMask){firstMask=view.mask;primary=object;}
      let overlap=0,union=0;
      for(let i=0;i<view.mask.length;i++){overlap+=view.mask[i]&&firstMask[i];union+=view.mask[i]||firstMask[i];}
      stats.push({level:row.level,sha256:sha,triangles:view.triangles,drawCalls:view.draws,objectPixels:view.filled,silhouetteIoU:overlap/union});
    }
    const mounted=new T.Group();
    async function install(id,translation) {
      const bytes=await (await fetch('/'+id)).arrayBuffer();
      const model=(await new GLTFLoader().parseAsync(bytes,'')).scene;
      model.position.fromArray(translation);mounted.add(model);
      return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
    }
    const tableSha=await install('table',[-.77,-.8,-.32]);
    const laptopSha=await install('laptop',[-.27,0,-.08]);
    mounted.add(primary);
    const detail=shot(mounted,900,355,.208,[.015,.255,.29],[-.11,.025,-.012],'Tether mounted on the original laptop and display table');
    return {levels:stats,detailPixels:detail.filled,tableSha,laptopSha};
  },evidence.levels);
  assert.deepEqual(errors,[]);
  for(const [i,row] of results.levels.entries()){
    const measured=evidence.levels[i];
    assert.equal(row.sha256,measured.sha256);
    assert.equal(row.triangles,measured.triangles);
    assert.equal(row.drawCalls,measured.draws);
    assert.ok(row.objectPixels>6700 && row.silhouetteIoU>.93,JSON.stringify(row));
  }
  assert.ok(results.detailPixels>80000);
  assert.equal(results.tableSha,evidence.tableSha256);assert.equal(results.laptopSha,evidence.laptopSha256);
  await page.screenshot({path:resolve(base,'reports/levels-and-installation.jpg'),type:'jpeg',quality:88});
  const report={browser:browser.version(),renderer:'Chromium software WebGL2',...results,errors};
  await fs.writeFile(resolve(base,'reports/browser.json'),JSON.stringify(report,null,2)+'\n');
  console.log(report);
} finally {
  await browser.close();
}
