# Procedural animation for the cast (used by art/polish_humans.py; build_humans.py can call make_all_clips too).
#
# Every clip is a function of time that poses a small skeleton solver (no depsgraph: plain matrix maths), sampled
# on every frame and written straight into an Action. Feet and (where it matters) hands are placed by two-bone IK,
# so planted feet stay planted. The character faces -Y, +X is his left, +Z is up; one Blender unit is a metre.
#
# Contracts kept for the games:
#   - bone names, hierarchy and rest pose are untouched; only pose-bone rotations and the pelvis location are keyed
#     (the Root bone never moves: every clip is IN PLACE);
#   - clip names Idle, Walk, Talk, LieBack, Aim, HandsUp as before; new ones are listed in CLIPS below;
#   - rig['walk_speed'] / rig['run_speed'] (m/s) are the ground speeds the Walk and Run cycles are authored for.
import math, random
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion

FPS = 30
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
FWD = Vector((0, -1, 0))
TAU = 2 * math.pi


def clamp01(x): return max(0.0, min(1.0, x))
def smooth(x): x = clamp01(x); return x * x * (3 - 2 * x)
def smoother(x): x = clamp01(x); return x * x * x * (x * (6 * x - 15) + 10)
def lerp(a, b, t): return a + (b - a) * t
def pulse(t, a, b, c, d):
    """0 -> 1 between a and b, held, 1 -> 0 between c and d (eased)."""
    return smoother((t - a) / max(1e-6, b - a)) * (1 - smoother((t - c) / max(1e-6, d - c)))
def hermite(w, p0, p1, m0, m1):
    w2, w3 = w * w, w * w * w
    return (2 * w3 - 3 * w2 + 1) * p0 + (w3 - 2 * w2 + w) * m0 + (-2 * w3 + 3 * w2) * p1 + (w3 - w2) * m1


def wob(t, T, seed, n=3, lo=1):
    """Loopable wobble in [-1, 1]: a few sines with whole numbers of cycles in T and seeded phases."""
    r = random.Random(seed)
    s = tot = 0.0
    for k in range(n):
        a = 1.0 / (1 + k * 0.8)
        s += a * math.sin(TAU * ((lo + k) * t / T + r.random()))
        tot += a
    return s / tot


def frame3(y, f):
    """Orthonormal frame with its Y along y and its Z as near f as it can be (columns s, y, f)."""
    y = Vector(y).normalized()
    f = Vector(f) - y * Vector(f).dot(y)
    if f.length < 1e-5:
        f = y.orthogonal()
    f.normalize()
    s = y.cross(f)
    return Matrix((s, y, f)).transposed()


def rx(a): return Matrix.Rotation(a, 3, 'X')
def ry(a): return Matrix.Rotation(a, 3, 'Y')
def rz(a): return Matrix.Rotation(a, 3, 'Z')


def world_co(o):
    """Vertex positions of a mesh object in world (= armature) space, as an (n, 3) array. The cast's meshes carry
    the height scale on the object, so raw vertex coordinates are not metres."""
    arr = np.empty(len(o.data.vertices) * 3, dtype=np.float32)
    o.data.vertices.foreach_get('co', arr)
    M = np.array(o.matrix_world)
    return arr.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


class Skel:
    def __init__(self, rig):
        B = rig.data.bones
        self.order = []
        def walk(b):
            self.order.append(b.name)
            for c in b.children: walk(c)
        for b in B:
            if not b.parent: walk(b)
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in B}
        self.rest = {b.name: b.matrix_local.copy() for b in B}
        self.rest3 = {n: m.to_3x3() for n, m in self.rest.items()}
        self.rel = {n: (self.rest[p].inverted() @ self.rest[n]) if p else self.rest[n].copy()
                    for n, p in self.parent.items()}
        self.head = {b.name: b.head_local.copy() for b in B}
        self.tail = {b.name: b.tail_local.copy() for b in B}
        self.desc = {n: [] for n in self.order}
        for n in self.order:
            p = self.parent[n]
            while p:
                self.desc[p].append(n); p = self.parent[p]


class Pose:
    def __init__(self, sk):
        self.sk = sk; self.q = {}; self.loc = {}; self._w = {}

    def W(self, b):
        m = self._w.get(b)
        if m is None:
            p = self.sk.parent[b]
            m = (self.W(p) @ self.sk.rel[b]) if p else self.sk.rel[b].copy()
            l = self.loc.get(b)
            if l is not None: m = m @ Matrix.Translation(l)
            q = self.q.get(b)
            if q is not None: m = m @ q.to_matrix().to_4x4()
            self._w[b] = m
        return m

    def _dirty(self, b):
        self._w.pop(b, None)
        for d in self.sk.desc[b]: self._w.pop(d, None)

    def pos(self, b): return self.W(b).to_translation()
    def R(self, b): return self.W(b).to_3x3()
    def point(self, b, rest_point):
        """Where a point given in armature rest space, carried by bone b, is now."""
        return self.W(b) @ (self.sk.rest[b].inverted() @ Vector(rest_point))
    def carried(self, b, rest_dir):
        return self.R(b) @ (self.sk.rest3[b].inverted() @ Vector(rest_dir))

    def _parent3(self, b):
        p = self.sk.parent[b]
        m = (self.W(p) @ self.sk.rel[b]) if p else self.sk.rel[b]
        return m.to_3x3()

    def rot(self, b, axis, ang):
        """Turn the bone about an armature-space axis, on top of however it is posed now."""
        if abs(ang) < 1e-9: return
        W3 = self.R(b)
        d = (W3.inverted() @ Matrix.Rotation(ang, 3, Vector(axis).normalized()) @ W3).to_quaternion()
        self.q[b] = self.q.get(b, Quaternion()) @ d
        self._dirty(b)

    def local(self, b, axis, ang):
        """Turn the bone about an axis fixed in its parent, given as it lies in the rest pose (a hinge)."""
        if abs(ang) < 1e-9: return
        M = self.sk.rest3[b]
        d = (M.inverted() @ Matrix.Rotation(ang, 3, Vector(axis).normalized()) @ M).to_quaternion()
        self.q[b] = d @ self.q.get(b, Quaternion())
        self._dirty(b)

    def twist(self, b, ang):
        if abs(ang) < 1e-9: return
        self.q[b] = self.q.get(b, Quaternion()) @ Quaternion((0, 1, 0), ang)
        self._dirty(b)

    def set_world(self, b, R3):
        self.q[b] = (self._parent3(b).inverted() @ R3).to_quaternion()
        self._dirty(b)

    def blend_world(self, b, R3, w):
        cur = self.R(b).to_quaternion()
        self.set_world(b, cur.slerp(R3.to_quaternion(), w).to_matrix())

    def move(self, b, v):
        """Offset the bone from its rest place by v (armature space)."""
        self.loc[b] = self._parent3(b).inverted() @ Vector(v)
        self._dirty(b)

    def orient(self, b, ydir, hint, rest_hint=FWD):
        """Point the bone along ydir with its rest-forward side kept toward hint (no stray twist)."""
        R = frame3(ydir, hint) @ frame3(self.sk.rest3[b].col[1], rest_hint).transposed()
        self.set_world(b, R @ self.sk.rest3[b])


# ---------------------------------------------------------------------------------------------------------------
# The character: measurements taken from the rig and meshes, a style, and the body mechanics shared by all clips.

HAND = dict(  # finger curls index..pinky, thumb curl, spread
    relax=((0.28, 0.36, 0.44, 0.52), 0.22, 0.0),
    soft=((0.42, 0.55, 0.64, 0.72), 0.3, 0.0),
    open=((0.05, 0.07, 0.1, 0.16), 0.02, 0.06),
    splay=((0.02, 0.02, 0.04, 0.08), -0.1, 0.14),
    fist=((1.25, 1.35, 1.4, 1.4), 0.65, 0.0),
    grip=((1.2, 1.25, 1.3, 1.32), 0.6, 0.0),
    point=((0.03, 1.3, 1.4, 1.42), 0.75, 0.0),
    pinch=((0.85, 0.95, 1.1, 1.2), 0.55, 0.0),
    cup=((0.5, 0.6, 0.66, 0.7), 0.35, 0.0),
    dead=((0.5, 0.62, 0.72, 0.8), 0.32, 0.03),
    hold=((0.75, 0.82, 0.86, 0.9), 0.1, 0.02),
)

STYLES = {
    # walk: v m/s, n frames per two steps; run likewise. posture: chest (- = out), stoop, head pitch (+ = down)
    'default': dict(walk=dict(v=1.3, n=32), run=dict(v=3.3, n=20), chest=-0.02, stoop=0.0, head=0.0, shoulders=0.0,
                    arm_abd=0.03, width=0.62, toe_out=0.1, arm=0.36, bounce=0.02, sway=0.02, hip_yaw=0.085,
                    chest_yaw=0.07, lean=0.03, lift=0.05, idle_shift=1.0, idle_look=1.0, talk=1.0, elbow=0.2),
    'holmes': dict(walk=dict(v=1.4, n=30), run=dict(v=3.6, n=20), chest=-0.045, head=-0.03, shoulders=0.03,
                   arm=0.34, bounce=0.018, sway=0.016, lean=0.035, idle_look=1.25, talk=1.1, width=0.55),
    'watson': dict(walk=dict(v=1.3, n=32), run=dict(v=3.3, n=20), chest=-0.06, shoulders=0.05, arm=0.42,
                   sway=0.022, bounce=0.02, toe_out=0.14, lean=0.02, idle_shift=0.8, elbow=0.12, width=0.7),
    'polhaus': dict(walk=dict(v=1.25, n=34), run=dict(v=3.1, n=22), chest=-0.03, arm=0.3, sway=0.03, bounce=0.022,
                    toe_out=0.17, width=0.85, arm_abd=0.07, lean=0.02, hip_yaw=0.07, idle_shift=1.1),
    'kelly': dict(walk=dict(v=1.35, n=30), run=dict(v=3.6, n=20), chest=-0.05, shoulders=0.04, arm=0.4,
                  lean=0.03, idle_shift=0.7, talk=0.8, elbow=0.14),
    'archer': dict(walk=dict(v=1.3, n=32), run=dict(v=3.3, n=20), arm_abd=0.05, width=0.75),
    'wilmer': dict(walk=dict(v=1.3, n=28), run=dict(v=3.5, n=18), chest=0.03, stoop=0.05, head=0.06, arm=0.26,
                   lean=0.06, sway=0.024, shoulders=-0.05, idle_look=1.4, talk=0.8, elbow=0.3),
    'cairo': dict(walk=dict(v=1.15, n=28), run=dict(v=3.0, n=20), chest=-0.03, arm=0.22, sway=0.026, bounce=0.014,
                  hip_yaw=0.11, toe_out=0.05, width=0.4, lift=0.04, elbow=0.42, talk=1.25, idle_look=1.2),
    'brigid': dict(walk=dict(v=0.95, n=30), run=dict(v=2.5, n=22), chest=-0.04, head=-0.02, arm=0.14, sway=0.028,
                   bounce=0.01, hip_yaw=0.1, chest_yaw=0.04, toe_out=0.04, width=0.38, lift=0.035, elbow=0.5,
                   arm_abd=0.05, lean=0.015, talk=0.9, lady=True),
    'gutman': dict(walk=dict(v=0.9, n=40), run=dict(v=1.9, n=26), chest=-0.08, head=-0.04, arm=0.2, sway=0.042,
                   bounce=0.012, hip_yaw=0.06, chest_yaw=0.09, toe_out=0.24, width=1.15, lift=0.04, arm_abd=0.1,
                   lean=-0.03, idle_shift=1.2, talk=1.3, elbow=0.3, heavy=True),
    'wren': dict(walk=dict(v=0.95, n=36), run=dict(v=1.8, n=28), chest=0.05, stoop=0.12, head=-0.02, arm=0.2,
                 bounce=0.01, sway=0.022, lift=0.03, lean=0.05, toe_out=0.12, width=0.7, idle_shift=0.7,
                 talk=0.85, elbow=0.34, old=True),
}


