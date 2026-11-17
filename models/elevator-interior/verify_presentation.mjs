// Independently raycast the delivered geometry from the gallery's default fit.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {Box3, MathUtils, PerspectiveCamera, Raycaster, Vector3} from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const read = name => JSON.parse(fs.readFileSync(new URL(name, import.meta.url)));
const metadata = read('metadata/elevator-interior.json');
const sources = read('reports/sources.json');
const browser = read('reports/browser.json');
const bytes = fs.readFileSync(new URL('exports/optimized.glb', import.meta.url));
const sha256 = createHash('sha256').update(bytes).digest('hex');
assert.equal(browser.loaded[0].sha256, sha256);
assert.equal(metadata.statistics.sha256, sha256);
assert.equal(metadata.statistics.glb_bytes, bytes.length);
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset+bytes.byteLength), '');
const model = gltf.scene;
model.rotation.y = metadata.display.previewRotationY;
model.updateMatrixWorld(true);
const bounds = new Box3().setFromObject(model, true);
const center = bounds.getCenter(new Vector3());
const radius = bounds.getSize(new Vector3()).length()/2;
const [width, height] = browser.canvas_size;
const camera = new PerspectiveCamera(35, width/height, radius/50, radius*50);
const vertical = MathUtils.degToRad(camera.fov/2);
const horizontal = Math.atan(Math.tan(vertical)*camera.aspect);
const distance = radius/Math.sin(Math.min(vertical, horizontal))*1.08;
camera.position.copy(center).addScaledVector(new Vector3(...metadata.display.previewCameraDirection).normalize(), distance);
camera.lookAt(center);
camera.updateMatrixWorld(true);
const ray = new Raycaster();
const visible = (point, name) => {
  point.applyMatrix4(model.matrixWorld);
  const projected = point.clone().project(camera);
  ray.set(camera.position, point.clone().sub(camera.position).normalize());
  const hit = ray.intersectObject(model, true)[0];
  return Math.abs(projected.x)<1 && Math.abs(projected.y)<1 &&
    hit?.object.name===name && hit.point.distanceTo(point)<1e-4;
};
const buttons = Object.entries(sources.parts).filter(([name]) => name.startsWith('BUTTON_Unlabelled_'))
  .map(([name, b]) => ({name, visible:visible(new Vector3(b.min[0], (b.min[2]+b.max[2])/2, -(b.min[1]+b.max[1])/2), 'CONTROL_UnlabelledButtons')}));
assert.equal(buttons.length, 8);
assert.ok(buttons.every(b => b.visible), 'all eight button centres are unobstructed');
const mirror = sources.parts.MIRROR_RearPanel;
let visibleMirrorSamples = 0;
for (const u of [.2,.5,.8]) for (const v of [.2,.5,.8]) {
  if (visible(new Vector3(MathUtils.lerp(mirror.min[0],mirror.max[0],u),
    MathUtils.lerp(mirror.min[2],mirror.max[2],v), -mirror.min[1]), 'MIRROR_Rear')) visibleMirrorSamples++;
}
assert.ok(visibleMirrorSamples>=3, 'rear mirror remains visible with the controls');
const projected = [];
model.traverse(o => {
  if (!o.isMesh) return;
  const position = o.geometry.attributes.position;
  for (let i=0;i<position.count;i++) projected.push(new Vector3().fromBufferAttribute(position,i).applyMatrix4(o.matrixWorld).project(camera));
});
const xs = projected.map(p => p.x), ys = projected.map(p => p.y);
assert.ok(Math.min(...xs)>-1 && Math.max(...xs)<1 && Math.min(...ys)>-1 && Math.max(...ys)<1, 'entire car fits');
const report = {result:'PASS',glb_sha256:sha256,canvas_size:[width,height],buttons,
  visible_mirror_samples:visibleMirrorSamples,mirror_samples:9,
  projected_model_pixels:[(Math.max(...xs)-Math.min(...xs))*width/2,(Math.max(...ys)-Math.min(...ys))*height/2],
  display:metadata.display,
  scope:'Independent geometry sightlines using the current gallery fit and measured Chromium canvas. Appearance requires the separate screenshot review.'};
fs.writeFileSync(new URL('reports/presentation.json', import.meta.url), JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
