// The Mark Hopkins Institute of Art on Nob Hill (the old Hopkins mansion), at
// night, with San Francisco spread out below it to the bay. The building comes
// from art/build_hopkins.py (hopkins.glb + hopkins.json: colliders, rooms,
// lamps and the places Holmes can use); the city below is generated here.
import * as THREE from 'three';
import { gltfLoader } from '../core/gltf.js';

let model = null, data = null;
export function loadHopkins() {
  return Promise.all([
    gltfLoader.loadAsync('models/hopkins.glb').then(g => { model = g.scene; }),
    fetch('models/hopkins.json').then(r => r.json()).then(d => { data = d; }),
  ]);
}

const LIGHTS = 6;  // a handful of gas lights follow Holmes from room to room; phones can't afford one per lamp

export class Hopkins {
  constructor(scene) {
    this.scene = scene;
    this.group = new THREE.Group();
    scene.add(this.group);
    this.data = data;
    this.colliders = data.colliders.map(c => new THREE.Box3(new THREE.Vector3(c[0], c[1], c[2]), new THREE.Vector3(c[3], c[4], c[5])));
    this.rooms = data.rooms;
    this.interact = data.interact;
    this.lamps = data.lamps.map(p => new THREE.Vector3(...p));

    scene.background = new THREE.Color('#0a1018');
    scene.fog = new THREE.FogExp2('#101823', 0.0035);
    this.group.add(model);
    // the solarium and observatory glass: thin and clear, so the city shows through
    model.traverse(o => {
      if (o.isMesh && o.material.name === 'glass_clear') {
        o.material.transparent = true; o.material.opacity = 0.12; o.material.depthWrite = false;
        o.material.metalness = 0.2; o.material.roughness = 0.05;
      }
    });

    scene.add(new THREE.HemisphereLight('#4a5a78', '#1a120c', 0.6));
    // the moon is behind the house over the bay; light the street front from the other side, softly
    const moon = new THREE.DirectionalLight('#9ab0d0', 0.85);
    moon.position.set(-30, 45, 60);
    scene.add(moon);
    this.gas = [];
    for (let i = 0; i < LIGHTS; i++) {
      const l = new THREE.PointLight('#ffb468', 0, 14, 1.4);
      scene.add(l);
      this.gas.push(l);
    }
    this.buildSky();
    this.buildCity();
  }

  // Floor height under (x, z): the terrace is 0, California Street below the wall, ramps and steps between.
  // Up in the tower the floor is wherever Holmes already is.
  groundAt(x, z, y) {
    if (y > 10) return y;
    const g = this.data.ground;
    for (const [x0, x1, z0, z1, y0, y1] of g.ramps) {
      if (x >= x0 && x <= x1 && z >= z0 && z <= z1) return y0 + (y1 - y0) * (z - z0) / (z1 - z0);
    }
    return z > g.wall ? g.street : 0;
  }

  roomAt(p) {
    if (p.y > 10) return 'The Tower Observatory';
    if (p.z > this.data.ground.wall) return 'California Street';
    const r = this.rooms.find(r => p.x > r.x0 && p.x < r.x1 && p.z > r.z0 && p.z < r.z1);
    return r ? r.name : 'The Grounds';
  }

