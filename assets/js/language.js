(() => {
  'use strict';
  const key = 'qa-language';
  const uk = location.pathname === '/ua' || location.pathname.startsWith('/ua/');
  const base = location.pathname.replace(/^\/ua(?=\/|$)/, '') || '/';
  const requested = new URLSearchParams(location.search).get('lang');
  let saved;
  try { saved = localStorage.getItem(key); } catch {}
  if (requested === 'en' || requested === 'uk') { saved = requested; try { localStorage.setItem(key, requested); } catch {} }
  const preferred = saved === 'en' || saved === 'uk' ? saved : /^uk(?:-|$)/i.test(navigator.language || '') ? 'uk' : 'en';
  // Direct Ukrainian URLs remain shareable; automatic detection applies on English routes.
  if (!uk && preferred === 'uk') location.replace('/ua' + base + location.search + location.hash);
  document.addEventListener('click', event => {
    const link = event.target.closest('[data-language]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    let stored = false;
    try { localStorage.setItem(key, link.dataset.language); stored = true; } catch {}
    event.preventDefault();
    const target = new URL(link.href);
    if (!stored) target.searchParams.set('lang', link.dataset.language);
    location.assign(target.pathname + target.search + location.hash);
  });
})();
