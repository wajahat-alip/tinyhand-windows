/**
 * TinyHand Windows — Landing Page Main Controller
 */

// Full Catalog of 36 3D Hands + 4 Vector FX
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

const SPECIAL_FX_POINTERS = [
  { id: 'cat_paw', name: 'Cat Paw', category: 'fx', icon: '🐾' },
  { id: 'magic_wand', name: 'Magic Wand', category: 'fx', icon: '✨' },
  { id: 'boxing_glove', name: 'Boxing Glove', category: 'fx', icon: '🥊' },
  { id: 'laser', name: 'Red Laser Dot', category: 'fx', icon: '🔴' }
];

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
    });
  }

  if (btnDraw) {
    btnDraw.addEventListener('click', () => {
      const active = heroStage.toggleDraw();
      btnDraw.classList.toggle('active', active);
    });
  }

  if (btnSound) {
    btnSound.addEventListener('click', () => {
      const active = heroStage.toggleSound();
      btnSound.classList.toggle('active', active);
      btnSound.innerHTML = active ? '🔊 Sound: ON' : '🔇 Muted';
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
      const card = document.createElement('div');
      card.className = `hand-tile ${heroStage.activeHand === item.id ? 'selected' : ''}`;
      card.dataset.id = item.id;

      if (item.category === 'fx') {
        card.innerHTML = `
          <div style="font-size: 46px; height: 78px; display: flex; align-items: center; justify-content: center; margin-bottom: 8px;">${item.icon}</div>
          <div class="hand-tile-name">${item.name}</div>
          <div class="hand-tile-sub">Vector FX</div>
        `;
      } else {
        card.innerHTML = `
          <picture>
            <source srcset="assets/hands/hand_${item.id}.webp" type="image/webp">
            <img src="assets/hands/hand_${item.id}.png" alt="${item.name}" loading="lazy">
          </picture>
          <div class="hand-tile-name">${item.name}</div>
          <div class="hand-tile-sub">3D Model</div>
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

        // Smooth scroll to stage if clicked from bottom
        const rect = document.getElementById('heroStageCanvas').getBoundingClientRect();
        if (rect.top < -100 || rect.bottom > window.innerHeight + 100) {
          document.getElementById('playgroundWrap').scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      });

      galleryGrid.appendChild(card);
    });
  }

  // Initial gallery render
  renderGallery('all');

  // Filter Tabs listener
  filterTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      filterTabs.forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      renderGallery(tab.dataset.filter);
    });
  });

  // 4. Bento Interactive Ink Pad
  const inkCanvas = document.getElementById('bentoInkPad');
  if (inkCanvas) {
    const ictx = inkCanvas.getContext('2d');
    let isDrawing = false;
    let bentoHue = 210;

    function resizeBentoCanvas() {
      const rect = inkCanvas.getBoundingClientRect();
      inkCanvas.width = rect.width * (window.devicePixelRatio || 1);
      inkCanvas.height = rect.height * (window.devicePixelRatio || 1);
      ictx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    }
    resizeBentoCanvas();
    window.addEventListener('resize', resizeBentoCanvas);

    inkCanvas.addEventListener('mousedown', (e) => {
      isDrawing = true;
      const rect = inkCanvas.getBoundingClientRect();
      ictx.beginPath();
      ictx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
      bentoHue = (bentoHue + 25) % 360;
    });

    inkCanvas.addEventListener('mousemove', (e) => {
      if (!isDrawing) return;
      const rect = inkCanvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      ictx.strokeStyle = `hsl(${bentoHue}, 100%, 65%)`;
      ictx.lineWidth = 4;
      ictx.lineCap = 'round';
      ictx.lineJoin = 'round';
      ictx.shadowColor = `hsl(${bentoHue}, 100%, 65%)`;
      ictx.shadowBlur = 6;
      ictx.lineTo(x, y);
      ictx.stroke();
    });

    window.addEventListener('mouseup', () => { isDrawing = false; });

    const btnClearBento = document.getElementById('bentoClearInk');
    if (btnClearBento) {
      btnClearBento.addEventListener('click', () => {
        ictx.clearRect(0, 0, inkCanvas.width, inkCanvas.height);
      });
    }
  }

  // 5. Comic Pop Interactive Button in Bento
  const comicDemoTile = document.getElementById('comicDemoTile');
  if (comicDemoTile) {
    const popAudio = new Audio('assets/sounds/tap_pop.wav');
    comicDemoTile.addEventListener('click', (e) => {
      popAudio.currentTime = 0;
      popAudio.play().catch(() => {});

      const words = ['BOOP!', 'POW!', 'CLICK!', 'WOW!', 'SUPER!'];
      const word = words[Math.floor(Math.random() * words.length)];

      const badge = document.createElement('div');
      badge.textContent = word;
      badge.style.position = 'absolute';
      badge.style.left = `${e.offsetX}px`;
      badge.style.top = `${e.offsetY - 20}px`;
      badge.style.background = '#2563EB';
      badge.style.color = '#FFFFFF';
      badge.style.padding = '4px 10px';
      badge.style.borderRadius = '9999px';
      badge.style.fontSize = '12px';
      badge.style.fontWeight = 'bold';
      badge.style.boxShadow = '0 0 15px rgba(37,99,235,0.7)';
      badge.style.pointerEvents = 'none';
      badge.style.transition = 'all 0.6s cubic-bezier(0.16, 1, 0.3, 1)';
      badge.style.transform = 'translate(-50%, -50%) scale(0.6)';
      badge.style.opacity = '1';

      comicDemoTile.appendChild(badge);

      requestAnimationFrame(() => {
        badge.style.transform = 'translate(-50%, -90px) scale(1.1)';
        badge.style.opacity = '0';
      });

      setTimeout(() => {
        badge.remove();
      }, 650);
    });
  }
});
