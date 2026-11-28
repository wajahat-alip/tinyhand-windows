/**
 * GalaxyCursorButton Engine (Talha / Framer 1:1 Vanilla Recreation)
 * - 3D perspective tilt wrapper (+/- 9deg X, +/- 12deg Y)
 * - Screen-blend dynamic spotlight overlay
 * - Inner canvas: ~35 twinkling stars + ~65 3-arm spiral galaxy particles with cursor repulsion (r < 60px)
 * - Overflow burst canvas: radial star burst on click
 * - ResizeObserver cached dimensions + IntersectionObserver visibility pause
 */

(function () {
  class GalaxyCursorButton {
    constructor(wrapEl) {
      this.wrap = wrapEl;
      this.btn = wrapEl.querySelector('[data-galaxy-btn]');
      this.innerCanvas = wrapEl.querySelector('.galaxy-canvas-inner');
      this.burstCanvas = wrapEl.querySelector('.galaxy-canvas-burst');
      if (!this.btn || !this.innerCanvas || !this.burstCanvas) return;

      this.ictx = this.innerCanvas.getContext('2d');
      this.bctx = this.burstCanvas.getContext('2d');
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      this.width = 210;
      this.height = 52;
      this.burstPad = 140;

      this.isHovered = false;
      this.isVisible = true;
      this.mouseX = -999;
      this.mouseY = -999;
      this.smoothX = -999;
      this.smoothY = -999;
      this.time = 0;
      this.rafId = null;

      this.bgStars = [];
      this.spiralStars = [];
      this.burstParticles = [];

      this.initStars();
      this.observe();
      this.bindEvents();
      this.updateCanvasSizes(this.btn.offsetWidth || 210, this.btn.offsetHeight || 52);
      this.renderInner(0);

      if (!this.reduceMotion) {
        this.startLoop();
      }
    }

    initStars() {
      this.bgStars = Array.from({ length: 35 }, () => ({
        nx: Math.random(),
        ny: Math.random(),
        r: 0.55 + Math.random() * 0.7,
        phase: Math.random() * Math.PI * 2,
        speed: 0.9 + Math.random() * 1.6,
        baseAlpha: 0.2 + Math.random() * 0.38,
        dx: 0,
        dy: 0,
      }));

      this.spiralStars = Array.from({ length: 65 }, (_, i) => {
        const arm = i % 3;
        const t = Math.pow(Math.random(), 0.78);
        return {
          arm,
          t,
          baseAngle: (arm * (Math.PI * 2)) / 3 + t * 2.4 + (Math.random() - 0.5) * 0.45,
          radialJitter: (Math.random() - 0.5) * 0.14,
          angularVel: (0.18 + (1 - t) * 0.35) * (Math.random() > 0.1 ? 1 : 0.7),
          size: 0.55 + Math.random() * 0.75,
          alpha: 0.28 + Math.random() * 0.42,
          isCross: i % 12 === 0,
          twinklePhase: Math.random() * Math.PI * 2,
          dx: 0,
          dy: 0,
        };
      });
    }

    updateCanvasSizes(w, h) {
      if (w <= 0 || h <= 0) return;
      this.width = w;
      this.height = h;
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);

      this.innerCanvas.width = Math.round(w * this.dpr);
      this.innerCanvas.height = Math.round(h * this.dpr);
      this.ictx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);

      const bw = w + this.burstPad * 2;
      const bh = h + this.burstPad * 2;
      this.burstCanvas.width = Math.round(bw * this.dpr);
      this.burstCanvas.height = Math.round(bh * this.dpr);
      this.bctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    }

    observe() {
      if ('ResizeObserver' in window) {
        this.resizeObserver = new ResizeObserver((entries) => {
          for (const entry of entries) {
            const cr = entry.contentRect;
            if (cr.width > 0 && cr.height > 0) {
              this.updateCanvasSizes(cr.width, cr.height);
            }
          }
        });
        this.resizeObserver.observe(this.btn);
      }

      if ('IntersectionObserver' in window) {
        this.intersectionObserver = new IntersectionObserver((entries) => {
          const entry = entries[0];
          this.isVisible = entry.isIntersecting;
          if (this.isVisible && !this.reduceMotion && !this.rafId) {
            this.startLoop();
          } else if (!this.isVisible && this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
          }
        }, { threshold: 0 });
        this.intersectionObserver.observe(this.wrap);
      }
    }

    bindEvents() {
      this.btn.addEventListener('pointerenter', () => {
        this.isHovered = true;
        this.wrap.style.transition = 'transform 0.08s cubic-bezier(0.22, 1, 0.36, 1)';
      });

      this.btn.addEventListener('pointermove', (e) => {
        const rect = this.btn.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        this.mouseX = x;
        this.mouseY = y;

        const nx = Math.max(0, Math.min(1, x / Math.max(1, rect.width)));
        const ny = Math.max(0, Math.min(1, y / Math.max(1, rect.height)));

        this.btn.style.setProperty('--mx', `${(nx * 100).toFixed(1)}%`);
        this.btn.style.setProperty('--my', `${(ny * 100).toFixed(1)}%`);

        if (!this.reduceMotion) {
          const tiltY = (nx - 0.5) * 2 * 12;
          const tiltX = -((ny - 0.5) * 2) * 9;
          this.wrap.style.setProperty('--tilt-x', `${tiltX.toFixed(2)}deg`);
          this.wrap.style.setProperty('--tilt-y', `${tiltY.toFixed(2)}deg`);
        }
      });

      this.btn.addEventListener('pointerleave', () => {
        this.isHovered = false;
        this.wrap.style.transition = 'transform 0.45s cubic-bezier(0.22, 1, 0.36, 1)';
        this.wrap.style.setProperty('--tilt-x', '0deg');
        this.wrap.style.setProperty('--tilt-y', '0deg');
        this.btn.style.setProperty('--mx', '50%');
        this.btn.style.setProperty('--my', '30%');
      });

      this.btn.addEventListener('click', (e) => {
        if (this.reduceMotion) return;
        const rect = this.btn.getBoundingClientRect();
        const cx = e.clientX ? e.clientX - rect.left : rect.width * 0.5;
        const cy = e.clientY ? e.clientY - rect.top : rect.height * 0.5;
        this.triggerBurst(cx + this.burstPad, cy + this.burstPad);
      });
    }

    triggerBurst(originX, originY) {
      const count = 28;
      for (let i = 0; i < count; i++) {
        const angle = (Math.PI * 2 * i) / count + (Math.random() - 0.5) * 0.35;
        const speed = 2.2 + Math.random() * 4.4;
        this.burstParticles.push({
          x: originX,
          y: originY,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          size: 0.9 + Math.random() * 1.4,
          alpha: 0.95,
          decay: 0.02 + Math.random() * 0.015,
          isCross: i % 4 === 0,
        });
      }
      if (!this.rafId && this.isVisible) {
        this.startLoop();
      }
    }

    applyRepulsion(baseX, baseY, particle) {
      let targetDx = 0;
      let targetDy = 0;
      if (this.isHovered && this.smoothX > -500) {
        const ox = baseX - this.smoothX;
        const oy = baseY - this.smoothY;
        const dist = Math.hypot(ox, oy);
        const radius = 60;
        if (dist < radius && dist > 0.01) {
          const strength = Math.pow((radius - dist) / radius, 1.35) * 34;
          targetDx = (ox / dist) * strength;
          targetDy = (oy / dist) * strength;
        } else if (dist <= 0.01) {
          targetDx = 18;
          targetDy = -18;
        }
      }
      particle.dx += (targetDx - particle.dx) * 0.22;
      particle.dy += (targetDy - particle.dy) * 0.22;
      return { x: baseX + particle.dx, y: baseY + particle.dy };
    }

    drawCrossGlint(ctx, x, y, r, alpha) {
      ctx.save();
      ctx.strokeStyle = `rgba(255, 255, 255, ${alpha})`;
      ctx.lineWidth = 1;
      const arm = r * 2.6;
      ctx.beginPath();
      ctx.moveTo(x - arm, y);
      ctx.lineTo(x + arm, y);
      ctx.moveTo(x, y - arm);
      ctx.lineTo(x, y + arm);
      ctx.stroke();
      ctx.fillStyle = `rgba(255, 255, 255, ${Math.min(1, alpha + 0.15)})`;
      ctx.beginPath();
      ctx.arc(x, y, r * 0.75, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    renderInner(t) {
      const ctx = this.ictx;
      const w = this.width;
      const h = this.height;
      ctx.clearRect(0, 0, w, h);

      if (this.isHovered) {
        if (this.smoothX < -500) {
          this.smoothX = this.mouseX;
          this.smoothY = this.mouseY;
        } else {
          this.smoothX += (this.mouseX - this.smoothX) * 0.35;
          this.smoothY += (this.mouseY - this.smoothY) * 0.35;
        }
      } else {
        this.smoothX = -999;
        this.smoothY = -999;
      }

      // 1. Twinkling background starfield
      for (const s of this.bgStars) {
        const bx = s.nx * w;
        const by = s.ny * h;
        const pos = this.applyRepulsion(bx, by, s);
        const tw = 0.65 + 0.35 * Math.sin(t * s.speed + s.phase);
        const alpha = s.baseAlpha * tw;
        ctx.fillStyle = `rgba(255, 255, 255, ${alpha.toFixed(3)})`;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }

      // 2. 3-Arm Spiral Galaxy Particles
      const cx = w * 0.36;
      const cy = h * 0.52;
      const rx = w * 0.52;
      const ry = h * 0.52;

      for (const p of this.spiralStars) {
        const theta = p.baseAngle + t * p.angularVel;
        const distNorm = Math.max(0.06, p.t + p.radialJitter);
        const bx = cx + Math.cos(theta) * distNorm * rx;
        const by = cy + Math.sin(theta) * distNorm * ry;
        const pos = this.applyRepulsion(bx, by, p);
        const tw = 0.7 + 0.3 * Math.sin(t * 2.1 + p.twinklePhase);
        const alpha = p.alpha * tw;

        if (p.isCross) {
          this.drawCrossGlint(ctx, pos.x, pos.y, p.size, alpha);
        } else {
          ctx.fillStyle = `rgba(244, 244, 246, ${alpha.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, p.size, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    renderBurst() {
      const ctx = this.bctx;
      const bw = this.width + this.burstPad * 2;
      const bh = this.height + this.burstPad * 2;
      ctx.clearRect(0, 0, bw, bh);

      for (let i = this.burstParticles.length - 1; i >= 0; i--) {
        const p = this.burstParticles[i];
        p.x += p.vx;
        p.y += p.vy;
        p.vx *= 0.96;
        p.vy *= 0.96;
        p.alpha -= p.decay;

        if (p.alpha <= 0) {
          this.burstParticles.splice(i, 1);
          continue;
        }

        if (p.isCross) {
          this.drawCrossGlint(ctx, p.x, p.y, p.size, p.alpha);
        } else {
          ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha.toFixed(3)})`;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }

    startLoop() {
      const tick = () => {
        if (!this.isVisible) {
          this.rafId = null;
          return;
        }
        this.time += 0.016;
        this.renderInner(this.time);
        if (this.burstParticles.length > 0) {
          this.renderBurst();
        } else {
          this.bctx.clearRect(0, 0, this.width + this.burstPad * 2, this.height + this.burstPad * 2);
        }
        this.rafId = requestAnimationFrame(tick);
      };
      this.rafId = requestAnimationFrame(tick);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-galaxy-tilt]').forEach((wrap) => {
      new GalaxyCursorButton(wrap);
    });
  });
})();
