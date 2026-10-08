// Game controllers (Xbox, PlayStation, MFi) through the browser's Gamepad API,
// with the "standard" button layout. Sticks drive Holmes and the camera;
// in menus the d-pad or left stick moves a highlight between whatever
// buttons are on screen (spatial navigation), so every screen works without
// knowing about controllers.
const DEAD = 0.18;

// standard mapping
export const BTN = { A: 0, B: 1, X: 2, Y: 3, LB: 4, RB: 5, LT: 6, RT: 7, VIEW: 8, MENU: 9, L3: 10, R3: 11, UP: 12, DOWN: 13, LEFT: 14, RIGHT: 15 };

const dz = v => (Math.abs(v) < DEAD ? 0 : (v - Math.sign(v) * DEAD) / (1 - DEAD));

export class Pad {
  constructor() {
    this.prev = [];
    this.down = [];
    this.lx = this.ly = this.rx = this.ry = 0;
    this.connected = false;
    this.sel = null;          // the highlighted button in menus
    this.lastPoint = null;    // where it was, to pick a neighbour after the screen re-renders
    this.navHold = 0;         // stick/d-pad auto-repeat
    this.navDir = null;
    addEventListener('gamepadconnected', () => this.wake());
    // any touch or mouse use hands the screen back to pointer controls
    addEventListener('pointerdown', () => this.sleep(), true);
  }

  wake() { this.connected = true; document.body.classList.add('pad'); }
  sleep() { document.body.classList.remove('pad'); this.clearSel(); }

  poll() {
    const gp = [...(navigator.getGamepads?.() ?? [])].find(g => g && g.connected);
    this.prev = this.down;
    if (!gp) { this.down = []; this.lx = this.ly = this.rx = this.ry = 0; return; }
    this.down = gp.buttons.map(b => b.pressed || b.value > 0.5);
    [this.lx, this.ly, this.rx, this.ry] = [0, 1, 2, 3].map(i => dz(gp.axes[i] ?? 0));
    this.justWoke = false;
    if (this.down.some(Boolean) || Math.hypot(this.lx, this.ly, this.rx, this.ry) > 0) {
      // the first touch of the controller only switches to controller mode (and shows the highlight)
      if (!document.body.classList.contains('pad')) { this.wake(); this.justWoke = true; this.prev = this.down; }
    }
  }

  pressed(b) { return !!this.down[b] && !this.prev[b]; }

  // one step of menu direction per press, repeating while held
  navStep(dt) {
    const d = this.down;
    let dir = d[BTN.UP] ? 'up' : d[BTN.DOWN] ? 'down' : d[BTN.LEFT] ? 'left' : d[BTN.RIGHT] ? 'right' : null;
    if (!dir && Math.hypot(this.lx, this.ly) > 0.6) dir = Math.abs(this.lx) > Math.abs(this.ly) ? (this.lx > 0 ? 'right' : 'left') : (this.ly > 0 ? 'down' : 'up');
    if (dir !== this.navDir) { this.navDir = dir; this.navHold = 0.4; return dir; }
    if (!dir) return null;
    this.navHold -= dt;
    if (this.navHold <= 0) { this.navHold = 0.14; return dir; }
    return null;
  }

  // --- menu highlight ---------------------------------------------------------------------------
  targets(roots) {
    const out = [];
    for (const r of roots) {
      if (!r) continue;
      for (const el of r.querySelectorAll('button, a[href]')) {
        if (el.disabled || el.offsetParent === null) continue;
        const b = el.getBoundingClientRect();
        if (b.width < 2 || b.height < 2 || b.bottom < 0 || b.top > innerHeight || b.right < 0 || b.left > innerWidth) {
          // allow things scrolled out of view inside a scrolling panel (the notebook, the Mind Palace board)
          if (!el.closest('.body, .board')) continue;
        }
        out.push(el);
      }
    }
    return out;
  }

  centre(el) { const b = el.getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }

  setSel(el) {
    if (this.sel === el) return;
    this.sel?.classList.remove('pad-sel');
    this.sel = el;
    if (el) {
      el.classList.add('pad-sel');
      el.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
      this.lastPoint = this.centre(el);
    }
  }

  clearSel() { this.sel?.classList.remove('pad-sel'); this.sel = null; }

  // keep a highlight on screen: the same element if it survived a re-render, else the one nearest where it was
  ensureSel(roots, prefer) {
    const list = this.targets(roots);
    if (!list.length) { this.clearSel(); return null; }
    if (this.sel && this.sel.isConnected && list.includes(this.sel)) return this.sel;
    let pick = prefer && list.find(el => el.matches(prefer));
    if (!pick && this.lastPoint) {
      const [px, py] = this.lastPoint;
      pick = list.reduce((a, el) => { const [x, y] = this.centre(el); const d = Math.hypot(x - px, y - py); return d < a[1] ? [el, d] : a; }, [null, Infinity])[0];
    }
    this.setSel(pick ?? list[0]);
    return this.sel;
  }

  move(roots, dir) {
    const list = this.targets(roots);
    if (!this.sel) return this.ensureSel(roots);
    const [sx, sy] = this.centre(this.sel);
    const [ux, uy] = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[dir];
    let best = null, bestScore = Infinity;
    for (const el of list) {
      if (el === this.sel) continue;
      const [x, y] = this.centre(el);
      const along = (x - sx) * ux + (y - sy) * uy;
      if (along <= 4) continue;
      const across = Math.abs((x - sx) * uy - (y - sy) * ux);
      const score = along + across * 2.5;
      if (score < bestScore) { best = el; bestScore = score; }
    }
    if (best) this.setSel(best);
    return this.sel;
  }
}
