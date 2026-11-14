import { Vector3 } from "three";
export const VIEW_DIRECTIONS = Object.freeze({ front:[0,.12,1], back:[0,.12,-1], left:[-1,.12,0], right:[1,.12,0], top:[0,1,.001], bottom:[0,-1,.001] });
export function fitProductDistance(radius, aspect, fov = 35) {
 const vertical=fov*Math.PI/180, horizontal=2*Math.atan(Math.tan(vertical/2)*aspect);
 return radius/Math.sin(Math.min(vertical,horizontal)/2)*1.18;
}

export function setProductView(camera, controls, center, distance, name) {
 camera.position.copy(center).add(new Vector3(...VIEW_DIRECTIONS[name]).normalize().multiplyScalar(distance));
 camera.up.set(0,1,0); camera.zoom=1; camera.updateProjectionMatrix();
 controls.target.copy(center);controls.update();
}
