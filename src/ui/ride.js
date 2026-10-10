// The cab ride between scenes: a hansom cab in silhouette through gaslit fog, with where we are going. It is
// also the loading screen: shown at once on page load, and kept up until the scene is ready (longer when we
// arrived by cab from another chapter, so the ride is seen).
const RIDE_KEY = 'blackbird.ride';

// mark the next page load as a cab ride (call before navigating to another chapter)
export function rideNext() {
  try { sessionStorage.setItem(RIDE_KEY, String(Date.now())); } catch { /* storage blocked: no matter */ }
}

function arrivedByCab() {
  try {
    const t = Number(sessionStorage.getItem(RIDE_KEY));
    sessionStorage.removeItem(RIDE_KEY);
    return t && Date.now() - t < 60000;
  } catch { return false; }
}

// rooftops for the parallax layers: a strip of buildings `w` wide, drawn twice so it can scroll seamlessly
function skyline(w, h0, rnd, lit) {
  let x = 0, d = `M0 900 `;
  const wins = [];
  while (x < w) {
    const bw = 60 + rnd() * 120, bh = h0 + rnd() * 160;
    const top = 720 - bh;
    d += `L${x} ${top} `;
    if (rnd() < 0.4) d += `L${x + bw * 0.5} ${top - 30 - rnd() * 30} `;   // a gable
    else if (rnd() < 0.3) d += `L${x + 8} ${top} L${x + 8} ${top - 26} L${x + 22} ${top - 26} L${x + 22} ${top} `;  // chimney
    d += `L${x + bw} ${top} `;
    if (lit) for (let k = 0; k < 4; k++) if (rnd() < 0.3) wins.push(`<rect x="${x + 10 + rnd() * (bw - 30)}" y="${top + 20 + rnd() * (bh - 80)}" width="12" height="18"/>`);
    x += bw;
  }
  d += `L${w} 900 Z`;
  return { d, wins: wins.join('') };
}

function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

const leg = (x, y, cls) => `<g class="leg ${cls}" style="transform-origin:${x}px ${y}px"><path d="M${x - 9} ${y} L${x - 6} ${y + 92} L${x - 2} ${y + 150} L${x - 10} ${y + 196} L${x + 12} ${y + 196} L${x + 9} ${y + 150} L${x + 10} ${y + 92} L${x + 11} ${y} Z"/></g>`;

