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
const stallMs = 1200;
const db = amplitude => amplitude > 0 ? 20 * Math.log10(amplitude) : -Infinity;

export function measureLevel(samples) {
  let peak = 0, sum = 0;
  for (const sample of samples) {
    peak = Math.max(peak, Math.abs(sample));
    sum += sample * sample;
  }
  return {peak: db(peak), rms: db(Math.sqrt(sum / samples.length))};
}

// The live and offline renders use the same graph and source envelopes.
export function createCardMix(context, {meter = false} = {}) {
  const master = context.createGain();
  const music = context.createGain();
  const effects = context.createGain();
  const compressor = context.createDynamicsCompressor();
  compressor.threshold.value = -12;
  compressor.knee.value = 6;
  compressor.ratio.value = 6;
  compressor.attack.value = .003;
  compressor.release.value = .15;
  const trim = context.createGain();
  trim.gain.value = .45;
  const limiter = context.createWaveShaper();
  // Pass ordinary peaks unchanged and keep transients below full scale.
  limiter.curve = Float32Array.from({length: 1025}, (_, i) => {
    const sample = i / 512 - 1;
    const excess = Math.max(0, Math.abs(sample) - .65);
    return sample - Math.sign(sample) * (.4 / .35) * excess ** 2;
  });
  // The gate also silences any samples still in the compressor's lookahead.
  music.gain.value = 2.3;
  effects.gain.value = 4.6;
  music.connect(compressor);
  effects.connect(compressor);
  compressor.connect(trim).connect(limiter).connect(master).connect(context.destination);
  const analyser = meter ? context.createAnalyser() : null;
  if (analyser) {
    analyser.fftSize = 4096;
    master.connect(analyser);
  }
  const samples = analyser && new Float32Array(analyser.fftSize);
  let noise, testVoice, noteIndex = 0, nextNote = null;
  const voices = new Set();

  function playSource(source, destination, start, duration, volume, {attack = .008, hold = 0, filter} = {}) {
    const envelope = context.createGain();
    envelope.gain.setValueAtTime(.0001, start);
    envelope.gain.exponentialRampToValueAtTime(volume, start + attack);
    if (hold) envelope.gain.setValueAtTime(volume, start + hold);
    else envelope.gain.exponentialRampToValueAtTime(volume * .055, start + duration * .8);
    envelope.gain.exponentialRampToValueAtTime(.0001, start + duration);
    if (filter) source.connect(filter).connect(envelope);
    else source.connect(envelope);
    envelope.connect(destination);
    voices.add(source);
    source.onended = () => {
      voices.delete(source);
      source.disconnect();
      filter?.disconnect();
      envelope.disconnect();
    };
    source.start(start);
    source.stop(start + duration);
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

  function fillMusic(earliest, until) {
    nextNote = Math.max(nextNote ?? 0, earliest);
    while (nextNote < until) {
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
    playSource(source, effects, start, duration, volume, {filter, attack: duration > .3 ? .16 : .014});
  }

  function play(effect, start) {
    switch (effect) {
      case 'entrance':
        rustle(start, .41, .08, 560, 1700);
        bell(79, effects, start + .13, .46, .075);
        bell(84, effects, start + .24, .56, .065);
        break;
      case 'seal':
        rustle(start, .092, .20, 2200, 590);
        tone(61, effects, start, .13, .12);
        break;
      case 'flap':
        rustle(start, .24, .36, 1060, 640);
        break;
      case 'sparkle':
        [84, 88, 91].forEach((note, i) => bell(note, effects, start + i * .052, .39, .062));
        break;
      case 'arrival':
        [72, 76, 79, 84].forEach((note, i) => bell(note, effects, start + i * .042, .58, .068));
        break;
    }
  }

  return {
    fillMusic,
    play,
    testSound(start) {
      if (voices.has(testVoice)) testVoice.stop(context.currentTime);
      testVoice = context.createOscillator();
      testVoice.frequency.value = 880;
      playSource(testVoice, limiter, start, 1, .55, {attack: .015, hold: .95});
    },
    setEnabled(value) { master.gain.setValueAtTime(Number(value), context.currentTime); },
    stop() {
      for (const voice of voices) voice.stop(context.currentTime);
      nextNote = null;
    },
    level() {
      if (!analyser) return null;
      analyser.getFloatTimeDomainData(samples);
      return measureLevel(samples);
    },
  };
}

export function createCardAudio({
  createContext = () => new (globalThis.AudioContext ?? globalThis.webkitAudioContext)(),
  audioSession = () => globalThis.navigator?.audioSession,
  storage = () => globalThis.localStorage,
  visible = true,
  meter = false,
  onStatus = () => {},
  now = () => performance.now(),
  schedule = setInterval,
  cancel = clearInterval,
} = {}) {
  let muted = false;
  try { muted = storage().getItem(mutePreference) === '1'; } catch {}
  let context, mix, timer = null, primed = false, testPending = false;
  let lastTime = 0, progressAt = 0, resumeAt = null, advancing = false, stalled = false;
  let needsResume = false, canRebuild = true, lastResumeError = '', pendingGestureResume, published;

  const enabled = () => visible && !muted;
  const playing = () => enabled() && context?.state === 'running' && !stalled && !needsResume;
  function status() {
    if (muted) return 'muted';
    if (!visible || needsResume) return 'waiting';
    // A running context remains muteable even when the clock monitor reports a stall.
    if (context?.state === 'running') return 'playing';
    if (pendingGestureResume && !stalled && context.state !== 'closed') return 'starting';
    return 'waiting';
  }

  function publish() {
    const next = status();
    if (published === next) return;
    published = next;
    onStatus(next);
  }

  function sessionType(type) {
    try {
      const session = audioSession();
      if (!session) return 'Unavailable';
      if (type && session.type !== type) session.type = type;
      return session.type;
    } catch { return 'Unavailable'; }
  }

  function unlock() {
    const source = context.createBufferSource();
    source.buffer = context.createBuffer(1, 1, context.sampleRate);
    source.connect(context.destination);
    source.onended = () => source.disconnect();
    source.start(0);
    primed = true;
  }

  function updatePlayback() {
    if (playing()) {
      const time = context.currentTime;
      mix.fillMusic(time + .025, time + .23);
      if (testPending) {
        testPending = false;
        mix.testSound(time + .015);
      }
    } else advancing = false;
    publish();
  }

  function tick() {
    const time = context.currentTime;
    if (context.state === 'running' && time > lastTime) {
      advancing = true;
      stalled = false;
      canRebuild = true;
      lastTime = time;
      progressAt = now();
      resumeAt = null;
    } else if (context.state === 'closed' ||
      ((context.state === 'running' || resumeAt !== null) && now() - (resumeAt ?? progressAt) >= stallMs)) {
      advancing = false;
      stalled = true;
      // Rebuild once automatically. If the browser still requires activation,
      // the next trusted gesture can rebuild again on its own call stack.
      if (canRebuild) {
        canRebuild = false;
        start(false, true);
        return;
      }
    }
    updatePlayback();
  }

  function start(gesture, replace = stalled || context?.state === 'closed') {
    if (!enabled()) return false;
    const first = !context;
    sessionType('playback');
    try {
      if (first || replace) {
        const previous = context;
        if (previous && previous.state !== 'closed') {
          mix?.setEnabled(false);
          void previous.close().catch(() => {});
        }
        context = undefined;
        mix = undefined;
        const current = createContext();
        context = current;
        mix = createCardMix(current, {meter});
        current.onstatechange = () => {
          if (current !== context) return;
          if (current.state !== 'running') {
            primed = false;
            pendingGestureResume = undefined;
          }
          updatePlayback();
        };
        primed = advancing = stalled = needsResume = false;
        pendingGestureResume = undefined;
        lastTime = current.currentTime;
        progressAt = now();
        resumeAt = null;
      }
      const current = context;
      if (timer === null) {
        progressAt = now();
        lastTime = current.currentTime;
        timer = schedule(tick, 95);
      }
      if (gesture && !primed) unlock();
      if (needsResume || current.state !== 'running') {
        resumeAt ??= now();
        needsResume = false;
        const attempt = current.resume();
        if (gesture) pendingGestureResume = attempt;
        const finishResume = () => {
          if (pendingGestureResume !== attempt) return;
          pendingGestureResume = undefined;
          publish();
        };
        void attempt.then(finishResume, error => {
          if (current === context) lastResumeError = String(error);
          finishResume();
        });
      }
      mix.setEnabled(true);
      updatePlayback();
      return first;
    } catch (error) {
      lastResumeError = String(error);
      if (context && !mix) {
        void context.close().catch(() => {});
        context = undefined;
      }
      pause();
      return false;
    }
  }

  function pause() {
    if (timer !== null) cancel(timer);
    timer = null;
    advancing = primed = testPending = false;
    resumeAt = null;
    pendingGestureResume = undefined;
    if (mix && context.state !== 'closed') {
      mix.setEnabled(false);
      mix.stop();
      needsResume = true;
      void context.suspend().catch(() => {});
    }
    sessionType('auto');
    publish();
  }

  return {
    get muted() { return muted; },
    // The click handler uses the same state that was published to the control.
    get status() { return published ?? status(); },
    activate() { return start(true); },
    setMuted(value) {
      muted = value;
      try { storage().setItem(mutePreference, value ? '1' : '0'); } catch {}
      if (value) pause();
      else publish();
    },
    setVisible(value) {
      visible = value;
      if (!visible) pause();
      else if (context && !muted) start(false);
    },
    play(effect) {
      if (enabled() && mix && context.state !== 'closed' && !stalled) {
        mix.play(effect, context.currentTime + .015);
      }
    },
    testSound() {
      if (!enabled()) return;
      testPending = true;
      start(true);
    },
    diagnostics() {
      return {
        state: context?.state ?? 'Not created',
        sampleRate: context?.sampleRate,
        currentTime: context?.currentTime,
        advancing,
        session: sessionType(),
        lastResumeError,
        level: playing() && advancing ? mix.level() : null,
      };
    },
  };
}
