// Saved games: an autosave and three manual slots, shared by every chapter, in this browser's storage. A save
// holds the chapter, the case state and where Holmes stands. Save codes carry a save to another device as text.
const KEY = 'blackbird.saves.v1';
export const SLOTS = ['auto', '1', '2', '3'];

function all() {
  try { return JSON.parse(localStorage.getItem(KEY)) ?? {}; } catch { return {}; }
}

export const saves = {
  list() { const a = all(); return SLOTS.map(id => ({ id, data: a[id] ?? null })); },
  read(id) { return all()[id] ?? null; },
  write(id, data) {
    const a = all(); a[id] = data;
    try { localStorage.setItem(KEY, JSON.stringify(a)); return true; } catch { return false; }
  },
  latest() { return Object.values(all()).sort((x, y) => y.savedAt - x.savedAt)[0] ?? null; },
  // a save as a copyable string, and back
  encode(data) { return 'BB1.' + btoa(unescape(encodeURIComponent(JSON.stringify(data)))); },
  decode(code) {
    try {
      const s = code.trim();
      if (!s.startsWith('BB1.')) return null;
      const d = JSON.parse(decodeURIComponent(escape(atob(s.slice(4)))));
      return d && d.chapter && d.state ? d : null;
    } catch { return null; }
  },
};

export function describe(d) {
  if (!d) return 'Empty';
  const when = new Date(d.savedAt).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
  return `${d.title} · ${when}`;
}
