// Full-screen cards: title, chapter intro, the accusation and the ending.
import { CHAPTER, CONCLUSION } from '../cases/current.js';
import { describe } from '../game/saves.js';
import { rideNext } from './ride.js';

const el = () => document.getElementById('screen');

function show(html) {
  const s = el();
  s.innerHTML = html;
  s.classList.add('show');
  return s;
}
export function hideScreen() { el().classList.remove('show'); }

// The title. latest: the most recent save anywhere (Continue resumes it, in whatever chapter); onLoad opens the
// slots; scenes: [[label, query string]] to jump straight to a scene.
export function titleScreen({ latest, onNew, onContinue, onLoad, scenes = [] }) {
  const s = show(`<div class="title">
      <p class="pre">A Sherlock Holmes Mystery</p>
      <h1>The Black Bird</h1>
      <p class="sub">${CHAPTER.title}</p>
      <div class="btns">
        ${latest ? '<button class="primary" data-a="continue">Continue</button>' : ''}
        <button class="${latest ? '' : 'primary'}" data-a="new">${latest ? 'New game' : 'Begin'}</button>
        <button data-a="load">Load</button>
        ${scenes.length ? '<button data-a="scenes">Scenes</button>' : ''}
      </div>
      ${latest ? `<p class="resume"></p>` : ''}
      <div class="scenes hidden">${scenes.map(([label, q]) => `<a href="./${q}">${label}</a>`).join('')}
        <button class="reset" data-a="reset">Reset all progress (testing)</button></div>
      <p class="credit">After Dashiell Hammett's <i>The Maltese Falcon</i> (1930) and Arthur Conan Doyle.</p>
    </div>`);
  if (latest) s.querySelector('.resume').textContent = describe(latest) + (latest.objective ? ` · ${latest.objective}` : '');
  s.querySelector('[data-a=new]').onclick = onNew;
  s.querySelector('[data-a=continue]')?.addEventListener('click', onContinue);
  s.querySelector('[data-a=load]').onclick = onLoad;
  s.querySelector('[data-a=scenes]')?.addEventListener('click', () => s.querySelector('.scenes').classList.toggle('hidden'));
  for (const a of s.querySelectorAll('.scenes a')) a.addEventListener('click', () => rideNext());  // arrive by cab
  // wipe every save, autosave and chapter's progress in this browser (a second tap confirms)
  const reset = s.querySelector('[data-a=reset]');
  reset.onclick = e => {
    e.stopPropagation();
    if (!reset.classList.contains('confirm')) { reset.classList.add('confirm'); reset.textContent = 'Tap again: erase every save'; return; }
    for (const store of [localStorage, sessionStorage]) {
      try { for (const k of Object.keys(store)) if (k.startsWith('blackbird.')) store.removeItem(k); } catch { /* blocked */ }
    }
    location.href = './';
  };
}

// The pause menu
export function pauseMenu({ objective, onResume, onSave, onLoad, onCode, onTitle }) {
  const s = show(`<div class="menu"><p class="pre">Paused</p><h2>${CHAPTER.title}</h2><p class="obj"></p>
      <div class="col">
        <button class="primary" data-a="resume">Resume</button>
        <button data-a="save">Save game</button>
        <button data-a="load">Load game</button>
        <button data-a="code">Save code</button>
        <button data-a="title">Title screen</button>
      </div>
      <p class="note">The game also saves itself as you play.</p></div>`);
  s.querySelector('.obj').textContent = objective;
  const on = (a, f) => (s.querySelector(`[data-a=${a}]`).onclick = e => { e.stopPropagation(); f(); });
  on('resume', onResume); on('save', onSave); on('load', onLoad); on('code', onCode); on('title', onTitle);
}

// Pick a save slot. mode 'save' writes (manual slots only), 'load' reads (any slot with a save, or a code).
export function slotPicker({ mode, slots, onPick, onBack, onEnterCode }) {
  const s = show(`<div class="menu"><p class="pre">${mode === 'save' ? 'Save game' : 'Load game'}</p>
      <div class="col slots"></div>
      <div class="col">${mode === 'load' ? '<button data-a="code">Enter a save code</button>' : ''}<button data-a="back">Back</button></div>
      <p class="reply"></p></div>`);
  const col = s.querySelector('.slots');
  for (const { id, data } of slots) {
    if (mode === 'save' && id === 'auto') continue;
    const b = document.createElement('button');
    b.className = 'slot';
    b.innerHTML = '<b></b><small></small>';
    b.querySelector('b').textContent = id === 'auto' ? 'Autosave' : `Slot ${id}`;
    b.querySelector('small').textContent = describe(data);
    b.disabled = mode === 'load' && !data;
    b.onclick = e => {
      e.stopPropagation();
      if (mode === 'save' && data && !b.classList.contains('confirm')) {  // overwriting: ask once
        b.classList.add('confirm'); b.querySelector('small').textContent = 'Tap again to overwrite'; return;
      }
      onPick(id);
    };
    col.appendChild(b);
  }
  s.querySelector('[data-a=back]').onclick = e => { e.stopPropagation(); onBack(); };
  s.querySelector('[data-a=code]')?.addEventListener('click', e => { e.stopPropagation(); onEnterCode(); });
  return msg => (s.querySelector('.reply').textContent = msg);
}

