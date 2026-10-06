// Synthesised night ambience: low wind off the bay, a foghorn now and then,
// plus small cues for clues and Focus. No audio files yet.
let ctx = null, master = null, hornT = 6;

function noiseBuffer(c, seconds = 2) {
  const b = c.createBuffer(1, c.sampleRate * seconds, c.sampleRate);
  const d = b.getChannelData(0);
  let last = 0;
  for (let i = 0; i < d.length; i++) { last = last * 0.985 + (Math.random() * 2 - 1) * 0.015; d[i] = last * 6; }
  return b;
}

export const audio = {
  start() {
    if (ctx) { ctx.resume(); return; }
    try { ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch { return; }
    master = ctx.createGain(); master.gain.value = 0.7; master.connect(ctx.destination);
    const wind = ctx.createBufferSource();
    wind.buffer = noiseBuffer(ctx, 4); wind.loop = true;
    const lp = ctx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 420;
    const g = ctx.createGain(); g.gain.value = 0.35;
    wind.connect(lp).connect(g).connect(master);
    wind.start();
  },

  update(dt) {
    if (!ctx) return;
    hornT -= dt;
    if (hornT <= 0) { hornT = 22 + Math.random() * 14; this.foghorn(); }
  },

  tone(freq, dur, vol, type = 'sine', delay = 0) {
    if (!ctx) return;
    const t = ctx.currentTime + delay;
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.frequency.value = freq;
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(vol, t + Math.min(0.4, dur * 0.2));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(master);
    o.start(t); o.stop(t + dur + 0.05);
  },

  foghorn() {
    // two-tone diaphone, far off across the water
    this.tone(98, 2.6, 0.14, 'triangle');
    this.tone(73, 2.2, 0.12, 'triangle', 2.4);
  },
  clue() { this.tone(880, 0.6, 0.06); this.tone(1320, 0.8, 0.04, 'sine', 0.08); },
  deduce() { [523, 659, 784, 1046].forEach((f, i) => this.tone(f, 1.2, 0.05, 'triangle', i * 0.09)); },
  wrong() { this.tone(180, 0.4, 0.06, 'triangle'); },
  focus(on) { this.tone(on ? 220 : 330, 0.5, 0.05, 'sine'); this.tone(on ? 330 : 220, 0.5, 0.04, 'sine', 0.12); },
};
