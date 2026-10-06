// Conversations: a greeting, then a list of topics. Tap to advance a line.
import { TALK, PEOPLE } from '../cases/archer.js';

const $ = id => document.getElementById(id);

export class Dialogue {
  constructor() {
    this.el = $('dialogue');
    this.who = this.el.querySelector('.who');
    this.line = this.el.querySelector('.line');
    this.choices = this.el.querySelector('.choices');
    this.queue = [];
    this.asked = new Set();
    this.el.addEventListener('click', e => { if (!e.target.closest('button')) this.next(); });
  }

  // hooks: { state, onGive(id), onClose() }
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
    this.next();
  }

  next() {
    if (!this.queue.length) {
      if (this.then) { const t = this.then; this.then = null; t(); }
      return;
    }
    const [who, text] = this.queue.shift();
    this.who.textContent = who;
    this.who.className = 'who ' + (who === 'Holmes' ? 'holmes' : '');
    this.line.textContent = text;
    this.el.classList.add('reading');
  }

  menu() {
    this.el.classList.remove('reading');
    const { state } = this.hooks;
    this.who.textContent = PEOPLE[this.person].name;
    this.who.className = 'who';
    this.line.textContent = '';
    this.choices.innerHTML = '';
    TALK[this.person].topics.forEach((t, i) => {
      if (t.needs && !t.needs.every(n => state.has(n))) return;
      const key = this.person + i;
      const b = document.createElement('button');
      b.textContent = t.q;
      if (this.asked.has(key) || (t.gives && state.has(t.gives))) b.classList.add('asked');
      b.onclick = () => {
        this.asked.add(key);
        this.play([['Holmes', t.q], ...t.a], () => {
          if (t.gives) this.hooks.onGive(t.gives);
          this.menu();
        });
      };
      this.choices.appendChild(b);
    });
    const bye = document.createElement('button');
    bye.textContent = 'That will be all.';
    bye.className = 'bye';
    bye.onclick = () => this.close();
    this.choices.appendChild(bye);
  }

  close() {
    this.el.classList.add('hidden');
    this.hooks?.onClose();
  }
}
