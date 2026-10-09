// Beranda display. Vanilla JS, no framework, no build step: it has to stay light on a Pi 3B.
// Data comes from one endpoint (/api/state); the display never talks to third parties.

import { createRadio } from '/static/radio.js';
import * as voice from '/static/voice.js';

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
  renderSecondClock(now);
  // Re-run exactly when the next minute starts: no per-second timer, no wasted CPU.
  clearTimeout(clockTimer);
  clockTimer = setTimeout(() => { renderClock(); renderAgenda(); }, 60_000 - (now.getTime() % 60_000) + 50);
}

// An optional second clock ("Tokyo 05:15"), small, under the date. A wrong zone name just hides it.
function renderSecondClock(now) {
  const el = $('clock2');
  const zone = state?.widgets?.second_clock;
  el.hidden = !zone;
  if (!zone) return;
  try {
    const city = zone.split('/').pop().replaceAll('_', ' ');
    const h24 = dtf({ hour: 'numeric' }).resolvedOptions().hourCycle?.startsWith('h2');
    const time = dtf({ hour: h24 ? '2-digit' : 'numeric', minute: '2-digit' }, zone).format(now);
    // Not the same calendar day there? Say which day ("lun.").
    const other = new Intl.DateTimeFormat('en-CA', { timeZone: zone, year: 'numeric', month: '2-digit', day: '2-digit' }).format(now);
    const day = other === dayKey(now) ? '' : ` · ${dtf({ weekday: 'short' }, zone).format(now)}`;
    el.replaceChildren(`${city} `, Object.assign(document.createElement('b'), { textContent: time }), day);
  } catch { el.hidden = true; }
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

// ---------------------------------------------------------------- the middle zone ------
// Photo frame + 24 h graph + air / UV / pollen. The zone hides when none of the three has anything.
const esc = (text) => String(text).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

function chartWanted() {
  return Boolean(state?.widgets?.chart && (state?.weather?.hourly || []).length >= 6);
}

function renderFeature() {
  renderAir();
  const chart = chartWanted();
  $('chart').hidden = !chart;
  document.querySelector('.now').classList.toggle('has-chart', chart);
  $('feature').hidden = $('phototile').hidden && !chart && $('air').hidden;
  drawChart();
}

// Temperature curve, rain bars along the bottom, wind every 3 hours, shaded nights. Drawn at the
// real pixel size of its box (so the text is never stretched) and redrawn when the window changes.
function drawChart() {
  if (!state || $('chart').hidden) return;
  const w = state.weather;
  const hours = w.hourly;
  const box = $('chart-plot');
  const W = box.clientWidth;
  const H = box.clientHeight;
  if (!W || !H) return;
  $('chart-title').textContent = t('chart.title', { wind: w.units.wind });
  const rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 16;
  const fs = rem * 0.8;
  const padX = rem * 0.6;
  const top = fs * 1.9;
  const withWind = H > rem * 9;          // a very short graph drops the wind numbers
  const bottom = H - fs * (withWind ? 3.2 : 2.0);  // the plot ends here; wind numbers and hours come below
  const height = Math.max(bottom - top, 20);
  const n = hours.length;
  const step = (W - 2 * padX) / (n - 1);
  const x = (i) => padX + i * step;
  const temps = hours.map((h) => h.temp);
  const lo = Math.min(...temps);
  const hi = Math.max(...temps);
  const span = Math.max(hi - lo, 2);
  const lineH = height * 0.68;           // the curve uses the upper part, the rain bars the lower part
  const y = (v) => top + (1 - (v - lo) / span) * lineH;
  const out = [];

  // nights: grey bands from sunset to sunrise
  const sun = Object.fromEntries(w.daily.map((d) => [d.date, d]));
  const isNight = (time) => {
    const d = sun[time.slice(0, 10)];
    return d ? time < d.sunrise || time >= d.sunset : false;
  };
  for (let i = 0; i < n;) {
    if (!isNight(hours[i].time)) { i += 1; continue; }
    let j = i;
    while (j + 1 < n && isNight(hours[j + 1].time)) j += 1;
    const x0 = Math.max(0, x(i) - step / 2);
    const x1 = Math.min(W, x(j) + step / 2);
    out.push(`<rect class="c-night" x="${x0.toFixed(1)}" y="${top - fs}" width="${(x1 - x0).toFixed(1)}" height="${(bottom - top + fs).toFixed(1)}"/>`);
    i = j + 1;
  }
  out.push(`<line class="c-grid" x1="0" x2="${W}" y1="${bottom}" y2="${bottom}"/>`);

  // rain bars (square-root scale, so drizzle stays visible next to a downpour)
  const barMax = height * 0.3;
  hours.forEach((h, i) => {
    if (h.precip < 0.1) return;
    const bh = Math.max(2, Math.min(1, Math.sqrt(h.precip / 4)) * barMax);
    out.push(`<rect class="c-rain" x="${(x(i) - step * 0.35).toFixed(1)}" y="${(bottom - bh).toFixed(1)}" width="${(step * 0.7).toFixed(1)}" height="${bh.toFixed(1)}" rx="1"/>`);
  });

  // temperature curve, with labels on the first, the coldest and the warmest point
  const path = hours.map((h, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(h.temp).toFixed(1)}`).join('');
  out.push(`<path class="c-line" d="${path}"/>`);
  const iMax = temps.indexOf(hi);
  const iMin = temps.indexOf(lo);
  const marks = new Set([0, iMax, iMin]);
  for (const i of marks) {
    const px = x(i);
    const anchor = i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle';
    const roomBelow = y(hours[i].temp) + fs * 1.5 < bottom - 2;  // the coldest label goes under its dot when there is room
    const above = i === iMin && i !== 0 && iMin !== iMax && roomBelow ? y(hours[i].temp) + fs * 1.5 : y(hours[i].temp) - fs * 0.7;
    out.push(`<circle class="c-dot" cx="${px.toFixed(1)}" cy="${y(hours[i].temp).toFixed(1)}" r="${(fs * 0.28).toFixed(1)}"/>`);
    out.push(`<text class="c-temp" x="${px.toFixed(1)}" y="${above.toFixed(1)}" text-anchor="${anchor}" font-size="${(fs * 1.1).toFixed(1)}">${Math.round(hours[i].temp)}°</text>`);
  }

  // every 3rd hour: the wind (small number) and the time of day
  const hourFmt = dtf({ hour: 'numeric' }, 'UTC');
  hours.forEach((h, i) => {
    const hh = Number(h.time.slice(11, 13));
    if (hh % 3 !== 0 || i > n - 2) return;
    const px = x(i);
    if (withWind) out.push(`<text class="c-wind" x="${px.toFixed(1)}" y="${(bottom + fs * 1.3).toFixed(1)}" text-anchor="middle" font-size="${fs.toFixed(1)}">${Math.round(h.wind)}</text>`);
    out.push(`<text x="${px.toFixed(1)}" y="${(H - fs * 0.2).toFixed(1)}" text-anchor="middle" font-size="${fs.toFixed(1)}">${esc(hourFmt.format(new Date(`${h.time.slice(0, 13)}:00:00Z`)))}</text>`);
  });
  box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(t('chart.title', { wind: w.units.wind }))}">${out.join('')}</svg>`;
}

// Air quality, UV and pollen as small coloured tiles. Colour = how worrying (green ... purple).
const AQI_COLOUR = [1, 1, 2, 3, 4, 5];   // 6 bands of the European / US scales
const UV_COLOUR = [1, 2, 3, 4, 5];
const POLLEN_COLOUR = [1, 1, 2, 3, 4];

function renderAir() {
  const a = state?.air;
  const tiles = [];
  const add = (label, value, word, colour) => tiles.push({ label, value, word, colour });
  if (a?.aqi != null) add(t('air.aqi'), a.aqi, t(`air.aqi_level.${a.aqi_level}`), AQI_COLOUR[a.aqi_level]);
  if (a?.uv != null) add(t('air.uv'), Math.round(a.uv * 10) / 10, t(`air.uv_level.${a.uv_level}`), UV_COLOUR[a.uv_level]);
  for (const p of a?.pollen || []) add(t(`air.kind.${p.kind}`), p.value, t(`air.pollen_level.${p.level}`), POLLEN_COLOUR[p.level]);
  $('air').hidden = !tiles.length;
  $('air').replaceChildren(...tiles.map((tile) => {
    const li = document.createElement('li');
    li.className = 'air-tile';
    li.style.setProperty('--lvl', `var(--lvl-${tile.colour || 1})`);
    for (const [cls, text] of [['air-label', tile.label], ['air-value', tile.value], ['air-word', tile.word]]) {
      const span = document.createElement('span');
      span.className = cls;
      span.textContent = text;
      li.append(span);
    }
    return li;
  }));
}

// Official weather warnings (MeteoAlarm) as coloured pills under the date.
function renderAlerts() {
  const a = state?.alerts;
  const ul = $('alerts');
  ul.hidden = !a;
  if (!a) return;
  const note = (text) => { const li = document.createElement('li'); li.className = 'alert-note'; li.textContent = text; return [li]; };
  const items = a.status !== 'ok' ? note(t(`alerts.${a.status}`))
    : !a.items.length ? note(t('alerts.quiet'))
      : a.items.map((w) => {
        const li = document.createElement('li');
        li.className = `alert l${w.level}`;
        li.textContent = `${t(`alerts.kind.${w.kind}`)} · ${t(`alerts.level.${w.level}`)}`;
        return li;
      });
  ul.replaceChildren(...items);
}

// ---------------------------------------------------------------- ephemeris -----------
// The date in the calendar people of your country also use. Worked out by the browser itself.
const ARAB_HIJRI = 'SA AE KW QA BH OM YE IQ JO LB SY EG LY TN DZ MA MR SD PS DJ SO KM MY BN'.split(' ');
const LOCAL_CALENDARS = {
  JP: () => japaneseDate(),
  KR: () => `음력 ${intlDate('ko-KR', 'chinese', { month: 'long', day: 'numeric' })}`,
  IR: () => intlDate(dateLocale(), 'persian'),
  AF: () => intlDate(dateLocale(), 'persian'),
  IL: () => intlDate(dateLocale(), 'hebrew'),
  IN: () => intlDate(dateLocale(), 'indian'),
  ET: () => intlDate(dateLocale(), 'ethiopic'),
  ER: () => intlDate(dateLocale(), 'ethiopic'),
  ID: () => pasaran(),
};
for (const c of ['CN', 'TW', 'HK', 'MO', 'SG']) LOCAL_CALENDARS[c] = () => chineseLunarDate();
for (const c of ['TH', 'KH', 'LA', 'MM']) LOCAL_CALENDARS[c] = () => intlDate(dateLocale(), 'buddhist');
for (const c of ARAB_HIJRI) LOCAL_CALENDARS[c] = () => intlDate(dateLocale(), 'islamic-umalqura');

function intlDate(locale, calendar, opts = { day: 'numeric', month: 'long', year: 'numeric' }) {
  try { return new Intl.DateTimeFormat(`${locale}-u-ca-${calendar}-nu-latn`, { timeZone: tz, ...opts }).format(new Date()); }
  catch { return ''; }
}

// "令和8年10月9日 · 大安": the era year, and the rokuyō (a six-day luck cycle from the lunar date).
function japaneseDate() {
  const ROKUYO = ['大安', '赤口', '先勝', '友引', '先負', '仏滅'];
  const era = intlDate('ja-JP', 'japanese', { era: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  try {
    const parts = new Intl.DateTimeFormat('en-u-ca-chinese', { timeZone: tz, month: 'numeric', day: 'numeric' }).formatToParts(new Date());
    const month = parseInt(parts.find((p) => p.type === 'month')?.value, 10);
    const day = parseInt(parts.find((p) => p.type === 'day')?.value, 10);
    return `${era} · ${ROKUYO[(month + day) % 6]}`;
  } catch { return era; }
}

// The 5-day Javanese market week (Legi, Pahing, Pon, Wage, Kliwon): counted from a known day.
function pasaran() {
  const names = ['Legi', 'Pahing', 'Pon', 'Wage', 'Kliwon'];
  const [y, m, d] = dayKey(new Date()).split('-').map(Number);
  const days = Math.round((Date.UTC(y, m - 1, d) - Date.UTC(1945, 7, 17)) / 86_400_000);  // 17 Aug 1945 was a Legi
  return `Pasaran ${names[((days % 5) + 5) % 5]}`;
}

function pad2(n) { return String(n).padStart(2, '0'); }
function spanText(seconds) {
  const m = Math.floor(seconds / 60);
  return m ? `${m} min ${pad2(seconds % 60)} s` : `${seconds} s`;
}

function renderEph() {
  const e = state?.ephemeris;
  const rows = [];
  if (e) {
    if (e.nameday) rows.push([t('eph.nameday'), e.nameday]);
    if (e.daylight_min != null) {
      const text = `${Math.floor(e.daylight_min / 60)} h ${pad2(e.daylight_min % 60)}`;
      const delta = e.delta_s ? ` (${e.delta_s > 0 ? '+' : '−'}${spanText(Math.abs(e.delta_s))})` : '';
      rows.push([t('eph.daylight'), text, delta]);
    }
    const cal = LOCAL_CALENDARS[(state.config.country || '').toUpperCase()]?.();
    if (cal) rows.push([t('eph.calendar'), cal]);
  }
  $('eph').hidden = !rows.length;
  $('eph-list').replaceChildren(...rows.map(([label, text, extra]) => {
    const li = document.createElement('li');
    const k = document.createElement('span');
    k.className = 'k';
    k.textContent = label;
    // The value keeps its own reading direction (numbers like "11 h 43" must not flip in Arabic).
    const v = document.createElement('span');
    v.dir = extra ? 'ltr' : 'auto';
    v.textContent = text;
    li.append(k, v);
    if (extra) {
      const d = document.createElement('span');
      d.className = 'delta';
      d.dir = 'ltr';
      d.textContent = extra;
      li.append(d);
    }
    return li;
  }));
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
  // The French Republican calendar (17 Vendémiaire, "Pumpkin") is only a curiosity: the box
  // "On this day" replaces it. Other themes keep their own seasonal block.
  $('season').hidden = s.kind === 'republican';
  $('sky').classList.toggle('no-season', s.kind === 'republican');
  if (s.kind === 'republican') return;
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

// ---------------------------------------------------------------- agenda ----------------
// The TV box and the agenda share the room left in the side column: the TV claims its lines
// first, the agenda then keeps what fits. Both are redone when fonts, theme or window size change.
function renderAgenda() { if (state) { drawChart(); renderTv(); renderUpcoming(); } }

function renderUpcoming() {
  const list = $('upcoming');
  list.replaceChildren();
  const today = new Date();
  const todayKey = dayKey(today);
  const tomorrowKey = dayKey(new Date(today.getTime() + 86_400_000));
  const soon = dayKey(new Date(today.getTime() + 6 * 86_400_000));

  const items = [
    ...state.special_days.map((d) => ({ date: d.date, kind: d.kind, label: d.label, time: '', sort: '00' })),
    ...state.events.map((e) => ({
      date: e.start.slice(0, 10), kind: 'event', label: e.title, sort: e.all_day ? '01' : e.start.slice(11, 16),
      time: e.all_day ? t('all_day') : dtf({ hour: '2-digit', minute: '2-digit' }).format(new Date(e.start)),
    })),
  ].filter((i) => i.date >= todayKey)  // everything the server sent: until the end of next month
    .sort((a, b) => a.date.localeCompare(b.date) || a.sort.localeCompare(b.sort))
    .slice(0, 8);

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
    else if (item.date <= soon) when.textContent = dtf({ weekday: 'short', day: 'numeric' }, 'UTC').format(noon(item.date));
    else when.textContent = dtf({ day: 'numeric', month: 'short' }, 'UTC').format(noon(item.date));  // further away: "3 nov."
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
// A few headlines at a time, 12 s each set, cross-faded. Titles only: no pictures, no links.
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

// The strip under the board shows news headlines, one at a time.
function tickerItems() {
  const news = (state?.news?.items || []).map((item) => ({
    source: item.source, title: item.title, age: newsAge(item.published),
  }));
  return news;  // TV has its own box now ("Tonight on TV"), see renderTv()
}

const NEWS_LINES = 3;  // headlines shown together; the next set fades in after NEWS_MS

function showHeadline() {
  const items = tickerItems();
  const box = $('news');
  if (!items.length) { box.hidden = true; return; }
  box.hidden = false;
  const pages = Math.ceil(items.length / NEWS_LINES);
  const first = (newsIndex % pages) * NEWS_LINES;
  $('news-list').replaceChildren(...items.slice(first, first + NEWS_LINES).map((item) => {
    const li = document.createElement('li');
    li.className = 'news-row';
    const src = document.createElement('span');
    src.className = 'news-src';
    src.textContent = item.source;
    const title = document.createElement('span');
    title.className = 'news-title';
    title.textContent = item.title;
    const age = document.createElement('span');
    age.className = 'news-age';
    age.textContent = item.age;
    li.append(src, title, age);
    return li;
  }));
}

function renderNews() {
  clearTimeout(newsTimer);
  showHeadline();
  if (tickerItems().length <= NEWS_LINES) return;
  const box = $('news');
  const next = () => {
    box.classList.add('out');
    setTimeout(() => { newsIndex += 1; showHeadline(); box.classList.remove('out'); }, 650);
    newsTimer = setTimeout(next, NEWS_MS);
  };
  newsTimer = setTimeout(next, NEWS_MS);
}

// ---------------------------------------------------------------- tonight on TV --------
// One line per channel the user ticked: the main programme of the evening. When there is
// nothing to list, the box says why in plain words instead of staying blank.
const TV_NOTES = { no_channels: 'tv_no_channels', empty: 'tv_empty', error: 'tv_error' };

const TV_LINES = 10;  // at most this many channels at once; more rotate, a page every few seconds
let tvPage = 0;
let tvTimer = null;

function tvRows(items) {
  return items.map((p) => {
    const li = document.createElement('li');
    li.className = 'tv-row';
    const chan = document.createElement('span');
    chan.className = 'tv-chan';
    chan.textContent = p.channel;
    const time = document.createElement('span');
    time.className = 'tv-time';
    time.textContent = p.start;
    const show = document.createElement('span');
    show.className = 'tv-show';
    show.textContent = p.title;
    li.append(chan, time, show);
    return li;
  });
}

function renderTv() {
  const tv = state?.tv;
  clearTimeout(tvTimer);
  $('tv').hidden = !tv;
  if (!tv) return;
  $('tv-title').replaceChildren(t('tv_title'));
  if (tv.from) {
    const when = document.createElement('span');
    when.className = 'tv-when';
    when.textContent = `${tv.from}–${tv.to}`;
    $('tv-title').append(when);
  }
  if (tv.status !== 'ok') {
    const li = document.createElement('li');
    li.className = 'tv-note';
    li.textContent = t(TV_NOTES[tv.status] || 'tv_empty');
    $('tv-list').replaceChildren(li);
    return;
  }
  // Show as many channels as fit (up to TV_LINES); if there are more, take turns.
  const all = tv.programmes;
  const list = $('tv-list');
  list.replaceChildren(...tvRows(all.slice(0, TV_LINES)));
  while (list.children.length > 1 && $('tv').scrollHeight > $('tv').clientHeight + 1) list.lastElementChild.remove();
  const size = list.children.length;
  if (all.length <= size) return;
  const pages = Math.ceil(all.length / size);
  const show = () => {
    tvPage = (tvPage + 1) % pages;
    list.replaceChildren(...tvRows(all.slice(tvPage * size, tvPage * size + size)));
    tvTimer = setTimeout(show, NEWS_MS);
  };
  tvPage = 0;
  tvTimer = setTimeout(show, NEWS_MS);
}

// ---------------------------------------------------------------- "On this day" -------
function renderFacts() {
  const items = (state.history || []).slice(0, 3);
  $('facts').hidden = !items.length;
  if (!items.length) return;
  $('facts-title').textContent = t('history_title');
  $('facts-list').replaceChildren(...items.map((h) => {
    const li = document.createElement('li');
    li.className = 'fact';
    const year = document.createElement('span');
    year.className = 'fact-year';
    year.textContent = h.year < 0 ? `−${-h.year}` : String(h.year);  // −44 = 44 before our era
    const text = document.createElement('span');
    text.className = 'fact-text';
    text.textContent = h.text;
    li.append(year, text);
    return li;
  }));
}

// ---------------------------------------------------------------- photo frame ----------
// A small frame that cross-fades through the pictures, one every `interval` seconds. It hides
// itself while the photo folder is empty. Two stacked <img>: the next one loads invisibly,
// then fades in over the other (only opacity changes - cheap on a Raspberry Pi).
let photosTimer = null;
let photosIndex = -1;
let photosNames = [];
let photosFront = 'photo-a';

function nextPhoto() {
  if (!photosNames.length) return;
  photosIndex = (photosIndex + 1) % photosNames.length;
  const back = $(photosFront === 'photo-a' ? 'photo-b' : 'photo-a');
  const front = $(photosFront);
  const loader = new Image();
  loader.onload = () => {
    back.src = loader.src;
    back.classList.add('on');
    front.classList.remove('on');
    photosFront = back.id;
  };
  loader.src = `/api/photos/${encodeURIComponent(photosNames[photosIndex])}`;
}

function renderPhotos() {
  const names = state?.photos?.names || [];
  const tile = $('phototile');
  const same = names.length === photosNames.length && names.every((n, i) => n === photosNames[i]);
  tile.hidden = !names.length;
  if (!names.length) { clearInterval(photosTimer); photosTimer = null; photosNames = []; return; }
  if (photosTimer && same) return;  // the slideshow keeps its own rhythm between polls
  photosNames = names;
  photosIndex = -1;
  clearInterval(photosTimer);
  nextPhoto();
  photosTimer = setInterval(nextPhoto, Math.max(5, state?.photos?.interval || 20) * 1000);
}

// ---------------------------------------------------------------- radio -----------------
const radio = createRadio($('radio-audio'), () => paintRadio());
const PLAY = 'M8 5v14l11-7z';
const PAUSE = 'M7 5h4v14H7zM13 5h4v14h-4z';
const SPEAKER = 'M4 9v6h4l5 4V5L8 9z';
const SPEAKER_OFF = 'M4 9v6h4l5 4V5L8 9zM16 9l5 6M21 9l-5 6';
let stations = [];

function currentStation() {
  const snap = radio.snapshot();
  return snap.station || stations.find((s) => (s.uuid || s.url) === radio.lastStationId()) || stations[0] || null;
}

function paintRadio() {
  const box = $('radio');
  const snap = radio.snapshot();
  const on = snap.status === 'playing' || snap.status === 'loading';
  box.classList.toggle('playing', snap.status === 'playing');
  box.classList.toggle('error', snap.status === 'error');
  $('radio-icon').setAttribute('d', on ? PAUSE : PLAY);
  const shown = currentStation();
  $('radio-name').textContent = snap.status === 'error' ? t('radio_error') : (shown?.name || '');
  $('radio-toggle').setAttribute('aria-label', shown?.name || 'Radio');
  $('radio-volume').value = snap.muted ? 0 : snap.volume;
  $('radio-speaker').setAttribute('d', snap.muted || snap.volume === 0 ? SPEAKER_OFF : SPEAKER);
  $('radio-next').hidden = stations.length < 2;
  $('radio-prev').hidden = stations.length < 2;
  $('radio-prev').setAttribute('aria-label', t('radio_prev'));
  $('radio-next').setAttribute('aria-label', t('radio_next'));
}

function renderRadio() {
  stations = state?.radio?.stations || [];
  $('radio').hidden = !stations.length;
  if (state?.radio) radio.defaultVolume(state.radio.volume);
  const snap = radio.snapshot();
  // A station removed from the favourites stops playing; one still there is left alone.
  if (snap.station && !stations.some((s) => s.url === snap.station.url)) radio.stop();
  paintRadio();
}

$('radio-toggle').addEventListener('click', () => radio.toggle(currentStation()));
$('radio-volume').addEventListener('input', (e) => radio.setVolume(e.target.value));
$('radio-mute').addEventListener('click', () => radio.toggleMute());
// step = +1 (next) or -1 (previous); after the last station it wraps round to the first.
function skip(step) {
  if (stations.length < 2) return;
  const here = stations.findIndex((s) => s.url === currentStation()?.url);
  radio.play(stations[(here + step + stations.length) % stations.length]);
}
$('radio-prev').addEventListener('click', () => skip(-1));
$('radio-next').addEventListener('click', () => skip(1));

function nudgeVolume(delta) {
  const now = radio.snapshot().volume;
  radio.setVolume(Math.max(0, Math.min(100, now + delta)));
}

// ---------------------------------------------------------------- voice -----------------
let toastTimer = null;
function toast(text, ms = 6000) {
  const el = $('toast');
  el.textContent = text;
  el.hidden = false;
  clearTimeout(toastTimer);
  if (ms) toastTimer = setTimeout(() => { el.hidden = true; }, ms);
}

async function listen() {
  const mic = $('mic');
  if (mic.classList.contains('listening')) return;
  if (voice.availability() !== 'ok') { toast(t('voice_unavailable'), 9000); return; }
  mic.classList.add('listening');
  toast(t('voice_listening'), 0);
  try {
    const heard = await voice.listenOnce(lang);
    if (!heard) { $('toast').hidden = true; return; }
    const response = await fetch('/api/voice', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: heard }),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const answer = await response.json();
    toast(`« ${heard} »\n${answer.reply}`);
    voice.speak(answer.reply, lang);
    if (answer.action?.type === 'radio_play') radio.play(answer.action);
    if (answer.action?.type === 'radio_stop') radio.stop();
    if (answer.action?.type === 'radio_next') skip(1);
    if (answer.action?.type === 'radio_prev') skip(-1);
    if (answer.action?.type === 'volume_up') nudgeVolume(15);
    if (answer.action?.type === 'volume_down') nudgeVolume(-15);
  } catch (err) {
    toast(t('voice_unavailable'), 9000);  // microphone blocked, or the browser's speech service is unreachable
    console.warn('voice failed', err);
  } finally {
    mic.classList.remove('listening');
  }
}
$('mic').addEventListener('click', listen);
function renderVoice() { $('mic').hidden = !state.voice; }

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
    link.addEventListener('load', () => renderAgenda(), { once: true });
    link.setAttribute('href', href);
  }
}

// Fonts and window size change how many agenda lines fit.
document.fonts?.ready.then(() => renderAgenda());
window.addEventListener('resize', () => renderAgenda());

async function render(online) {
  tz = state.config.location.timezone;
  lang = params.get('lang') || state.config.language;
  await loadStrings(lang);
  applyTheme();
  applyMode();
  renderClock();
  renderWeather();
  renderSky();
  renderFacts();
  renderUpcoming();
  renderNews();
  renderPhotos();
  renderFeature();
  renderAlerts();
  renderEph();
  renderRadio();
  renderVoice();
  renderAgenda();  // the widgets above may have changed how much room the agenda has
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