class Char:
    def __init__(self, rig, name):
        self.rig, self.name = rig, name
        self.sk = sk = Skel(rig)
        self.st = {**STYLES['default'], **STYLES.get(name, {})}
        self.seed = sum(ord(ch) for ch in name)
        h = sk.head
        self.legs = {}
        meshes = [o for o in rig.children if o.type == 'MESH']
        shoe = next((o for o in meshes if 'shoes' in o.name), None)
        shoe_co = world_co(shoe) if shoe else None
        sole = float(shoe_co[:, 2].min()) if shoe else 0.0
        self.ground = sole
        for s in 'lr':
            A, K, Hh, B = h[f'foot_{s}'], h[f'calf_{s}'], h[f'thigh_{s}'], h[f'ball_{s}']
            heel_y = A.y + 0.06
            toe_y = sk.tail[f'ball_{s}'].y - 0.02
            if shoe:
                ys = shoe_co[((shoe_co[:, 0] > 0) == (s == 'l')) & (shoe_co[:, 2] < A.z), 1]
                if len(ys): heel_y, toe_y = float(ys.max()) - 0.012, float(ys.min()) + 0.01
            self.legs[s] = dict(L1=(K - Hh).length, L2=(A - K).length, A=A.copy(), B=Vector((A.x, B.y, sole + 0.012)),
                                heel=Vector((A.x, heel_y, sole + 0.004)), toe=Vector((A.x, toe_y, sole + 0.01)), H=Hh.copy())
        self.arms = {}
        for s in 'lr':
            S, E, Wr = h[f'upperarm_{s}'], h[f'lowerarm_{s}'], h[f'hand_{s}']
            g0 = (h[f'middle_01_{s}'] - Wr).normalized()
            axis = (h[f'index_01_{s}'] - h[f'pinky_01_{s}']).normalized()
            palm = axis.cross(g0).normalized()
            if palm.dot(h[f'thumb_01_{s}'] - h[f'middle_01_{s}']) < 0: axis = -axis
            # the palm faces the body's midline when the arm hangs
            inward = Vector((-1 if s == 'l' else 1, 0, 0))
            p0 = (inward - g0 * inward.dot(g0)).normalized()
            t0 = (sk.tail[f'thumb_03_{s}'] - h[f'thumb_02_{s}']).normalized()
            t_add = 1 if t0.cross(g0).dot(p0) > 0 else -1
            t_opp = 1 if g0.cross(t0).dot(p0) > 0 else -1
            self.arms[s] = dict(t_add=t_add, t_opp=t_opp, L1=(E - S).length, L2=(Wr - E).length, S=S.copy(), W=Wr.copy(), g0=g0, p0=p0,
                                axis=axis, sign=(1 if s == 'l' else -1),
                                hand_len=(sk.tail[f'middle_03_{s}'] - Wr).length)
        self.hipw = abs(h['thigh_l'].x)
        self.head_len = (sk.tail['head'] - h['head']).length
        self.scale = self.head_len / 0.155
        # silhouette of the clothed body at rest: how far forward (-Y) the front is, and the back, by height
        zs, fr, bk = [], [], []
        pts = []
        for o in meshes:
            if any(k in o.name for k in ('Cane', 'Skirt')): continue
            pts.append(world_co(o))
        pts = np.concatenate(pts)
        self._prof = []
        for z in np.arange(0.5, h['neck_01'].z, 0.04):
            m = (np.abs(pts[:, 2] - z) < 0.03) & (np.abs(pts[:, 0]) < 0.1)
            if m.any(): self._prof.append((float(z), float(pts[m, 1].min()), float(pts[m, 1].max())))
        m = (pts[:, 2] > h['pelvis'].z) & (pts[:, 2] < h['neck_01'].z) & (np.abs(pts[:, 0]) < 0.12)
        self.back_y = float(np.percentile(pts[m, 1], 99.5))
        m = (pts[:, 2] > h['thigh_l'].z - 0.25) & (pts[:, 2] < h['spine_03'].z)
        self.side_x = float(np.percentile(np.abs(pts[m, 0]), 97))   # includes the hanging arms
        # the cane, if he carries one: where its tip is at rest and which hand has it
        self.cane = None
        for o in meshes:
            if o.name == 'CaneFerrule':
                side = 'l' if any(g.name == 'hand_l' for g in o.vertex_groups) else 'r'
                co = world_co(o)
                tip = Vector(co[co[:, 2] < co[:, 2].min() + 0.004].mean(axis=0).tolist())
                self.cane = dict(side=side, tip=tip.copy(), wrist=h[f'hand_{side}'].copy())
        if self.cane:
            self.cane['len'] = (self.cane['tip'] - self.cane['wrist']).length
            self.cane['dir'] = (self.cane['tip'] - self.cane['wrist']).normalized()

    # -- measurements ------------------------------------------------------------------------------------------
    def front(self, z):
        """Y of the front surface of the clothed trunk at height z (rest pose)."""
        best = min(self._prof, key=lambda r: abs(r[0] - z))
        return best[1]

    def pose(self): return Pose(self.sk)

    # -- hands ---------------------------------------------------------------------------------------------------
    def fingers(self, P, s, shape='relax', mix=None, k=0.0, wiggle=0.0):
        """shape: a HAND preset; mix/k blends toward a second preset; wiggle adds a little to every curl."""
        a = self.arms[s]
        curls, thumb, spread = HAND[shape]
        if mix:
            c2, t2, s2 = HAND[mix]
            curls = [lerp(x, y, k) for x, y in zip(curls, c2)]; thumb = lerp(thumb, t2, k); spread = lerp(spread, s2, k)
        if self.cane and self.cane['side'] == s:
            curls, thumb, spread = HAND['grip']; wiggle = 0.0
        for i, f in enumerate(('index', 'middle', 'ring', 'pinky')):
            c = max(-0.05, curls[i] + wiggle * (1 + 0.3 * i))
            for j, kk in ((1, 0.85), (2, 1.0), (3, 0.7)):
                P.local(f'{f}_0{j}_{s}', a['axis'], c * kk)
            if spread: P.local(f'{f}_01_{s}', a['p0'], a['sign'] * spread * (i - 1.3))
        # the thumb: brought in beside the index (adduction, in the plane of the palm), rolled toward the palm
        # (opposition), and its two end joints bent
        add, opp, flex = (0.18 + 0.5 * thumb, 0.9 * thumb, 0.85 * thumb) if thumb >= 0 else (thumb, 0.0, 0.0)
        P.local(f'thumb_01_{s}', a['p0'], a['t_add'] * add)
        P.local(f'thumb_01_{s}', a['g0'], a['t_opp'] * opp)
        P.local(f'thumb_02_{s}', a['p0'], a['t_add'] * flex * 0.6)
        P.local(f'thumb_03_{s}', a['p0'], a['t_add'] * flex)

    def hand_world(self, P, s, fingers_dir, palm_dir, share=0.55):
        """Orient the hand: fingers along one direction, palm facing another; part of the turn goes into the
        forearm (pronation) rather than all into the wrist."""
        a = self.arms[s]
        hb, fb = f'hand_{s}', f'lowerarm_{s}'
        R = frame3(fingers_dir, palm_dir) @ frame3(a['g0'], a['p0']).transposed()
        target = R @ self.sk.rest3[hb]
        P.set_world(hb, target)
        q = P.q[hb]
        tw = Quaternion((q.w, 0, q.y, 0))
        if tw.magnitude > 1e-6:
            tw.normalize()
            ang = 2 * math.atan2(tw.y, tw.w)
            if ang > math.pi: ang -= TAU
            if ang < -math.pi: ang += TAU
            P.twist(fb, ang * share)
            P.set_world(hb, target)

    # -- limbs ---------------------------------------------------------------------------------------------------
    def leg(self, P, s, ankle, pitch=0.0, yaw=0.0, toe_pitch=None, pole=None, roll=0.0):
        """Two-bone IK: put the ankle at a point, knee toward pole (default: forward, turned with the foot)."""
        L = self.legs[s]
        Hp = P.pos(f'thigh_{s}')
        d = Vector(ankle) - Hp
        dist = min(d.length, (L['L1'] + L['L2']) * 0.9995)
        u = d.normalized()
        pole = Vector(pole) if pole is not None else rz(yaw * 0.6) @ FWD
        w = pole - u * pole.dot(u)
        if w.length < 1e-5: w = FWD - u * FWD.dot(u)
        w.normalize()
        ca = (L['L1'] ** 2 + dist ** 2 - L['L2'] ** 2) / (2 * L['L1'] * dist)
        a = math.acos(max(-1, min(1, ca)))
        K = Hp + (u * math.cos(a) + w * math.sin(a)) * L['L1']
        A = Hp + u * dist
        P.orient(f'thigh_{s}', K - Hp, w + u * 0.001)
        P.orient(f'calf_{s}', A - K, (K - Hp).normalized() + w * 0.25)
        Rf = rz(yaw) @ ry(roll) @ rx(pitch)
        P.set_world(f'foot_{s}', Rf @ self.sk.rest3[f'foot_{s}'])
        tp = pitch if toe_pitch is None else toe_pitch
        P.set_world(f'ball_{s}', rz(yaw) @ ry(roll) @ rx(tp) @ self.sk.rest3[f'ball_{s}'])
        return A

    def foot_on(self, s, y, pitch, yaw=0.0, x=None):
        """Ankle position for a foot whose flat-on-the-ground ankle would be at (x, y), rolled onto the heel
        (pitch < 0) or up on the ball (pitch > 0)."""
        L = self.legs[s]
        A0 = L['A']
        x = A0.x if x is None else x
        piv = L['heel'] if pitch < 0 else L['B']
        off = rz(yaw) @ rx(pitch) @ (A0 - piv)
        base = Vector((x, y, 0)) + rz(yaw) @ Vector((0, piv.y - A0.y, 0))
        return Vector((base.x + off.x, base.y + off.y, piv.z + off.z))

    def arm_ik(self, P, s, wrist, pole=None, bend=None):
        """Two-bone IK for the arm: wrist to a point, elbow toward pole (default down, back and a little out)."""
        a = self.arms[s]
        Sp = P.pos(f'upperarm_{s}')
        d = Vector(wrist) - Sp
        dist = min(d.length, (a['L1'] + a['L2']) * 0.999)
        dist = max(dist, abs(a['L1'] - a['L2']) + 0.02)
        u = d.normalized()
        pole = Vector(pole) if pole is not None else Vector((a['sign'] * 0.5, 0.6, -0.7))
        w = pole - u * pole.dot(u)
        if w.length < 1e-5: w = u.orthogonal()
        w.normalize()
        ca = (a['L1'] ** 2 + dist ** 2 - a['L2'] ** 2) / (2 * a['L1'] * dist)
        ang = math.acos(max(-1, min(1, ca)))
        E = Sp + (u * math.cos(ang) + w * math.sin(ang)) * a['L1']
        Wp = Sp + u * dist
        P.orient(f'upperarm_{s}', E - Sp, (Wp - E).normalized() - w * 0.02)
        P.orient(f'lowerarm_{s}', Wp - E, -(E - Sp).normalized() - w * 0.25)
        return Wp

    def arm_fk(self, P, s, swing=0.0, abd=0.0, twist=0.0, elbow=0.0, wrist=0.0, wrist_side=0.0, pron=0.0):
        """Angles relative to the chest: swing forward, abduct out, twist the forearm inward across the body,
        bend the elbow; wrist flex (+ = palm side) and pronation."""
        a = self.arms[s]; sg = a['sign']
        up, lo, hd = f'upperarm_{s}', f'lowerarm_{s}', f'hand_{s}'
        P.local(up, Y, -sg * abd)
        P.local(up, X, -swing)
        P.twist(up, sg * twist)
        P.local(lo, X, -elbow)
        if pron: P.twist(lo, sg * pron)
        if wrist: P.local(hd, a['axis'], wrist)
        if wrist_side: P.local(hd, a['p0'], wrist_side)

    def cane_arm(self, P, tip, wrist_hint, pole=None):
        """Hold the cane with its tip at a point: the wrist goes on the sphere of the cane's length about the tip,
        as near wrist_hint as it can; the hand turns to carry the cane along that line."""
        c = self.cane; s = c['side']
        tip = Vector(tip)
        d = (Vector(wrist_hint) - tip).normalized()
        wrist = tip + d * c['len']
        a = self.arms[s]
        Sp = P.pos(f'upperarm_{s}')
        reach = (a['L1'] + a['L2']) * 0.985
        if (wrist - Sp).length > reach:   # the nearest point to the hint that the arm can reach with the tip down
            ax = Sp - tip; dd = ax.length; ax.normalize()
            if dd < c['len'] + reach:
                al = (c['len'] ** 2 - reach ** 2 + dd * dd) / (2 * dd)
                hh = math.sqrt(max(0.0, c['len'] ** 2 - al * al))
                pc = tip + ax * al
                v = Vector(wrist_hint) - pc; v -= ax * v.dot(ax)
                if v.length > 1e-6: wrist = pc + v.normalized() * hh
        Wp = self.arm_ik(P, s, wrist, pole or Vector((self.arms[s]['sign'] * 0.35, 1, -0.25)))
        d = (Wp - tip).normalized()
        hb = f'hand_{s}'
        Rd = c['dir'].rotation_difference(-d).to_matrix()
        P.set_world(hb, Rd @ self.sk.rest3[hb])
        self.fingers(P, s, 'grip')

    def head(self, P, yaw=0.0, pitch=0.0, roll=0.0, w=1.0):
        """Aim the head in armature space (yaw + = to his left, pitch + = down, roll + = toward his left
        shoulder), blended over whatever the spine has done to it by w."""
        hp = pitch + self.st['head']
        P.blend_world('neck_01', rz(yaw * 0.4) @ ry(roll * 0.3) @ rx(hp * 0.4 + self.st['stoop'] * 0.6) @ self.sk.rest3['neck_01'], w)
        P.blend_world('head', rz(yaw) @ ry(roll) @ rx(hp) @ self.sk.rest3['head'], w)

    # -- the standing body -----------------------------------------------------------------------------------------
    def base(self):
        """Parameters of the neutral stance; clips change them over time and hand them to apply()."""
        st = self.st
        return dict(shift=0.0, sink=0.0, fwd=0.0, pel_yaw=0.0, pel_pitch=0.0, pel_list=0.0,
                    lean=0.0, turn=0.0, side=0.0, breath=0.0, shrug_l=0.0, shrug_r=0.0,
                    head=(0.0, 0.0, 0.0), head_w=0.75,
                    arm_l=dict(swing=0.02, abd=st['arm_abd'], twist=0.08, elbow=st['elbow'], wrist=0.05),
                    arm_r=dict(swing=0.02, abd=st['arm_abd'], twist=0.08, elbow=st['elbow'], wrist=0.05),
                    hand_l='relax', hand_r='relax', feet={}, cane=True)

    def apply(self, P, S):
        st = self.st
        sh = S['shift']
        P.move('pelvis', (sh * self.hipw * 0.4, S['fwd'], -0.006 - S['sink'] - 0.006 * abs(sh)))
        P.rot('pelvis', Z, S['pel_yaw'])
        P.rot('pelvis', Y, -0.055 * sh + S['pel_list'])
        P.rot('pelvis', X, S['pel_pitch'])
        br = S['breath']
        lean, turn, side = S['lean'] + st['stoop'], S['turn'], S['side'] + 0.05 * sh
        for b, k in (('spine_01', 0.4), ('spine_02', 0.3), ('spine_03', 0.3)):
            P.rot(b, Z, turn * k - S['pel_yaw'] * 0.0)
            P.rot(b, Y, side * k)
            P.rot(b, X, lean * k)
        P.rot('spine_02', X, -0.012 * br)
        P.rot('spine_03', X, st['chest'] - 0.02 * br)
        for s, sg in (('l', 1), ('r', -1)):
            c = f'clavicle_{s}'
            P.local(c, Y, -sg * (S[f'shrug_{s}'] + 0.014 * br))
            P.local(c, Z, sg * st['shoulders'])
        yaw, pitch, roll = S['head']
        self.head(P, yaw, pitch, roll, S['head_w'])
        for s in 'lr':
            ft = S['feet'].get(s)
            if ft is None:
                self.leg(P, s, self.legs[s]['A'])
            elif callable(ft):
                ft(P)
            else:
                self.leg(P, s, **ft)
        for s in 'lr':
            arm = S[f'arm_{s}']
            if self.cane and self.cane['side'] == s and S['cane']:
                c = self.cane
                tip = S['cane'] if isinstance(S['cane'], (tuple, list, Vector)) else Vector((c['tip'].x + 0.03, c['tip'].y + 0.06, self.ground + 0.005))
                hint = S.get('cane_hint') or (c['wrist'] + Vector((0.03, -0.02, 0.035)) + Vector((sh * 0.012, 0, -S['sink'] * 0.5)))
                if callable(hint): hint = hint(P)
                self.cane_arm(P, tip, hint, S.get('cane_pole'))
                continue
            if callable(arm):
                arm(P)
            elif 'ik' in arm:
                self.arm_ik(P, s, arm['ik'], arm.get('pole'))
                if 'hand' in arm: self.hand_world(P, s, *arm['hand'])
                self.fingers(P, s, S[f'hand_{s}'], *S.get(f'mix_{s}', (None, 0.0)), wiggle=S.get(f'wig_{s}', 0.0))
            else:
                arm = dict(arm)   # a raised shoulder should lift the arm, not swing it out from the body
                arm['abd'] = arm.get('abd', 0.0) - 0.9 * (S[f'shrug_{s}'] + 0.014 * S['breath'])
                self.arm_fk(P, s, **arm)
                self.fingers(P, s, S[f'hand_{s}'], *S.get(f'mix_{s}', (None, 0.0)), wiggle=S.get(f'wig_{s}', 0.0))
        return P


