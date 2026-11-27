/**
 * TinyHand Windows — Landing Page Main Controller
 */

const HAND_CATALOG = [
  { id: 'astro', name: 'Astro', category: 'special' },
  { id: 'glass', name: 'Frosted Glass', category: 'material' },
  { id: 'robot', name: 'Cyber Robot', category: 'special' },
  { id: 'cookie', name: 'Choco Cookie', category: 'hands' },
  { id: 'cactus', name: 'Prickly Cactus', category: 'hands' },
  { id: 'holo', name: 'Holographic', category: 'special' },
  { id: 'black', name: 'Obsidian Black', category: 'material' },
  { id: 'blue', name: 'Azure Blue', category: 'hands' },
  { id: 'choco', name: 'Chocolate Bar', category: 'hands' },
  { id: 'chrome', name: 'Liquid Chrome', category: 'material' },
  { id: 'cloud', name: 'Puffy Cloud', category: 'hands' },
  { id: 'coral', name: 'Living Coral', category: 'hands' },
  { id: 'fuzzy', name: 'Fuzzy Wool', category: 'material' },
  { id: 'glove', name: 'White Glove', category: 'hands' },
  { id: 'grass', name: 'Fresh Grass', category: 'hands' },
  { id: 'jelly', name: 'Jelly Candy', category: 'hands' },
  { id: 'knit', name: 'Knitted Yarn', category: 'material' },
  { id: 'lava', name: 'Molten Lava', category: 'special' },
  { id: 'lavender', name: 'Soft Lavender', category: 'hands' },
  { id: 'leaf', name: 'Spring Leaf', category: 'hands' },
  { id: 'lemon', name: 'Citrus Lemon', category: 'hands' },
  { id: 'lowpoly', name: 'Low Poly Facets', category: 'special' },
  { id: 'marble', name: 'White Marble', category: 'material' },
  { id: 'mech', name: 'Mechanical Arm', category: 'special' },
  { id: 'mint', name: 'Cool Mint', category: 'hands' },
  { id: 'monster', name: 'Friendly Monster', category: 'hands' },
  { id: 'neon', name: 'Cyberpunk Neon', category: 'special' },
  { id: 'pastel', name: 'Pastel Dream', category: 'hands' },
  { id: 'pink', name: 'Bubblegum Pink', category: 'hands' },
  { id: 'pixel', name: '8-Bit Pixel', category: 'special' },
  { id: 'plush', name: 'Teddy Plush', category: 'material' },
  { id: 'skeleton', name: 'Spooky Bones', category: 'special' },
  { id: 'space', name: 'Deep Nebula', category: 'special' },
  { id: 'terrazzo', name: 'Modern Terrazzo', category: 'material' },
  { id: 'water', name: 'Crystal Water', category: 'special' },
  { id: 'wood', name: 'Carved Wood', category: 'material' }
];

const VECTOR_ICONS_SVG = {
  cat_paw: `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="4" r="2"/><circle cx="18" cy="8" r="2"/><circle cx="20" cy="16" r="2"/><path d="M9 10a5 5 0 0 1 5 5v3.5a3.5 3.5 0 0 1-6.84 1.045Q6.52 17.48 4.46 16.84A3.5 3.5 0 0 1 5.5 10Z"/></svg>`,
  magic_wand: `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 4V2"/><path d="M15 16v-2"/><path d="M8 9h2"/><path d="M20 9h2"/><path d="M17.8 11.8 19 13"/><path d="M15 9h.01"/><path d="M17.8 6.2 19 5"/><path d="m3 21 9-9"/><path d="M12.2 6.2 11 5"/></svg>`,
  boxing_glove: `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="6" y="4" width="12" height="12" rx="5"/><path d="M8 16v3a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-3"/><path d="M6 10H4a1 1 0 0 0-1 1v2a2 2 0 0 0 2 2h1"/></svg>`,
  laser: `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="12" cy="12" r="7" stroke="#EF4444"/><circle cx="12" cy="12" r="3" fill="#EF4444" stroke="none"/></svg>`
};

const SPECIAL_FX_POINTERS = [
  { id: 'cat_paw', name: 'Cat Paw', category: 'fx' },
  { id: 'magic_wand', name: 'Magic Wand', category: 'fx' },
  { id: 'boxing_glove', name: 'Boxing Glove', category: 'fx' },
  { id: 'laser', name: 'Laser Dot', category: 'fx' }
];

