// Beranda settings page. Vanilla JS, no build step. Talks only to /api/admin/*.
// Written for people who are not technical: every section explains itself.

import { createRadio } from '/static/radio.js';
import * as voiceApi from '/static/voice.js';

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
let limits = {};  // the most this computer may hold (see limits.py): calendars, news_sources, tv_channels...
let currentPort = 8080;  // the port this server listens on (from /system)
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
  $('menu-label').textContent = t('admin.menu');
  $('coffee-label').textContent = t('admin.coffee');
  $('menu-coffee-label').textContent = `☕ ${t('admin.coffee')}`;
  $('coffee').title = t('admin.coffee_hint');
  buildMenu();
  document.title = `Beranda · ${t('admin.title')}`;
}

// ------------------------------------------------------------------ api ----
async function api(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(pin ? { 'X-Beranda-Pin': pin } : {}), ...(opts.headers || {}) };
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

// ------------------------------------------------------------------ limits ---
// Each list has a maximum that depends on the computer (a small Raspberry Pi cannot follow 80
// news feeds). When the maximum is reached the page says so and does not add one more.
let limitTimer = null;
function atLimit(kind, count, anchor) {
  const max = limits[kind];
  if (!max || count < max) return false;
  const card = (anchor || document.body).closest?.('.card') || $('sec-system');
  let note = card.querySelector('.limit-note');
  if (!note) { note = el('p', { className: 'error limit-note', role: 'status' }); card.querySelector('h2').after(note); }
  note.textContent = t('admin.limit_reached', { n: max, what: t(`admin.limit_${kind}`) });
  note.hidden = false;
  clearTimeout(limitTimer);
  limitTimer = setTimeout(() => { note.hidden = true; }, 8000);
  return true;
}
const newsCount = () => $('feed-list').children.length + (newsAuto ? 0 : newsSelected.size);