def mix_arm(a, b, k):
    """Blend two FK arm dicts."""
    keys = set(a) | set(b)
    return {x: lerp(a.get(x, 0.0), b.get(x, 0.0), k) for x in keys}


# ---------------------------------------------------------------------------------------------------------------
# Locomotion

def gait_params(c, kind):
    st = c.st
    g = dict(st[kind])
    T = g['n'] / FPS
    if kind == 'walk':
        slow = clamp01((1.3 - g['v']) / 0.5)
        g.update(T=T, beta=0.61 + 0.05 * slow, hs=0.32 - 0.14 * slow, to=0.95 - 0.25 * slow, lift=st['lift'],
                 s1=0.16, s2=0.52, drop=0.028, bounce=st['bounce'], sway=st['sway'], list=0.05 + 0.02 * slow,
                 hip_yaw=st['hip_yaw'], chest_yaw=st['chest_yaw'], lean=st['lean'], arm=st['arm'],
                 elbow0=st['elbow'] * 0.7 + 0.08, elbow1=0.32, width=st['width'], toe_out=st['toe_out'], top=0.3,
                 head_w=0.8, k0=0.9, k1=0.55, fore=-0.02, run=False)
        if st.get('lady'): g.update(hs=0.12, to=0.4, elbow1=0.1, list=0.06, beta=0.66)
    else:
        fast = clamp01((g['v'] - 1.8) / 1.8)
        g.update(T=T, beta=lerp(0.52, 0.32, fast), hs=0.1, to=lerp(0.7, 1.0, fast), lift=lerp(0.1, 0.3, fast),
                 s1=0.1, s2=0.4, drop=lerp(0.035, 0.075, fast), bounce=lerp(0.02, 0.04, fast), sway=st['sway'] * 0.5,
                 list=0.04, hip_yaw=st['hip_yaw'] * 1.5, chest_yaw=st['chest_yaw'] * 1.6,
                 lean=st['lean'] + lerp(0.08, 0.2, fast), arm=lerp(0.4, 0.75, fast) * (0.6 if st.get('lady') else 1),
                 elbow0=lerp(1.0, 1.45, fast), elbow1=0.3, width=st['width'] * 0.6, toe_out=st['toe_out'] * 0.5,
                 top=None, head_w=0.7, k0=1.0, k1=0.8, fore=-0.05 * fast, run=True)
    return g


