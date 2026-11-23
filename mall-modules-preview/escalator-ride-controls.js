import { Vector3 } from 'three';
import { createEscalatorPassenger } from './escalator-passenger.js';

export function setupEscalatorRide({ loadAvatar, getMachine, focusPassenger, moveCamera }) {
  const start = document.querySelector('#ride-start');
  const panel = document.querySelector('#ride-controls');
  const toggle = document.querySelector('#ride-toggle');
  const scrubber = document.querySelector('#ride-time');
  const readout = document.querySelector('#ride-readout');
  const message = document.querySelector('#ride-message');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const lastPosition = new Vector3();
  const position = new Vector3();
  const movement = new Vector3();
  let ride, request = 0;

  function refresh() {
    const label = ride.playing ? 'Pause ride' : ride.time >= ride.duration ? 'Replay ride' : 'Play ride';
    if (toggle.textContent !== label) toggle.textContent = label;
    const time = ride.time.toFixed(1);
    if (scrubber.valueAsNumber !== Number(time)) scrubber.value = time;
    const text = time + ' / ' + ride.duration.toFixed(1) + ' s';
    if (readout.value !== text) readout.value = text;
    ride.visual.getWorldPosition(position);
    moveCamera(movement.subVectors(position, lastPosition));
    lastPosition.copy(position);
  }

  function close() {
    request++;
    ride?.dispose();
    ride = null;
    panel.hidden = true;
    start.hidden = false;
    start.disabled = false;
    start.textContent = 'Ride a step';
    message.textContent = '';
  }
  start.addEventListener('click', async () => {
    const machine = getMachine();
    if (!machine || ride) return;
    const id = ++request;
    start.disabled = true;
    start.textContent = 'Loading passenger…';
    message.textContent = '';
    try {
      const avatar = await loadAvatar();
      if (id !== request) return;
      ride = createEscalatorPassenger({ machine, clips: machine.animations, avatar, avatarClips: avatar.animations });
      ride.visual.getWorldPosition(lastPosition);
      focusPassenger(ride.visual);
      scrubber.max = ride.duration.toFixed(1);
      panel.hidden = false;
      start.hidden = true;
      message.textContent = '';
      if (!reduced.matches && !document.hidden) ride.play();
      refresh();
      toggle.focus({ preventScroll: true });
    } catch (error) {
      if (id !== request) return;
      close();
      message.textContent = 'Unable to load the passenger. Select Ride a step to retry.';
      console.error('Escalator passenger failed to load', error);
    }
  });
  toggle.addEventListener('click', () => {
    if (ride.playing) ride.pause();
    else ride.play();
    refresh();
  });
  scrubber.addEventListener('input', () => {
    ride.seek(scrubber.valueAsNumber);
    refresh();
  });
  function pause() {
    if (!ride?.playing) return;
    ride.pause();
    refresh();
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) pause(); });
  reduced.addEventListener('change', () => { if (reduced.matches) pause(); });
  return {
    close,
    update(dt) {
      if (!ride?.playing) return;
      ride.update(dt);
      refresh();
    },
  };
}
