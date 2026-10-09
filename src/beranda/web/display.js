// Beranda display. Vanilla JS, no framework, no build step: it has to stay light on a Pi 3B.
// Data comes from one endpoint (/api/state); the display never talks to third parties.

const POLL_MS = 60_000;
const RETRY_MS = 5_000;
const params = new URLSearchParams(location.search);

let state = null;
let strings = {};
let lang = 'fr';
let tz = 'Europe/Paris';
let loadedLang = null;

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- i18n -----
function deepMerge(base, extra) {
  const out = { ...base };
  for (const [k, v] of Object.entries(extra)) {
    out[k] = v && typeof v === 'object' && !Array.isArray(v) ? deepMerge(base[k] || {}, v) : v;
  }
  return out;
}

const RTL = new Set(['ar', 'fa', 'he', 'ur']);

// "pt-BR" loads en.json, then pt.json, then pt-BR.json: each file only needs what differs.
async function loadStrings(code) {
  const m = /^([a-z]{2,3})(?:-([A-Za-z]{2}))?$/.exec(String(code).replace('_', '-'));
  if (!m) return;
  const full = m[2] ? `${m[1]}-${m[2].toUpperCase()}` : m[1];
  if (loadedLang === full) return;
  const get = async (name) => {
    try { const r = await fetch(`/static/i18n/${name}.json`); return r.ok ? await r.json() : {}; }
    catch { return {}; }
  };
  // English is the fallback for any string a translation does not have yet.
  let merged = await get('en');
  if (m[1] !== 'en') merged = deepMerge(merged, await get(m[1]));
  if (full !== m[1]) merged = deepMerge(merged, await get(full));
  strings = merged;
  loadedLang = full;
  document.documentElement.lang = full;
  document.documentElement.dir = RTL.has(m[1]) ? 'rtl' : 'ltr';
}

function t(key, vars) {
  let s = key.split('.').reduce((o, k) => (o ? o[k] : undefined), strings);
  if (typeof s !== 'string') return key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, v);
  return s;
}