def foot_path(c, s, u, g):
    """Ankle position (body frame), foot pitch, toe pitch and yaw at cycle phase u; the left foot strikes at 0."""
    L = c.legs[s]
    sg = 1 if s == 'l' else -1
    ph = (u + (0.5 if s == 'r' else 0.0)) % 1.0
    beta, T, v = g['beta'], g['T'], g['v']
    D = v * beta * T
    x = sg * c.hipw * g['width']
    yaw = sg * g['toe_out']
    ymid = L['A'].y + g['fore']
    def stance(sv):
        yflat = ymid + D * (sv - 0.5)
        if sv < g['s1']: pitch = -g['hs'] * (1 - smooth(sv / g['s1']))
        elif sv > g['s2']: pitch = g['to'] * smooth((sv - g['s2']) / (1 - g['s2'])) ** 1.25
        else: pitch = 0.0
        return c.foot_on(s, yflat, pitch, yaw, x), pitch
    if ph < beta:
        A, pitch = stance(ph / beta)
        return A, pitch, min(pitch, 0.0), yaw, True
    w = (ph - beta) / (1 - beta)
    A0, p0 = stance(1.0)
    A1, p1 = stance(0.0)
    Tsw = (1 - beta) * T
    y = hermite(w, A0.y, A1.y, v * Tsw * g['k0'], v * Tsw * g['k1'])
    if g['run']:
        bump = math.sin(math.pi * clamp01(w / 0.9) ** 0.75) ** 1.3
        pitch = lerp(p0, 0.55, smooth(w / 0.3)) * (1 - smooth((w - 0.45) / 0.45)) + p1 * smooth((w - 0.5) / 0.5)
    else:
        bump = math.sin(math.pi * w ** 0.85) ** 1.4
        pitch = p0 * (1 - smooth(w / 0.55)) + p1 * smooth((w - 0.35) / 0.6)
    z = lerp(A0.z, A1.z, smooth(w)) + g['lift'] * bump
    A = Vector((x, y, z))
    # keep the toe and the heel clear of the ground
    for pt in (L['toe'], L['heel']):
        tipz = (A + rz(yaw) @ rx(pitch) @ (pt - L['A'])).z
        need = c.ground + 0.012 * math.sin(math.pi * w) + 0.004
        if tipz < need: A.z += need - tipz
    return A, pitch, lerp(0.0, pitch, smooth(w / 0.3)), yaw, False


def gait_pose(c, P, u, g):
    st = c.st
    cu = math.cos(TAU * u)
    top = g['top'] if g['top'] is not None else g['beta'] / 2 + 0.25   # phase at which the pelvis rides highest
    feet = {s: foot_path(c, s, u, g) for s in 'lr'}
    dz = dz0 = -g['drop'] + g['bounce'] * math.cos(2 * TAU * (u - top))
    sway = g['sway'] * math.cos(TAU * (u - g['beta'] / 2))
    plist = -g['list'] * math.cos(TAU * (u - 0.2))
    pyaw = -g['hip_yaw'] * cu
    for it in range(5):   # no leg may be asked to reach further than it can
        P.q.pop('pelvis', None); P.loc.pop('pelvis', None); P._dirty('pelvis')
        P.move('pelvis', (sway, g['fore'] * 0.5 - 0.012 * math.cos(2 * TAU * (u - 0.1)) * (0 if g['run'] else 1), dz))
        P.rot('pelvis', Z, pyaw); P.rot('pelvis', Y, plist); P.rot('pelvis', X, 0.02 + g['lean'] * 0.3)
        over = 0.0
        for s in 'lr':
            L = c.legs[s]
            d = (feet[s][0] - P.pos(f'thigh_{s}')).length
            over = max(over, d - (L['L1'] + L['L2']) * (0.996 if feet[s][4] else 0.999))
        if over <= 1e-4: break
        dz -= over * 1.6 + 0.001
    g.setdefault('_clamped', []).append(dz0 - dz)
    for s in 'lr':
        A, pitch, toe, yaw, _ = feet[s]
        c.leg(P, s, A, pitch, yaw + pyaw * 0.3, toe)
    # trunk: leans into the walk, counter-turns against the hips, keeps the shoulders nearly level
    cy = (g['hip_yaw'] + g['chest_yaw']) * math.cos(TAU * (u - 0.03))
    for b, k in (('spine_01', 0.3), ('spine_02', 0.35), ('spine_03', 0.35)):
        P.rot(b, Z, cy * k)
        P.rot(b, Y, -plist * 0.85 * k - 0.4 * sway * k)
        P.rot(b, X, (g['lean'] + st['stoop']) * k * 1.2)
    P.rot('spine_03', X, st['chest'] + 0.012 * math.cos(2 * TAU * (u - top - 0.1)))
    c.head(P, 0.12 * g['chest_yaw'] * cu, 0.02 - 0.012 * math.cos(2 * TAU * (u - top - 0.12)) + (0.05 if g['run'] else 0),
           0.0, g['head_w'])
    # arms swing against the legs; the elbow opens behind and closes in front, a beat late, the hand later still
    for s, sg, off in (('l', 1, 0.5), ('r', -1, 0.0)):
        ph = u - off - 0.035
        sw = math.cos(TAU * ph)
        late = math.cos(TAU * (ph - 0.09))
        amp = g['arm']
        if c.cane and c.cane['side'] == s:
            cane_gait(c, P, s, u, g, sw)
            continue
        if st.get('lady'):   # hands carried together at the waist, clear of the skirt; they only give with the step
            k = 0.6 if g['run'] else 0.25
            c.arm_fk(P, s, swing=0.2 + 0.1 * k * sw, abd=0.1, twist=0.8 - 0.1 * k * sw, elbow=1.2 + 0.12 * k * late, wrist=0.15)
            c.fingers(P, s, 'cup')
            continue
        elbow = g['elbow0'] + g['elbow1'] * (0.5 + 0.5 * late) ** 1.5 * (amp / 0.36 if not g['run'] else 1)
        swing = amp * (sw + (0.12 if not g['run'] else -0.25))
        if st.get('lady') and not g['run']: swing += 0.12
        P.local(f'clavicle_{s}', Z, sg * (st['shoulders'] - 0.05 * sw * (2 if g['run'] else 1)))
        c.arm_fk(P, s, swing=swing, abd=st['arm_abd'] + 0.03 * (1 - sw) * 0.5 + (0.1 if g['run'] else 0),
                 twist=0.04 + 0.08 * max(0, sw) + (0.1 if g['run'] else 0), elbow=elbow,
                 wrist=0.1 * math.cos(TAU * (ph - 0.2)) + 0.05)
        c.fingers(P, s, 'soft', 'fist' if g['run'] else 'relax', 0.45, wiggle=0.03 * math.cos(TAU * (ph - 0.25)))


def cane_gait(c, P, s, u, g, sw):
    """The cane hand: the tip goes down with the opposite foot, stays put on the pavement while he walks past it,
    then swings forward. Running, he carries it clear of the ground."""
    a = c.arms[s]; sg = a['sign']; cn = c.cane
    P.local(f'clavicle_{s}', Z, sg * (c.st['shoulders'] - 0.03 * sw))
    Sp = P.pos(f'upperarm_{s}')
    if g['run']:
        c.arm_fk(P, s, swing=0.45 * sw - 0.05, abd=c.st['arm_abd'] + 0.12, twist=0.2, elbow=0.9 + 0.2 * sw)
        hb = f'hand_{s}'
        want = Vector((sg * 0.1, 0.4 - 0.2 * sw, -0.9)).normalized()
        P.set_world(hb, cn['dir'].rotation_difference(want).to_matrix() @ c.sk.rest3[hb])
        c.fingers(P, s, 'grip')
        return
    # one cane beat per stride (two steps): down as the opposite foot lands, left behind, swung forward again.
    # The cane is only as long as the hanging arm, so it can stay planted for a third of the stride at most.
    off = 0.5 if s == 'l' else 0.0          # phase at which the opposite foot strikes
    ph = (u - off + 0.02) % 1.0
    v, T = g['v'], g['T']
    D = min(0.46, v * 0.36 * T)
    duty = D / (v * T)
    x = sg * (c.side_x + 0.06)
    front = c.arms[s]['S'].y - 0.27
    if ph < duty:
        k = ph / duty
        tip = Vector((x, front + D * k, c.ground + 0.004))
    else:
        w = (ph - duty) / (1 - duty)
        y = hermite(w, front + D, front, v * (1 - duty) * T * 0.8, v * (1 - duty) * T * 0.5)
        tip = Vector((x + sg * 0.02 * math.sin(math.pi * w), y, c.ground + 0.004 + 0.085 * math.sin(math.pi * w ** 0.8) ** 1.2))
    k = (ph / duty) if ph < duty else 1 - smooth((ph - duty) / (1 - duty))
    hint = Vector((Sp.x + sg * 0.06, Sp.y - 0.2 + 0.26 * k, cn['wrist'].z + 0.03))
    c.cane_arm(P, tip, hint, pole=Vector((sg * 0.3, 1, -0.1)))


def make_gait(c, kind):
    g = gait_params(c, kind)
    def fn(P, f):
        gait_pose(c, P, (f / g['n']) % 1.0, g)
    return fn, g


# ---------------------------------------------------------------------------------------------------------------
# Standing clips

def idle_state(c, t, T=12.0):
    """The living stance: breath, the weight moving from one leg to the other and back, the head looking about."""
    st = c.st; sd = c.seed
    S = c.base()
    a = st['idle_shift']
    # weight: on the right leg, across to the left for the middle of the clip, and back
    sh = -0.55 + 1.15 * pulse(t, T * 0.26, T * 0.26 + 1.5, T * 0.74, T * 0.74 + 1.7)
    sh = sh * a + 0.08 * wob(t, T, sd + 1, 2)
    S['shift'] = sh
    S['fwd'] = 0.006 * wob(t, T, sd + 2, 2)
    S['breath'] = 0.5 - 0.5 * math.cos(TAU * t / (T / 3))
    S['pel_yaw'] = 0.035 * sh + 0.01 * wob(t, T, sd + 3)
    S['turn'] = -0.05 * sh + 0.02 * wob(t, T, sd + 4, 2)
    S['lean'] = 0.012 * wob(t, T, sd + 5, 2)
    look = st['idle_look']
    yaw = 0.3 * look * (pulse(t, T * 0.12, T * 0.12 + 0.7, T * 0.3, T * 0.3 + 0.9)
                        - 0.8 * pulse(t, T * 0.5, T * 0.5 + 0.8, T * 0.66, T * 0.66 + 1.0)) + 0.03 * wob(t, T, sd + 6)
    pitch = 0.04 * wob(t, T, sd + 7, 2) + 0.07 * look * pulse(t, T * 0.84, T * 0.84 + 0.6, T * 0.93, T * 0.93 + 0.7)
    S['head'] = (yaw, pitch, 0.02 * wob(t, T, sd + 8) - 0.03 * sh)
    S['turn'] += yaw * 0.12
    for s, k in (('l', 9), ('r', 12)):
        arm = S[f'arm_{s}']
        arm['swing'] += 0.025 * wob(t - 0.4, T, sd + k, 2) - 0.02 * S['lean']
        arm['elbow'] += 0.05 * wob(t - 0.6, T, sd + k + 1, 2) + 0.03 * S['breath']
        arm['wrist'] += 0.05 * wob(t - 0.8, T, sd + k + 2, 3)
        S[f'wig_{s}'] = 0.05 * wob(t, T, sd + k + 3, 3)
    if st.get('lady'): lady_hands(c, S, t, T)
    return S


