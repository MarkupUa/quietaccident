(() => {
  'use strict';
  const uk = document.documentElement.lang === 'uk';
  const t = value => {
    if (!uk) return value;
    const dictionary = window.QA_TRANSLATIONS || {};
    if (dictionary[value]) return dictionary[value];
    return value.replace('Upcoming release', 'Майбутній реліз').replace('Latest release', 'Новий реліз').replace(' / Single', ' / Сингл').replace(' — official single artwork', ' — офіційна обкладинка синглу').replace('SINGLE / ', 'СИНГЛ / ').replace('ARTWORK PENDING', 'ОБКЛАДИНКА НЕЗАБАРОМ').replace(/^View /, 'Переглянути ');
  };
  const localized = markup => markup.replace(/>([^<]+)</g, (_, text) => '>' + text.replace(/\S[\s\S]*\S|\S/, value => t(value)) + '<').replace(/(alt|aria-label)="([^"]*)"/g, (_, key, value) => key + '="' + t(value) + '"');
  const root = document.body.dataset.root || './';
  const releases = (window.QA_RELEASES || []).filter(r => r.published === true).sort((a,b) => b.releaseDate.localeCompare(a.releaseDate));
  const escape = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const date = s => new Date(s + 'T12:00:00Z').toLocaleDateString(uk ? 'uk-UA' : 'en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
  const url = r => `${uk ? '/ua' : ''}/releases/${r.slug}/`;
  const art = r => `<div class="artwork"><div class="art-placeholder" hidden><small>QUIET ACCIDENT</small><strong>${escape(r.title)}</strong><small class="art-label">SINGLE / ${r.releaseDate.slice(0,4)} · ARTWORK PENDING</small></div><img src="${root + escape(r.artwork)}" alt="${escape(r.title)} — official single artwork" width="1254" height="1254" loading="lazy" decoding="async"></div>`;
  function loadArtwork(scope = document) {
    scope.querySelectorAll('.artwork img').forEach(img => {
      const show = () => { img.hidden = false; img.previousElementSibling.hidden = true; };
      const fallback = () => { img.hidden = true; img.previousElementSibling.hidden = false; };
      img.addEventListener('load',show,{once:true});
      img.addEventListener('error',fallback,{once:true});
      if(img.complete) {
        if(img.naturalWidth) show();
        else fallback();
      }
    });
  }
  document.querySelectorAll('[data-release-grid]').forEach(grid => {
    const catalogue = grid.hasAttribute('data-home-catalogue') ? releases.slice(1, 4) : releases;
    grid.innerHTML = localized(catalogue.map(r => `<a class="release-card" href="${url(r)}">${art(r)}<div class="card-info"><div><h3>${escape(r.title)}</h3><time class="date" datetime="${r.releaseDate}">${date(r.releaseDate)}</time></div><span class="card-arrow" aria-hidden="true">↗</span></div><span class="text-link">View Release</span></a>`).join(''));
  });
  const latest = document.querySelector('[data-latest]');
  if(latest && releases.length){const r = releases[0];latest.innerHTML = localized(`<a href="${url(r)}" aria-label="View ${escape(r.title)}">${art(r)}</a><div class="latest-copy"><p class="eyebrow red">${r.releaseDate > new Date().toISOString().slice(0,10) ? 'Upcoming release' : 'Latest release'} / Single</p><h2>${escape(r.title)}</h2><p class="date"><time datetime="${r.releaseDate}">${date(r.releaseDate)}</time></p><p class="lede">${escape(t(r.description))}</p><a class="button" href="${url(r)}">View Release <span aria-hidden="true">↗</span></a></div>`);}
  const icons = {
    Spotify:'<circle cx="12" cy="12" r="11"/><path d="M6 9q6-3 12 1M7 12q5-2 10 1M8 15q4-1 8 1" fill="none" stroke="#121214" stroke-width="1.5" stroke-linecap="round"/>',
    'Apple Music':'<path d="M9 5v11a3 3 0 1 0 2 3V9l8-2v7a3 3 0 1 0 2 3V2z"/>',
    iTunes:'<path d="M9 5v11a3 3 0 1 0 2 3V9l8-2v7a3 3 0 1 0 2 3V2z"/>',
    'YouTube Music':'<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="7" fill="none" stroke="currentColor"/><path d="m10 8 6 4-6 4z"/>',
    'Amazon Music':'<path d="M10 3v12a3 3 0 1 0 2 2V7l7-2v8a3 3 0 1 0 2 2V1zM3 21q9 5 18-1l-1-1q-8 4-17 1z"/>',
    Deezer:'<path d="M2 16h3v6H2zm4-5h3v11H6zm4-8h3v19h-3zm4 5h3v14h-3zm4-3h3v17h-3z"/>'
  };
  const release = releases.find(r => r.slug === document.body.dataset.release);
  const platforms = document.querySelector('[data-platforms]');
  if(release && platforms){
    const services = [['Spotify Pre-Save','preSaveUrl'],['Amazon Music','amazonMusicUrl'],['Spotify','spotifyUrl'],['YouTube Music','youtubeMusicUrl'],['Apple Music','appleMusicUrl'],['iTunes','itunesUrl'],['Deezer','deezerUrl']];
    const links = services.filter(([,key]) => /^https:\/\//.test(release[key] || ''));
    platforms.innerHTML = localized(links.length ? links.map(([name,key]) => `<a class="platform" href="${escape(release[key])}" target="_blank" rel="noopener noreferrer"><svg viewBox="0 0 24 24" aria-hidden="true">${icons[name === 'Spotify Pre-Save' ? 'Spotify' : name]}</svg><span>${name}</span><span class="arrow" aria-hidden="true">↗</span><span class="sr-only"> (opens in a new tab)</span></a>`).join('') : '<p class="empty-platforms">Streaming links for this single will be added here. Explore Quiet Accident on <a class="text-link" href="https://open.spotify.com/artist/0Uoyw8HMxfw0RG67OHzQJS" target="_blank" rel="noopener noreferrer">Spotify ↗</a>.</p>');
  }
  loadArtwork();
  const menu = document.querySelector('.menu'); const nav = document.querySelector('#navigation');
  function closeMenu(){nav.classList.remove('open');menu.setAttribute('aria-expanded','false');}
  menu?.addEventListener('click',() => {const open = menu.getAttribute('aria-expanded') !== 'true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('open',open);});
  document.addEventListener('keydown',e => {if(e.key === 'Escape' && nav?.classList.contains('open')){closeMenu();menu.focus();}});
  nav?.querySelectorAll('a').forEach(a => a.addEventListener('click',closeMenu));
  document.querySelector('[data-share]')?.addEventListener('click', async () => {
    const status = document.querySelector('[data-share-status]');
    const shareUrl = location.href.split('#')[0];
    if(navigator.share){try{await navigator.share({title:document.title,url:shareUrl});status.textContent=t('Release shared.');return;}catch(e){if(e.name==='AbortError')return;}}
    try{await navigator.clipboard.writeText(shareUrl);status.textContent=t('Link copied to clipboard.');}
    catch{const input=document.createElement('input');input.className='manual-copy';input.readOnly=true;input.value=shareUrl;input.setAttribute('aria-label',t('Release URL — copy this link'));status.replaceChildren(document.createTextNode(t('Copy this link: ')),input);input.focus();input.select();}
  });
})();
