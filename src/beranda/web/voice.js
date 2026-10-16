// Voice control, done by the tablet's own browser and microphone (the Raspberry Pi needs none).
//
//   1. You tap the microphone button and say a short sentence.
//   2. The browser turns the speech into text. NOTE: in Chrome this step is done by Google's
//      speech service over the internet - the audio leaves the tablet. The settings page says so.
//   3. The text goes to Beranda (/api/voice), which works out what you meant and answers.
//   4. The tablet reads the answer aloud and, for the radio, starts or stops the sound.
//
// Browsers only allow microphones on "secure" pages (https, or localhost). A tablet opening
// http://beranda.local:8080 is not secure, so `availability()` explains what is wrong and the
// settings page says how to allow it.

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const MAX_FAILS = 6;  // failures in a row before the wake word gives up and says so

// Lower case, no accents, no punctuation: a speech service writes "Béranda," or "tais-toi"
// as it pleases, and all of those must match the same word.
const normalise = (s) => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .replace(/[^\p{L}\p{N}\s']/gu, ' ').replace(/\s+/g, ' ').trim();

// A browser allows ONE listening at a time. The wake word listens all the time, so the
// microphone button has to borrow the microphone from it and give it back afterwards;
// otherwise both fail silently and nothing works any more.
let running = null;  // the wake word of this page, if any

// ONE microphone for the whole browser. Chrome lets a single page listen at a time: a second
// one gets cut off ("aborted", or nothing heard). So every Beranda page in this browser - the
// screens and the settings page - agrees through one note kept in the browser's storage:
//   * a "once" note: a button or the settings test is listening right now. Everybody else
//     steps aside, whatever they were doing; it lasts 15 s at most.
//   * a "wake" note: the screen whose wake word holds the microphone. The FIRST screen keeps
//     it and refreshes it every 4 s; the others wait, and take over if it is closed (12 s).
// Two different addresses for the same Pi (rp4.local and 192.168.1.x) do not share a note:
// open Beranda with one address only.
const NOTE = 'beranda-microphone';
const me = Math.random().toString(36).slice(2);
const ONCE_MS = 15_000;
const WAKE_MS = 12_000;
function readNote() { try { return JSON.parse(localStorage.getItem(NOTE) || 'null'); } catch { return null; } }
function writeNote(note) {
  try { if (note) localStorage.setItem(NOTE, JSON.stringify(note)); else localStorage.removeItem(NOTE); } catch { /* no storage */ }
}
const freshOnce = (n) => n?.kind === 'once' && Date.now() - n.at < ONCE_MS;
const freshWake = (n) => n?.kind === 'wake' && Date.now() - n.at < WAKE_MS;
const sleep = (ms) => new Promise((ok) => { setTimeout(ok, ms); });

// A device with no microphone at all answers "audio-capture" to everything, after the fact.
// The browser lists its microphones without asking permission, so the settings page can say
// so before anybody switches voice control on.
export async function microphoneExists() {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices.some((device) => device.kind === 'audioinput');
  } catch { return true; }  // cannot tell: better to say nothing than to say something wrong
}

export function availability() {
  if (!Recognition) return 'unsupported';
  if (!window.isSecureContext) return 'insecure';
  return 'ok';
}

// Listen once; resolves with the text heard ('' if nothing was said), rejects with a short
// error name ('not-allowed' when the microphone is blocked, ...).
export async function listenOnce(lang) {
  // Ask every Beranda page in this browser to step aside, and wait a moment if a wake word
  // somewhere else holds the microphone: starting while it still listens would get us cut off.
  const before = readNote();
  const id = `${me}-once`;
  // Whoever held the microphone before gets it back afterwards, rather than every screen
  // rushing for it at once.
  const restore = freshWake(before) ? before : null;
  writeNote({ id, kind: 'once', at: Date.now() });
  running?.pause();
  if (freshWake(before) && before.id !== me) await sleep(900);
  return new Promise((resolve, reject) => {
    let over = false;
    const give_back = () => {
      if (over) return;
      over = true;
      clearTimeout(guard);
      if (readNote()?.id === id) writeNote(restore && { ...restore, at: Date.now() });  // only our own note
      running?.resume();
    };
    // A browser sometimes answers nothing at all: no words, no error, no end. Without this the
    // microphone would stay borrowed for ever and the wake word would never listen again.
    const guard = setTimeout(() => { try { rec.stop(); } catch { /* already */ } failed(new Error('no answer')); }, 12_000);
    const done = (text) => { give_back(); resolve(text); };
    const failed = (err) => { give_back(); reject(err); };
    const rec = new Recognition();
    rec.lang = lang;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    let heard = '';
    rec.onresult = (event) => { heard = event.results[0]?.[0]?.transcript || ''; };
    rec.onerror = (event) => { if (event.error !== 'no-speech' && event.error !== 'aborted') failed(new Error(event.error)); };
    rec.onend = () => done(heard);
    try { rec.start(); } catch (err) { failed(err); }
  });
}

export function wakeListener({ lang, word, onWake, onCommand, onError, onState }) {
  if (!Recognition) return { stop() {}, pause() {}, resume() {} };
  const wake = normalise(word);
  let rec = null;
  let live = false;       // a recognition of ours is running right now
  let stopped = false;    // for good (turned off, or gave up)
  let borrowed = false;   // this page's own button is listening
  let yielded = false;    // another page holds the microphone
  let awake = false;      // the word was heard on its own: the next sentence is the command
  let fails = 0;          // failures in a row; the wait doubles, so a failing service is left alone
  let timer = 0;
  let listening_since = 0;
  let said_last = '';
  // Only changes go to the diagnostic file: one line per change, not one per restart.
  const state = (what) => { if (what !== said_last) { said_last = what; onState?.(what); } };

  const wanted = () => !stopped && !borrowed && !yielded;
  const halt = () => { clearTimeout(timer); if (live) { try { rec?.stop(); } catch { /* already */ } } };
  const later = (ms) => { clearTimeout(timer); timer = setTimeout(start, ms); };
  const give_up = (why) => { stopped = true; halt(); state('stopped'); onError(why); };

  function start() {
    if (!wanted() || live) return;
    listening_since = 0;  // set when the browser says it really started
    rec = new Recognition();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onstart = () => { listening_since = Date.now(); state('listening'); };
    rec.onresult = (event) => {
      fails = 0;  // it answered: start counting again from zero
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const said = normalise(event.results[i][0]?.transcript || '');
        if (!said) continue;
        if (awake) { awake = false; onCommand(said); continue; }
        const at = said.indexOf(wake);
        if (at < 0) continue;
        const rest = said.slice(at + wake.length).trim();
        if (rest) onCommand(rest);
        else { awake = true; onWake(); setTimeout(() => { awake = false; }, 8000); }
      }
    };
    rec.onerror = (event) => {
      const why = event.error;
      // "The microphone could not be used." When it comes after a while of listening fine, it is
      // something else taking the microphone (another window, the system's own voice assistant):
      // that passes, so wait and try again. Right at the start, it means there is none: give up.
      const worked_first = listening_since > 0 && Date.now() - listening_since > 5000;
      if (why === 'audio-capture' && !worked_first) return give_up(why);
      if (why === 'not-allowed' || why === 'service-not-allowed') return give_up(why);
      if (why === 'no-speech' || why === 'aborted') return;  // normal: nobody spoke, or we stopped it
      fails += 1;
      state(`error ${why} (${fails})`);
      if (fails >= MAX_FAILS) give_up(`${why} x${fails}`);
    };
    // The browser ends a long listen by itself (silence, a hiccup, its service): start again,
    // at once when all is well, waiting longer and longer when it keeps failing.
    rec.onend = () => { live = false; if (wanted()) later(fails ? Math.min(1000 * 2 ** fails, 60_000) : 400); };
    try { rec.start(); live = true; } catch (err) {
      fails += 1;
      if (fails >= MAX_FAILS) give_up(err.message || String(err)); else later(2000);
    }
  }

  // Who may listen? Looked at every 1.5 s, and at once when another page changes the note.
  function look() {
    if (stopped) return;
    const note = readNote();
    const other = (freshOnce(note) && note.id !== `${me}-once`) || (freshWake(note) && note.id !== me);
    if (other && !yielded) {
      yielded = true;
      halt();
      state(note.kind === 'once' ? 'lent to a test or a button' : 'another screen has the microphone');
      return;
    }
    if (other) return;
    if (!freshOnce(note)) writeNote({ id: me, kind: 'wake', at: Date.now() });  // free, or ours: keep it
    if (yielded) { yielded = false; state('taking the microphone back'); later(600); }
  }
  const tick = setInterval(() => { if (stopped) { clearInterval(tick); return; } look(); }, 1500);
  window.addEventListener('storage', (event) => { if (event.key === NOTE) look(); });

  const self = {
    stop() { stopped = true; halt(); clearInterval(tick); if (readNote()?.id === me) writeNote(null); },
    // This page's own button borrows the microphone, then gives it back.
    pause() { if (borrowed) return; borrowed = true; halt(); },
    resume() { if (!borrowed || stopped) return; borrowed = false; later(600); },
  };
  running = self;
  window.addEventListener('pagehide', () => self.stop());
  look();
  if (wanted()) start();
  return self;
}

export function speak(text, lang, onSilent) {
  if (!('speechSynthesis' in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  let started = false;
  utterance.onstart = () => { started = true; };
  window.speechSynthesis.speak(utterance);
  if (onSilent) setTimeout(() => { if (!started) onSilent(); }, 1200);
}

// A touch, a click or a key is enough to let sound out afterwards: say nothing out loud,
// which is enough for the browser to count it as "the person asked for sound".
export function allowSound() {
  if (!('speechSynthesis' in window)) return;
  try { window.speechSynthesis.speak(new SpeechSynthesisUtterance('')); } catch { /* nothing to do */ }
}
