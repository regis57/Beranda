// The radio player, shared by the display and the settings page. It plays through the page's
// own <audio> element, so the sound comes out of whatever device shows the page (the tablet).
//
// Why a few odd-looking lines below: a live stream never "ends", so after pausing we drop the
// address completely. Otherwise pressing play again would first replay minutes of old audio
// that the browser had kept in its buffer.

const VOLUME_KEY = 'beranda.radio.volume';
const STATION_KEY = 'beranda.radio.station';

function readStore(key) {
  try { return localStorage.getItem(key); } catch { return null; } // private mode: just forget
}
function writeStore(key, value) {
  try { localStorage.setItem(key, String(value)); } catch { /* nothing to do */ }
}

export function createRadio(audio, onChange) {
  const saved = Number(readStore(VOLUME_KEY));
  let volume = readStore(VOLUME_KEY) !== null && Number.isFinite(saved) ? Math.min(100, Math.max(0, saved)) : null;
  let muted = false;
  let station = null;
  let status = 'idle'; // idle | loading | playing | error

  const set = (next) => { status = next; onChange?.(api.snapshot()); };
  const apply = () => { audio.volume = muted ? 0 : (volume ?? 70) / 100; };

  audio.addEventListener('playing', () => set('playing'));
  audio.addEventListener('waiting', () => { if (status === 'playing') set('loading'); });
  audio.addEventListener('error', () => { if (station) set('error'); });

  const api = {
    snapshot: () => ({ station, status, volume: volume ?? 70, muted }),
    // The first time ever, the volume the owner chose in the settings is used as the start.
    defaultVolume(percent) { if (volume === null) { volume = percent; apply(); onChange?.(api.snapshot()); } },
    lastStationId: () => readStore(STATION_KEY),
    async play(next) {
      station = next;
      writeStore(STATION_KEY, next.uuid || next.url);
      apply();
      set('loading');
      audio.src = next.url;
      try { await audio.play(); } catch { set('error'); } // a blocked or dead stream
    },
    stop() {
      audio.pause();
      audio.removeAttribute('src');
      audio.load();
      set('idle');
    },
    toggle(fallback) {
      if (status === 'playing' || status === 'loading') return api.stop();
      const target = station || fallback;
      if (target) return api.play(target);
    },
    setVolume(percent) {
      volume = Math.min(100, Math.max(0, Number(percent) || 0));
      muted = false;
      writeStore(VOLUME_KEY, volume);
      apply();
      onChange?.(api.snapshot());
    },
    toggleMute() { muted = !muted; apply(); onChange?.(api.snapshot()); },
  };
  apply();
  return api;
}
