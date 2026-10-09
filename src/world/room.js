// An interior built by a set script (palace.glb + palace.json): colliders, gas lamps and named places.
// A few warm lights move to the lamps nearest Holmes; the fire flickers. Used for Holmes's suite at the Palace
// (Chapter II) and Brigid's at the St. Mark (Chapter III).
import * as THREE from 'three';
import { gltfLoader } from '../core/gltf.js';

let model = null, data = null;
export function loadRoom(name) {
  return Promise.all([
    gltfLoader.loadAsync(`models/${name}.glb`).then(g => { model = g.scene; }),
    fetch(`models/${name}.json`).then(r => r.json()).then(d => { data = d; }),
  ]);
}

export class Room {
  constructor(scene) {
    this.data = data;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.group.add(model);
    model.traverse(o => {
      const m = o.material;
      if (!o.isMesh || !m) return;
      // the street outside the windows is painted with its own fog and daylight: the room's fog would black it out
      if (m.name.startsWith('view_')) m.fog = false;
      // glass and lace are opaque in the glTF; here they let the street show through
      if (m.name === 'glass_clear') Object.assign(m, { transparent: true, opacity: 0.16, depthWrite: false });
      if (m.name === 'lace') Object.assign(m, { transparent: true, opacity: 0.5, depthWrite: false });
    });
    this.colliders = data.colliders.map(c => new THREE.Box3(new THREE.Vector3(c[0], c[1], c[2]), new THREE.Vector3(c[3], c[4], c[5])));
    this.lamps = data.lamps.map(p => new THREE.Vector3(...p));
    this.interact = [];
    scene.background = new THREE.Color('#0c1016');
    scene.fog = new THREE.FogExp2('#141a22', 0.03);
    scene.add(new THREE.HemisphereLight('#6a6a78', '#2a1c12', 0.55));
    const day = new THREE.DirectionalLight('#9ab0d0', 0.35);  // grey morning light from the bay window
    day.position.set(0, 6, -20);
    scene.add(day);
    this.gas = this.lamps.slice(0, 4).map(() => { const l = new THREE.PointLight('#ffb468', 0, 12, 1.5); scene.add(l); return l; });
  }

  update(dt, t, focus, camera, holmes) {
    const near = this.lamps.map(l => [l, l.distanceToSquared(holmes)]).sort((a, b) => a[1] - b[1]);
    this.gas.forEach((g, i) => {
      const n = near[i]; if (!n) return;
      g.position.copy(n[0]);
      const fire = n[0].y < 1;  // the firelight, low down: it flickers
      g.intensity = (fire ? 6 + Math.sin(t * 11) * 1.2 + Math.sin(t * 7.3) * 0.8 : 12);
      g.color.set(fire ? '#ff8a40' : '#ffb468');
    });
  }
}
