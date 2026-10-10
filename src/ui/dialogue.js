// Conversations: a greeting, then a list of topics. Tap to advance a line.
// Some answers can be challenged, L.A. Noire style: Believe, Press, or Prove a
// lie with a fact from the casebook. Each challenge is called once.
// A line may carry options as a third element: { tell } is a giveaway seen only in Focus, and { present } lets
// Holmes cut in while it is being said and show the fact that breaks it (Chapter III):
//   present: { id, evidence: [clue or deduction ids], gives, right: [lines], wrong: [lines] }
import { TALK, PEOPLE, CLUES, DEDUCTIONS, CHAPTER } from '../cases/current.js';

const $ = id => document.getElementById(id);
const CALLS = [['truth', 'Believe', 'Take it as the truth'], ['doubt', 'Press', 'Something is held back'], ['lie', 'Prove a lie', 'Show the fact that breaks it']];

export class Dialogue {
  constructor() {
    this.el = $('dialogue');
    this.who = this.el.querySelector('.who');
    this.line = this.el.querySelector('.line');
    this.tell = this.el.querySelector('.tell');
    this.choices = this.el.querySelector('.choices');
    // buttons used while a line is being said (Focus, Present evidence); kept apart from the topic choices
    this.inline = document.createElement('div');
    this.inline.className = 'inline';
    this.tell.after(this.inline);
    this.queue = [];
    this.asked = new Set();
    this.el.addEventListener('click', e => { if (!e.target.closest('button')) this.next(); });
  }

  // hooks: { state, onGive(id), onCall(right), onClose(), onEvent(name) }
  open(personId, hooks) {
    this.person = personId; this.hooks = hooks;
    this.el.classList.remove('hidden');
    const greeted = hooks.state.talked.includes(personId);
    const hello = TALK[personId].hello;
    this.play(greeted ? [hello[hello.length - 1]] : hello, () => this.menu());
    if (!greeted) { hooks.state.talked.push(personId); hooks.state.save(); }
  }

  play(lines, then) {
    this.queue = lines.slice();
    this.then = then;
    this.choices.innerHTML = '';
    this.setTell('');
    this.next();
  }

  next() {
    if (!this.queue.length) {
      if (this.then) { const t = this.then; this.then = null; t(); }
      return;
    }
    const [who, text, opts] = this.queue.shift();
    this.cur = opts ?? null;
    this.speaker(who);
    this.line.textContent = text;
    this.line.classList.remove('in'); void this.line.offsetWidth; this.line.classList.add('in');
    this.el.classList.add('reading');
    this.lineTools();
  }

  // while a line is said: its tell (in Focus only), a Focus toggle, and Present evidence when it can be broken
  lineTools() {
    this.inline.innerHTML = '';
    const o = this.cur, h = this.hooks;
    const focus = h?.focus?.() ?? false;
    if (!this.judging) this.setTell(o?.tell && focus ? o.tell : '');
    if (!CHAPTER.focusTalk || !h) return;
    const mk = (label, cls, fn) => {
      const b = document.createElement('button');
      b.className = cls; b.textContent = label;
      b.onclick = e => { e.stopPropagation(); fn(); };
      this.inline.appendChild(b);
    };
    mk(focus ? '◉ Focus' : '○ Focus', 'focus' + (focus ? ' on' : ''), () => { h.toggleFocus?.(); this.lineTools(); });
    const p = o?.present, open = p && (!(('p:' + p.id) in h.state.calls) || (p.gives && !h.state.has(p.gives)));
    if (open) mk('Present evidence', 'present', () => this.present(p));
  }

  // cut in mid-speech with a fact
  present(p) {
    const { state } = this.hooks;
    const rest = this.queue, then = this.then;
    this.inline.innerHTML = '';
    this.choices.innerHTML = '';
    this.setTell('Which fact gives the lie to what she is saying?');
    this.el.classList.add('judging'); this.judging = true;
    const done = right => {
      this.el.classList.remove('judging'); this.judging = false;
      if (!(('p:' + p.id) in state.calls)) { state.calls['p:' + p.id] = right; state.save(); }
      this.hooks.onCall(right);
      if (right) this.play(p.right, () => { if (p.gives) this.hooks.onGive(p.gives); then?.(); });
      else this.play([...p.wrong, ...rest], then);  // the lie goes on
    };
    for (const id of [...state.clues, ...state.deductions]) {
      const src = CLUES[id] ?? DEDUCTIONS[id];
      this.button(src.title, 'fact', () => done(p.evidence.includes(id)));
    }
    this.button('Let her go on…', 'bye', () => {
      this.el.classList.remove('judging'); this.judging = false;
      this.choices.innerHTML = ''; this.lineTools();
    });
  }

