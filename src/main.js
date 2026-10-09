// THE BLACK BIRD: boot, the explore / close-up / talk / think loop.
import * as THREE from 'three';
import { Renderer } from './core/renderer.js';
import { Input } from './core/input.js';
import { audio } from './core/audio.js';
import { fullscreen } from './core/fullscreen.js';
import { Pad, BTN } from './core/gamepad.js';
import { Alley, loadSet } from './world/alley.js';
import { Hopkins, loadHopkins } from './world/hopkins.js';
import { Kearny, loadKearny } from './world/kearny.js';
import { Room, loadRoom } from './world/room.js';
import { Tail } from './game/tail.js';
import { createFigure, loadModels, makePistol } from './game/figure.js';
import { CaseState } from './game/state.js';
import { HUD } from './ui/hud.js';
import { Dialogue } from './ui/dialogue.js';
import { Casebook, MindPalace } from './ui/palace.js';
import { titleScreen, cards, accuse, endCard, hideScreen, reconstruct, pauseMenu, slotPicker, codeScreen, profileSheet, fightPlanner } from './ui/screens.js';
import { CHAPTER, CLUES, PEOPLE, SPOTS, CLOSEUP, READS, CONCLUSION, EVENTS, TAIL, PORTRAITS, FIGHTS, chapterNumber } from './cases/current.js';
import { saves } from './game/saves.js';
import { showRide, rideNext } from './ui/ride.js';
import { NEXT_PLAYABLE, chapterNames } from './cases/current.js';

const HOLMES_LOOK = { model: 'holmes', coat: '#4a4740', trousers: '#2e2c2a', hat: 'deerstalker', hatColor: '#6b6250', cape: true, longCoat: true, hair: '#1d1712', height: 1.86 };
const WALK = 2.0;           // m/s at full stick: a brisk walk
const R = 0.3;              // body radius for collisions
const _v = new THREE.Vector3(), _w = new THREE.Vector3(), _ray = new THREE.Ray();

// What to play. ?chapter=4 picks the chapter (src/cases/current.js), which names its world. ?scene=hopkins walks
// the Institute freely with no case (a preview); ?skip=1 starts straight in, without the title or intro.
// The title screen's Scenes button sets these.
const params = new URLSearchParams(location.search);
const PREVIEW = params.get('scene') === 'hopkins';
const WORLD = PREVIEW ? 'hopkins' : CHAPTER.world;
const SKIP = params.has('skip');
const LOAD = params.get('load');  // a save to resume on arrival: a slot id, or 'pending' (a code, in sessionStorage)

const damp = (a, b, k, dt) => a + (b - a) * (1 - Math.exp(-k * dt));

class Game {
  constructor() {
    this.canvas = document.getElementById('gl');
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.05, 200);
    this.renderer = new Renderer(this.canvas);
    this.renderer.setup(this.scene, this.camera);
    this.input = new Input(this.canvas);
    this.pad = new Pad();
    this.input.pad = this.pad;
    this.hud = new HUD();
    this.dialogue = new Dialogue();
    this.book = new Casebook();
    this.palace = new MindPalace();
    this.state = new CaseState();
    if (WORLD === 'hopkins') {
      this.world = new Hopkins(this.scene);
      this.alley = null;
      // the city below Nob Hill runs out to the far shore of the bay
      this.camera.near = 0.08; this.camera.far = 6000; this.camera.updateProjectionMatrix();
    } else if (WORLD === 'palace') {
      this.world = new Room(this.scene);
      this.alley = null;
    } else if (WORLD === 'kearny') {
      this.world = new Kearny(this.scene);
      this.alley = null;
      this.camera.far = 400; this.camera.updateProjectionMatrix();
    } else {
      this.world = this.alley = new Alley(this.scene);
    }
    this.colliders = this.world.colliders;
    // the case's places to look: worldId spots take their position, reach and label from the world
    this.spots = PREVIEW ? [] : SPOTS.map(s => {
      const w = s.worldId && this.world.interact?.find(i => i.id === s.worldId);
      if (w) return { pos: w.pos, r: w.r, label: w.label, ...s };
      const p = s.place && this.world.data?.places?.[s.place];  // a named place in the world (a shop door)
      if (p) return { pos: [p[0], p[1] + 1.4, p[2]], r: 2.2, ...s };
      return s;
    });
    // the world's own doings: in the preview all of them, in a chapter only travel (the tower stair)
    this.inters = (this.world.interact ?? []).filter(i => PREVIEW || i.to);

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
    blob(this.holmes);
    this.scene.add(this.holmes.object);

