/**
 * Wajji TinyHand PRO — Interactive Canvas Pointer Engine
 * High-performance 60 FPS HTML5 Canvas Telescopic Arm & 3D Hand Simulator
 */

class InteractivePointerStage {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');

    // State
    this.activeHand = 'astro';
    this.activeSize = 'M'; // XS, S, M, L, XL
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
    this.rainbowHue = 0;

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

    // Default center position
    this.target = { x: this.canvas.width * 0.5, y: this.canvas.height * 0.45 };
    this.current = { ...this.target };

    this.canvas.addEventListener('mousemove', this.onMouseMove);
    this.canvas.addEventListener('mousedown', this.onMouseDown);
    this.canvas.addEventListener('mouseup', this.onMouseUp);
    this.canvas.addEventListener('mouseenter', this.onMouseEnter);
    this.canvas.addEventListener('mouseleave', this.onMouseLeave);

    // Touch support for mobile/tablet
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

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.displayWidth = rect.width;
    this.displayHeight = rect.height;

    // Anchor rod to bottom-right quadrant
    this.rodAnchor = {
      x: this.displayWidth * 0.85,
      y: this.displayHeight + 40
    };
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
    } catch(e) {}
  }

  loadHandImage(name) {
    if (this.handImages[name]) return;
    const img = new Image();
    // Try webp first, fallback to png
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
      this.rainbowHue = (this.rainbowHue + 40) % 360;
      this.currentStroke = {
        color: `hsl(${this.rainbowHue}, 100%, 65%)`,
        points: [{ x, y }]
      };
      this.inkPaths.push(this.currentStroke);
    }
  }

  onMouseUp() {
    this.currentStroke = null;
  }

  triggerTap(x, y) {
    // Sound
    this.playTapSound();

    // Click Ripple
    this.ripples.push({
      x,
      y,
      radius: 5,
      maxRadius: 45,
      alpha: 0.9
    });

    // Comic Pop Bubble
    const words = ['BOOP!', 'POP!', 'POW!', 'CLICK!', 'WOW!', 'SNAP!'];
    const word = words[Math.floor(Math.random() * words.length)];
    this.bubbles.push({
      x,
      y: y - 25,
      word,
      alpha: 1,
      scale: 0.7,
      vy: -1.2
    });
  }

  getHandScaleFactor() {
    switch(this.activeSize) {
      case 'XS': return 0.55;
      case 'S':  return 0.70;
      case 'M':  return 0.88;
      case 'L':  return 1.10;
      case 'XL': return 1.35;
      default:   return 0.88;
    }
  }

  loop() {
    // Smooth kinematic easing
    const ease = 0.22;
    this.current.x += (this.target.x - this.current.x) * ease;
    this.current.y += (this.target.y - this.current.y) * ease;

    const ctx = this.ctx;
    const w = this.displayWidth;
    const h = this.displayHeight;

    ctx.clearRect(0, 0, w, h);

    // 1. Draw Inks
    this.renderInk(ctx);

    // 2. Draw Spotlight Backdrop if active
    if (this.isSpotlight) {
      this.renderSpotlight(ctx, w, h);
    }

    // 3. Draw Ripples
    this.renderRipples(ctx);

    // 4. Draw Telescopic Rod & Hand
    this.renderPointer(ctx);

    // 5. Draw Comic Pop Bubbles
    this.renderBubbles(ctx);

    requestAnimationFrame(this.loop);
  }

  renderSpotlight(ctx, w, h) {
    const radius = 110;
    const cx = this.current.x;
    const cy = this.current.y;

    ctx.save();
    // Dark vignette
    const grad = ctx.createRadialGradient(cx, cy, radius * 0.4, cx, cy, radius);
    grad.addColorStop(0, 'rgba(0, 0, 0, 0)');
    grad.addColorStop(0.7, 'rgba(5, 7, 12, 0.55)');
    grad.addColorStop(1, 'rgba(5, 7, 12, 0.85)');

    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);

    // Golden spotlight ring
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(59, 130, 246, 0.35)';
    ctx.lineWidth = 2;
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
      ctx.lineWidth = 5;
      ctx.shadowColor = stroke.color;
      ctx.shadowBlur = 8;
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
      ctx.strokeStyle = `rgba(59, 130, 246, ${r.alpha})`;
      ctx.lineWidth = 2.5;
      ctx.stroke();
      ctx.restore();
    }
  }

  renderBubbles(ctx) {
    for (let i = this.bubbles.length - 1; i >= 0; i--) {
      const b = this.bubbles[i];
      b.y += b.vy;
      b.scale = Math.min(1.0, b.scale + 0.04);
      b.alpha -= 0.02;

      if (b.alpha <= 0) {
        this.bubbles.splice(i, 1);
        continue;
      }

      ctx.save();
      ctx.translate(b.x, b.y);
      ctx.scale(b.scale, b.scale);

      // Bubble Capsule
      ctx.font = 'bold 12px "Inter", sans-serif';
      const textWidth = ctx.measureText(b.word).width;
      const padX = 10;
      const padY = 5;
      const bw = textWidth + padX * 2;
      const bh = 22;

      ctx.fillStyle = `rgba(37, 99, 235, ${b.alpha * 0.95})`;
      ctx.shadowColor = 'rgba(59, 130, 246, 0.5)';
      ctx.shadowBlur = 10;

      // Rounded rect
      ctx.beginPath();
      ctx.roundRect(-bw / 2, -bh / 2, bw, bh, 10);
      ctx.fill();

      // Text
      ctx.fillStyle = `rgba(255, 255, 255, ${b.alpha})`;
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

    // Telescopic Rod
    ctx.save();

    // Rod Shadow
    if (this.hasShadow) {
      ctx.beginPath();
      ctx.moveTo(anchorX + 8, anchorY + 8);
      ctx.lineTo(tipX + 8, tipY + 8);
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.4)';
      ctx.lineWidth = 14 * scale;
      ctx.lineCap = 'round';
      ctx.stroke();
    }

    // Rod Body (Dark Metal Gradient)
    const rodGrad = ctx.createLinearGradient(
      anchorX - Math.sin(angle) * 7,
      anchorY + Math.cos(angle) * 7,
      anchorX + Math.sin(angle) * 7,
      anchorY - Math.cos(angle) * 7
    );
    rodGrad.addColorStop(0, '#1C212B');
    rodGrad.addColorStop(0.5, '#353D4E');
    rodGrad.addColorStop(1, '#11151C');

    ctx.beginPath();
    ctx.moveTo(anchorX, anchorY);
    ctx.lineTo(tipX, tipY);
    ctx.strokeStyle = rodGrad;
    ctx.lineWidth = 12 * scale;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Chrome Collar at connection tip
    ctx.beginPath();
    const collarX = tipX - Math.cos(angle) * (18 * scale);
    const collarY = tipY - Math.sin(angle) * (18 * scale);
    ctx.arc(collarX, collarY, 7 * scale, 0, Math.PI * 2);
    ctx.fillStyle = '#64748B';
    ctx.fill();

    ctx.restore();

    // Render Hand Artwork or Special Vector Pointer
    if (this.activeHand === 'cat_paw') {
      this.renderCatPaw(ctx, tipX, tipY, angle, scale);
    } else if (this.activeHand === 'magic_wand') {
      this.renderMagicWand(ctx, tipX, tipY, angle, scale);
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
    // Align hand along rod angle
    ctx.rotate(angle + Math.PI / 2);

    const baseSize = 85 * scale;

    // Drop shadow
    if (this.hasShadow) {
      ctx.shadowColor = 'rgba(0, 0, 0, 0.55)';
      ctx.shadowBlur = 14;
      ctx.shadowOffsetX = 6;
      ctx.shadowOffsetY = 10;
    }

    // Draw hand with tip centered at (0, 0)
    ctx.drawImage(img, -baseSize * 0.45, -baseSize * 0.08, baseSize, baseSize);

    ctx.restore();
  }

  renderCatPaw(ctx, x, y, angle, scale) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle + Math.PI / 2);
    const s = 1.3 * scale;
    ctx.scale(s, s);

    // Fur Pad
    ctx.fillStyle = '#FFFFFF';
    ctx.shadowColor = 'rgba(0,0,0,0.3)';
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.ellipse(0, 10, 18, 16, 0, 0, Math.PI * 2);
    ctx.fill();

    // Pink Toe Pads
    ctx.fillStyle = '#F472B6';
    ctx.beginPath();
    ctx.ellipse(0, 13, 9, 7, 0, 0, Math.PI * 2);
    ctx.fill();

    const toes = [-10, -4, 4, 10];
    toes.forEach(tx => {
      ctx.beginPath();
      ctx.arc(tx, 0, 3.5, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.restore();
  }

  renderMagicWand(ctx, x, y, angle, scale) {
    ctx.save();
    ctx.translate(x, y);
    // Glowing star tip
    ctx.fillStyle = '#FBBF24';
    ctx.shadowColor = '#F59E0B';
    ctx.shadowBlur = 18;
    ctx.beginPath();
    ctx.arc(0, 0, 9 * scale, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.arc(0, 0, 4 * scale, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  renderBoxingGlove(ctx, x, y, angle, scale) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(angle + Math.PI / 2);
    ctx.fillStyle = '#EF4444';
    ctx.shadowColor = 'rgba(0,0,0,0.4)';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.roundRect(-16 * scale, -10 * scale, 32 * scale, 36 * scale, 14 * scale);
    ctx.fill();
    ctx.restore();
  }

  renderLaser(ctx, x, y) {
    ctx.save();
    ctx.fillStyle = '#EF4444';
    ctx.shadowColor = '#F87171';
    ctx.shadowBlur = 20;
    ctx.beginPath();
    ctx.arc(x, y, 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#FFFFFF';
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

window.InteractivePointerStage = InteractivePointerStage;