// Show a save code to copy, or take one to paste
export function codeScreen({ code, onBack, onSubmit }) {
  const s = show(`<div class="menu"><p class="pre">Save code</p>
      <p class="note">${code ? 'Copy this and paste it into the game on another device (Load game, then Enter a save code).' : 'Paste a save code from another device.'}</p>
      <textarea spellcheck="false"></textarea>
      <div class="col">${code ? '<button class="primary" data-a="copy">Copy</button>' : '<button class="primary" data-a="go">Load</button>'}<button data-a="back">Back</button></div>
      <p class="reply"></p></div>`);
  const ta = s.querySelector('textarea'), reply = s.querySelector('.reply');
  ta.addEventListener('click', e => e.stopPropagation());
  if (code) { ta.value = code; ta.readOnly = true; }
  s.querySelector('[data-a=back]').onclick = e => { e.stopPropagation(); onBack(); };
  s.querySelector('[data-a=copy]')?.addEventListener('click', async e => {
    e.stopPropagation(); ta.select();
    try { await navigator.clipboard.writeText(code); reply.textContent = 'Copied.'; } catch { reply.textContent = 'Select the text and copy it.'; }
  });
  s.querySelector('[data-a=go]')?.addEventListener('click', e => { e.stopPropagation(); reply.textContent = onSubmit(ta.value) ?? ''; });
}

// one line at a time, tap to advance
export function cards(lines, done, cls = 'intro') {
  let i = 0;
  const s = show(`<div class="${cls}"><p class="line"></p><p class="tap">Tap to continue</p></div>`);
  const p = s.querySelector('.line');
  const step = () => {
    if (i >= lines.length) { s.onclick = null; done(); return; }
    const l = lines[i++];
    if (Array.isArray(l)) p.innerHTML = `<b>${l[0]}</b>${l[1]}`;
    else p.textContent = l;
    p.classList.remove('in'); void p.offsetWidth; p.classList.add('in');
  };
  // the tap that opened these cards is still bubbling; listen from the next tick
  s.onclick = null;
  setTimeout(() => (s.onclick = step), 0);
  step();
}

export function accuse({ onAnswer, onBack }) {
  const s = show(`<div class="accuse"><h2>${CONCLUSION.question}</h2><div class="btns"></div>
    <p class="reply"></p><button class="back">Back to the alley</button></div>`);
  const btns = s.querySelector('.btns');
  const reply = s.querySelector('.reply');
  for (const ans of CONCLUSION.answers) {
    const b = document.createElement('button');
    b.textContent = ans.a;
    b.onclick = () => {
      reply.textContent = ans.reply;
      if (ans.right) {
        btns.querySelectorAll('button').forEach(x => (x.disabled = true));
        b.classList.add('right');
        const go = document.createElement('button');
        go.className = 'primary'; go.textContent = 'Continue';
        go.onclick = () => onAnswer(true);
        reply.after(go);
        s.querySelector('.back').remove();
      } else {
        b.classList.add('wrong'); b.disabled = true;
        onAnswer(false);
      }
    };
    btns.appendChild(b);
  }
  s.querySelector('.back').onclick = onBack;
}

// End of chapter: the case rating, then on to what comes next.
export function endCard({ rating, onTitle, next }) {
  const stars = '★'.repeat(rating.stars) + '☆'.repeat(5 - rating.stars);
  const s = show(`<div class="title end">
      <p class="pre">Case closed</p>
      <h1>Chapter ${CHAPTER.number}</h1>
      <div class="rating"><div class="stars" aria-label="${rating.stars} of 5">${stars}</div>
        <table>${rating.rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('')}</table></div>
      <p class="sub">To be continued · ${CHAPTER.next}</p>
      <div class="btns">${next ? '<button class="primary" data-a="next"></button>' : ''}<button class="${next ? '' : 'primary'}" data-a="title">Title screen</button></div>
    </div>`);
  s.querySelector('[data-a=title]').onclick = onTitle;
  if (next) { const b = s.querySelector('[data-a=next]'); b.textContent = `On to ${next.label}`; b.onclick = next.go; }
}

// A broken memory: fragments of a scene shown out of order. Tap them in the order they happened; a wrong one
// shakes and Holmes complains. ev: { title, prompt, fragments (in the true order), wrong: [lines] }
export function reconstruct(ev, onDone, sound) {
  const order = ev.fragments.map((_, i) => i);
  for (let i = order.length - 1; i > 0; i--) {  // shuffle, but never leave it already solved
    const j = (Math.random() * (i + 1)) | 0; [order[i], order[j]] = [order[j], order[i]];
  }
  if (order.every((v, i) => v === i)) order.reverse();
  const s = show(`<div class="recon"><p class="pre">Reconstruction</p><h2></h2><p class="prompt"></p>
      <ol class="placed"></ol><div class="frags"></div><p class="reply"></p></div>`);
  s.querySelector('h2').textContent = ev.title;
  s.querySelector('.prompt').textContent = ev.prompt;
  const placed = s.querySelector('.placed'), frags = s.querySelector('.frags'), reply = s.querySelector('.reply');
  let next = 0, w = 0;
  for (const i of order) {
    const b = document.createElement('button');
    b.className = 'frag';
    b.textContent = ev.fragments[i];
    b.onclick = e => {
      e.stopPropagation();
      if (i !== next) {
        b.classList.remove('shake'); void b.offsetWidth; b.classList.add('shake');
        reply.textContent = ev.wrong[w++ % ev.wrong.length];
        sound?.wrong();
        return;
      }
      const li = document.createElement('li');
      li.textContent = ev.fragments[i];
      placed.appendChild(li);
      b.remove();
      reply.textContent = '';
      sound?.clue();
      if (++next === ev.fragments.length) {
        const go = document.createElement('button');
        go.className = 'primary'; go.textContent = 'Wake up';
        go.onclick = e2 => { e2.stopPropagation(); onDone(); };
        frags.appendChild(go);
      }
    };
    frags.appendChild(b);
  }
}
