(() => {
  'use strict';
  // The URL determines language. Native EN/UA links work without JavaScript,
  // browser-language detection, storage access or automatic redirection.
  document.addEventListener('click', event => {
    const link = event.target.closest?.('[data-language]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
    try { localStorage.setItem('qa-language', link.dataset.language); } catch {}
    // Preserve native link navigation; the corresponding language URL is explicit.
  });
})();
