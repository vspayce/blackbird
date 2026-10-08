// Stylised low-poly people. Characters built in Blender (art/build_characters.py)
// load from public/models/<name>.glb as a hierarchy of pivots (hips, torso,
// head, leg_R/leg_L, arm_R/arm_L); anyone without a model is built from
// primitives with the same pivots, so the animation code drives both.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const models = new Map();

// Load models before building figures; a missing model falls back to primitives.
export function loadModels(names) {
  const loader = new GLTFLoader();
  return Promise.all(names.map(n => loader.loadAsync(`models/${n}.glb`)
    .then(g => models.set(n, g.scene))
    .catch(e => console.warn(`model ${n} not loaded, using primitives`, e))));
}

function fromModel(src, o) {
  const root = src.clone(true);
  const get = n => root.getObjectByName(n);
  const body = get('body');
  body.scale.setScalar((o.height ?? 1.8) / 1.8);
  return withAnimation({ root, body, hips: get('hips'), torso: get('torso'), head: get('head'),
    legs: [get('leg_R'), get('leg_L')], arms: [get('arm_R'), get('arm_L')] });
}

const mats = new Map();
function mat(color, rough = 0.85) {
  const k = color + ':' + rough;
  if (!mats.has(k)) mats.set(k, new THREE.MeshStandardMaterial({ color, roughness: rough, side: THREE.DoubleSide }));
  return mats.get(k);
}

function mesh(geo, m, x = 0, y = 0, z = 0) {
  const o = new THREE.Mesh(geo, m);
  o.position.set(x, y, z);
  return o;
}

function hat(type, color) {
  const g = new THREE.Group();
  const m = mat(color, 0.9);
  if (type === 'deerstalker') {
    const crown = mesh(new THREE.SphereGeometry(0.125, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), m);
    crown.scale.set(1, 0.85, 1.12);
    g.add(crown);
    for (const s of [1, -1]) {
      const peak = mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.012, 10, 1, false, 0, Math.PI), m, 0, 0.005, s * 0.11);
      peak.rotation.y = s > 0 ? -Math.PI / 2 : Math.PI / 2;
      peak.scale.set(1, 1, 1.0);
      g.add(peak);
    }
    // the ear flaps tied up on top
    g.add(mesh(new THREE.BoxGeometry(0.06, 0.02, 0.03), m, 0, 0.11, 0));
  } else if (type === 'bowler') {
    const crown = mesh(new THREE.SphereGeometry(0.12, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), m);
    crown.scale.set(1, 1.05, 1.08);
    g.add(crown);
    g.add(mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.012, 16), m, 0, 0.004, 0));
  } else if (type === 'helmet') {
    const crown = mesh(new THREE.SphereGeometry(0.13, 12, 10, 0, Math.PI * 2, 0, Math.PI / 1.7), m);
    crown.scale.set(1, 1.5, 1.1);
    g.add(crown);
    g.add(mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.015, 16), m));
    g.add(mesh(new THREE.SphereGeometry(0.018, 6, 4), mat('#c9a04a', 0.4), 0, 0.12, 0.12));
  } else if (type === 'ladies') {
    g.add(mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.012, 16), m));
    g.add(mesh(new THREE.CylinderGeometry(0.09, 0.11, 0.08, 12), m, 0, 0.04, 0));
    g.add(mesh(new THREE.SphereGeometry(0.035, 6, 5), mat('#5f7aa8', 0.6), 0.08, 0.06, 0.04));
  }
  return g;
}

