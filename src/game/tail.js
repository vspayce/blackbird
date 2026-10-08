// Tailing, both ways (Chapter V). Driven by a chapter's TAIL:
//   who: the person; follow: metres he keeps behind Holmes while shadowing him;
//   after: the event that turns the tables (Holmes now follows him); until: the event when the tail ends;
//   path: [[x, z], ...] he walks; pauses: { index: seconds } where he stops and looks back;
//   waitFor: { index: 'cablecar' } wait there until the cable car is clear; speed;
//   sight: he spots you inside this distance while looking back unless you are in cover;
//   close: he spots you inside this distance at any time; lose: farther than this for loseTime and he is gone.
// Fails send you back to the last checkpoint (the last pause he reached), with Holmes a way behind.
const damp = (a, b, k, dt) => a + (b - a) * (1 - Math.exp(-k * dt));

export class Tail {
  constructor(game, def) {
    this.g = game; this.d = def;
    this.who = game.people[def.who];
    this.i = 0; this.pause = 0; this.lostT = 0; this.suspicion = 0; this.checkpoint = 0;
    this.started = false;  // the lead phase starts him at the head of his path the first time it runs
  }

  get phase() {
    const ev = this.g.state.events;
    if (ev.includes(this.d.until)) return 'done';
    return ev.includes(this.d.after) ? 'lead' : 'shadow';
  }

  // put him at a path point and Holmes behind him
  reset(i) {
    this.i = i; this.pause = 0; this.lostT = 0; this.suspicion = 0; this.checkpoint = i;
    const [x, z] = this.d.path[i];
    this.who?.fig.object.position.set(x, 0, z);
  }

  placeHolmesBehind() {
    // walk back along the path from the checkpoint, about 16 m
    const P = this.d.path, h = this.g.holmes.object.position;
    let i = this.checkpoint, [x, z] = P[i], left = 16;
    while (i > 0 && left > 0) {
      const [px, pz] = P[i - 1], seg = Math.hypot(x - px, z - pz);
      if (seg >= left) { x += (px - x) * left / seg; z += (pz - z) * left / seg; left = 0; } else { x = px; z = pz; left -= seg; i--; }
    }
    if (left > 0) z += left;  // before the start: further south
    h.set(x, 0, z);
    this.g.people.watson.fig.object.position.set(x - 0.9, 0, z + 0.7);
    this.g.yaw = 0; this.g.camDistNow = 3;
  }

  fail(lines) {
    this.g.hud.say(lines[(Math.random() * lines.length) | 0]);
    this.reset(this.checkpoint);
    this.placeHolmesBehind();
  }

  update(dt) {
    const phase = this.phase, hud = this.g.hud;
    if (!this.who || phase === 'done') { hud.setTail(null); return; }
    const o = this.who.fig.object, h = this.g.holmes.object.position;
    const dist = Math.hypot(o.position.x - h.x, o.position.z - h.z);
    let speed = 0;

    if (phase === 'shadow') {
      // keep about `follow` metres behind Holmes (south of him), on the far sidewalk; stop if he comes back
      hud.setTail(null);
      const tx = this.d.shadowX, tz = Math.max(h.z + this.d.follow, Math.min(o.position.z, h.z + 30));
      const dx = tx - o.position.x, dz = tz - o.position.z, d = Math.hypot(dx, dz);
      if (dist > 11 && d > 1.2) {
        speed = Math.min(1.6, d);
        o.position.x += dx / d * speed * dt; o.position.z += dz / d * speed * dt;
        o.rotation.y = Math.atan2(dx, dz);
      } else if (dist <= 11) {
        o.rotation.y = damp(o.rotation.y, Math.PI / 2 * Math.sign(-o.position.x || 1), 3, dt);  // studies a shop window
      }
      this.who.speed = damp(this.who.speed, speed, 6, dt);
      return;
    }

    // --- Holmes follows him ---
    if (!this.started) { this.started = true; this.reset(0); }
    const P = this.d.path;
    let looking = false;
    if (this.pause > 0) {
      this.pause -= dt;
      looking = this.pauseLen - this.pause > 0.7;  // he takes a moment to turn: time to step behind something
      o.rotation.y = Math.atan2(h.x - o.position.x, h.z - o.position.z);  // looks back down the street
    } else if (this.i < P.length - 1) {
      const wait = this.d.waitFor?.[this.i] === 'cablecar' && this.g.world.car?.visible && Math.abs(this.g.world.car.position.x) < 14;
      if (!wait) {
        const [nx, nz] = P[this.i + 1];
        const dx = nx - o.position.x, dz = nz - o.position.z, d = Math.hypot(dx, dz);
        speed = this.d.speed;
        if (d < speed * dt) {
          o.position.set(nx, 0, nz);
          this.i++;
          if (this.d.pauses[this.i]) { this.pause = this.pauseLen = this.d.pauses[this.i]; this.checkpoint = this.i; }
          if (this.i === P.length - 1) { hud.setTail(null); this.who.speed = 0; this.g.runEvent(this.d.until); return; }
        } else {
          o.position.x += dx / d * speed * dt; o.position.z += dz / d * speed * dt;
          o.rotation.y = Math.atan2(dx, dz);
        }
      }
    }
    this.who.speed = damp(this.who.speed, speed, 6, dt);

    // being seen
    const cover = this.g.world.inCover(h.x, h.z, o.position.x, o.position.z);
    const seen = dist < this.d.close || (looking && dist < this.d.sight && !cover);
    this.suspicion = seen ? Math.min(1, this.suspicion + dt * (dist < this.d.close ? 1.5 : 0.9)) : Math.max(0, this.suspicion - dt * 0.25);
    if (this.suspicion >= 1) return this.fail(this.d.spotted);
    // losing him
    this.lostT = dist > this.d.lose ? this.lostT + dt : 0;
    if (this.lostT > this.d.loseTime) return this.fail(this.d.lost);

    hud.setTail({
      dist,
      state: looking ? (cover ? 'He looks back. You are hidden' : 'He is looking back!') : dist > this.d.lose * 0.8 ? 'Losing him in the fog' : 'Following',
      warn: looking && !cover || dist > this.d.lose * 0.8,
      suspicion: this.suspicion,
    });
  }
}
