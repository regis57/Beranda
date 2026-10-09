// Beranda settings page. Vanilla JS, no build step. Talks only to /api/admin/*.
// Written for people who are not technical: every section explains itself.

const $ = (id) => document.getElementById(id);
const THEME_COLORS = {
  japan: ['#f4efe4', '#bf3b2b', '#2f5d8a', '#23201d'],
  indonesia: ['#f3e8d0', '#b5651d', '#1f4a73', '#3a2518'],
  france: ['#f6f3ec', '#c8372d', '#2a4d8f', '#1b2340'],
  germany: ['#efeeea', '#d6301f', '#f1b51c', '#141414'],
  spain: ['#f6eddf', '#b4441f', '#23519f', '#3a1e12'],
  italy: ['#f5efe3', '#a8322d', '#335c8a', '#2b2420'],
  portugal: ['#f5f7fa', '#1d4fb0', '#2f86c9', '#102a5c'],
  brazil: ['#f4f5ef', '#0d8a4a', '#e7b400', '#1f4aa8'],
  africa: ['#efe3cd', '#e2a414', '#2e7a3a', '#b8281c'],
  arab: ['#f5f0e6', '#0f6e62', '#b8862b', '#13292a'],
  america: ['#f2e8d2', '#c4512a', '#2f5d3a', '#2b5c8a'],
  india: ['#fbf3e2', '#e0700c', '#b3236a', '#2a1b45'],
  china: ['#f5efe2', '#b3261e', '#b28a36', '#1d1a18'],
  oceania: ['#f0f5f1', '#d9634b', '#128a95', '#7a4a2a'],
  creole: ['#fdf6e6', '#f2b705', '#d8431b', '#2f8f46'],
};
const KINDS = ['birth', 'death', 'anniversary', 'other'];
const IMPERIAL = new Set(['US', 'LR', 'MM']);
const RTL = new Set(['ar', 'fa', 'he', 'ur']);

// Official help pages, opened in the reader's language when the site offers it.
const MS_LOCALE = { fr: 'fr-fr', de: 'de-de', es: 'es-es', it: 'it-it', pt: 'pt-pt', 'pt-BR': 'pt-br', ja: 'ja-jp', id: 'id-id', ar: 'ar-sa' };
const APPLE_LOCALE = { fr: 'fr-fr/', de: 'de-de/', es: 'es-es/', it: 'it-it/', pt: 'pt-pt/', 'pt-BR': 'pt-br/', ja: 'ja-jp/', id: 'id-id/' };
const CAL_GUIDES = [
  ['google', 'Google Calendar', (l) => `https://support.google.com/calendar/answer/37648?hl=${l}`],
  ['apple', 'Apple iCloud', (l) => `https://support.apple.com/${APPLE_LOCALE[l] || ''}guide/icloud/share-a-calendar-mm6b1a9479/icloud`],
  ['outlook', 'Outlook / Microsoft 365', (l) => `https://support.microsoft.com/${MS_LOCALE[l] || 'en-us'}/outlook/share-your-calendar-in-outlook-com`],
  ['nextcloud', 'Nextcloud', () => 'https://docs.nextcloud.com/server/stable/user_manual/en/groupware/calendar.html#publishing-a-calendar'],
  ['proton', 'Proton Calendar', () => 'https://proton.me/support/share-calendar-via-link'],
];

let strings = {};
let lang = 'en';
let options = { countries: {}, languages: [], themes: [], news: [], region_of: {}, country_languages: {} };
let cfg = null;
let editable = true;
let dirty = false;
let unitsTouched = false;
let languageTouched = false;
let newsSelected = new Set();
let newsAuto = true;
let pin = '';
try { pin = sessionStorage.getItem('beranda-pin') || ''; } catch { /* storage may be blocked */ }

