// Full-screen cards: title, chapter intro, the accusation and the ending.
import { CHAPTER, CONCLUSION } from '../cases/archer.js';

const el = () => document.getElementById('screen');

function show(html) {
  const s = el();
  s.innerHTML = html;
  s.classList.add('show');
  return s;
}
export function hideScreen() { el().classList.remove('show'); }

export function titleScreen({ hasSave, onNew, onContinue }) {
  const s = show(`<div class="title">
      <p class="pre">A Sherlock Holmes Mystery</p>
      <h1>The Black Bird</h1>
      <p class="sub">${CHAPTER.title}</p>
      <div class="btns">
        ${hasSave ? '<button class="primary" data-a="continue">Continue</button>' : ''}
        <button class="${hasSave ? '' : 'primary'}" data-a="new">${hasSave ? 'Start over' : 'Begin'}</button>
      </div>
      <p class="credit">After Dashiell Hammett's <i>The Maltese Falcon</i> (1930) and Arthur Conan Doyle.</p>
    </div>`);
  s.querySelector('[data-a=new]').onclick = onNew;
  s.querySelector('[data-a=continue]')?.addEventListener('click', onContinue);
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
export function endCard({ rating, onTitle }) {
  const stars = '★'.repeat(rating.stars) + '☆'.repeat(5 - rating.stars);
  const s = show(`<div class="title end">
      <p class="pre">Case closed</p>
      <h1>Chapter I</h1>
      <div class="rating"><div class="stars" aria-label="${rating.stars} of 5">${stars}</div>
        <table>${rating.rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('')}</table></div>
      <p class="sub">To be continued · Chapter II · The Levantine</p>
      <div class="btns"><button class="primary">Title screen</button></div>
    </div>`);
  s.querySelector('button').onclick = onTitle;
}
