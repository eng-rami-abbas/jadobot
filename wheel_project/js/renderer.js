import { SEGMENTS } from './segments.js';

export class WheelRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.rotation = 0;
    this.bulbPhase = 0;
  }

  setRotation(deg) {
    this.rotation = deg;
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const size = Math.min(rect.width, rect.height) || 360;
    this.canvas.width = size * dpr;
    this.canvas.height = size * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.logicalSize = size;
  }

  draw() {
    const ctx = this.ctx;
    const size = this.logicalSize || 360;
    const cx = size / 2;
    const cy = size / 2;
    const r = size / 2 - 8;
    const n = SEGMENTS.length;
    const arc = (Math.PI * 2) / n;

    ctx.clearRect(0, 0, size, size);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((this.rotation * Math.PI) / 180);

    // Outer gold rim
    const rimGrad = ctx.createRadialGradient(0, 0, r * 0.85, 0, 0, r + 6);
    rimGrad.addColorStop(0, '#3d2e10');
    rimGrad.addColorStop(0.5, '#e8c547');
    rimGrad.addColorStop(1, '#6b5218');
    ctx.beginPath();
    ctx.arc(0, 0, r + 5, 0, Math.PI * 2);
    ctx.fillStyle = rimGrad;
    ctx.fill();

    // Bulbs
    this.bulbPhase += 0.04;
    for (let i = 0; i < 24; i++) {
      const a = (i / 24) * Math.PI * 2;
      const bx = Math.cos(a) * (r + 2);
      const by = Math.sin(a) * (r + 2);
      const on = Math.sin(this.bulbPhase + i * 0.5) > 0;
      ctx.beginPath();
      ctx.arc(bx, by, 4, 0, Math.PI * 2);
      ctx.fillStyle = on ? '#fff8dc' : '#5a4520';
      ctx.shadowColor = on ? '#ffe9a0' : 'transparent';
      ctx.shadowBlur = on ? 12 : 0;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    // Segments
    SEGMENTS.forEach((seg, i) => {
      const start = -Math.PI / 2 + i * arc;
      const end = start + arc;
      const grad = ctx.createRadialGradient(0, 0, 0, 0, 0, r);
      grad.addColorStop(0, seg.color);
      grad.addColorStop(1, seg.colorEnd);
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, r * 0.98, start, end);
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,215,120,.35)';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Label
      ctx.save();
      const mid = start + arc / 2;
      ctx.rotate(mid);
      ctx.translate(r * 0.62, 0);
      ctx.rotate(Math.PI / 2);
      ctx.textAlign = 'center';
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${Math.max(11, size * 0.028)}px Cairo, sans-serif`;
      ctx.shadowColor = 'rgba(0,0,0,.8)';
      ctx.shadowBlur = 4;
      ctx.fillText(seg.icon, 0, -8);
      ctx.font = `600 ${Math.max(9, size * 0.024)}px Cairo, sans-serif`;
      const lines = seg.labelAr.split(' ');
      lines.forEach((line, li) => ctx.fillText(line, 0, 6 + li * 14));
      ctx.restore();
    });

    // Inner ring
    ctx.beginPath();
    ctx.arc(0, 0, r * 0.22, 0, Math.PI * 2);
    ctx.strokeStyle = '#e8c547';
    ctx.lineWidth = 3;
    ctx.stroke();

    ctx.restore();
  }
}
