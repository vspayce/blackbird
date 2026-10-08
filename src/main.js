// THE BLACK BIRD: boot, the explore / close-up / talk / think loop.
import * as THREE from 'three';
import { Renderer } from './core/renderer.js';
import { Input } from './core/input.js';
import { audio } from './core/audio.js';
import { fullscreen } from './core/fullscreen.js';
import { Alley, loadSet } from './world/alley.js';
import { Hopkins, loadHopkins } from './world/hopkins.js';
import { createFigure, loadModels } from './game/figure.js';
import { CaseState } from './game/state.js';
import { HUD } from './ui/hud.js';
import { Dialogue } from './ui/dialogue.js';
import { Casebook, MindPalace } from './ui/palace.js';
import { titleScreen, cards, accuse, endCard, hideScreen } from './ui/screens.js';
import { CHAPTER, CLUES, PEOPLE, SPOTS, CLOSEUP, READS, CONCLUSION } from './cases/archer.js';

const HOLMES_LOOK = { model: 'holmes', coat: '#4a4740', trousers: '#2e2c2a', hat: 'deerstalker', hatColor: '#6b6250', cape: true, longCoat: true, hair: '#1d1712', height: 1.86 };
const WALK = 2.0;           // m/s at full stick: a brisk walk
const R = 0.3;              // body radius for collisions
const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _ray = new THREE.Ray();

// Which scene to play: ?scene=hopkins walks the Mark Hopkins Institute (a preview until its chapter is written);
// ?skip=1 drops straight into the alley without the intro. The title screen's Scenes button sets these.
const params = new URLSearchParams(location.search);
const SCENE = params.get('scene') === 'hopkins' ? 'hopkins' : 'alley';
const SKIP = params.has('skip');

const damp = (a, b, k, dt) => a + (b - a) * (1 - Math.exp(-k * dt));

class Game {
  constructor() {
    this.canvas = document.getElementById('gl');
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.05, 200);
    this.renderer = new Renderer(this.canvas);
    this.renderer.setup(this.scene, this.camera);
    this.input = new Input(this.canvas);
    this.hud = new HUD();
    this.dialogue = new Dialogue();
    this.book = new Casebook();
    this.palace = new MindPalace();
    this.state = new CaseState();
    if (SCENE === 'hopkins') {
      this.world = new Hopkins(this.scene);
      this.alley = null;
    } else {
      this.world = this.alley = new Alley(this.scene);
    }
    this.colliders = this.world.colliders;
    if (!this.alley) {  // the city below Nob Hill runs out to the far shore of the bay
      this.camera.near = 0.08; this.camera.far = 6000; this.camera.updateProjectionMatrix();
    }

    this.time = 0;
    this.focusOn = false; this.focus = 0; this.meter = 1;
    this.yaw = 0; this.pitch = 0.28; this.camDist = 3.3;
    this.mode = 'title';

