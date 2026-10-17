// Voice control, done by the tablet's own browser and microphone (the Raspberry Pi needs none).
//
//   1. You tap the microphone button and say a short sentence.
//   2. The browser turns the speech into text. NOTE: in Chrome this step is done by Google's
//      speech service over the internet - the audio leaves the tablet. The settings page says so.
//   3. The text goes to Beranda (/api/voice), which works out what you meant and answers.
//   4. The tablet reads the answer aloud and, for the radio, starts or stops the sound.
//
// The microphone only listens while a tap on the button asked it to: Beranda keeps no
// microphone open in the background. (An always-on wake word was tried in 0.17.2-0.17.7
// and taken out again: a browser's continuous listening proved too fragile to trust.)
//
// Browsers only allow microphones on "secure" pages (https, or localhost). A tablet opening
// http://beranda.local:8080 is not secure, so `availability()` explains what is wrong and the
// settings page says how to allow it. Beranda's own https (self-made certificate) is enough.

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

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
export function listenOnce(lang) {
  return new Promise((resolve, reject) => {
    let over = false;
    // A browser sometimes answers nothing at all: no words, no error, no end. Give up after
    // a while instead of leaving the button stuck on "Listening...".
    const guard = setTimeout(() => { try { rec.stop(); } catch { /* already */ } failed(new Error('no answer')); }, 12_000);
    const done = (text) => { if (over) return; over = true; clearTimeout(guard); resolve(text); };
    const failed = (err) => { if (over) return; over = true; clearTimeout(guard); reject(err); };
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

// Browsers refuse to make a sound on a page nobody has touched yet (the same rule that stops
// a video playing by itself). `onSilent` is called when that happens, so the page can say
// "touch the screen once" instead of staying quiet with no explanation.
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
