/**
 * TinyHand Windows — Interactive Canvas Pointer Engine
 * High-performance 60 FPS HTML5 Canvas Telescopic Arm & 3D Hand Simulator
 */

class InteractivePointerStage {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');

    // State
    this.activeHand = 'astro';
    this.activeSize = 'M';
    this.isSpotlight = false;
    this.isDrawing = false;
    this.isSound = true;
    this.hasShadow = true;

    // Kinematics
    this.target = { x: 0, y: 0 };
    this.current = { x: 0, y: 0 };
    this.rodAnchor = { x: 0, y: 0 };
    this.isInside = false;

    // FX Collections
    this.ripples = [];
    this.bubbles = [];
    this.inkPaths = [];
    this.currentStroke = null;
    this.hasCustomInk = false;
    this.rainbowHue = 215;

    // Audio Pool
    this.audioPool = {};
    this.initAudio();

    // Hand Images Cache
    this.handImages = {};
    this.loadHandImage(this.activeHand);

    // Bindings
    this.resize = this.resize.bind(this);
    this.onMouseMove = this.onMouseMove.bind(this);
    this.onMouseDown = this.onMouseDown.bind(this);
    this.onMouseUp = this.onMouseUp.bind(this);
    this.onMouseEnter = this.onMouseEnter.bind(this);
    this.onMouseLeave = this.onMouseLeave.bind(this);
    this.loop = this.loop.bind(this);