// ------------------------------------------------------------------ i18n ---
const merge = (a, b) => {
  const out = { ...a };
  for (const [k, v] of Object.entries(b)) out[k] = v && typeof v === 'object' ? merge(a[k] || {}, v) : v;
  return out;
};
async function loadStrings(code) {
  const get = async (n) => { try { const r = await fetch(`/static/i18n/${n}.json`); return r.ok ? r.json() : {}; } catch { return {}; } };
  const m = /^([a-z]{2,3})(?:-([A-Za-z]{2}))?/.exec(String(code).replace('_', '-').toLowerCase()) || [null, 'en'];
  const base = m[1];
  const full = m[2] ? `${base}-${m[2].toUpperCase()}` : base;
  const chain = [...new Set(['en', base, full])];
  let merged = {};
  for (const c of chain) merged = merge(merge(merged, await get(c)), { admin: await get(`admin/${c}`) });
  strings = merged;
  lang = full;
  document.documentElement.lang = full;
  document.documentElement.dir = RTL.has(base) ? 'rtl' : 'ltr';
}
function t(key, vars) {
  let s = key.split('.').reduce((o, k) => (o ? o[k] : undefined), strings);
  if (typeof s !== 'string') return key;
  for (const [k, v] of Object.entries(vars || {})) s = s.replaceAll(`{${k}}`, v);
  return s;
}
function translateStatic() {
  for (const el of document.querySelectorAll('[data-i18n]')) el.textContent = t(el.dataset.i18n);
  for (const el of document.querySelectorAll('[data-ph]')) el.placeholder = t(el.dataset.ph);
  $('open-display').textContent = t('admin.open_display');
  document.title = `Beranda · ${t('admin.title')}`;
}

