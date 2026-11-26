import * as THREE from 'three';

export const particleLimit = 192;
const entrancePoints = 44;
const pointDiameterLimit = 32;

function makeGlowMaterial() {
  const side = 32;
  const pixels = new Uint8Array(side * side * 3);
  const { smoothstep } = THREE.MathUtils;
  for (let y = 0; y < side; y++) for (let x = 0; x < side; x++) {
    const px = Math.abs((x + .5) / side * 2 - 1), py = Math.abs((y + .5) / side * 2 - 1);
    const radius = Math.hypot(px, py);
    const core = 1 - smoothstep(radius, .14, .41);
    const rays = (1 - smoothstep(Math.min(px, py), 0, .12)) * (1 - smoothstep(radius, .12, .85));
    const halo = Math.max(0, 1 - radius) ** 2.4;
    const i = y * side * 3 + x;
    pixels[i] = Math.min(1, .90 * core + .65 * rays + .52 * halo) * 255;
    pixels[i + side] = Math.min(1, .90 * core + .52 * halo) * 255;
    pixels[i + side * 2] = Math.max(0, 1 - radius) ** 2 * 220;
  }
  const atlas = new THREE.DataTexture(pixels, side * 3, side, THREE.RedFormat);
  atlas.minFilter = atlas.magFilter = THREE.LinearFilter;
  atlas.needsUpdate = true;
  return new THREE.ShaderMaterial({
    uniforms: { pixels: { value: 1 }, atlas: { value: atlas } },
    vertexShader: `
      uniform float pixels;
      attribute float aSize, aAlpha, aStyle;
      varying float opacity, tile;
      varying vec3 tint;
      void main() {
        vec4 eye = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * eye;
        gl_PointSize = clamp(aSize * pixels * projectionMatrix[1][1] / -eye.z, 2.0, ${pointDiameterLimit}.0);
        opacity = aAlpha;
        tile = min(aStyle, 2.0);
        tint = aStyle < .5 ? vec3(1.0, .82, .55) : aStyle < 1.5 ? vec3(.94, .97, 1.0) :
          aStyle < 2.5 ? vec3(1.0, .84, .53) : aStyle < 3.5 ? vec3(1.0, .972, .913) : vec3(.91, .867, 1.0);
      }`,
    fragmentShader: `
      uniform sampler2D atlas;
      varying float opacity, tile;
      varying vec3 tint;
      void main() {
        vec2 uv = vec2((tile * ${side}.0 + .5 + gl_PointCoord.x * ${side - 1}.0) / ${side * 3}.0, gl_PointCoord.y);
        gl_FragColor = vec4(tint, opacity * texture2D(atlas, uv).r);
      }`,
    blending: THREE.AdditiveBlending, transparent: true, depthWrite: false, toneMapped: false,
  });
}

function createGlowBatch(scene, material, capacity, name) {
  const geometry = new THREE.BufferGeometry();
  const position = new THREE.Float32BufferAttribute(new Float32Array(capacity * 3), 3);
  const size = new THREE.Float32BufferAttribute(new Float32Array(capacity), 1);
  const alpha = new THREE.Float32BufferAttribute(new Float32Array(capacity), 1);
  const style = new THREE.Float32BufferAttribute(new Float32Array(capacity), 1);
  const attributes = { position, aSize: size, aAlpha: alpha, aStyle: style };
  const streams = Object.values(attributes);
  for (const [key, attribute] of Object.entries(attributes)) geometry.setAttribute(key, attribute.setUsage(THREE.DynamicDrawUsage));
  const points = new THREE.Points(geometry, material);
  points.name = name;
  points.frustumCulled = false;
  points.visible = false;
  points.renderOrder = 9;
  scene.add(points);
  return {
    attributes, capacity,
    put(i, point, diameter, opacity, shape) {
      position.setXYZ(i, point.x, point.y, point.z);
      size.setX(i, diameter);
      alpha.setX(i, opacity);
      style.setX(i, shape);
    },
    draw(count) {
      geometry.setDrawRange(0, count);
      points.visible = count > 0;
      if (count) for (const attribute of streams) attribute.needsUpdate = true;
    },
  };
}

