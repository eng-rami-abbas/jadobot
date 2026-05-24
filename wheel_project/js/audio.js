/** Procedural roulette sounds via Web Audio API (no external files). */
export class RouletteAudio {
  constructor() {
    this.enabled = true;
    this.ctx = null;
  }

  _ac() {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this.ctx.state === 'suspended') this.ctx.resume();
    return this.ctx;
  }

  setEnabled(on) {
    this.enabled = on;
  }

  _tone(freq, dur, type = 'sine', vol = 0.08, ramp = true) {
    if (!this.enabled) return;
    const ctx = this._ac();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = type;
    o.frequency.value = freq;
    g.gain.value = vol;
    if (ramp) {
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
    }
    o.connect(g);
    g.connect(ctx.destination);
    o.start();
    o.stop(ctx.currentTime + dur);
  }

  spinStart() {
    this._tone(120, 0.4, 'sawtooth', 0.06);
    setTimeout(() => this._tone(80, 0.3, 'triangle', 0.05), 100);
  }

  ballTick() {
    this._tone(800 + Math.random() * 400, 0.04, 'square', 0.03, true);
  }

  ballBounce() {
    this._tone(400, 0.08, 'triangle', 0.05);
    setTimeout(() => this._tone(600, 0.06, 'sine', 0.04), 40);
  }

  friction() {
    if (!this.enabled) return;
    const ctx = this._ac();
    const len = ctx.sampleRate * 0.05;
    const buf = ctx.createBuffer(1, len, ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * 0.3;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const g = ctx.createGain();
    g.gain.value = 0.04;
    src.connect(g);
    g.connect(ctx.destination);
    src.start();
  }

  win() {
    [523, 659, 784, 1047].forEach((f, i) => {
      setTimeout(() => this._tone(f, 0.25, 'sine', 0.07), i * 120);
    });
  }

  lose() {
    this._tone(200, 0.5, 'sine', 0.05);
  }
}
