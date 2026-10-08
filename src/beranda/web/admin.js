// Beranda admin page. Vanilla JS, no build step. Talks only to /api/admin/*.

const $ = (id) => document.getElementById(id);
const THEME_COLORS = {
  japan: ['#f4efe4', '#bf3b2b', '#2f5d8a', '#23201d'],
  indonesia: ['#f3e8d0', '#b5651d', '#1f4a73', '#3a2518'],
  france: ['#f6f3ec', '#c8372d', '#2a4d8f', '#1b2340'],
};
const KINDS = ['birth', 'death', 'anniversary', 'other'];
const IMPERIAL = new Set(['US', 'LR', 'MM']);

let strings = {};
let lang = 'en';
let options = { countries: {}, languages: [], themes: [] };
let cfg = null;
let editable = true;
let dirty = false;
let unitsTouched = false;
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
  const short = String(code).slice(0, 2).toLowerCase();
  const en = await get('en');
  strings = short === 'en' ? en : merge(en, await get(short));
  lang = short;
  document.documentElement.lang = short;
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
  if (current != null && ![...select.options].some((o) => o.value === current)) {
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
  const s = $('state');
  s.textContent = t('admin.unsaved');
  s.className = '';
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
  $('preview').style.setProperty('--s', ($('frame').clientWidth / 1280).toFixed(4));
}

// ------------------------------------------------------------------ render ---
function renderPlace() {
  $('loc-name').value = cfg.location.name;
  $('loc-lat').value = cfg.location.latitude;
  $('loc-lon').value = cfg.location.longitude;
  const zones = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : [];
  fill($('loc-tz'), zones.map((z) => [z, z]), cfg.location.timezone);
}

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

