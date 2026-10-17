// The one-page guide of what to say. Reads the phrases from the server (the language the screen
// listens in) and the words around them from the settings page's own translations.

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const VOICE_LANGUAGES = ['en', 'fr', 'de', 'es', 'it', 'pt', 'pt-BR', 'ar', 'sw', 'id'];
// The action names are grouped so a page reads like a menu, not a list.
const GROUPS = [
  ['guide_group_day', ['time', 'date', 'weather', 'agenda', 'tomorrow', 'read_day', 'news', 'tv']],
  ['guide_group_radio', ['radio_play', 'radio_stop', 'radio_next', 'radio_prev', 'volume_up', 'volume_down']],
  ['guide_group_look', ['bigger', 'smaller', 'contrast_on', 'contrast_off', 'quiet']],
];
let pin = '';
try { pin = sessionStorage.getItem('beranda-pin') || ''; } catch { /* no storage */ }

async function json(url, headers = {}) {
  const r = await fetch(url, { headers });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

async function strings(language) {
  // The settings page speaks 9 languages; anything else reads the guide in English.
  const base = await json('/static/i18n/admin/en.json');
  const code = language.split('-')[0];
  for (const name of [code, language]) {
    if (name === 'en') continue;
    try { Object.assign(base, await json(`/static/i18n/admin/${name}.json`)); } catch { /* not translated: English */ }
  }
  return base;
}

function t(dict, key, vars = {}) {
  let s = dict[key] || key;
  for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, v);
  return s;
}

async function render(language) {
  const commands = await json(`/api/admin/voice-commands?language=${encodeURIComponent(language)}`, pin ? { 'X-Beranda-Pin': pin } : {});
  const dict = await strings(commands.language);
  const names = new Intl.DisplayNames([commands.language], { type: 'language' });
  document.documentElement.lang = commands.language;
  document.documentElement.dir = commands.language.startsWith('ar') ? 'rtl' : 'ltr';
  document.title = `Beranda · ${t(dict, 'guide_title')}`;
  $('subtitle').textContent = `${t(dict, 'guide_title')} · ${names.of(commands.language)}`;
  $('date').textContent = new Date().toLocaleDateString(commands.language, { day: 'numeric', month: 'long', year: 'numeric' });
  $('how').textContent = `${t(dict, 'guide_how_button')} ${t(dict, 'guide_how_2')}`;
  $('groups').replaceChildren(...GROUPS.map(([title, intents]) => {
    const section = document.createElement('section');
    const h2 = document.createElement('h2');
    h2.textContent = t(dict, title);
    const dl = document.createElement('dl');
    for (const intent of intents) {
      const phrases = commands.commands[intent];
      if (!phrases?.length) continue;
      const dt = document.createElement('dt');
      dt.textContent = t(dict, `voice_act_${intent}`);
      const dd = document.createElement('dd');
      dd.textContent = phrases.map((p) => `« ${p} »`).join('  ·  ');
      dl.append(dt, dd);
    }
    section.append(h2, dl);
    return section;
  }));
  $('own').textContent = commands.own?.length
    ? t(dict, 'guide_own', { n: commands.own.length }) + ' ' + commands.own.map((c) => `« ${c} »`).join(' · ')
    : t(dict, 'guide_own_none');
  $('print').textContent = t(dict, 'guide_print');
  $('lang').previousSibling.textContent = `${t(dict, 'language')} `;
}

async function boot() {
  const wanted = params.get('language') || 'en';
  const select = $('lang');
  const names = new Intl.DisplayNames([wanted], { type: 'language' });
  for (const code of VOICE_LANGUAGES) {
    const o = document.createElement('option');
    o.value = code; o.textContent = names.of(code);
    select.append(o);
  }
  select.value = VOICE_LANGUAGES.includes(wanted) ? wanted : 'en';
  select.addEventListener('change', () => render(select.value));
  $('print').addEventListener('click', () => window.print());
  try { await render(select.value); } catch (err) { $('how').textContent = `${err.message}. Open this page from the settings page.`; }
}
boot();