def lady_hands(c, S, t, T, k=1.0):
    """Hands folded in front at the waist, clear of the skirt."""
    z = c.sk.head['spine_01'].z + 0.03
    y = c.front(z) - 0.05
    S['arm_r'] = dict(ik=Vector((-0.012, y - 0.012, z + 0.004 * wob(t, T, 31))), pole=Vector((-1, 0.5, -0.5)),
                      hand=(Vector((0.85, -0.1, -0.5)), Vector((0.1, 1, 0.1))))
    S['arm_l'] = dict(ik=Vector((0.03, y - 0.03, z - 0.012)), pole=Vector((1, 0.5, -0.5)),
                      hand=(Vector((-0.85, -0.1, -0.45)), Vector((-0.1, 1, 0.1))))
    S['hand_l'] = S['hand_r'] = 'cup'


def make_idle(c, T=12.0):
    def fn(P, f):
        c.apply(P, idle_state(c, f / FPS, T))
    return fn


def neutral(c):
    """The stance the one-shot clips start from and return to: the Idle's first frame."""
    return idle_state(c, 0.0)


def gesture_arm(c, kind, s, e=1.0):
    """FK arm shapes for talking, as offsets from the chest. e scales the size."""
    st = c.st
    if kind == 'offer':     # forearm out, palm up, toward the listener
        return dict(swing=0.42 * e, abd=0.1 + 0.08 * e, twist=-0.25, elbow=1.25, wrist=-0.25, pron=-1.25), 'open'
    if kind == 'beat':      # a small chop with the edge of the hand
        return dict(swing=0.3 * e, abd=0.06, twist=0.15, elbow=1.45, wrist=0.05, pron=-0.3), 'soft'
    if kind == 'count':     # index finger raised
        return dict(swing=0.5 * e, abd=0.12, twist=0.05, elbow=1.9, wrist=-0.1, pron=-0.2), 'point'
    if kind == 'lapel':     # hand to the lapel
        return dict(swing=0.3, abd=0.22, twist=0.95, elbow=2.15, wrist=0.25, pron=0.2), 'hold'
    if kind == 'wide':      # both arms opened, palms up
        return dict(swing=0.3 * e, abd=0.35 * e, twist=-0.55, elbow=1.1, wrist=-0.3, pron=-1.3), 'splay'
    if kind == 'low':       # a turn of the hand low down
        return dict(swing=0.16, abd=0.12, twist=-0.2, elbow=0.75, wrist=-0.2, pron=-0.9), 'open'
    if kind == 'belly':     # hands laced over the stomach
        return dict(swing=0.12, abd=0.2, twist=0.8, elbow=1.5, wrist=0.2, pron=0.1), 'cup'
    raise KeyError(kind)


TALKS = {  # (start s, rise s, hold s, fall s, kind, arm(s), size)
    'default': [(0.4, 0.5, 1.5, 0.7, 'offer', 'r', 1.0), (3.4, 0.4, 0.9, 0.6, 'beat', 'r', 1.0),
                (5.6, 0.55, 1.6, 0.8, 'wide', 'lr', 0.8), (9.0, 0.45, 1.2, 0.8, 'low', 'l', 1.0)],
    'holmes': [(0.3, 0.45, 1.3, 0.6, 'count', 'r', 1.0), (2.9, 0.4, 1.4, 0.7, 'offer', 'r', 1.1),
               (5.9, 0.5, 2.0, 0.7, 'lapel', 'r', 1.0), (9.3, 0.35, 0.9, 0.7, 'beat', 'r', 1.1)],
    'watson': [(0.5, 0.5, 1.4, 0.7, 'low', 'r', 1.0), (3.3, 0.5, 1.6, 0.7, 'offer', 'r', 0.9),
               (6.4, 0.5, 1.8, 0.8, 'lapel', 'l', 1.0), (9.4, 0.4, 1.0, 0.7, 'beat', 'r', 0.9)],
    'polhaus': [(0.4, 0.5, 1.6, 0.7, 'beat', 'r', 1.1), (3.4, 0.5, 1.5, 0.8, 'wide', 'lr', 0.7),
                (6.6, 0.4, 1.2, 0.6, 'count', 'r', 0.9), (9.2, 0.5, 1.2, 0.8, 'low', 'l', 1.0)],
    'kelly': [(0.6, 0.5, 1.2, 0.7, 'low', 'r', 0.9), (3.6, 0.5, 1.3, 0.7, 'offer', 'r', 0.8),
              (7.0, 0.5, 1.3, 0.8, 'low', 'l', 0.9), (9.6, 0.4, 0.8, 0.7, 'beat', 'r', 0.7)],
    'gutman': [(0.3, 0.6, 1.8, 0.9, 'wide', 'lr', 1.0), (3.9, 0.5, 1.2, 0.7, 'count', 'r', 0.9),
               (6.3, 0.6, 2.2, 0.9, 'belly', 'lr', 1.0), (10.0, 0.4, 0.7, 0.6, 'offer', 'r', 1.0)],
    'brigid': [(0.5, 0.5, 1.4, 0.8, 'low', 'r', 0.8), (3.6, 0.5, 1.6, 0.8, 'lapel', 'r', 1.0),
               (7.0, 0.5, 1.4, 0.8, 'offer', 'l', 0.7)],
    'cairo': [(0.3, 0.4, 1.3, 0.6, 'offer', 'r', 1.0), (2.9, 0.4, 1.2, 0.6, 'count', 'r', 1.0),
              (5.4, 0.5, 1.6, 0.8, 'wide', 'lr', 0.9), (8.7, 0.4, 1.4, 0.8, 'lapel', 'l', 1.0)],
}


def make_talk(c, T=12.0):
    st = c.st; sd = c.seed + 100
    seq = TALKS.get(c.name, TALKS['default'])
    e0 = st['talk']
    def fn(P, f):
        t = f / FPS
        S = idle_state(c, 0.0)
        S['shift'] = -0.45 + 0.9 * pulse(t, 4.6, 6.0, 10.4, 11.8) * st['idle_shift']
        S['breath'] = 0.5 - 0.5 * math.cos(TAU * t / (T / 4))
        S['lean'] = 0.02 + 0.012 * wob(t, T, sd, 2)
        # the head goes with the sense: small nods on the stresses, turns and tilts between
        nod = sum(math.exp(-((t - t0 - 0.25) / 0.16) ** 2) for t0, *_ in seq)
        nod += 0.6 * sum(math.exp(-((t - x) / 0.14) ** 2) for x in (2.2, 4.9, 8.3, 11.0))
        yaw = 0.07 * wob(t, T, sd + 1, 3) * e0
        S['head'] = (yaw, 0.02 + 0.075 * nod + 0.025 * wob(t, T, sd + 2, 4), 0.045 * wob(t, T, sd + 3, 2))
        S['head_w'] = 0.8
        S['turn'] = 0.03 * wob(t, T, sd + 4, 2)
        if st.get('lady'):   # hands carried folded at the waist; the gestures leave from there
            for s in 'lr':
                S[f'arm_{s}'] = dict(swing=0.2, abd=0.1, twist=0.8, elbow=1.2, wrist=0.15)
                S[f'hand_{s}'] = 'cup'
        arms = {'l': dict(S['arm_l']), 'r': dict(S['arm_r'])}
        used = {}
        for t0, rise, hold, fall, kind, sides, size in seq:
            k = pulse(t, t0, t0 + rise, t0 + rise + hold, t0 + rise + hold + fall)
            if k <= 0: continue
            S['lean'] += 0.03 * k; S['turn'] += (0.05 if 'r' in sides else -0.05) * k * (0 if sides == 'lr' else 1)
            for s in sides:
                if c.cane and c.cane['side'] == s: continue
                tgt, shape = gesture_arm(c, kind, s, size * e0)
                # a little life while the pose is held: the hand beats with the words
                beat = 0.07 * math.sin(TAU * (t - t0) * 2.2) * k
                tgt = dict(tgt); tgt['elbow'] += beat; tgt['swing'] += beat * 0.4; tgt['wrist'] += beat * 0.8
                S[f'arm_{s}'] = mix_arm(arms[s], tgt, k)
                used[s] = (shape, k)
        for s, (shape, k) in used.items():
            S[f'mix_{s}'] = (shape, smooth(k * 1.4))
        for s, kk in (('l', 9), ('r', 12)):
            if s not in used:
                S[f'arm_{s}']['elbow'] += 0.05 * wob(t, T, sd + kk, 2)
                S[f'arm_{s}']['swing'] += 0.02 * wob(t, T, sd + kk + 1, 2)
        c.apply(P, S)
    return fn


def reach(c, P, s, target, k, pole=None, mid=None):
    """Take the wrist from where the pose has it now toward target by k (0..1), along an arc through mid; at
    k = 0 the arm is exactly as it was, so a clip can leave the neutral stance without a pop."""
    if k <= 0: return
    a = c.arms[s]
    Sp, E0, W0 = P.pos(f'upperarm_{s}'), P.pos(f'lowerarm_{s}'), P.pos(f'hand_{s}')
    pole0 = (E0 - Sp).normalized()
    pole = pole0.lerp(Vector(pole).normalized(), smooth(k * 1.5)) if pole is not None else pole0
    target = Vector(target)
    if mid is not None:
        mid = Vector(mid)
        w = W0 * (1 - k) ** 2 + mid * 2 * k * (1 - k) + target * k ** 2
    else:
        w = W0.lerp(target, k)
    c.arm_ik(P, s, w, pole)


def hand_toward(c, P, s, fingers_dir, palm_dir, k):
    """Blend the hand from however the forearm carries it toward a world orientation."""
    if k <= 0: return
    a = c.arms[s]
    g0 = P.carried(f'hand_{s}', a['g0']); p0 = P.carried(f'hand_{s}', a['p0'])
    c.hand_world(P, s, g0.lerp(Vector(fingers_dir).normalized(), k), p0.lerp(Vector(palm_dir).normalized(), k))


