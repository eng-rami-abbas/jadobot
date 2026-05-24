// sound.js
const SoundManager = {
  muted: false,
  audioCtx: null,
  gainNode: null,
  init() {
    this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    this.gainNode = this.audioCtx.createGain();
    this.gainNode.connect(this.audioCtx.destination);
  },
  playTone(freq, duration, type = 'sine', volume = 0.3) {
    if (this.muted || !this.audioCtx) return;
    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime);
    gain.gain.setValueAtTime(volume, this.audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + duration);
    osc.connect(gain);
    gain.connect(this.gainNode);
    osc.start();
    osc.stop(this.audioCtx.currentTime + duration);
  },
  playSpinStart() {
    this.playTone(800, 0.3, 'square', 0.2);
  },
  playBallRoll() {
    // صوت دوران الكرة: تغيير تردد مستمر
    if (this.muted || !this.audioCtx) return;
    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(1200, this.audioCtx.currentTime);
    osc.frequency.linearRampToValueAtTime(400, this.audioCtx.currentTime + 2);
    gain.gain.setValueAtTime(0.15, this.audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 2);
    osc.connect(gain);
    gain.connect(this.gainNode);
    osc.start();
    osc.stop(this.audioCtx.currentTime + 2);
  },
  playClick() {
    this.playTone(2000, 0.05, 'square', 0.2);
  },
  playWin() {
    this.playTone(523, 0.2, 'sine', 0.3);
    setTimeout(() => this.playTone(659, 0.2, 'sine', 0.3), 200);
    setTimeout(() => this.playTone(784, 0.4, 'sine', 0.3), 400);
  },
  playLose() {
    this.playTone(300, 0.3, 'sine', 0.2);
    setTimeout(() => this.playTone(200, 0.5, 'sine', 0.2), 300);
  },
  toggleMute() {
    this.muted = !this.muted;
    document.getElementById('muteBtn').textContent = this.muted ? '🔇' : '🔊';
  }
};

// التهيئة بعد تفاعل المستخدم
document.getElementById('muteBtn').addEventListener('click', () => {
  if (!SoundManager.audioCtx) SoundManager.init();
  SoundManager.toggleMute();
});
// تأخير تهيئة AudioContext حتى أول نقرة لتجنب قيود المتصفح
window.addEventListener('click', () => {
  if (!SoundManager.audioCtx) SoundManager.init();
}, { once: true });