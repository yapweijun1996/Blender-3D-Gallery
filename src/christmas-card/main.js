import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import modelUrl from '../../models/christmas-envelope/envelope.glb?url';
import '../../christmas-card/card.css';
import { greeting } from './config.js';
import { frameEnvelope } from './framing.js';

const $ = id => document.getElementById(id);
const words = {
  en:{title:'A Christmas Greeting',subtitle:'A little wish, wrapped with love.',eyebrow:'✦  A LITTLE CHRISTMAS MAGIC  ✦',open:'Tap to Open / 点击打开',replay:'Replay ↻',sound:'Sound on',muted:'Muted',update:'Check for updates',install:'Update now',checking:'Checking…',current:'You have the latest version.',ready:'An update is ready.',error:'Unable to check for updates.',fallback:'The 3D card could not be loaded. Here is your greeting:',lang:'Switch to Chinese'},
  zh:{title:'圣诞祝福',subtitle:'一份小小心意，满载温暖。',eyebrow:'✦  一点圣诞魔法  ✦',open:'点击打开 / Tap to Open',replay:'重新播放 ↻',sound:'声音开启',muted:'静音',update:'检查更新',install:'立即更新',checking:'正在检查…',current:'已是最新版本。',ready:'新版本已准备好。',error:'无法检查更新。',fallback:'无法加载 3D 贺卡，请阅读这份祝福：',lang:'切换为英文'},
};
let lang='en', muted=false, state='loading', mixer, action, envelope, letter, renderer, scene, camera, registration, pendingUpdate=false, audio, start=performance.now(), revealTimers=[], particles=[], bodyWidth=3.2, burstDone=false;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
// The browser test can freeze an actual rendered burst, rather than guessing a delay.
let testCaptureTime=null, testFrozen=false;
const testHook=new URLSearchParams(location.search).has('card-test') ? {
  snapshot:null,
  captureAt(time){this.snapshot=null;testCaptureTime=time;testFrozen=false},
  release(){testFrozen=false},
} : null;
if(testHook) window.__christmasCardTest=testHook;
function localize() {
  const w=words[lang], g=greeting[lang];
  document.documentElement.lang=lang==='zh'?'zh-Hans':'en';
  $('title').textContent=w.title; $('subtitle').textContent=w.subtitle; document.querySelector('.eyebrow').textContent=w.eyebrow;
  $('open').textContent=w.open; $('replay').textContent=w.replay; $('mute').textContent=muted?w.muted:w.sound;
  $('language').textContent=lang==='en'?'中文':'EN'; $('language').setAttribute('aria-label',w.lang);
  $('update').textContent=pendingUpdate?w.install:w.update; $('recipient').textContent=g.recipient; $('sender').textContent=g.sender; $('fallback').textContent=w.fallback;
  const container=$('lines'), hidden=[...container.children].map(e=>e.hasAttribute('data-pending'));
  container.replaceChildren(...g.lines.map((line,i)=>{const p=document.createElement('p');p.textContent=line;if(hidden[i])p.setAttribute('data-pending','');return p;}));
}
$('language').addEventListener('click',()=>{lang=lang==='en'?'zh':'en';localize()});
$('mute').addEventListener('click',()=>{muted=!muted;$('mute').setAttribute('aria-pressed',String(muted));localize()});
function sound() {
  if(muted)return;
  try { audio ||= new AudioContext(); audio.resume(); for(const [i,f] of [523,659,784].entries()) { const o=audio.createOscillator(),g=audio.createGain(),t=audio.currentTime+i*.11; o.type='sine';o.frequency.value=f;g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.08,t+.02);g.gain.exponentialRampToValueAtTime(.0001,t+.35);o.connect(g).connect(audio.destination);o.start(t);o.stop(t+.36) } } catch {}
}
function showMessage(immediate=false) {
  state='message';
  // The HTML face replaces the risen paper at the start of its approach.
  if(letter) letter.visible=false;
  $('message').hidden=false; document.body.classList.add('opened'); localize();
  [...$('lines').children].forEach((p,i)=>{if(!immediate){p.setAttribute('data-pending','');revealTimers.push(setTimeout(()=>p.removeAttribute('data-pending'),650+i*450))}});
}
function fail(){ $('open').hidden=true; $('fallback').hidden=false; showMessage(true) }
function clearParticles(){for(const p of particles){scene.remove(p);p.geometry?.dispose();p.material.dispose()}particles=[]}
function burst() {
  if(reduced||!scene||!envelope)return;
  const star=new THREE.Shape();
  for(let i=0;i<10;i++){const a=Math.PI/2+i*Math.PI/5,r=i%2?.055:.13,x=Math.cos(a)*r,y=Math.sin(a)*r;if(i===0)star.moveTo(x,y);else star.lineTo(x,y)}
  star.closePath();
  const origin=envelope.localToWorld(new THREE.Vector3(0,1.05,.15));
  for(let i=0;i<38;i++){
    const gold=i%3===0;
    const p=gold?new THREE.Mesh(new THREE.ShapeGeometry(star),new THREE.MeshBasicMaterial({color:0xffdf83,side:THREE.DoubleSide,transparent:true,depthTest:false,depthWrite:false,toneMapped:false})):new THREE.Sprite(new THREE.SpriteMaterial({map:snowTexture,color:0xffffff,transparent:true,depthTest:false,depthWrite:false,toneMapped:false}));
    if(!gold)p.scale.setScalar(.10+Math.random()*.12);
    p.position.copy(origin);p.renderOrder=10;p.userData={gold,vx:(Math.random()-.5)*2.1,vy:Math.random()*1.7+.7,vz:(Math.random()-.5)*.5,life:1.5+Math.random()*.5};scene.add(p);particles.push(p);
  }
}
let snowTexture;
function makeSnowTexture(){const n=32,data=new Uint8Array(n*n*4);for(let y=0;y<n;y++)for(let x=0;x<n;x++){const i=(y*n+x)*4,d=Math.hypot((x+.5-n/2)/(n/2),(y+.5-n/2)/(n/2));data[i]=data[i+1]=data[i+2]=255;data[i+3]=Math.round(220*Math.max(0,1-d)**2)}const texture=new THREE.DataTexture(data,n,n,THREE.RGBAFormat);texture.magFilter=THREE.LinearFilter;texture.minFilter=THREE.LinearFilter;texture.needsUpdate=true;return texture}
$('open').addEventListener('click',()=>{
  if(state!=='idle')return; sound(); state='opening'; $('open').hidden=true; burstDone=false;
  action.reset().setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();
  if(reduced){action.paused=true;action.time=action.getClip().duration;mixer.update(0);showMessage(true)}
});
$('replay').addEventListener('click',()=>{
  revealTimers.forEach(clearTimeout);revealTimers=[];$('message').hidden=true;document.body.classList.remove('opened');
  if(!action){showMessage(true);return} clearParticles();letter.visible=true;action.reset().play();action.paused=true;mixer.update(0);state='idle';$('open').hidden=false;start=performance.now()-2000;localize();
});
if ('ongesturestart' in window) document.addEventListener('gesturestart',event=>event.preventDefault(),{passive:false});
localize();
try {
  renderer=new THREE.WebGLRenderer({canvas:$('canvas'),alpha:true,antialias:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NeutralToneMapping;renderer.toneMappingExposure=1;
  scene=new THREE.Scene();
  const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment();const metalEnvironment=pmrem.fromScene(room,.04).texture;room.dispose();pmrem.dispose();
  camera=new THREE.OrthographicCamera(-2,2,2,-2,.1,100);camera.position.z=12;
  scene.add(new THREE.HemisphereLight(0xfff5dd,0x9ba797,.8));const light=new THREE.DirectionalLight(0xffe4b5,2.8);light.position.set(-3,4,6);scene.add(light);snowTexture=makeSnowTexture();
  new GLTFLoader().load(modelUrl,gltf=>{
    envelope=gltf.scene;envelope.traverse(object=>{if(object.isMesh){const materials=Array.isArray(object.material)?object.material:[object.material];for(const material of materials)if(material.metalness>.5){material.envMap=metalEnvironment;material.envMapIntensity=.55;material.needsUpdate=true}}});scene.add(envelope);mixer=new THREE.AnimationMixer(envelope);letter=envelope.getObjectByName('Letter');
    if(!gltf.animations.length||!letter){fail();return}
    envelope.updateMatrixWorld(true);const body=new THREE.Box3();for(const name of ['PocketLeft','PocketRight','PocketBottom']){const part=envelope.getObjectByName(name);if(part)body.union(new THREE.Box3().setFromObject(part))}bodyWidth=body.getSize(new THREE.Vector3()).x;
    action=mixer.clipAction(gltf.animations[0]);mixer.addEventListener('finished',()=>{if(state==='opening')showMessage()});state='idle';$('open').disabled=false;localize();
  },undefined,fail);
  const bounds=new THREE.Box3(),size=new THREE.Vector3();let last=performance.now(),lastWidth=0,lastHeight=0;
  function frame(now) {
    if(testFrozen){last=now;renderer.render(scene,camera);requestAnimationFrame(frame);return}
    const dt=Math.min((now-last)/1000,.05);last=now;const box=$('canvas').getBoundingClientRect();
    if(box.width&&box.height&&(box.width!==lastWidth||box.height!==lastHeight)){renderer.setSize(box.width,box.height,false);lastWidth=box.width;lastHeight=box.height}
    mixer?.update(dt);
    if(envelope&&box.width&&box.height){
      if(state==='opening'&&!burstDone&&action.time>=64/24){burstDone=true;burst()}
      const t=(now-start)/1000;envelope.position.x=reduced?0:-5*Math.max(0,1-t/1.4)**2;envelope.position.y=reduced?0:Math.sin(t*1.3)*.04+Math.sin(Math.min(t/1.4,1)*Math.PI)*.5;envelope.rotation.y=reduced?0:Math.sin(t*.8)*.025;
      envelope.updateMatrixWorld(true);bounds.setFromObject(envelope);bounds.getSize(size);
      const fit=frameEnvelope(box.width,box.height,bodyWidth,{width:size.x,height:size.y+.08,minY:bounds.min.y-envelope.position.y-.04,maxY:bounds.max.y-envelope.position.y+.04});
      // During the message the envelope recedes below the approaching letter.
      const recession=state==='message'?1.35:1;
      camera.left=-fit.halfWidth*recession;camera.right=fit.halfWidth*recession;camera.top=fit.halfHeight*recession;camera.bottom=-fit.halfHeight*recession;camera.position.y=fit.centerY+(state==='message'?1.1:0);camera.updateProjectionMatrix();
    }
    for(const p of particles){p.position.x+=p.userData.vx*dt;p.position.y+=p.userData.vy*dt;p.position.z+=p.userData.vz*dt;p.userData.vy-=1.2*dt;p.userData.life-=dt;p.material.opacity=Math.min(1,Math.max(0,p.userData.life)*1.4);if(p.userData.life<=0){scene.remove(p);p.geometry?.dispose();p.material.dispose()}}
    particles=particles.filter(p=>p.userData.life>0);renderer.render(scene,camera);
    if(testHook&&testCaptureTime!==null&&state==='opening'&&action.time>=testCaptureTime){
      testFrozen=true;testCaptureTime=null;
      testHook.snapshot={time:action.time,age:action.time-64/24,particles:particles.map(p=>{const v=p.position.clone().project(camera);return {x:(v.x+1)*box.width/2,y:(1-v.y)*box.height/2,gold:p.userData.gold}})};
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
} catch { fail() }
if('serviceWorker' in navigator){navigator.serviceWorker.register('./sw.js',{scope:'./'}).then(r=>{registration=r;function ready(){pendingUpdate=!!r.waiting||!!(r.active&&r.installing);localize()}ready();r.addEventListener('updatefound',()=>r.installing?.addEventListener('statechange',ready));navigator.serviceWorker.addEventListener('controllerchange',()=>{if(pendingUpdate)location.reload()})}).catch(()=>{});}
$('update').addEventListener('click',async()=>{if(!registration){$('update-status').textContent=words[lang].error;return}if(registration.waiting||registration.installing){pendingUpdate=true;(registration.waiting||registration.installing).postMessage({type:'ACTIVATE'});return}$('update-status').textContent=words[lang].checking;try{await registration.update();pendingUpdate=!!registration.waiting||!!registration.installing;localize();$('update-status').textContent=pendingUpdate?words[lang].ready:words[lang].current}catch{$('update-status').textContent=words[lang].error}});
fetch('./version.json').then(r=>r.ok?r.json():Promise.reject()).then(info=>{$('version').textContent='v'+info.version}).catch(()=>{});