function cabSVG() {
  const far = skyline(1800, 120, rng(3), false), mid = skyline(1800, 60, rng(9), true);
  const lamps = Array.from({ length: 5 }, (_, i) => {
    const x = 120 + i * 400;
    return `<g transform="translate(${x} 0)"><rect x="-5" y="470" width="10" height="250"/><rect x="-14" y="700" width="28" height="20"/>
      <path d="M-20 430 L20 430 L14 470 L-14 470 Z" class="glass"/><path d="M-24 430 L0 410 L24 430 Z"/>
      <circle cx="0" cy="452" r="70" class="halo"/></g>`;
  }).join('');
  const spokes = Array.from({ length: 12 }, (_, i) => `<line x1="0" y1="0" x2="${(Math.cos(i * Math.PI / 6) * 92).toFixed(1)}" y2="${(Math.sin(i * Math.PI / 6) * 92).toFixed(1)}"/>`).join('');
  return `<svg viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
  <defs>
    <linearGradient id="rsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#080b10"/><stop offset="0.7" stop-color="#1c2430"/><stop offset="1" stop-color="#2a3240"/></linearGradient>
    <linearGradient id="rstreet" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1a1d22"/><stop offset="1" stop-color="#07080a"/></linearGradient>
    <radialGradient id="rglow"><stop offset="0" stop-color="#ffcf8a" stop-opacity="0.55"/><stop offset="1" stop-color="#ffcf8a" stop-opacity="0"/></radialGradient>
    <linearGradient id="rfog" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#8fa0b4" stop-opacity="0"/><stop offset="0.5" stop-color="#8fa0b4" stop-opacity="0.13"/><stop offset="1" stop-color="#8fa0b4" stop-opacity="0"/></linearGradient>
  </defs>
  <rect width="1600" height="900" fill="url(#rsky)"/>
  <g class="layer far"><path d="${far.d}"/><path d="${far.d}" transform="translate(1800 0)"/></g>
  <g class="layer mid"><path d="${mid.d}"/><g class="wins">${mid.wins}</g><g transform="translate(1800 0)"><path d="${mid.d}"/><g class="wins">${mid.wins}</g></g></g>
  <rect y="718" width="1600" height="182" fill="url(#rstreet)"/>
  <g class="layer lamps">${lamps}<g transform="translate(2000 0)">${lamps}</g></g>
  <g class="fogband f1"><rect x="-400" y="520" width="2400" height="150" fill="url(#rfog)"/></g>
  <g class="cab">
    <g class="bob">
      <!-- shafts and harness -->
      <path d="M880 600 L1040 572 M880 585 L1040 560" class="line"/>
      <!-- the cab: a cabin with a curved front, the driver's perch behind and above -->
      <path d="M640 612 L640 470 Q640 432 680 432 L820 432 Q842 432 852 452 L888 560 L888 612 Z"/>
      <rect x="672" y="458" width="92" height="66" class="window"/>
      <path d="M600 438 L660 438 L660 452 L600 452 Z"/>
      <path d="M588 338 Q590 318 610 316 L640 316 Q656 318 654 340 L656 438 L594 438 Z"/>
      <rect x="600" y="276" width="44" height="40"/><rect x="590" y="312" width="64" height="6"/>
      <path d="M650 352 Q760 250 1000 330" class="whip"/>
      <circle cx="880" cy="478" r="11" class="glass"/><circle cx="880" cy="478" r="60" class="halo"/>
    </g>
    <!-- the wheel -->
    <g transform="translate(760 622)"><circle r="98" class="rim"/><circle r="12"/><g class="spin">${spokes}</g></g>
    <!-- the horse -->
    <g class="horse">
      ${leg(1010, 520, 'h1')}${leg(1040, 520, 'h2')}${leg(1190, 515, 'f1')}${leg(1215, 515, 'f2')}
      <path d="M985 470 Q1000 440 1060 438 L1180 436 Q1230 438 1240 470 Q1246 530 1200 548 L1040 552 Q985 550 980 512 Z"/>
      <path d="M1200 450 Q1230 380 1262 350 L1300 332 Q1322 330 1330 352 L1336 372 Q1332 384 1318 382 L1290 384 Q1268 420 1240 470 Z"/>
      <path d="M1290 336 L1298 312 L1306 334 Z"/>
      <path d="M988 480 Q950 500 948 560 Q970 520 990 508 Z" class="tail"/>
      <path d="M1236 440 Q1210 470 1190 470" class="line"/>
    </g>
  </g>
  <g class="fogband f2"><rect x="-400" y="740" width="2400" height="160" fill="url(#rfog)"/></g>
</svg>`;
}

// how much of the scene has come down the wire (bytes); shown once it is plainly taking a while
export function rideProgress(loaded, total) {
  const el = document.querySelector('#loading .progress');
  if (!el || !total) return;
  el.classList.add('on');
  el.querySelector('em').style.width = `${Math.min(100, loaded / total * 100).toFixed(1)}%`;
  const mb = n => (n / 1048576).toFixed(1);
  el.querySelector('small').textContent = loaded >= total ? 'Arriving…' : `${mb(loaded)} of ${mb(total)} MB`;
}

// Show the ride. dest: { to, place, time }. Returns finish(): call when the scene is ready; it resolves once
// the ride has been seen long enough and has faded out.
export function showRide(dest) {
  const el = document.getElementById('loading');
  const cab = arrivedByCab();
  el.classList.add('ride');
  el.innerHTML = `${cabSVG()}<div class="dest"><small>${cab ? 'By cab' : 'San Francisco, 1895'}</small>
      <b></b><span class="place"></span><i></i></div>
      <div class="progress"><span><em></em></span><small></small></div>`;
  el.querySelector('b').textContent = dest?.to ?? '';
  el.querySelector('.place').textContent = dest?.place ?? '';
  el.querySelector('i').textContent = dest?.time ?? '';
  const start = performance.now(), min = cab ? 4200 : 1400;
  return () => new Promise(resolve => {
    const wait = Math.max(0, min - (performance.now() - start));
    setTimeout(() => {
      el.classList.add('out');
      setTimeout(() => { el.remove(); resolve(); }, 700);
    }, wait);
  });
}
