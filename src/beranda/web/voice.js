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

export function availability() {
  if (!Recognition) return 'unsupported';
  if (!window.isSecureContext) return 'insecure';
  return 'ok';
}

// Listen once; resolves with the text heard ('' if nothing was said), rejects with a short
// error name ('not-allowed' when the microphone is blocked, ...).
export function listenOnce(lang) {
  return new Promise((resolve, reject) => {
    const rec = new Recognition();
    rec.lang = lang;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    let heard = '';
    rec.onresult = (event) => { heard = event.results[0]?.[0]?.transcript || ''; };
    rec.onerror = (event) => { if (event.error !== 'no-speech' && event.error !== 'aborted') reject(new Error(event.error)); };
    rec.onend = () => resolve(heard);
    try { rec.start(); } catch (err) { reject(err); }
  });
}

// Keep listening, all the time, for one word ("Beranda"); what follows it in the same breath
// is the command. If only the word was said, the next sentence is the command. The browser
// stops a long listen now and then (silence, a hiccup): `onend` simply starts it again.
// Nothing is sent anywhere by Beranda; the browser's own speech service does the listening.
export function wakeListener({ lang, word, onWake, onCommand, onError }) {
  if (!Recognition) return { stop() {} };
  const normalise = (s) => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^\p{L}\p{N}\s']/gu, ' ').replace(/\s+/g, ' ').trim();
  const wake = normalise(word);
  let rec = null;
  let stopped = false;
  let awake = false;  // the word was heard, the next sentence is the command
  let restartAt = 0;
  const start = () => {
    if (stopped) return;
    rec = new Recognition();
    rec.lang = lang;
    rec.continuous = true;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (event) => {
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
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') { stopped = true; onError(event.error); }
      else if (event.error !== 'no-speech' && event.error !== 'aborted') restartAt = Date.now() + 5000;  // network...: not at once
    };
    rec.onend = () => { if (!stopped) setTimeout(start, Math.max(300, restartAt - Date.now())); };
    try { rec.start(); } catch (err) { onError(err.message || String(err)); }
  };
  start();
  return { stop() { stopped = true; try { rec?.stop(); } catch { /* already */ } } };
}

export function speak(text, lang) {
  if (!('speechSynthesis' in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  window.speechSynthesis.speak(utterance);
}
