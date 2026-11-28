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
  laser: `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><circle cx="12" cy="12" r="7" stroke="#FF6B4A"/><circle cx="12" cy="12" r="3" fill="#FF6B4A" stroke="none"/></svg>`
};

const SPECIAL_FX_POINTERS = [
  { id: 'cat_paw', name: 'Cat Paw', category: 'fx' },
  { id: 'magic_wand', name: 'Magic Wand', category: 'fx' },
  { id: 'boxing_glove', name: 'Boxing Glove', category: 'fx' },
  { id: 'laser', name: 'Laser Dot', category: 'fx' }
];

const SOUND_ICON_ON = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>`;
const SOUND_ICON_OFF = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>`;

const RELEASE_BINARY_URL = 'https://github.com/wajahat-alip/tinyhand-windows/releases/download/v1.0.0/TinyHandWindows.exe';
const BINARY_SHA256 = '4963e345e87726495c1edb78d7a4d607c9d14e3f8dece1731a8eb2303d517ddb';

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

  // 3. Bottom-Right Toast Notification System
  const stageToast = document.getElementById('stageToast');
  const toastMessage = document.getElementById('toastMessage');
  const toastJumpBtn = document.getElementById('toastJumpBtn');
  const toastDismissBtn = document.getElementById('toastDismissBtn');
  let toastTimer = null;

  function hideToast() {
    if (!stageToast) return;
    stageToast.classList.remove('is-visible');
    clearTimeout(toastTimer);
  }

  function showEquippedToast(handName) {
    if (!stageToast || !toastMessage) return;
    toastMessage.textContent = `Equipped ${handName}`;
    stageToast.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(hideToast, 4600);
  }

  if (stageToast) {
    stageToast.addEventListener('mouseenter', () => clearTimeout(toastTimer));
    stageToast.addEventListener('mouseleave', () => {
      if (stageToast.classList.contains('is-visible')) {
        toastTimer = setTimeout(hideToast, 2500);
      }
    });
  }

  if (toastJumpBtn) {
    toastJumpBtn.addEventListener('click', () => {
      const wrap = document.getElementById('playgroundWrap');
      if (wrap) {
        wrap.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      hideToast();
    });
  }

  if (toastDismissBtn) {
    toastDismissBtn.addEventListener('click', hideToast);
  }

  // 4. Render Hand Gallery Grid + Non-Intrusive Toast Sync
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
      const isSelected = heroStage.activeHand === item.id;
      const card = document.createElement('button');
      card.type = 'button';
      card.className = `hand-tile ${isSelected ? 'selected' : ''}`;
      card.dataset.id = item.id;
      card.setAttribute('aria-pressed', String(isSelected));

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
        document.querySelectorAll('.hand-tile').forEach(c => {
          c.classList.remove('selected');
          c.setAttribute('aria-pressed', 'false');
        });
        card.classList.add('selected');
        card.setAttribute('aria-pressed', 'true');

        heroStage.setHand(item.id);
        heroStage.playTapSound();

        if (handIndicator) {
          handIndicator.textContent = item.name;
        }

        showEquippedToast(item.name);
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

  // 5. Morphing Download CTA + Windows-Native Quick-Start Modal
  const downloadModal = document.getElementById('downloadModal');
  const modalCloseBtn = document.getElementById('downloadModalClose');
  const modalRetryBtn = document.getElementById('modalRetryBtn');
  const copyChecksumBtn = document.getElementById('copyChecksumBtn');
  const downloadCtas = document.querySelectorAll('[data-download-cta]');

  function triggerExeDownload(url = RELEASE_BINARY_URL) {
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener';
    link.setAttribute('download', 'TinyHandWindows.exe');
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  function morphCtaButton(btn) {
    if (!btn || btn.dataset.morphing === '1') return;
    btn.dataset.morphing = '1';

    const originalHtml = btn.innerHTML;
    const width = btn.getBoundingClientRect().width;
    if (width > 0) {
      btn.style.minWidth = `${Math.ceil(width)}px`;
    }

    btn.classList.add('is-morphing');
    btn.innerHTML = `<span class="accent-dot" aria-hidden="true"></span><span>Starting download...</span>`;

    setTimeout(() => {
      btn.classList.remove('is-morphing');
      btn.classList.add('is-ready');
      btn.innerHTML = `<span class="accent-dot" aria-hidden="true"></span><span>Ready &#10003;</span>`;
    }, 550);

    setTimeout(() => {
      btn.classList.remove('is-ready');
      btn.innerHTML = originalHtml;
      btn.style.minWidth = '';
      delete btn.dataset.morphing;
    }, 2400);
  }

  downloadCtas.forEach(cta => {
    cta.addEventListener('click', (e) => {
      e.preventDefault();
      morphCtaButton(cta);
      triggerExeDownload(cta.getAttribute('href') || RELEASE_BINARY_URL);

      if (downloadModal && typeof downloadModal.showModal === 'function' && !downloadModal.open) {
        downloadModal.showModal();
      }
    });
  });

  if (modalCloseBtn && downloadModal) {
    modalCloseBtn.addEventListener('click', () => {
      downloadModal.close();
    });
  }

  if (downloadModal) {
    downloadModal.addEventListener('click', (e) => {
      if (e.target === downloadModal) {
        downloadModal.close();
      }
    });
  }

  if (modalRetryBtn) {
    modalRetryBtn.addEventListener('click', () => {
      triggerExeDownload(RELEASE_BINARY_URL);
      const prev = modalRetryBtn.textContent;
      modalRetryBtn.textContent = 'Retrying...';
      setTimeout(() => {
        modalRetryBtn.textContent = prev;
      }, 1500);
    });
  }

  if (copyChecksumBtn) {
    const originalCopyHtml = copyChecksumBtn.innerHTML;
    let copyTimer = null;

    copyChecksumBtn.addEventListener('click', async () => {
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(BINARY_SHA256);
        } else {
          const area = document.createElement('textarea');
          area.value = BINARY_SHA256;
          area.style.position = 'fixed';
          area.style.opacity = '0';
          document.body.appendChild(area);
          area.select();
          document.execCommand('copy');
          area.remove();
        }
      } catch (e) {}

      copyChecksumBtn.innerHTML = `<span class="accent-dot" aria-hidden="true"></span><span>Copied!</span>`;
      clearTimeout(copyTimer);
      copyTimer = setTimeout(() => {
        copyChecksumBtn.innerHTML = originalCopyHtml;
      }, 2000);
    });
  }

  // 6. Scroll-Triggered Compact CTA Pill (Visible only after Hero Section)
  const heroSection = document.getElementById('stageSection');
  const floatingPill = document.getElementById('floatingCtaPill');
  const floatingBtn = document.getElementById('floatingDownloadBtn');

  function setFloatingVisible(visible) {
    if (!floatingPill) return;
    floatingPill.classList.toggle('is-visible', visible);
    floatingPill.setAttribute('aria-hidden', String(!visible));
    if (floatingBtn) {
      floatingBtn.tabIndex = visible ? 0 : -1;
    }
  }

  if (heroSection && floatingPill && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      const entry = entries[0];
      const scrolledPastHero = !entry.isIntersecting && entry.boundingClientRect.bottom < 80;
      setFloatingVisible(scrolledPastHero);
    }, { threshold: 0 });

    observer.observe(heroSection);
  }
});
