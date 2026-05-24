/**
 * Wheel + ball physics — ball orbits opposite wheel, decelerates with pocket snaps.
 * Target angle comes from server only.
 */
export class SpinPhysics {
  constructor({ onWheel, onBall, onTick, onBounce, onComplete }) {
    this.onWheel = onWheel;
    this.onBall = onBall;
    this.onTick = onTick;
    this.onBounce = onBounce;
    this.onComplete = onComplete;
    this.running = false;
  }

  start(targetWheelDeg, durationMs = 11000) {
    if (this.running) return;
    this.running = true;

    const startWheel = 0;
    const endWheel = targetWheelDeg;
    const startBall = -Math.PI / 2;
    const ballTurns = -7 * Math.PI * 2;
    const endBall = -Math.PI / 2;

    const t0 = performance.now();
    const deflectors = 8;
    let lastDeflector = -1;

    const frame = (now) => {
      const t = Math.min((now - t0) / durationMs, 1);
      const ease = 1 - Math.pow(1 - t, 4);

      const wheel = startWheel + (endWheel - startWheel) * ease;
      let ball = startBall + ballTurns * (1 - ease) + (endBall - startBall) * ease;

      // Pocket snap near end — land exactly on segment center under pointer
      if (t > 0.88) {
        const snap = (endWheel % 360) * (Math.PI / 180);
        ball = -Math.PI / 2 - snap * 0.02;
      }

      const defIdx = Math.floor(((ball % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2) / (Math.PI * 2) * deflectors);
      if (defIdx !== lastDeflector && t > 0.15 && t < 0.92) {
        lastDeflector = defIdx;
        this.onBounce?.();
      }
      if (t > 0.1 && t < 0.95 && Math.random() < 0.12) {
        this.onTick?.();
      }

      this.onWheel?.(wheel);
      this.onBall?.(ball, t);

      if (t < 1) {
        requestAnimationFrame(frame);
      } else {
        this.onWheel?.(endWheel);
        this.running = false;
        this.onComplete?.();
      }
    };
    requestAnimationFrame(frame);
  }
}
