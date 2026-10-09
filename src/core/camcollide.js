// Keeps the follow camera out of walls and props. Rays go from the point it looks at (Holmes's head) to the
// corners and centre of a small box round where the camera wants to be, against the world's real geometry (not
// just the walking colliders, which leave out door frames, beams, lamps and furniture). A BVH per mesh keeps
// that cheap enough for phones.
import * as THREE from 'three';
import { computeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh';

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

const ray = new THREE.Raycaster();
ray.firstHitOnly = true;
const _to = new THREE.Vector3(), _d = new THREE.Vector3(), _r = new THREE.Vector3(), _u = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);

function shown(o) {
  for (; o; o = o.parent) if (!o.visible) return false;
  return true;
}

export class CameraCollider {
  // skip: the roots of things the camera may pass through (people, Holmes)
  constructor(scene, skip) {
    const skipSet = new Set(skip);
    this.meshes = [];
    scene.traverse(o => {
      if (!o.isMesh || o.isSkinnedMesh || o.isInstancedMesh || o.userData.noOcclude) return;
      for (let p = o; p; p = p.parent) if (skipSet.has(p)) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      if (mats.every(m => m.transparent || !m.visible || m.depthWrite === false)) return;  // fog, halos, glass sheets
      if (!o.geometry.boundsTree) o.geometry.computeBoundsTree();
      this.meshes.push(o);
    });
  }

  // How far back along dir (unit) from target the camera can sit, at most `want`, keeping `pad` clear of a hit.
  // half: half the width and height of the box round the camera (the near plane, and a little more).
  limit(target, dir, want, pad = 0.22, half = 0.2) {
    const live = this.meshes.filter(shown);
    if (!live.length) return want;
    _r.crossVectors(dir, UP);
    if (_r.lengthSq() < 1e-6) _r.set(1, 0, 0);
    _r.normalize();
    _u.crossVectors(_r, dir).normalize();
    let best = want;
    for (const [a, b] of [[0, 0], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      _to.copy(target).addScaledVector(dir, want).addScaledVector(_r, a * half).addScaledVector(_u, b * half * 0.7);
      _d.subVectors(_to, target);
      const len = _d.length();
      ray.set(target, _d.divideScalar(len));
      ray.far = len + pad;
      const hit = ray.intersectObjects(live, false)[0];
      if (hit) best = Math.min(best, (hit.distance - pad) / len * want);
    }
    return best;
  }
}
