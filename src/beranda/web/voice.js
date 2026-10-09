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

export function speak(text, lang) {
  if (!('speechSynthesis' in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  window.speechSynthesis.speak(utterance);
}
