// Kearny Street in the fog, Market Street to Bush (art/build_city.py: kearny.glb + kearny.json). Flat ground;
// colliders, gas lamps, cover points (doorways, lamp posts, cabs) and named places from the JSON; a Sutter Street
// cable car runs across the intersection on a loop and is cover while it passes.
import * as THREE from 'three';
import { gltfLoader, fetchJSON } from '../core/gltf.js';
import { audio } from '../core/audio.js';

let model = null, data = null;
export function loadKearny() {
  return Promise.all([
    gltfLoader.loadAsync('models/kearny.glb').then(g => { model = g.scene; }),
    fetchJSON('models/kearny.json').then(d => { data = d; }),
  ]);
}

const LIGHTS = 6;

export class Kearny {
  constructor(scene) {
    this.scene = scene;
    this.data = data;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.group.add(model);
    this.colliders = data.colliders.map(c => new THREE.Box3(new THREE.Vector3(c[0], c[1], c[2]), new THREE.Vector3(c[3], c[4], c[5])));
    this.lamps = data.lamps.map(p => new THREE.Vector3(...p));
    this.cover = data.cover.map(([x, z, kind]) => ({ x, z, kind }));
    this.interact = [];

    scene.background = new THREE.Color('#141a22');
    scene.fog = new THREE.FogExp2('#1a222c', 0.042);
    scene.add(new THREE.HemisphereLight('#56667e', '#1a140e', 0.8));
    const moon = new THREE.DirectionalLight('#8fa6c8', 0.35);
    moon.position.set(-10, 30, 10);
    scene.add(moon);
    this.gas = Array.from({ length: LIGHTS }, () => { const l = new THREE.PointLight('#ffb468', 0, 16, 1.5); scene.add(l); return l; });

    // the cable car: its own node in the model, run along Sutter Street; a moving collider and moving cover
    this.car = model.getObjectByName('CableCar');
    const c = data.cablecar;
    this.carBox = new THREE.Box3();
    this.colliders.push(this.carBox);
    this.carT = c.period * 0.55;  // first pass comes soon after you reach the first block's end
    this.carLight = new THREE.PointLight('#ffd08a', 0, 9, 1.6);
    scene.add(this.carLight);
  }

  // is (x, z) in cover from someone looking from (fx, fz)? Doorways and posts hide you close by;
  // the cable car hides you while it is between you and them
  inCover(x, z, fx, fz) {
    for (const c of this.cover) if (Math.hypot(c.x - x, c.z - z) < (c.kind === 'doorway' ? 1.5 : 1.1)) return c.kind;
    if (this.car?.visible) {
      const b = this.carBox, ray = new THREE.Ray(new THREE.Vector3(fx, 1.4, fz), new THREE.Vector3(x - fx, 0, z - fz).normalize());
      const hit = ray.intersectBox(b, new THREE.Vector3());
      if (hit && hit.distanceTo(ray.origin) < Math.hypot(x - fx, z - fz)) return 'cablecar';
    }
    return null;
  }

  update(dt, t, focus, camera, holmes) {
    const c = this.data.cablecar;
    // the car: across the intersection one way, a pause off in the fog, back the other way
    this.carT = (this.carT + dt) % (c.period * 2);
    const run = (c.x1 - c.x0) / c.speed;
    const leg = this.carT % c.period, dir = this.carT < c.period ? 1 : -1;
    const k = Math.min(1, leg / run);
    const x = dir > 0 ? c.x0 + (c.x1 - c.x0) * k : c.x1 - (c.x1 - c.x0) * k;
    this.car.visible = leg < run;
    this.car.position.x = x;
    if (this.car.visible) {
      this.carBox.min.set(x - c.length / 2, 0, c.z - c.width / 2);
      this.carBox.max.set(x + c.length / 2, 3, c.z + c.width / 2);
      this.carLight.position.set(x + dir * (c.length / 2 + 1), 2.2, c.z);
      this.carLight.intensity = 8;
      // the bell as it comes up to Kearny
      if (!this.rang && Math.abs(x) < 16) { this.rang = true; audio.bell(); }
    } else {
      this.carBox.makeEmpty(); this.carLight.intensity = 0; this.rang = false;
    }
    // gas lights on the lamps nearest Holmes
    const near = this.lamps.map(l => [l, l.distanceToSquared(holmes)]).sort((a, b) => a[1] - b[1]);
    this.gas.forEach((g, i) => {
      g.position.copy(near[i][0]);
      g.intensity = 9 * (1 + Math.sin(t * 9 + i * 1.7) * 0.03);
    });
  }
}
