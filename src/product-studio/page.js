import { localize, mountMarkup, t } from '../i18n/index.js';
import { fitProductDistance, setProductView } from './camera.js';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { createPoseController } from './pose.js';
import { createLatestLoader, disposeProduct } from './load.js';
import { createLabelController, LABEL_PRESETS } from './labels.js';
import './style.css';

const button = (label, attrs = {}, message = true) => {
  const el = document.createElement('button'); el.type = 'button';
  if (message) localize(el, label);
  else el.textContent = label;
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  return el;
};
const labels = item => item.root === 'ASSET_DemoBeverageCan'
  ? { open:'product.liftTab', close:'product.resetTab', closed:'product.tabClosed', opened:'product.tabOpened', note:'product.tabNote' }
  : { open:'product.openLid', close:'product.closeLid', closed:'product.lidClosed', opened:'product.lidOpened', note:'product.lidNote' };

export async function mountProductStudio(root, asset, signal, alternatives = []) {
  if (!asset) throw new Error('Demo packaging asset is unavailable');
  if (signal.aborted) throw new DOMException('Navigation cancelled', 'AbortError');
  const products = [...new Map([asset,...alternatives].filter(Boolean).map(item => [item.id,item])).values()];
  root.replaceChildren();
  const section = document.createElement('section'); section.className='product-studio';
  mountMarkup(section, `<header class="ps-heading"><div><p class="ps-kicker" data-i18n="product.kicker"></p><h1><span data-i18n="demo.product-studio.title"></span><span data-i18n="common.period"></span></h1></div><p data-i18n="product.intro"></p></header><div class="ps-layout"><div class="ps-stage" aria-busy="true"><div class="ps-loading" role="status"></div></div><aside class="ps-panel"><span class="ps-demo" data-i18n="product.badge"></span><h2></h2><p class="ps-description"></p><div class="ps-choice" role="group" data-i18n-aria-label="product.choose"></div><fieldset class="ps-labels" disabled><legend data-i18n="product.originalLabel"></legend><div class="ps-label-grid"></div><p class="ps-label-help" data-i18n="product.labelHelp"></p></fieldset><div class="ps-actions"></div><fieldset class="ps-views" disabled><legend data-i18n="product.inspect"></legend><div class="ps-view-grid"></div></fieldset><p class="ps-status" aria-live="polite" data-i18n="common.preparing"></p><p class="ps-note"></p></aside></div><p class="ps-hint" data-i18n="product.hint"></p>`);
  root.append(section);
  const $=s=>section.querySelector(s), stage=$('.ps-stage'), loading=$('.ps-loading'), status=$('.ps-status'), choice=$('.ps-choice'), views=$('.ps-views'), labelChoices=$('.ps-labels');
  const openButton=button('product.openLid',{'data-action':'open','aria-pressed':'false'}), explodeButton=button('product.exploded',{'data-action':'explode','aria-pressed':'false'}), resetButton=button('product.reset',{'data-action':'reset'});
  $('.ps-actions').append(openButton,explodeButton,resetButton);
  for (const preset of LABEL_PRESETS) labelChoices.querySelector('.ps-label-grid').append(button(`product.label.${preset.id}`, {'data-label': preset.id, 'aria-pressed': 'false'}));
  for(const name of ['front','back','left','right','top','bottom']) $('.ps-view-grid').append(button(`direction.${name}`,{'data-view':name}));
  for(const item of products) choice.append(button(item.name,{'data-product':item.id,'aria-pressed':String(item.id===asset.id)}, false));
  const local=new AbortController(), motion=matchMedia('(prefers-reduced-motion: reduce)');
  let disposed=false, renderer, controls, observer, environment, model, poses, labelsController, loader;
  let frame=0, dirty=true, ready=false, animation=null, mode='closed', amount=0, targetMode='closed', targetAmount=0, lastTime=0, current=asset, modelRadius=0;
  const center=new THREE.Vector3(), camera=new THREE.PerspectiveCamera(35,1,.001,10), scene=new THREE.Scene();
  const setBusy=busy=>{stage.setAttribute('aria-busy',String(busy));for(const el of [openButton,explodeButton,resetButton]) el.disabled=busy||!ready||disposed;views.disabled=busy||!ready||disposed;labelChoices.disabled=busy||!ready||disposed||current.root!=='ASSET_DemoBeverageCan';choice.querySelectorAll('button').forEach(el=>el.disabled=disposed);if(controls)controls.enabled=ready&&!busy&&!disposed;};
  const invalidate=()=>{dirty=true;if(!disposed&&!document.hidden&&!frame)frame=requestAnimationFrame(render);};
  const report=()=>{
    if(disposed)return;
    const text=labels(current),opening=targetMode==='open'&&targetAmount===1,exploding=targetMode==='exploded'&&targetAmount===1;
    openButton.setAttribute('aria-pressed',String(opening));localize(openButton, opening?text.close:text.open);
    explodeButton.setAttribute('aria-pressed',String(exploding));localize(explodeButton, exploding?'product.assemble':'product.exploded');
    localize(status, animation?'product.moving':amount===0||mode==='closed'?text.closed:mode==='open'?text.opened:'product.separated');
    stage.dataset.pose=animation?'moving':amount===0?'closed':mode;
  };
  const fitDistance=()=>fitProductDistance(modelRadius,camera.aspect,camera.fov);
  const view=name=>{if(!ready||disposed)return;setProductView(camera,controls,center,fitDistance(),name);invalidate();};
  const setPose=(next,end=1,immediate=false)=>{
    if(!ready||disposed)return;targetMode=next;targetAmount=end;
    if(next!==mode){poses.apply('closed');amount=0;mode=next;}
    if(immediate||motion.matches||next==='closed'){amount=next==='closed'?0:end;poses.apply(next,amount);animation=null;}
    else animation={start:amount,end,elapsed:0};
    lastTime=0;report();invalidate();
  };
  const syncLabelState=()=>{stage.dataset.labelId=labelsController?.current??'original';stage.dataset.labelTexture=labelsController?.texture?'runtime-canvas':'authored';};
  const reset=()=>{labelsController?.reset();labelChoices.querySelectorAll('[data-label]').forEach(b=>b.setAttribute('aria-pressed','false'));syncLabelState();setPose('closed',0,true);view('front');};
  function render(now){
    frame=0;if(disposed||document.hidden)return;
    if(animation){animation.elapsed+=lastTime?Math.min((now-lastTime)/1000,.05):0;const p=Math.min(animation.elapsed/.45,1);amount=animation.start+(animation.end-animation.start)*p;poses.apply(mode,amount);dirty=true;if(p===1){animation=null;report();}}
    lastTime=now;if(dirty){renderer.render(scene,camera);dirty=false;}if(animation)frame=requestAnimationFrame(render);
  }
  function disposeModel(){labelsController?.dispose();labelsController=null;syncLabelState();labelChoices.querySelectorAll('[data-label]').forEach(b=>b.setAttribute('aria-pressed','false'));poses?.dispose();poses=null;if(model){scene.remove(model);disposeProduct(model);model=null;}ready=false;animation=null;lastTime=0;setBusy(true);}
  function showError(item){
    if(disposed)return;stage.dataset.pose='error';setBusy(true);stage.setAttribute('aria-busy','false');
    loading.hidden=false;localize(loading);loading.replaceChildren(localize(document.createElement('span'), 'product.loadError', { name: item.name }), ' ');
    const retry=button('common.retryExperience',{'class':'outline-button','data-retry':'true'});loading.append(retry);
    retry.addEventListener('click',()=>void loader.select(current),{signal:local.signal});localize(status, 'product.retryStudy');
  }
  function dispose(){
    if(disposed)return;disposed=true;loader?.dispose();local.abort();signal.removeEventListener('abort',dispose);
    cancelAnimationFrame(frame);frame=0;observer?.disconnect();controls?.dispose();disposeModel();environment?.dispose();renderer?.dispose();renderer?.domElement.remove();
  }
  signal.addEventListener('abort',dispose,{once:true});
  loader=createLatestLoader({
    start(item){
      current=item;disposeModel();mode=targetMode='closed';amount=targetAmount=0;
      stage.dataset.pose='loading';delete stage.dataset.modelId;delete stage.dataset.modelRoot;
      loading.hidden=false;localize(loading, 'product.loading', { name: item.name.toLowerCase() });localize(status, 'product.selectedLoading');
      const text=labels(item);localize(openButton, text.open);openButton.setAttribute('aria-pressed','false');localize(explodeButton, 'product.exploded');explodeButton.setAttribute('aria-pressed','false');
      $('h2').textContent=item.name;$('.ps-description').textContent=item.description;localize($('.ps-note'), 'product.note', () => ({ note: t(text.note) }));
      choice.querySelectorAll('[data-product]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.product===item.id)));invalidate();
    },
    async prepare(item,requestSignal){
      const response=await fetch(item.file,{signal:requestSignal});if(!response.ok)throw new Error(`Packaging request failed: ${response.status}`);
      const bytes=await response.arrayBuffer();if(requestSignal.aborted)throw new DOMException('Selection changed','AbortError');
      return new GLTFLoader().parseAsync(bytes,THREE.LoaderUtils.extractUrlBase(new URL(item.file,document.baseURI).href));
    },
    commit(gltf,item){
      let nextPoses;
      try{
        nextPoses=createPoseController(gltf,item);const bounds=new THREE.Box3();
        for(const state of ['closed','open','exploded']){nextPoses.apply(state);bounds.union(new THREE.Box3().setFromObject(gltf.scene));}nextPoses.apply('closed');
        if(bounds.isEmpty())throw new Error('Packaging model has no visible geometry');
        const nextCenter=new THREE.Vector3();bounds.getCenter(nextCenter);const radius=bounds.getSize(new THREE.Vector3()).length()/2;
        if(!Number.isFinite(radius)||radius<=0)throw new Error('Invalid packaging size');
        model=gltf.scene;poses=nextPoses;scene.add(model);labelsController=item.root==='ASSET_DemoBeverageCan'?createLabelController(model):null;center.copy(nextCenter);modelRadius=radius;
        camera.aspect=Math.max(stage.clientWidth,1)/Math.max(stage.clientHeight,1);camera.near=radius/80;camera.far=radius*80;camera.updateProjectionMatrix();
        controls.minDistance=radius*1.2;controls.maxDistance=Math.max(radius*12,fitDistance()*3);
        ready=true;stage.dataset.modelId=item.id;stage.dataset.modelRoot=model.getObjectByName(item.root).name;
        loading.hidden=true;localize(loading);setBusy(false);reset();
      }catch(error){nextPoses?.dispose();throw error;}
    },
    release(gltf){disposeProduct(gltf?.scene);},
    fail(){disposeModel();showError(current);},
  });
  try{
    renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setClearColor(0xe6e8df);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
    const canvas=renderer.domElement;canvas.tabIndex=0;canvas.setAttribute('role','img');localize(canvas, 'product.canvas', undefined, 'aria-label');stage.append(canvas);
    controls=new OrbitControls(camera,canvas);controls.enableDamping=false;controls.enablePan=false;controls.enabled=false;controls.addEventListener('change',invalidate);
    scene.add(new THREE.HemisphereLight(0xffffff,0x566356,2.2));const light=new THREE.DirectionalLight(0xffffff,2.4);light.position.set(.3,.5,.4);scene.add(light);
    const room=new RoomEnvironment(),pmrem=new THREE.PMREMGenerator(renderer);try{environment=pmrem.fromScene(room,.04);scene.environment=environment.texture;scene.environmentIntensity=.75;}finally{room.dispose();pmrem.dispose();}
    observer=new ResizeObserver(()=>{const w=stage.clientWidth,h=stage.clientHeight;if(w&&h){renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();invalidate();}});observer.observe(stage);
    canvas.addEventListener('webglcontextlost',event=>{
      event.preventDefault();dispose();stage.dataset.pose='error';delete stage.dataset.modelId;delete stage.dataset.modelRoot;stage.setAttribute('aria-busy','false');
      loading.hidden=false;localize(loading);loading.append(localize(document.createElement('span'), 'product.interrupted'), ' ');
      const retry=button('common.retryExperience',{'class':'outline-button','data-retry':'true'});loading.append(retry);retry.addEventListener('click',()=>location.reload());localize(status, 'product.recovery');
    },{signal:local.signal});
    document.addEventListener('visibilitychange',()=>{if(document.hidden){cancelAnimationFrame(frame);frame=0;lastTime=0;}else invalidate();},{signal:local.signal});
    motion.addEventListener('change',()=>{if(motion.matches&&animation)setPose(targetMode,targetAmount,true);},{signal:local.signal});
    openButton.addEventListener('click',()=>setPose('open',targetMode==='open'&&targetAmount===1?0:1),{signal:local.signal});
    explodeButton.addEventListener('click',()=>setPose('exploded',targetMode==='exploded'&&targetAmount===1?0:1),{signal:local.signal});resetButton.addEventListener('click',reset,{signal:local.signal});
    $('.ps-view-grid').querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>view(b.dataset.view),{signal:local.signal}));
    labelChoices.querySelectorAll('[data-label]').forEach(b=>b.addEventListener('click',()=>{if(!labelsController||!ready)return;labelsController.apply(b.dataset.label);labelChoices.querySelectorAll('[data-label]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));syncLabelState();invalidate();},{signal:local.signal}));
    choice.querySelectorAll('[data-product]').forEach(b=>b.addEventListener('click',()=>{const next=products.find(item=>item.id===b.dataset.product);if(next&&next.id!==current.id)void loader.select(next);},{signal:local.signal}));
    canvas.addEventListener('keydown',event=>{
      if(!ready||disposed)return;const key=event.key;if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','Home'].includes(key))return;event.preventDefault();if(key==='Home'){reset();return;}
      const spherical=new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));if(key==='ArrowLeft')spherical.theta-=Math.PI/18;if(key==='ArrowRight')spherical.theta+=Math.PI/18;if(key==='ArrowUp')spherical.phi-=Math.PI/18;if(key==='ArrowDown')spherical.phi+=Math.PI/18;if(key==='+'||key==='=')spherical.radius*=.85;if(key==='-')spherical.radius/=.85;
      spherical.phi=THREE.MathUtils.clamp(spherical.phi,.01,Math.PI-.01);spherical.radius=THREE.MathUtils.clamp(spherical.radius,controls.minDistance,controls.maxDistance);camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));controls.update();invalidate();
    },{signal:local.signal});void loader.select(asset);return{dispose};
  }catch(error){dispose();throw error;}
}
