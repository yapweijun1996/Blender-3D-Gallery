import { Vector3 } from 'three';
import { createEscalatorPassenger } from './escalator-passenger.js';
import { createEscalatorRoute } from './escalator-passenger-route.js';

const phaseText = {
  approach: 'Walking from the lower floor to the escalator',
  board: 'Stepping onto the moving tread',
  ride: 'Riding the tread to the upper floor',
  alight: 'Stepping onto the upper landing',
  depart: 'Walking across the upper floor joint',
};

export function setupEscalatorRide({ loadAvatar, getMachine, focusPassenger, moveCamera }) {
  const stepButton = document.querySelector('#ride-start');
  const journeyButton = document.querySelector('#journey-start');
  const starts = [stepButton, journeyButton];
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
  let ride, journey = false, request = 0;

  function refresh() {
    const verb = ride.playing ? 'Pause' : ride.time >= ride.duration ? 'Replay' : 'Play';
    const label = verb + (journey ? ' journey' : ' ride');
    if (toggle.textContent !== label) toggle.textContent = label;
    const precision = journey ? 2 : 1;
    const time = ride.time.toFixed(precision);
    if (scrubber.valueAsNumber !== Number(time)) scrubber.value = time;
    const text = time + ' / ' + ride.duration.toFixed(precision) + ' s';
    if (readout.value !== text) readout.value = text;
    let description = 'Follow the passenger from the lower flat steps to the upper flat steps.';
    if (journey) description = ride.time >= ride.duration ? 'Arrived on the upper floor' : phaseText[ride.phase];
    if (phase.textContent !== description) phase.textContent = description;
    ride.visual.getWorldPosition(position);
    moveCamera(movement.subVectors(position, lastPosition));
    lastPosition.copy(position);
  }

  function close() {
    request++;
    ride?.dispose();
    ride = null;
    panel.hidden = true;
    for (const button of starts) {
      button.hidden = false;
      button.disabled = false;
    }
    stepButton.textContent = 'Ride a step';
    journeyButton.textContent = 'Travel between floors';
    message.textContent = '';
  }
  async function start(event) {
    const machine = getMachine();
    if (!machine || ride) return;
    const button = event.currentTarget;
    journey = button === journeyButton;
    const id = ++request;
    for (const option of starts) option.disabled = true;
    button.textContent = 'Loading passenger…';
    message.textContent = '';
    try {
      const avatar = await loadAvatar();
      if (id !== request) return;
      const create = journey ? createEscalatorRoute : createEscalatorPassenger;
      ride = create({ machine, clips: machine.animations, avatar, avatarClips: avatar.animations });
      ride.visual.getWorldPosition(lastPosition);
      focusPassenger(ride.visual, journey);
      // Hundredths expose the brief interval with one foot on each surface.
      scrubber.step = journey ? '.01' : '.1';
      scrubber.max = ride.duration.toFixed(journey ? 2 : 1);
      panel.hidden = false;
      for (const option of starts) option.hidden = true;
      message.textContent = '';
      if (!reduced.matches && !document.hidden) ride.play();
      refresh();
      toggle.focus({ preventScroll: true });
    } catch (error) {
      if (id !== request) return;
      close();
      message.textContent = journey ? 'Unable to load the passenger. Select Travel between floors to retry.'
        : 'Unable to load the passenger. Select Ride a step to retry.';
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