// Dates in the reader's language; where the browser has no calendar data for it (Haitian
// Creole, for one), in the closest language people there read.
const DATE_FALLBACK = { ht: 'fr' };
function dateLocale() {
  const code = loadedLang || lang;
  try { if (Intl.DateTimeFormat.supportedLocalesOf([code]).length) return code; } catch { /* odd code */ }
  return DATE_FALLBACK[code.split('-')[0]] || 'en';
}
// Latin digits everywhere: the temperatures next to the dates are Latin digits too.
const dtf = (opts, zone = tz) => new Intl.DateTimeFormat(dateLocale(), { timeZone: zone, numberingSystem: 'latn', ...opts });
const dayKey = (d) => new Intl.DateTimeFormat('en-CA', { timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
const noon = (iso) => new Date(`${iso}T12:00:00Z`); // a date-only string, safely in the middle of its day

// ---------------------------------------------------------------- icons ----
// Original line icons on a 64x64 grid, drawn with strokes so they inherit the theme colour.
const CLOUD = 'M18 46h28a10 10 0 0 0 1.5-19.9A14 14 0 0 0 20.5 24 11 11 0 0 0 18 46z';
const RAYS = (cx, cy, r1, r2) => [0, 45, 90, 135, 180, 225, 270, 315].map((a) => {
  const rad = (a * Math.PI) / 180, c = Math.cos(rad), s = Math.sin(rad);
  return `M${(cx + c * r1).toFixed(1)} ${(cy + s * r1).toFixed(1)}L${(cx + c * r2).toFixed(1)} ${(cy + s * r2).toFixed(1)}`;
}).join('');
const DROPS = (xs, y) => xs.map((x) => `M${x} ${y}l-3 7`).join('');
const MOON = 'M40 14a20 20 0 1 0 12 36A17 17 0 0 1 40 14z';

const ICONS = {
  sun: `<circle cx="32" cy="32" r="10"/><path d="${RAYS(32, 32, 16, 24)}"/>`,
  moon: `<path d="${MOON}" transform="translate(-4 2)"/>`,
  partly: `<circle cx="24" cy="24" r="8"/><path d="${RAYS(24, 24, 13, 18)}"/><g transform="translate(6 6)"><path fill="var(--bg)" d="${CLOUD}"/></g>`,
  partlyNight: `<path d="${MOON}" transform="translate(-14 -6) scale(.75)"/><g transform="translate(6 6)"><path fill="var(--bg)" d="${CLOUD}"/></g>`,
  cloud: `<path d="${CLOUD}"/>`,
  fog: `<path d="M12 24h40M8 34h40M16 44h40"/>`,
  drizzle: `<path d="${CLOUD}" transform="translate(0 -6)"/><path d="${DROPS([24, 36, 48], 44)}" stroke-dasharray="3 5"/>`,
  rain: `<path d="${CLOUD}" transform="translate(0 -6)"/><path d="${DROPS([22, 33, 44], 44)}"/><path d="${DROPS([28, 39], 53)}"/>`,
  snow: `<path d="${CLOUD}" transform="translate(0 -6)"/><path d="M22 46v6M19 49h6M34 46v6M31 49h6M46 46v6M43 49h6"/>`,
  storm: `<path d="${CLOUD}" transform="translate(0 -6)"/><path d="M34 38l-7 10h8l-5 10"/>`,
};

function iconName(code, isDay) {
  if (code === 0 || code === 1) return isDay ? 'sun' : 'moon';
  if (code === 2) return isDay ? 'partly' : 'partlyNight';
  if (code === 3) return 'cloud';
  if (code === 45 || code === 48) return 'fog';
  if ([51, 53, 55, 56, 57].includes(code)) return 'drizzle';
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return 'rain';
  if ([71, 73, 75, 77, 85, 86].includes(code)) return 'snow';
  if ([95, 96, 99].includes(code)) return 'storm';
  return 'cloud';
}

function icon(code, isDay = true) {
  return `<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[iconName(code, isDay)]}</svg>`;
}

// ---------------------------------------------------------------- clock ----
let clockTimer = null;
function renderClock() {
  const now = new Date();
  // "09:05" on a 24-hour clock, "9:05 PM" on a 12-hour one.
  const h24 = dtf({ hour: 'numeric' }).resolvedOptions().hourCycle?.startsWith('h2');
  const parts = dtf({ hour: h24 ? '2-digit' : 'numeric', minute: '2-digit' }).formatToParts(now);
  const get = (type) => parts.find((p) => p.type === type)?.value ?? '';
  const hour = get('hour');
  $('hm').textContent = `${hour}${get('literal') || ':'}${get('minute')}`;
  $('period').textContent = get('dayPeriod');
  $('date').textContent = dtf({ weekday: 'long', day: 'numeric', month: 'long' }).format(now);
  // Re-run exactly when the next minute starts: no per-second timer, no wasted CPU.
  clearTimeout(clockTimer);
  clockTimer = setTimeout(() => { renderClock(); renderCalendarDay(); }, 60_000 - (now.getTime() % 60_000) + 50);
}

// ---------------------------------------------------------------- weather ----
function renderWeather() {
  const w = state.weather;
  if (!w) {
    $('now-icon').innerHTML = '';
    $('now-temp').textContent = '–';
    $('now-label').textContent = t('no_weather');
    $('now-detail').textContent = '';
    $('rain-bars').replaceChildren();
    $('rain-text').textContent = '';
    $('week').replaceChildren();
    return;
  }
  const c = w.current;
  $('now-icon').innerHTML = icon(c.code, c.is_day);
  $('now-temp').textContent = c.temp;
  $('now-unit').textContent = w.units.temp;
  $('now-label').textContent = t(`wmo.${c.code}`);
  $('now-detail').textContent = `${t('feels')} ${c.feels}° · ${c.humidity} % · ${c.wind} ${w.units.wind}`;
  renderRain(w.rain);
  renderWeek(w);
}

function renderRain(rain) {
  const bars = $('rain-bars');
  bars.replaceChildren();
  const slots = Math.max(rain.intervals.length, 8);
  for (let i = 0; i < slots; i++) {
    const mm = rain.intervals[i] ?? 0;
    const bar = document.createElement('div');
    bar.className = mm >= 0.1 ? 'bar' : 'bar dry';
    // sqrt scale: a drizzle must stay visible next to a downpour
    if (mm >= 0.1) bar.style.setProperty('--h', Math.min(1, Math.sqrt(mm / 1.2)).toFixed(2));
    bars.append(bar);
  }
  $('rain-from').textContent = t('rain.now');
  $('rain-to').textContent = t('rain.in2h');
  let text;
  if (rain.raining_now) {
    text = rain.stops_in_min == null ? t('rain.long') : t('rain.stops', { min: rain.stops_in_min });
  } else if (rain.starts_in_min != null) {
    text = rain.starts_in_min === 0 ? t('rain.starts_now') : t('rain.starts', { min: rain.starts_in_min });
  } else {
    text = t('rain.none');
  }
  $('rain-text').textContent = text;
}

function renderWeek(w) {
  const root = $('week');
  root.replaceChildren();
  const lo = Math.min(...w.daily.map((d) => d.tmin));
  const hi = Math.max(...w.daily.map((d) => d.tmax));
  const span = Math.max(hi - lo, 1);
  const today = dayKey(new Date());
  for (const d of w.daily) {
    const el = document.createElement('div');
    el.className = `day${d.date === today ? ' today' : ''}`;
    const top = ((hi - d.tmax) / span) * 100;
    const len = Math.max(((d.tmax - d.tmin) / span) * 100, 8);
    el.innerHTML = `
      <div class="day-name"></div>
      <div class="day-icon">${icon(d.code, true)}</div>
      <div class="day-hi"></div>
      <div class="day-track"><div class="day-range"></div></div>
      <div class="day-lo"></div>
      <div class="day-pop"></div>`;
    el.querySelector('.day-name').textContent = dtf({ weekday: 'short' }, 'UTC').format(noon(d.date));
    el.querySelector('.day-hi').textContent = `${d.tmax}°`;
    el.querySelector('.day-lo').textContent = `${d.tmin}°`;
    el.querySelector('.day-pop').textContent = d.pop >= 20 ? `${d.pop}%` : '';
    const range = el.querySelector('.day-range');
    range.style.setProperty('--top', top.toFixed(1));
    range.style.setProperty('--len', len.toFixed(1));
    root.append(el);
  }
}

// ---------------------------------------------------------------- sky ---------
// Draw the lit part of the moon as one path: a half-disc limb plus the terminator ellipse.
function moonPath(phase, r) {
  const waxing = phase < 0.5;
  const rx = Math.abs(Math.cos(2 * Math.PI * phase)) * r;
  const crescent = phase < 0.25 || phase > 0.75;
  const limb = waxing ? 1 : 0;
  const term = waxing ? (crescent ? 0 : 1) : (crescent ? 1 : 0);
  return `M0 ${-r}A${r} ${r} 0 0 ${limb} 0 ${r}A${rx.toFixed(2)} ${r} 0 0 ${term} 0 ${-r}Z`;
}

function renderSky() {
  const m = state.sky.moon;
  const flip = m.mirrored ? ' transform="scale(-1 1)"' : '';
  $('moon-svg').innerHTML =
    `<g${flip}><circle r="50" fill="var(--moon-dark)" stroke="var(--line)" stroke-width="1"/>` +
    `<path d="${moonPath(m.phase, 50)}" fill="var(--moon-lit)"/></g>`;
  $('moon-name').textContent = t(`moon.${m.name}`);
  const shortDate = (iso) => dtf({ day: 'numeric', month: 'short' }).format(new Date(iso));
  const events = [
    { at: m.next_full, text: t('moon.next_full', { date: shortDate(m.next_full) }) },
    { at: m.next_new, text: t('moon.next_new', { date: shortDate(m.next_new) }) },
  ].sort((a, b) => a.at.localeCompare(b.at));
  const lit = t('moon.lit', { pct: Math.round(m.illumination * 100) });
  const detail = $('moon-detail');
  detail.replaceChildren(...[lit, events[0].text].map((line) => {
    const div = document.createElement('div');
    div.textContent = line;
    return div;
  }));

  const sun = $('sun');
  sun.replaceChildren();
  const time = (iso) => dtf({ hour: '2-digit', minute: '2-digit' }).format(new Date(iso));
  if (state.sky.sun.sunrise) {
    for (const [key, iso] of [['sun.rise', state.sky.sun.sunrise], ['sun.set', state.sky.sun.sunset]]) {
      const span = document.createElement('span');
      span.textContent = `${t(key)} ${time(iso)}`;
      sun.append(span);
    }
  }

  const s = state.season;
  const base = (loadedLang || 'en').split('-')[0];
  const pick = (o) => (o && (o[loadedLang] || o[base] || o.en)) || '';
  const own = s.kind === 'ko' ? 'ja' : s.kind === 'jieqi' ? 'zh' : loadedLang;
  let glyph = s.glyph;
  let title = s.title_key ? t(s.title_key) : pick(s.title);
  let sub = pick(s.sub);
  let note = typeof s.note === 'string' ? s.note : pick(s.note);
  if (s.kind === 'hijri') [glyph, title, sub] = hijri();
  if (s.kind === 'hijri' && base === 'ar') sub = '';  // the month is already in Arabic above
  if (s.kind === 'fullmoon') note = t('moon.next_full', { date: dtf({ day: 'numeric', month: 'long' }, 'UTC').format(noon(s.next_change)) });
  if (s.kind === 'jieqi') note = chineseLunarDate();
  $('season').dataset.kind = s.kind;
  $('season-kanji').textContent = glyph;
  $('season-kanji').lang = s.kind === 'hijri' ? 'ar' : own;
  $('season-seal').textContent = s.seal;
  $('season-seal').lang = own;
  $('season-name').textContent = title;
  $('season-name').lang = s.title_lang || (s.kind === 'jieqi' && !s.title[loadedLang] ? 'en' : loadedLang);
  $('season-romaji').textContent = sub;
  $('season-romaji').lang = s.sub_lang || (s.kind === 'hijri' ? 'ar' : own);
  $('season-note').textContent = note;
  $('season-next').textContent = s.days_left == null ? ''
    : s.days_left <= 1 ? t('season.tomorrow') : t('season.in_days', { n: s.days_left });
}

// The Islamic (Hijri) date, Umm al-Qura reckoning, straight from the browser's calendars.
function hijri() {
  try {
    const now = new Date();
    const fmt = (locale, opts) => new Intl.DateTimeFormat(`${locale}-u-ca-islamic-umalqura-nu-latn`, { timeZone: tz, ...opts }).format(now);
    const day = fmt('en', { day: 'numeric' });
    const local = fmt(loadedLang || 'en', { month: 'long', year: 'numeric' });
    const arabic = fmt('ar', { month: 'long', year: 'numeric' });
    return [day, local, arabic];
  } catch { return ['', '', '']; }
}

// The Chinese lunar date (农历), e.g. "八月廿九", from the browser's calendars.
function chineseLunarDate() {
  try {
    const parts = new Intl.DateTimeFormat('zh-CN-u-ca-chinese', { timeZone: tz, month: 'long', day: 'numeric' }).formatToParts(new Date());
    const month = parts.find((p) => p.type === 'month')?.value ?? '';
    const day = Number(parts.find((p) => p.type === 'day')?.value ?? 0);
    const names = ['初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
      '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
      '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'];
    return `农历 ${month}${names[day - 1] || ''}`;
  } catch { return ''; }
}

// ---------------------------------------------------------------- calendar --------
function marksByDay() {
  const map = new Map();
  const add = (date, cls) => {
    const list = map.get(date) || [];
    if (!list.includes(cls)) list.push(cls);
    map.set(date, list);
  };
  for (const d of state.special_days) add(d.date, d.kind);
  for (const e of state.events) {
    const first = e.start.slice(0, 10);
    add(first, 'event');
    if (e.all_day) { // an all-day event's end date is exclusive
      const last = e.end.slice(0, 10);
      for (let d = new Date(`${first}T12:00:00Z`); ; ) {
        d.setUTCDate(d.getUTCDate() + 1);
        const key = d.toISOString().slice(0, 10);
        if (key >= last) break;
        add(key, 'event');
      }
    }
  }
  return map;
}

function renderCalendar() {
  const todayKey = dayKey(new Date());
  const [y, m] = todayKey.split('-').map(Number);
  const startJS = (state.config.week_start + 1) % 7; // server: 0=Mon..6=Sun -> JS: 0=Sun..6=Sat
  const first = new Date(Date.UTC(y, m - 1, 1));
  const lead = (first.getUTCDay() - startJS + 7) % 7;
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate();

  $('cal-title').textContent = dtf({ month: 'long', year: 'numeric' }, 'UTC').format(first);
  const grid = $('cal-grid');
  grid.replaceChildren();

  for (let i = 0; i < 7; i++) {
    const dow = document.createElement('div');
    dow.className = 'cal-dow';
    dow.textContent = dtf({ weekday: 'narrow' }, 'UTC').format(new Date(Date.UTC(2024, 0, 7 + startJS + i)));
    grid.append(dow);
  }
  for (let i = 0; i < lead; i++) grid.append(document.createElement('div'));

  const marks = marksByDay();
  for (let day = 1; day <= days; day++) {
    const key = `${y}-${String(m).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const kinds = marks.get(key) || [];
    const cell = document.createElement('div');
    const dow = new Date(Date.UTC(y, m - 1, day)).getUTCDay();
    cell.className = 'cal-cell';
    if (key < todayKey) cell.classList.add('past');
    if (key === todayKey) cell.classList.add('today');
    if (dow === 0) cell.classList.add('sunday');
    if (kinds.includes('holiday')) cell.classList.add('holiday-day');
    const num = document.createElement('span');
    num.className = 'cal-num';
    num.textContent = day;
    const row = document.createElement('div');
    row.className = 'cal-marks';
    for (const kind of kinds.slice(0, 3)) {
      const mark = document.createElement('i');
      mark.className = `mark ${kind}`;
      row.append(mark);
    }
    cell.append(num, row);
    grid.append(cell);
  }
}

function renderCalendarDay() { if (state) { renderCalendar(); renderUpcoming(); } }

function renderUpcoming() {
  const list = $('upcoming');
  list.replaceChildren();
  const today = new Date();
  const todayKey = dayKey(today);
  const tomorrowKey = dayKey(new Date(today.getTime() + 86_400_000));
  const horizon = dayKey(new Date(today.getTime() + 12 * 86_400_000));

  const items = [
    ...state.special_days.map((d) => ({ date: d.date, kind: d.kind, label: d.label, time: '', sort: '00' })),
    ...state.events.map((e) => ({
      date: e.start.slice(0, 10), kind: 'event', label: e.title, sort: e.all_day ? '01' : e.start.slice(11, 16),
      time: e.all_day ? t('all_day') : dtf({ hour: '2-digit', minute: '2-digit' }).format(new Date(e.start)),
    })),
  ].filter((i) => i.date >= todayKey && i.date <= horizon)
    .sort((a, b) => a.date.localeCompare(b.date) || a.sort.localeCompare(b.sort))
    .slice(0, 7);

  if (!items.length) {
    const li = document.createElement('li');
    li.className = 'empty';
    li.textContent = t('nothing_upcoming');
    list.append(li);
    return;
  }
  for (const item of items) {
    const li = document.createElement('li');
    li.className = 'up';
    const when = document.createElement('span');
    when.className = 'up-when';
    if (item.date === todayKey) { when.textContent = t('today'); when.classList.add('soon'); }
    else if (item.date === tomorrowKey) when.textContent = t('tomorrow');
    else when.textContent = dtf({ weekday: 'short', day: 'numeric' }, 'UTC').format(noon(item.date));
    const mark = document.createElement('i');
    mark.className = `mark ${item.kind}`;
    const label = document.createElement('span');
    label.className = 'up-label';
    label.textContent = item.label;
    const time = document.createElement('span');
    time.className = 'up-time';
    time.textContent = item.time;
    li.append(when, mark, label, time);
    list.append(li);
  }
  // Drop the lines that would be cut by the bottom edge rather than show half of one.
  const box = list.parentElement;
  while (list.children.length > 1 && list.scrollHeight > box.clientHeight) list.lastElementChild.remove();
}

// ---------------------------------------------------------------- news ------------------
// One headline at a time, 12 s each, cross-faded. Titles only: no pictures, no links.
const NEWS_MS = 12_000;
let newsIndex = 0;
let newsTimer = null;

function newsAge(iso) {
  if (!iso) return '';
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  const rtf = new Intl.RelativeTimeFormat(dateLocale(), { numeric: 'auto', style: 'short' });
  if (minutes < 60) return rtf.format(-Math.max(minutes, 1), 'minute');
  if (minutes < 48 * 60) return rtf.format(-Math.round(minutes / 60), 'hour');
  return rtf.format(-Math.round(minutes / 1440), 'day');
}

// The strip shows news headlines and, when a TV guide is set up, upcoming prime-time
// programmes too - interleaved so TV doesn't end up buried behind a long news list.
function tickerItems() {
  const news = (state?.news?.items || []).map((item) => ({
    source: item.source, title: item.title, age: newsAge(item.published),
  }));
  const shows = (state?.tv?.programmes || []).map((p) => ({
    source: p.channel, title: p.title, age: `${p.start}–${p.stop}`,
  }));
  // "On this day": the source column becomes the year it happened (negative = BCE).
  const onThisDay = (state?.history || []).map((h) => ({
    source: h.year < 0 ? `${-h.year} BCE` : String(h.year), title: h.label, age: '',
  }));
  const merged = [];
  const count = Math.max(news.length, shows.length, onThisDay.length);
  for (let i = 0; i < count; i++) {
    if (i < news.length) merged.push(news[i]);
    if (i < shows.length) merged.push(shows[i]);
    if (i < onThisDay.length) merged.push(onThisDay[i]);
  }
  return merged;
}

function showHeadline() {
  const items = tickerItems();
  const box = $('news');
  if (!items.length) { box.hidden = true; return; }
  box.hidden = false;
  const item = items[newsIndex % items.length];
  $('news-src').textContent = item.source;
  $('news-title').textContent = item.title;
  $('news-age').textContent = item.age;
}

function renderNews() {
  clearTimeout(newsTimer);
  showHeadline();
  const items = tickerItems();
  if (items.length < 2) return;
  const box = $('news');
  const next = () => {
    box.classList.add('out');
    setTimeout(() => { newsIndex += 1; showHeadline(); box.classList.remove('out'); }, 650);
    newsTimer = setTimeout(next, NEWS_MS);
  };
  newsTimer = setTimeout(next, NEWS_MS);
}

// ---------------------------------------------------------------- photo carousel ------
// Alternates full-screen photo / dashboard, each for `interval` seconds, so a mirror with
// no folder configured never shows this at all (names stays empty and the timer is skipped).
let photosTimer = null;
let photosRunning = false;
let photosIndex = -1;
let photosNames = [];

function renderPhotos() {
  const names = state?.photos?.names || [];
  if (!names.length) {
    clearTimeout(photosTimer);
    photosTimer = null;
    photosRunning = false;
    photosNames = [];
    $('photos').classList.remove('show');
    $('photos').hidden = true;
    return;
  }
  $('photos').hidden = false;
  const sameSet = names.length === photosNames.length && names.every((n, i) => n === photosNames[i]);
  photosNames = names;
  // The carousel polls every minute like everything else, but its own slideshow timing is
  // independent: only (re)start it when it isn't running yet, or the folder's contents changed.
  if (photosRunning && sameSet) return;
  clearTimeout(photosTimer);
  photosIndex = -1;
  photosRunning = true;
  const seconds = Math.max(5, state?.photos?.interval || 20);
  const box = $('photos');
  const img = $('photos-img');
  const showNext = () => {
    photosIndex = (photosIndex + 1) % photosNames.length;
    img.src = `/api/photos/${encodeURIComponent(photosNames[photosIndex])}`;
    box.classList.add('show');
    photosTimer = setTimeout(hideAgain, seconds * 1000);
  };
  const hideAgain = () => {
    box.classList.remove('show');
    photosTimer = setTimeout(showNext, seconds * 1000);
  };
  showNext();
}

// ---------------------------------------------------------------- first start ---------
function renderSetup() {
  const setup = state.setup || { needed: false, urls: [], wifi: null };
  const show = setup.needed || params.get('setup') === 'preview';  // ?setup=preview: see the card
  // No network at all yet: show "join this Wi-Fi" instead of a LAN address, since there isn't one.
  const wifiShow = show && !!setup.wifi;
  $('setup-wifi').hidden = !wifiShow;
  $('setup').hidden = !show || wifiShow;
  if (wifiShow) {
    $('setup-wifi-title').textContent = t('setup.wifi_title');
    $('setup-wifi-help').textContent = t('setup.wifi_text', { ssid: setup.wifi.ssid });
    if (!$('setup-wifi-qr').getAttribute('src')) $('setup-wifi-qr').setAttribute('src', '/api/setup-wifi-qr.svg');
    return;
  }
  if (!show) return;
  $('setup-title').textContent = t('setup.title');
  $('setup-help').textContent = t('setup.text');
  $('setup-urls').replaceChildren(...setup.urls.map((url) => {
    const li = document.createElement('li');
    li.textContent = url.replace(/^https?:\/\//, '');
    return li;
  }));
  if (!$('setup-qr').getAttribute('src')) $('setup-qr').setAttribute('src', '/api/setup-qr.svg');
}

// ---------------------------------------------------------------- status & loop ------
function renderStatus(online) {
  const demo = $('badge-demo');
  demo.hidden = !state?.demo;
  demo.textContent = t('demo');
  const off = $('badge-offline');
  off.hidden = online && !(state?.stale?.length);
  off.textContent = t('offline');
  const onAir = $('badge-radio');
  onAir.hidden = !state?.radio?.playing;
  onAir.textContent = state?.radio?.station ? `▶ ${state.radio.station.name}` : '';
  // Open-Meteo's free tier requires attribution.
  const credit = state?.weather?.source === 'Open-Meteo' ? ' · Open-Meteo' : '';
  $('place').textContent = (state?.config.location.name ?? '') + credit;
}

function applyMode() {
  const forced = params.get('mode');
  const mode = forced === 'light' || forced === 'night' ? forced : state.mode;
  document.documentElement.dataset.mode = mode;
}

function applyTheme() {
  const name = params.get('theme') || state.config.theme;
  if (!/^[a-z0-9-]+$/.test(name)) return;
  const link = $('theme-css') || document.querySelector('link#theme-css');
  const href = `/static/themes/${name}.css`;
  if (link && !link.getAttribute('href').endsWith(href)) {
    // A new theme changes the size of the blocks: fit the agenda list again once it applies.
    link.addEventListener('load', () => renderCalendarDay(), { once: true });
    link.setAttribute('href', href);
  }
}

// Fonts and window size change how many agenda lines fit.
document.fonts?.ready.then(() => renderCalendarDay());
window.addEventListener('resize', () => renderCalendarDay());

async function render(online) {
  tz = state.config.location.timezone;
  lang = params.get('lang') || state.config.language;
  await loadStrings(lang);
  applyTheme();
  applyMode();
  renderClock();
  renderWeather();
  renderSky();
  renderCalendar();
  renderUpcoming();
  renderNews();
  renderPhotos();
  renderSetup();
  document.body.dataset.sleep = String(Boolean(state.sleep));
  renderStatus(online);
  document.body.dataset.ready = 'true'; // handy for screenshots and tests
}

async function refresh() {
  let delay = POLL_MS;
  try {
    const forced = params.get('theme');
    const query = forced && /^[a-z0-9-]+$/.test(forced) ? `?theme=${forced}` : '';
    const response = await fetch(`/api/state${query}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state = await response.json();
    await render(true);
  } catch (err) {
    console.warn('refresh failed', err);
    if (state) renderStatus(false); // keep showing the last good data
    delay = RETRY_MS;
  }
  setTimeout(refresh, delay);
}

refresh();