def make_oneshot(c, kind):
    """Point, Nod, Shrug: from the neutral stance and back to it."""
    st = c.st
    n = {'Point': 66, 'Nod': 39, 'Shrug': 54}[kind]
    def fn(P, f):
        t = f / FPS
        env = smooth(t / 0.12) * smooth((n / FPS - t) / 0.15)
        S = neutral(c)
        k = 0.0
        if kind == 'Nod':
            k1 = math.exp(-((t - 0.4) / 0.17) ** 2); k2 = math.exp(-((t - 0.88) / 0.15) ** 2)
            up = math.exp(-((t - 0.14) / 0.1) ** 2)
            y, p, r = S['head']
            S['head'] = (y, p + env * (0.2 * k1 + 0.12 * k2 - 0.035 * up), r)
            S['lean'] += env * (0.025 * k1 + 0.012 * k2)
        elif kind == 'Shrug':
            k = pulse(t, 0.12, 0.55, 0.95, 1.6)
            S['shrug_l'] += 0.2 * k; S['shrug_r'] += 0.22 * k
            y, p, r = S['head']
            S['head'] = (y, p - 0.03 * k, r + 0.13 * k)
            S['lean'] -= 0.02 * k
            if not st.get('lady'):
                for s in 'lr':
                    if c.cane and c.cane['side'] == s: continue
                    tgt = dict(swing=0.1, abd=0.2, twist=-0.5, elbow=0.95, wrist=-0.35, pron=-1.2)
                    S[f'arm_{s}'] = mix_arm(S[f'arm_{s}'], tgt, smooth(pulse(t, 0.18, 0.62, 0.95, 1.65)))
                    S[f'mix_{s}'] = ('splay', k)
        elif kind == 'Point':
            k = pulse(t, 0.1, 0.6, 1.5, 2.15)
            S['turn'] += -0.1 * k; S['lean'] += 0.05 * k
            y, p, r = S['head']
            S['head'] = (y * (1 - k) - 0.05 * k, p + 0.1 * k, r * (1 - k))
            S['mix_r'] = ('point', smooth(k * 1.5))
        c.apply(P, S)
        if kind == 'Point' and k > 0:
            over = 0.05 * math.exp(-((t - 0.62) / 0.12) ** 2)
            Sp = P.pos('upperarm_r')
            a = c.arms['r']
            d = Vector((-0.04, -1, -0.2 + over)).normalized()
            target = Sp + d * (a['L1'] + a['L2']) * 0.97
            reach(c, P, 'r', target, smoother(k), Vector((-0.35, 0.3, -1)), Sp + Vector((-0.03, -0.42, -0.34)))
            hand_toward(c, P, 'r', d, Vector((0.9, 0, -0.45)), smooth((k - 0.2) / 0.6))
    return fn, n


def make_turn(c, direction):
    """Turn in place through 90 degrees: the game turns the figure (yaw = 90 * smoothstep(t / T)) while this clip
    steps the feet round so that they stay where they are planted. direction: +1 = to his left."""
    T = 0.9
    A = math.radians(90) * direction
    def ground(t):   # how far the ground has turned under him (opposite to his own turn)
        return -A * smooth(t / T)
    lead, trail = ('l', 'r') if direction > 0 else ('r', 'l')
    steps = {lead: (0.05, 0.42), trail: (0.45, 0.85)}   # the foot on the side he turns to steps first
    def fn(P, f):
        t = f / FPS
        S = neutral(c)
        k = math.sin(math.pi * clamp01(t / T))
        y0, p0, r0 = S['head']
        S['head'] = (y0 + direction * 0.5 * k * (1 - smooth(t / T)) * 2.0, p0, r0)   # the head goes first
        S['turn'] += direction * 0.12 * k * (1 - smooth(t / T)) * 2
        S['sink'] += 0.012 * k
        w1 = pulse(t, 0.0, 0.12, 0.34, 0.47); w2 = pulse(t, 0.4, 0.52, 0.78, 0.9)
        sgn = 1 if lead == 'l' else -1
        S['shift'] = S['shift'] * (1 - k) + (-sgn * 0.8 * w1 + sgn * 0.8 * w2)   # onto the standing foot
        feet = {}
        for s in 'lr':
            a, b = steps[s]
            A0 = c.legs[s]['A']
            w = smooth((t - a) / (b - a))
            ang = ground(t) - w * ground(T)       # carried by the ground until it steps, and again after
            lift = 0.05 * math.sin(math.pi * w) if 0 < w < 1 else 0.0
            pos = rz(ang) @ Vector((A0.x, A0.y, 0))
            feet[s] = dict(ankle=Vector((pos.x, pos.y, A0.z + lift)), yaw=ang, pitch=0.3 * math.sin(math.pi * w) if lift else 0.0)
        S['feet'] = feet
        c.apply(P, S)
    return fn, T


def think_state(c, t, T=8.0):
    """Hand to the chin, the other arm across the body carrying its elbow; weight on one leg."""
    st = c.st; sd = c.seed + 300
    S = neutral(c)
    S['shift'] = 0.6 * st['idle_shift'] + 0.05 * wob(t, T, sd, 2)
    S['breath'] = 0.5 - 0.5 * math.cos(TAU * t / (T / 2))
    S['lean'] = 0.03 + 0.01 * wob(t, T, sd + 1, 2)
    S['turn'] = 0.05
    S['head'] = (0.1 * wob(t, T, sd + 2, 2) - 0.05, 0.13 + 0.03 * wob(t, T, sd + 3, 2), -0.05)
    S['head_w'] = 0.9
    return S


def think_arms(c, P, t, T=8.0):
    """After the trunk and head are placed: the right hand finds the chin."""
    sd = c.seed + 300
    k = c.scale
    chin = P.point('head', c.sk.head['head'] + Vector((-0.01, -0.1 * k, -0.05 * k)))
    tap = 0.005 * wob(t, T, sd + 5, 4)
    wr = chin + Vector((-0.05, -0.035 + tap, -0.12 * k))
    c.arm_ik(P, 'r', wr, Vector((-0.45, 0.2, -1)))
    c.hand_world(P, 'r', Vector((0.3, 0.25, 1)), Vector((0.5, 1, -0.2)))
    c.fingers(P, 'r', 'fist', 'point', 0.55, wiggle=0.03 * wob(t, T, sd + 6, 3))
    if not (c.cane and c.cane['side'] == 'l'):
        z = c.sk.head['spine_02'].z + 0.05
        y = c.front(z) - 0.035
        el = P.pos('lowerarm_r')
        c.arm_ik(P, 'l', Vector((-0.07, min(y, el.y + 0.0), z)), Vector((1, 0.6, -0.6)))
        c.hand_world(P, 'l', Vector((-1, -0.1, 0.12)), Vector((0.05, 1, 0.25)))
        c.fingers(P, 'l', 'cup')


def make_think(c, T=8.0):
    def fn(P, f):
        t = f / FPS
        S = think_state(c, t, T)
        S['arm_r'] = lambda P: None
        if not (c.cane and c.cane['side'] == 'l'): S['arm_l'] = lambda P: None
        c.apply(P, S)
        think_arms(c, P, t, T)
    return fn


def make_guard(c, T=10.0):
    """A policeman's standing guard: feet planted, hands clasped behind, rocking a little, watching the street."""
    sd = c.seed + 400
    def fn(P, f):
        t = f / FPS
        S = neutral(c)
        S['shift'] = 0.12 * wob(t, T, sd, 2)
        S['fwd'] = 0.012 * math.sin(TAU * t / (T / 2))            # rocks heel to toe
        S['breath'] = 0.5 - 0.5 * math.cos(TAU * t / (T / 2.5 if False else T / 2))
        S['lean'] = -0.03
        S['shrug_l'] = S['shrug_r'] = -0.02
        yaw = 0.42 * (pulse(t, 1.0, 2.0, 3.6, 4.6) - pulse(t, 5.6, 6.6, 8.0, 9.2))
        S['head'] = (yaw, -0.03 + 0.02 * wob(t, T, sd + 1, 2), 0.0)
        S['turn'] = yaw * 0.18
        S['head_w'] = 0.9
        S['arm_l'] = lambda P: None; S['arm_r'] = lambda P: None
        S['cane'] = False
        c.apply(P, S)
        P.local('clavicle_l', Z, 0.1); P.local('clavicle_r', Z, -0.1)
        z = c.sk.head['pelvis'].z + 0.03
        back = P.point('pelvis', Vector((0, c.back_y + 0.035, z)))
        c.arm_ik(P, 'r', back + Vector((0.02, 0.0, 0.0)), Vector((-1, 0.9, 0.1)))
        c.hand_world(P, 'r', Vector((1, 0.1, -0.35)), Vector((0, -1, 0.1)))
        c.fingers(P, 'r', 'cup')
        c.arm_ik(P, 'l', back + Vector((-0.045, 0.03, 0.02)), Vector((1, 0.9, 0.1)))
        c.hand_world(P, 'l', Vector((-1, 0.1, -0.2)), Vector((0, -1, 0.1)))
        c.fingers(P, 'l', 'hold')
    return fn


def make_notes(c, T=8.0):
    """Taking notes: the notebook in the left hand at the chest, the right writing; a glance up now and then."""
    sd = c.seed + 500
    def fn(P, f):
        t = f / FPS
        S = neutral(c)
        S['shift'] = -0.35 + 0.06 * wob(t, T, sd, 2)
        S['breath'] = 0.5 - 0.5 * math.cos(TAU * t / (T / 2))
        up = pulse(t, 4.6, 5.1, 6.0, 6.6)                           # looks up at the speaker
        S['lean'] = 0.07 - 0.04 * up
        S['head'] = (0.1 - 0.12 * up, 0.42 - 0.38 * up, 0.03)
        S['head_w'] = 0.9
        S['arm_l'] = lambda P: None; S['arm_r'] = lambda P: None
        S['cane'] = False
        c.apply(P, S)
        z = c.sk.head['spine_03'].z + 0.0
        y = c.front(z) - 0.12
        book = P.point('spine_02', Vector((0.05, y, z)))
        c.arm_ik(P, 'l', book + Vector((0.035, 0.03, -0.035)), Vector((0.8, 0.5, -1)))
        c.hand_world(P, 'l', Vector((-0.75, -0.6, 0.22)), Vector((0.15, 0.35, 1)))
        c.fingers(P, 'l', 'hold')
        P.local('thumb_01_l', c.arms['l']['g0'], -0.3)
        # the pencil hand: moves along a line, hops back, pauses when he looks up
        rate = 7.0 / T                                  # seven lines of writing in the loop
        w = (t * rate) % 1.0
        line = smooth(w / 0.8) - smooth((w - 0.8) / 0.2)
        scr = 0.004 * math.sin(TAU * t * 6.0) * (1 - up)
        r0 = int(t * rate) % 7 % 3; r1 = (int(t * rate) + 1) % 7 % 3
        row = 0.012 * lerp(r0, r1, smooth((w - 0.8) / 0.2))
        pen = book + Vector((-0.085 + 0.05 * line * (1 - up), -0.035 + row + scr, 0.052 + 0.03 * up))
        c.arm_ik(P, 'r', pen, Vector((-0.9, 0.6, -0.7)))
        c.hand_world(P, 'r', Vector((0.72, -0.5, -0.5)), Vector((0.45, 0.2, -0.9)))
        c.fingers(P, 'r', 'pinch')
    return fn


