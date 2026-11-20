// Small synthesised soundscape for the drive demo: engine, horn, a bump, checkpoint beeps and a soft city bed.
// No audio files. The AudioContext is created on the first user gesture because browsers refuse to start it earlier.
export function createDriveAudio() {
  let context = null, enabled = true;
  let engine, engineGain, filter, bed, bedGain;

  function start() {
    if (context) { context.resume?.(); return; }
    const Context = globalThis.AudioContext ?? globalThis.webkitAudioContext;
    if (!Context) return;
    context = new Context();
    const master = context.createGain();
    master.gain.value = enabled ? 0.5 : 0;
    master.connect(context.destination);
    context.master = master;
    // Engine: a detuned saw pair through a low-pass filter.
    engine = [context.createOscillator(), context.createOscillator()];
    engine[0].type = "sawtooth"; engine[1].type = "square";
    filter = context.createBiquadFilter();
    filter.type = "lowpass"; filter.frequency.value = 500;
    engineGain = context.createGain();
    engineGain.gain.value = 0;
    for (const oscillator of engine) { oscillator.connect(filter); oscillator.start(); }
    filter.connect(engineGain).connect(master);
    // City bed: filtered noise.
    const buffer = context.createBuffer(1, context.sampleRate * 2, context.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = (Math.random() * 2 - 1) * 0.5;
    bed = context.createBufferSource();
    bed.buffer = buffer; bed.loop = true;
    const bedFilter = context.createBiquadFilter();
    bedFilter.type = "bandpass"; bedFilter.frequency.value = 380; bedFilter.Q.value = 0.4;
    bedGain = context.createGain();
    bedGain.gain.value = 0.03;
    bed.connect(bedFilter).connect(bedGain).connect(master);
    bed.start();
  }

  function tone(frequency, seconds, { type = "sine", gain = 0.25, slide = 0 } = {}) {
    if (!context || !enabled) return;
    const oscillator = context.createOscillator(), envelope = context.createGain(), now = context.currentTime;
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, now);
    if (slide) oscillator.frequency.linearRampToValueAtTime(frequency + slide, now + seconds);
    envelope.gain.setValueAtTime(0.0001, now);
    envelope.gain.exponentialRampToValueAtTime(gain, now + 0.02);
    envelope.gain.exponentialRampToValueAtTime(0.0001, now + seconds);
    oscillator.connect(envelope).connect(context.master);
    oscillator.start(now);
    oscillator.stop(now + seconds + 0.05);
  }

  return {
    start,
    get enabled() { return enabled; },
    set enabled(value) {
      enabled = Boolean(value);
      if (context) context.master.gain.setTargetAtTime(enabled ? 0.5 : 0, context.currentTime, 0.05);
    },
    /** Called every frame with the speed in m/s and how built-up the surroundings are (0 to 1). */
    update(speed, busy) {
      if (!context || !enabled) return;
      const now = context.currentTime;
      const base = 48 + speed * 3.4;
      engine[0].frequency.setTargetAtTime(base, now, 0.08);
      engine[1].frequency.setTargetAtTime(base * 0.5, now, 0.08);
      filter.frequency.setTargetAtTime(280 + speed * 28, now, 0.1);
      engineGain.gain.setTargetAtTime(0.05 + Math.min(1, speed / 30) * 0.1, now, 0.1);
      bedGain.gain.setTargetAtTime(0.015 + busy * 0.04, now, 0.5);
    },
    horn() { tone(392, 0.45, { type: "square", gain: 0.12 }); tone(494, 0.45, { type: "square", gain: 0.1 }); },
    bump() { tone(90, 0.25, { type: "triangle", gain: 0.3, slide: -40 }); },
    beep() { tone(880, 0.12, { type: "sine", gain: 0.18 }); },
    stamp() { tone(160, 0.18, { type: "triangle", gain: 0.35, slide: -60 }); },
    gate() { tone(520, 0.5, { type: "sine", gain: 0.12, slide: 200 }); },
    arrive() { tone(523, 0.25, { gain: 0.2 }); setTimeout(() => tone(659, 0.25, { gain: 0.2 }), 180); setTimeout(() => tone(784, 0.45, { gain: 0.2 }), 360); },
    dispose() {
      try { engine?.forEach(oscillator => oscillator.stop()); bed?.stop(); context?.close(); } catch { /* Already stopped. */ }
      context = null;
    },
  };
}
