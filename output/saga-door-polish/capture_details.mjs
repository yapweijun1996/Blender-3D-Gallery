import {chromium} from 'playwright';
const b=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{const page=await b.newPage({viewport:{width:1200,height:900}});await page.goto(process.env.SAGA_DOOR_URL ?? 'http://127.0.0.1:4188/demo.html');await page.waitForFunction(()=>window.sagaRig?.doors);
for(const id of ['FL','FR','RL','RR']){
 await page.locator('#reset').click();await page.selectOption('#door',id);await page.locator('#door-open').fill('60');
 await page.evaluate(id=>{const {THREE,renderer,scene,camera,doors,model}=window.sagaRig;renderer.setAnimationLoop(null);model.updateMatrixWorld(true);let card;doors[id].traverse(o=>{if(o.isMesh&&o.material?.name==='Dark woven seat cloth')card=o});const center=new THREE.Box3().setFromObject(card).getCenter(new THREE.Vector3());const normal=new THREE.Vector3(0,0,id.endsWith('L')?-1:1).applyQuaternion(doors[id].quaternion);camera.position.copy(center).addScaledVector(normal,.8).add(new THREE.Vector3(0,.12,0));camera.fov=62;camera.lookAt(center);camera.updateProjectionMatrix();renderer.render(scene,camera)},id);
 await page.screenshot({path:new URL(`./door-${id}-interior.png`,import.meta.url).pathname});
}
}finally{await b.close()}