// ------------------------------------------------------------------ api ----
async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(pin ? { 'X-Beranda-Pin': pin } : {}) };
  const res = await fetch(`/api/admin${path}`, { ...opts, headers });
  if (!res.ok) {
    let detail = '';
    try { detail = (await res.json()).detail || ''; } catch { /* not JSON */ }
    const err = new Error(detail || `HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

// ------------------------------------------------------------------ helpers ---
const el = (tag, props = {}, ...kids) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...kids);
  return node;
};
function fill(select, items, current) {
  select.replaceChildren(...items.map(([value, label]) => el('option', { value, textContent: label })));
  if (current != null && current !== '' && ![...select.options].some((o) => o.value === current)) {
    select.prepend(el('option', { value: current, textContent: current }));
  }
  select.value = current ?? select.options[0]?.value ?? '';
}
function regionName(code) {
  try { return new Intl.DisplayNames([lang], { type: 'region' }).of(code) || code; } catch { return code; }
}
function languageName(code) {
  try { return new Intl.DisplayNames([code], { type: 'language' }).of(code) || code; } catch { return code; }
}
function markDirty() {
  dirty = true;
  $('state').textContent = t('admin.unsaved');
  $('state').className = '';
}
let previewTimer = null;
function refreshPreview() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(() => {
    const q = new URLSearchParams({ theme: cfg.theme, lang: $('language').value });
    if (cfg.mode !== 'auto') q.set('mode', cfg.mode);
    $('preview').src = `/?${q}`;
  }, 250);
}
function fitPreview() {
  $('frame').style.setProperty('--s', ($('frame').clientWidth / 1280).toFixed(4));
}
function testButton(run) {
  const button = el('button', { type: 'button', textContent: t('admin.test') });
  const msg = el('div', { className: 'msg', hidden: true });
  button.addEventListener('click', async () => {
    msg.hidden = false; msg.className = 'msg'; msg.textContent = '…';
    try {
      const [ok, text] = await run();
      msg.className = `msg ${ok ? 'ok' : 'bad'}`;
      msg.textContent = text;
    } catch (e) { msg.className = 'msg bad'; msg.textContent = e.message; }
  });
  return [button, msg];
}

// ------------------------------------------------------------------ 1. place ---
function renderPlace() {
  $('loc-name').value = cfg.location.name;
  $('loc-lat').value = cfg.location.latitude;
  $('loc-lon').value = cfg.location.longitude;
  const zones = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : [];
  fill($('loc-tz'), zones.map((z) => [z, z]), cfg.location.timezone);
}
async function search() {
  const q = $('q').value.trim();
  const list = $('q-results');
  $('q-error').hidden = true;
  if (q.length < 2) { list.hidden = true; return; }
  try {
    const { results } = await api(`/geocode?q=${encodeURIComponent(q)}&language=${lang}`);
    list.replaceChildren(...results.map((r) => {
      const b = el('button', { type: 'button' }, `${r.name} `, el('small', { textContent: [r.region, r.country && regionName(r.country)].filter(Boolean).join(', ') }));
      b.addEventListener('click', () => {
        $('loc-name').value = r.name;
        $('loc-lat').value = r.latitude;
        $('loc-lon').value = r.longitude;
        if (r.timezone) fill($('loc-tz'), [...$('loc-tz').options].map((o) => [o.value, o.value]), r.timezone);
        if (r.country && options.countries[r.country]) { $('country').value = r.country; onCountry(); }
        list.hidden = true;
        markDirty();
        refreshNews();
      });
      return el('li', {}, b);
    }));
    list.hidden = results.length === 0;
    if (!results.length) { $('q-error').textContent = t('admin.no_result'); $('q-error').hidden = false; }
  } catch {
    $('q-error').textContent = t('admin.search_failed'); $('q-error').hidden = false;
  }
}

// ------------------------------------------------------------------ 2. region ---
function renderRegion() {
  const codes = Object.keys(options.countries).sort((a, b) => regionName(a).localeCompare(regionName(b), lang));
  fill($('country'), codes.map((c) => [c, `${regionName(c)} (${c})`]), cfg.country);
  renderSubdivisions(cfg.subdivision || '');
  fill($('language'), options.languages.map((l) => [l, languageName(l)]), cfg.language);
  fill($('units'), [['metric', t('admin.metric')], ['imperial', t('admin.imperial')]], cfg.units);
}
function renderSubdivisions(current) {
  const subs = options.countries[$('country').value] || [];
  fill($('subdivision'), [['', t('admin.none')], ...subs.map((s) => [s, s])], current);
  $('subdivision').disabled = subs.length === 0;
}
function onCountry() {
  const country = $('country').value;
  renderSubdivisions('');
  if (!unitsTouched) $('units').value = IMPERIAL.has(country) ? 'imperial' : 'metric';
  const suggested = (options.country_languages[country] || [])[0];
  if (!languageTouched && suggested && options.languages.includes(suggested)) {
    $('language').value = suggested;
    refreshPreview();
  }
  refreshNews();
}

// ------------------------------------------------------------------ 3. look ---
function renderLook() {
  $('themes').replaceChildren(...options.themes.map((name) => {
    const sw = el('span', { className: 'sw' }, ...(THEME_COLORS[name] || []).map((c) => {
      const i = el('i'); i.style.setProperty('background', c); return i;
    }));
    const b = el('button', { type: 'button', className: 'theme' }, sw,
      el('b', { textContent: t(`admin.themes.${name}.name`) }),
      el('span', { className: 'd', textContent: t(`admin.themes.${name}.desc`) }));
    b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(cfg.theme === name));
    b.addEventListener('click', () => { cfg.theme = name; renderLook(); markDirty(); refreshPreview(); });
    return b;
  }));
  $('modes').replaceChildren(...['auto', 'light', 'night'].map((m) => {
    const b = el('button', { type: 'button', textContent: t(`admin.${m}`) });
    b.setAttribute('role', 'radio');
    b.setAttribute('aria-checked', String(cfg.mode === m));
    b.addEventListener('click', () => { cfg.mode = m; renderLook(); markDirty(); refreshPreview(); });
    return b;
  }));
}

// ------------------------------------------------------------------ 4. calendar ---
function renderCalendarGuide() {
  $('cal-providers').replaceChildren(...CAL_GUIDES.map(([key, name, url]) => el('li', {},
    el('b', { textContent: name }),
    el('span', { textContent: t(`admin.cal_${key}`) }),
    el('a', { href: url(lang), target: '_blank', rel: 'noopener', textContent: t('admin.official_guide') }))));
}
function addIcsRow(url = '') {
  const input = el('input', { type: 'url', placeholder: t('admin.ics_placeholder'), value: url, spellcheck: false });
  const [test, msg] = testButton(async () => {
    const r = await api('/test-ics', { method: 'POST', body: JSON.stringify({ url: input.value.trim() }) });
    return [r.ok, r.ok ? t('admin.test_ok', { n: r.count, next: r.next.join(' · ') }) : t('admin.test_fail', { err: r.error })];
  });
  const del = el('button', { type: 'button', textContent: '✕', title: t('admin.remove') });
  const row = el('div', { className: 'item ics' }, input, test, del, msg);
  input.addEventListener('input', markDirty);
  del.addEventListener('click', () => { row.remove(); markDirty(); });
  $('ics-list').append(row);
}

// ------------------------------------------------------------------ 5. key dates ---
function addKeyRow(k = { date: '', label: '', kind: 'birth' }) {
  const date = el('input', { value: k.date, placeholder: 'YYYY-MM-DD / MM-DD', pattern: '(\\d{4}-)?\\d{2}-\\d{2}', required: true });
  const label = el('input', { value: k.label, placeholder: t('admin.label'), required: true });
  const kind = el('select');
  fill(kind, KINDS.map((x) => [x, t(`kind.${x}`)]), k.kind);
  const del = el('button', { type: 'button', textContent: '✕', title: t('admin.remove') });
  const row = el('div', { className: 'item key' }, date, label, kind, del);
  for (const f of [date, label, kind]) f.addEventListener('input', markDirty);
  del.addEventListener('click', () => { row.remove(); markDirty(); });
  $('key-list').append(row);
}

// ------------------------------------------------------------------ 6. news ---
const sourceById = (id) => options.news.find((s) => s.id === id);
const cityName = () => $('loc-name').value.trim();
function sourceLabel(id) {
  if (id === 'city') return t('admin.news_city', { city: cityName() || '…' });
  return sourceById(id)?.name || id;
}
function sourceRow(id, desc = '') {
  const src = sourceById(id);
  const box = el('input', { type: 'checkbox', checked: newsSelected.has(id) });
  box.addEventListener('change', () => {
    if (box.checked) newsSelected.add(id); else newsSelected.delete(id);
    markDirty(); renderChips();
  });
  const name = el('label', { className: 'check' }, box, el('span', { textContent: sourceLabel(id) }));
  if (src) name.append(el('span', { className: 'lang', textContent: src.lang }));
  const [test, msg] = testButton(async () => {
    const r = await api('/test-feed', { method: 'POST', body: JSON.stringify({ id, city: cityName(), language: $('language').value }) });
    return [r.ok, r.ok ? t('admin.feed_ok', { n: r.count, first: r.first }) : t('admin.feed_fail', { err: r.error })];
  });
  const row = el('div', { className: 'src' }, name, el('span', { className: 'meta', textContent: desc }), test, msg);
  return row;
}
function renderChips() {
  const chips = $('news-chips');
  const ids = [...newsSelected];
  chips.replaceChildren(...ids.map((id) => {
    const chip = el('span', { className: 'chip', textContent: sourceLabel(id) });
    if (!newsAuto) {
      const x = el('button', { type: 'button', textContent: '✕', title: t('admin.remove') });
      x.addEventListener('click', () => { newsSelected.delete(id); markDirty(); renderNewsLists(); renderChips(); });
      chip.append(x);
    }
    return chip;
  }));
}
function renderNewsLists() {
  const country = $('country').value;
  const base = $('language').value.split('-')[0];
  $('news-city').replaceChildren(sourceRow('city', t('admin.news_city_desc')));
  $('news-country-title').textContent = t('admin.news_country', { country: regionName(country) });
  let mine = options.news.filter((s) => (s.countries || []).includes(country));
  const region = options.region_of[country];
  if (region) mine = mine.concat(options.news.filter((s) => s.region === region));
  $('news-country').replaceChildren(...(mine.length ? mine.map((s) => sourceRow(s.id)) : [el('p', { className: 'hint', textContent: t('admin.news_none_country') })]));
  const world = options.news.filter((s) => s.scope === 'world').sort((a, b) => (a.lang !== base) - (b.lang !== base));
  $('news-world').replaceChildren(...world.filter((s) => s.lang === base || s.lang === 'en').map((s) => sourceRow(s.id)));
  const other = $('news-other-country').value;
  $('news-other').replaceChildren(...options.news.filter((s) => other && (s.countries || []).includes(other)).map((s) => sourceRow(s.id)));
}
let newsTimer = null;
function refreshNews() {
  clearTimeout(newsTimer);
  newsTimer = setTimeout(async () => {
    const country = $('country').value;
    $('news-auto-hint').textContent = t('admin.news_auto_hint', { city: cityName() || '…', country: regionName(country) });
    if (newsAuto) {
      try {
        const q = new URLSearchParams({ country, language: $('language').value, city: cityName() });
        newsSelected = new Set((await api(`/news-auto?${q}`)).sources);
      } catch { /* keep the previous preview */ }
    }
    $('news-manual').hidden = newsAuto;
    renderNewsLists();
    renderChips();
  }, 200);
}
function addFeedRow(url = '') {
  const input = el('input', { type: 'url', placeholder: t('admin.news_feed_placeholder'), value: url, spellcheck: false });
  const [test, msg] = testButton(async () => {
    const r = await api('/test-feed', { method: 'POST', body: JSON.stringify({ url: input.value.trim() }) });
    return [r.ok, r.ok ? t('admin.feed_ok', { n: r.count, first: r.first }) : t('admin.feed_fail', { err: r.error })];
  });
  const del = el('button', { type: 'button', textContent: '✕', title: t('admin.remove') });
  const row = el('div', { className: 'item feed' }, input, test, del, msg);
  input.addEventListener('input', markDirty);
  del.addEventListener('click', () => { row.remove(); markDirty(); });
  $('feed-list').append(row);
}
function renderNews() {
  const news = cfg.news || { enabled: true, feeds: [] };
  $('news-on').checked = news.enabled !== false;
  newsAuto = news.sources == null;
  $('news-auto').checked = newsAuto;
  newsSelected = new Set(news.sources || []);
  $('news-body').hidden = !$('news-on').checked;
  const codes = Object.keys(options.countries).filter((c) => options.news.some((s) => (s.countries || []).includes(c)));
  codes.sort((a, b) => regionName(a).localeCompare(regionName(b), lang));
  fill($('news-other-country'), [['', t('admin.news_pick_country')], ...codes.map((c) => [c, regionName(c)])], '');
  $('feed-list').replaceChildren();
  for (const u of news.feeds || []) addFeedRow(u);
  refreshNews();
  const history = cfg.history || { enabled: true };
  $('history-on').checked = history.enabled !== false;
}

// ------------------------------------------------------------------ 7. photos ---
function renderPhotos() {
  const photos = cfg.photos || { folder: '', interval: 20 };
  $('photos-folder').value = photos.folder || '';
  $('photos-interval').value = photos.interval || 20;
  refreshPhotosCount();
}
let photosCountTimer = null;
async function refreshPhotosCount() {
  const folder = $('photos-folder').value.trim();
  $('photos-count').textContent = folder ? t('admin.photos_checking') : t('admin.photos_none');
  if (!folder) return;
  try {
    const { count } = await api(`/photos-count?folder=${encodeURIComponent(folder)}`);
    $('photos-count').textContent = count ? t('admin.photos_found', { n: count }) : t('admin.photos_empty');
  } catch { $('photos-count').textContent = t('admin.photos_empty'); }
}

// ------------------------------------------------------------------ 8. radio ---
let radioStations = [];
let radioStatus = { playing: false, station: null };

function stationRow(station, { onRemove } = {}) {
  const playing = radioStatus.playing && radioStatus.station?.uuid === station.uuid;
  const btn = el('button', { type: 'button', textContent: playing ? t('admin.radio_stop') : t('admin.radio_play') });
  btn.addEventListener('click', async () => {
    try {
      radioStatus = await api(playing ? '/radio-stop' : '/radio-play', playing ? { method: 'POST' } : { method: 'POST', body: JSON.stringify(station) });
    } catch (e) { $('radio-now').textContent = e.message; }
    renderRadioFavorites();
  });
  const label = el('span', {}, station.name, station.country ? el('small', { textContent: ` (${regionName(station.country)})` }) : '');
  const kids = [label, btn];
  if (onRemove) {
    const rm = el('button', { type: 'button', textContent: '✕', title: t('admin.remove') });
    rm.addEventListener('click', onRemove);
    kids.push(rm);
  }
  return el('div', { className: 'item radio' }, ...kids);
}

function renderRadioFavorites() {
  $('radio-list').replaceChildren(...radioStations.map((s) => stationRow(s, {
    onRemove: () => { radioStations = radioStations.filter((x) => x.uuid !== s.uuid); renderRadioFavorites(); markDirty(); },
  })));
  $('radio-empty').hidden = radioStations.length > 0;
  $('radio-now').textContent = radioStatus.playing && radioStatus.station
    ? t('admin.radio_now_playing', { name: radioStatus.station.name }) : '';
}

async function radioSearch() {
  const params = new URLSearchParams();
  if ($('radio-q').value.trim()) params.set('name', $('radio-q').value.trim());
  if ($('radio-country').value) params.set('country', $('radio-country').value);
  if ($('radio-language').value) params.set('language', $('radio-language').value);
  const box = $('radio-results');
  box.textContent = t('admin.loading');
  try {
    const { stations } = await api(`/radio-search?${params}`);
    box.replaceChildren(...stations.map((s) => {
      const add = el('button', { type: 'button', textContent: t('admin.radio_add') });
      add.disabled = radioStations.some((x) => x.uuid === s.uuid);
      add.addEventListener('click', () => {
        if (!radioStations.some((x) => x.uuid === s.uuid)) radioStations.push(s);
        renderRadioFavorites();
        add.disabled = true;
        markDirty();
      });
      const label = el('span', {}, s.name, s.country ? el('small', { textContent: ` (${regionName(s.country)})` }) : '');
      return el('div', { className: 'item radio' }, label, add);
    }));
    if (!stations.length) box.textContent = t('admin.radio_no_result');
  } catch (e) { box.textContent = e.message; }
}

function renderRadio() {
  const radio = cfg.radio || { stations: [], volume: 70 };
  radioStations = [...radio.stations];
  $('radio-volume').value = radio.volume ?? 70;
  fill($('radio-country'), [['', t('admin.radio_any_country')], ...Object.keys(options.countries).sort((a, b) => regionName(a).localeCompare(regionName(b), lang)).map((c) => [c, regionName(c)])], '');
  fill($('radio-language'), [['', t('admin.radio_any_language')], ...options.languages.map((l) => [l, languageName(l)])], '');
  renderRadioFavorites();
}
async function refreshRadioStatus() {
  try { radioStatus = await api('/radio-status'); } catch { /* offline: leave the last known status */ }
  renderRadioFavorites();
}

// ------------------------------------------------------------------ 9. tv ---
// The guide is only ever read, never stored: "find channels" fetches it once so the user
// can tick the ones they want; the names we got back are kept just so ticks keep their labels.
let tvChannels = [];
let tvSelected = new Set();

function renderTvChips() {
  $('tv-channels').replaceChildren(...tvChannels.map((c) => {
    const box = el('input', { type: 'checkbox', checked: tvSelected.has(c.id) });
    box.addEventListener('change', () => {
      if (box.checked) tvSelected.add(c.id); else tvSelected.delete(c.id);
      markDirty();
    });
    return el('label', { className: 'check chip' }, box, el('span', { textContent: c.name }));
  }));
  $('tv-empty').hidden = tvChannels.length > 0;
}

async function tvFind() {
  const url = $('tv-url').value.trim();
  if (!url) return;
  $('tv-message').textContent = t('admin.loading');
  try {
    const r = await api('/test-tv', { method: 'POST', body: JSON.stringify({ url }) });
    if (!r.ok) { $('tv-message').textContent = t('admin.tv_fail', { err: r.error }); return; }
    tvChannels = r.channels;
    $('tv-message').textContent = t('admin.tv_ok', { n: r.channels.length });
    renderTvChips();
    markDirty();
  } catch (e) { $('tv-message').textContent = e.message; }
}

function renderTv() {
  const tv = cfg.tv || { url: '', channels: [], prime_start: '20:00', prime_end: '23:00' };
  $('tv-url').value = tv.url || '';
  $('tv-start').value = tv.prime_start || '20:00';
  $('tv-end').value = tv.prime_end || '23:00';
  tvSelected = new Set(tv.channels || []);
  // Until "find channels" is used again, show the saved ids as their own label.
  tvChannels = [...tvSelected].map((id) => ({ id, name: id }));
  renderTvChips();
}

// ------------------------------------------------------------------ 10. voice ---
// Beranda itself only stores whether voice control is on and which wake word to listen
// for; the actual listening happens in a separate, optional service (`beranda-voice`),
// started only if that was installed with `--with-voice`.
function renderVoice() {
  const voice = cfg.voice || { enabled: false, wake_word: 'hey_jarvis' };
  $('voice-on').checked = !!voice.enabled;
  $('voice-wake-word').value = voice.wake_word || 'hey_jarvis';
  $('voice-body').hidden = !voice.enabled;
}

// ------------------------------------------------------------------ 9. screen ---
function renderScreen() {
  const screen = cfg.screen || { rotate: 0, off: '', on: '' };
  fill($('rotate'), [0, 90, 180, 270].map((r) => [String(r), t(`admin.rotate_${r}`)]), String(screen.rotate || 0));
  $('off-at').value = screen.off || '';
  $('on-at').value = screen.on || '';
}

// ------------------------------------------------------------------ 10. system ---
// Buttons that change the Pi ask for a second click instead of a pop-up.
function armed(button, run) {
  button.addEventListener('click', async () => {
    if (!button.classList.contains('confirm')) {
      const label = button.textContent;
      button.classList.add('confirm');
      button.textContent = t('admin.confirm');
      setTimeout(() => { button.classList.remove('confirm'); button.textContent = label; }, 5000);
      return;
    }
    button.classList.remove('confirm');
    button.textContent = t(button.dataset.i18n);
    await run();
  });
}
async function renderSystem() {
  const msg = $('sys-message');
  try {
    const info = await api('/system');
    $('sys-version').textContent = t('admin.version', { v: info.version }) + (info.commit ? ` (${info.commit})` : '');
    for (const id of ['sys-update', 'sys-screen', 'sys-reboot', 'sys-reset']) $(id).disabled = !info.actions;
    $('sys-screen').hidden = !info.screen;
    if (!info.installed) msg.textContent = t('admin.not_installed');
  } catch (e) { msg.textContent = e.message; }
}
async function checkUpdates() {
  const msg = $('sys-message');
  msg.textContent = '…';
  try {
    const r = await api('/system/latest');
    if (!r.latest) { msg.textContent = t('admin.search_failed'); return; }
    msg.textContent = r.update_available ? t('admin.update_available', { v: r.latest }) : t('admin.up_to_date');
    $('sys-update').hidden = !r.update_available;
  } catch (e) { msg.textContent = e.message; }
}
async function systemAction(action) {
  try {
    await api(`/system/${action}`, { method: 'POST' });
    $('sys-message').textContent = t(`admin.requested_${action.replace('-', '_')}`);
  } catch (e) { $('sys-message').textContent = e.message; }
}

// ------------------------------------------------------------------ save -----
function collect() {
  const body = {
    country: $('country').value,
    language: $('language').value,
    units: $('units').value,
    theme: cfg.theme,
    mode: cfg.mode,
    location: {
      name: cityName(),
      latitude: Number($('loc-lat').value),
      longitude: Number($('loc-lon').value),
      timezone: $('loc-tz').value,
    },
    calendar: { ics_urls: [...$('ics-list').querySelectorAll('input')].map((i) => i.value.trim()).filter(Boolean) },
    key_dates: [...$('key-list').querySelectorAll('.item')].map((row) => {
      const [d, l, k] = row.querySelectorAll('input, select');
      return { date: d.value.trim(), label: l.value.trim(), kind: k.value };
    }),
    news: {
      enabled: $('news-on').checked,
      sources: newsAuto ? null : [...newsSelected],
      feeds: [...$('feed-list').querySelectorAll('input')].map((i) => i.value.trim()).filter(Boolean),
    },
  };
  body.history = { enabled: $('history-on').checked };
  body.photos = { folder: $('photos-folder').value.trim(), interval: Number($('photos-interval').value) || 20 };
  body.radio = { stations: radioStations, volume: Number($('radio-volume').value) || 0 };
  body.tv = {
    url: $('tv-url').value.trim(),
    channels: [...tvSelected],
    prime_start: $('tv-start').value,
    prime_end: $('tv-end').value,
  };
  body.voice = { enabled: $('voice-on').checked, wake_word: $('voice-wake-word').value };
  body.screen = { rotate: Number($('rotate').value), off: $('off-at').value, on: $('on-at').value };
  if ($('subdivision').value) body.subdivision = $('subdivision').value;
  if ($('pin').value !== '') body.pin = $('pin').value;
  return body;
}

async function save(event) {
  event.preventDefault();
  if (!$('form').reportValidity()) return;
  const state = $('state');
  $('save').disabled = true;
  try {
    const body = collect();
    await api('/config', { method: 'PUT', body: JSON.stringify(body) });
    if ('pin' in body) {
      pin = body.pin;
      try { sessionStorage.setItem('beranda-pin', pin); } catch { /* ignore */ }
      $('pin').value = '';
    }
    dirty = false;
    state.textContent = t('admin.saved');
    state.className = 'ok';
    $('welcome').hidden = true;
    cfg = { ...cfg, ...body };
    if (body.language !== lang) { await loadStrings(body.language); translateStatic(); renderAll(); }
    refreshPreview();
  } catch (e) {
    state.textContent = e.status === 409 ? t('admin.demo_readonly') : `${t('admin.error')}: ${e.message}`;
    state.className = 'bad';
  } finally {
    $('save').disabled = false;
  }
}

// ------------------------------------------------------------------ boot -----
function renderAll() {
  renderPlace(); renderRegion(); renderLook(); renderCalendarGuide(); renderNews(); renderPhotos(); renderRadio(); renderTv(); renderVoice(); renderScreen(); renderSystem();
  $('ics-list').replaceChildren();
  $('key-list').replaceChildren();
  for (const u of cfg.calendar.ics_urls) addIcsRow(u);
  for (const k of cfg.key_dates) addKeyRow(k);
}

async function start() {
  const data = await api('/config');
  cfg = data.config;
  options = data.options;
  editable = data.editable;
  await loadStrings(cfg.language);
  translateStatic();
  $('gate').hidden = true;
  $('app').hidden = false;
  $('welcome').hidden = !data.first_run;
  renderAll();
  $('pin').placeholder = data.pin_set ? '••••' : '';
  if (!editable) { $('state').textContent = t('admin.demo_readonly'); $('state').className = 'bad'; }
  fitPreview();
  refreshPreview();
  refreshRadioStatus();
  setInterval(refreshRadioStatus, 10_000);
}

async function boot() {
  await loadStrings(navigator.language || 'en');
  translateStatic();
  $('form').addEventListener('submit', save);
  $('form').addEventListener('change', (e) => {
    if (e.target.id === 'units') unitsTouched = true;
    if (e.target.id === 'language') { languageTouched = true; refreshPreview(); refreshNews(); }
    if (e.target.id !== 'q' && e.target.id !== 'news-other-country') markDirty();
  });
  $('country').addEventListener('change', onCountry);
  $('loc-name').addEventListener('change', refreshNews);
  $('photos-folder').addEventListener('input', () => {
    clearTimeout(photosCountTimer);
    photosCountTimer = setTimeout(refreshPhotosCount, 500);
  });
  $('q-go').addEventListener('click', search);
  $('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); search(); } });
  $('radio-go').addEventListener('click', radioSearch);
  $('radio-q').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); radioSearch(); } });
  $('tv-find').addEventListener('click', tvFind);
  $('ics-add').addEventListener('click', () => { addIcsRow(); markDirty(); });
  $('key-add').addEventListener('click', () => { addKeyRow(); markDirty(); });
  $('feed-add').addEventListener('click', () => { addFeedRow(); markDirty(); });
  $('news-on').addEventListener('change', () => { $('news-body').hidden = !$('news-on').checked; });
  $('voice-on').addEventListener('change', () => { $('voice-body').hidden = !$('voice-on').checked; });
  $('news-auto').addEventListener('change', () => { newsAuto = $('news-auto').checked; refreshNews(); });
  $('news-other-country').addEventListener('change', renderNewsLists);
  $('sys-check').addEventListener('click', checkUpdates);
  for (const id of ['sys-update', 'sys-screen', 'sys-reboot', 'sys-reset']) armed($(id), () => systemAction($(id).dataset.action));
  $('tz-device').addEventListener('click', () => {
    fill($('loc-tz'), [...$('loc-tz').options].map((o) => [o.value, o.value]), Intl.DateTimeFormat().resolvedOptions().timeZone);
    markDirty();
  });
  window.addEventListener('resize', fitPreview);
  window.addEventListener('beforeunload', (e) => { if (dirty) e.preventDefault(); });
  $('gate-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    pin = $('pin-input').value;
    try { await start(); try { sessionStorage.setItem('beranda-pin', pin); } catch { /* ignore */ } }
    catch { $('gate-error').textContent = t('admin.pin_wrong'); $('gate-error').hidden = false; }
  });

  try {
    const status = await api('/status');
    if (status.pin_required && !pin) throw Object.assign(new Error('pin'), { status: 401 });
    await start();
  } catch (err) {
    $('gate').hidden = false;
    if (err.status === 401) {
      $('gate-label').textContent = t('admin.enter_pin');
      $('gate-btn').textContent = t('admin.unlock');
    } else {
      const text = err.status === 403 ? t('admin.forbidden') : `${t('admin.error')}: ${err.message}`;
      $('gate-form').replaceChildren(el('p', { className: 'error', textContent: text }));
    }
  }
}

boot();
