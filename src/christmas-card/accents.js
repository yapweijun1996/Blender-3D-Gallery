import * as THREE from 'three';
import { entranceDuration, poseEntrance } from './motion.js';
import { wrapAddress } from './fit-copy.js';

export const trailLifetime = 1.48;

export function createAddress(envelope) {
  const canvas = document.createElement('canvas');
  canvas.width = 960;
  canvas.height = 620;
  const ctx = canvas.getContext('2d');
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const address = new THREE.Mesh(new THREE.PlaneGeometry(3.17, 2.06), new THREE.MeshBasicMaterial({
    map: texture, transparent: true, depthWrite: false, toneMapped: false,
  }));
  address.name = 'Address';
  address.position.z = -.086;
  address.rotation.y = Math.PI;
  envelope.add(address);

  let lastRecipient;
  return recipient => {
    if(recipient === lastRecipient) return;
    lastRecipient = recipient;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    texture.needsUpdate = true;
    if (!recipient) return;
    ctx.fillStyle = '#f6eedc';
    ctx.font = '600 43px system-ui';
    ctx.fillText('To:', 221, 294);
    let size = 62, lines;
    do {
      ctx.font = `${size}px Georgia, serif`;
      lines = wrapAddress(recipient, text => ctx.measureText(text).width, 570);
      if (lines.length <= 3 || size === 24) break;
      size -= 2;
    } while (true);
    lines.forEach((line, i)=>ctx.fillText(line, 221, 367 + i * size * 1.1, 570));
    ctx.fillStyle = '#d2a367';
    ctx.fillRect(221, 394 + (lines.length - 1) * size * 1.1, 425, 2);

    // The perforated stamp and its fir motif share the address texture.
    ctx.fillStyle = '#f6eedc';
    ctx.fillRect(735, 69, 144, 158);
    for (let i = 0; i <= 12; i++) {
      ctx.clearRect(733 + i * 12, 66, 5, 7);
      ctx.clearRect(733 + i * 12, 223, 5, 7);
    }
    for (let i = 0; i <= 13; i++) {
      ctx.clearRect(732, 67 + i * 12, 7, 5);
      ctx.clearRect(875, 67 + i * 12, 7, 5);
    }
    ctx.fillStyle = '#214838';
    ctx.fillRect(747, 81, 120, 134);
    ctx.fillStyle = '#ffe29a';
    ctx.beginPath();
    ctx.moveTo(807, 105);
    ctx.lineTo(829, 141);
    ctx.lineTo(817, 141);
    ctx.lineTo(843, 181);
    ctx.lineTo(771, 181);
    ctx.lineTo(797, 141);
    ctx.lineTo(785, 141);
    ctx.closePath();
    ctx.fill();
    ctx.fillRect(803, 181, 8, 13);
  };
}

export function createEntranceTrail(batch) {
  const samples = Array.from({ length: batch.capacity }, (_, i) => ({
    age: .055 + i * .032,
    x: Math.cos(i * 2.4), y: Math.sin(i * 2.4), z: .23 + Math.sin(i * 1.73) * .18,
    phase: i * 3.2, size: .20 + (i % 4) * .043, kind: i % 5 === 0 ? 3 : i % 3 === 0 ? 4 : 2,
  }));
  const pose = new THREE.Object3D();
  return (time, flight) => {
    let count = 0;
    for (const { age, x, y, z, phase, size, kind } of samples) {
      const birth = time - age;
      if (birth <= 0 || birth >= entranceDuration - .1) continue;
      poseEntrance(pose, birth, flight);
      pose.position.x += x * (.16 + age * .17);
      pose.position.y += y * (.10 + age * .22) - age * .075;
      pose.position.z += z;
      const twinkle = .78 + .22 * Math.sin(phase + time * 9);
      const opacity = twinkle * (1 - age / trailLifetime) ** .7 *
        THREE.MathUtils.smoothstep(entranceDuration - .1 - birth, 0, .22);
      batch.put(count++, pose.position, size * (1 - .31 * age / trailLifetime), opacity, kind);
    }
    batch.draw(count);
  };
}
