/**
 * TinyHand Windows — Cinematic Motion Graphics & Ambient Background Engine
 * Implements MotionSites techniques: Fluid interactive nebula, constellation mesh, and parallax depth
 */

class BackgroundMotionEngine {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');

    this.mouse = { x: window.innerWidth * 0.5, y: window.innerHeight * 0.35, targetX: window.innerWidth * 0.5, targetY: window.innerHeight * 0.35 };
    this.particles = [];
    this.cursorDust = [];
    this.decorElements = document.querySelectorAll('.floating-decor');

    this.initParticles(55);
    this.resize = this.resize.bind(this);
    this.loop = this.loop.bind(this);
    this.onMouseMove = this.onMouseMove.bind(this);

    window.addEventListener('resize', this.resize);
    window.addEventListener('mousemove', this.onMouseMove);
    this.resize();
    requestAnimationFrame(this.loop);
  }

  resize() {
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = this.width * dpr;
    this.canvas.height = this.height * dpr;
    this.ctx.scale(dpr, dpr);
  }

  initParticles(count) {
    this.particles = [];
    for (let i = 0; i < count; i++) {
      this.particles.push({
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.35,
        radius: Math.random() * 1.8 + 0.8,
        baseAlpha: Math.random() * 0.45 + 0.15,
        alpha: 0.3,
        pulseSpeed: Math.random() * 0.02 + 0.01,
        color: Math.random() > 0.4 ? '#3B82F6' : '#60A5FA'
      });
    }
  }

  onMouseMove(e) {
    this.mouse.targetX = e.clientX;
    this.mouse.targetY = e.clientY;

    // Add subtle luminous cursor dust
    if (Math.random() > 0.55 && this.cursorDust.length < 35) {
      this.cursorDust.push({
        x: e.clientX,
        y: e.clientY,
        vx: (Math.random() - 0.5) * 0.8,
        vy: (Math.random() - 0.5) * 0.8 - 0.3,
        size: Math.random() * 2.5 + 1.2,
        alpha: 0.7,
        color: Math.random() > 0.3 ? '#60A5FA' : '#93C5FD'
      });
    }
  }

  updateParallax() {
    // Smooth lerp mouse
    this.mouse.x += (this.mouse.targetX - this.mouse.x) * 0.06;
    this.mouse.y += (this.mouse.targetY - this.mouse.y) * 0.06;

    const normX = (this.mouse.x / this.width - 0.5) * 2;
    const normY = (this.mouse.y / this.height - 0.5) * 2;

    this.decorElements.forEach(el => {
      const depth = parseFloat(el.dataset.depth || 1);
      const moveX = normX * depth * 28;
      const moveY = normY * depth * 28;
      const rot = normX * depth * 8;
      el.style.transform = `translate3d(${moveX}px, ${moveY}px, 0) rotate(${rot}deg)`;
    });
  }

  loop() {
    this.updateParallax();

    const ctx = this.ctx;
    const w = this.width;
    const h = this.height;

    ctx.clearRect(0, 0, w, h);

    // 1. Draw Volumetric Aurora Nebula around mouse
    const nebulaGrad = ctx.createRadialGradient(
      this.mouse.x, this.mouse.y, 40,
      this.mouse.x, this.mouse.y, 580
    );
    nebulaGrad.addColorStop(0, 'rgba(37, 99, 235, 0.16)');
    nebulaGrad.addColorStop(0.35, 'rgba(59, 130, 246, 0.07)');
    nebulaGrad.addColorStop(0.7, 'rgba(16, 185, 129, 0.025)');
    nebulaGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

    ctx.fillStyle = nebulaGrad;
    ctx.fillRect(0, 0, w, h);

    // Top Atmospheric Horizon Beam
    const topGlow = ctx.createRadialGradient(w * 0.5, -40, 20, w * 0.5, -40, 650);
    topGlow.addColorStop(0, 'rgba(37, 99, 235, 0.22)');
    topGlow.addColorStop(0.5, 'rgba(59, 130, 246, 0.06)');
    topGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = topGlow;
    ctx.fillRect(0, 0, w, h);

    // 2. Draw Constellation Particle Mesh
    const particles = this.particles;
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;

      // Wrap screen edges
      if (p.x < 0) p.x = w;
      if (p.x > w) p.x = 0;
      if (p.y < 0) p.y = h;
      if (p.y > h) p.y = 0;

      // Pulse alpha
      p.alpha = p.baseAlpha + Math.sin(Date.now() * 0.002 * p.pulseSpeed * 100) * 0.15;

      // Draw particle dot
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.globalAlpha = Math.max(0.1, p.alpha);
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 8;
      ctx.fill();

      // Connect nearby particles with subtle hairlines
      for (let j = i + 1; j < particles.length; j++) {
        const p2 = particles[j];
        const dx = p.x - p2.x;
        const dy = p.y - p2.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 115) {
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = '#3B82F6';
          ctx.globalAlpha = (1 - dist / 115) * 0.18;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }

    // 3. Draw & update luminous cursor dust
    for (let i = this.cursorDust.length - 1; i >= 0; i--) {
      const d = this.cursorDust[i];
      d.x += d.vx;
      d.y += d.vy;
      d.alpha -= 0.022;

      if (d.alpha <= 0) {
        this.cursorDust.splice(i, 1);
        continue;
      }

      ctx.beginPath();
      ctx.arc(d.x, d.y, d.size, 0, Math.PI * 2);
      ctx.fillStyle = d.color;
      ctx.globalAlpha = d.alpha;
      ctx.shadowColor = d.color;
      ctx.shadowBlur = 10;
      ctx.fill();
    }

    ctx.globalAlpha = 1.0;
    ctx.shadowBlur = 0;

    requestAnimationFrame(this.loop);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  new BackgroundMotionEngine('bgCanvas');
});
