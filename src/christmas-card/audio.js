export const mutePreference = 'christmas-card-mute';

// Jingle Bells chorus, in C. Each pair is a MIDI note and its length in beats.
const bells = [
  [76,1],[76,1],[76,2], [76,1],[76,1],[76,2], [76,1],[79,1],[72,1],[74,1], [76,4],
  [77,1],[77,1],[77,1],[77,1], [77,1],[76,1],[76,1],[76,.5],[76,.5],
  [76,1],[74,1],[74,1],[76,1], [74,2],[79,2],
  [76,1],[76,1],[76,2], [76,1],[76,1],[76,2], [76,1],[79,1],[72,1],[74,1], [76,4],
  [77,1],[77,1],[77,1],[77,1], [77,1],[76,1],[76,1],[76,.5],[76,.5],
  [79,1],[79,1],[77,1],[74,1], [72,4], [0,2],
];
const beat = .39;
const frequency = note => 440 * 2 ** ((note - 69) / 12);

export function createCardAudio({
  createContext = () => new AudioContext(),
  storage = () => globalThis.localStorage,
  visible = true,
  schedule = setInterval,
  cancel = clearInterval,
} = {}) {
  let muted = false;
  try { muted = storage().getItem(mutePreference) === '1'; } catch {}
  let context, master, music, noise, timer = null, noteIndex = 0, nextNote = null;
  const voices = new Set();

  function playSource(source, destination, start, duration, volume, attack = .008) {
    const envelope = context.createGain();
    envelope.gain.setValueAtTime(.0001, start);
    envelope.gain.exponentialRampToValueAtTime(volume, start + attack);
    envelope.gain.exponentialRampToValueAtTime(.0001, start + duration);
    source.connect(envelope).connect(destination);
    voices.add(source);
    source.onended = () => { voices.delete(source); source.disconnect(); envelope.disconnect(); };
    source.start(start);
    source.stop(start + duration + .02);
  }

  function tone(note, destination, start, duration, volume, ratio = 1) {
    const voice = context.createOscillator();
    voice.frequency.value = frequency(note) * ratio;
    playSource(voice, destination, start, duration, volume);
  }

  function bell(note, destination, start, duration, volume) {
    tone(note, destination, start, duration, volume);
    tone(note, destination, start, duration * .64, volume * .22, 2.01);
  }

  function fillMusic() {
    const now = context.currentTime;
    if (context.state !== 'running') return;
    nextNote = Math.max(nextNote ?? 0, now + .025);
    while (nextNote < now + .23) {
      const [note, length] = bells[noteIndex];
      if (note) {
        bell(note, music, nextNote, Math.min(.8, length * beat + .22), .095);
        if ([0, 9, 10, 25, 34, 35, bells.length - 2].includes(noteIndex)) {
          tone(noteIndex === 9 || noteIndex === 34 ? 55 : 48, music, nextNote, .74, .045);
        }
      }
      nextNote += length * beat;
      noteIndex = (noteIndex + 1) % bells.length;
    }
  }

  function sync() {
    if (!master) return;
    master.gain.setValueAtTime(visible && !muted ? .64 : 0, context.currentTime);
    if (visible && !muted) {
      if (context.state !== 'running') context.resume().catch(() => {});
      if (timer === null) {
        fillMusic();
        timer = schedule(fillMusic, 95);
      }
    } else {
      if (timer !== null) cancel(timer);
      timer = null;
      if (!visible) context.suspend().catch(() => {});
    }
  }

  function rustle(start, duration, volume, from, to) {
    if (!noise) {
      noise = context.createBuffer(1, Math.ceil(context.sampleRate * .48), context.sampleRate);
      const samples = noise.getChannelData(0);
      let seed = 901;
      for (let i = 0; i < samples.length; i++) {
        seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
        samples[i] = (seed / 2 ** 32) * 2 - 1;
      }
    }
    const source = context.createBufferSource();
    source.buffer = noise;
    const filter = context.createBiquadFilter();
    filter.type = 'bandpass';
    filter.Q.value = .8;
    filter.frequency.setValueAtTime(from, start);
    filter.frequency.exponentialRampToValueAtTime(to, start + duration);
    const envelope = context.createGain();
    envelope.gain.setValueAtTime(.0001, start);
    envelope.gain.exponentialRampToValueAtTime(volume, start + (duration > .3 ? .16 : .014));
    envelope.gain.exponentialRampToValueAtTime(.0001, start + duration);
    source.connect(filter).connect(envelope).connect(master);
    voices.add(source);
    source.onended = () => { voices.delete(source); source.disconnect(); filter.disconnect(); envelope.disconnect(); };
    source.start(start);
    source.stop(start + duration);
  }

  return {
    get muted() { return muted; },
    activate() {
      if (muted || !visible) return false;
      const first = !context;
      try {
        if (first) {
          context = createContext();
          master = context.createGain();
          music = context.createGain();
          music.gain.value = .23;
          music.connect(master).connect(context.destination);
        }
        sync();
        return first;
      } catch { return false; }
    },
    setMuted(value) {
      muted = value;
      try { storage().setItem(mutePreference, value ? '1' : '0'); } catch {}
      sync();
      if (muted && context) {
        for (const voice of voices) voice.stop(context.currentTime);
        nextNote = null;
      }
    },
    setVisible(value) {
      visible = value;
      sync();
    },
    play(effect) {
      if (!master || !visible || muted) return;
      const start = context.currentTime + .015;
      switch (effect) {
        case 'entrance':
          rustle(start, .41, .08, 560, 1700);
          bell(79, master, start + .13, .46, .065);
          bell(84, master, start + .24, .56, .055);
          break;
        case 'seal':
          rustle(start, .092, .20, 2200, 590);
          tone(61, master, start, .13, .042);
          break;
        case 'flap':
          rustle(start, .24, .08, 1060, 640);
          break;
        case 'sparkle':
          [84, 88, 91].forEach((note, i) => bell(note, master, start + i * .052, .39, .062));
          break;
        case 'arrival':
          [72, 76, 79, 84].forEach((note, i) => bell(note, master, start + i * .042, .58, .068));
          break;
      }
    },
  };
}
