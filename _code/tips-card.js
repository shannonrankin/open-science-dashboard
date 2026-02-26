/* ============================================================
   _code/tips-card.js
   Open Science Tips card logic.

   Expects window.OSTIPS to be set by the Quarto page via an
   inline <script> that reads tips.yaml at render time (see
   index.qmd for the ojs/knitr chunk that does this).
   ============================================================ */

(function () {
  'use strict';

  /* ── Helpers ─────────────────────────────────────────────── */
  function getRandom(arr, exclude) {
    if (arr.length === 1) return 0;
    let idx;
    do { idx = Math.floor(Math.random() * arr.length); }
    while (idx === exclude);
    return idx;
  }

  const CATEGORY_ICONS = {
    'Preregistration':          '📋',
    'Open Data':                '📂',
    'Reproducibility':          '🔁',
    'Open Tools & Software':    '🛠️',
    'Transparent Reporting':    '📝',
    'Community & Collaboration':'🤝',
  };

  /* ── Render a tip into the card ──────────────────────────── */
  function renderTip(tip, card, animate) {
    // Category
    card.setAttribute('data-category', tip.category || '');

    // Reset animation
    if (animate) {
      card.classList.remove('tip-animating');
      void card.offsetWidth; // reflow
      card.classList.add('tip-animating');
    }

    const icon = CATEGORY_ICONS[tip.category] || '💡';

    // Badge
    card.querySelector('.tip-category-badge').innerHTML =
      `<span>${icon}</span><span>${tip.category || 'Open Science'}</span>`;

    // Name
    card.querySelector('.tip-name').textContent = tip.name;

    // Thumbnail (optional)
    // Image paths in tips.yaml are repo-root-relative (e.g. "content/tip-images/foo.png").
    // We prefix them with the site base URL read from the <meta name="ostip-base-url">
    // tag injected by index.qmd at render time — giving a stable absolute URL that
    // works regardless of which page or subdirectory the card is embedded in.
    const thumbEl = card.querySelector('.tip-thumb');
    if (tip.image) {
      const baseMeta = document.querySelector('meta[name="ostip-base-url"]');
      const base     = baseMeta ? baseMeta.getAttribute('content').replace(/\/$/, '') : '';
      thumbEl.src    = base ? `${base}/${tip.image}` : tip.image;
      thumbEl.alt    = tip.name;
      thumbEl.style.display = 'block';
    } else {
      thumbEl.style.display = 'none';
    }

    // Text
    card.querySelector('.tip-text').textContent = tip.text;

    // Learn more link
    const link = card.querySelector('.tip-learn-link');
    link.href = tip.link;
    link.querySelector('.tip-link-label').textContent =
      tip.link_label || 'Learn more';
  }

  /* ── Boot ────────────────────────────────────────────────── */
  function init() {
    const tips = window.OSTIPS;
    if (!tips || !tips.length) {
      console.warn('tips-card.js: window.OSTIPS is empty or undefined.');
      return;
    }

    const card       = document.getElementById('os-tip-card');
    const counter    = document.getElementById('tip-counter');
    const btnPrev    = document.getElementById('tip-btn-prev');
    const btnNext    = document.getElementById('tip-btn-next');
    const btnShuffle = document.getElementById('tip-btn-shuffle');

    if (!card) {
      console.warn('tips-card.js: #os-tip-card not found.');
      return;
    }

    // Shuffle tips array
    const shuffled = [...tips].sort(() => Math.random() - 0.5);
    let current = 0;

    function updateCounter() {
      if (counter) counter.textContent = `${current + 1} / ${shuffled.length}`;
    }

    function show(idx, animate) {
      current = ((idx % shuffled.length) + shuffled.length) % shuffled.length;
      renderTip(shuffled[current], card, animate);
      updateCounter();
    }

    // Initial render — random starting tip, no animation
    show(Math.floor(Math.random() * shuffled.length), false);

    if (btnNext)    btnNext.addEventListener('click',    () => show(current + 1, true));
    if (btnPrev)    btnPrev.addEventListener('click',    () => show(current - 1, true));
    if (btnShuffle) btnShuffle.addEventListener('click', () => {
      // Re-shuffle and go to first
      shuffled.sort(() => Math.random() - 0.5);
      current = -1;
      show(0, true);
    });
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