    this.people = {};
    for (const [id, p] of Object.entries(PEOPLE)) {
      if (PREVIEW && id !== 'watson') continue;  // the preview: just Watson at Holmes's side
      const f = createFigure(p.look);
      blob(f);
      this.scene.add(f.object);
      if (p.pos) {  // [x, z] on flat ground, or [x, y, z]
        const [x, y, z] = p.pos.length === 3 ? p.pos : [p.pos[0], 0, p.pos[1]];
        f.object.position.set(x, y, z);
        f.object.rotation.y = Math.atan2(p.face[0] - x, p.face[1] - z);
      }
      this.people[id] = { id, fig: f, def: p, speed: 0 };
    }
    this.anchors = {};  // things (not people) that Focus reads can sit on
    if (CHAPTER.id === 'archer' && !PREVIEW) this.buildArcherScene();
    this.tail = TAIL && !PREVIEW ? new Tail(this, TAIL) : null;
  }

  // Chapter I's body in the alley (the one piece of set dressing that belongs to the case, not the world)
  buildArcherScene() {
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
    this.anchors.hat = { position: hat.position, height: 0.25 };
    // Holmes's pocket lamp, lit for the close-up
    this.pocketLamp = new THREE.PointLight('#ffd7a0', 0, 4, 1.5);
    this.pocketLamp.position.set(1.0, 1.0, -19.6);
    this.scene.add(this.pocketLamp);
  }

  // people still in the scene (some leave after a story event), other than Watson
  present() {
    return Object.values(this.people).filter(p => p.id !== 'watson' && !(p.def.leaves && this.state.events.includes(p.def.leaves)));
  }

  syncPresence() {
    for (const p of Object.values(this.people)) p.fig.object.visible = p.id === 'watson' || this.present().includes(p);
  }

  // --- buttons and keys -----------------------------------------------------
  bindButtons() {
    const on = (id, f) => document.getElementById(id).addEventListener('click', e => { e.stopPropagation(); f(); });
    on('btn-focus', () => this.toggleFocus());
    on('btn-act', () => this.interact());
    on('btn-book', () => this.openBook());
    on('btn-palace', () => this.openPalace());
    on('btn-back', () => this.leaveCloseup());
    on('btn-menu', () => this.openMenu());
    addEventListener('keydown', e => {
      if (e.repeat) return;
      if (e.code === 'KeyF') this.toggleFocus();
      else if (e.code === 'KeyE' || e.code === 'Space') { if (this.mode === 'explore') this.interact(); else if (this.mode === 'talk') this.dialogue.next(); }
      else if (e.code === 'KeyB' || e.code === 'Tab') { e.preventDefault(); this.openBook(); }
      else if (e.code === 'KeyM') this.openPalace();
      else if (e.code === 'Escape' && this.mode === 'closeup') this.leaveCloseup();
      else if (e.code === 'Escape' && this.mode === 'explore') this.openMenu();
    });
  }

  setMode(m) {
    this.mode = m;
    this.input.enabled = m === 'explore';
    if (!this.input.enabled) this.input.release();
    const playing = ['explore', 'closeup'].includes(m);
    this.hud.show(playing || m === 'talk' || m === 'portrait');
    document.body.dataset.mode = m;
    this.hud.back.classList.toggle('hidden', m !== 'closeup');
    if (m !== 'explore') this.hud.setAct(null);
    if (!playing) this.hud.hideSay();
    if (!playing && this.focusOn) this.toggleFocus();
  }

  // --- flow ---------------------------------------------------------------
  title() {
    this.setMode('title');
    if (LOAD) {  // arrived to resume a save
      const data = LOAD === 'pending' ? JSON.parse(sessionStorage.getItem('blackbird.pending') ?? 'null') : saves.read(LOAD);
      history.replaceState(null, '', location.pathname + (chapterNumber > 1 ? `?chapter=${chapterNumber}` : ''));
      if (data) return this.applySave(data);
    }
    if (PREVIEW || SKIP) {  // arrived from the Scenes menu: straight in
      this.state.load();
      return this.boot(false);
    }
    const latest = saves.latest();
    titleScreen({
      latest,
      onContinue: () => this.applySave(latest),
      onLoad: () => this.loadMenu(() => this.title()),
      scenes: [
        ['Chapter I · Burritt Alley', './'],
        ['Chapter I, skip the intro', '?skip=1'],
        ['Chapter IV · The Fat Man', '?chapter=4'],
        ['Chapter V · The Gunsel', '?chapter=5'],
        ['The Mark Hopkins Institute (free roam)', '?scene=hopkins'],
      ],
      onNew: () => { this.state.reset(); this.state.save(); this.boot(true); },
    });
  }

  // --- saving -------------------------------------------------------------------------------
  snapshot() {
    const h = this.holmes.object, w = this.people.watson.fig.object;
    // mid-tail, a save resumes at the start of the tail rather than somewhere Wilmer can't be
    const midTail = this.tail && this.tail.phase === 'lead';
    return {
      v: 1, chapter: chapterNumber, title: CHAPTER.title, objective: this.state.objective(), savedAt: Date.now(),
      state: this.state.toJSON(),
      at: midTail || PREVIEW ? null : { pos: h.position.toArray(), rot: h.rotation.y, watson: w.position.toArray(), yaw: this.yaw },
    };
  }

  autosave() {
    if (PREVIEW || !['explore', 'closeup', 'talk', 'book', 'palace'].includes(this.mode)) return;
    saves.write('auto', this.snapshot());
    this.lastAutosave = this.time;
  }

  // Resume a save. Another chapter's save reloads the page into that chapter, which picks it up from there.
  applySave(data, slotId = null) {
    if (data.chapter !== chapterNumber) {
      let id = slotId;
      if (!id || !saves.read(id)) { sessionStorage.setItem('blackbird.pending', JSON.stringify(data)); id = 'pending'; }
      rideNext();
      location.href = `./?chapter=${data.chapter}&load=${id}`;
      return;
    }
    this.state.reset();
    this.state.fromJSON(data.state);
    this.state.save();
    this.resumeAt = data.at;
    if (this.tail) this.tail.started = false;  // a tail in progress starts again from its beginning
    hideScreen();
    this.boot(false);
  }

  openMenu() {
    if (!['explore', 'closeup'].includes(this.mode)) return;
    const back = this.mode;
    this.setMode('menu');
    const resume = () => { hideScreen(); this.setMode(back); };
    const menu = () => pauseMenu({
      objective: this.state.objective(),
      onResume: resume,
      onSave: () => {
        const say = slotPicker({
          mode: 'save', slots: saves.list(), onBack: menu,
          onPick: id => { saves.write(id, this.snapshot()); say(`Saved to slot ${id}.`); setTimeout(menu, 700); },
        });
      },
      onLoad: () => this.loadMenu(menu),
      onCode: () => codeScreen({ code: saves.encode(this.snapshot()), onBack: menu }),
      onTitle: () => { this.autosave(); location.href = './' + (chapterNumber > 1 ? `?chapter=${chapterNumber}` : ''); },
    });
    menu();
  }

  loadMenu(back) {
    const prev = this.mode;
    this.setMode('menu');
    const pick = () => slotPicker({
      mode: 'load', slots: saves.list(), onBack: () => { this.setMode(prev); back(); },
      onPick: id => this.applySave(saves.read(id), id),
      onEnterCode: () => codeScreen({
        onBack: pick,
        onSubmit: text => { const d = saves.decode(text); if (!d) return 'That is not a save code.'; this.applySave(d); },
      }),
    });
    pick();
  }

  boot(intro) {
    fullscreen.enter();
    audio.start();
    const go = () => { hideScreen(); this.begin(); };
    if (intro) { this.setMode('intro'); cards(CHAPTER.intro, go); } else go();
  }

  begin() {
    this.syncPresence();
    if (FIGHTS?.fight && this.state.events.includes('fight')) this.showPockets();
    const h = this.holmes.object, w = this.people.watson.fig.object;
    if (this.resumeAt && !PREVIEW) {  // a loaded save: exactly where he stood
      const r = this.resumeAt; this.resumeAt = null;
      h.position.fromArray(r.pos); h.rotation.y = r.rot; w.position.fromArray(r.watson);
      this.yaw = r.yaw; this.pitch = 0.2; this.camDistNow = this.camDist;
      this.setMode('explore');
      this.hud.say('Where were we, Watson?');
      return;
    }
    const woke = Object.entries(EVENTS ?? {}).filter(([k, e]) => e.wake && this.state.events.includes(k)).pop();
    if (woke && !PREVIEW) {  // continuing after a story event: pick up where it left Holmes
      h.position.fromArray(woke[1].wake); w.position.set(woke[1].wake[0] + 0.9, woke[1].wake[1], woke[1].wake[2] + 0.6);
      this.yaw = 0; this.pitch = 0.2;
    } else if (WORLD === 'hopkins' || CHAPTER.start === 'spawn') {  // the world's own starting place
      const s = this.world.data.spawn;
      h.position.fromArray(s.pos);
      h.rotation.y = s.yaw;
      w.position.set(s.pos[0] - 1.1, s.pos[1], s.pos[2] - 0.7);
      this.yaw = s.yaw - Math.PI; this.pitch = WORLD === 'hopkins' ? -0.12 : 0.2;  // (up at the house over the wall)
    } else {
      h.position.set(CHAPTER.start.x, 0, CHAPTER.start.z);
      h.rotation.y = Math.PI;
      w.position.set(CHAPTER.start.x - 0.9, 0, CHAPTER.start.z + 1.2);
      this.yaw = 0; this.pitch = 0.28;
    }
    this.camDistNow = this.camDist;
    this.setMode('explore');
    const line = PREVIEW ? 'There it is, Watson: the Hopkins house. Four years an art school, and still the grandest folly on Nob Hill.'
      : !this.state.talked.length && !woke ? CHAPTER.opening : null;
    if (line) setTimeout(() => { if (this.mode === 'explore') this.hud.say(line); }, 600);
  }

  // A story event from a conversation (Chapter IV: the drugged whisky). 'reconstruct': the scene breaks off into
  // cards, the player puts the fragments of memory in order, then Holmes wakes somewhere else.
  runEvent(name) {
    const ev = EVENTS[name];
    if (!ev) return;
    if (ev.type === 'fight') return this.runFight(name, FIGHTS[name]);
    this.setMode('intro');
    if (ev.type === 'cards') {  // a short scene told in cards, then Holmes is somewhere (wake) with a clue (gives)
      cards(ev.lines, () => {
        hideScreen();
        this.state.addEvent(name);
        this.syncPresence();
        if (ev.wake) {
          this.holmes.object.position.fromArray(ev.wake);
          this.people.watson.fig.object.position.set(ev.wake[0] - 0.9, ev.wake[1], ev.wake[2] + 0.7);
        }
        this.setMode('explore');
        if (ev.gives) this.gain(ev.gives);
      });
      return;
    }
    const wake = () => {
      this.state.addEvent(name);
      this.syncPresence();
      const h = this.holmes.object, w = this.people.watson.fig.object;
      h.position.fromArray(ev.wake); w.position.set(ev.wake[0] + 0.9, ev.wake[1], ev.wake[2] + 0.6);
      this.yaw = 0; this.pitch = 0.2; this.camDistNow = 1.5;
      cards(ev.after ?? [], () => {
        hideScreen();
        this.setMode('explore');
        if (ev.gives) this.gain(ev.gives);
      }, 'intro epilogue');
    };
    cards(ev.before ?? [], () => reconstruct(ev, wake, audio));
  }

  gain(id) {
    const c = CLUES[id];
    if (this.state.addClue(id)) {
      setTimeout(() => this.autosave(), 0);
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
  // a spot can be used now: its event has happened, and (in Focus, if hidden) it can be seen
  spotLive(s) {
    if (s.after && !this.state.events.includes(s.after)) return false;
    const found = s.clue && this.state.has(s.clue);
    return !(s.focus && !found && this.focus < 0.3);
  }

  // on Holmes's floor: within reach of a marker at height y
  sameFloor(y, p = this.holmes.object.position) { return Math.abs(y - p.y) < 3; }

  candidate() {
    const p = this.holmes.object.position;
    let best = null, bestScore = Infinity;
    for (const s of this.inters) {
      const d = Math.hypot(s.pos[0] - p.x, s.pos[2] - p.z);
      if (this.sameFloor(s.pos[1], p) && d < s.r && d / s.r < bestScore) { best = { inter: s }; bestScore = d / s.r; }
    }
    for (const s of this.spots) {
      if (!this.spotLive(s) || !this.sameFloor(s.pos[1], p)) continue;
      const d = Math.hypot(s.pos[0] - p.x, s.pos[2] - p.z);
      if (d < s.r && d / s.r < bestScore) { best = { spot: s }; bestScore = d / s.r; }
    }
    for (const person of this.present()) {
      const o = person.fig.object.position;
      if (Math.abs(o.y - p.y) > 1.5 || person.def.notalk) continue;
      const d = Math.hypot(o.x - p.x, o.z - p.z);
      if (d < 2 && d / 2 < bestScore) { best = { person: person.id }; bestScore = d / 2; }
    }
    if (!best && !PREVIEW) {
      const o = this.people.watson.fig.object.position;
      if (Math.hypot(o.x - p.x, o.z - p.z) < 2.2 && Math.abs(o.y - p.y) < 1.5) best = { person: 'watson' };
    }
    return best;
  }

  interact(target = this.candidate()) {
    if (!target || this.mode !== 'explore') return;
    if (target.inter) return this.useHopkins(target.inter);
    if (target.person) return this.talk(target.person);
    const s = target.spot;
    if (s.closeup) return this.enterCloseup();
    if (s.needs && !s.needs.every(n => this.state.has(n))) return this.hud.say(s.early ?? 'Nothing here that I can use yet.');
    if (s.event && !this.state.events.includes(s.event)) return this.runEvent(s.event);
    if (s.clues) return this.gain(s.clues.find(c => !this.state.has(c)) ?? s.clues[s.clues.length - 1]);  // one at a time
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
      prints: 'Engravings for the students to copy. Valletta, the harbour, the Grand Master\'s palace. Someone has been looking at Malta.',
      studio: 'Still warm. The model left in a hurry, and in a lady\'s glove, by the look of that mark on the velvet.',
      bedroom: 'Mrs. Hopkins never slept here. She built it, furnished it, and went back East. The Association shows it to visitors on Sundays.',
      casts: 'Plaster gods, Watson. The students draw them for a year before they are allowed a living model.',
      fountain: 'Granite, and dry since the Association took the house. Water costs money on Nob Hill.',
      flood: 'Bronze, the whole length of the block. Flood made his money in silver and wanted everyone to know it.',
    };
    if (s.to) {
      if (s.to === 'tower_room') this.towerFrom = s.id;  // come back down to the floor you climbed from
      const foot = this.towerFrom === 'tower2' ? [d.foot[0], 6, d.foot[2]] : d.foot;
      const to = s.to === 'tower_room' ? d.top : foot;
      const waits = s.to === 'tower_room' && this.watsonWaits();
      this.holmes.object.position.fromArray(to);
      if (!waits) this.people.watson.fig.object.position.set(to[0] + 0.8, to[1], to[2] + 0.6);
      this.camDistNow = 1.5;
      this.hud.say(waits ? CHAPTER.watsonWaits.line
        : s.to === 'tower_room' ? 'A hundred and twenty steps. Hopkins never climbed them; he died before the house was finished.' : 'Down again.');
      return;
    }
    this.hud.say(lines[s.id] ?? s.label);
  }

  // A fixed camera for the portrait and the fight: placed relative to a person (fwd: toward their front)
  fixCamera(o, fwd, side, up, lookUp) {
    const f = new THREE.Vector3(Math.sin(o.rotation.y), 0, Math.cos(o.rotation.y));
    const r = new THREE.Vector3(f.z, 0, -f.x);
    this.fixedCam = {
      pos: o.position.clone().addScaledVector(f, fwd).addScaledVector(r, side).add(new THREE.Vector3(0, up, 0)),
      look: o.position.clone().add(new THREE.Vector3(0, lookUp, 0)),
      t: 0, from: this.camera.position.clone(), lookFrom: this.camLook?.clone() ?? o.position.clone(),
    };
  }

  // The character portrait (Chapter II): meeting someone freezes the moment in a close-up. Markers on them give
  // readings; once all are found, Holmes's reading is completed line by line; then the conversation begins.
  enterPortrait(id, def) {
    const person = this.people[id].fig.object, h = this.holmes.object.position;
    person.rotation.y = Math.atan2(h.x - person.position.x, h.z - person.position.z);
    this.setMode('portrait');
    this.fixCamera(person, 1.25, 0.28, 1.58, 1.32);
    this.portrait = { id, def, person };
    this.hud.say('Hold. Look at him, Watson, before he says a word.');
  }

  portraitFound(spot) {
    this.gain(spot.clue);
    const P = this.portrait;
    if (!P.def.spots.every(s => this.state.has(s.clue)) || P.sheet) return;
    P.sheet = true;
    setTimeout(() => profileSheet({
      who: PEOPLE[P.id].name, lines: P.def.lines,
      onWrong: () => { this.state.misses++; this.state.save(); audio.wrong(); },
      onDone: () => {
        hideScreen();
        this.state.addEvent(P.def.event);
        this.gain(P.def.gives);
        this.portrait = null; this.fixedCam = null;
        this.talk(P.id);
      },
    }), 900);
  }

  // Fight prediction (Chapter II): the pistol comes out, time stops, the player plans three moves
  runFight(name, def) {
    const foe = this.people[def.who], h = this.holmes.object;
    this.setMode('fight');
    foe.fig.object.rotation.y = Math.atan2(h.position.x - foe.fig.object.position.x, h.position.z - foe.fig.object.position.z);
    foe.fig.pose('Aim');
    this.pistol = makePistol();
    foe.fig.hold(this.pistol);
    this.holmes.pose('HandsUp');
    h.rotation.y = Math.atan2(foe.fig.object.position.x - h.position.x, foe.fig.object.position.z - h.position.z);
    // a side-on two-shot from the room's side: both men, and the gun between them
    const c = foe.fig.object.position, mid = h.position.clone().lerp(c, 0.5);
    const dir = c.clone().sub(h.position).setY(0).normalize(), perp = new THREE.Vector3(dir.z, 0, -dir.x);
    if (perp.dot(mid.clone().negate()) < 0) perp.negate();  // toward the middle of the room, away from the walls
    this.fixedCam = {
      pos: mid.clone().addScaledVector(perp, 3.0).addScaledVector(dir, -0.6).add(new THREE.Vector3(0, 1.55, 0)),
      look: mid.clone().add(new THREE.Vector3(0, 1.3, 0)),
      t: 0, from: this.camera.position.clone(), lookFrom: this.camLook?.clone() ?? mid.clone(),
    };
    fightPlanner({
      title: def.title, prompt: def.prompt, moves: def.moves,
      check: plan => {
        const at = plan.findIndex((m, i) => m !== def.plan[i]);
        return at < 0 ? { ok: true } : { ok: false, at, why: def.why[plan[at]] ?? 'No.' };
      },
      onFail: () => { this.state.misses++; this.state.save(); audio.wrong(); },
      onSuccess: () => {
        audio.deduce();
        // for real: Holmes goes in under the gun
        const from = h.position.clone(), to = foe.fig.object.position.clone().lerp(h.position, 0.55);
        let k = 0;
        const lunge = () => { k = Math.min(1, k + 0.08); h.position.lerpVectors(from, to, k * k * (3 - 2 * k)); if (k < 1) requestAnimationFrame(lunge); };
        this.holmes.pose(null); lunge();
        this.setMode('intro');
        cards(def.success, () => {
          hideScreen();
          foe.fig.pose(null); foe.fig.hold(null);
          this.pistol.position.set(-1.6, 0.74, 0.2); this.pistol.rotation.set(Math.PI / 2, 0, 0.6);  // on the table now
          this.scene.add(this.pistol);
          this.showPockets();
          this.state.addEvent(name);
          this.fixedCam = null;
          this.setMode('explore');
          this.hud.say('Now then, Mr. Cairo. Your pockets, onto the table.');
          this.autosave();
        }, 'intro epilogue');
      },
    });
  }

  // Chapter II: what came out of Cairo's pockets, laid on the table by the sofa
  showPockets() {
    if (this.pocketProps) return;
    this.pocketProps = new THREE.Group();
    const add = (geo, color, x, z, r) => { const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.7 })); m.position.set(x, 0.73, z); m.rotation.y = r; this.pocketProps.add(m); };
    const book = new THREE.BoxGeometry(0.09, 0.012, 0.13);
    add(book, '#5a1a14', -2.05, -0.15, 0.3); add(book, '#1e2a4a', -1.92, -0.2, -0.2); add(book, '#2a3a2a', -1.98, -0.05, 0.9);
    add(new THREE.BoxGeometry(0.06, 0.002, 0.12), '#d8cfb8', -1.75, 0.1, 0.4);
    add(new THREE.BoxGeometry(0.1, 0.002, 0.16), '#cfc6ae', -1.85, 0.2, -0.5);
    this.scene.add(this.pocketProps);
  }

  // Chapter IV: Watson stays below while Holmes goes up to meet Gutman alone
  watsonWaits() {
    const w = CHAPTER.watsonWaits;
    return !PREVIEW && w && !this.state.events.includes(w.until);
  }

  talk(id) {
    const portrait = PORTRAITS?.[id];
    if (portrait && !this.state.events.includes(portrait.event)) return this.enterPortrait(id, portrait);
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
      onEvent: name => this.runEvent(name),
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
      onDeduce: d => { this.state.addDeduction(d); audio.deduce(); this.autosave(); },
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
          saves.write('auto', { ...this.snapshot(), objective: 'Chapter complete' });
          const next = NEXT_PLAYABLE[chapterNumber];
          endCard({
            rating: this.state.rating(), onTitle: () => this.title(),
            next: next && { label: chapterNames[next], go: () => { rideNext(); location.href = `./?chapter=${next}`; } },
          });
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
    for (const person of this.present()) {
      const o = person.fig.object.position;
      if (Math.abs(o.y - pos.y) > 1.5) continue;
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
    const look = this.input.takeLook(dt);
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
    if (this.watsonWaits() && h.position.y > CHAPTER.watsonWaits.above) {  // waiting below, as he was told
      w.fig.animate(dt, 0, t);
      return;
    }
    // left behind on another floor (he doesn't take stairs on his own): catch up out of sight
    if (Math.abs(o.position.y - h.position.y) > 1.5 && Math.hypot(o.position.x - h.position.x, o.position.z - h.position.z) > 2.5) {
      o.position.set(tx, h.position.y, tz);
    }
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
    if ((this.mode === 'title' || this.mode === 'intro') && !this.state.events.length) {
      const a = this.time * 0.05;
      if (WORLD === 'hopkins') {  // along California Street, looking up at the house
        cam.position.set(Math.sin(a) * 14, 1.2 + Math.sin(a * 0.7) * 0.4, 44 + Math.cos(a) * 2);
        this.camLook = new THREE.Vector3(0, 8, 8);
      } else if (WORLD === 'kearny') {  // up Kearny Street into the fog
        cam.position.set(Math.sin(a) * 3, 2.4, 4 - (this.time * 0.6) % 60);
        this.camLook = new THREE.Vector3(0, 3, cam.position.z - 30);
      } else {  // slow drift down Bush Street toward the alley
        cam.position.set(Math.sin(a) * 6, 2.2 + Math.sin(a * 0.7) * 0.4, 17 + Math.cos(a) * 2);
        this.camLook = new THREE.Vector3(0, 1.6, -6);
      }
      cam.lookAt(this.camLook);
      return;
    }
    if (this.fixedCam && ['portrait', 'fight', 'intro'].includes(this.mode)) {
      const c = this.fixedCam;
      c.t = Math.min(1, c.t + dt * 1.6);
      const k = c.t * c.t * (3 - 2 * c.t);
      cam.position.lerpVectors(c.from, c.pos, k);
      this.camLook = c.lookFrom.clone().lerp(c.look, k);
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
    if (this.mode === 'explore') {
      for (const s of this.inters) {
        if (!this.sameFloor(s.pos[1], p) || Math.hypot(s.pos[0] - p.x, s.pos[2] - p.z) > 7) continue;
        const sc = this.project(...s.pos);
        if (sc) hud.label('in:' + s.id, sc[0], sc[1], s.label, 'mark', () => {
          if (Math.hypot(s.pos[0] - this.holmes.object.position.x, s.pos[2] - this.holmes.object.position.z) < s.r * 1.3) this.useHopkins(s);
          else this.hud.say('Closer.');
        });
      }
      for (const s of this.spots) {
        if (!this.spotLive(s) || !this.sameFloor(s.pos[1], p)) continue;
        const found = s.clues ? s.clues.every(c => this.state.has(c)) : s.clue && this.state.has(s.clue);
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
      if (f > 0.3 && !PREVIEW) {
        const reads = Object.keys(READS).map(id => {
          const person = this.people[id];
          if (person) return person.fig.object.visible ? [id, person.fig.object.position, 2.05] : null;
          return this.anchors[id] ? [id, this.anchors[id].position, this.anchors[id].height] : null;
        }).filter(Boolean);
        for (const [id, o, hgt] of reads) {
          if (Math.hypot(o.x - p.x, o.z - p.z) > 6 || Math.abs(o.y - p.y) > 1.5) continue;
          const sc = this.project(o.x, o.y + hgt, o.z);
          if (!sc) continue;
          READS[id].forEach((txt, i) => {
            hud.label(`read:${id}:${i}`, sc[0] + 18, sc[1] - 34 + i * 20, txt, 'read');
            if (f > 0.9) this.state.addRead(`${id}:${i}`);
          });
        }
      }
    } else if (this.mode === 'portrait' && this.portrait && this.fixedCam?.t > 0.85) {
      for (const s of this.portrait.def.spots) {
        const found = this.state.has(s.clue);
        const w = this.portrait.person.localToWorld(new THREE.Vector3(...s.local));
        const sc = this.project(w.x, w.y, w.z);
        if (sc) hud.label('pt:' + s.clue, sc[0], sc[1], found ? CLUES[s.clue].title : s.label, 'mark focus' + (found ? ' done' : ''), () => { if (!found) this.portraitFound(s); });
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

  // --- controller --------------------------------------------------------------------------------
  // Where the menu highlight lives in each mode (null: the sticks play the game instead).
  padRoots() {
    const $ = id => document.getElementById(id);
    switch (this.mode) {
      case 'title': case 'intro': case 'accuse': case 'menu': return [$('screen')];
      case 'talk': return [$('dialogue')];
      case 'book': return [$('book')];
      case 'palace': return [$('palace')];
      case 'closeup': return [$('labels'), $('btn-back')];
      case 'portrait': return [$('labels'), $('screen')];
      case 'fight': return [$('screen')];
      default: return null;
    }
  }

  updatePad(dt) {
    const p = this.pad;
    p.poll();
    if (!document.body.classList.contains('pad')) return;
    if (p.justWoke) { const r = this.padRoots(); if (r) p.ensureSel(r, this.mode === 'title' ? '.primary' : null); return; }
    const roots = this.padRoots();
    const $ = id => document.getElementById(id);
    const click = el => el?.dispatchEvent(new MouseEvent('click', { bubbles: true }));

    // menu highlight: always on screen where there is one, moved with the d-pad or the left stick
    if (roots && !(this.mode === 'talk' && !this.dialogue.choices.children.length)) {
      p.ensureSel(roots, this.mode === 'title' ? '.primary' : null);
      const dir = p.navStep(dt);
      if (dir) p.move(roots, dir);
    } else p.clearSel();

    if (p.pressed(BTN.A)) {
      if (this.mode === 'explore') this.interact();
      else if (this.mode === 'talk' && !this.dialogue.choices.children.length) this.dialogue.next();
      else if (p.sel) click(p.sel);
      else if (['intro', 'title', 'accuse'].includes(this.mode)) click($('screen'));  // tap-to-continue cards
    }
    if (p.pressed(BTN.B)) {
      if (this.mode === 'closeup') this.leaveCloseup();
      else if (this.mode === 'book') click($('book').querySelector('.close'));
      else if (this.mode === 'palace') click($('palace').querySelector('.close'));
      else if (this.mode === 'talk') click(this.dialogue.choices.querySelector('.bye'));
      else if (this.mode === 'accuse') click($('screen').querySelector('.back'));
      else if (this.mode === 'menu') click($('screen').querySelector('[data-a=resume], [data-a=back]'));
    }
    if (p.pressed(BTN.X) || p.pressed(BTN.R3)) this.toggleFocus();
    if (p.pressed(BTN.Y)) this.mode === 'palace' ? click($('palace').querySelector('.close')) : this.openPalace();
    if (p.pressed(BTN.VIEW)) this.mode === 'menu' ? click($('screen').querySelector('[data-a=resume], [data-a=back]')) : this.openMenu();
    if (p.pressed(BTN.MENU)) this.mode === 'book' ? click($('book').querySelector('.close')) : this.openBook();
    if (this.mode === 'book' && (p.pressed(BTN.LB) || p.pressed(BTN.RB))) {  // flip notebook tabs
      const tabs = [...$('book').querySelectorAll('.tabs button')];
      const i = tabs.findIndex(t => t.classList.contains('on'));
      click(tabs[(i + (p.pressed(BTN.RB) ? 1 : tabs.length - 1)) % tabs.length]);
    }
  }

  frame() {
    this.timer.update();
    const dt = Math.min(0.05, this.timer.getDelta());
    this.time += dt;
    this.updatePad(dt);

    // Focus: drains while on, refills while off; the world slows around Holmes
    if (this.focusOn) {
      this.meter = Math.max(0, this.meter - dt * 0.1);
      if (this.meter === 0) { this.focusOn = false; audio.focus(false); this.hud.say('Enough. The mind must rest.'); }
    } else this.meter = Math.min(1, this.meter + dt * 0.08);
    this.focus = damp(this.focus, this.focusOn || ['portrait', 'fight'].includes(this.mode) ? 1 : 0, 5, dt);
    const wdt = dt * (1 - 0.7 * this.focus);
    this.camera.fov = 55 - 7 * this.focus;
    this.camera.updateProjectionMatrix();

    if (this.mode === 'explore') this.updateHolmes(dt);
    this.holmes.animate(dt, this.mode === 'explore' ? this.holmesSpeed ?? 0 : 0, this.time);
    this.updateWatson(wdt, this.time);
    if (this.mode === 'explore') this.tail?.update(dt);
    if (this.mode === 'explore' && this.time - (this.lastAutosave ?? 0) > 20) this.autosave();
    for (const person of this.present()) person.fig.animate(wdt, person.speed ?? 0, this.time);
    this.world.update(wdt, this.time, this.focus, this.camera, this.holmes.object.position);
    if (this.pocketLamp) this.pocketLamp.intensity = damp(this.pocketLamp.intensity, this.mode === 'closeup' ? 3.5 : 0, 4, dt);
    this.updateCamera(dt);

    if (this.mode === 'explore') {
      const c = this.candidate();
      this.hud.setAct(c ? (c.inter ? c.inter.label : c.person ? 'Talk to ' + PEOPLE[c.person].name : c.spot.label) : null);
      this.hud.setObjective(PREVIEW ? this.world.roomAt(this.holmes.object.position) : this.state.objective());
    }
    this.hud.setFocus(this.focusOn, this.meter);
    this.updateLabels();
    this.hud.update(dt);
    audio.update(dt);
    this.renderer.render(this.time, this.focus);
  }
}

const models = ['holmes', ...new Set(Object.values(PREVIEW ? { w: PEOPLE.watson } : PEOPLE).map(p => p.look.model).filter(Boolean))];
if (CHAPTER.id === 'archer' && !PREVIEW) models.push('archer');
const ride = showRide(PREVIEW ? { to: 'Nob Hill', place: 'The Mark Hopkins Institute of Art', time: 'An evening walk' } : CHAPTER.ride);
const assets = [loadModels(models), { hopkins: loadHopkins, kearny: loadKearny, palace: () => loadRoom('palace') }[WORLD]?.() ?? loadSet()];
Promise.all(assets).then(() => { window.game = new Game(); return ride(); });
