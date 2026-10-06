// Procedural canvas textures. Everything in the slice is drawn here so the
// scene needs no downloads; real baked assets replace these later (DESIGN.md).
import * as THREE from 'three';

function canvas(w, h = w) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}

// small deterministic RNG so textures look the same every load
function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function tex(c, repeatX = 1, repeatY = 1, srgb = true) {
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeatX, repeatY);
  t.anisotropy = 4;
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export function cobbles(rx, ry) {
  const [c, g] = canvas(512);
  const r = rng(7);
  g.fillStyle = '#1b1712'; g.fillRect(0, 0, 512, 512);
  const rows = 16, h = 512 / rows;
  for (let y = 0; y < rows; y++) {
    let x = (y % 2) * -14;
    while (x < 512) {
      const w = 22 + r() * 18;
      const l = 38 + r() * 26, tint = r() * 10;
      g.fillStyle = `rgb(${l + tint},${l + tint * 0.6},${l - 4})`;
      g.beginPath();
      g.roundRect(x + 2, y * h + 2, w - 4, h - 4, 7);
      g.fill();
      // wet highlight on the crown of each stone
      g.fillStyle = 'rgba(190,200,215,0.10)';
      g.beginPath(); g.ellipse(x + w * 0.45, y * h + h * 0.38, w * 0.25, h * 0.16, 0, 0, Math.PI * 2); g.fill();
      x += w;
    }
  }
  return tex(c, rx, ry);
}

export function bricks(rx, ry, base = [96, 44, 32]) {
  const [c, g] = canvas(512);
  const r = rng(11);
  g.fillStyle = '#3b3631'; g.fillRect(0, 0, 512, 512);
  const bh = 512 / 24, bw = 512 / 8;
  for (let y = 0; y < 24; y++) {
    for (let x = -1; x < 9; x++) {
      const ox = (y % 2) * bw * 0.5;
      const k = 0.7 + r() * 0.45;
      g.fillStyle = `rgb(${base[0] * k | 0},${base[1] * k | 0},${base[2] * k | 0})`;
      g.fillRect(x * bw + ox + 2, y * bh + 2, bw - 4, bh - 3);
    }
  }
  // soot running down from the top
  const grad = g.createLinearGradient(0, 0, 0, 512);
  grad.addColorStop(0, 'rgba(10,8,6,0.45)'); grad.addColorStop(0.5, 'rgba(10,8,6,0.0)');
  g.fillStyle = grad; g.fillRect(0, 0, 512, 512);
  return tex(c, rx, ry);
}

export function planks(rx, ry, base = [86, 70, 52]) {
  const [c, g] = canvas(256);
  const r = rng(23);
  for (let x = 0; x < 8; x++) {
    const k = 0.75 + r() * 0.4;
    g.fillStyle = `rgb(${base[0] * k | 0},${base[1] * k | 0},${base[2] * k | 0})`;
    g.fillRect(x * 32, 0, 32, 256);
    g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(x * 32, 0, 2, 256);
    for (let i = 0; i < 6; i++) {
      g.fillStyle = `rgba(0,0,0,${0.08 + r() * 0.1})`;
      g.fillRect(x * 32 + 4 + r() * 24, 0, 1, 256);
    }
  }
  return tex(c, rx, ry);
}

export function plaster(rx, ry, base = [120, 110, 92]) {
  const [c, g] = canvas(256);
  const r = rng(5);
  g.fillStyle = `rgb(${base.join(',')})`; g.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 900; i++) {
    g.fillStyle = `rgba(${r() < 0.5 ? '0,0,0' : '255,255,255'},${r() * 0.06})`;
    g.fillRect(r() * 256, r() * 256, 2 + r() * 10, 2 + r() * 10);
  }
  return tex(c, rx, ry);
}

// Billboard at the dead end of the alley
export function poster() {
  const [c, g] = canvas(512, 256);
  g.fillStyle = '#d8c79c'; g.fillRect(0, 0, 512, 256);
  g.fillStyle = '#7a1f17'; g.fillRect(14, 14, 484, 228);
  g.fillStyle = '#e9dcb8'; g.fillRect(24, 24, 464, 208);
  g.fillStyle = '#2a1d14'; g.textAlign = 'center';
  g.font = 'bold 26px Georgia'; g.fillText("DR. PETTIBONE'S", 256, 70);
  g.font = 'bold 50px Georgia'; g.fillStyle = '#7a1f17'; g.fillText('CELEBRATED TONIC', 256, 128);
  g.font = 'italic 22px Georgia'; g.fillStyle = '#2a1d14';
  g.fillText('Cures Every Ailment Known to Science', 256, 170);
  g.font = '18px Georgia'; g.fillText('Sold at all Druggists · 50¢', 256, 205);
  // weathering
  const r = rng(3);
  for (let i = 0; i < 260; i++) {
    g.fillStyle = `rgba(40,30,20,${r() * 0.18})`;
    g.fillRect(r() * 512, r() * 256, 1 + r() * 18, 1 + r() * 4);
  }
  return tex(c);
}

// soft round blob: fog puffs, lamp halos, blob shadows
export function glow(inner = 'rgba(255,255,255,1)', outer = 'rgba(255,255,255,0)') {
  const [c, g] = canvas(128);
  const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grad.addColorStop(0, inner); grad.addColorStop(1, outer);
  g.fillStyle = grad; g.fillRect(0, 0, 128, 128);
  return tex(c);
}

// a narrow pointed heel and sole, used for the prints Focus reveals
export function heelPrint() {
  const [c, g] = canvas(64, 128);
  g.fillStyle = '#fff';
  g.beginPath(); g.ellipse(32, 38, 15, 30, 0, 0, Math.PI * 2); g.fill();
  g.beginPath(); g.ellipse(32, 108, 7, 10, 0, 0, Math.PI * 2); g.fill();
  return tex(c);
}
