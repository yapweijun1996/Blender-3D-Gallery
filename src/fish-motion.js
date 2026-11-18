import { localize } from "./i18n/index.js";
import { AnimationMixer, LoopRepeat } from 'three';

// Fish playback owns its clock and controls; other gallery models stay on demand.
export default function createFishMotion({ model, clips, container, invalidate }) {
  const clip = clips.find(item => item.name === 'Swim_Loop') ?? clips[0];
  if (!clip) throw new Error('This fish has no swimming animation.');
  const mixer = new AnimationMixer(model);
  const action = mixer.clipAction(clip).setLoop(LoopRepeat, Infinity);
  action.play();
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  let playing = !preference.matches;
  let lastTime = 0;
  const controls = document.createElement('div');
  controls.className = 'fish-motion-controls';
  controls.setAttribute('role', 'group');
  localize(controls, "viewer.fish", undefined, "aria-label");
  // Inline layout keeps these isolated controls usable without gallery CSS changes.
  Object.assign(controls.style, { display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap', padding: '12px 24px' });
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'outline-button';
  button.dataset.fishPlayback = '';
  button.style.minHeight = '44px';
  const sync = () => {
    localize(button, playing ? 'viewer.pauseFish' : 'viewer.playFish');
    button.setAttribute('aria-pressed', String(playing));
    lastTime = 0;
    invalidate();
  };
  const changePreference = () => { playing = !preference.matches; sync(); };
  button.addEventListener('click', () => { playing = !playing; sync(); });
  preference.addEventListener('change', changePreference);
  controls.append(button);
  container.insertAdjacentElement('afterend', controls);
  sync();
  return {
    update() {
      const now = performance.now();
      const delta = lastTime ? Math.min((now - lastTime) / 1000, .05) : 0;
      lastTime = now;
      // Reset the elapsed clock after tab suspension instead of jumping the pose.
      if (playing) mixer.update(delta);
      else mixer.update(0);
      return playing;
    },
    suspend() { lastTime = 0; },
    dispose() {
      preference.removeEventListener('change', changePreference);
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
      const skeletons = new Set();
      model.traverse(object => { if (object.isSkinnedMesh) skeletons.add(object.skeleton); });
      for (const skeleton of skeletons) skeleton.dispose();
      controls.remove();
    },
  };
}