function renderLook() {
  const box = $('themes');
  box.replaceChildren(...options.themes.map((name) => {
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

function addIcsRow(url = '') {
  const input = el('input', { type: 'url', placeholder: t('admin.ics_placeholder'), value: url, spellcheck: false });
  const test = el('button', { type: 'button', textContent: t('admin.test') });
  const del = el('button', { type: 'button', textContent: '✕', title: t('admin.remove') });
  const msg = el('div', { className: 'msg', hidden: true });
  const row = el('div', { className: 'item ics' }, input, test, del, msg);
  input.addEventListener('input', markDirty);
  del.addEventListener('click', () => { row.remove(); markDirty(); });
  test.addEventListener('click', async () => {
    msg.hidden = false; msg.className = 'msg'; msg.textContent = '…';
    try {
      const r = await api('/test-ics', { method: 'POST', body: JSON.stringify({ url: input.value.trim() }) });
      msg.className = `msg ${r.ok ? 'ok' : 'bad'}`;
      msg.textContent = r.ok ? t('admin.test_ok', { n: r.count, next: r.next.join(' · ') }) : t('admin.test_fail', { err: r.error });
    } catch (e) { msg.className = 'msg bad'; msg.textContent = e.message; }
  });
  $('ics-list').append(row);
}

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

function renderLists() {
  $('ics-list').replaceChildren();
  $('key-list').replaceChildren();
  for (const u of cfg.calendar.ics_urls) addIcsRow(u);
  for (const k of cfg.key_dates) addKeyRow(k);
}

// ------------------------------------------------------------------ search ---
async function search() {
  const q = $('q').value.trim();
  const list = $('q-results');
  $('q-error').hidden = true;
  if (q.length < 2) { list.hidden = true; return; }
  try {
    const { results } = await api(`/geocode?q=${encodeURIComponent(q)}&language=${lang}`);
    list.replaceChildren(...results.map((r) => {
      const b = el('button', { type: 'button' }, `${r.name} `, el('small', { textContent: [r.region, r.country].filter(Boolean).join(', ') }));
      b.addEventListener('click', () => {
        $('loc-name').value = r.name;
        $('loc-lat').value = r.latitude;
        $('loc-lon').value = r.longitude;
        if (r.timezone) fill($('loc-tz'), [...$('loc-tz').options].map((o) => [o.value, o.value]), r.timezone);
        if (r.country && options.countries[r.country]) { $('country').value = r.country; renderSubdivisions(''); onCountry(); }
        list.hidden = true;
        markDirty();
      });
      return el('li', {}, b);
    }));
    list.hidden = results.length === 0;
    if (!results.length) { $('q-error').textContent = t('admin.no_result'); $('q-error').hidden = false; }
  } catch (e) {
    $('q-error').textContent = t('admin.search_failed'); $('q-error').hidden = false;
  }
}
function onCountry() {
  renderSubdivisions('');
  if (!unitsTouched) $('units').value = IMPERIAL.has($('country').value) ? 'imperial' : 'metric';
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
      name: $('loc-name').value.trim(),
      latitude: Number($('loc-lat').value),
      longitude: Number($('loc-lon').value),
      timezone: $('loc-tz').value,
    },
    calendar: { ics_urls: [...$('ics-list').querySelectorAll('input')].map((i) => i.value.trim()).filter(Boolean) },
    key_dates: [...$('key-list').querySelectorAll('.item')].map((row) => {
      const [d, l, k] = row.querySelectorAll('input, select');
      return { date: d.value.trim(), label: l.value.trim(), kind: k.value };
    }),
  };
  if ($('subdivision').value) body.subdivision = $('subdivision').value;
  if ($('pin').value !== '') body.pin = $('pin').value;
  return body;
}

async function save(event) {
  event.preventDefault();
  const form = $('form');
  if (!form.reportValidity()) return;
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
    cfg = { ...cfg, ...body, mode: cfg.mode, theme: cfg.theme };
    refreshPreview();
  } catch (e) {
    state.textContent = e.status === 409 ? t('admin.demo_readonly') : `${t('admin.error')}: ${e.message}`;
    state.className = 'bad';
  } finally {
    $('save').disabled = false;
  }
}

// ------------------------------------------------------------------ boot -----
async function start() {
  const data = await api('/config');
  cfg = data.config;
  options = data.options;
  editable = data.editable;
  await loadStrings(cfg.language);
  translateStatic();
  $('gate').hidden = true;
  $('app').hidden = false;
  renderPlace(); renderRegion(); renderLook(); renderLists();
  $('pin').placeholder = data.pin_set ? '••••' : '';
  if (!editable) { $('state').textContent = t('admin.demo_readonly'); $('state').className = 'bad'; }
  fitPreview();
  refreshPreview();
}

async function boot() {
  await loadStrings(navigator.language || 'en');
  translateStatic();
  $('form').addEventListener('submit', save);
  $('form').addEventListener('input', (e) => { if (e.target.id === 'units') unitsTouched = true; });
  $('form').addEventListener('change', (e) => { if (e.target.id !== 'q') markDirty(); });
  $('country').addEventListener('change', onCountry);
  $('language').addEventListener('change', refreshPreviewLang);
  $('q-go').addEventListener('click', search);
  $('q').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); search(); } });
  $('ics-add').addEventListener('click', () => { addIcsRow(); markDirty(); });
  $('key-add').addEventListener('click', () => { addKeyRow(); markDirty(); });
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
    catch (err) { $('gate-error').textContent = t('admin.pin_wrong'); $('gate-error').hidden = false; }
  });

  try {
    const status = await api('/status');
    if (status.pin_required && !pin) throw Object.assign(new Error('pin'), { status: 401 });
    await start();
  } catch (err) {
    if (err.status === 401) {
      $('gate-label').textContent = t('admin.enter_pin');
      $('gate-btn').textContent = t('admin.unlock');
      $('gate').hidden = false;
    } else if (err.status === 403) {
      $('gate').hidden = false;
      $('gate-form').replaceChildren(el('p', { className: 'error', textContent: t('admin.forbidden') }));
    } else {
      $('gate').hidden = false;
      $('gate-form').replaceChildren(el('p', { className: 'error', textContent: `${t('admin.error')}: ${err.message}` }));
    }
  }
}
function refreshPreviewLang() { refreshPreview(); }

boot();