    this.init();
  }

  init() {
    window.addEventListener('resize', this.resize);
    this.resize();

    // Rest pointer cleanly above/right of slide underline so Panel 2 copy stays unobstructed
    this.target = {
      x: this.displayWidth * 0.64,
      y: this.displayHeight * 0.30
    };
    this.current = { ...this.target };

    // Seed one subtle Chaikin-style sample annotation stroke on initial load
    this.seedSampleInk();

    this.canvas.addEventListener('mousemove', this.onMouseMove);
    this.canvas.addEventListener('mousedown', this.onMouseDown);
    this.canvas.addEventListener('mouseup', this.onMouseUp);
    this.canvas.addEventListener('mouseenter', this.onMouseEnter);
    this.canvas.addEventListener('mouseleave', this.onMouseLeave);

    this.canvas.addEventListener('touchmove', (e) => {
      e.preventDefault();
      const rect = this.canvas.getBoundingClientRect();
      const touch = e.touches[0];
      this.target.x = touch.clientX - rect.left;
      this.target.y = touch.clientY - rect.top;
    }, { passive: false });

    this.canvas.addEventListener('touchstart', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const touch = e.touches[0];
      this.target.x = touch.clientX - rect.left;
      this.target.y = touch.clientY - rect.top;
      this.current = { ...this.target };
      this.triggerTap(this.target.x, this.target.y);
    });

    requestAnimationFrame(this.loop);
  }

  seedSampleInk() {
    const w = this.displayWidth || 960;
    const h = this.displayHeight || 396;
    const isNarrow = w < 560;
    const sw = Math.min(w - (isNarrow ? 24 : 48), 660);
    const sh = isNarrow ? Math.min(h - 116, 224) : Math.min(h - 104, 260);
    const sx = (w - sw) / 2;
    const sy = isNarrow ? 16 : (h - sh) / 2 - 14;

    // Crisp cobalt underline highlight below slide headline
    const yBase = isNarrow ? sy + 72 : sy + 82;
    const xStart = sx + (isNarrow ? 16 : 24);
    const xEnd = isNarrow ? sx + Math.min(sw - 32, 160) : sx + Math.min(272, sw * 0.44);
    const pts = [];
    const steps = 10;
    for (let i = 0; i <= steps; i++) {
      const t = i / steps;
      pts.push({
        x: xStart + (xEnd - xStart) * t,
        y: yBase + Math.sin(t * Math.PI) * 3
      });
    }
    this.inkPaths = [{ color: '#3B82F6', points: pts }];
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.displayWidth = rect.width;
    this.displayHeight = rect.height;

    this.rodAnchor = {
      x: this.displayWidth * 0.84,
      y: this.displayHeight + 40
    };

    if (!this.isInside) {
      this.target = {
        x: this.displayWidth * 0.64,
        y: this.displayHeight * 0.30
      };
      this.current = { ...this.target };
    }

    if (!this.hasCustomInk && this.inkPaths.length > 0) {
      this.seedSampleInk();
    }
  }

  initAudio() {
    const sounds = ['boop', 'click', 'pop', 'thock'];
    sounds.forEach(name => {
      const audio = new Audio(`assets/sounds/tap_${name}.wav`);
      audio.volume = 0.5;
      this.audioPool[name] = audio;
    });
  }

  playTapSound() {
    if (!this.isSound) return;
    try {
      const keys = ['boop', 'click', 'pop', 'thock'];
      const chosen = keys[Math.floor(Math.random() * keys.length)];
      const audio = this.audioPool[chosen];
      if (audio) {
        audio.currentTime = 0;
        audio.play().catch(() => {});
      }
    } catch (e) {}
  }

  loadHandImage(name) {
    if (this.handImages[name]) return;
    const img = new Image();
    img.src = `assets/hands/hand_${name}.webp`;
    img.onerror = () => {
      img.src = `assets/hands/hand_${name}.png`;
    };
    this.handImages[name] = img;
  }

  setHand(name) {
    this.activeHand = name;
    this.loadHandImage(name);
  }

  toggleSpotlight() {
    this.isSpotlight = !this.isSpotlight;
    return this.isSpotlight;
  }

  toggleDraw() {
    this.isDrawing = !this.isDrawing;
    return this.isDrawing;
  }

  toggleSound() {
    this.isSound = !this.isSound;
    return this.isSound;
  }

  clearInk() {
    this.inkPaths = [];
  }

  onMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    this.target.x = e.clientX - rect.left;
    this.target.y = e.clientY - rect.top;

    if (this.isDrawing && this.currentStroke) {
      this.currentStroke.points.push({ x: this.target.x, y: this.target.y });
    }
  }

  onMouseEnter() {
    this.isInside = true;
  }

  onMouseLeave() {
    this.isInside = false;
    this.currentStroke = null;
  }

  onMouseDown(e) {
    const rect = this.canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    this.triggerTap(x, y);

    if (this.isDrawing) {
      this.hasCustomInk = true;
      this.rainbowHue = (this.rainbowHue + 40) % 360;
      this.currentStroke = {
        color: `hsl(${this.rainbowHue}, 88%, 62%)`,
        points: [{ x, y }]
      };
      this.inkPaths.push(this.currentStroke);
    }
  }

  onMouseUp() {
    this.currentStroke = null;
  }

  triggerTap(x, y) {
    this.playTapSound();

    this.ripples.push({
      x,
      y,
      radius: 5,
      maxRadius: 44,
      alpha: 0.85
    });

    const words = ['BOOP', 'POP', 'TAP', 'CLICK', 'SNAP'];
    const word = words[Math.floor(Math.random() * words.length)];
    this.bubbles.push({
      x,
      y: y - 24,
      word,
      alpha: 1,
      scale: 0.78,
      vy: -1.1
    });
  }

  getHandScaleFactor() {
    switch (this.activeSize) {
      case 'XS': return 0.55;
      case 'S': return 0.70;
      case 'M': return 0.86;
      case 'L': return 1.10;
      case 'XL': return 1.35;
      default: return 0.86;
    }
  }

  loop() {
    const ease = 0.22;
    this.current.x += (this.target.x - this.current.x) * ease;
    this.current.y += (this.target.y - this.current.y) * ease;

    const ctx = this.ctx;
    const w = this.displayWidth;
    const h = this.displayHeight;

    ctx.clearRect(0, 0, w, h);

    this.renderSlideMockup(ctx, w, h);
    this.renderInk(ctx);

    if (this.isSpotlight) {
      this.renderSpotlight(ctx, w, h);
    }

    this.renderRipples(ctx);
    this.renderPointer(ctx);
    this.renderBubbles(ctx);

    requestAnimationFrame(this.loop);
  }

  renderSlideMockup(ctx, w, h) {
    const isNarrow = w < 560;
    const sw = Math.min(w - (isNarrow ? 24 : 48), 660);
    const sh = isNarrow ? Math.min(h - 116, 224) : Math.min(h - 104, 260);
    const sx = (w - sw) / 2;
    const sy = isNarrow ? 16 : (h - sh) / 2 - 14;
    const pad = isNarrow ? 16 : 24;

    ctx.save();

    // Slide Card Surface
    ctx.fillStyle = '#0E1118';
    ctx.strokeStyle = 'rgba(238, 240, 245, 0.10)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(sx, sy, sw, sh, 12);
    ctx.fill();
    ctx.stroke();

    // Clip slide internals cleanly so narrow viewports never bleed outside frame
    ctx.save();
    ctx.beginPath();
    ctx.roundRect(sx, sy, sw, sh, 12);
    ctx.clip();

    // Slide Top Header Bar
    ctx.fillStyle = '#141822';
    ctx.fillRect(sx, sy, sw, 34);

    ctx.fillStyle = '#7A8296';
    ctx.font = '500 12px "JetBrains Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(isNarrow ? 'Slide 01 · Win32 preview' : 'Slide 01 · Kinematics & overlay preview', sx + pad, sy + 21);

    ctx.fillStyle = '#EEF0F5';
    ctx.font = isNarrow ? '500 17px "Familjen Grotesk", sans-serif' : '500 20px "Familjen Grotesk", sans-serif';
    ctx.fillText(isNarrow ? 'Zero-lag 3D pointer' : 'Zero-lag Win32 presentation pointer', sx + pad, sy + (isNarrow ? 60 : 66));

    ctx.fillStyle = '#A3A9B8';
    ctx.font = isNarrow ? '400 12px "Inter", sans-serif' : '400 13px "Inter", sans-serif';
    ctx.fillText(
      isNarrow ? 'Steer hand or click to test sound & ink.' : 'Steer the 3D hand across elements or click to test sound and ink.',
      sx + pad,
      sy + (isNarrow ? 92 : 100)
    );

    // Two clean content cards inside slide
    const gap = isNarrow ? 10 : 16;
    const pw = (sw - pad * 2 - gap) / 2;
    const ph = isNarrow ? 92 : 104;
    const py = sy + (isNarrow ? 114 : 122);

    // Panel 1
    const p1x = sx + pad;
    ctx.fillStyle = '#11141C';
    ctx.strokeStyle = 'rgba(238, 240, 245, 0.10)';
    ctx.beginPath();
    ctx.roundRect(p1x, py, pw, ph, 8);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#60A5FA';
    ctx.font = '500 11.5px "JetBrains Mono", monospace';
    ctx.fillText('01 · Pointers', p1x + 12, py + 24);

    ctx.fillStyle = '#EEF0F5';
    ctx.font = isNarrow ? '500 13px "Familjen Grotesk", sans-serif' : '500 15px "Familjen Grotesk", sans-serif';
    ctx.fillText(isNarrow ? '36 3D hands' : '36 sculpted 3D hands', p1x + 12, py + 48);

    ctx.fillStyle = '#7A8296';
    ctx.font = '400 11.5px "Inter", sans-serif';
    ctx.fillText(isNarrow ? 'Pick style below' : 'Pick any hand style in the grid below', p1x + 12, py + 70);

    // Panel 2
    const p2x = p1x + pw + gap;
    ctx.fillStyle = '#11141C';
    ctx.strokeStyle = 'rgba(238, 240, 245, 0.10)';
    ctx.beginPath();
    ctx.roundRect(p2x, py, pw, ph, 8);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = '#4CC38A';
    ctx.font = '500 11.5px "JetBrains Mono", monospace';
    ctx.fillText('02 · Tap target', p2x + 12, py + 24);

    ctx.fillStyle = '#EEF0F5';
    ctx.font = isNarrow ? '500 13px "Familjen Grotesk", sans-serif' : '500 15px "Familjen Grotesk", sans-serif';
    ctx.fillText(isNarrow ? 'Sound & pop' : 'Click for sound and pop', p2x + 12, py + 48);

    ctx.fillStyle = '#7A8296';
    ctx.font = '400 11.5px "Inter", sans-serif';
    ctx.fillText(isNarrow ? 'WAV + ripple ring' : 'Plays acoustic WAV + ripple ring', p2x + 12, py + 70);

    ctx.restore();
    ctx.restore();
  }

  renderSpotlight(ctx, w, h) {
    const radius = 104;
    const cx = this.current.x;
    const cy = this.current.y;

    ctx.save();
    const grad = ctx.createRadialGradient(cx, cy, radius * 0.45, cx, cy, radius);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    grad.addColorStop(0.75, 'rgba(7, 8, 13, 0.58)');
    grad.addColorStop(1, 'rgba(7, 8, 13, 0.86)');

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(96, 165, 250, 0.45)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.restore();
  }

  renderInk(ctx) {
    if (this.inkPaths.length === 0) return;

    ctx.save();
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    for (const stroke of this.inkPaths) {
      if (stroke.points.length < 2) continue;

      ctx.beginPath();
      ctx.moveTo(stroke.points[0].x, stroke.points[0].y);

      for (let i = 1; i < stroke.points.length; i++) {
        const xc = (stroke.points[i].x + stroke.points[i - 1].x) / 2;
        const yc = (stroke.points[i].y + stroke.points[i - 1].y) / 2;
        ctx.quadraticCurveTo(stroke.points[i - 1].x, stroke.points[i - 1].y, xc, yc);
      }

      ctx.strokeStyle = stroke.color;
      ctx.lineWidth = 4;
      ctx.stroke();
    }
    ctx.restore();
  }

  renderRipples(ctx) {
    for (let i = this.ripples.length - 1; i >= 0; i--) {
      const r = this.ripples[i];
      r.radius += 2.2;
      r.alpha -= 0.035;

      if (r.alpha <= 0 || r.radius >= r.maxRadius) {
        this.ripples.splice(i, 1);
        continue;
      }

      ctx.save();
      ctx.beginPath();
      ctx.arc(r.x, r.y, r.radius, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(96, 165, 250, ${r.alpha})`;
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.restore();
    }
  }

  renderBubbles(ctx) {
    for (let i = this.bubbles.length - 1; i >= 0; i--) {
      const b = this.bubbles[i];
      b.y += b.vy;
      b.scale = Math.min(1.0, b.scale + 0.04);
      b.alpha -= 0.022;

      if (b.alpha <= 0) {
        this.bubbles.splice(i, 1);
        continue;
      }

      ctx.save();
      ctx.translate(b.x, b.y);
      ctx.scale(b.scale, b.scale);

      ctx.font = '500 12px "JetBrains Mono", monospace';
      const textWidth = ctx.measureText(b.word).width;
      const bw = textWidth + 16;
      const bh = 22;

      ctx.fillStyle = `rgba(37, 99, 235, ${b.alpha})`;
      ctx.beginPath();
      ctx.roundRect(-bw / 2, -bh / 2, bw, bh, 6);
      ctx.fill();

      ctx.fillStyle = `rgba(248, 250, 252, ${b.alpha})`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(b.word, 0, 0);

      ctx.restore();
    }
  }

  renderPointer(ctx) {
    const tipX = this.current.x;
    const tipY = this.current.y;
    const anchorX = this.rodAnchor.x;
    const anchorY = this.rodAnchor.y;

    const dx = tipX - anchorX;
    const dy = tipY - anchorY;
    const angle = Math.atan2(dy, dx);
    const scale = this.getHandScaleFactor();

    ctx.save();

    if (this.hasShadow) {
      ctx.beginPath();
      ctx.moveTo(anchorX + 6, anchorY + 6);
      ctx.lineTo(tipX + 6, tipY + 6);
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.45)';
      ctx.lineWidth = 12 * scale;
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    const rodGrad = ctx.createLinearGradient(
      anchorX - Math.sin(angle) * 6,
      anchorY + Math.cos(angle) * 6,
      anchorX + Math.sin(angle) * 6,
      anchorY - Math.cos(angle) * 6
    );
    rodGrad.addColorStop(0, '#1C212B');
    rodGrad.addColorStop(0.5, '#353D4E');
    rodGrad.addColorStop(1, '#11151C');

    ctx.beginPath();
    ctx.moveTo(anchorX, anchorY);
    ctx.lineTo(tipX, tipY);
    ctx.strokeStyle = rodGrad;
    ctx.lineWidth = 11 * scale;
    ctx.lineCap = 'round';
    ctx.stroke();

    ctx.beginPath();
    const collarX = tipX - Math.cos(angle) * (16 * scale);
    const collarY = tipY - Math.sin(angle) * (16 * scale);
    ctx.arc(collarX, collarY, 6 * scale, 0, Math.PI * 2);
    ctx.fillStyle = '#64748B';
    ctx.fill();

    ctx.restore();

    if (this.activeHand === 'cat_paw') {
      this.renderCatPaw(ctx, tipX, tipY, angle, scale);
    } else if (this.activeHand === 'magic_wand') {
      this.renderMagicWand(ctx, tipX, tipY, scale);
    } else if (this.activeHand === 'boxing_glove') {
      this.renderBoxingGlove(ctx, tipX, tipY, angle, scale);
    } else if (this.activeHand === 'laser') {
      this.renderLaser(ctx, tipX, tipY);
    } else {
      this.renderHandImage(ctx, tipX, tipY, angle, scale);
    }
  }

  renderHandImage(ctx, tipX, tipY, angle, scale) {
    const img = this.handImages[this.activeHand];
    if (!img || !img.complete || img.naturalWidth === 0) return;

    ctx.save();
    ctx.translate(tipX, tipY);
    ctx.rotate(angle + Math.PI / 2);

    const baseSize = 84 * scale;

    if (this.hasShadow) {
      ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
      ctx.shadowBlur = 12;
      ctx.shadowOffsetX = 4;
      ctx.shadowOffsetY = 8;
    }

    ctx.drawImage(img, -baseSize * 0.45, -baseSize * 0.08, baseSize, baseSize);
    ctx.restore();
  }

  renderCatPaw(ctx, x, y, angle, scale) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle + Math.PI / 2);
    const s = 1.25 * scale;
    ctx.scale(s, s);

    ctx.fillStyle = '#EEF0F5';
    ctx.beginPath();
    ctx.ellipse(0, 10, 18, 16, 0, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#F472B6';
    ctx.beginPath();
    ctx.ellipse(0, 13, 9, 7, 0, 0, Math.PI * 2);
    ctx.fill();

    [-10, -4, 4, 10].forEach(tx => {
      ctx.beginPath();
      ctx.arc(tx, 0, 3.5, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.restore();
  }

  renderMagicWand(ctx, x, y, scale) {
    ctx.save();
    ctx.translate(x, y);

    ctx.fillStyle = '#38BDF8';
    ctx.beginPath();
    ctx.arc(0, 0, 8 * scale, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#F8FAFC';
    ctx.beginPath();
    ctx.arc(0, 0, 3.5 * scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  renderBoxingGlove(ctx, x, y, angle, scale) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle + Math.PI / 2);
    ctx.fillStyle = '#DC2626';
    ctx.beginPath();
    ctx.roundRect(-16 * scale, -10 * scale, 32 * scale, 36 * scale, 12 * scale);
    ctx.fill();
    ctx.restore();
  }

  renderLaser(ctx, x, y) {
    ctx.save();
    ctx.fillStyle = '#EF4444';
    ctx.beginPath();
    ctx.arc(x, y, 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#F8FAFC';
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

window.InteractivePointerStage = InteractivePointerStage;
