// Burritt Alley off Bush Street, San Francisco, a little after two in the
// morning. The alley runs along -Z from Bush Street (z ≈ 8) to a plank fence
// at z = -22, beyond which the hill drops away to Stockton Street.
import * as THREE from 'three';
import * as T from './textures.js';
import { gltfLoader } from '../core/gltf.js';

const ALLEY_HALF = 2.5;
export const FENCE_Z = -22;

// The modelled set (art/build_set.py): buildings, lamps, wires and clutter.
// Without it the alley falls back to the boxes below, which always provide
// the colliders.
let set = null;
export function loadSet() {
  return gltfLoader.loadAsync('models/burritt.glb')
    .then(g => { set = g.scene; })
    .catch(e => console.warn('set not loaded, using blockout', e));
}

export class Alley {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.colliders = [];   // THREE.Box3, used for walking and the camera
    this.hidden = [];      // { material, base } faded in by Focus
    this.fog = [];
    this.blockout = new THREE.Group();  // stand-in boxes the modelled set replaces
    this.group.add(this.blockout);

    scene.background = new THREE.Color('#0d1218');
    scene.fog = new THREE.FogExp2('#18202a', 0.052);

    this.buildGround();
    this.buildBuildings();
    this.buildAlleyDressing();
    this.buildFence();
    this.buildLights();
    this.buildFog();
    this.buildHiddenDetails();
    if (set) this.useSet();
  }

  useSet() {
    this.blockout.visible = false;
    this.group.add(set);
  }

  box(w, h, d, material, x, y, z, collide = true, into = this.blockout) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), material);
    m.position.set(x, y, z);
    into.add(m);
    if (collide) this.colliders.push(new THREE.Box3().setFromObject(m));
    return m;
  }

  buildGround() {
    const street = new THREE.MeshStandardMaterial({ map: T.cobbles(30, 7), roughness: 0.42, metalness: 0.05 });
    const s = new THREE.Mesh(new THREE.PlaneGeometry(60, 14), street);
    s.rotation.x = -Math.PI / 2; s.position.set(0, 0, 15);
    this.group.add(s);

    const alley = new THREE.MeshStandardMaterial({ map: T.cobbles(2.5, 15), roughness: 0.5 });
    const a = new THREE.Mesh(new THREE.PlaneGeometry(ALLEY_HALF * 2, 30), alley);
    a.rotation.x = -Math.PI / 2; a.position.set(0, 0, -7);
    this.group.add(a);

    // cable car slot and rails down the middle of Bush Street
    const iron = new THREE.MeshStandardMaterial({ color: '#4a4a4c', roughness: 0.3, metalness: 0.8 });
    for (const z of [14.2, 15.0, 15.8]) {
      const r = new THREE.Mesh(new THREE.BoxGeometry(60, 0.02, z === 15.0 ? 0.04 : 0.08), z === 15.0 ? new THREE.MeshBasicMaterial({ color: '#050505' }) : iron);
      r.position.set(0, 0.01, z);
      this.group.add(r);
    }
    // kerbs
    const stone = new THREE.MeshStandardMaterial({ color: '#5d5a54', roughness: 0.8 });
    this.box(23.5, 0.15, 1.6, stone, -14.25, 0.075, 8.8, false, this.group);
    this.box(23.5, 0.15, 1.6, stone, 14.25, 0.075, 8.8, false, this.group);
    this.box(60, 0.15, 1.6, stone, 0, 0.075, 21.2, false, this.group);

    // the drop beyond the fence: a weedy ledge, then the lights of Stockton Street far below
    const ledge = new THREE.Mesh(new THREE.PlaneGeometry(6, 2.2), new THREE.MeshStandardMaterial({ color: '#2a2b1f', roughness: 1 }));
    ledge.rotation.x = -Math.PI / 2; ledge.position.set(0, -0.25, FENCE_Z - 1.2);
    this.group.add(ledge);
    const pts = [];
    for (let i = 0; i < 60; i++) pts.push((Math.random() - 0.5) * 70, -14 - Math.random() * 6, -45 - Math.random() * 40);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
    this.group.add(new THREE.Points(g, new THREE.PointsMaterial({ color: '#ffcf8a', size: 0.5, fog: true })));
  }

  buildBuildings() {
    const brickL = new THREE.MeshStandardMaterial({ map: T.bricks(4, 4), roughness: 0.9 });
    const brickR = new THREE.MeshStandardMaterial({ map: T.bricks(4, 3, [80, 52, 40]), roughness: 0.9 });
    const plasterA = new THREE.MeshStandardMaterial({ map: T.plaster(4, 4), roughness: 0.9 });
    const plasterB = new THREE.MeshStandardMaterial({ map: T.plaster(4, 4, [92, 96, 90]), roughness: 0.9 });

    // the two buildings the alley runs between
    this.box(11.5, 12, 30, brickL, -8.25, 6, -7);
    this.box(11.5, 9, 30, brickR, 8.25, 4.5, -7);
    // the rest of the near side of Bush Street
    this.box(14, 10, 14, plasterA, -21, 5, 1);
    this.box(14, 11, 14, plasterB, 21, 5.5, 1);
    // far side of Bush Street
    const far = [[-24, 9, plasterB], [-12, 13, brickR], [0, 10, plasterA], [12, 12, brickL], [24, 8, plasterB]];
    for (const [x, h, m] of far) this.box(12, h, 8, m, x, h / 2, 26);
    // the ends of the street, where the fog takes it: deep enough that there is no slipping round the corner
    // fronts at |x| = 28 into the dark behind them (the set's last fronts end at |x| = 44)
    this.colliders.push(new THREE.Box3(new THREE.Vector3(-34, 0, -8), new THREE.Vector3(-28.5, 10, 30)));
    this.colliders.push(new THREE.Box3(new THREE.Vector3(28.5, 0, -8), new THREE.Vector3(34, 10, 30)));
    // the iron lamp posts and telegraph poles along Bush Street (burritt.glb), which Holmes walked through
    for (const [x, z, r] of [[13, 9.6, 0.2], [-19, 9.6, 0.2], [7, 20.6, 0.2], [-13, 20.6, 0.2], [24, 20.6, 0.2], [-10, 9.5, 0.15], [10, 9.5, 0.15]]) {
      this.colliders.push(new THREE.Box3(new THREE.Vector3(x - r, 0, z - r), new THREE.Vector3(x + r, 4, z + r)));
    }

    // lit and dark windows on the street fronts
    const lit = new THREE.MeshBasicMaterial({ color: '#ffb25a' });
    const dark = new THREE.MeshStandardMaterial({ color: '#0b0d10', roughness: 0.2, metalness: 0.4 });
    const win = new THREE.PlaneGeometry(1.0, 1.6);
    const add = (x, y, z, ry) => {
      const w = new THREE.Mesh(win, Math.random() < 0.22 ? lit : dark);
      w.position.set(x, y, z); w.rotation.y = ry;
      this.blockout.add(w);
    };
    for (let x = -27; x <= 27; x += 2.4) for (const y of [3, 6, 9]) {
      const h = [9, 13, 10, 12, 8][Math.min(4, Math.floor((x + 30) / 12))];
      if (y < h - 1) add(x, y, 21.99, Math.PI);
    }
    for (const [x0, x1] of [[-14, -3], [3, 14], [-28, -14], [14, 28]]) {
      for (let x = x0 + 1.2; x < x1 - 0.6; x += 2.4) for (const y of [3, 6]) add(x, y, 8.01, 0);
    }
  }

  buildAlleyDressing() {
    const wood = new THREE.MeshStandardMaterial({ map: T.planks(1, 1), roughness: 0.9 });
    const tin = new THREE.MeshStandardMaterial({ color: '#4c4e4a', roughness: 0.6, metalness: 0.5 });
    // crates and barrels (collide so you walk round them)
    this.box(0.9, 0.9, 0.9, wood, -1.9, 0.45, -3.5);
    this.box(0.7, 0.7, 0.7, wood, -1.95, 1.25, -3.4, false).rotation.y = 0.3;
    this.box(0.8, 0.8, 0.8, wood, 1.95, 0.4, -11.5);
    for (const [x, z] of [[2.0, -6.2], [1.95, -7.1], [-2.0, -13.0]]) {
      const b = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.95, 12), tin);
      b.position.set(x, 0.475, z);
      this.blockout.add(b);
      this.colliders.push(new THREE.Box3().setFromObject(b));
    }
    // drainpipes and a back door on each wall
    for (const [x, z] of [[-2.45, 2], [2.45, -9]]) {
      const p = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 9, 6), tin);
      p.position.set(x, 4.5, z); this.blockout.add(p);
    }
    const door = new THREE.MeshStandardMaterial({ color: '#2b1c12', roughness: 0.8 });
    this.box(0.08, 2.2, 1.1, door, -2.47, 1.1, -10, false);
    this.box(0.08, 2.2, 1.1, door, 2.47, 1.1, -15, false);

    // billboard on the right wall at the dead end
    const bill = new THREE.Mesh(new THREE.PlaneGeometry(3.4, 1.7), new THREE.MeshStandardMaterial({ map: T.poster(), roughness: 0.95 }));
    bill.position.set(2.44, 2.6, -19.5); bill.rotation.y = -Math.PI / 2;
    this.group.add(bill);
  }

  buildFence() {
    const wood = new THREE.MeshStandardMaterial({ map: T.planks(1, 1, [70, 60, 46]), roughness: 0.95 });
    const z = FENCE_Z;
    // boards with a gap where Archer went back against it
    for (let x = -2.4; x < 2.45; x += 0.2) {
      if (x > 0.35 && x < 1.15) continue;
      this.box(0.18, 1.9, 0.04, wood, x, 0.95, z, false, this.group);
    }
    this.box(5, 0.1, 0.08, wood, 0, 1.6, z - 0.05, false, this.group);
    this.box(5, 0.1, 0.08, wood, 0, 0.4, z - 0.05, false, this.group);
    // snapped boards lying outward on the ledge
    for (const [x, rz, ry] of [[0.5, 0.2, 0.3], [0.9, -0.15, -0.4], [0.7, 0.05, 0.1]]) {
      const b = new THREE.Mesh(new THREE.BoxGeometry(0.18, 1.2, 0.04), wood);
      b.position.set(x, -0.2, z - 0.9);
      b.rotation.set(-Math.PI / 2 + 0.15, ry, rz);
      this.group.add(b);
    }
    this.colliders.push(new THREE.Box3(new THREE.Vector3(-2.5, 0, z - 0.3), new THREE.Vector3(2.5, 2, z + 0.25)));
  }

  buildLights() {
    this.scene.add(new THREE.HemisphereLight('#5a7290', '#1a140e', 0.95));
    // a little moonlight through the fog, so faces read against the dark
    const moon = new THREE.DirectionalLight('#8fa6c8', 0.45);
    moon.position.set(-6, 14, 8);
    this.scene.add(moon);

    const iron = new THREE.MeshStandardMaterial({ color: '#1b1c1e', roughness: 0.5, metalness: 0.7 });
    // brighter than white, so the bloom pass gives the flame its glow
    const glass = new THREE.MeshBasicMaterial({ color: new THREE.Color(3.2, 2.2, 1.2) });
    const lamp = (x, y, z, intensity, dist) => {
      const l = new THREE.PointLight('#ffb468', intensity, dist, 1.6);
      l.position.set(x, y, z);
      this.scene.add(l);
      const g = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.32, 0.22), glass);
      g.position.copy(l.position); this.blockout.add(g);
      return l;
    };
    // street lamp on Bush Street, by the alley mouth
    const post = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 3.6, 8), iron);
    post.position.set(-3.6, 1.8, 9.6); this.blockout.add(post);
    this.colliders.push(new THREE.Box3().setFromObject(post));
    this.streetLamp = lamp(-3.6, 3.4, 9.6, 26, 18);
    // bracket lamp on the alley wall
    this.box(0.7, 0.05, 0.05, iron, -2.15, 3.2, -8, false);
    this.alleyLamp = lamp(-1.85, 3.03, -8, 12, 11);
    // the police lantern by the body, set on the cobbles
    this.lantern = new THREE.PointLight('#ffc27a', 7, 7, 1.8);
    this.lantern.position.set(-0.9, 0.5, -17.8);
    this.scene.add(this.lantern);
    const lan = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 0.28, 8), glass);
    lan.position.set(-0.9, 0.14, -17.8); this.group.add(lan);
  }

  buildFog() {
    const map = T.glow('rgba(150,165,180,0.5)');
    for (let i = 0; i < 26; i++) {
      // own material each so puffs near the camera can fade out
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map, depthWrite: false, transparent: true, opacity: 0 }));
      const inAlley = i < 12;
      s.position.set(inAlley ? (Math.random() - 0.5) * 4 : (Math.random() - 0.5) * 50, 0.6 + Math.random() * 2.5,
        inAlley ? -20 + Math.random() * 26 : 9 + Math.random() * 12);
      s.scale.setScalar(5 + Math.random() * 5);
      s.userData.v = 0.15 + Math.random() * 0.25;
      this.group.add(s);
      this.fog.push(s);
    }
  }

  // Details only Focus brings out. Each fades in with the Focus amount.
  buildHiddenDetails() {
    const reveal = (material, base = 1) => { material.transparent = true; material.opacity = 0; material.depthWrite = false; this.hidden.push({ material, base }); return material; };

    // a lady's narrow heels, toes toward the fence, where the shooter stood
    const heel = reveal(new THREE.MeshBasicMaterial({ map: T.heelPrint(), color: '#ffd27a', fog: false }), 0.9);
    const geo = new THREE.PlaneGeometry(0.1, 0.22);
    for (const [x, z, r] of [[0.35, -17.1, 0.1], [0.62, -17.25, -0.05], [0.1, -16.4, 0.2], [0.42, -15.6, 0.0], [0.05, -14.8, 0.15]]) {
      const p = new THREE.Mesh(geo, heel);
      p.rotation.set(-Math.PI / 2, 0, Math.PI + r);
      p.position.set(x, 0.012, z);
      this.group.add(p);
    }

    // a wisp of scent beneath the alley lamp
    const wisp = reveal(new THREE.SpriteMaterial({ map: T.glow('rgba(200,170,255,0.9)'), blending: THREE.AdditiveBlending, depthWrite: false, fog: false }), 0.55);
    this.wisps = [];
    for (let i = 0; i < 5; i++) {
      const s = new THREE.Sprite(wisp);
      s.scale.setScalar(0.6 + i * 0.12);
      s.userData.o = i;
      this.group.add(s);
      this.wisps.push(s);
    }

    // the revolver in the weeds past the fence, catching the light
    const steel = new THREE.MeshStandardMaterial({ color: '#2b2b2e', roughness: 0.35, metalness: 0.9 });
    const gun = new THREE.Group();
    gun.add(new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.03, 0.03), steel));
    const grip = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.1, 0.03), new THREE.MeshStandardMaterial({ color: '#2a1a10' }));
    grip.position.set(-0.1, -0.04, 0); grip.rotation.z = -0.4; gun.add(grip);
    gun.position.set(0.9, -0.22, FENCE_Z - 1.3); gun.rotation.set(Math.PI / 2, 0, 0.6);
    this.group.add(gun);
    const glint = new THREE.Sprite(new THREE.SpriteMaterial({ map: T.glow('rgba(255,240,200,1)'), blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
    reveal(glint.material, 1);
    glint.scale.setScalar(0.5);
    glint.position.set(0.95, -0.12, FENCE_Z - 1.3);
    this.group.add(glint);
    this.glint = glint;

    // powder scorch on Archer's coat (shown in the close-up)
    const burn = reveal(new THREE.MeshBasicMaterial({ map: T.glow('rgba(255,180,90,0.9)'), color: '#ffffff', fog: false }), 0.9);
    const b = new THREE.Mesh(new THREE.CircleGeometry(0.09, 16), burn);
    b.position.set(0.6, 0.39, -20.38); b.rotation.x = -Math.PI / 2;
    this.group.add(b);
  }

  update(dt, t, focus, camera) {
    for (const s of this.fog) {
      const d = s.position.distanceTo(camera.position);
      s.material.opacity = 0.13 * Math.min(1, Math.max(0, (d - 2) / 5));
      s.position.x += s.userData.v * dt;
      if (s.position.x > (s.position.z < 8 ? 2.5 : 25)) s.position.x -= s.position.z < 8 ? 5 : 50;
    }
    for (const h of this.hidden) h.material.opacity = h.base * focus;
    for (const w of this.wisps) {
      const k = w.userData.o;
      w.position.set(-1.9 + Math.sin(t * 0.7 + k) * 0.25, 1.1 + k * 0.22 + Math.sin(t * 0.5 + k * 2) * 0.1, -8 + Math.cos(t * 0.6 + k) * 0.3);
    }
    this.glint.scale.setScalar(0.35 + Math.max(0, Math.sin(t * 3)) * 0.35);
    this.lantern.intensity = 7 + Math.sin(t * 13) * 0.4 + Math.sin(t * 7.3) * 0.3;
  }
}