    this.buildPeople();
    this.bindButtons();
    this.timer = new THREE.Timer();
    this.timer.connect?.(document);
    this.renderer.r.setAnimationLoop(() => this.frame());
    this.title();
    document.getElementById('loading').remove();
  }

  // --- people -------------------------------------------------------------
  buildPeople() {
    const shadowTex = new THREE.CanvasTexture((() => {
      const c = document.createElement('canvas'); c.width = c.height = 64;
      const g = c.getContext('2d'), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      r.addColorStop(0, 'rgba(0,0,0,0.6)'); r.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = r; g.fillRect(0, 0, 64, 64); return c;
    })());
    const shadowMat = new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false });
    const blob = fig => {
      const s = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9), shadowMat);
      s.rotation.x = -Math.PI / 2; s.position.y = 0.01;
      fig.object.add(s);
    };

    this.holmes = createFigure(HOLMES_LOOK);
    this.holmes.object.position.set(CHAPTER.start.x, 0, CHAPTER.start.z);
    blob(this.holmes);
    this.scene.add(this.holmes.object);

    this.people = {};
    if (!this.alley) {  // the Institute: just Watson at Holmes's side
      const f = createFigure(PEOPLE.watson.look);
      blob(f); this.scene.add(f.object);
      this.people.watson = { id: 'watson', fig: f, def: PEOPLE.watson, speed: 0 };
      return;
    }
    for (const [id, p] of Object.entries(PEOPLE)) {
      const f = createFigure(p.look);
      blob(f);
      this.scene.add(f.object);
      if (p.pos) {
        f.object.position.set(p.pos[0], 0, p.pos[1]);
        f.object.rotation.y = Math.atan2(p.face[0] - p.pos[0], p.face[1] - p.pos[1]);
      }
      else f.object.position.set(CHAPTER.start.x - 0.9, 0, CHAPTER.start.z + 1.2);
      this.people[id] = { id, fig: f, def: p, speed: 0 };
    }

    // Miles Archer, on his back, head toward the fence
    const archer = createFigure({ model: 'archer', coat: '#3d3a33', trousers: '#2b2925', hair: '#4a3324', longCoat: true, buttons: true, height: 1.8 });
    archer.object.rotation.x = -Math.PI / 2;
    archer.object.position.set(0.5, 0.18, -19.0);
    archer.lieBack();
    this.scene.add(archer.object);
    this.colliders.push(new THREE.Box3(new THREE.Vector3(0.15, 0, -20.9), new THREE.Vector3(0.85, 0.5, -18.9)));
    const blood = new THREE.Mesh(new THREE.CircleGeometry(0.35, 18), new THREE.MeshStandardMaterial({ color: '#2a0505', roughness: 0.15 }));
    blood.rotation.x = -Math.PI / 2; blood.position.set(0.35, 0.008, -20.5); blood.scale.set(1, 0.7, 1);
    this.scene.add(blood);
    const hat = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.11, 14), new THREE.MeshStandardMaterial({ color: '#28241f', roughness: 0.9 }));
    hat.position.set(-0.5, 0.06, -18.2); hat.rotation.set(0.2, 0, 0.3);
    this.scene.add(hat);
    this.archerHat = hat;
    // Holmes's pocket lamp, lit for the close-up
    this.pocketLamp = new THREE.PointLight('#ffd7a0', 0, 4, 1.5);
    this.pocketLamp.position.set(1.0, 1.0, -19.6);
    this.scene.add(this.pocketLamp);
  }

  // --- buttons and keys -----------------------------------------------------
  bindButtons() {
    const on = (id, f) => document.getElementById(id).addEventListener('click', e => { e.stopPropagation(); f(); });
    on('btn-focus', () => this.toggleFocus());
    on('btn-act', () => this.interact());
    on('btn-book', () => this.openBook());
    on('btn-palace', () => this.openPalace());
    on('btn-back', () => this.leaveCloseup());
    addEventListener('keydown', e => {
      if (e.repeat) return;
      if (e.code === 'KeyF') this.toggleFocus();
      else if (e.code === 'KeyE' || e.code === 'Space') { if (this.mode === 'explore') this.interact(); else if (this.mode === 'talk') this.dialogue.next(); }
      else if (e.code === 'KeyB' || e.code === 'Tab') { e.preventDefault(); this.openBook(); }
      else if (e.code === 'KeyM') this.openPalace();
      else if (e.code === 'Escape' && this.mode === 'closeup') this.leaveCloseup();
    });
  }

  setMode(m) {
    this.mode = m;
    this.input.enabled = m === 'explore';
    if (!this.input.enabled) this.input.release();
    const playing = ['explore', 'closeup'].includes(m);
    this.hud.show(playing || m === 'talk');
    document.body.dataset.mode = m;
    this.hud.back.classList.toggle('hidden', m !== 'closeup');
    if (m !== 'explore') this.hud.setAct(null);
    if (!playing) this.hud.hideSay();
    if (!playing && this.focusOn) this.toggleFocus();
  }

  // --- flow ---------------------------------------------------------------
  title() {
    this.setMode('title');
    if (SCENE === 'hopkins' || SKIP) {  // arrived from the Scenes menu: straight in
      this.state.load();
      return this.boot(false);
    }
    titleScreen({
      hasSave: CaseState.hasSave(),
      scenes: [
        ['Chapter I from the start', '?'],
        ['Burritt Alley, skip the intro', '?skip=1'],
        ['The Mark Hopkins Institute (preview)', '?scene=hopkins'],
      ],
      onNew: () => { this.state.reset(); this.state.save(); this.boot(true); },
      onContinue: () => { this.state.load(); this.boot(false); },
    });
  }

  boot(intro) {
    fullscreen.enter();
    audio.start();
    const go = () => { hideScreen(); this.begin(); };
    if (intro) { this.setMode('intro'); cards(CHAPTER.intro, go); } else go();
  }

  begin() {
    if (!this.alley) {
      const s = this.world.data.spawn;
      this.holmes.object.position.fromArray(s.pos);
      this.holmes.object.rotation.y = s.yaw;
      this.people.watson.fig.object.position.set(s.pos[0] - 1.1, s.pos[1], s.pos[2] - 0.7);
      this.yaw = s.yaw - Math.PI; this.pitch = -0.12;  // looking up at the house over the wall
      this.camDistNow = this.camDist;
      this.setMode('explore');
      setTimeout(() => this.hud.say('There it is, Watson: the Hopkins house. Four years an art school, and still the grandest folly on Nob Hill.'), 600);
      return;
    }
    this.holmes.object.position.set(CHAPTER.start.x, 0, CHAPTER.start.z);
    this.holmes.object.rotation.y = Math.PI;
    this.people.watson.fig.object.position.set(CHAPTER.start.x - 0.9, 0, CHAPTER.start.z + 1.2);
    this.yaw = 0; this.pitch = 0.28;
    this.setMode('explore');
    if (!this.state.talked.length) setTimeout(() => this.hud.say('Two in the morning, and Polhaus already here. Let us see what the fog has left us, Watson.'), 600);
  }

  gain(id) {
    const c = CLUES[id];
    if (this.state.addClue(id)) {
      audio.clue();
      this.hud.toast(c.kind === 'testimony' ? 'testimony' : 'clue', c.title);
    }
    if (c.kind !== 'testimony') this.hud.say(c.text);
  }

  toggleFocus() {
    if (!['explore', 'closeup'].includes(this.mode) && !this.focusOn) return;
    if (!this.focusOn && this.meter < 0.15) { this.hud.say('My eyes need a moment\'s rest.'); return; }
    this.focusOn = !this.focusOn;
    audio.focus(this.focusOn);
  }

  // nearest thing worth doing from where Holmes stands
  candidate() {
    const p = this.holmes.object.position;
    if (!this.alley) {
      let best = null, bd = Infinity;
      for (const s of this.world.interact) {
        const d = Math.hypot(s.pos[0] - p.x, s.pos[2] - p.z);
        if (Math.abs(s.pos[1] - p.y) < 3 && d < s.r && d < bd) { best = { inter: s }; bd = d; }
      }
      return best;
    }
    let best = null, bestScore = Infinity;
    for (const s of SPOTS) {
      const found = s.clue && this.state.has(s.clue);
      if (s.focus && !found && this.focus < 0.3) continue;
      const d = Math.hypot(s.pos[0] - p.x, s.pos[2] - p.z);
      if (d < s.r && d / s.r < bestScore) { best = { spot: s }; bestScore = d / s.r; }
    }
    for (const id of ['polhaus', 'kelly']) {
      if (!this.people[id]) continue;
      const o = this.people[id].fig.object.position;
      const d = Math.hypot(o.x - p.x, o.z - p.z);
      if (d < 2 && d / 2 < bestScore) { best = { person: id }; bestScore = d / 2; }
    }
    if (!best) {
      const o = this.people.watson.fig.object.position;
      if (Math.hypot(o.x - p.x, o.z - p.z) < 2.2) best = { person: 'watson' };
    }
    return best;
  }

  interact(target = this.candidate()) {
    if (!target || this.mode !== 'explore') return;
    if (target.inter) return this.useHopkins(target.inter);
    if (target.person) return this.talk(target.person);
    const s = target.spot;
    if (s.closeup) return this.enterCloseup();
    if (s.clue) return this.gain(s.clue);
    if (s.say) this.hud.say(s.say);
  }

  // the Institute preview: the tower stair moves Holmes up and down; the rest are remarks for now
  useHopkins(s) {
    const d = this.world.data.tower;
    const lines = {
      archive: 'The Art Association\'s minute books, catalogues of every exhibition since \'71. If anyone in this city has written about a jewelled bird, it will be in here.',
      curator: 'The curator keeps a tidy desk and an untidy correspondence: dealers in Paris, Vienna, Constantinople.',
      view: 'The whole city, Watson, laid out in gaslight. Somewhere down there a woman in blue gloves is lying to someone.',
      telescope: 'Hopkins built this for the view. I find it serves equally well for watching the doors of the Palace Hotel.',
    };
    if (s.to) {
      const to = s.to === 'tower_room' ? d.top : d.foot;
      this.holmes.object.position.fromArray(to);
      this.people.watson.fig.object.position.set(to[0] + 0.8, to[1], to[2] + 0.6);
      this.camDistNow = 1.5;
      this.hud.say(s.to === 'tower_room' ? 'A hundred and twenty steps. Hopkins never climbed them; he died before the house was finished.' : 'Down again.');
      return;
    }
    this.hud.say(lines[s.id] ?? s.label);
  }

  talk(id) {
    this.setMode('talk');
    const fig = this.people[id].fig.object;
    const h = this.holmes.object.position;
    fig.rotation.y = Math.atan2(h.x - fig.position.x, h.z - fig.position.z);
    this.holmes.object.rotation.y = Math.atan2(fig.position.x - h.x, fig.position.z - h.z);
    // over Holmes's shoulder, onto whoever he is talking to
    this.yaw = this.holmes.object.rotation.y + Math.PI + 0.45;
    this.pitch = 0.12;
    this.hud.hideSay();
    this.people[id].fig.setTalking(true);
    this.dialogue.open(id, {
      state: this.state,
      onGive: c => this.gain(c),
      onCall: right => { right ? audio.deduce() : audio.wrong(); this.hud.toast(right ? 'right' : 'wrong', right ? 'You read them right' : 'You misjudged them'); },
      onClose: () => { this.people[id].fig.setTalking(false); this.setMode('explore'); },
    });
  }

  enterCloseup() {
    this.setMode('closeup');
    this.holmes.object.visible = false;
    this.camFrom = this.camera.position.clone();
    this.lookFrom = this.camLook?.clone() ?? new THREE.Vector3();
    this.camT = 0;
    if (!this.state.has('coat')) this.hud.say('Now then, Archer. Tell me how it happened.');
  }

  leaveCloseup() {
    if (this.mode !== 'closeup') return;
    this.holmes.object.visible = true;
    this.setMode('explore');
  }

  openBook() {
    if (!['explore', 'closeup'].includes(this.mode)) return;
    const back = this.mode;
    this.setMode('book');
    this.book.open(this.state, () => this.setMode(back));
  }

  openPalace() {
    if (!['explore', 'closeup'].includes(this.mode)) return;
    const back = this.mode;
    this.setMode('palace');
    if (back === 'closeup') this.holmes.object.visible = true;
    this.palace.open({
      state: this.state,
      sound: audio,
      onDeduce: d => { this.state.addDeduction(d); audio.deduce(); },
      onMiss: () => { this.state.misses++; this.state.save(); audio.wrong(); },
      onClose: () => this.setMode('explore'),
      onConclude: () => this.conclude(),
    });
  }

  conclude() {
    this.setMode('accuse');
    accuse({
      onAnswer: right => {
        if (!right) { this.state.wrongAccusations++; this.state.save(); audio.wrong(); return; }
        audio.deduce();
        cards(CONCLUSION.epilogue, () => {
          this.state.solved = true; this.state.save();
          endCard({ rating: this.state.rating(), onTitle: () => this.title() });
        }, 'intro epilogue');
      },
      onBack: () => { hideScreen(); this.setMode('explore'); },
    });
  }

  // --- simulation -----------------------------------------------------------
  collide(pos) {
    for (const b of this.colliders) {
      if (b.max.y < pos.y + 0.2 || b.min.y > pos.y + 1.8) continue;  // only what stands on this floor
      const cx = Math.max(b.min.x, Math.min(pos.x, b.max.x));
      const cz = Math.max(b.min.z, Math.min(pos.z, b.max.z));
      const dx = pos.x - cx, dz = pos.z - cz, d = Math.hypot(dx, dz);
      if (d > 0 && d < R) { pos.x = cx + dx / d * R; pos.z = cz + dz / d * R; }
      else if (d === 0) {
        // inside: leave by the nearest face
        const opts = [[b.min.x - R - pos.x, 0], [b.max.x + R - pos.x, 0], [0, b.min.z - R - pos.z], [0, b.max.z + R - pos.z]];
        opts.sort((a, c) => Math.abs(a[0] + a[1]) - Math.abs(c[0] + c[1]));
        pos.x += opts[0][0]; pos.z += opts[0][1];
      }
    }
    for (const id of ['polhaus', 'kelly']) {
      if (!this.people[id]) continue;
      const o = this.people[id].fig.object.position;
      const dx = pos.x - o.x, dz = pos.z - o.z, d = Math.hypot(dx, dz);
      if (d > 0 && d < 0.6) { pos.x = o.x + dx / d * 0.6; pos.z = o.z + dz / d * 0.6; }
    }
  }

  // walk up and down slopes and steps where the world has them
  followGround(pos, dt) {
    if (!this.world.groundAt) return;
    const g = this.world.groundAt(pos.x, pos.z, pos.y);
    pos.y += (g - pos.y) * Math.min(1, dt * 14);
  }

  updateHolmes(dt) {
    const look = this.input.takeLook();
    this.yaw -= look.x * 0.006;
    this.pitch = Math.max(-0.15, Math.min(0.95, this.pitch + look.y * 0.004));

    const m = this.input.moveVector();
    const fx = -Math.sin(this.yaw), fz = -Math.cos(this.yaw);
    const rx = Math.cos(this.yaw), rz = -Math.sin(this.yaw);
    const vx = fx * m.y + rx * m.x, vz = fz * m.y + rz * m.x;
    const sp = Math.hypot(vx, vz) * WALK * (1 - 0.45 * this.focus);
    const o = this.holmes.object;
    if (sp > 0.05) {
      const k = sp / Math.hypot(vx, vz);
      o.position.x += vx * k * dt; o.position.z += vz * k * dt;
      this.collide(o.position);
      this.followGround(o.position, dt);
      const target = Math.atan2(vx, vz);
      let d = target - o.rotation.y;
      d = Math.atan2(Math.sin(d), Math.cos(d));
      o.rotation.y += d * Math.min(1, dt * 10);
      // the camera drifts in behind when walking forward
      if (m.y > 0.3 && Math.abs(m.x) < 0.5) {
        let dy = (o.rotation.y + Math.PI) - this.yaw;
        dy = Math.atan2(Math.sin(dy), Math.cos(dy));
        this.yaw += dy * Math.min(1, dt * 0.8);
      }
    }
    this.holmesSpeed = damp(this.holmesSpeed ?? 0, sp, 10, dt);
  }

  updateWatson(dt, t) {
    const w = this.people.watson, o = w.fig.object, h = this.holmes.object;
    const ry = h.rotation.y;
    // at Holmes's left shoulder, half a pace back, out of the camera's way
    const tx = h.position.x + Math.sin(ry) * -0.4 + Math.cos(ry) * 1.0;
    const tz = h.position.z + Math.cos(ry) * -0.4 - Math.sin(ry) * 1.0;
    const dx = tx - o.position.x, dz = tz - o.position.z, d = Math.hypot(dx, dz);
    let sp = 0;
    if (this.mode === 'explore' && d > 0.45) {
      sp = Math.min(WALK * 1.05, d * 1.6);
      o.position.x += dx / d * sp * dt; o.position.z += dz / d * sp * dt;
      this.collide(o.position);
      this.followGround(o.position, dt);
      const a = Math.atan2(dx, dz);
      o.rotation.y += Math.atan2(Math.sin(a - o.rotation.y), Math.cos(a - o.rotation.y)) * Math.min(1, dt * 8);
    } else if (this.mode !== 'talk') {
      const a = Math.atan2(h.position.x - o.position.x, h.position.z - o.position.z);
      o.rotation.y += Math.atan2(Math.sin(a - o.rotation.y), Math.cos(a - o.rotation.y)) * Math.min(1, dt * 3);
    }
    w.speed = damp(w.speed, sp, 8, dt);
    w.fig.animate(dt, w.speed, t);
  }

  updateCamera(dt) {
    const h = this.holmes.object.position;
    const cam = this.camera;
    if (this.mode === 'title' || this.mode === 'intro') {
      // slow drift down Bush Street toward the alley
      const a = this.time * 0.05;
      cam.position.set(Math.sin(a) * 6, 2.2 + Math.sin(a * 0.7) * 0.4, 17 + Math.cos(a) * 2);
      this.camLook = new THREE.Vector3(0, 1.6, -6);
      cam.lookAt(this.camLook);
      return;
    }
    if (this.mode === 'closeup') {
      this.camT = Math.min(1, this.camT + dt * 1.4);
      const k = this.camT * this.camT * (3 - 2 * this.camT);
      _v.fromArray(CLOSEUP.cam); _w.fromArray(CLOSEUP.look);
      // a little parallax sway so it feels hand-held
      _v.x += Math.sin(this.time * 0.4) * 0.03; _v.y += Math.sin(this.time * 0.55) * 0.02;
      cam.position.lerpVectors(this.camFrom, _v, k);
      this.camLook = this.lookFrom.clone().lerp(_w, k);
      cam.lookAt(this.camLook);
      return;
    }
    const target = _w.set(h.x, h.y + 1.55, h.z);
    const cp = Math.cos(this.pitch);
    const dir = _v.set(Math.sin(this.yaw) * cp, Math.sin(this.pitch), Math.cos(this.yaw) * cp);
    let dist = this.camDist;
    _ray.set(target, dir);
    const hit = new THREE.Vector3();
    for (const b of this.colliders) {
      if (_ray.intersectBox(b, hit)) dist = Math.min(dist, Math.max(0.6, hit.distanceTo(target) - 0.25));
    }
    if (target.y + dir.y * dist < h.y + 0.25) dist = (h.y + 0.25 - target.y) / dir.y;
    this.camDistNow = damp(this.camDistNow ?? dist, dist, dist < (this.camDistNow ?? dist) ? 30 : 4, dt);
    cam.position.copy(target).addScaledVector(dir, this.camDistNow);
    this.camLook = target.clone();
    cam.lookAt(target);
  }

  project(x, y, z) {
    _v.set(x, y, z).project(this.camera);
    if (_v.z > 1 || Math.abs(_v.x) > 1.1 || Math.abs(_v.y) > 1.1) return null;
    return [(_v.x + 1) / 2 * innerWidth, (1 - _v.y) / 2 * innerHeight];
  }

  updateLabels() {
    const hud = this.hud;
    hud.begin();
    const p = this.holmes.object.position;
    const f = this.focus;
    if (this.mode === 'explore' && !this.alley) {
      for (const s of this.world.interact) {
        if (Math.abs(s.pos[1] - p.y) > 3 || Math.hypot(s.pos[0] - p.x, s.pos[2] - p.z) > 7) continue;
        const sc = this.project(...s.pos);
        if (sc) hud.label('in:' + s.id, sc[0], sc[1], s.label, 'mark', () => {
          if (Math.hypot(s.pos[0] - this.holmes.object.position.x, s.pos[2] - this.holmes.object.position.z) < s.r * 1.3) this.useHopkins(s);
          else this.hud.say('Closer.');
        });
      }
    } else if (this.mode === 'explore') {
      for (const s of SPOTS) {
        const found = s.clue && this.state.has(s.clue);
        const d = Math.hypot(s.pos[0] - p.x, s.pos[2] - p.z);
        if (s.focus && !found) {
          if (f < 0.3 || d > 9) continue;
        } else if (found || d > 5 || s.closeup) continue;
        const sc = this.project(...s.pos);
        if (!sc) continue;
        hud.label('spot:' + s.id, sc[0], sc[1], s.label, s.focus ? 'mark focus' : 'mark', () => {
          const dd = Math.hypot(s.pos[0] - this.holmes.object.position.x, s.pos[2] - this.holmes.object.position.z);
          if (dd < s.r * 1.3) this.interact({ spot: s });
          else this.hud.say('Too far to make it out. Closer.');
        });
      }
      if (f > 0.3) {
        const reads = [
          ...['polhaus', 'kelly', 'watson'].map(id => [id, this.people[id].fig.object.position, 2.05]),
          ['hat', this.archerHat.position, 0.25],
        ];
        for (const [id, o, hgt] of reads) {
          if (Math.hypot(o.x - p.x, o.z - p.z) > 6) continue;
          const sc = this.project(o.x, o.y + hgt, o.z);
          if (!sc) continue;
          READS[id].forEach((txt, i) => {
            hud.label(`read:${id}:${i}`, sc[0] + 18, sc[1] - 34 + i * 20, txt, 'read');
            if (f > 0.9) this.state.addRead(`${id}:${i}`);
          });
        }
      }
    } else if (this.mode === 'closeup' && this.camT > 0.85) {
      for (const s of CLOSEUP.spots) {
        const found = this.state.has(s.clue);
        if (s.focus && !found && f < 0.3) continue;
        const sc = this.project(...s.pos);
        if (!sc) continue;
        hud.label('cu:' + s.clue, sc[0], sc[1], found ? CLUES[s.clue].title : s.label, 'mark' + (found ? ' done' : '') + (s.focus ? ' focus' : ''), () => this.gain(s.clue));
      }
    }
    hud.end();
  }

  frame() {
    this.timer.update();
    const dt = Math.min(0.05, this.timer.getDelta());
    this.time += dt;

    // Focus: drains while on, refills while off; the world slows around Holmes
    if (this.focusOn) {
      this.meter = Math.max(0, this.meter - dt * 0.1);
      if (this.meter === 0) { this.focusOn = false; audio.focus(false); this.hud.say('Enough. The mind must rest.'); }
    } else this.meter = Math.min(1, this.meter + dt * 0.08);
    this.focus = damp(this.focus, this.focusOn ? 1 : 0, 5, dt);
    const wdt = dt * (1 - 0.7 * this.focus);
    this.camera.fov = 55 - 7 * this.focus;
    this.camera.updateProjectionMatrix();

    if (this.mode === 'explore') this.updateHolmes(dt);
    this.holmes.animate(dt, this.mode === 'explore' ? this.holmesSpeed ?? 0 : 0, this.time);
    this.updateWatson(wdt, this.time);
    for (const id of ['polhaus', 'kelly']) this.people[id]?.fig.animate(wdt, 0, this.time);
    this.world.update(wdt, this.time, this.focus, this.camera, this.holmes.object.position);
    if (this.pocketLamp) this.pocketLamp.intensity = damp(this.pocketLamp.intensity, this.mode === 'closeup' ? 3.5 : 0, 4, dt);
    this.updateCamera(dt);

    if (this.mode === 'explore') {
      const c = this.candidate();
      this.hud.setAct(c ? (c.inter ? c.inter.label : c.person ? 'Talk to ' + PEOPLE[c.person].name : c.spot.label) : null);
      this.hud.setObjective(this.alley ? this.state.objective() : this.world.roomAt(this.holmes.object.position));
    }
    this.hud.setFocus(this.focusOn, this.meter);
    this.updateLabels();
    this.hud.update(dt);
    audio.update(dt);
    this.renderer.render(this.time, this.focus);
  }
}

const assets = SCENE === 'hopkins'
  ? [loadModels(['holmes', 'watson']), loadHopkins()]
  : [loadModels(['holmes', 'watson', 'polhaus', 'kelly', 'archer']), loadSet()];
Promise.all(assets).then(() => { window.game = new Game(); });
