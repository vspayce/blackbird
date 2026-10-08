// The Notebook (everything gathered, by tab) and the Mind Palace: a board of
// facts where picking two that belong together draws a deduction, threaded
// back to what it came from and on toward the question the chapter ends on.
import { CHAPTER, CLUES, DEDUCTIONS, CONCLUSION, PEOPLE, ABSENT, READS, combine, wrongLine } from '../cases/current.js';

const $ = id => document.getElementById(id);
const KIND = { memory: 'Remembered', clue: 'Observed', testimony: 'Heard' };
const esc = s => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const TABS = [['case', 'Case'], ['clues', 'Clues'], ['people', 'People'], ['deductions', 'Deductions']];

export class Casebook {
  constructor() {
    this.el = $('book');
    this.tab = 'case';
  }

  open(state, onClose) {
    this.state = state;
    this.onClose = onClose;
    this.el.classList.remove('hidden');
    this.render();
  }

  render() {
    const el = this.el;
    el.innerHTML = `<div class="notebook">
        <div class="page"><header><h2></h2><button class="close" aria-label="Close notebook">✕</button></header><div class="body"></div></div>
        <nav class="tabs">${TABS.map(([id, n]) => `<button data-t="${id}" class="${id === this.tab ? 'on' : ''}">${n}</button>`).join('')}</nav>
      </div>`;
    el.querySelector('h2').textContent = TABS.find(t => t[0] === this.tab)[1];
    el.querySelector('.close').onclick = () => { el.classList.add('hidden'); this.onClose(); };
    el.querySelectorAll('.tabs button').forEach(b => (b.onclick = () => { this.tab = b.dataset.t; this.render(); }));
    el.querySelector('.body').innerHTML = this[this.tab]();
  }

  case() {
    const s = this.state;
    const keys = CONCLUSION.needs.filter(d => s.deductions.includes(d)).length;
    return `<p class="chapter">${esc(CHAPTER.title)}</p>
      <div class="objective-note"><small>Current line of inquiry</small><p>${esc(s.objective())}</p></div>
      <p class="hand">${esc(CHAPTER.summary)}</p>
      <ul class="tally">
        <li><span>Clues</span><b>${s.clues.length} / ${Object.keys(CLUES).length}</b></li>
        <li><span>Deductions</span><b>${s.deductions.length} / ${Object.keys(DEDUCTIONS).length}</b></li>
        <li><span>Key deductions</span><b>${keys} / ${CONCLUSION.needs.length}</b></li>
      </ul>`;
  }

  clues() {
    const s = this.state;
    const n = Object.keys(CLUES).length;
    return `<p class="count">${s.clues.length} of ${n} found${s.clues.length < n ? '. There is more to see.' : '. Nothing has been missed.'}</p>` +
      s.clues.map(id => {
        const c = CLUES[id];
        return `<article class="entry ${c.kind}"><span class="stamp">${KIND[c.kind]}</span><h4>${esc(c.title)}</h4><p>${esc(c.text)}</p></article>`;
      }).join('');
  }

  people() {
    const s = this.state;
    const list = [
      ...Object.entries(ABSENT).filter(([, p]) => !p.needs || s.has(p.needs)),
      ...Object.entries(PEOPLE).filter(([id]) => id === 'watson' || s.talked.includes(id)),
    ];
    return list.map(([id, p]) => {
      const seen = (READS[id] ?? []).filter((_, i) => s.reads.includes(`${id}:${i}`));
      const said = s.clues.filter(c => CLUES[c].who === id).map(c => CLUES[c].text);
      return `<article class="person"><h4>${esc(p.name)}</h4><p class="role">${esc(p.role)}</p><p>${esc(p.note)}</p>
        ${seen.length ? `<p class="sub">Observed</p><ul>${seen.map(t => `<li>${esc(t)}</li>`).join('')}</ul>` : ''}
        ${said.length ? `<p class="sub">Testimony</p><ul>${said.map(t => `<li>${esc(t)}</li>`).join('')}</ul>` : ''}</article>`;
    }).join('');
  }

  deductions() {
    const s = this.state;
    if (!s.deductions.length) return '<p class="count">Nothing yet. Facts are combined in the Mind Palace.</p>';
    return s.deductions.map(id => {
      const d = DEDUCTIONS[id];
      const from = d.from.map(f => (CLUES[f] ?? DEDUCTIONS[f]).title).join(' + ');
      return `<article class="entry deduction${d.key ? ' key' : ''}">${d.key ? '<span class="stamp">Key</span>' : ''}<h4>${esc(d.title)}</h4><p>${esc(d.text)}</p><p class="from">${esc(from)}</p></article>`;
    }).join('');
  }
}

// --- Mind Palace ------------------------------------------------------------
const W = 172, H = 54, ROW = 64, COL = 236, PAD = 18;

function depth(id) {
  const d = DEDUCTIONS[id];
  return d ? 1 + Math.max(...d.from.map(depth)) : 0;
}

export class MindPalace {
  constructor() {
    this.el = $('palace');
  }

  // hooks: { state, onDeduce(id), onMiss(), onConclude(), onClose(), sound }
  open(hooks) {
    this.hooks = hooks;
    this.sel = [];
    this.fresh = null;
    this.el.classList.remove('hidden');
    this.render('Choose two facts that speak to one another.');
  }