# ---------------------------------------------------------------------------------------------------------------
# Kneeling to examine

def kneel_state(c, k, t=0.0, T=8.0, alive=0.0):
    sd = c.seed + 600
    S = neutral(c)
    Lr = c.legs['r']
    kz = c.ground + 0.075                                  # the knee joint's height when it rests on the ground
    down = c.sk.head['thigh_r'].z - (kz + Lr['L1'] * 0.97)
    back = 0.34 * c.scale + 0.02
    ks = smoother(k)
    S['sink'] = down * ks
    S['fwd'] = back * smooth(k * 1.15)
    S['shift'] = S['shift'] * (1 - ks) + 0.1 * ks
    look = alive * wob(t, T, sd, 2)
    S['lean'] = 0.3 * math.sin(math.pi * k) + 0.62 * ks + 0.06 * alive * wob(t, T, sd + 1, 2)
    S['pel_pitch'] = 0.2 * ks
    S['turn'] = S['turn'] * (1 - ks) - 0.1 * ks + 0.07 * look
    S['breath'] = (0.5 - 0.5 * math.cos(TAU * t / (T / 2))) if alive else 0.0
    y0, p0, r0 = S['head']
    S['head'] = (y0 * (1 - ks) + (-0.15 + 0.22 * look) * ks,
                 p0 * (1 - ks) + (0.6 + 0.07 * alive * wob(t, T, sd + 2, 3)) * ks, r0 * (1 - ks))
    S['head_w'] = lerp(S['head_w'], 0.95, ks)
    return S, ks, look


def kneel_pose(c, P, k, t=0.0, T=8.0, alive=0.0):
    """k: 0 standing (neutral) .. 1 down on the right knee, sitting back from the thing he examines.
    alive: the examining motion (0..1)."""
    sd = c.seed + 600
    Ll, Lr = c.legs['l'], c.legs['r']
    kz = c.ground + 0.075
    if not hasattr(c, '_kneel'):   # where the right hip ends up, and so where the knee and ankle rest
        S1, _, _ = kneel_state(c, 1.0)
        S1['feet'] = {'l': lambda P: None, 'r': lambda P: None}
        S1['arm_l'] = S1['arm_r'] = lambda P: None; S1['cane'] = False
        P1 = c.apply(c.pose(), S1)
        H1 = P1.pos('thigh_r')
        dz = H1.z - kz
        K1 = Vector((H1.x - 0.02, H1.y + math.sqrt(max(0.0, Lr['L1'] ** 2 - dz * dz - 0.02 ** 2)), kz))
        za = c.ground + 0.012 + (Lr['A'] - Lr['B']).length * 0.97
        A1 = Vector((K1.x - 0.01, K1.y + math.sqrt(max(0.0, Lr['L2'] ** 2 - (za - kz) ** 2)), za))
        c._kneel = (K1, A1)
    K1, A1 = c._kneel
    S, ks, look = kneel_state(c, k, t, T, alive)
    kr = smooth(k / 0.6)
    def right(P):
        H = P.pos('thigh_r')
        A = Lr['A'].lerp(A1, kr)
        A.z += 0.06 * math.sin(math.pi * clamp01(k / 0.6))
        pole = FWD.lerp((K1 - (H + A) / 2).normalized(), smooth(k / 0.7))
        c.leg(P, 'r', A, 1.2 * kr, -0.04 * kr, 0.15 * kr, pole=pole)
    def left(P):
        c.leg(P, 'l', Ll['A'], 0.0, 0.0, pole=Vector((0.25 * ks, -1, 0)))
    S['feet'] = {'r': right, 'l': left}
    cane_side = c.cane['side'] if c.cane else None
    if cane_side:
        cn = c.cane; sg = c.arms[cane_side]['sign']
        S['cane'] = Vector((cn['tip'].x + sg * 0.1 * ks, cn['tip'].y + 0.06 - 0.02 * ks, c.ground + 0.005))
        S['cane_hint'] = lambda P: P.pos(f'upperarm_{cane_side}') + Vector((sg * (0.05 + 0.12 * ks), -0.04 - 0.22 * ks, lerp(-0.5, -0.02, ks)))
        S['cane_pole'] = Vector((sg * 0.6, 1, -0.6))
    c.apply(P, S)
    # left hand to the left knee (or on the cane), right hand down to what he is looking at
    if cane_side != 'l':
        knee = P.pos('calf_l')
        kk = smooth((k - 0.15) / 0.75)
        reach(c, P, 'l', knee + Vector((0.01, -0.035, 0.075)), kk, Vector((1, 0.5, -0.3)))
        hand_toward(c, P, 'l', Vector((-0.3, -0.9, -0.3)), Vector((0.05, 0.25, -1)), smooth((k - 0.3) / 0.6))
        c.fingers(P, 'l', 'relax', 'cup', ks)
    if cane_side != 'r':
        hip0 = c.sk.head['pelvis']
        r01 = alive * (0.5 + 0.5 * wob(t, T, sd + 4, 2))
        probe = alive * pulse(t % T, T * 0.55, T * 0.63, T * 0.8, T * 0.9)     # lifts something to look at it
        tgt = Vector((-0.2 + 0.1 * look, hip0.y - 0.22 - 0.1 * r01, c.ground + 0.2 + 0.03 * math.sin(TAU * t / (T / 4)) * alive))
        Sp = P.pos('upperarm_r')
        tgt = tgt.lerp(Sp + Vector((0.1, -0.3, -0.12)), probe)
        kk = smooth((k - 0.3) / 0.7)
        reach(c, P, 'r', tgt, kk, Vector((-1, 0.5, 0.3)))
        hand_toward(c, P, 'r', Vector((0.15, -0.5, -0.85)).lerp(Vector((0.3, -0.3, 0.7)), probe),
                    Vector((0.2, 0.85, -0.5)).lerp(Vector((0.5, 0.8, 0.2)), probe), kk)
        c.fingers(P, 'r', 'relax', 'pinch' if probe > 0.3 else 'open', max(ks * 0.7, probe),
                  wiggle=0.05 * alive * wob(t, T, sd + 7, 4))


def make_kneel(c, kind):
    if kind == 'KneelDown':
        T = 1.5
        return (lambda P, f: kneel_pose(c, P, smooth((f / FPS) / T) ** 0.9)), T
    if kind == 'KneelUp':
        T = 1.4
        return (lambda P, f: kneel_pose(c, P, 1 - smooth((f / FPS) / T) ** 1.1)), T
    T = 8.0
    return (lambda P, f: kneel_pose(c, P, 1.0, f / FPS, T, 1.0)), T


# ---------------------------------------------------------------------------------------------------------------
# Held story poses

def make_lie(c):
    """A dead man on his back. The games lay the standing figure down, so the ground is the plane behind him
    (y = back_y) and -Y is up. Limbs lie where they fell: on the ground, not at attention."""
    sk = c.sk
    def fn(P, f):
        g = c.back_y
        P.move('pelvis', (0.0, 0.0, 0.0))
        P.rot('pelvis', Z, -0.06); P.rot('pelvis', Y, 0.03)
        P.rot('spine_01', Y, -0.03); P.rot('spine_02', Z, 0.05); P.rot('spine_03', Z, 0.07); P.rot('spine_03', Y, -0.04)
        # the head has rolled to his right and back
        P.rot('neck_01', X, -0.16); P.rot('neck_01', Z, -0.3)
        P.rot('head', Z, -0.5); P.rot('head', X, -0.1); P.rot('head', Y, 0.12)
        # left leg straight, the foot fallen outward; right knee bent and dropped to the side
        Ll, Lr = c.legs['l'], c.legs['r']
        c.leg(P, 'l', Ll['A'] + Vector((0.04, 0.02, 0.0)), 0.5, 0.5, pole=Vector((0.3, -1, 0)), roll=0.0)
        Hr = P.pos('thigh_r')
        A = Vector((Lr['A'].x - 0.06, g - 0.07, Lr['A'].z + 0.09))
        c.leg(P, 'r', A, 0.7, -0.95, pole=Vector((-1, -0.12, 0.05)))
        P.rot('foot_r', Y, 0.0)
        # right arm thrown out and up beside the head, the back of the hand on the ground
        Sr = P.pos('upperarm_r'); ar = c.arms['r']
        E = Vector((Sr.x - ar['L1'] * 0.9, 0, Sr.z - ar['L1'] * 0.3)); E.y = g - 0.045
        E = Sr + (E - Sr).normalized() * ar['L1']
        Wp = E + Vector((-0.3, 0, 0.95)).normalized() * ar['L2']; Wp.y = g - 0.03
        Wp = E + (Wp - E).normalized() * ar['L2']
        P.orient('upperarm_r', E - Sr, Wp - E)
        P.orient('lowerarm_r', Wp - E, -(E - Sr))
        c.hand_world(P, 'r', Vector((0.3, 0.12, 1)), Vector((0.15, -1, 0)), share=0.5)
        c.fingers(P, 'r', 'dead')
        # left arm fallen by his side, a little away, palm down, elbow soft
        Sl = P.pos('upperarm_l'); al = c.arms['l']
        E = Vector((Sl.x + al['L1'] * 0.42, g - 0.05, Sl.z - al['L1'] * 0.88))
        E = Sl + (E - Sl).normalized() * al['L1']
        Wp = Vector((E.x + al['L2'] * 0.1, g - 0.035, E.z - al['L2']))
        Wp = E + (Wp - E).normalized() * al['L2']
        P.orient('upperarm_l', E - Sl, Vector((-0.2, -1, 0)))
        P.orient('lowerarm_l', Wp - E, Vector((-0.5, -1, 0)))
        c.hand_world(P, 'l', Vector((0.25, 0.1, -1)), Vector((-0.2, 1, 0)), share=0.5)
        hs = 'l' if not (c.cane and c.cane['side'] == 'l') else None
        if hs: c.fingers(P, 'l', 'dead')
        else: c.fingers(P, 'l', 'grip')
    return fn