  // Focus was switched on or off: show or hide the tell on the current line
  refresh() { if (!this.el.classList.contains('hidden') && this.el.classList.contains('reading')) this.lineTools(); }

  speaker(who) {
    this.who.textContent = who;
    this.who.className = 'who' + (who === 'Holmes' ? ' holmes' : '');
  }

  setTell(text) {
    this.tell.textContent = text;
    this.tell.classList.toggle('hidden', !text);
  }

  button(label, cls, onClick, sub) {
    const b = document.createElement('button');
    b.className = cls || '';
    b.innerHTML = '<span></span>' + (sub ? '<small></small>' : '');
    b.firstChild.textContent = label;
    if (sub) b.lastChild.textContent = sub;
    b.onclick = e => { e.stopPropagation(); onClick(); };
    this.choices.appendChild(b);
    return b;
  }

  menu() {
    this.el.classList.remove('reading');
    this.inline.innerHTML = ''; this.cur = null;
    const { state } = this.hooks;
    this.speaker(PEOPLE[this.person].name);
    this.line.textContent = '';
    this.choices.innerHTML = '';
    this.setTell('');
    TALK[this.person].topics.forEach((t, i) => {
      if (t.needs && !t.needs.every(n => state.has(n))) return;
      if (t.event && state.events.includes(t.event)) return;
      if (t.after && !state.events.includes(t.after)) return;   // only once something has happened
      if (t.before && state.events.includes(t.before)) return;  // only until it has
      const key = this.person + i;
      const called = t.challenge && key in state.calls;
      // a wrong call costs the rating, never the case: while its testimony is missing it can be put again
      const retry = t.challenge && called && t.challenge.gives && !state.has(t.challenge.gives);
      const done = !retry && (this.asked.has(key) || (t.gives && state.has(t.gives)) || called);
      const b = this.button(t.q, done ? 'asked' : '', () => {
        this.asked.add(key);
        this.play([['Holmes', t.q], ...t.a], () => {
          if (t.event) { const h = this.hooks; this.close(); h.onEvent?.(t.event); return; }  // the scene breaks off
          if (t.gives) this.hooks.onGive(t.gives);
          if (t.challenge && (!(key in state.calls) || retry)) this.challenge(key, t.challenge);
          else this.menu();
        });
      });
      if (t.challenge) b.classList.add(...(called && !retry ? ['called', state.calls[key] ? 'right' : 'wrong'] : ['contest']));
    });
    this.button('That will be all.', 'bye', () => this.close());
  }

  // Believe / Press / Prove a lie
  challenge(key, c) {
    this.el.classList.remove('reading');
    this.el.classList.add('judging');
    this.inline.innerHTML = '';
    this.setTell(c.focusTell && !this.hooks.focus?.() ? 'Something in her manner. Focus to read it.' : c.tell);
    this.choices.innerHTML = '';
    if (c.focusTell && CHAPTER.focusTalk) this.button(this.hooks.focus?.() ? '◉ Focus' : '○ Focus', 'focus', () => { this.hooks.toggleFocus?.(); this.challenge(key, c); });
    for (const [id, label, sub] of CALLS) {
      this.button(label, 'call ' + id, () => id === 'lie' ? this.evidence(key, c) : this.resolve(key, c, id === c.answer), sub);
    }
  }

  // pick the fact that breaks the statement
  evidence(key, c) {
    const { state } = this.hooks;
    this.choices.innerHTML = '';
    this.setTell('Which fact gives the lie to it?');
    for (const id of [...state.clues, ...state.deductions]) {
      const src = CLUES[id] ?? DEDUCTIONS[id];
      this.button(src.title, 'fact', () => this.resolve(key, c, c.answer === 'lie' && c.evidence.includes(id)));
    }
    this.button('On second thought…', 'bye', () => this.challenge(key, c));
  }

  resolve(key, c, right) {
    this.el.classList.remove('judging');
    const st = this.hooks.state;
    if (!(key in st.calls)) { st.calls[key] = right; st.save(); }  // the first call is the one that counts
    this.hooks.onCall(right);
    this.play(right ? c.right : c.wrong, () => {
      if (right && c.gives) this.hooks.onGive(c.gives);
      this.menu();
    });
  }

  close() {
    this.el.classList.add('hidden');
    this.el.classList.remove('judging'); this.judging = false;
    this.inline.innerHTML = '';
    this.hooks?.onClose();
  }
}
