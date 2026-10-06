// The Casebook (everything gathered, read-only) and the Mind Palace (pick two
// facts; if they belong together Holmes draws the deduction).
import { CLUES, DEDUCTIONS, CONCLUSION, combine, wrongLine } from '../cases/archer.js';

const $ = id => document.getElementById(id);
const KIND = { memory: 'Memory', clue: 'Clue', testimony: 'Testimony' };

function card(title, text, cls) {
  const d = document.createElement('div');
  d.className = 'card ' + cls;
  d.innerHTML = '<h4></h4><p></p>';
  d.querySelector('h4').textContent = title;
  d.querySelector('p').textContent = text;
  return d;
}

export class Casebook {
  constructor() {
    this.el = $('book');
  }

  open(state, onClose) {
    const el = this.el;
    el.innerHTML = '<header><h2>Casebook</h2><button class="close">Close</button></header><div class="body"></div>';
    el.querySelector('.close').onclick = () => { el.classList.add('hidden'); onClose(); };
    const body = el.querySelector('.body');
    const obj = document.createElement('p');
    obj.className = 'obj'; obj.textContent = 'Now: ' + state.objective();
    body.appendChild(obj);
    const section = (name, items) => {
      if (!items.length) return;
      const h = document.createElement('h3'); h.textContent = name; body.appendChild(h);
      const grid = document.createElement('div'); grid.className = 'grid';
      for (const it of items) grid.appendChild(it);
      body.appendChild(grid);
    };
    section('Clues', state.clues.filter(c => CLUES[c].kind !== 'testimony').map(c => card(CLUES[c].title, CLUES[c].text, CLUES[c].kind)));
    section('Testimony', state.clues.filter(c => CLUES[c].kind === 'testimony').map(c => card(CLUES[c].title, CLUES[c].text, 'testimony')));
    section('Deductions', state.deductions.map(d => card(DEDUCTIONS[d].title, DEDUCTIONS[d].text, 'deduction' + (DEDUCTIONS[d].key ? ' key' : ''))));
    el.classList.remove('hidden');
  }
}

export class MindPalace {
  constructor() {
    this.el = $('palace');
  }

  // hooks: { state, onDeduce(id), onConclude(), onClose(), sound }
  open(hooks) {
    this.hooks = hooks;
    this.sel = [];
    this.el.classList.remove('hidden');
    this.render('Choose two facts that speak to one another.');
  }

  render(msg) {
    const { state } = this.hooks;
    const el = this.el;
    el.innerHTML = `<header><h2>Mind Palace</h2><button class="close">Close</button></header>
      <p class="thought"></p><div class="body"><div class="grid"></div></div>
      <footer><span class="count"></span><button class="conclude">Name the killer</button></footer>`;
    el.querySelector('.thought').textContent = msg;
    el.querySelector('.close').onclick = () => { el.classList.add('hidden'); this.hooks.onClose(); };
    const grid = el.querySelector('.grid');

    const ids = [...state.clues, ...state.deductions];
    for (const id of ids) {
      const ded = DEDUCTIONS[id];
      const src = ded ?? CLUES[id];
      const c = card(src.title, src.text, ded ? 'deduction' + (ded.key ? ' key' : '') : src.kind);
      c.tabIndex = 0;
      if (this.sel.includes(id)) c.classList.add('sel');
      // a fact is spent once every deduction it feeds has been made
      const feeds = Object.entries(DEDUCTIONS).filter(([, d]) => d.from.includes(id));
      if (feeds.length && feeds.every(([k]) => state.deductions.includes(k))) c.classList.add('spent');
      c.onclick = () => this.pick(id);
      grid.appendChild(c);
    }

    const total = Object.keys(DEDUCTIONS).length;
    const keys = CONCLUSION.needs.filter(d => state.deductions.includes(d)).length;
    el.querySelector('.count').textContent = `Deductions ${state.deductions.length}/${total} · Key ${keys}/${CONCLUSION.needs.length}`;
    const btn = el.querySelector('.conclude');
    btn.disabled = !state.canConclude;
    btn.onclick = () => { el.classList.add('hidden'); this.hooks.onConclude(); };
  }

  pick(id) {
    const i = this.sel.indexOf(id);
    if (i >= 0) { this.sel.splice(i, 1); this.render('Choose two facts that speak to one another.'); return; }
    this.sel.push(id);
    if (this.sel.length < 2) { this.render('…and what does it connect to?'); return; }
    const [a, b] = this.sel;
    this.sel = [];
    const d = combine(a, b);
    if (d && !this.hooks.state.deductions.includes(d)) {
      this.hooks.onDeduce(d);
      this.render(DEDUCTIONS[d].title + '. ' + DEDUCTIONS[d].text);
      this.el.querySelector('.thought').classList.add('eureka');
    } else if (d) {
      this.render('I have already drawn that thread.');
    } else {
      this.hooks.sound.wrong();
      this.render(wrongLine());
    }
  }
}