def make_aim(c, T=4.0):
    """Pistol levelled in the right hand (the bone's +Y is the barrel), body turned side-on behind it."""
    sd = c.seed + 700
    def fn(P, f):
        t = f / FPS
        S = neutral(c)
        S['shift'] = 0.1; S['sink'] = 0.012
        S['pel_yaw'] = 0.22
        S['turn'] = 0.42 + 0.01 * wob(t, T, sd, 2)
        S['lean'] = 0.03
        S['breath'] = 0.5 - 0.5 * math.cos(TAU * t / T)
        S['head'] = (0.0, 0.03, 0.03); S['head_w'] = 1.0
        S['arm_r'] = lambda P: None
        if not (c.cane and c.cane['side'] == 'l'):
            S['arm_l'] = dict(swing=-0.12, abd=0.1, twist=0.3, elbow=0.5, wrist=0.1)
            S['hand_l'] = 'soft'
        c.apply(P, S)
        a = c.arms['r']
        Sp = P.pos('upperarm_r')
        eye = P.point('head', sk_eye(c))
        sway = Vector((0.004 * wob(t, T, sd + 1, 2), 0, 0.005 * wob(t, T, sd + 2, 2) - 0.004 * S['breath']))
        wr = Vector((eye.x - 0.07, Sp.y - (a['L1'] + a['L2']) * 0.94, Sp.z + 0.05)) + sway
        c.arm_ik(P, 'r', wr, Vector((-0.5, 0.2, -1)))
        hb = 'hand_r'
        P.set_world(hb, rz(0.02) @ rx(-math.pi / 2 + 0.02) @ c.sk.rest3[hb])
        c.fingers(P, 'r', 'grip')
        P.local('index_01_r', a['axis'], -0.55); P.local('index_02_r', a['axis'], -0.3)
    return fn


def sk_eye(c):
    h = c.sk.head['head']
    return h + Vector((0, -0.1 * c.scale, 0.036 * c.scale))


def make_handsup(c, T=4.0):
    sd = c.seed + 800
    def fn(P, f):
        t = f / FPS
        S = neutral(c)
        S['breath'] = 0.5 - 0.5 * math.cos(TAU * t / (T / 2))
        S['shift'] = 0.0; S['lean'] = -0.03
        S['shrug_l'] = S['shrug_r'] = 0.1
        S['head'] = (0.0, -0.02, 0.0)
        S['arm_l'] = lambda P: None; S['arm_r'] = lambda P: None
        S['cane'] = False
        c.apply(P, S)
        for s, sg in (('l', 1), ('r', -1)):
            a = c.arms[s]
            Sp = P.pos(f'upperarm_{s}')
            tr = 0.006 * wob(t, T, sd + (3 if s == 'l' else 9), 4)
            asym = 0.03 if s == 'l' else -0.01
            wr = Sp + Vector((sg * (0.3 + asym), -0.1, 0.33 + asym + tr - 0.006 * S['breath']))
            c.arm_ik(P, s, wr, Vector((sg * 1, 0.25, -0.8)))
            if c.cane and c.cane['side'] == s:
                hb = f'hand_{s}'
                P.set_world(hb, c.cane['dir'].rotation_difference(Vector((sg * 0.75, -0.1, -0.6)).normalized()).to_matrix() @ c.sk.rest3[hb])
                c.fingers(P, s, 'grip')
            else:
                c.hand_world(P, s, Vector((sg * 0.12, -0.05, 1)), Vector((-sg * 0.1, -1, 0)))
                c.fingers(P, s, 'open', 'splay', 0.5, wiggle=0.02 * wob(t, T, sd + 5, 4))
    return fn


# ---------------------------------------------------------------------------------------------------------------
# Baking

CLIPS = [  # name, loops, who ('all' or a tuple of names), export step for the web (frames between keys)
    ('Idle', True, 'all', 3), ('Walk', True, 'all', 1), ('Run', True, 'all', 1), ('Talk', True, 'all', 3),
    ('LieBack', False, 'all', 1), ('Aim', True, 'all', 4), ('HandsUp', True, 'all', 4),
    ('KneelDown', False, 'all', 2), ('KneelIdle', True, 'all', 3), ('KneelUp', False, 'all', 2),
    ('ThinkIdle', True, 'all', 4), ('Point', False, 'all', 2), ('Nod', False, 'all', 2), ('Shrug', False, 'all', 2),
    ('TurnLeft', False, 'all', 1), ('TurnRight', False, 'all', 1),
    ('GuardIdle', True, ('polhaus', 'kelly'), 4), ('NotesIdle', True, ('polhaus', 'kelly', 'watson'), 3),
]


def clip_fn(c, name):
    """(pose function of frame, number of frames)"""
    if name == 'Idle': return make_idle(c), 360
    if name == 'Walk':
        fn, g = make_gait(c, 'walk'); c.gaits['walk'] = g; return fn, g['n']
    if name == 'Run':
        fn, g = make_gait(c, 'run'); c.gaits['run'] = g; return fn, g['n']
    if name == 'Talk': return make_talk(c), 360
    if name == 'LieBack': return make_lie(c), 1
    if name == 'Aim': return make_aim(c), 120
    if name == 'HandsUp': return make_handsup(c), 120
    if name.startswith('Kneel'):
        fn, T = make_kneel(c, name); return fn, round(T * FPS)
    if name == 'ThinkIdle': return make_think(c), 240
    if name in ('Point', 'Nod', 'Shrug'): return make_oneshot(c, name)
    if name in ('TurnLeft', 'TurnRight'):
        fn, T = make_turn(c, 1 if name == 'TurnLeft' else -1); return fn, round(T * FPS)
    if name == 'GuardIdle': return make_guard(c), 300
    if name == 'NotesIdle': return make_notes(c), 240
    raise KeyError(name)


def sample(c, fn, n):
    """Pose every frame 0..n; returns {bone: (n+1, 4) quaternions}, pelvis locations (n+1, 3)."""
    sk = c.sk
    bones = sk.order
    Q = np.zeros((n + 1, len(bones), 4), dtype=np.float64); Q[:, :, 0] = 1
    L = np.zeros((n + 1, 3), dtype=np.float64)
    for f in range(n + 1):
        P = c.pose()
        fn(P, f)
        for i, b in enumerate(bones):
            q = P.q.get(b)
            if q is not None: Q[f, i] = (q.w, q.x, q.y, q.z)
        l = P.loc.get('pelvis')
        if l is not None: L[f] = l[:]
    for f in range(1, n + 1):   # keep each quaternion on the same side as the frame before
        flip = (Q[f] * Q[f - 1]).sum(axis=1) < 0
        Q[f, flip] *= -1
    return Q, L


def write_action(rig, name, Q, L, bones, loop):
    """Replace the Action (and its NLA track) of this name with one keyed on every frame."""
    ad = rig.animation_data_create()
    for tr in [t for t in ad.nla_tracks if t.name == name]: ad.nla_tracks.remove(tr)
    old = bpy.data.actions.get(name)
    if old: bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    slot = act.slots.new(id_type='OBJECT', name=rig.name)
    layer = act.layers.new('Layer'); strip = layer.strips.new(type='KEYFRAME')
    cb = strip.channelbag(slot, ensure=True)
    n = Q.shape[0]
    frames = np.arange(n, dtype=np.float64)
    lin = np.ones(n, dtype=np.int32)
    def curve(path, idx, group, vals):
        fc = cb.fcurves.new(path, index=idx, group_name=group)
        fc.keyframe_points.add(n)
        co = np.empty(n * 2); co[0::2] = frames; co[1::2] = vals
        fc.keyframe_points.foreach_set('co', co)
        fc.keyframe_points.foreach_set('interpolation', lin)
        fc.update()
    for i, b in enumerate(bones):
        for k in range(4):
            curve(f'pose.bones["{b}"].rotation_quaternion', k, b, Q[:, i, k])
    for k in range(3):
        curve('pose.bones["pelvis"].location', k, 'pelvis', L[:, k])
    act.frame_range = (0, n - 1)
    act.use_frame_range = True
    act.use_cyclic = bool(loop)
    tr = ad.nla_tracks.new(); tr.name = name
    st = tr.strips.new(name, 0, act)
    try: st.action_slot = slot
    except Exception: pass
    return act


def make_all_clips(rig, name, only=None, log=print):
    """Author every clip for this character. Returns the metadata the games need."""
    scene = bpy.context.scene
    scene.render.fps = FPS; scene.render.fps_base = 1.0
    c = Char(rig, name)
    c.gaits = {}
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    ad = rig.animation_data_create()
    ad.action = None
    meta = {}
    wanted = [x for x in CLIPS if (x[2] == 'all' or name in x[2]) and (not only or x[0] in only)]
    for cname, loop, who, step in wanted:
        fn, n = clip_fn(c, cname)
        Q, L = sample(c, fn, n)
        if loop:   # the last frame is the first again
            err = float(np.abs(Q[-1] - Q[0]).max())
            if err > 2e-3: log(f'  ! {name} {cname}: loop seam {err:.4f}')
            Q[-1] = Q[0]; L[-1] = L[0]
        write_action(rig, cname, Q, L, c.sk.order, loop)
        meta[cname] = dict(frames=n, seconds=round(n / FPS, 3), loop=loop, in_place=True, web_step=step)
    for kind in ('walk', 'run'):
        g = c.gaits.get(kind)
        if g:
            rig[f'{kind}_speed'] = round(g['v'], 3)
            meta[kind.capitalize()]['speed'] = round(g['v'], 3)
            cl = max(g.get('_clamped', [0]))
            if cl > 0.004: log(f'  ! {name} {kind}: pelvis lowered {cl * 100:.1f} cm more to keep a leg in reach')
    for old in ('walk_speed', 'run_speed'):
        if old not in rig.keys(): pass
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
    ad.action = None
    ad.use_nla = True
    return meta, c


def foot_slide(c, kind):
    """Check: how far each planted foot's contact point drifts against the ground during stance (metres)."""
    g = c.gaits[kind]
    n = g['n']; worst = 0.0
    for s in 'lr':
        L = c.legs[s]
        ref = None
        for i in range(n * 4):
            u = i / (n * 4)
            A, pitch, toe, yaw, st = foot_path(c, s, u, g)
            if not st: ref = None; continue
            piv = L['heel'] if pitch < 0 else L['B']
            pt = A + rz(yaw) @ rx(pitch) @ (piv - L['A'])
            gy = pt.y - g['v'] * g['T'] * u        # in the ground's frame
            if ((u + (0.5 if s == 'r' else 0)) % 1.0) < 1.0 / (n * 4) + 1e-9: ref = None
            if ref is None: ref = (gy, pt.z, piv)
            if ref[2] is piv: worst = max(worst, abs(gy - ref[0]))
            else: ref = (gy, pt.z, piv)
    return worst