// o: { height, coat, trousers, skin, hair, hat, hatColor, longCoat, cape, moustache, skirt, buttons }
export function createFigure(o = {}) {
  if (o.model && models.has(o.model)) return fromModel(models.get(o.model), o);
  const s = (o.height ?? 1.8) / 1.8;
  const root = new THREE.Group();
  const body = new THREE.Group();
  body.scale.setScalar(s);
  root.add(body);

  const coat = mat(o.coat ?? '#3a3a3a');
  const trousers = mat(o.trousers ?? '#2a2622');
  const skin = mat(o.skin ?? '#d9b49a', 0.7);
  const shoe = mat('#141110', 0.5);

  const hips = new THREE.Group(); hips.position.y = 0.92; body.add(hips);

  const legs = [];
  for (const side of [-1, 1]) {
    const leg = new THREE.Group(); leg.position.x = side * 0.1; hips.add(leg);
    leg.add(mesh(new THREE.CapsuleGeometry(0.072, 0.72, 4, 8), o.skirt ? mat(o.skirt) : trousers, 0, -0.44, 0));
    leg.add(mesh(new THREE.BoxGeometry(0.1, 0.07, 0.25), shoe, 0, -0.885, 0.04));
    legs.push(leg);
  }

  const torso = new THREE.Group(); hips.add(torso);
  torso.add(mesh(new THREE.CylinderGeometry(0.2, 0.165, 0.62, 12), coat, 0, 0.32, 0));
  if (o.longCoat) torso.add(mesh(new THREE.CylinderGeometry(0.18, 0.27, 0.66, 12, 1, true), coat, 0, -0.3, 0));
  if (o.skirt) torso.add(mesh(new THREE.CylinderGeometry(0.17, 0.34, 0.86, 14, 1, true), mat(o.skirt), 0, -0.42, 0));
  if (o.cape) torso.add(mesh(new THREE.CylinderGeometry(0.17, 0.38, 0.4, 14, 1, true), coat, 0, 0.47, 0));
  if (o.buttons) {
    const b = mat('#16120e', 0.4);
    for (let i = 0; i < 4; i++) torso.add(mesh(new THREE.SphereGeometry(0.016, 6, 4), b, 0.02, 0.52 - i * 0.12, 0.19 - i * 0.004));
  }

  const arms = [];
  for (const side of [-1, 1]) {
    const arm = new THREE.Group(); arm.position.set(side * 0.24, 0.58, 0); torso.add(arm);
    arm.add(mesh(new THREE.CapsuleGeometry(0.058, 0.5, 4, 8), coat, 0, -0.3, 0));
    arm.add(mesh(new THREE.SphereGeometry(0.048, 8, 6), o.gloves ? mat(o.gloves, 0.6) : skin, 0, -0.62, 0));
    arms.push(arm);
  }

  const head = new THREE.Group(); head.position.y = 0.68; torso.add(head);
  head.add(mesh(new THREE.CylinderGeometry(0.05, 0.055, 0.1, 8), skin, 0, 0.0, 0));
  const skull = mesh(new THREE.SphereGeometry(0.105, 14, 10), skin, 0, 0.13, 0);
  skull.scale.set(0.92, 1.12, 1);
  head.add(skull);
  const nose = mesh(new THREE.ConeGeometry(0.02, 0.05, 6), skin, 0, 0.12, 0.105);
  nose.rotation.x = Math.PI / 2;
  head.add(nose);
  if (o.hair) {
    const hair = mesh(new THREE.SphereGeometry(0.11, 12, 8, 0, Math.PI * 2, 0, Math.PI / 1.8), mat(o.hair, 0.9), 0, 0.15, -0.012);
    hair.scale.set(0.96, 1.1, 1.04);
    head.add(hair);
  }
  if (o.moustache) head.add(mesh(new THREE.BoxGeometry(0.08, 0.018, 0.02), mat(o.moustache, 0.9), 0, 0.085, 0.1));
  if (o.hat) {
    const h = hat(o.hat, o.hatColor ?? '#2b2520');
    h.position.y = 0.21;
    head.add(h);
  }

  return withAnimation({ root, body, hips, legs, arms, torso, head });
}

function withAnimation(parts) {
  const { hips, legs, arms, torso } = parts;
  const hipY = hips.position.y;
  let phase = Math.random() * 10;

  // speed in m/s; 0 = idle
  function animate(dt, speed, t) {
    const walk = Math.min(1, speed / 1.4);
    phase += dt * (2.4 + speed * 2.2);
    const sw = Math.sin(phase);
    legs[0].rotation.x = sw * 0.55 * walk;
    legs[1].rotation.x = -sw * 0.55 * walk;
    arms[0].rotation.x = -sw * 0.4 * walk;
    arms[1].rotation.x = sw * 0.4 * walk;
    hips.position.y = hipY + Math.abs(Math.cos(phase)) * 0.035 * walk;
    // breathing when still
    torso.rotation.x = 0.03 * walk + Math.sin(t * 1.3) * 0.012 * (1 - walk);
  }

  return { ...parts, animate, object: parts.root };
}
