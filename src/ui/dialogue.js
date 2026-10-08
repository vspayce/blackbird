// Conversations: a greeting, then a list of topics. Tap to advance a line.
// Some answers can be challenged, L.A. Noire style: Believe, Press, or Prove a
// lie with a fact from the casebook. Each challenge is called once.
import { TALK, PEOPLE, CLUES, DEDUCTIONS } from '../cases/archer.js';

const $ = id => document.getElementById(id);
const CALLS = [['truth', 'Believe', 'Take it as the truth'], ['doubt', 'Press', 'Something is held back'], ['lie', 'Prove a lie', 'Show the fact that breaks it']];

export class Dialogue {
  constructor() {
    this.el = $('dialogue');
    this.who = this.el.querySelector('.who');
    this.line = this.el.querySelector('.line');
    this.tell = this.el.querySelector('.tell');
    this.choices = this.el.querySelector('.choices');
    this.queue = [];
    this.asked = new Set();
    this.el.addEventListener('click', e => { if (!e.target.closest('button')) this.next(); });
  }

  // hooks: { state, onGive(id), onCall(right), onClose() }
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
    const [who, text] = this.queue.shift();
    this.speaker(who);
    this.line.textContent = text;
    this.line.classList.remove('in'); void this.line.offsetWidth; this.line.classList.add('in');
    this.el.classList.add('reading');
  }

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
    const { state } = this.hooks;
    this.speaker(PEOPLE[this.person].name);
    this.line.textContent = '';
    this.choices.innerHTML = '';
    this.setTell('');
    TALK[this.person].topics.forEach((t, i) => {
      if (t.needs && !t.needs.every(n => state.has(n))) return;
      const key = this.person + i;
      const called = t.challenge && key in state.calls;
      const done = this.asked.has(key) || (t.gives && state.has(t.gives)) || called;
      const b = this.button(t.q, done ? 'asked' : '', () => {
        this.asked.add(key);
        this.play([['Holmes', t.q], ...t.a], () => {
          if (t.gives) this.hooks.onGive(t.gives);
          if (t.challenge && !(key in state.calls)) this.challenge(key, t.challenge);
          else this.menu();
        });
      });
      if (t.challenge) b.classList.add(called ? (state.calls[key] ? 'called right' : 'called wrong') : 'contest');
    });
    this.button('That will be all.', 'bye', () => this.close());
  }

  // Believe / Press / Prove a lie
  challenge(key, c) {
    this.el.classList.remove('reading');
    this.el.classList.add('judging');
    this.setTell(c.tell);
    this.choices.innerHTML = '';
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
    this.hooks.state.calls[key] = right;
    this.hooks.state.save();
    this.hooks.onCall(right);
    this.play(right ? c.right : c.wrong, () => {
      if (right && c.gives) this.hooks.onGive(c.gives);
      this.menu();
    });
  }

  close() {
    this.el.classList.add('hidden');
    this.el.classList.remove('judging');
    this.hooks?.onClose();
  }
}