  buildSky() {
    // stars and a gibbous moon over the bay
    const n = 900, pts = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2, e = 0.08 + Math.random() * 1.3;
      pts.set([Math.cos(a) * Math.cos(e) * 900, Math.sin(e) * 900, Math.sin(a) * Math.cos(e) * 900], i * 3);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pts, 3));
    this.group.add(new THREE.Points(g, new THREE.PointsMaterial({ color: '#c8d4e8', size: 1.6, sizeAttenuation: false, fog: false })));
    const moon = new THREE.Mesh(new THREE.CircleGeometry(16, 32), new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 2.2, 2.0), fog: false }));
    moon.position.set(-260, 240, -700);
    moon.lookAt(0, 0, 0);
    this.group.add(moon);
  }

  // San Francisco in 1895 falling away from Nob Hill: streets of gas lamps on a grid, windows lit in the blocks,
  // the dark water of the bay with ships' riding lights, and the far shore's scattered lights.
  buildCity() {
    const rng = (() => { let s = 1895; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); })();
    const lamps = [], windows = [];
    const ground = (x, z) => {
      // Nob Hill's top is here; the land falls to the bay (north, -z) and east (+x), more gently west and south
      const d = Math.hypot(x, z);
      const fall = -0.12 * Math.max(0, d - 40) - 0.06 * Math.max(0, -z - 40) - 0.04 * Math.max(0, x - 40);
      return Math.max(-95, fall) - 3;
    };
    const R = 1300, block = 42;
    for (let x = -R; x <= R; x += block) {
      for (let z = -R; z <= R; z += block) {
        if (Math.hypot(x, z) < 70) continue;
        if (this.water(x, z)) continue;
        const y = ground(x, z);
        // gas lamps at the street corners and halfway along
        lamps.push(x, y + 3.5, z, x + block / 2, y + 3.5, z);
        // lit windows: fewer at two in the morning, more toward the waterfront and Chinatown
        const busy = (z < -500 || (x > -200 && x < 150 && z < -100 && z > -500)) ? 6 : 2;
        for (let k = 0; k < busy; k++) if (rng() < 0.55) windows.push(x + 4 + rng() * (block - 8), y + 3 + rng() * 9, z + 4 + rng() * (block - 8));
      }
    }
    // the far shore: Oakland and the Contra Costa hills
    const shore = [];
    for (let i = 0; i < 700; i++) {
      const x = -1800 + rng() * 4200, z = -2600 - rng() * 600;
      shore.push(x, -80 + rng() * 40 + Math.max(0, (z + 2600) * -0.05), z);
    }
    // ships at anchor and the ferries
    const ships = [];
    for (let i = 0; i < 40; i++) {
      let x, z;
      do { x = -1500 + rng() * 3200; z = -800 - rng() * 1700; } while (!this.water(x, z));
      ships.push(x, -96, z, x + 3, -90 - rng() * 6, z);
    }
    const pts = (arr, color, size) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.Float32BufferAttribute(arr, 3));
      const m = new THREE.PointsMaterial({ color, size, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.95 });
      this.group.add(new THREE.Points(g, m));
    };
    pts(lamps, new THREE.Color(3.0, 1.9, 0.9), 2.2);
    pts(windows, new THREE.Color(2.2, 1.5, 0.8), 1.6);
    pts(shore, new THREE.Color(1.8, 1.3, 0.8), 1.4);
    pts(ships, new THREE.Color(2.4, 2.0, 1.6), 1.8);

    // the land as a dark sheet so the lights sit on something, and the bay below it
    const seg = 90, size = 2 * R + 400;
    const land = new THREE.PlaneGeometry(size, size, seg, seg);
    land.rotateX(-Math.PI / 2);
    const pos = land.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), z = pos.getZ(i);
      pos.setY(i, Math.hypot(x, z) < 45 ? -3.5 : ground(x, z) - 0.5);
    }
    land.computeVertexNormals();
    this.group.add(new THREE.Mesh(land, new THREE.MeshLambertMaterial({ color: '#0d1014' })));
    const bay = new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000), new THREE.MeshStandardMaterial({ color: '#05080c', roughness: 0.25, metalness: 0.6 }));
    bay.rotation.x = -Math.PI / 2; bay.position.y = -97;
    this.group.add(bay);
    // the far hills as a dark silhouette against the sky
    const hills = new THREE.Mesh(new THREE.CylinderGeometry(3200, 3200, 260, 64, 1, true, Math.PI * 0.6, Math.PI * 0.9),
      new THREE.MeshBasicMaterial({ color: '#0b0f16', side: THREE.BackSide, fog: false }));
    hills.position.y = -60;
    this.group.add(hills);
  }

  water(x, z) {
    // the bay wraps the city's north and east; Telegraph Hill and the waterfront end around here
    return z < -620 + 0.18 * x || x > 900 - 0.3 * z;
  }

  update(dt, t, focus, camera, holmes) {
    // give the gas lights to the lamps nearest Holmes (and on his floor)
    const p = holmes;
    const near = this.lamps
      .map(l => [l, l.distanceToSquared(p) + (Math.abs(l.y - p.y) > 12 ? 1e4 : 0)])
      .sort((a, b) => a[1] - b[1]);
    this.gas.forEach((g, i) => {
      const n = near[i];
      if (!n) { g.intensity = 0; return; }
      g.position.copy(n[0]);
      const flick = 1 + Math.sin(t * 9 + i * 1.7) * 0.03;
      g.intensity = (n[0].y > 8 ? 30 : 16) * flick;
      g.distance = n[0].y > 8 ? 22 : 13;
    });
  }
}
