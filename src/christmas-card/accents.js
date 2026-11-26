import * as THREE from 'three';
import { entranceDuration, poseEntrance } from './motion.js';

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
    ctx.fillStyle = '#f6eedc';
    ctx.font = '600 43px system-ui';
    ctx.fillText('To:', 221, 294);
    ctx.font = '62px Georgia, serif';
    ctx.fillText(recipient, 221, 368, 590);
    ctx.fillStyle = '#d2a367';
    ctx.fillRect(221, 394, 425, 2);

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
    texture.needsUpdate = true;
  };
}

export function createEntranceTrail(scene, texture) {
  const samples = Array.from({ length: 44 }, (_, i) => {
    const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
      map: texture, color: i % 5 === 0 ? 0xfff8e9 : (i % 3 === 0 ? 0xe8ddff : 0xffd788), transparent: true,
      depthWrite: false, toneMapped: false, blending: THREE.AdditiveBlending,
    }));
    sprite.visible = false;
    scene.add(sprite);
    return sprite;
  });
  const pose = new THREE.Object3D();
  return (time, flight) => {
    samples.forEach((sprite, i) => {
      const age = .055 + i * .032;
      const birth = time - age;
      sprite.visible = birth > 0 && birth < entranceDuration - .1;
      if (!sprite.visible) return;
      poseEntrance(pose, birth, flight);
      sprite.position.copy(pose.position);
      sprite.position.x += Math.cos(i * 2.4) * (.16 + age * .17);
      sprite.position.y += Math.sin(i * 2.4) * (.10 + age * .22) - age * .075;
      sprite.position.z += .23 + Math.sin(i * 1.73) * .18;
      const twinkle = .78 + .22 * Math.sin(i * 3.2 + time * 9);
      sprite.scale.setScalar((.20 + (i % 4) * .043) * (1 - .31 * age / trailLifetime));
      sprite.material.opacity = twinkle * (1 - age / trailLifetime) ** .7 *
        THREE.MathUtils.smoothstep(entranceDuration - .1 - birth, 0, .22);
    });
  };
}