// ------------------------------------------------------------------ burger menu ---
// One entry per card of the page (built from the card titles, so it follows the language).
function buildMenu() {
  const items = [...document.querySelectorAll('#form > section.card[id]')].filter((s) => !s.hidden && s.querySelector('h2 .num'));
  $('menu-list').replaceChildren(...items.map((section) => {
    const num = section.querySelector('h2 .num').textContent;
    const title = section.querySelector('h2 [data-i18n]')?.textContent || '';
    const a = el('a', { href: `#${section.id}` }, el('span', { className: 'num', textContent: num }), el('span', { textContent: title }));
    a.addEventListener('click', (e) => {
      e.preventDefault();
      closeMenu();
      const calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      section.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
    });
    return el('li', {}, a);
  }));
  $('menu-btn').hidden = !items.length || $('app').hidden;
}
function closeMenu() {
  $('menu').hidden = true;
  $('menu-btn').setAttribute('aria-expanded', 'false');
}
function toggleMenu() {
  const open = $('menu').hidden;
  $('menu').hidden = !open;
  $('menu-btn').setAttribute('aria-expanded', String(open));
  if (open) $('menu-list').querySelector('a')?.focus();
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
  $('q-note').hidden = true;
  if (q.length < 2) { list.hidden = true; return; }
  try {
    const { results } = await api(`/geocode?q=${encodeURIComponent(q)}&language=${lang}`);
    list.replaceChildren(...results.map((r) => {
      const b = el('button', { type: 'button' }, `${r.name} `, el('small', { textContent: [r.region, r.country && regionName(r.country)].filter(Boolean).join(', ') }));
      b.addEventListener('click', () => {
        $('loc-name').value = r.name;
        $('loc-lat').value = Math.round(r.latitude * 1e4) / 1e4;  // 4 decimals = about 10 m, plenty
        $('loc-lon').value = Math.round(r.longitude * 1e4) / 1e4;
        // A new town: everything that belonged to the old one is replaced, never kept by mistake.
        $('w-area').value = r.area || '';  // area of the weather warnings (the new town's county / region)
        $('w-area-msg').textContent = '';
        if (r.timezone) fill($('loc-tz'), [...$('loc-tz').options].map((o) => [o.value, o.value]), r.timezone);
        if (r.country && options.countries[r.country]) { $('country').value = r.country; onCountry(); }
        list.hidden = true;
        $('q-note').textContent = t('admin.city_changed');  // the region was reset: say so
        $('q-note').hidden = false;
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
    const when = (e) => new Intl.DateTimeFormat(lang, { weekday: 'short', day: 'numeric', month: 'short' }).format(new Date(e.start));
    return [r.ok, r.ok ? t('admin.test_ok', { n: r.count, next: r.next.map((e) => `${when(e)} ${e.title}`).join(' · ') }) : t('admin.test_fail', { err: r.error })];
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
    if (box.checked && atLimit('news_sources', newsCount(), box)) { box.checked = false; return; }
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
// Pictures are sent straight away (no need to press Save): one request per picture, the file
// itself as the request body. Beranda keeps them in its own folder, shown below the buttons.
function renderPhotos() {
  const photos = cfg.photos || { folder: '', interval: 20, dropbox_url: '' };
  $('photos-folder').value = photos.folder || '';
  $('photos-interval').value = photos.interval || 20;
  $('photos-dropbox').value = photos.dropbox_url || '';
  refreshPhotosCount();
  loadPhotos();
}
async function loadPhotos() {
  try {
    const data = await api('/photos');
    $('photos-where').textContent = t('admin.photos_where', { folder: data.folder });
    $('photos-empty').hidden = data.names.length > 0;
    $('photos-grid').replaceChildren(...data.names.slice(0, 60).map((name) => {
      const rm = el('button', { type: 'button', textContent: '✕', title: t('admin.remove') });
      rm.addEventListener('click', async () => {
        try { await api(`/photos/${encodeURIComponent(name)}`, { method: 'DELETE' }); } catch (e) { $('photos-upload-msg').textContent = e.message; }
        loadPhotos();
      });
      return el('div', { className: 'thumb' }, el('img', { src: `/api/photos/${encodeURIComponent(name)}`, alt: '', loading: 'lazy' }), rm);
    }));
    showDropboxStatus(data.dropbox);
  } catch { /* the page is still loading, or offline */ }
}
function showDropboxStatus(d) {
  const box = $('photos-sync-msg');
  if (!d || !d.at) { box.textContent = ''; return; }
  box.textContent = d.ok ? t('admin.photos_sync_ok', { n: d.total, added: d.added })
    : t('admin.photos_sync_fail', { err: t(`admin.photos_err_${d.code || 'net'}`) });
}
async function uploadPhotos(files) {
  const msg = $('photos-upload-msg');
  let sent = 0;
  for (const file of files) {
    msg.textContent = t('admin.photos_sending', { i: sent + 1, n: files.length });
    try {
      await api(`/photos?name=${encodeURIComponent(file.name)}`, { method: 'POST', body: file, headers: { 'Content-Type': file.type || 'application/octet-stream' } });
      sent += 1;
    } catch (e) {
      const err = e.status === 422 ? t('admin.photos_bad') : e.status === 413 ? t('admin.photos_err_big')
        : e.status === 409 ? t('admin.limit_reached', { n: limits.photos, what: t('admin.limit_photos') }) : e.message;
      msg.textContent = t('admin.photos_refused', { name: file.name, err });
      await loadPhotos();
      return;
    }
  }
  msg.textContent = t('admin.photos_sent', { n: sent });
  await loadPhotos();
}
async function syncDropbox() {
  const box = $('photos-sync-msg');
  const link = $('photos-dropbox').value.trim();
  if (link !== (cfg.photos?.dropbox_url || '')) { box.textContent = t('admin.photos_save_first'); return; }
  if (!link) { box.textContent = t('admin.photos_dropbox_empty'); return; }
  box.textContent = t('admin.loading');
  try { showDropboxStatus(await api('/photos-sync', { method: 'POST' })); await loadPhotos(); }
  catch (e) { box.textContent = e.message; }
}
let photosCountTimer = null;
async function refreshPhotosCount() {
  const folder = $('photos-folder').value.trim();
  $('photos-count').textContent = '';
  if (!folder) return;
  $('photos-count').textContent = t('admin.photos_checking');
  try {
    const { count } = await api(`/photos-count?folder=${encodeURIComponent(folder)}`);
    $('photos-count').textContent = count ? t('admin.photos_found', { n: count }) : t('admin.photos_empty');
  } catch { $('photos-count').textContent = t('admin.photos_empty'); }
}

// ------------------------------------------------------------------ 8. radio ---
// The sound plays in this page (on the device you are holding), which is also how it plays
// on the tablet showing Beranda - so "Listen" here is a true test of what the tablet will do.
let radioStations = [];
const adminRadio = createRadio($('admin-audio'), () => renderRadioFavorites());

function stationRow(station, { onRemove } = {}) {
  const snap = adminRadio.snapshot();
  const here = snap.station?.url === station.url;
  const playing = here && (snap.status === 'playing' || snap.status === 'loading');
  const btn = el('button', { type: 'button', textContent: playing ? t('admin.radio_stop') : t('admin.radio_play') });
  btn.addEventListener('click', () => (playing ? adminRadio.stop() : adminRadio.play(station)));
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
  const snap = adminRadio.snapshot();
  $('radio-now').textContent = snap.status === 'playing' ? t('admin.radio_now_playing', { name: snap.station.name })
    : snap.status === 'loading' ? t('admin.loading')
    : snap.status === 'error' ? t('admin.radio_error') : '';
}

// Long lists can be folded away with one button, so the settings page stays short.
let radioResultsOpen = true;
function paintRadioResults(count) {
  if (count !== undefined) {  // undefined = just folding/unfolding: leave the header as it is
    $('radio-results-head').hidden = count === null || count === 0;
    if (count) $('radio-results-count').textContent = t('admin.results_count', { n: count });
  }
  $('radio-results').hidden = !radioResultsOpen;
  $('radio-results-toggle').textContent = radioResultsOpen ? t('admin.hide_list') : t('admin.show_list');
}

async function radioSearch() {
  const params = new URLSearchParams();
  if ($('radio-q').value.trim()) params.set('name', $('radio-q').value.trim());
  if ($('radio-country').value) params.set('country', $('radio-country').value);
  if ($('radio-language').value) params.set('language', $('radio-language').value);
  const box = $('radio-results');
  box.hidden = false;
  box.textContent = t('admin.loading');
  try {
    const { stations } = await api(`/radio-search?${params}`);
    box.replaceChildren(...stations.map((s) => {
      const add = el('button', { type: 'button', textContent: t('admin.radio_add') });
      add.disabled = radioStations.some((x) => x.uuid === s.uuid);
      add.addEventListener('click', () => {
        if (atLimit('radio_stations', radioStations.length, add)) return;
        if (!radioStations.some((x) => x.uuid === s.uuid)) radioStations.push(s);
        renderRadioFavorites();
        add.disabled = true;
        markDirty();
      });
      const label = el('span', {}, s.name, s.country ? el('small', { textContent: ` (${regionName(s.country)})` }) : '');
      return el('div', { className: 'item radio' }, label, add);
    }));
    radioResultsOpen = true;  // a new search always opens the list
    if (!stations.length) box.textContent = t('admin.radio_no_result');
    paintRadioResults(stations.length);
  } catch (e) { box.textContent = e.message; paintRadioResults(null); }
}

function renderRadio() {
  $('radio-results-toggle').onclick = () => { radioResultsOpen = !radioResultsOpen; paintRadioResults(undefined); };
  const radio = cfg.radio || { stations: [], volume: 70 };
  radioStations = [...radio.stations];
  $('radio-volume').value = radio.volume ?? 70;
  adminRadio.defaultVolume(radio.volume ?? 70);
  fill($('radio-country'), [['', t('admin.radio_any_country')], ...Object.keys(options.countries).sort((a, b) => regionName(a).localeCompare(regionName(b), lang)).map((c) => [c, regionName(c)])], '');
  fill($('radio-language'), [['', t('admin.radio_any_language')], ...options.languages.map((l) => [l, languageName(l)])], '');
  renderRadioFavorites();
}
// ------------------------------------------------------------------ 9. tv ---
// The guide is only ever read, never stored: "find channels" fetches it once so the user
// can tick the ones they want; the names we got back are kept just so ticks keep their labels.
let tvChannels = [];
let tvSelected = new Set();

const TV_SHOWN_MAX = 150;  // thousands of checkboxes would make the page sluggish: filter instead
let tvOpen = true;

function renderTvChips() {
  const q = $('tv-filter').value.trim().toLowerCase();
  const only = $('tv-only').checked;
  // Ticked channels first, so the user's choices are always at the top of the list.
  const ordered = [...tvChannels].sort((a, b) => Number(tvSelected.has(b.id)) - Number(tvSelected.has(a.id)));
  const matching = ordered.filter((c) => (!q || c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q))
    && (!only || tvSelected.has(c.id)));
  $('tv-channels').replaceChildren(...matching.slice(0, TV_SHOWN_MAX).map((c) => {
    const box = el('input', { type: 'checkbox', checked: tvSelected.has(c.id) });
    box.addEventListener('change', () => {
      if (box.checked && atLimit('tv_channels', tvSelected.size, box)) { box.checked = false; return; }
      if (box.checked) tvSelected.add(c.id); else tvSelected.delete(c.id);
      $('tv-count').textContent = t('admin.tv_count', { n: tvChannels.length, k: tvSelected.size });
      markDirty();
    });
    return el('label', { className: 'check chip' }, box, el('span', { textContent: c.name }));
  }));
  const more = matching.length - TV_SHOWN_MAX;
  $('tv-more').hidden = more <= 0 || !tvOpen;
  if (more > 0) $('tv-more').textContent = t('admin.tv_more', { n: more });
  $('tv-empty').hidden = tvChannels.length > 0;
  $('tv-head').hidden = tvChannels.length === 0;
  $('tv-tools').hidden = tvChannels.length === 0 || !tvOpen;
  $('tv-channels').hidden = !tvOpen;
  $('tv-count').textContent = t('admin.tv_count', { n: tvChannels.length, k: tvSelected.size });
  $('tv-toggle').textContent = tvOpen ? t('admin.hide_list') : t('admin.show_list');
}

// Which free guides exist for the chosen country? The server tries each known address and
// keeps those that answer; one tap fills the address in and lists the channels.
async function tvSuggest() {
  const box = $('tv-suggestions');
  const msg = $('tv-suggest-msg');
  box.replaceChildren();
  msg.textContent = t('admin.tv_suggest_searching');
  try {
    const r = await api(`/tv-guides?country=${encodeURIComponent($('country').value)}`);
    if (!r.guides.length) { msg.textContent = t('admin.tv_suggest_none', { country: regionName(r.country) }); return; }
    msg.textContent = t('admin.tv_suggest_found', { country: regionName(r.country) });
    box.replaceChildren(...r.guides.map((g) => {
      const b = el('button', { type: 'button', textContent: g.name });
      b.addEventListener('click', () => { $('tv-url').value = g.url; markDirty(); tvFind(); });
      return b;
    }));
  } catch (e) { msg.textContent = e.message; }
}

async function tvFind() {
  const url = $('tv-url').value.trim();
  if (!url) return;
  $('tv-message').textContent = t('admin.loading');
  try {
    const r = await api('/test-tv', { method: 'POST', body: JSON.stringify({ url }) });
    if (!r.ok) { $('tv-message').textContent = t('admin.tv_fail', { err: r.error }); return; }
    tvChannels = r.channels;
    // Ticks made on another guide mean nothing here (each guide has its own channel codes).
    const known = new Set(r.channels.map((c) => c.id));
    tvSelected = new Set([...tvSelected].filter((id) => known.has(id)));
    $('tv-message').textContent = t('admin.tv_ok', { n: r.channels.length });
    renderTvChips();
    markDirty();
  } catch (e) { $('tv-message').textContent = e.message; }
}

function renderTv() {
  $('tv-toggle').onclick = () => { tvOpen = !tvOpen; renderTvChips(); };
  $('tv-filter').oninput = renderTvChips;
  $('tv-only').onchange = renderTvChips;
  const tv = cfg.tv || { url: '', channels: [] };
  $('tv-url').value = tv.url || '';
  tvSelected = new Set(tv.channels || []);
  // Until "find channels" is used again, show the saved ids as their own label.
  tvChannels = [...tvSelected].map((id) => ({ id, name: id }));
  renderTvChips();
}

// ------------------------------------------------------------------ 10. voice ---
// Beranda only stores whether voice control is on. Listening happens in the browser of the
// tablet that shows the display, so here we just tell whether THIS device could do it.
let voiceCommands = [];
const VOICE_ACTIONS = ['radio_play', 'radio_stop', 'radio_next', 'radio_prev', 'volume_up', 'volume_down', 'weather', 'time', 'tv', 'say'];

function renderVoiceCommands() {
  $('voice-commands').replaceChildren(...voiceCommands.map((c, i) => {
    const phrase = el('input', { className: 'v-phrase', type: 'text', value: c.phrase, maxLength: 80, placeholder: t('admin.voice_phrase_ph') });
    phrase.addEventListener('input', () => { c.phrase = phrase.value; markDirty(); });
    const action = el('select', { className: 'v-action' });
    fill(action, VOICE_ACTIONS.map((a) => [a, t(`admin.voice_act_${a}`)]), c.action);
    action.addEventListener('change', () => { c.action = action.value; renderVoiceCommands(); markDirty(); });
    let extra = el('span', { className: 'v-extra' });  // most actions need nothing more
    if (c.action === 'say') {
      extra = el('input', { className: 'v-extra', type: 'text', value: c.reply || '', maxLength: 200, placeholder: t('admin.voice_reply_ph') });
      extra.addEventListener('input', () => { c.reply = extra.value; markDirty(); });
    } else if (c.action === 'radio_play') {
      extra = el('select', { className: 'v-extra' });
      fill(extra, [['', t('admin.voice_any_station')], ...radioStations.map((s) => [s.uuid, s.name])], c.station || '');
      extra.addEventListener('change', () => { c.station = extra.value; markDirty(); });
    }
    const rm = el('button', { className: 'v-rm', type: 'button', textContent: '✕', title: t('admin.remove') });
    rm.addEventListener('click', () => { voiceCommands.splice(i, 1); renderVoiceCommands(); markDirty(); });
    return el('div', { className: 'item voice' }, phrase, action, extra, rm);
  }));
  $('voice-add').disabled = voiceCommands.length >= 50;
}

// The built-in phrases, in the language chosen for the display (that is the language the
// tablet listens in), so the user can see exactly what to say.
async function renderVoiceDefaults() {
  const box = $('voice-defaults');
  try {
    const r = await api(`/voice-commands?language=${encodeURIComponent($('language').value)}`);
    $('voice-defaults-summary').textContent = t('admin.voice_defaults_show', { language: languageName(r.language) });
    const dl = el('dl');
    for (const [intent, phrases] of Object.entries(r.commands)) {
      dl.append(el('dt', { textContent: t(`admin.voice_act_${intent}`) }), el('dd', { textContent: phrases.map((p) => `« ${p} »`).join('  ·  ') }));
    }
    box.replaceChildren(dl);
  } catch (e) { box.textContent = e.message; }
}

function renderVoice() {
  const voice = cfg.voice || { enabled: false };
  $('voice-on').checked = !!voice.enabled;
  $('voice-check').hidden = !voice.enabled;
  $('voice-check').textContent = t(`admin.voice_check_${voiceApi.availability()}`);
  voiceCommands = (voice.commands || []).map((c) => ({ ...c }));
  renderVoiceCommands();
  renderVoiceDefaults();
}

// ------------------------------------------------------------------ widgets ---
// Small optional extras of the main screen. Each one can be switched off.
function renderWidgets() {
  const w = cfg.widgets || {};
  $('w-chart').checked = w.chart !== false;
  $('w-air').checked = w.air !== false;
  $('w-eph').checked = w.ephemeris !== false;
  $('w-alerts').checked = !!w.alerts;
  $('w-area').value = w.alerts_area || '';
  $('w-clock2').checked = !!w.second_clock;
  $('w-clock2-tz').value = w.second_clock || '';
  const zones = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : [];
  $('tz-list').replaceChildren(...zones.map((z) => el('option', { value: z })));
  $('w-area-msg').textContent = '';
  showWidgetBodies();
}
function showWidgetBodies() {
  $('w-alerts-body').hidden = !$('w-alerts').checked;
  $('w-clock2-body').hidden = !$('w-clock2').checked;
}
// Ask the warning service once, and say in plain words whether the typed area is understood.
async function testAlertsArea() {
  const msg = $('w-area-msg');
  const area = $('w-area').value.trim();
  if (!area) { msg.textContent = t('admin.w_area_empty'); return; }
  msg.textContent = '…';
  try {
    const r = await api('/test-alerts', { method: 'POST', body: JSON.stringify({ country: $('country').value, area }) });
    if (!r.ok) {
      msg.textContent = r.error === 'unsupported' ? t('admin.w_area_unsupported') : t('admin.w_area_error');
    } else if (r.mine.length) {
      msg.textContent = t('admin.w_area_found', { n: r.mine.length, area });
    } else {
      const others = r.warned_areas.length ? ` ${t('admin.w_area_others', { list: r.warned_areas.slice(0, 12).join(', ') })}` : '';
      msg.textContent = t('admin.w_area_calm', { area }) + others;
    }
  } catch (e) { msg.textContent = e.message; }
}
function collectWidgets() {
  const zone = $('w-clock2').checked ? $('w-clock2-tz').value.trim() : '';
  return {
    chart: $('w-chart').checked,
    air: $('w-air').checked,
    ephemeris: $('w-eph').checked,
    alerts: $('w-alerts').checked,
    alerts_area: $('w-area').value.trim(),
    second_clock: zone,
  };
}
// A time zone typed by hand must be a real one, otherwise the clock would just stay hidden.
function validZone(zone) {
  if (!zone) return true;
  try { new Intl.DateTimeFormat('en', { timeZone: zone }); return true; } catch { return false; }
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
    $('sys-device').textContent = t('admin.device_line', {
      device: limits.device ? limits.device.replace(/ Rev [\d.]+$/, '') : t('admin.device_other'),
      mem: limits.memory_gb, profile: t(`admin.profile_${limits.profile}`),
    });
    for (const id of ['sys-update', 'sys-screen', 'sys-reboot', 'sys-reset']) $(id).disabled = !info.actions;
    currentPort = info.port;
    $('port-current').textContent = t('admin.port_current', { port: info.port })
      + (info.saved_port !== info.port ? ` ${t('admin.port_pending', { port: info.saved_port })}` : '');
    if (!$('port-new').value) $('port-new').placeholder = String(info.port);
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
// The word that confirms a reset: "yes" in the language of the page (no accents or capitals needed).
const plain = (text) => String(text).normalize('NFD').replace(/\p{M}/gu, '').trim().toLowerCase();
function resetWordOk() { return plain($('reset-word').value) === plain(t('admin.reset_word')); }
function openReset() {
  $('reset-box').hidden = false;
  $('reset-prompt').textContent = t('admin.reset_prompt', { word: t('admin.reset_word') });
  $('reset-word').value = '';
  $('reset-go').disabled = true;
  $('reset-word').focus();
}
function closeReset() { $('reset-box').hidden = true; $('reset-word').value = ''; }
async function systemAction(action, body, messageId = 'sys-message') {
  try {
    await api(`/system/${action}`, { method: 'POST', ...(body ? { body: JSON.stringify(body) } : {}) });
    $(messageId).textContent = t(`admin.requested_${action.replace('-', '_')}`);
    if (action === 'reset' && currentPort !== 8080) $(messageId).append(' ', t('admin.reset_port_note', { url: addressWithPort(8080) }));
  } catch (e) { $(messageId).textContent = e.message; }
}

// ------------------------------------------------------------------ 11. advanced user ---
// The same address as this page, with another port.
function addressWithPort(port) {
  const url = new URL(location.href);
  url.port = String(port);
  url.pathname = '/admin';
  url.search = '';
  url.hash = '';
  return url.href;
}
async function changePort() {
  const msg = $('port-msg');
  const port = Number($('port-new').value);
  msg.replaceChildren();
  if (!Number.isInteger(port) || port < 1024 || port > 65535) { msg.textContent = t('admin.port_err_range'); return; }
  if (port === currentPort) { msg.textContent = t('admin.port_err_same'); return; }
  msg.textContent = '…';
  try {
    const r = await api('/system/port', { method: 'POST', body: JSON.stringify({ port, confirmed: true }) });
    const address = addressWithPort(r.port);
    const link = el('a', { href: address, textContent: t('admin.port_open_new') });
    if (r.restarting) {
      msg.replaceChildren(t('admin.port_done', { url: address }), ' ', link);
      setTimeout(() => { location.assign(address); }, 12000);  // the new server needs a few seconds
    } else {
      msg.replaceChildren(t('admin.port_done_manual', { url: address }));
    }
  } catch (e) {
    const code = /^port_(range|busy|same)$/.exec(e.message);
    msg.textContent = code ? t(`admin.port_err_${code[1]}`) : e.message;
  }
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
  body.photos = {
    folder: $('photos-folder').value.trim(),
    interval: Number($('photos-interval').value) || 20,
    dropbox_url: $('photos-dropbox').value.trim(),
  };
  body.radio = { stations: radioStations, volume: Number($('radio-volume').value) || 0 };
  body.tv = { url: $('tv-url').value.trim(), channels: [...tvSelected] };
  body.voice = {
    enabled: $('voice-on').checked,
    commands: voiceCommands.filter((c) => c.phrase.trim()).map((c) => ({ phrase: c.phrase.trim(), action: c.action, station: c.station || '', reply: c.reply || '' })),
  };
  body.widgets = collectWidgets();
  body.screen = { rotate: Number($('rotate').value), off: $('off-at').value, on: $('on-at').value };
  if ($('subdivision').value) body.subdivision = $('subdivision').value;
  if ($('pin').value !== '') body.pin = $('pin').value;
  return body;
}

async function save(event) {
  event.preventDefault();
  if (!$('form').reportValidity()) return;
  const state = $('state');
  const zoneBad = $('w-clock2').checked && !validZone($('w-clock2-tz').value.trim());
  $('w-clock2-err').hidden = !zoneBad;
  if (zoneBad) {
    $('w-clock2-err').textContent = t('admin.w_clock2_bad');
    $('w-clock2-tz').scrollIntoView({ block: 'center' });
    return;
  }
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
  renderPlace(); renderRegion(); renderLook(); renderCalendarGuide(); renderNews(); renderPhotos(); renderRadio(); renderTv(); renderVoice(); renderWidgets(); renderScreen(); renderSystem();
  $('ics-list').replaceChildren();
  $('key-list').replaceChildren();
  for (const u of cfg.calendar.ics_urls) addIcsRow(u);
  for (const k of cfg.key_dates) addKeyRow(k);
}

async function start() {
  const data = await api('/config');
  cfg = data.config;
  options = data.options;
  limits = data.limits || {};
  editable = data.editable;
  await loadStrings(cfg.language);
  translateStatic();
  $('gate').hidden = true;
  $('app').hidden = false;
  buildMenu();
  $('welcome').hidden = !data.first_run;
  renderAll();
  $('pin').placeholder = data.pin_set ? '••••' : '';
  if (!editable) { $('state').textContent = t('admin.demo_readonly'); $('state').className = 'bad'; }
  fitPreview();
  refreshPreview();
  if (!cfg.tv?.url) tvSuggest();  // first visit: offer the guides for the country straight away
}

async function boot() {
  await loadStrings(navigator.language || 'en');
  translateStatic();
  $('form').addEventListener('submit', save);
  $('form').addEventListener('change', (e) => {
    if (e.target.id === 'units') unitsTouched = true;
    if (e.target.id === 'language') { languageTouched = true; refreshPreview(); refreshNews(); }
    if (!['q', 'news-other-country', 'reset-word', 'port-new'].includes(e.target.id)) markDirty();
  });
  $('country').addEventListener('change', onCountry);
  $('loc-name').addEventListener('change', refreshNews);
  $('photos-folder').addEventListener('input', () => {
    clearTimeout(photosCountTimer);
    photosCountTimer = setTimeout(refreshPhotosCount, 500);
  });
  $('q-go').addEventListener('click', search);
  $('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); search(); } });
  $('radio-volume').addEventListener('input', (e) => adminRadio.setVolume(e.target.value));  // hear it as you slide
  $('radio-go').addEventListener('click', radioSearch);
  $('radio-q').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); radioSearch(); } });
  $('tv-find').addEventListener('click', tvFind);
  $('tv-suggest').addEventListener('click', tvSuggest);
  $('photos-file').addEventListener('change', (e) => { uploadPhotos([...e.target.files]); e.target.value = ''; });
  $('photos-sync').addEventListener('click', syncDropbox);
  $('ics-add').addEventListener('click', () => { if (atLimit('calendars', $('ics-list').children.length, $('ics-add'))) return; addIcsRow(); markDirty(); });
  $('key-add').addEventListener('click', () => { if (atLimit('key_dates', $('key-list').children.length, $('key-add'))) return; addKeyRow(); markDirty(); });
  $('feed-add').addEventListener('click', () => { if (atLimit('news_sources', newsCount(), $('feed-add'))) return; addFeedRow(); markDirty(); });
  $('news-on').addEventListener('change', () => { $('news-body').hidden = !$('news-on').checked; });
  $('voice-add').addEventListener('click', () => { if (atLimit('voice_commands', voiceCommands.length, $('voice-add'))) return; voiceCommands.push({ phrase: '', action: 'say', station: '', reply: '' }); renderVoiceCommands(); markDirty(); });
  $('language').addEventListener('change', renderVoiceDefaults);
  $('voice-on').addEventListener('change', () => { $('voice-check').hidden = !$('voice-on').checked; });
  $('news-auto').addEventListener('change', () => { newsAuto = $('news-auto').checked; refreshNews(); });
  $('news-other-country').addEventListener('change', renderNewsLists);
  $('sys-check').addEventListener('click', checkUpdates);
  for (const id of ['sys-update', 'sys-screen', 'sys-reboot']) armed($(id), () => systemAction($(id).dataset.action));
  // Starting again from zero: no double-click shortcut, the word has to be typed.
  $('sys-reset').addEventListener('click', openReset);
  $('reset-word').addEventListener('input', () => { $('reset-go').disabled = !resetWordOk(); });
  $('reset-word').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); $('reset-go').click(); } });
  $('reset-cancel').addEventListener('click', closeReset);
  $('reset-go').addEventListener('click', async () => {
    if (!resetWordOk()) return;
    closeReset();
    await systemAction('reset', { confirmed: true }, 'adv-message');
  });
  armed($('port-apply'), changePort);
  $('port-new').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); $('port-apply').click(); } });
  $('w-alerts').addEventListener('change', showWidgetBodies);
  $('w-clock2').addEventListener('change', showWidgetBodies);
  $('w-area-test').addEventListener('click', testAlertsArea);
  $('w-clock2-tz').addEventListener('input', () => { $('w-clock2-err').hidden = true; });
  $('menu-btn').addEventListener('click', toggleMenu);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !$('menu').hidden) { closeMenu(); $('menu-btn').focus(); } });
  document.addEventListener('click', (e) => { if (!$('menu').hidden && !e.target.closest('#menu, #menu-btn')) closeMenu(); });
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
