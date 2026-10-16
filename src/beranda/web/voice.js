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
let running = null;

export function availability() {
  if (!Recognition) return 'unsupported';
  if (!window.isSecureContext) return 'insecure';
  return 'ok';
}

// Listen once; resolves with the text heard ('' if nothing was said), rejects with a short
// error name ('not-allowed' when the microphone is blocked, ...).
export function listenOnce(lang) {
  return new Promise((resolve, reject) => {
    running?.pause();  // the wake word steps aside: one listening at a time
    let over = false;
    const give_back = () => { if (over) return; over = true; running?.resume(); };
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

// Keep listening, all the time, for one word ("Beranda"); what follows it in the same breath
// is the command. If only the word was said, the next sentence is the command. The browser
// stops a long listen now and then (silence, a hiccup): `onend` simply starts it again.
// Nothing is sent anywhere by Beranda; the browser's own speech service does the listening.
export function wakeListener({ lang, word, onWake, onCommand, onError, onState }) {
  if (!Recognition) return { stop() {}, pause() {}, resume() {} };
  const wake = normalise(word);
  let rec = null;
  let stopped = false;
  let paused = false;
  let awake = false;  // the word was heard on its own: the next sentence is the command
  let fails = 0;      // failures in a row; the wait doubles, so a service that is down is left alone
  let timer = 0;

  const later = (ms) => { clearTimeout(timer); timer = setTimeout(start, ms); };
  const give_up = (why) => { stopped = true; clearTimeout(timer); onState?.('stopped'); onError(why); };

  function start() {
    if (stopped || paused) return;
    rec = new Recognition();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onstart = () => { onState?.('listening'); };
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
      if (why === 'not-allowed' || why === 'service-not-allowed' || why === 'audio-capture') return give_up(why);
      if (why === 'no-speech' || why === 'aborted') return;  // normal: nobody spoke, or we stopped it
      fails += 1;
      onState?.(`error ${why} (${fails})`);
      if (fails >= MAX_FAILS) give_up(`${why} x${fails}`);
    };
    // The browser ends a long listen by itself (silence, a hiccup, its service): start again,
    // at once when all is well, waiting longer and longer when it keeps failing.
    rec.onend = () => { if (!stopped && !paused) later(fails ? Math.min(1000 * 2 ** fails, 60_000) : 400); };
    try { rec.start(); } catch (err) { fails += 1; if (fails >= MAX_FAILS) give_up(err.message || String(err)); else later(2000); }
  }

  const self = {
    stop() { stopped = true; clearTimeout(timer); try { rec?.stop(); } catch { /* already stopped */ } },
    // The browser allows one listening at a time: the microphone button borrows it, then gives it back.
    pause() { if (paused) return; paused = true; clearTimeout(timer); onState?.('paused'); try { rec?.stop(); } catch { /* already */ } },
    resume() { if (!paused || stopped) return; paused = false; later(600); },
  };
  running = self;
  start();
  return self;
}

// Browsers refuse to make a sound on a page nobody has touched yet (the same rule that stops
// a video playing by itself). A wall display is never touched, so the first answer can be
// silent: `onSilent` is called then, and the page says "touch the screen once".
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
