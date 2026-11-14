import test from 'node:test';
import assert from 'node:assert/strict';
import { Group, Mesh, CylinderGeometry, MeshStandardMaterial, Texture, SRGBColorSpace } from 'three';
import { LABEL_PRESETS, createLabelController } from '../src/product-studio/labels.js';
function setup(){
 const model=new Group(),originalMap=new Texture(),material=new MeshStandardMaterial({map:originalMap}),mesh=new Mesh(new CylinderGeometry(),material);mesh.name='LABEL_OriginalCitrusBand';model.add(mesh);
 const canvases=[];let originalDisposals=0;originalMap.addEventListener('dispose',()=>originalDisposals++);material.addEventListener('dispose',()=>originalDisposals++);
 const canvasFactory=()=>{const ops=[],ctx={fillRect(...args){ops.push({type:'rect',color:this.fillStyle,args});},fillText(...args){ops.push({type:'text',color:this.fillStyle,args});}};const canvas={getContext:()=>ctx,ops};canvases.push(canvas);return canvas;};
 const controller=createLabelController(model,{canvasFactory});
 return {controller,mesh,material,originalMap,canvases,get originalDisposals(){return originalDisposals;}};
}
const observe=o=>{let count=0;o.addEventListener('dispose',()=>count++);return()=>count;};
test('presets are distinct fictional studies',()=>{
 assert.equal(LABEL_PRESETS.length,3);assert.equal(new Set(LABEL_PRESETS.map(p=>p.id)).size,3);
 for(const p of LABEL_PRESETS)assert.doesNotMatch(p.name+' '+p.caption,/brand|certif|nutrition|calorie|vitamin|organic/i);
});
test('actual Three material replacement retains original map and releases each generated resource once',()=>{
 const h=setup();h.controller.apply('citrus-grid');const first=h.mesh.material,map=first.map,textureCount=observe(map),materialCount=observe(first);
 assert.notEqual(first,h.material);assert.equal(map.isCanvasTexture,true);assert.equal(map.flipY,false);assert.equal(map.colorSpace,SRGBColorSpace);assert.equal(map.image.width,1024);assert.equal(map.image.height,512);
 h.controller.apply('citrus-grid');assert.equal(h.mesh.material,first);assert.equal(h.canvases.length,1);
 h.controller.apply('berry-night');assert.equal(textureCount(),1);assert.equal(materialCount(),1);
 const second=h.mesh.material,c2=observe(second),t2=observe(second.map);h.controller.reset();assert.equal(h.mesh.material,h.material);assert.equal(h.mesh.material.map,h.originalMap);assert.equal(c2(),1);assert.equal(t2(),1);assert.equal(h.originalDisposals,0);
 h.controller.reset();h.controller.dispose();h.controller.dispose();h.controller.apply('mint-signal');assert.equal(h.canvases.length,2);assert.equal(h.originalDisposals,0);assert.equal(c2(),1);assert.equal(t2(),1);
});
test('disposing while runtime label active restores authored material without disposing its map',()=>{
 const h=setup();h.controller.apply('mint-signal');const m=observe(h.mesh.material),t=observe(h.mesh.material.map);h.controller.dispose();h.controller.dispose();assert.equal(m(),1);assert.equal(t(),1);assert.equal(h.mesh.material,h.material);assert.equal(h.originalDisposals,0);
});
test('invalid selection and failed canvas preserve current visible label',()=>{
 const h=setup();h.controller.apply('mint-signal');const m=h.mesh.material;assert.throws(()=>h.controller.apply('unknown'),/Unknown/);assert.equal(h.mesh.material,m);h.controller.dispose();
 const broken=createLabelController(h.mesh.parent,{canvasFactory:()=>({getContext:()=>null})});assert.throws(()=>broken.apply('citrus-grid'),/canvas/);assert.equal(h.mesh.material,h.material);broken.dispose();
 assert.throws(()=>createLabelController(new Group()),/unavailable/);
});
test('drawn backgrounds repeat seamlessly and all captions have contrasting solid backing',()=>{
 for(const preset of LABEL_PRESETS){const h=setup();h.controller.apply(preset.id);const c=h.canvases[0];
 const pixel=(x,y)=>c.ops.filter(o=>o.type==='rect'&&x>=o.args[0]&&x<o.args[0]+o.args[2]&&y>=o.args[1]&&y<o.args[1]+o.args[3]).at(-1)?.color;
 for(let y=0;y<512;y++)assert.equal(pixel(0,y),pixel(1023,y),'seam row '+y);
 for(const op of c.ops.filter(o=>o.type==='text')){assert.equal(op.color,preset.paper);assert.equal(pixel(op.args[1],op.args[2]),preset.ink);}
 const luminance=hex=>{const rgb=hex.slice(1).match(/../g).map(c=>parseInt(c,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];};
 const a=luminance(preset.ink),b=luminance(preset.paper);assert.ok((Math.max(a,b)+.05)/(Math.min(a,b)+.05)>7);h.controller.dispose();
 }
});
