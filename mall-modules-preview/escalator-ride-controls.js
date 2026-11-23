import { Vector3 } from 'three';
import { createEscalatorPassenger } from './escalator-passenger.js';
import { createEscalatorRoute } from './escalator-passenger-route.js';

function journeyPhases(from, to) {
  return {
    approach: `Walking from the ${from} floor to the escalator`,
    board: `Stepping from the ${from} landing onto the moving tread`,
    ride: `Riding the tread to the ${to} floor`,
    alight: `Stepping onto the ${to} landing`,
    depart: `Walking across the ${to} floor joint`,
    arrived: `Arrived on the ${to} floor`,
  };
}

const phaseText = { up: journeyPhases('lower', 'upper'), down: journeyPhases('upper', 'lower') };

export function setupEscalatorRide({ loadAvatar, getMachine, focusPassenger, moveCamera }) {
  const starts = document.querySelectorAll('#terminal-tools button[aria-controls="ride-controls"]');
  const labels = new Map(Array.from(starts, button => [button, button.textContent]));
  const phase = document.querySelector('#ride-phase');
  const panel = document.querySelector('#ride-controls');
  const toggle = document.querySelector('#ride-toggle');
  const scrubber = document.querySelector('#ride-time');
  const readout = document.querySelector('#ride-readout');
  const message = document.querySelector('#ride-message');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const lastPosition = new Vector3();
  const position = new Vector3();
  const movement = new Vector3();
  let ride, direction, request = 0;

  function refresh() {
    const verb = ride.playing ? 'Pause' : ride.time >= ride.duration ? 'Replay' : 'Play';
    const label = verb + (direction ? ' journey' : ' ride');
    if (toggle.textContent !== label) toggle.textContent = label;
    const precision = direction ? 2 : 1;
    const time = ride.time.toFixed(precision);
    if (scrubber.valueAsNumber !== Number(time)) scrubber.value = time;
    const text = time + ' / ' + ride.duration.toFixed(precision) + ' s';
    if (readout.value !== text) readout.value = text;
    let description = 'Follow the passenger from the lower flat steps to the upper flat steps.';
    if (direction) description = phaseText[direction][ride.time >= ride.duration ? 'arrived' : ride.phase];
    if (phase.textContent !== description) phase.textContent = description;
    ride.visual.getWorldPosition(position);
    moveCamera(movement.subVectors(position, lastPosition));
    lastPosition.copy(position);
  }

  function close() {
    request++;
    ride?.dispose();
    ride = null;
    direction = undefined;
    panel.hidden = true;
    for (const button of starts) {
      button.hidden = false;
      button.disabled = false;
      button.textContent = labels.get(button);
    }
    message.textContent = '';
  }
  async function start(event) {
    const machine = getMachine();
    if (!machine || ride) return;
    const button = event.currentTarget;
    direction = button.dataset.direction;
    const id = ++request;
    for (const option of starts) option.disabled = true;
    button.textContent = 'Loading passenger…';
    message.textContent = '';
    try {
      const avatar = await loadAvatar();
      if (id !== request) return;
      const options = { machine, clips: machine.animations, avatar, avatarClips: avatar.animations };
      ride = direction ? createEscalatorRoute(options, direction) : createEscalatorPassenger(options);
      ride.visual.getWorldPosition(lastPosition);
      focusPassenger(ride.visual, direction);
      // Hundredths expose the brief interval with one foot on each surface.
      scrubber.step = direction ? '.01' : '.1';
      scrubber.max = ride.duration.toFixed(direction ? 2 : 1);
      panel.hidden = false;
      for (const option of starts) option.hidden = true;
      message.textContent = '';
      if (!reduced.matches && !document.hidden) ride.play();
      refresh();
      toggle.focus({ preventScroll: true });
    } catch (error) {
      if (id !== request) return;
      close();
      message.textContent = `Unable to load the passenger. Select ${labels.get(button)} to retry.`;
      console.error('Escalator passenger failed to load', error);
    }
  }
  for (const button of starts) button.addEventListener('click', start);
  toggle.addEventListener('click', () => {
    if (ride.playing) ride.pause();
    else ride.play();
    refresh();
  });
  scrubber.addEventListener('input', () => {
    // The displayed range is rounded. Its last tick reaches the exact endpoint.
    ride.seek(scrubber.valueAsNumber >= Number(scrubber.max) ? ride.duration : scrubber.valueAsNumber);
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
