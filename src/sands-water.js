import { Reflector } from "three/addons/objects/Reflector.js";

export function createBayReflection(model) {
  const surface = model.getObjectByName("Bay_Surface");
  const water = new Reflector(surface.geometry, {
    textureWidth: 768, textureHeight: 384, multisample: 0, clipBias: 0.001,
    color: 0x327e80,
    shader: {
      ...Reflector.ReflectorShader,
      uniforms: { ...Reflector.ReflectorShader.uniforms, phase: { value: 0 } },
      vertexShader: Reflector.ReflectorShader.vertexShader
        .replace("void main()", "varying vec2 surfaceUv; void main()")
        .replace("vUv = textureMatrix", "surfaceUv = position.xy; vUv = textureMatrix"),
      fragmentShader: `
        uniform sampler2D tDiffuse;
        uniform vec3 color;
        uniform float phase;
        varying vec4 vUv;
        varying vec2 surfaceUv;
        #include <logdepthbuf_pars_fragment>
        void main() {
          #include <logdepthbuf_fragment>
          vec2 p = surfaceUv;
          float swell = sin(21.0*p.y + 2.7*p.x + sin(p.x*2.2) + phase);
          float ripple = sin(36.0*p.y - 3.9*p.x - 2.0*phase);
          vec2 uv = vUv.xy / vUv.w + vec2(ripple*0.0017, swell*0.005 + ripple*0.002);
          vec3 reflection = texture2D(tDiffuse, clamp(uv, 0.0, 1.0)).rgb;
          float crest = smoothstep(0.78, 1.45, swell + ripple*0.48);
          gl_FragColor = vec4(mix(color, reflection, 0.46) + vec3(0.055,0.075,0.07)*crest, 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    },
  });
  water.position.copy(surface.position);
  water.quaternion.copy(surface.quaternion);
  surface.visible = false;
  surface.parent.add(water);
  return {
    sample(fraction) { water.material.uniforms.phase.value = fraction * Math.PI * 2; },
    dispose() { water.removeFromParent(); water.dispose(); surface.visible = true; },
  };
}