  layout() {
    const { state } = this.hooks;
    const order = Object.keys(DEDUCTIONS);
    const firstUse = id => { const i = order.findIndex(k => DEDUCTIONS[k].from.includes(id)); return i < 0 ? 99 : i; };
    const pos = {};
    const clues = state.clues.slice().sort((a, b) => firstUse(a) - firstUse(b));
    clues.forEach((id, i) => (pos[id] = { x: 0, y: i * ROW }));
    const deds = state.deductions.slice().sort((a, b) => depth(a) - depth(b) || order.indexOf(a) - order.indexOf(b));
    const cols = {};
    for (const id of deds) (cols[depth(id)] ??= []).push(id);
    for (const [c, ids] of Object.entries(cols)) {
      // sit each deduction level with its sources, then nudge apart
      const want = ids.map(id => {
        const ys = DEDUCTIONS[id].from.filter(f => pos[f]).map(f => pos[f].y);
        return [id, ys.reduce((a, b) => a + b, 0) / ys.length];
      }).sort((a, b) => a[1] - b[1]);
      let last = -Infinity;
      for (const [id, y] of want) { const yy = Math.max(y, last + ROW); pos[id] = { x: c * COL, y: yy }; last = yy; }
    }
    const maxDepth = Math.max(2, ...Object.keys(cols).map(Number));
    const made = CONCLUSION.needs.filter(d => pos[d]);
    const cy = made.length ? made.reduce((a, d) => a + pos[d].y, 0) / made.length : (clues.length - 1) * ROW / 2;
    pos.$end = { x: (maxDepth + 1) * COL, y: Math.max(0, cy) };
    return pos;
  }

  render(msg) {
    const { state } = this.hooks;
    const el = this.el;
    const pos = this.layout();
    const w = Math.max(...Object.values(pos).map(p => p.x)) + W + PAD * 2;
    const h = Math.max(...Object.values(pos).map(p => p.y)) + H + PAD * 2;
    el.innerHTML = `<header><h2>Mind Palace</h2><p class="thought"></p><button class="close" aria-label="Close">✕</button></header>
      <div class="board"><div class="plane" style="width:${w}px;height:${h}px"><svg width="${w}" height="${h}"></svg></div></div>
      <footer><span class="count"></span></footer>`;
    el.querySelector('.thought').textContent = msg;
    el.querySelector('.close').onclick = () => { el.classList.add('hidden'); this.hooks.onClose(); };
    const plane = el.querySelector('.plane'), svg = el.querySelector('svg');

    const thread = (a, b, cls) => {
      const x1 = a.x + W + PAD, y1 = a.y + H / 2 + PAD, x2 = b.x + PAD, y2 = b.y + H / 2 + PAD, mx = (x1 + x2) / 2;
      const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', `M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`);
      p.setAttribute('class', cls);
      svg.appendChild(p);
    };
    for (const id of state.deductions) {
      for (const f of DEDUCTIONS[id].from) if (pos[f]) thread(pos[f], pos[id], DEDUCTIONS[id].key ? 'key' : '');
    }
    for (const d of CONCLUSION.needs) if (pos[d]) thread(pos[d], pos.$end, 'key');

    const node = (id, title, cls, onClick) => {
      const b = document.createElement('button');
      b.className = 'node ' + cls;
      b.style.left = pos[id].x + PAD + 'px'; b.style.top = pos[id].y + PAD + 'px';
      b.textContent = title;
      b.onclick = onClick;
      plane.appendChild(b);
      return b;
    };
    for (const id of [...state.clues, ...state.deductions]) {
      const ded = DEDUCTIONS[id];
      const src = ded ?? CLUES[id];
      let cls = ded ? 'deduction' + (ded.key ? ' key' : '') : src.kind;
      if (this.sel.includes(id)) cls += ' sel';
      if (id === this.fresh) cls += ' fresh';
      // a fact is spent once every deduction it feeds has been made
      const feeds = Object.entries(DEDUCTIONS).filter(([, d]) => d.from.includes(id));
      if (feeds.length && feeds.every(([k]) => state.deductions.includes(k))) cls += ' spent';
      node(id, src.title, cls, () => this.pick(id));
    }
    const end = node('$end', CONCLUSION.question, 'conclusion' + (state.canConclude ? ' ready' : ''), () => {
      if (!state.canConclude) return this.render('Not yet. I have not enough to name anyone.');
      el.classList.add('hidden'); this.hooks.onConclude();
    });
    end.setAttribute('aria-label', state.canConclude ? 'Name the killer' : CONCLUSION.question);

    const total = Object.keys(DEDUCTIONS).length;
    const keys = CONCLUSION.needs.filter(d => state.deductions.includes(d)).length;
    el.querySelector('.count').textContent = `Threads drawn ${state.deductions.length} / ${total} · Key ${keys} / ${CONCLUSION.needs.length}` +
      (state.canConclude ? ' · Tap the question to name the killer' : '');
    if (this.fresh) requestAnimationFrame(() => plane.querySelector('.fresh')?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' }));
    this.fresh = null;
  }

  pick(id) {
    const src = CLUES[id] ?? DEDUCTIONS[id];
    const i = this.sel.indexOf(id);
    if (i >= 0) { this.sel.splice(i, 1); this.render('Choose two facts that speak to one another.'); return; }
    this.sel.push(id);
    if (this.sel.length < 2) { this.render(src.text + ' …and what does it speak to?'); return; }
    const [a, b] = this.sel;
    this.sel = [];
    const d = combine(a, b);
    if (d && !this.hooks.state.deductions.includes(d)) {
      this.hooks.onDeduce(d);
      this.fresh = d;
      this.render(DEDUCTIONS[d].title + '. ' + DEDUCTIONS[d].text);
      this.el.querySelector('.thought').classList.add('eureka');
    } else if (d) {
      this.render('I have already drawn that thread.');
    } else {
      this.hooks.onMiss();
      this.render(wrongLine());
      this.el.querySelector('.thought').classList.add('miss');
    }
  }
}