export function createStardust(scene) {
  const material = makeGlowMaterial();
  const batch = createGlowBatch(scene, material, particleLimit, 'Stardust');
  const { position, aSize: size, aAlpha: alpha, aStyle: style } = batch.attributes;
  const pool = Array.from({ length: particleLimit }, () => ({ origin: new THREE.Vector3(), velocity: new THREE.Vector3(), life: 0 }));
  let seed = 71, next = 0, active = 0, drawn = 0, pixelRatio = 1;
  const random = () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 2 ** 32;
  };
  function add(origin, velocity, life, diameter, isSnow, delay, gravity) {
    const particle = pool[next];
    next = (next + 1) % pool.length;
    if (!particle.life) active++;
    particle.origin.copy(origin);
    particle.velocity.copy(velocity);
    particle.age = -delay;
    particle.life = life;
    particle.size = diameter;
    particle.snow = isSnow;
    particle.gravity = gravity;
    particle.phase = random() * Math.PI * 2;
  }
  const velocity = new THREE.Vector3(), point = new THREE.Vector3(), eye = new THREE.Vector3();
  return {
    createEntranceBatch() { return createGlowBatch(scene, material, entrancePoints, 'EntranceStardust'); },
    setPixels(height, cssHeight = height) {
      material.uniforms.pixels.value = height / 2;
      pixelRatio = height / cssHeight;
    },
    mouth(origin) {
      const sizes = [.046, .085, .16];
      for (let i = 0; i < 90; i++) {
        const diameter = sizes[i % sizes.length];
        velocity.set((random() - .5) * 1.65, .72 + random() * 1.58, (random() - .32) * .57);
        const life = 1.45 + random() * .85;
        const delay = random() * .18;
        add(origin, velocity, life, diameter, false, delay, .53);
        if (i % 5 === 2) add(origin, velocity, life * .83, .053, false, delay + .095, .53);
      }
      for (let i = 0; i < 28; i++) {
        velocity.set((random() - .5) * 1.15, .30 + random() * .72, (random() - .25) * .6);
        add(origin, velocity, 2.25 + random() * .42, .092 + random() * .06, true, random() * .21, .19);
      }
    },
    scatter(origin) {
      for (let i = 0; i < 5; i++) {
        velocity.set((random() - .5) * .9, .18 + random() * .55, .08 + random() * .34);
        add(origin, velocity, .56 + random() * .46, i % 2 === 0 ? .067 : .105, false, random() * .10, .13);
      }
    },
    update(dt) {
      if (!active) return;
      drawn = 0;
      for (const p of pool) {
        if (!p.life) continue;
        p.age += dt;
        if (p.age < 0) continue;
        if (p.age >= p.life) { p.life = 0; active--; continue; }
        const t = p.age;
        point.copy(p.origin).addScaledVector(p.velocity, t);
        point.y -= p.gravity * t * t;
        point.x += (p.snow ? .09 : .045) * Math.sin(t * 3 + p.phase) * Math.min(t, 1);
        const fade = Math.min(1, (p.life - t) * 2.5);
        const twinkle = .78 + .22 * Math.cos(t * (p.snow ? 3 : 11) + p.phase);
        batch.put(drawn++, point, p.size, fade * twinkle, Number(p.snow));
      }
      batch.draw(drawn);
    },
    measure(camera, viewport) {
      const result = [];
      for (let i = 0; i < drawn; i++) {
        if (alpha.getX(i) < .15) continue;
        point.fromBufferAttribute(position, i);
        const depth = -eye.copy(point).applyMatrix4(camera.matrixWorldInverse).z;
        const diameter = size.getX(i) * viewport.height * pixelRatio * camera.projectionMatrix.elements[5] / (2 * depth);
        const radius = THREE.MathUtils.clamp(diameter, 2, pointDiameterLimit) / (2 * pixelRatio);
        point.project(camera);
        result.push({ x: (point.x + 1) * viewport.width / 2, y: (1 - point.y) * viewport.height / 2,
          radius, gold: style.getX(i) === 0, size: size.getX(i) });
      }
      return result;
    },
    clear() {
      for (const particle of pool) particle.life = 0;
      batch.draw(0);
      drawn = active = next = 0;
      seed = 71;
    },
  };
}

const beams = [[-.8, 1.57, .30], [-.37, 1.89, .31], [.20, 1.76, .27], [.73, 1.48, .32]];
const glowBounds = { left: -1.18, right: 1.18, bottom: -.45, top: 1.90 };
const halo = { xRadius: 1.15, yRadius: .715, y: .17, cutoff: .86 };

function makeMouthGlow() {
  const width = 72, height = 80;
  const pixels = new Uint8Array(width * height * 4);
  const { left, right, bottom, top } = glowBounds;
  const { lerp, smoothstep } = THREE.MathUtils;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const wx = lerp(left, right, (x + .5) / width), wy = lerp(bottom, top, (y + .5) / height);
    let rays = 0;
    for (const [lean, rise, spread] of beams) {
      if (wy <= 0 || wy >= rise) continue;
      const t = wy / rise;
      const edge = Math.abs(wx - lerp(lean * .13, lean, t)) / lerp(.035, spread, t);
      rays += Math.max(0, 1 - edge) ** 1.65 * (1 - t) ** 1.45 * .38;
    }
    const radius = Math.hypot(wx / halo.xRadius, (wy - halo.y) / halo.yRadius);
    const haze = Math.max(0, 1 - radius) ** 2 * (1 - smoothstep(radius, .67, halo.cutoff)) * .76;
    const light = rays + haze;
    if (!light) continue;
    pixels.set([255, (215 * rays + 196 * haze) / light, (151 * rays + 103 * haze) / light,
      Math.min(1, light) * 255], (y * width + x) * 4);
  }
  const texture = new THREE.DataTexture(pixels, width, height);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;

  // One non-overlapping strip follows the glow footprint instead of drawing
  // four translucent cones plus a large rectangular halo over the same pixels.
  const positions = [], uvs = [], indices = [];
  for (let row = 0; row <= 28; row++) {
    const t = row / 28, y = lerp(bottom, top, t);
    const half = halo.xRadius * Math.sqrt(Math.max(0, halo.cutoff ** 2 - ((y - halo.y) / halo.yRadius) ** 2));
    let min = -half, max = half;
    for (const [lean, rise, spread] of beams) {
      if (y < 0 || y > rise) continue;
      const center = lerp(lean * .13, lean, y / rise);
      const radius = lerp(.035, spread, y / rise);
      min = Math.min(min, center - radius);
      max = Math.max(max, center + radius);
    }
    for (const x of [Math.max(left, min - .035), Math.min(right, max + .035)]) {
      positions.push(x, y, 0);
      uvs.push((x - left) / (right - left), t);
    }
    if (row) {
      const a = row * 2 - 2;
      indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  return new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ map: texture, blending: THREE.AdditiveBlending,
    depthWrite: false, transparent: true, toneMapped: false }));
}

export function createMouthLight(scene) {
  const glow = makeMouthGlow();
  glow.name = 'MouthGlow';
  glow.renderOrder = 7;
  glow.visible = false;
  scene.add(glow);
  return (envelope, strength) => {
    glow.visible = strength > 0;
    if (!glow.visible) return;
    glow.position.set(0, 1.05, .25);
    envelope.localToWorld(glow.position);
    glow.material.opacity = strength;
  };
}