const SOUND_ICON_ON = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>`;
const SOUND_ICON_OFF = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>`;

document.addEventListener('DOMContentLoaded', () => {
  // 1. Initialize Hero Interactive Stage
  const heroStage = new InteractivePointerStage('heroStageCanvas');

  // 2. Bind HUD Controls on Stage
  const btnSpotlight = document.getElementById('stageBtnSpotlight');
  const btnDraw = document.getElementById('stageBtnDraw');
  const btnSound = document.getElementById('stageBtnSound');
  const btnClear = document.getElementById('stageBtnClear');
  const handIndicator = document.getElementById('stageActiveHandName');

  if (btnSpotlight) {
    btnSpotlight.addEventListener('click', () => {
      const active = heroStage.toggleSpotlight();
      btnSpotlight.classList.toggle('active', active);
      btnSpotlight.setAttribute('aria-pressed', String(active));
    });
  }

  if (btnDraw) {
    btnDraw.addEventListener('click', () => {
      const active = heroStage.toggleDraw();
      btnDraw.classList.toggle('active', active);
      btnDraw.setAttribute('aria-pressed', String(active));
    });
  }

  if (btnSound) {
    btnSound.addEventListener('click', () => {
      const active = heroStage.toggleSound();
      btnSound.classList.toggle('active', active);
      btnSound.setAttribute('aria-pressed', String(active));
      btnSound.innerHTML = `${active ? SOUND_ICON_ON : SOUND_ICON_OFF}<span>${active ? 'Sound: On' : 'Muted'}</span>`;
    });
  }

  if (btnClear) {
    btnClear.addEventListener('click', () => {
      heroStage.clearInk();
    });
  }

  // 3. Render Hand Gallery Grid
  const galleryGrid = document.getElementById('galleryGrid');
  const filterTabs = document.querySelectorAll('.filter-tab');

  function renderGallery(filter = 'all') {
    if (!galleryGrid) return;
    galleryGrid.innerHTML = '';

    let items = [];
    if (filter === 'all') {
      items = [...HAND_CATALOG, ...SPECIAL_FX_POINTERS];
    } else if (filter === 'hands') {
      items = HAND_CATALOG.filter(h => h.category === 'hands');
    } else if (filter === 'material') {
      items = HAND_CATALOG.filter(h => h.category === 'material');
    } else if (filter === 'special') {
      items = HAND_CATALOG.filter(h => h.category === 'special');
    } else if (filter === 'fx') {
      items = SPECIAL_FX_POINTERS;
    }

    items.forEach(item => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = `hand-tile ${heroStage.activeHand === item.id ? 'selected' : ''}`;
      card.dataset.id = item.id;

      if (item.category === 'fx') {
        card.innerHTML = `
          <div class="hand-tile-vector">${VECTOR_ICONS_SVG[item.id] || ''}</div>
          <div class="hand-tile-name">${item.name}</div>
          <div class="hand-tile-sub">Vector FX</div>
        `;
      } else {
        card.innerHTML = `
          <picture>
            <source srcset="assets/hands/hand_${item.id}.webp" type="image/webp">
            <img src="assets/hands/hand_${item.id}.png" alt="${item.name} pointer" decoding="async">
          </picture>
          <div class="hand-tile-name">${item.name}</div>
          <div class="hand-tile-sub">3D hand</div>
        `;
      }

      card.addEventListener('click', () => {
        document.querySelectorAll('.hand-tile').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');

        heroStage.setHand(item.id);
        heroStage.playTapSound();

        if (handIndicator) {
          handIndicator.textContent = item.name;
        }

        const stageCanvas = document.getElementById('heroStageCanvas');
        if (stageCanvas) {
          const rect = stageCanvas.getBoundingClientRect();
          if (rect.top < -80 || rect.bottom > window.innerHeight + 80) {
            const wrap = document.getElementById('playgroundWrap');
            if (wrap) wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }
      });

      galleryGrid.appendChild(card);
    });
  }

  renderGallery('all');

  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      renderGallery(tab.dataset.filter);
    });
  });

  // 4. Bento Interactive Ink Pad (Pre-seeded Chaikin curve on initial load)
  const inkCanvas = document.getElementById('bentoInkPad');
  if (inkCanvas) {
    const ictx = inkCanvas.getContext('2d');
    let isDrawing = false;
    let bentoHue = 215;
    let cssW = 0;
    let cssH = 0;

    function drawSampleSpline() {
      if (cssW <= 0 || cssH <= 0) return;
      ictx.save();
      ictx.beginPath();
      const padX = 36;
      const midY = cssH * 0.52;
      const span = cssW - padX * 2;
      ictx.moveTo(padX, midY + 18);
      ictx.bezierCurveTo(
        padX + span * 0.25, midY - 46,
        padX + span * 0.52, midY + 48,
        padX + span * 0.88, midY - 22
      );
      ictx.strokeStyle = '#3B82F6';
      ictx.lineWidth = 4;
      ictx.lineCap = 'round';
      ictx.lineJoin = 'round';
      ictx.stroke();

      // Quiet annotation arrow & label
      ictx.fillStyle = '#7A8296';
      ictx.font = '500 12px "JetBrains Mono", monospace';
      ictx.fillText('Drag to sketch smoothed curve', padX, cssH - 18);
      ictx.restore();
    }

    function resizeBentoCanvas() {
      const rect = inkCanvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      cssW = rect.width;
      cssH = rect.height;
      inkCanvas.width = rect.width * dpr;
      inkCanvas.height = rect.height * dpr;
      ictx.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawSampleSpline();
    }

    resizeBentoCanvas();
    window.addEventListener('resize', resizeBentoCanvas);

    inkCanvas.addEventListener('mousedown', (e) => {
      isDrawing = true;
      const rect = inkCanvas.getBoundingClientRect();
      ictx.beginPath();
      ictx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
      bentoHue = (bentoHue + 28) % 360;
    });

    inkCanvas.addEventListener('mousemove', (e) => {
      if (!isDrawing) return;
      const rect = inkCanvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      ictx.strokeStyle = `hsl(${bentoHue}, 85%, 62%)`;
      ictx.lineWidth = 4;
      ictx.lineCap = 'round';
      ictx.lineJoin = 'round';
      ictx.lineTo(x, y);
      ictx.stroke();
    });

    window.addEventListener('mouseup', () => {
      isDrawing = false;
    });

    const btnClearBento = document.getElementById('bentoClearInk');
    if (btnClearBento) {
      btnClearBento.addEventListener('click', () => {
        ictx.clearRect(0, 0, cssW, cssH);
      });
    }
  }

  // 5. Interactive Bento Spotlight Reveal
  const spotlightPanel = document.getElementById('bentoSpotlightPanel');
  if (spotlightPanel) {
    spotlightPanel.addEventListener('mousemove', (e) => {
      const rect = spotlightPanel.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      spotlightPanel.style.setProperty('--spot-x', `${x.toFixed(1)}%`);
      spotlightPanel.style.setProperty('--spot-y', `${y.toFixed(1)}%`);
    });
    spotlightPanel.addEventListener('mouseleave', () => {
      spotlightPanel.style.setProperty('--spot-x', '50%');
      spotlightPanel.style.setProperty('--spot-y', '50%');
    });
  }

  // 6. Comic Pop Interactive Button in Bento
  const comicDemoTile = document.getElementById('comicDemoTile');
  if (comicDemoTile) {
    const popAudio = new Audio('assets/sounds/tap_pop.wav');
    comicDemoTile.addEventListener('click', (e) => {
      popAudio.currentTime = 0;
      popAudio.play().catch(() => {});

      const rect = comicDemoTile.getBoundingClientRect();
      const px = e.clientX ? e.clientX - rect.left : rect.width * 0.5;
      const py = e.clientY ? e.clientY - rect.top : rect.height * 0.5;

      const words = ['BOOP', 'POP', 'CLICK', 'TAP', 'SNAP'];
      const word = words[Math.floor(Math.random() * words.length)];

      const badge = document.createElement('div');
      badge.className = 'comic-demo-badge';
      badge.textContent = word;
      badge.style.left = `${px}px`;
      badge.style.top = `${py - 16}px`;

      comicDemoTile.appendChild(badge);

      requestAnimationFrame(() => {
        badge.style.transform = 'translate(-50%, -64px) scale(1)';
        badge.style.opacity = '0';
      });

      setTimeout(() => {
        badge.remove();
      }, 520);
    });
  }
});
