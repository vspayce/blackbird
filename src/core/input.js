// Touch: a fixed stick in the bottom-left corner, drag anywhere else to look.
// Desktop: WASD / arrows to walk, drag with the mouse to look.
export class Input {
  constructor(el) {
    this.el = el;
    this.keys = new Set();
    this.stick = { id: null, ox: 0, oy: 0, x: 0, y: 0 };
    this.lookId = null; this.lx = 0; this.ly = 0;
    this.dx = 0; this.dy = 0;
    this.enabled = true;
    this.stickEl = document.getElementById('stick');
    this.knobEl = this.stickEl.querySelector('i');

    el.addEventListener('pointerdown', e => this.down(e));
    addEventListener('pointermove', e => this.move(e));
    addEventListener('pointerup', e => this.up(e));
    addEventListener('pointercancel', e => this.up(e));
    addEventListener('keydown', e => { this.keys.add(e.code); });
    addEventListener('keyup', e => { this.keys.delete(e.code); });
    addEventListener('blur', () => { this.keys.clear(); this.release(); });
  }

  down(e) {
    if (!this.enabled) return;
    const c = this.stickEl.getBoundingClientRect();  // zero-size element sitting at the stick's centre
    const near = this.stickEl.offsetParent !== null && Math.hypot(e.clientX - c.left, e.clientY - c.top) < 95;
    if (e.pointerType === 'touch' && near && this.stick.id === null) {
      Object.assign(this.stick, { id: e.pointerId, ox: c.left, oy: c.top, x: 0, y: 0 });
      this.stickEl.classList.add('on');
      this.move(e);
    } else if (this.lookId === null) {
      this.lookId = e.pointerId; this.lx = e.clientX; this.ly = e.clientY;
    }
  }

  move(e) {
    if (e.pointerId === this.stick.id) {
      const R = 56;
      let x = e.clientX - this.stick.ox, y = e.clientY - this.stick.oy;
      const l = Math.hypot(x, y);
      if (l > R) { x *= R / l; y *= R / l; }
      this.stick.x = x / R; this.stick.y = -y / R;
      this.knobEl.style.transform = `translate(${x}px, ${y}px)`;
    } else if (e.pointerId === this.lookId) {
      this.dx += e.clientX - this.lx; this.dy += e.clientY - this.ly;
      this.lx = e.clientX; this.ly = e.clientY;
    }
  }

  up(e) {
    if (e.pointerId === this.stick.id) this.releaseStick();
    if (e.pointerId === this.lookId) this.lookId = null;
  }

  releaseStick() {
    this.stick.id = null; this.stick.x = this.stick.y = 0;
    this.stickEl.classList.remove('on');
    this.knobEl.style.transform = '';
  }

  release() { this.releaseStick(); this.lookId = null; this.dx = this.dy = 0; }

  // {x: right, y: forward}, length ≤ 1
  moveVector() {
    if (!this.enabled) return { x: 0, y: 0 };
    let x = this.stick.x, y = this.stick.y;
    const k = this.keys;
    if (k.has('KeyW') || k.has('ArrowUp')) y += 1;
    if (k.has('KeyS') || k.has('ArrowDown')) y -= 1;
    if (k.has('KeyD') || k.has('ArrowRight')) x += 1;
    if (k.has('KeyA') || k.has('ArrowLeft')) x -= 1;
    const l = Math.hypot(x, y);
    if (l > 1) { x /= l; y /= l; }
    return { x, y };
  }

  takeLook() {
    const r = { x: this.dx, y: this.dy };
    this.dx = this.dy = 0;
    return r;
  }
}
