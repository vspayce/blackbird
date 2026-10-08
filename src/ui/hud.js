// HUD: objective line, Focus button and meter, the context action button,
// toasts, Holmes's spoken remarks and the world-anchored labels and markers.
const $ = id => document.getElementById(id);

export class HUD {
  constructor() {
    this.root = $('hud');
    this.objective = $('objective').querySelector('span');
    this.objBox = $('objective');
    this.act = $('btn-act');
    this.actLabel = this.act.querySelector('span');
    this.focusBtn = $('btn-focus');
    this.focusRing = this.focusBtn.querySelector('.meter');
    this.back = $('btn-back');
    this.toasts = $('toasts');
    this.sayEl = $('say');
    this.layer = $('labels');
    this.pool = new Map();
    this.used = new Set();
    this.sayT = 0;
    this.sayEl.addEventListener('click', () => this.hideSay());
  }

  show(on) { this.root.classList.toggle('hidden', !on); this.layer.classList.toggle('hidden', !on); }

  setObjective(text) {
    if (this.objective.textContent !== text) {
      this.objective.textContent = text;
      this.objBox.classList.remove('flash'); void this.objBox.offsetWidth; this.objBox.classList.add('flash');
    }
  }

  setAct(label) {
    this.act.classList.toggle('hidden', !label);
    if (label) this.actLabel.textContent = label;
  }

  setFocus(on, meter) {
    this.focusBtn.classList.toggle('on', on);
    this.focusRing.style.setProperty('--p', meter.toFixed(3));
  }

  // a slip of paper tucked into the notebook: new clue, testimony, deduction, or a call in an interrogation
  toast(kind, text) {
    const d = document.createElement('div');
    d.className = 'toast ' + kind;
    const head = { deduction: 'Deduction', testimony: 'Testimony noted', clue: 'Clue noted', right: 'Well read', wrong: 'A misstep' }[kind];
    d.innerHTML = `<small>${head}</small><b></b>`;
    d.querySelector('b').textContent = text;
    this.toasts.appendChild(d);
    setTimeout(() => d.classList.add('out'), 3000);
    setTimeout(() => d.remove(), 3600);
  }

  // Holmes thinking aloud: tap to dismiss, otherwise fades on its own
  say(text, who = 'Holmes') {
    this.sayEl.innerHTML = '<b></b><span></span>';
    this.sayEl.querySelector('b').textContent = who;
    this.sayEl.querySelector('span').textContent = text;
    this.sayEl.classList.remove('hidden');
    this.sayT = 2.5 + text.length * 0.045;
  }
  hideSay() { this.sayEl.classList.add('hidden'); this.sayT = 0; }

  update(dt) {
    if (this.sayT > 0 && (this.sayT -= dt) <= 0) this.hideSay();
  }

  // --- world labels: call begin(), label() for each, then end() ---
  begin() { this.used.clear(); }

  label(key, x, y, text, cls, onClick) {
    let el = this.pool.get(key);
    if (!el) {
      el = document.createElement(onClick ? 'button' : 'div');
      el.innerHTML = '<span></span>';
      if (onClick) el.addEventListener('click', e => { e.stopPropagation(); el._click?.(); });
      this.layer.appendChild(el);
      this.pool.set(key, el);
    }
    el._click = onClick;
    el.className = 'wl ' + cls;
    const s = el.firstChild;
    if (s.textContent !== text) s.textContent = text;
    if (onClick) el.setAttribute('aria-label', text);
    el.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px)`;
    el.style.display = '';
    this.used.add(key);
  }

  end() {
    for (const [k, el] of this.pool) if (!this.used.has(k)) el.style.display = 'none';
  }
}
