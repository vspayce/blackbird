# Pieces for the Burritt Alley / Bush Street set (art/build_set.py), on top of the shared kit (setkit.py):
# walls with real openings, recessed sash windows, bays, cornices, shopfronts, paving, street furniture and
# the clutter of a San Francisco back alley in 1895. setkit's own pieces are left as the other sets use them.
#
# Conventions (setkit's): game coordinates, Y up, metres. A facade frame F maps (u, v, w) = (along the wall,
# up, out of the wall) to the world; w = 0 is the wall face.
import math
from setkit import *  # noqa: F401,F403
import setkit
import alleytex as AT

PAPER = {}      # atlas regions, filled by alley_materials()
REGION = 'main'
_REG = {}


def region(name):
    """Geometry made from here on goes into objects named <material>.<name>. Splitting the set by place keeps
    each mesh within reach of only a few gaslights (URP lights eight per object)."""
    global REGION
    _REG[REGION] = dict(setkit.BM)
    setkit.BM.clear()
    setkit.BM.update(_REG.get(name, {}))
    REGION = name


# --- materials ---------------------------------------------------------------------------------------

def alley_materials():
    AT.brick_set({'brick_red': ('#7a3a28', '#8a8478', 0.5), 'brick_brown': ('#5e3b2c', '#857c6e', 0.45),
                  'brick_tan': ('#9a7b5a', '#a49c8a', 0.35)})
    for nm in ('brick_red', 'brick_brown', 'brick_tan'):
        AT.pbr(nm, nm, 'brick_n', 'brick', rough=0.9, scale=2.0)
    claps = {'clap_cream': '#c2b388', 'clap_sage': '#7d8a6c', 'clap_grey': '#7c8288', 'clap_ochre': '#a8834a'}
    AT.clap_set(claps)
    for nm in claps:
        AT.pbr(nm, nm, 'clap_n', 'clap', rough=0.8, scale=2.0)
    AT.setts(); AT.cobbles(); AT.planks(); AT.granite()
    AT.granite('stone_sand', base='#9c8f76', seed=151, speck=0.10, tool=0.25, wet=0.15)
    AT.pbr('stone', 'stone', 'stone_n', 'stone', rough=0.7, scale=1.5)
    AT.pbr('stone_sand', 'stone_sand', 'stone_sand_n', 'stone_sand', rough=0.8, scale=1.6)
    AT.pbr('stone_setts', 'stone_setts', 'stone_setts_n', 'stone_setts', rough=0.4, scale=4.0)
    AT.pbr('stone_cobble', 'stone_cobble', 'stone_cobble_n', 'stone_cobble', rough=0.4, scale=2.5)
    AT.pbr('stone_puddle', 'stone_setts_wet', rough=0.035, scale=4.0)
    AT.pbr('stone_puddle_alley', 'stone_cobble_wet', rough=0.035, scale=2.5)
    AT.pbr('wood_walk', 'wood_walk', 'wood_walk_n', 'wood_walk', rough=0.7, scale=2.0)
    AT.wood('door_wood', '#3a2618', boards=6, seed=61, contrast=0.3)
    AT.pbr('door_wood', 'door_wood', 'door_wood_n', rough=0.6, scale=1.2)
    AT.wood('crate_wood', '#8a6f4a', boards=5, seed=62, contrast=0.5, gapw=2.2)
    AT.pbr('crate_wood', 'crate_wood', 'crate_wood_n', rough=0.9, scale=0.75)
    AT.wood('barrel_wood', '#5a4026', boards=10, seed=63, contrast=0.4, soot=0.3)
    AT.pbr('barrel_wood', 'barrel_wood', 'barrel_wood_n', rough=0.75, scale=1.0)
    AT.wood('wood_fence', '#6b655c', boards=5, seed=64, contrast=0.6, gapw=1.0, soot=0.35)
    AT.pbr('wood_fence', 'wood_fence', 'wood_fence_n', rough=0.9, scale=1.0)
    AT.wood('wood_green', '#57483a', boards=5, seed=65, contrast=0.4, paint='#2c4034')
    AT.pbr('wood_green', 'wood_green', 'wood_green_n', rough=0.7, scale=1.0)
    AT.wood('wood_red', '#57483a', boards=6, seed=66, contrast=0.4, paint='#5e1f18')
    AT.pbr('wood_red', 'wood_red', 'wood_red_n', rough=0.7, scale=1.0)
    AT.metal_sheet('tin', '#575a56', seed=71, amount=0.55)
    AT.pbr('tin', 'tin', 'tin_n', rough=0.5, metal=0.55, scale=0.7)
    AT.metal_sheet('iron_rust', '#23201e', seed=72, rust='#4a2a18', amount=0.8)
    AT.pbr('iron_rust', 'iron_rust', 'iron_rust_n', rough=0.6, metal=0.6, scale=0.6)
    AT.stripes('cloth_awning', '#6b2a20', '#b8ab8a')
    AT.pbr('cloth_awning', 'cloth_awning', rough=0.95, scale=1.2)
    AT.stripes('cloth_awning_green', '#2c4a3a', '#b8ab8a', seed=82)
    AT.pbr('cloth_awning_green', 'cloth_awning_green', rough=0.95, scale=1.2)
    for nm, c, r, me in (('trim_cream', '#d0c5a8', 0.55, 0), ('trim_dark', '#27302a', 0.5, 0), ('trim_maroon', '#4a2420', 0.5, 0),
                         ('trim_olive', '#4d5238', 0.55, 0), ('trim_brown', '#46301f', 0.55, 0), ('trim_white', '#bdb9a8', 0.55, 0),
                         ('trim_blue', '#2c3a4a', 0.5, 0),
                         ('iron', '#16171a', 0.42, 0.7), ('glass_dark', '#0a0e13', 0.06, 0.5), ('sign_board', '#1a2a21', 0.45, 0),
                         ('sign_board_red', '#3d1612', 0.45, 0), ('sign_board_black', '#101010', 0.4, 0),
                         ('gilt', '#c79a3e', 0.3, 0.9), ('paint_faded', '#b9ad8f', 1.0, 0),
                         ('roof', '#1a1918', 0.9, 0), ('blind_cream', '#6e664f', 0.9, 0), ('blind_green', '#26392c', 0.9, 0),
                         ('cloth_white', '#a8a59a', 0.95, 0), ('cloth_blue', '#3c4a5e', 0.95, 0), ('cloth_red', '#6e2a24', 0.95, 0),
                         ('sack', '#7a6a4c', 1.0, 0), ('rope', '#6a5a3c', 1.0, 0), ('weeds', '#2c3320', 1.0, 0),
                         ('porcelain', '#9fb0a8', 0.25, 0), ('brass', '#a8853a', 0.35, 0.9), ('rail_steel', '#55575a', 0.25, 0.9),
                         ('slot_black', '#020202', 1.0, 0), ('earth', '#241f17', 1.0, 0), ('hydrant_red', '#5a1a14', 0.5, 0.2)):
        material(nm, c, rough=r, metal=me)
    AT.pbr('paint_black', nrm='brick_n', rough=0.8, scale=2.0, color='#141414')      # paint on brick, for wall adverts
    AT.pbr('paint_white', nrm='brick_n', rough=0.85, scale=2.0, color='#a39c88')
    AT.pbr('paint_blue', nrm='brick_n', rough=0.85, scale=2.0, color='#27384a')
    AT.lit_windows()
    for k in range(5):
        AT.lit(f'glass_lit{k}', f'glass_lit{k}', strength=(1.6, 1.5, 1.6, 1.1, 1.4)[k])
    material('lamp_glass', '#000000', rough=0.2, emit='#ffcf8a', emit_strength=6.0)
    PAPER.update(AT.paper_atlas())
    material('paper_atlas', rough=0.92, tex=AT.TEX['paper_atlas'], scale=None)


# --- low-level geometry -------------------------------------------------------------------------------

def lquad(F, mat, pts, facing=None, uv=None):
    """A face through local points; turned to face `facing` (a local direction); uv fitted if given."""
    bm = bm_for(mat)
    vs = [bm.verts.new(F @ Vector(p)) for p in pts]
    f = bm.faces.new(vs)
    if facing is not None:
        f.normal_update()
        if f.normal.dot(F.to_3x3() @ Vector(facing)) < 0: f.normal_flip()
    if uv is not None:
        layer = bm.loops.layers.uv.verify()
        m = {v: t for v, t in zip(vs, uv)}
        for loop in f.loops: loop[layer].uv = m[loop.vert]
    return f


def cloth(F, mat, pts, uv=None):
    """Thin sheet seen from both sides (engines cull back faces)."""
    lquad(F, mat, pts, uv=uv)
    lquad(F, mat, pts[::-1], uv=uv[::-1] if uv else None)


I4 = Matrix.Identity(4)


def cbox(F, mat, u0, u1, v0, v1, w0, w1, b=0.012, rot=0.0, tilt=0.0):
    """A box with its edges chamfered by b, so that it catches the light along them. rot: about its vertical
    axis; tilt: about its u axis."""
    if b <= 0 and not tilt:
        return lbox(F, mat, u0, u1, v0, v1, w0, w1, rot)
    hx, hy, hz = abs(u1 - u0) / 2, abs(v1 - v0) / 2, abs(w1 - w0) / 2
    b = min(b, hx * 0.45, hy * 0.45, hz * 0.45)
    c = Vector(((u0 + u1) / 2, (v0 + v1) / 2, (w0 + w1) / 2))
    M = F @ Matrix.Translation(c) @ Matrix.Rotation(rot, 4, 'Y') @ Matrix.Rotation(tilt, 4, 'X')
    bm = bm_for(mat)
    h = (hx, hy, hz)
    V = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                s = (sx, sy, sz)
                for ax in range(3):
                    p = [s[i] * (h[i] - (0 if i == ax else b)) for i in range(3)]
                    V[(s, ax)] = bm.verts.new(M @ Vector(p))

    def face(vs, n):
        f = bm.faces.new(vs)
        f.normal_update()
        if f.normal.dot(M.to_3x3() @ Vector(n)) < 0: f.normal_flip()

    for ax in range(3):
        a1, a2 = [i for i in range(3) if i != ax]
        for s in (-1, 1):   # the six faces
            vs = []
            for t1, t2 in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                k = [0, 0, 0]; k[ax] = s; k[a1] = t1; k[a2] = t2
                vs.append(V[(tuple(k), ax)])
            n = [0, 0, 0]; n[ax] = s
            face(vs, n)
    for ax in range(3):     # the twelve chamfers: edges running along ax
        a1, a2 = [i for i in range(3) if i != ax]
        for t1 in (-1, 1):
            for t2 in (-1, 1):
                vs = []
                for s, fa in ((-1, a1), (1, a1), (1, a2), (-1, a2)):
                    k = [0, 0, 0]; k[ax] = s; k[a1] = t1; k[a2] = t2
                    vs.append(V[(tuple(k), fa)])
                n = [0, 0, 0]; n[a1] = t1; n[a2] = t2
                face(vs, n)
    for sx in (-1, 1):      # the eight corners
        for sy in (-1, 1):
            for sz in (-1, 1):
                s = (sx, sy, sz)
                face([V[(s, 0)], V[(s, 1)], V[(s, 2)]], s)


def extrude(F, mat, poly, a0, a1, axis='u', caps=True, smooth=False):
    """A closed polygon pushed along an axis of the frame. axis 'u': poly is [(w, v)], a moulding running
    along the wall; axis 'w': poly is [(u, v)], a shape standing out of it; axis 'v': poly is [(u, w)]."""
    area = sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))
    sgn = 1 if area > 0 else -1

    def P(p, a):
        return {'u': (a, p[1], p[0]), 'w': (p[0], p[1], a), 'v': (p[0], a, p[1])}[axis]

    def N(n):
        return {'u': (0, n[1], n[0]), 'w': (n[0], n[1], 0), 'v': (n[0], 0, n[1])}[axis]

    for p, q in zip(poly, poly[1:] + poly[:1]):
        n = ((q[1] - p[1]) * sgn, -(q[0] - p[0]) * sgn)
        f = lquad(F, mat, [P(p, a0), P(p, a1), P(q, a1), P(q, a0)], facing=N(n))
        f.smooth = smooth
    if caps:
        ax = {'u': (1, 0, 0), 'w': (0, 0, 1), 'v': (0, 1, 0)}[axis]
        lquad(F, mat, [P(p, a0) for p in poly], facing=tuple(-c for c in ax))
        lquad(F, mat, [P(p, a1) for p in poly], facing=ax)


def wall(F, mat, u0, u1, v0, v1, holes=(), w=0.0):
    """A wall face with rectangular openings (a, b, c, d = u from a to b, v from c to d) left out of it."""
    us = sorted(set([u0, u1] + [x for h in holes for x in h[:2] if u0 < x < u1]))
    vs = sorted(set([v0, v1] + [x for h in holes for x in h[2:] if v0 < x < v1]))
    for a, b in zip(us, us[1:]):
        for c, d in zip(vs, vs[1:]):
            cu, cv = (a + b) / 2, (c + d) / 2
            if any(h[0] < cu < h[1] and h[2] < cv < h[3] for h in holes): continue
            lquad(F, mat, [(a, c, w), (b, c, w), (b, d, w), (a, d, w)], facing=(0, 0, 1))


def reveal(F, mat, a, b, c, d, depth, sides='lrtb'):
    """The four returns of an opening, from the wall face back to -depth."""
    if 'l' in sides: lquad(F, mat, [(a, c, 0), (a, c, -depth), (a, d, -depth), (a, d, 0)], facing=(1, 0, 0))
    if 'r' in sides: lquad(F, mat, [(b, c, 0), (b, c, -depth), (b, d, -depth), (b, d, 0)], facing=(-1, 0, 0))
    if 't' in sides: lquad(F, mat, [(a, d, 0), (b, d, 0), (b, d, -depth), (a, d, -depth)], facing=(0, -1, 0))
    if 'b' in sides: lquad(F, mat, [(a, c, 0), (b, c, 0), (b, c, -depth), (a, c, -depth)], facing=(0, 1, 0))


def pane(F, mat, a, b, c, d, w, lit=None, flip=False):
    """Glass. lit: the name of a lamplit material whose picture is fitted to the pane (flip: mirrored)."""
    if lit:
        uv = [(1, 0), (0, 0), (0, 1), (1, 1)] if flip else [(0, 0), (1, 0), (1, 1), (0, 1)]
        lquad(F, lit, [(a, c, w), (b, c, w), (b, d, w), (a, d, w)], facing=(0, 0, 1), uv=uv)
    else:
        lquad(F, mat, [(a, c, w), (b, c, w), (b, d, w), (a, d, w)], facing=(0, 0, 1))


def sub(F, o, r):
    """A frame standing in F at local point o, its wall running along local direction r = (du, dw)."""
    ru, rw = Vector(r).normalized()
    M = Matrix(((ru, 0, -rw, o[0]), (0, 1, 0, o[1]), (rw, 0, ru, o[2]), (0, 0, 0, 1)))
    return F @ M


def poster(F, name, u, v, w=0.01, rot=0.0, scale=1.0, mat='paper_atlas'):
    """A bill from the atlas pasted on the wall, centred at (u, v)."""
    u0, v0, u1, v1, wm, hm = PAPER[name]
    hw, hh = wm * scale / 2, hm * scale / 2
    c, s = math.cos(rot), math.sin(rot)
    pts = [(u + x * c - y * s, v + x * s + y * c, w) for x, y in ((-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh))]
    lquad(F, mat, pts, facing=(0, 0, 1), uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def sheet(F, name, pts):
    """A bill from the atlas on any four points (a newspaper in the gutter), seen from both sides."""
    u0, v0, u1, v1, wm, hm = PAPER[name]
    cloth(F, 'paper_atlas', pts, uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def arc(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * k / n), cy + r * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]


def rod(mat, a, b, r, seg=6):
    tube(mat, [a, b], r, seg)


def wire3(a, b, sag=0.6, seg=8, r=0.009, mat='iron'):
    pts = []
    for k in range(seg + 1):
        t = k / seg
        p = Vector(a).lerp(Vector(b), t)
        p.y -= sag * 4 * t * (1 - t)
        pts.append(p)
    tube(mat, pts, r, seg=3)
    return pts


def blob(mat, x, z, r, y=0.008, seed=0, n=14, squash=1.0, rot=0.0):
    """An irregular flat patch on the ground (a puddle)."""
    g = random.Random(seed)
    k = [0.65 + 0.5 * g.random() for _ in range(n)]
    k = [(k[i] + k[(i + 1) % n] + k[i - 1]) / 3 for i in range(n)]
    pts = []
    for i in range(n):
        a = i / n * math.tau
        px, pz = math.cos(a) * r * k[i], math.sin(a) * r * k[i] * squash
        pts.append((x + px * math.cos(rot) - pz * math.sin(rot), y, z + px * math.sin(rot) + pz * math.cos(rot)))
    lquad(I4, mat, pts, facing=(0, 1, 0))


# --- windows and doors --------------------------------------------------------------------------------

def console(F, mat, u, v_top, depth, drop, width=0.1):
    """A scrolled bracket under a cornice or hood, its top at v_top."""
    d, h = depth, drop
    prof = [(0, 0), (d, 0), (d, -0.12 * h), (d * 0.8, -0.26 * h), (d * 0.5, -0.42 * h), (d * 0.32, -0.66 * h),
            (d * 0.28, -0.86 * h), (d * 0.16, -h), (0, -h)]
    extrude(F, mat, [(w, v_top + v) for w, v in prof], u - width / 2, u + width / 2)


def window_head(F, kind, a, b, t, trim, stone='stone'):
    """What sits over an opening whose top is at t, between a and b."""
    if kind == 'lintel':       # a stone lintel with a keystone
        cbox(F, stone, a - 0.14, b + 0.14, t, t + 0.22, -0.03, 0.02, b=0.008)
        cbox(F, stone, (a + b) / 2 - 0.07, (a + b) / 2 + 0.07, t - 0.005, t + 0.25, -0.02, 0.035, b=0.008)
    elif kind == 'arch':       # a segmental arch of dressed stone over a sunk, boarded tympanum
        w = b - a
        rise = 0.2
        r = (w * w / 4 + rise * rise) / (2 * rise)
        cy = t + rise - r
        half = math.asin(w / 2 / r)
        inner = arc((a + b) / 2, cy, r, math.pi / 2 + half, math.pi / 2 - half, 6)
        outer = arc((a + b) / 2, cy, r + 0.17, math.pi / 2 + half * 1.1, math.pi / 2 - half * 1.1, 6)
        extrude(F, trim, [(a, t)] + inner + [(b, t)], -0.09, -0.06, axis='w')
        for (p0, p1), (q0, q1) in zip(zip(inner, inner[1:]), zip(outer, outer[1:])):
            extrude(F, stone, [p0, p1, q1, q0], -0.09, 0.03, axis='w')
    elif kind == 'hood':       # a bracketed Italianate hood
        lbox(F, trim, a - 0.12, b + 0.12, t, t + 0.2, 0, 0.035)
        prof = [(0, 0.2), (0.06, 0.2), (0.1, 0.25), (0.19, 0.28), (0.19, 0.33), (0.0, 0.36)]
        extrude(F, trim, [(w, t + v) for w, v in prof], a - 0.2, b + 0.2)
        for u in (a - 0.07, b + 0.07):
            console(F, trim, u, t + 0.2, 0.15, 0.34, 0.09)
    elif kind == 'pediment':   # a little triangular pediment
        lbox(F, trim, a - 0.12, b + 0.12, t, t + 0.14, 0, 0.035)
        prof = [(0, 0.14), (0.08, 0.14), (0.14, 0.2), (0.14, 0.24), (0, 0.24)]
        extrude(F, trim, [(w, t + v) for w, v in prof], a - 0.2, b + 0.2)
        m = (a + b) / 2
        extrude(F, trim, [(a - 0.2, t + 0.24), (b + 0.2, t + 0.24), (m, t + 0.24 + (b - a) * 0.32)], 0.0, 0.1, axis='w')
        extrude(F, trim, [(a - 0.26, t + 0.24), (a - 0.2, t + 0.24), (m, t + 0.24 + (b - a) * 0.32), (m, t + 0.3 + (b - a) * 0.32)], 0.0, 0.16, axis='w')
        extrude(F, trim, [(b + 0.26, t + 0.24), (b + 0.2, t + 0.24), (m, t + 0.24 + (b - a) * 0.32), (m, t + 0.3 + (b - a) * 0.32)], 0.0, 0.16, axis='w')
    elif kind == 'cap':        # a plain moulded cap
        prof = [(0, 0.0), (0.04, 0.0), (0.05, 0.08), (0.11, 0.12), (0.11, 0.16), (0, 0.18)]
        extrude(F, trim, [(w, t + v) for w, v in prof], a - 0.14, b + 0.14)


def sash_window(F, u, v, w=0.95, h=1.8, wall_mat='brick_red', trim='trim_cream', head='lintel', depth=0.18,
                state='dark', sill='stone', casing=False, shutters=None, bars=1, blind=None, seed=None):
    """A double-hung sash window set back in the wall: sill at v, centred on u. Returns its hole for wall().
    state: 'dark' | 'lit0'..'lit3' | 'boarded'.  shutters: None | 'shut' | 'open' (iron fire shutters).
    blind: None, or (material, fraction drawn down)."""
    a, b, c, d = u - w / 2, u + w / 2, v, v + h
    reveal(F, trim if casing else wall_mat, a, b, c, d, depth)
    g = -depth
    if shutters == 'shut':
        for k, (x0, x1) in enumerate(((a, u - 0.008), (u + 0.008, b))):
            lbox(F, 'iron_rust', x0, x1, c, d, -0.06, -0.035)
            for vv in (c + 0.22 * h, c + 0.78 * h):   # strap hinges
                lbox(F, 'iron', x0 if k == 0 else x1 - 0.3, x0 + 0.3 if k == 0 else x1, vv - 0.025, vv + 0.025, -0.035, -0.027)
        lbox(F, 'iron', a + 0.1, b - 0.1, c + h * 0.5 - 0.02, c + h * 0.5 + 0.02, -0.035, -0.02)   # the bar across
        lquad(F, 'roof', [(a, c, g), (b, c, g), (b, d, g), (a, d, g)], facing=(0, 0, 1))
    elif state == 'boarded':
        lquad(F, 'roof', [(a, c, g), (b, c, g), (b, d, g), (a, d, g)], facing=(0, 0, 1))
        r = random.Random(seed or int(u * 31 + v * 7))
        vv = c + 0.03
        while vv < d - 0.1:
            bh = 0.16 + 0.06 * r.random()
            lbox(F, 'wood_fence', a - 0.0, b + 0.0, vv, min(d, vv + bh), -0.07, -0.045, rot=(r.random() - 0.5) * 0.03)
            vv += bh + 0.01 + 0.05 * r.random()
    else:
        mid = c + h * 0.5
        lit_mat = ('glass_' + state) if state.startswith('lit') else None
        if lit_mat:
            pane(F, None, a, b, c, d, g + 0.012, lit=lit_mat)
        else:
            pane(F, 'glass_dark', a, b, c, mid, g + 0.012)
            pane(F, 'glass_dark', a, b, mid, d, g + 0.034)
            if blind:
                bm_, fr = blind
                pane(F, bm_, a + 0.04, b - 0.04, d - (h - 0.1) * fr, d - 0.04, g + 0.04)
        t = 0.05
        lbox(F, trim, a, a + t, c, d, g, g + 0.06)
        lbox(F, trim, b - t, b, c, d, g, g + 0.06)
        lbox(F, trim, a + t, b - t, d - t, d, g, g + 0.06)
        lbox(F, trim, a + t, b - t, c, c + 0.07, g, g + 0.045)
        lbox(F, trim, a + t, b - t, mid - 0.022, mid + 0.022, g, g + 0.06)
        if not (lit_mat and state in ('lit0', 'lit3')):   # those pictures carry their own glazing bars
            for k in range(bars):
                x = a + (k + 1) * w / (bars + 1)
                if lit_mat or not blind:
                    lbox(F, trim, x - 0.012, x + 0.012, c + 0.07, mid - 0.022, g + 0.012, g + 0.04)
                lbox(F, trim, x - 0.012, x + 0.012, mid + 0.022, d - t, g + 0.03, g + 0.058)
    if shutters == 'open':
        lw = w / 2
        for s, x0 in ((-1, a - lw - 0.03), (1, b + 0.03)):
            lbox(F, 'iron_rust', x0, x0 + lw, c, d, 0.012, 0.035)
            for vv in (c + 0.22 * h, c + 0.78 * h):
                lbox(F, 'iron', x0 + (lw - 0.3 if s < 0 else 0), x0 + (lw if s < 0 else 0.3), vv - 0.025, vv + 0.025, 0.035, 0.043)
    if casing:
        lbox(F, trim, a - 0.11, a, c, d, 0, 0.03)
        lbox(F, trim, b, b + 0.11, c, d, 0, 0.03)
        lbox(F, trim, a - 0.11, b + 0.11, d, d + 0.03, 0, 0.03)
    if sill:
        cbox(F, sill, a - 0.13, b + 0.13, c - 0.08, c, -depth * 0.6, 0.085, b=0.012)
        if casing:
            for x in (a - 0.05, b + 0.05):
                lbox(F, trim, x - 0.04, x + 0.04, c - 0.2, c - 0.08, 0, 0.05)
    window_head(F, head, a, b, d, trim, stone=sill or 'stone')
    return (a, b, c, d)


def plank_door(F, u, w=1.1, h=2.2, wall_mat='brick_red', trim='trim_dark', leaf='door_wood', depth=0.22, step=0.16,
               head='lintel', transom=True, v0=0.0, lit=None, strap=True, stepdepth=0.42):
    """A back door: boarded leaf with strap hinges set back in the wall, a transom light, a worn stone step."""
    a, b = u - w / 2, u + w / 2
    c = v0 + step
    top = c + h + (0.42 if transom else 0)
    reveal(F, wall_mat, a, b, c, top, depth, 'lrt')
    g = -depth
    t = 0.07
    lbox(F, trim, a, a + t, c, top, g, g + 0.08)
    lbox(F, trim, b - t, b, c, top, g, g + 0.08)
    lbox(F, trim, a + t, b - t, top - t, top, g, g + 0.08)
    lbox(F, leaf, a + t, b - t, c, c + h, g, g + 0.045)
    for vv in (c + 0.3, c + h * 0.5, c + h - 0.3):      # ledges across the boards
        lbox(F, leaf, a + t + 0.02, b - t - 0.02, vv - 0.07, vv + 0.07, g + 0.045, g + 0.07)
    if strap:
        for vv in (c + 0.3, c + h - 0.3):
            lbox(F, 'iron', a + t, a + t + 0.5, vv - 0.02, vv + 0.02, g + 0.07, g + 0.08)
    sphere('iron', F @ Vector((b - t - 0.12, c + h * 0.47, g + 0.09)), 0.035, 8)
    lbox(F, 'iron', b - t - 0.16, b - t - 0.08, c + h * 0.47 - 0.1, c + h * 0.47 + 0.1, g + 0.045, g + 0.052)
    if transom:
        lbox(F, trim, a + t, b - t, c + h, c + h + 0.06, g, g + 0.08)
        pane(F, 'glass_dark', a + t, b - t, c + h + 0.06, top - t, g + 0.02, lit=lit)
        lbox(F, trim, u - 0.012, u + 0.012, c + h + 0.06, top - t, g + 0.02, g + 0.05)
    if step:
        cbox(F, 'stone', a - 0.12, b + 0.12, v0, c, -depth, stepdepth, b=0.02)
    else:
        lquad(F, 'stone', [(a, c, 0), (b, c, 0), (b, c, -depth), (a, c, -depth)], facing=(0, 1, 0))
    window_head(F, head, a, b, top, trim)
    return (a, b, c, top)


def panel_door(F, a, b, c, h, w0, leaf='door_wood', glazed=True, lit=None, knob_right=True):
    """A panelled shop door leaf in the plane w0 (facing +w): stiles and rails proud of sunk panels."""
    d = c + h
    lbox(F, leaf, a, b, c, d, w0 - 0.04, w0)
    s = 0.11
    for x0, x1, y0, y1 in ((a, a + s, c, d), (b - s, b, c, d), (a + s, b - s, c, c + 0.22), (a + s, b - s, d - 0.14, d),
                           (a + s, b - s, c + h * 0.42, c + h * 0.42 + 0.14)):
        lbox(F, leaf, x0, x1, y0, y1, w0, w0 + 0.022)
    if glazed:
        pane(F, 'glass_dark', a + s, b - s, c + h * 0.42 + 0.14, d - 0.14, w0 + 0.012, lit=lit)
    kx = b - s / 2 if knob_right else a + s / 2
    sphere('brass', F @ Vector((kx, c + h * 0.45, w0 + 0.05)), 0.028, 8)
    lbox(F, 'brass', kx - 0.025, kx + 0.025, c + h * 0.45 - 0.09, c + h * 0.45 + 0.09, w0 + 0.022, w0 + 0.028)


# --- cornices, bays, fronts ---------------------------------------------------------------------------

def cornice2(F, u0, u1, top, trim='trim_cream', depth=0.6, height=1.0, brackets=1.1, dentils=False, panels=True,
             returns=True):
    """A bracketed Italianate cornice, its top at `top`: frieze, bed moulding, consoles, a deep moulded crown."""
    v0 = top - height
    lbox(F, trim, u0, u1, v0, top - 0.3, 0, 0.05)                           # frieze board
    extrude(F, trim, [(0, v0 - 0.06), (0.1, v0 - 0.03), (0.1, v0 + 0.04), (0.05, v0 + 0.08), (0, v0 + 0.08)], u0 - 0.04, u1 + 0.04)
    e = 0.12 if returns else 0.0
    crown = [(0, top - 0.34), (depth * 0.5, top - 0.34), (depth * 0.56, top - 0.27), (depth * 0.86, top - 0.2), (depth * 0.9, top - 0.13),
             (depth, top - 0.1), (depth, top - 0.02), (depth * 0.9, top), (0, top)]
    extrude(F, trim, crown, u0 - e, u1 + e)
    n = max(2, int(round((u1 - u0) / brackets)))
    xs = [u0 + 0.14 + k * (u1 - u0 - 0.28) / n for k in range(n + 1)]
    for x in xs:
        console(F, trim, x, top - 0.34, depth * 0.52, height - 0.42, 0.12)
    if panels:
        for x0, x1 in zip(xs, xs[1:]):
            lbox(F, trim, x0 + 0.16, x1 - 0.16, v0 + 0.16, top - 0.42, 0.05, 0.065)
    if dentils:
        k = int((u1 - u0) / 0.16)
        for i in range(k):
            x = u0 + (i + 0.5) * (u1 - u0) / k
            lbox(F, trim, x - 0.04, x + 0.04, top - 0.42, top - 0.34, 0.05, 0.14)


def gable_parapet(F, u0, u1, top, wall_mat, trim, rise=1.5, text_s=None):
    """A false front: the wall carried up above the cornice into a stepped gable with a moulded coping."""
    m = (u0 + u1) / 2
    hw = (u1 - u0) * 0.3
    poly = [(u0, top), (u1, top), (u1, top + 0.35), (m + hw, top + 0.35), (m + hw * 0.55, top + rise), (m - hw * 0.55, top + rise),
            (m - hw, top + 0.35), (u0, top + 0.35)]
    extrude(F, wall_mat, poly, -0.25, 0.0, axis='w')
    for p, q in zip(poly[1:], poly[2:]):
        dx, dy = q[0] - p[0], q[1] - p[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L
        extrude(F, trim, [p, q, (q[0] + nx * 0.09, q[1] + ny * 0.09), (p[0] + nx * 0.09, p[1] + ny * 0.09)], -0.3, 0.07, axis='w')
    if text_s:
        text('paint_faded', text_s, F, m, top + 0.35 + (rise - 0.35) * 0.45, 0.0, min(0.5, hw * 1.5 / max(3, len(text_s))))


def bay2(F, u, v0, sills, wh, width=2.4, depth=0.7, wall_mat='clap_cream', trim='trim_cream', states=None):
    """The San Francisco bay window: three-sided, bracketed underneath, panelled below each window (sills at the
    given heights, wh tall), capped with its own little cornice."""
    fw = width - 2 * depth
    v1 = sills[-1] + wh + 0.42
    faces = [(sub(F, (u - width / 2, 0, 0), (1, 1)), depth * math.sqrt(2)),
             (sub(F, (u - fw / 2, 0, depth), (1, 0)), fw),
             (sub(F, (u + fw / 2, 0, depth), (1, -1)), depth * math.sqrt(2))]
    k = 0
    for Fs, L in faces:
        holes = []
        floor = v0
        for sv in sills:
            ww = L - 0.36
            st = (states[k % len(states)] if states else 'dark'); k += 1
            holes.append(sash_window(Fs, L / 2, sv, w=ww, h=wh, wall_mat=trim, trim=trim, head=None, depth=0.07,
                                     state=st, sill=None, bars=1 if ww > 0.75 else 0,
                                     blind=('blind_cream', 0.3 + 0.4 * rnd.random()) if rnd.random() < 0.45 and st == 'dark' else None))
            lbox(Fs, trim, 0.06, L - 0.06, sv - 0.07, sv, 0, 0.05)                      # sill
            lbox(Fs, trim, 0.16, L - 0.16, floor + 0.16, sv - 0.2, 0, 0.022)             # the panel under it
            lbox(Fs, trim, 0.0, L, sv + wh + 0.1, sv + wh + 0.22, 0, 0.03)
            floor = sv + wh + 0.22
        wall(Fs, wall_mat, 0, L, v0, v1, holes)
        for x in (0.0, L):
            lbox(Fs, trim, x - 0.06, x + 0.06, v0, v1, -0.02, 0.035)                        # corner boards
        lbox(Fs, trim, -0.04, L + 0.04, v1 - 0.2, v1 - 0.06, 0, 0.04)                        # the cap
        extrude(Fs, trim, [(0, v1 - 0.1), (0.07, v1 - 0.1), (0.1, v1 - 0.04), (0.2, v1), (0.2, v1 + 0.06), (0, v1 + 0.1)], -0.1, L + 0.1)
        extrude(Fs, trim, [(0, v0 - 0.16), (0.06, v0 - 0.16), (0.1, v0 - 0.06), (0.1, v0), (0, v0)], -0.06, L + 0.06)
    hull = [(u - width / 2 - 0.1, -0.02), (u - fw / 2 - 0.05, depth + 0.1), (u + fw / 2 + 0.05, depth + 0.1), (u + width / 2 + 0.1, -0.02)]
    lquad(F, 'roof', [(x, v1 + 0.1, w) for x, w in hull], facing=(0, 1, 0))
    extrude(F, trim, [(u - width / 2, 0.0), (u - fw / 2, depth), (u + fw / 2, depth), (u + width / 2, 0.0)], v0 - 0.3, v0 - 0.16, axis='v')
    for x in (u - fw / 2 + 0.05, u + fw / 2 - 0.05):
        console(F, trim, x, v0 - 0.3, depth * 0.9, 0.75, 0.13)


def upper_floors(F, u0, u1, v0, top, wall_mat, trim, floors, bays=(), head='hood', win_w=1.0, win_h=None, per=2.7,
                 lit=(), casing=None, depth=None, cornice=True, cornice_h=1.0, cornice_d=0.6, dentils=False, belt=True,
                 blinds=0.4, quoins=False, pilasters=False, sill='stone', states=None, bay_floors=None):
    """The storeys above a shopfront: a wall with recessed sashes or bays, belt courses, and a cornice."""
    wood = wall_mat.startswith('clap')
    casing = wood if casing is None else casing
    depth = (0.1 if wood else 0.2) if depth is None else depth
    pitch = (top - cornice_h - v0) / floors
    wh = win_h or min(2.0, pitch - 1.2)
    n = max(1, int(round((u1 - u0) / per)))
    holes = []
    taken = [(c - 1.45, c + 1.45) for c in bays]
    k = 0
    for f in range(floors):
        sv = v0 + f * pitch + 0.62
        for i in range(n):
            u = u0 + (i + 0.5) * (u1 - u0) / n
            if any(a < u < b for a, b in taken): continue
            st = 'dark'
            if (f, i) in lit: st = lit[(f, i)] if isinstance(lit, dict) else 'lit0'
            bl = None
            if st == 'dark' and rnd.random() < blinds:
                bl = ('blind_green' if rnd.random() < 0.3 else 'blind_cream', 0.2 + 0.7 * rnd.random())
            holes.append(sash_window(F, u, sv, w=win_w, h=wh, wall_mat=wall_mat, trim=trim, head=head, depth=depth, state=st,
                                     casing=casing, blind=bl, sill=(trim if wood else sill)))
        if belt and f > 0:
            extrude(F, trim if wood else 'stone', [(0, sv - 0.5), (0.05, sv - 0.48), (0.07, sv - 0.4), (0.05, sv - 0.36), (0, sv - 0.36)], u0, u1)
    wall(F, wall_mat, u0, u1, v0, top - (0.25 if cornice else 0), holes)
    for c in bays:
        bf = bay_floors or floors
        bay2(F, c, v0 + 0.32, [v0 + f * pitch + 0.62 for f in range(bf)], wh, wall_mat=wall_mat, trim=trim, states=states)
    if quoins:
        for x, s in ((u0, 1), (u1, -1)):
            vv = v0
            i = 0
            while vv < top - cornice_h - 0.3:
                L = 0.5 if i % 2 == 0 else 0.3
                cbox(F, 'stone', min(x, x + s * L), max(x, x + s * L), vv + 0.01, vv + 0.39, 0.0, 0.04, b=0.012)
                vv += 0.4; i += 1
    if pilasters:
        for x in (u0 + 0.22, u1 - 0.22):
            lbox(F, trim, x - 0.2, x + 0.2, v0, top - cornice_h, 0, 0.06)
            lbox(F, trim, x - 0.13, x + 0.13, v0 + 0.3, top - cornice_h - 0.3, 0.06, 0.075)
    if cornice:
        cornice2(F, u0, u1, top, trim, depth=cornice_d, height=cornice_h, dentils=dentils)
    return pitch


def fascia(F, u0, u1, v, sign, sign_mat='sign_board', trim='trim_cream', h=0.72, letter='gilt', size=None):
    """The shop's signboard and the moulded shelf over it."""
    lbox(F, sign_mat, u0, u1, v, v + h, 0.0, 0.07)
    for vv in (v, v + h - 0.035):
        lbox(F, letter if letter == 'gilt' else trim, u0 + 0.06, u1 - 0.06, vv + 0.0, vv + 0.035, 0.07, 0.08)
    extrude(F, trim, [(0, v + h), (0.1, v + h), (0.14, v + h + 0.07), (0.3, v + h + 0.12), (0.3, v + h + 0.18), (0, v + h + 0.22)], u0 - 0.06, u1 + 0.06)
    extrude(F, trim, [(0, v - 0.08), (0.12, v - 0.08), (0.12, v - 0.03), (0.08, v), (0, v)], u0 - 0.03, u1 + 0.03)
    if sign:
        s = size or min(0.46, (u1 - u0 - 0.8) / max(4, len(sign)) * 1.5)
        text(letter, sign, F, (u0 + u1) / 2, v + h / 2, 0.072, s)


def iron_pier(F, u, h, wd=0.34, mat='iron', proud=0.1):
    """A cast-iron shopfront pilaster: plinth, panelled shaft, capital."""
    cbox(F, mat, u - wd / 2, u + wd / 2, 0.02, h, -0.12, proud, b=0.012)
    cbox(F, mat, u - wd / 2 - 0.04, u + wd / 2 + 0.04, 0.0, 0.42, -0.12, proud + 0.04, b=0.015)
    lbox(F, mat, u - wd / 2 + 0.07, u + wd / 2 - 0.07, 0.62, h - 0.5, proud, proud + 0.015)
    extrude(F, mat, [(proud, h - 0.3), (proud + 0.04, h - 0.26), (proud + 0.04, h - 0.2), (proud + 0.09, h - 0.12), (proud + 0.09, h), (-0.1, h), (-0.1, h - 0.3)],
            u - wd / 2 - 0.05, u + wd / 2 + 0.05)


def display_bay(F, a, b, h, trim, bulk='door_wood', lit=None, w0=-0.1, transom_v=2.72, blind=None, glazing=1, bulk_h=0.58,
                letters=None, flip=False):
    """One bay of plate glass over a panelled bulkhead, with a transom light above."""
    lbox(F, bulk, a, b, 0, bulk_h, w0 - 0.06, w0 + 0.02)
    n = max(1, int((b - a) / 1.1))
    for k in range(n):
        x0, x1 = a + 0.1 + k * (b - a - 0.2) / n, a + 0.1 + (k + 1) * (b - a - 0.2) / n
        lbox(F, bulk, x0 + 0.05, x1 - 0.05, 0.12, bulk_h - 0.1, w0 + 0.02, w0 + 0.04)
    extrude(F, trim, [(w0 - 0.06, bulk_h), (w0 + 0.07, bulk_h), (w0 + 0.09, bulk_h + 0.03), (w0 + 0.03, bulk_h + 0.07), (w0 - 0.06, bulk_h + 0.07)], a, b)
    pane(F, 'glass_dark', a, b, bulk_h + 0.07, transom_v, w0, lit=lit, flip=flip)
    if blind and not lit:
        pane(F, blind[0], a + 0.03, b - 0.03, transom_v - (transom_v - bulk_h) * blind[1], transom_v, w0 + 0.012)
    for k in range(1, glazing + 1):
        x = a + k * (b - a) / (glazing + 1)
        lbox(F, trim, x - 0.018, x + 0.018, bulk_h + 0.07, transom_v, w0, w0 + 0.035)
    lbox(F, trim, a, b, transom_v, transom_v + 0.08, w0 - 0.02, w0 + 0.05)
    pane(F, 'glass_dark', a, b, transom_v + 0.08, h - 0.06, w0, lit=('glass_lit4' if lit else None))
    m = max(2, int((b - a) / 0.55))
    for k in range(1, m):
        x = a + k * (b - a) / m
        lbox(F, trim, x - 0.012, x + 0.012, transom_v + 0.08, h - 0.06, w0, w0 + 0.03)
    lbox(F, trim, a, b, h - 0.06, h, w0 - 0.02, w0 + 0.05)
    if letters:
        text('gilt', letters, F, (a + b) / 2, 1.75, w0 + 0.002, min(0.2, (b - a - 0.4) / max(4, len(letters)) * 1.5))


def entry_bay(F, a, b, h, trim, leaf='door_wood', lit=None, w0=-0.1, deep=0.85, transom_v=2.72, double=True, bulk='door_wood'):
    """A recessed shop entrance: splayed side lights, a stone threshold, panelled doors under a transom."""
    sp = 0.42 if (b - a) > 2.0 else 0.25
    soft = 'glass_lit4' if lit else None
    r = w0 - deep
    lquad(F, 'stone', [(a, 0.03, w0 + 0.1), (b, 0.03, w0 + 0.1), (b - sp, 0.03, r), (a + sp, 0.03, r)], facing=(0, 1, 0))
    lquad(F, 'stone', [(a, 0.0, w0 + 0.1), (b, 0.0, w0 + 0.1), (b, 0.03, w0 + 0.1), (a, 0.03, w0 + 0.1)], facing=(0, 0, 1))
    lquad(F, trim, [(a, transom_v, w0), (b, transom_v, w0), (b - sp, transom_v, r), (a + sp, transom_v, r)], facing=(0, -1, 0))
    for s, (p, q) in ((1, ((a, w0), (a + sp, r))), (-1, ((b - sp, r), (b, w0)))):
        Fs = sub(F, (p[0], 0, p[1]), (q[0] - p[0], q[1] - p[1]))
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        lbox(Fs, bulk, 0, L, 0.03, 0.58, -0.05, 0.0)
        lbox(Fs, trim, 0, L, 0.58, 0.65, -0.05, 0.03)
        pane(Fs, 'glass_dark', 0, L, 0.65, transom_v, -0.01, lit=soft)
        lbox(Fs, trim, -0.03, 0.03, 0.03, transom_v, -0.04, 0.03)
        lbox(Fs, trim, L - 0.03, L + 0.03, 0.03, transom_v, -0.04, 0.03)
    da, db = a + sp, b - sp
    lbox(F, trim, da, da + 0.06, 0.03, transom_v, r - 0.03, r + 0.05)
    lbox(F, trim, db - 0.06, db, 0.03, transom_v, r - 0.03, r + 0.05)
    if double and db - da > 1.5:
        m = (da + db) / 2
        panel_door(F, da + 0.06, m - 0.005, 0.03, 2.2, r, leaf, lit=soft, knob_right=True)
        panel_door(F, m + 0.005, db - 0.06, 0.03, 2.2, r, leaf, lit=soft, knob_right=False)
    else:
        panel_door(F, da + 0.06, db - 0.06, 0.03, 2.2, r, leaf, lit=soft)
    lbox(F, trim, da, db, 2.23, 2.31, r - 0.03, r + 0.05)
    pane(F, 'glass_dark', da + 0.06, db - 0.06, 2.31, transom_v, r, lit=soft)
    # over the recess, the transom lights carry across on the front plane
    lbox(F, trim, a, b, transom_v, transom_v + 0.08, w0 - 0.02, w0 + 0.05)
    pane(F, 'glass_dark', a, b, transom_v + 0.08, h - 0.06, w0, lit=soft)
    m = max(2, int((b - a) / 0.55))
    for k in range(1, m):
        x = a + k * (b - a) / m
        lbox(F, trim, x - 0.012, x + 0.012, transom_v + 0.08, h - 0.06, w0, w0 + 0.03)
    lbox(F, trim, a, b, h - 0.06, h, w0 - 0.02, w0 + 0.05)


def shopfront2(F, u0, u1, sign, h=3.5, trim='trim_cream', pier='iron', sign_mat='sign_board', bays=None, door=None, lit=None,
               leaf='door_wood', bulk='door_wood', blinds=0.5, glazing=1, letters=None, fascia_h=0.72, wall_mat=None,
               double=True, lit_bays=None):
    """A whole shopfront between u0 and u1: piers, display bays, a recessed entrance, signboard and shelf.
    wall_mat: build the end piers of the wall's own masonry instead of cast iron. Returns the top of it."""
    n = bays or max(2, int(round((u1 - u0) / 3.0)))
    door = n // 2 if door is None else door
    pw = 0.36
    xs = [u0 + pw / 2 + k * (u1 - u0 - pw) / n for k in range(n + 1)]
    for k, x in enumerate(xs):
        if wall_mat and k in (0, n):
            cbox(F, wall_mat, x - pw / 2, x + pw / 2, 0, h, -0.14, 0.0, b=0.0)
            cbox(F, 'stone', x - pw / 2 - 0.03, x + pw / 2 + 0.03, 0, 0.5, -0.14, 0.04, b=0.015)
            cbox(F, 'stone', x - pw / 2 - 0.03, x + pw / 2 + 0.03, h - 0.22, h, -0.14, 0.05, b=0.015)
        else:
            iron_pier(F, x, h, pw if k in (0, n) else 0.2, pier)
    for k in range(n):
        a = xs[k] + (pw / 2 if k == 0 else 0.1)
        b = xs[k + 1] - (pw / 2 if k == n - 1 else 0.1)
        lt = lit if (lit_bays is None or k in lit_bays) else None
        if k == door:
            entry_bay(F, a, b, h, trim, leaf, lit=lt, double=double, bulk=bulk)
        else:
            display_bay(F, a, b, h, trim, bulk, lit=lt, glazing=glazing, letters=(letters or {}).get(k), flip=k % 2 == 1)
    fascia(F, u0, u1, h + 0.08, sign, sign_mat, trim, h=fascia_h)
    return h + 0.08 + fascia_h + 0.22


def awning(F, u0, u1, v, out=1.5, drop=0.75, mat='cloth_awning', valance=0.22):
    """A canvas roller awning let down on its iron arms."""
    v1 = v - drop
    cloth(F, mat, [(u0, v, 0.06), (u1, v, 0.06), (u1, v1, out), (u0, v1, out)])
    n = max(4, int((u1 - u0) / 0.3))
    for k in range(n):     # a scalloped valance
        a, b = u0 + k * (u1 - u0) / n, u0 + (k + 1) * (u1 - u0) / n
        cloth(F, mat, [(a, v1, out), (b, v1, out), (b - 0.04, v1 - valance, out + 0.01), (a + 0.04, v1 - valance, out + 0.01)])
    for u in (u0, u1):
        cloth(F, mat, [(u, v, 0.06), (u, v1, out), (u, v1, 0.06)])
        rod('iron', F @ Vector((u, v1, out)), F @ Vector((u, v1 - 0.55, 0.06)), 0.012, 4)
    rod('iron', F @ Vector((u0, v1, out)), F @ Vector((u1, v1, out)), 0.014, 4)
    cyl('iron', F @ Vector((u0 - 0.05, v + 0.03, 0.09)), u1 - u0 + 0.1, 0.045, seg=6, axis=(F.to_3x3() @ Vector((1, 0, 0))))


def hanging_sign(F, u, v, name, out=1.1, mat='paper_atlas', scale=1.0):
    """A painted board hung square to the wall from a scrolled iron bracket, lettered on both sides."""
    u0, v0, u1, v1, wm, hm = PAPER[name]
    wm, hm = wm * scale, hm * scale
    rod('iron', F @ Vector((u, v, 0)), F @ Vector((u, v, out + 0.15)), 0.016, 5)
    rod('iron', F @ Vector((u, v - 0.5, 0)), F @ Vector((u, v, out * 0.6)), 0.012, 4)
    tube('iron', [F @ Vector((u, v - 0.06 - 0.1 * math.sin(t * 5), out * 0.6 + t * (out * 0.4 + 0.15))) for t in np.linspace(0, 1, 6)], 0.008, 4)
    w0 = out + 0.1 - wm
    top = v - 0.12
    for x in (w0 + 0.08, w0 + wm - 0.08):
        rod('iron', F @ Vector((u, v, x)), F @ Vector((u, top, x)), 0.006, 3)
    Fb = sub(F, (u, 0, w0), (0, 1))
    lbox(Fb, 'door_wood', -0.03, wm + 0.03, top - hm - 0.03, top + 0.03, -0.02, 0.02)
    uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    lquad(Fb, mat, [(0, top - hm, 0.023), (wm, top - hm, 0.023), (wm, top, 0.023), (0, top, 0.023)], facing=(0, 0, 1), uv=uv)
    lquad(Fb, mat, [(wm, top - hm, -0.023), (0, top - hm, -0.023), (0, top, -0.023), (wm, top, -0.023)], facing=(0, 0, -1), uv=uv)


# --- street furniture ---------------------------------------------------------------------------------

def street_lamp(x, z, y=0.15):
    """A San Francisco gas lamp: cast-iron post with a ladder bar, a square tapered lantern under a vented
    roof. Returns the centre of the glass (for the Lamp_ marker)."""
    i = 'iron'
    cyl(i, (x, y, z), 0.1, 0.2, 0.19, seg=8)
    cyl(i, (x, y + 0.1, z), 0.5, 0.16, 0.11, seg=8)
    cyl(i, (x, y + 0.6, z), 0.07, 0.135, 0.135, seg=8)
    cyl(i, (x, y + 0.67, z), 0.25, 0.1, 0.075, seg=8, cap=False)
    cyl(i, (x, y + 0.92, z), 1.5, 0.075, 0.052, seg=10, cap=False)
    cyl(i, (x, y + 2.42, z), 0.06, 0.085, 0.085, seg=8)
    cyl(i, (x, y + 2.48, z), 0.38, 0.05, 0.045, seg=8, cap=False)
    yb = y + 2.55
    rod(i, (x - 0.45, yb, z), (x + 0.45, yb, z), 0.016, 5)             # the lamplighter's ladder bar
    for s in (-1, 1): sphere(i, (x + s * 0.46, yb, z), 0.03, 6)
    y0, y1 = y + 2.98, y + 3.52                                          # the lantern
    r0, r1 = 0.105, 0.2
    cyl(i, (x, y + 2.86, z), 0.05, 0.05, 0.09, seg=8)
    for s1, s2 in ((1, 1), (1, -1), (-1, -1), (-1, 1)):                  # frog arms to the lantern's corners
        tube(i, [(x + s1 * 0.04, y + 2.84, z + s2 * 0.04), (x + s1 * 0.12, y + 2.9, z + s2 * 0.12), (x + s1 * r0, y0, z + s2 * r0)], 0.011, 4)
        tube(i, [(x + s1 * r0, y0, z + s2 * r0), (x + s1 * r1, y1, z + s2 * r1)], 0.011, 4)
    cs = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
    for (a1, a2), (b1, b2) in zip(cs, cs[1:] + cs[:1]):
        lquad(I4, 'lamp_glass', [(x + a1 * r0, y0, z + a2 * r0), (x + b1 * r0, y0, z + b2 * r0), (x + b1 * r1, y1, z + b2 * r1), (x + a1 * r1, y1, z + a2 * r1)],
              facing=((a1 + b1) / 2, 0.2, (a2 + b2) / 2))
        rod(i, (x + a1 * r0, y0, z + a2 * r0), (x + b1 * r0, y0, z + b2 * r0), 0.01, 4)
        rod(i, (x + a1 * r1, y1, z + a2 * r1), (x + b1 * r1, y1, z + b2 * r1), 0.013, 4)
        lquad(I4, i, [(x + a1 * (r1 + 0.03), y1, z + a2 * (r1 + 0.03)), (x + b1 * (r1 + 0.03), y1, z + b2 * (r1 + 0.03)),
                      (x + b1 * 0.07, y1 + 0.17, z + b2 * 0.07), (x + a1 * 0.07, y1 + 0.17, z + a2 * 0.07)], facing=((a1 + b1) / 2, 1, (a2 + b2) / 2))
    lquad(I4, i, [(x + a * r0, y0, z + b * r0) for a, b in cs], facing=(0, -1, 0))
    lquad(I4, i, [(x + a * (r1 + 0.03), y1, z + b * (r1 + 0.03)) for a, b in cs], facing=(0, -1, 0))
    cyl(i, (x, y1 + 0.17, z), 0.09, 0.07, 0.06, seg=8)
    cyl(i, (x, y1 + 0.26, z), 0.03, 0.1, 0.03, seg=8)
    sphere(i, (x, y1 + 0.32, z), 0.03, 6)
    return Vector((x, (y0 + y1) / 2, z))


def wall_lamp(x_wall, y, z, out=1):
    """The alley's gas lamp on its scrolled bracket (out = +1: it stands out along +x). Returns the glass centre."""
    i = 'iron'
    cbox(I4, i, min(x_wall, x_wall + 0.03 * out), max(x_wall, x_wall + 0.03 * out), y - 0.32, y + 0.2, z - 0.06, z + 0.06, b=0.008)
    lx = x_wall + out * 0.65
    rod(i, (x_wall, y + 0.1, z), (lx + out * 0.06, y + 0.1, z), 0.018, 6)
    tube(i, [(x_wall + out * (0.02 + 0.5 * t), y - 0.28 + 0.36 * (1 - (1 - t) ** 2), z) for t in np.linspace(0, 1, 7)], 0.013, 5)
    tube(i, [(x_wall + out * (0.3 + 0.09 * math.cos(a)), y - 0.02 + 0.09 * math.sin(a), z) for a in np.linspace(0, 5.2, 9)], 0.008, 4)
    rod(i, (lx, y + 0.1, z), (lx, y - 0.02, z), 0.012, 5)
    yt = y - 0.02
    r0, r1 = 0.07, 0.125
    y1, y0 = yt - 0.12, yt - 0.5
    cs = [(1, 1), (1, -1), (-1, -1), (-1, 1)]
    for (a1, a2), (b1, b2) in zip(cs, cs[1:] + cs[:1]):
        lquad(I4, 'lamp_glass', [(lx + a1 * r0, y0, z + a2 * r0), (lx + b1 * r0, y0, z + b2 * r0), (lx + b1 * r1, y1, z + b2 * r1), (lx + a1 * r1, y1, z + a2 * r1)],
              facing=((a1 + b1) / 2, 0.2, (a2 + b2) / 2))
        rod(i, (lx + a1 * r0, y0, z + a2 * r0), (lx + a1 * r1, y1, z + a2 * r1), 0.008, 4)
        rod(i, (lx + a1 * r1, y1, z + a2 * r1), (lx + b1 * r1, y1, z + b2 * r1), 0.009, 4)
        lquad(I4, i, [(lx + a1 * (r1 + 0.02), y1, z + a2 * (r1 + 0.02)), (lx + b1 * (r1 + 0.02), y1, z + b2 * (r1 + 0.02)),
                      (lx + b1 * 0.03, yt, z + b2 * 0.03), (lx + a1 * 0.03, yt, z + a2 * 0.03)], facing=((a1 + b1) / 2, 1, (a2 + b2) / 2))
    lquad(I4, i, [(lx + a * r0, y0, z + b * r0) for a, b in cs], facing=(0, -1, 0))
    sphere(i, (lx, y0 - 0.03, z), 0.025, 6)
    return Vector((lx, (y0 + y1) / 2, z))


def telegraph_pole(x, z, h=9.6, arms=3, y=0.15, along='x'):
    """A redwood pole with crossarms and glass insulators; iron steps for the lineman, a fire-alarm box.
    Returns the insulator tops (for stringing wires)."""
    cyl('wood_fence', (x, y, z), h, 0.15, 0.1, seg=8)
    tops = []
    ax = Vector((0, 0, 1)) if along == 'x' else Vector((1, 0, 0))    # arms lie across the line of the wires
    for k in range(arms):
        ya = y + h - 0.45 - k * 0.62
        L = 0.85 - k * 0.1
        c = Vector((x, ya, z))
        F = frame(c, ax, (-1, 0, 0) if along == 'x' else (0, 0, 1))
        cbox(F, 'wood_fence', -L, L, -0.05, 0.05, 0.1, 0.19, b=0.01)
        rod('iron', F @ Vector((-0.5, -0.02, 0.15)), F @ Vector((0, -0.45, 0.13)), 0.01, 4)
        rod('iron', F @ Vector((0.5, -0.02, 0.15)), F @ Vector((0, -0.45, 0.13)), 0.01, 4)
        row = []
        for t in (-0.92, -0.55, 0.55, 0.92):
            p = F @ Vector((t * L, 0.05, 0.145))
            cyl('door_wood', p, 0.07, 0.012, seg=4)
            cyl('porcelain', p + Vector((0, 0.06, 0)), 0.075, 0.032, 0.02, seg=6)
            row.append(p + Vector((0, 0.11, 0)))
        tops.append(row)
    for k in range(9):       # steps
        s = 1 if k % 2 else -1
        ys = y + 2.6 + k * 0.5
        d = ax * (s * 0.24)
        rod('iron', (x, ys, z), (x + d.x, ys, z + d.z), 0.012, 4)
    return tops


def hitching_post(x, z, y=0.15):
    cyl('iron', (x, y, z), 0.06, 0.07, 0.065, seg=8)
    cyl('iron', (x, y + 0.06, z), 0.85, 0.042, 0.034, seg=8, cap=False)
    sphere('iron', (x, y + 0.97, z), 0.065, 8)
    cyl('iron', (x, y + 0.9, z), 0.03, 0.05, 0.05, seg=8)
    tube('iron', [(x + 0.05 + 0.05 * math.cos(a), y + 0.78 + 0.05 * math.sin(a), z) for a in np.linspace(0, math.tau, 9)], 0.008, 4)


def hydrant(x, z, y=0.15):
    m = 'hydrant_red'
    cyl(m, (x, y, z), 0.06, 0.16, 0.15, seg=10)
    cyl(m, (x, y + 0.06, z), 0.5, 0.11, 0.1, seg=10, cap=False)
    cyl(m, (x, y + 0.56, z), 0.05, 0.135, 0.135, seg=10)
    cyl(m, (x, y + 0.61, z), 0.12, 0.12, 0.05, seg=10)
    cyl('iron', (x, y + 0.73, z), 0.05, 0.03, 0.03, seg=5)
    for d in ((1, 0, 0), (0, 0, 1), (-1, 0, 0)):
        cyl(m, (x + d[0] * 0.09, y + 0.4, z + d[2] * 0.09), 0.09, 0.055, seg=8, axis=d)
        cyl('iron', (x + d[0] * 0.18, y + 0.4, z + d[2] * 0.18), 0.03, 0.065, seg=6, axis=d)


def trough(x0, x1, z0, z1, y=0.0):
    """A horse trough: redwood planks bound with iron straps on two skids, black water standing in it."""
    for z in (z0, z1 - 0.06):
        cbox(I4, 'wood_fence', x0, x1, y + 0.1, y + 0.62, z, z + 0.06, b=0.008)
    for x in (x0, x1 - 0.06):
        cbox(I4, 'wood_fence', x, x + 0.06, y + 0.1, y + 0.62, z0 + 0.05, z1 - 0.05, b=0.008)
    lquad(I4, 'glass_dark', [(x0 + 0.05, y + 0.55, z0 + 0.05), (x1 - 0.05, y + 0.55, z0 + 0.05), (x1 - 0.05, y + 0.55, z1 - 0.05), (x0 + 0.05, y + 0.55, z1 - 0.05)], facing=(0, 1, 0))
    for x in (x0 + 0.25, (x0 + x1) / 2, x1 - 0.25):
        for z, n in ((z0 - 0.006, -1), (z1 + 0.006, 1)):
            lbox(I4, 'iron_rust', x - 0.025, x + 0.025, y + 0.1, y + 0.62, min(z, z + 0.006 * n), max(z, z + 0.006 * n))
    for x in (x0 + 0.2, x1 - 0.2):
        cbox(I4, 'wood_fence', x - 0.06, x + 0.06, y, y + 0.1, z0 - 0.05, z1 + 0.05, b=0.01)
    # the pump at one end
    cyl('iron', (x1 + 0.14, y, (z0 + z1) / 2), 1.05, 0.05, 0.045, seg=8)
    cyl('iron', (x1 + 0.14, y + 1.05, (z0 + z1) / 2), 0.2, 0.07, 0.07, seg=8)
    tube('iron', [(x1 + 0.14, y + 0.95, (z0 + z1) / 2), (x1 - 0.02, y + 0.95, (z0 + z1) / 2), (x1 - 0.06, y + 0.86, (z0 + z1) / 2)], 0.025, 6)
    tube('iron', [(x1 + 0.14, y + 1.2, (z0 + z1) / 2), (x1 + 0.3, y + 1.3, (z0 + z1) / 2), (x1 + 0.5, y + 0.85, (z0 + z1) / 2)], 0.014, 5)


def bollard(x, z, y=0.0, h=0.8):
    """A cast-iron guard post at the alley's corner, to keep cart wheels off the brickwork."""
    cyl('iron', (x, y, z), 0.12, 0.14, 0.12, seg=8)
    cyl('iron', (x, y + 0.12, z), h - 0.3, 0.1, 0.075, seg=8, cap=False)
    cyl('iron', (x, y + h - 0.18, z), 0.05, 0.095, 0.095, seg=8)
    sphere('iron', (x, y + h - 0.06, z), 0.085, 8)


def kerb(x0, x1, z, face, y=0.15, wd=0.2, joint=1.8, seed=0):
    """Granite kerbstones from x0 to x1, their street face at z (face = +1 if the street is toward +z)."""
    g = random.Random(seed)
    x = x0
    z0, z1 = (z - wd, z) if face > 0 else (z, z + wd)
    while x < x1 - 0.01:
        L = min(x1 - x, joint * (0.8 + 0.4 * g.random()))
        if x1 - (x + L) < 0.5: L = x1 - x
        dy = (g.random() - 0.5) * 0.012
        cbox(I4, 'stone', x + 0.004, x + L - 0.004, -0.05, y + dy, z0, z1, b=0.018)
        x += L


def sidewalk(x0, x1, z0, z1, y=0.15):
    lquad(I4, 'wood_walk', [(x0, y - 0.004, z0), (x1, y - 0.004, z0), (x1, y - 0.004, z1), (x0, y - 0.004, z1)], facing=(0, 1, 0))


def cellar_flap(x0, x1, z0, z1, y=0.15):
    """Iron cellar doors let into the sidewalk before a shop."""
    cbox(I4, 'iron_rust', x0, x1, y - 0.02, y + 0.012, z0, z1, b=0.006)
    m = (x0 + x1) / 2
    lbox(I4, 'iron', m - 0.012, m + 0.012, y + 0.012, y + 0.02, z0 + 0.02, z1 - 0.02)
    for x in (x0 + 0.08, x1 - 0.08):
        for z in (z0 + 0.15, z1 - 0.15):
            lbox(I4, 'iron', min(x, x + 0.0) - 0.04, x + 0.04, y + 0.012, y + 0.022, z - 0.02, z + 0.02)
    for x in (m - 0.12, m + 0.12):
        tube('iron', [(x, y + 0.012, (z0 + z1) / 2 - 0.06), (x, y + 0.035, (z0 + z1) / 2), (x, y + 0.012, (z0 + z1) / 2 + 0.06)], 0.007, 4)


def coal_hole(x, z, y=0.15, r=0.22):
    cyl('iron_rust', (x, y - 0.01, z), 0.016, r, r, seg=12)
    cyl('iron', (x, y + 0.006, z), 0.004, r * 0.55, r * 0.55, seg=10)


# --- alley clutter ---------------------------------------------------------------------------------------

def crate2(x, y, z, s, rot=0.0, h=None, label=None, open_top=False, tilt=0.0):
    """A slatted packing case centred at (x, y, z), s across and h high."""
    h = h or s
    F = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Y') @ Matrix.Rotation(tilt, 4, 'Z')
    a, b = s / 2, h / 2
    m = 'crate_wood'
    lbox(F, m, -a + 0.015, a - 0.015, -b + 0.015, b - (0.1 if open_top else 0.015), -a + 0.015, a - 0.015)
    for sz in (-1, 1):       # battens on the long faces: top, bottom, uprights
        w0, w1 = (a, a + 0.016) if sz > 0 else (-a - 0.016, -a)
        cbox(F, m, -a, a, b - 0.09, b, w0, w1, b=0.004)
        cbox(F, m, -a, a, -b, -b + 0.09, w0, w1, b=0.004)
        for sx in (-1, 1):
            cbox(F, m, sx * a - (0.08 if sx > 0 else 0), sx * a + (0.08 if sx < 0 else 0), -b + 0.09, b - 0.09, w0, w1, b=0.004)
    for sx in (-1, 1):
        u0_, u1_ = (a, a + 0.016) if sx > 0 else (-a - 0.016, -a)
        cbox(F, m, u0_, u1_, b - 0.09, b, -a - 0.016, a + 0.016, b=0.004)
        cbox(F, m, u0_, u1_, -b, -b + 0.09, -a - 0.016, a + 0.016, b=0.004)
        cbox(F, m, u0_, u1_, -b + 0.09, b - 0.09, -0.04, 0.04, b=0.004)
    if label:
        Fl = F @ Matrix.Translation((0, 0, a))
        poster(Fl, label, 0, 0, w=0.018, scale=min(1.0, (s - 0.2) / PAPER[label][4]))


def barrel2(x, z, y=0.0, h=0.95, r=0.31, lid=True, tilt=0.0, rot=0.0, mat='barrel_wood'):
    """A coopered cask: bulged staves, six iron hoops, the head set down inside the chime."""
    F = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Y') @ Matrix.Rotation(tilt, 4, 'X')
    bm = bm_for(mat)
    seg, rings = 14, 6
    prof = []
    for k in range(rings + 1):
        t = k / rings
        prof.append((r * (0.82 + 0.18 * math.sin(t * math.pi) ** 0.8), t * h))
    for (r0, y0), (r1, y1) in zip(prof, prof[1:]):
        for s in range(seg):
            a0, a1 = s / seg * math.tau, (s + 1) / seg * math.tau
            f = lquad(F, mat, [(r0 * math.cos(a0), y0, r0 * math.sin(a0)), (r0 * math.cos(a1), y0, r0 * math.sin(a1)),
                               (r1 * math.cos(a1), y1, r1 * math.sin(a1)), (r1 * math.cos(a0), y1, r1 * math.sin(a0))],
                      facing=(math.cos((a0 + a1) / 2), 0, math.sin((a0 + a1) / 2)))
            f.smooth = True
    rt = prof[-1][0]
    lquad(F, mat, [(rt * 0.94 * math.cos(s / seg * math.tau), h - 0.035 if lid else 0.05, rt * 0.94 * math.sin(s / seg * math.tau)) for s in range(seg)], facing=(0, 1, 0))
    lquad(F, mat, [(rt * math.cos(s / seg * math.tau), 0.0, rt * math.sin(s / seg * math.tau)) for s in range(seg)], facing=(0, -1, 0))
    for t in (0.04, 0.2, 0.36, 0.64, 0.8, 0.96):
        rr = r * (0.82 + 0.18 * math.sin(t * math.pi) ** 0.8) + 0.006
        cyl('iron_rust', F @ Vector((0, t * h - 0.02, 0)), 0.04, rr, rr, seg=seg, cap=False, axis=F.to_3x3() @ Vector((0, 1, 0)))


def ash_can2(x, z, lid='on', tilt=0.0, rot=0.0, dent=0.0):
    """A galvanised ash can with ribbed sides and side handles; the lid on, askew, or off."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y') @ Matrix.Rotation(tilt, 4, 'Z')
    up = F.to_3x3() @ Vector((0, 1, 0))
    cyl('tin', F @ Vector((0, 0, 0)), 0.76, 0.25, 0.29, seg=14)
    for yy in (0.05, 0.3, 0.55, 0.74):
        rr = 0.25 + 0.04 * yy / 0.76 + 0.008
        cyl('tin', F @ Vector((0, yy - 0.012, 0)), 0.024, rr, rr, seg=14, cap=False, axis=up)
    for s in (-1, 1):
        tube('iron', [F @ Vector((s * 0.285, 0.6, -0.06)), F @ Vector((s * 0.33, 0.58, -0.06)), F @ Vector((s * 0.33, 0.58, 0.06)), F @ Vector((s * 0.285, 0.6, 0.06))], 0.008, 4)
    if lid == 'on':
        cyl('tin', F @ Vector((0, 0.76, 0)), 0.03, 0.305, 0.305, seg=14, axis=up)
        cyl('tin', F @ Vector((0, 0.79, 0)), 0.05, 0.3, 0.1, seg=14, axis=up)
        tube('iron', [F @ Vector((-0.06, 0.83, 0)), F @ Vector((-0.04, 0.88, 0)), F @ Vector((0.04, 0.88, 0)), F @ Vector((0.06, 0.83, 0))], 0.008, 4)
    else:
        lquad(F, 'earth', [(0.27 * math.cos(a), 0.7, 0.27 * math.sin(a)) for a in np.linspace(0, math.tau, 13)[:-1]], facing=(0, 1, 0))
    if lid == 'off':     # the lid leaning against it
        Fl = F @ Matrix.Translation((0.36, 0.3, 0.12)) @ Matrix.Rotation(1.2, 4, 'Z')
        ax = Fl.to_3x3() @ Vector((0, 1, 0))
        cyl('tin', Fl @ Vector((0, 0, 0)), 0.03, 0.305, 0.305, seg=14, axis=ax)
        cyl('tin', Fl @ Vector((0, 0.03, 0)), 0.05, 0.3, 0.1, seg=14, axis=ax)


def sack(x, z, y=0.0, s=1.0, rot=0.0, lying=False, mat='sack'):
    """A filled jute sack, standing with its neck tied or lying flat."""
    bm = bm_for(mat)
    if lying:
        M = Matrix.Translation((x, y + 0.14 * s, z)) @ Matrix.Rotation(rot, 4, 'Y') @ Matrix.Diagonal((0.42 * s, 0.15 * s, 0.26 * s, 1))
    else:
        M = Matrix.Translation((x, y + 0.33 * s, z)) @ Matrix.Rotation(rot, 4, 'Y') @ Matrix.Diagonal((0.24 * s, 0.36 * s, 0.2 * s, 1))
    r = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0, matrix=M @ Matrix.Rotation(math.pi / 2, 4, 'X'))
    g = random.Random(int(x * 100 + z * 10))
    for v in r['verts']:
        v.co += Vector((g.random() - 0.5, (g.random() - 0.5) * 0.5, g.random() - 0.5)) * 0.035 * s
        for f in v.link_faces: f.smooth = True
    if not lying:
        cyl(mat, (x, y + 0.66 * s, z), 0.1 * s, 0.05 * s, 0.09 * s, seg=6)
        cyl('rope', (x, y + 0.665 * s, z), 0.025 * s, 0.058 * s, 0.058 * s, seg=6, cap=False)


def bottle(x, z, y=0.0, lying=False, rot=0.0, mat='glass_dark', s=1.0):
    F = Matrix.Translation((x, y + (0.04 * s if lying else 0), z)) @ Matrix.Rotation(rot, 4, 'Y') @ (Matrix.Rotation(math.pi / 2, 4, 'X') if lying else I4)
    ax = F.to_3x3() @ Vector((0, 1, 0))
    cyl(mat, F @ Vector((0, 0, 0)), 0.17 * s, 0.038 * s, 0.038 * s, seg=7, axis=ax)
    cyl(mat, F @ Vector((0, 0.17 * s, 0)), 0.06 * s, 0.038 * s, 0.014 * s, seg=7, cap=False, axis=ax)
    cyl(mat, F @ Vector((0, 0.23 * s, 0)), 0.06 * s, 0.014 * s, 0.013 * s, seg=7, axis=ax)


def drainpipe2(x_wall, z, top, out, bottom=0.3, r=0.055, shoe=True, mat='tin'):
    """A rain leader standing just off the wall: hopper head, joints and holdfasts, a shoe turned out at the foot."""
    x = x_wall + out * (r + 0.035)
    cyl(mat, (x, bottom, z), top - bottom, r, seg=8, cap=False)
    cbox(I4, mat, x - 0.13, x + 0.13, top, top + 0.22, z - 0.14, z + 0.14, b=0.03)          # hopper
    cyl(mat, (x, top - 0.12, z), 0.12, r, 0.1, seg=8, cap=False)
    yy = bottom + 0.9
    while yy < top - 0.3:
        cyl(mat, (x, yy, z), 0.07, r + 0.012, r + 0.012, seg=8, cap=False)
        lbox(I4, 'iron', min(x_wall, x_wall + out * 0.05), max(x_wall, x_wall + out * 0.05), yy + 0.02, yy + 0.05, z - 0.09, z + 0.09)
        yy += 1.7
    if shoe:
        tube(mat, [(x, bottom + 0.02, z), (x + out * 0.06, bottom - 0.12, z), (x + out * 0.24, bottom - 0.22, z)], r, 8)


def fire_escape2(F, u0, u1, levels, ladder_u, depth=1.0, drop=True):
    """An iron fire escape: slatted balconies on brackets with bar railings, raking ladders between, and the
    counterbalanced drop ladder held up out of reach."""
    i, ir = 'iron', 'iron_rust'
    for li, v in enumerate(levels):
        # the deck: an angle-iron frame with flat slats, left open where the ladder comes up
        lbox(F, i, u0, u1, v - 0.05, v, depth - 0.04, depth)
        lbox(F, i, u0, u1, v - 0.05, v, 0.02, 0.06)
        for u in (u0, u1 - 0.04):
            lbox(F, i, u, u + 0.04, v - 0.05, v, 0.02, depth)
        n = int((u1 - u0) / 0.09)
        for k in range(1, n):
            u = u0 + k * (u1 - u0) / n
            if li > 0 and abs(u - (ladder_u + 0.1)) < 0.4: continue
            lbox(F, ir, u - 0.02, u + 0.02, v - 0.03, v - 0.018, 0.06, depth - 0.04)
        # railing: top and mid rails, close-set bars, corner posts
        for vv in (v + 0.98, v + 0.5):
            lbox(F, i, u0, u1, vv, vv + 0.03, depth - 0.035, depth - 0.005)
            for u in (u0, u1 - 0.03):
                lbox(F, i, u, u + 0.03, vv, vv + 0.03, 0.02, depth)
        for k in np.arange(u0, u1 + 0.01, 0.15):
            lbox(F, i, k - 0.007, k + 0.007, v, v + 0.98, depth - 0.027, depth - 0.013)
        for u in (u0 + 0.015, u1 - 0.015):
            for w in np.arange(0.17, depth - 0.05, 0.15):
                lbox(F, i, u - 0.007, u + 0.007, v, v + 0.98, w - 0.007, w + 0.007)
        # brackets down to the wall
        for u in np.linspace(u0 + 0.05, u1 - 0.05, 3):
            rod(i, F @ Vector((u, v - 0.05, depth - 0.03)), F @ Vector((u, v - 0.95, 0.03)), 0.016, 4)
            lbox(F, i, u - 0.04, u + 0.04, v - 1.0, v - 0.86, 0.0, 0.02)
    for a, b in zip(levels, levels[1:]):    # raking ladders
        p0, p1 = Vector((ladder_u - 1.3, a, 0)), Vector((ladder_u + 0.1, b, 0))
        for w in (0.2, 0.72):
            rod(i, F @ Vector((p0.x, p0.y, w)), F @ Vector((p1.x, p1.y, w)), 0.018, 4)
            rod(i, F @ Vector((p0.x, p0.y + 0.9, w)), F @ Vector((p1.x, p1.y + 0.9, w)), 0.012, 4)   # hand rail
            rod(i, F @ Vector((p1.x, p1.y, w)), F @ Vector((p1.x, p1.y + 0.9, w)), 0.012, 4)
        steps = int((b - a) / 0.24)
        for k in range(1, steps):
            t = k / steps
            p = p0.lerp(p1, t)
            lbox(F, ir, p.x - 0.07, p.x + 0.07, p.y - 0.012, p.y, 0.2, 0.72)
    if drop:
        v = levels[0]
        for w in (depth + 0.03, depth + 0.45):
            rod(i, F @ Vector((ladder_u + 0.6, v - 0.6, w)), F @ Vector((ladder_u + 0.6, v + 2.2, w)), 0.016, 4)
        for k in range(10):
            rod(ir, F @ Vector((ladder_u + 0.6, v - 0.5 + k * 0.29, depth + 0.03)), F @ Vector((ladder_u + 0.6, v - 0.5 + k * 0.29, depth + 0.45)), 0.011, 4)
        lbox(F, i, ladder_u + 0.56, ladder_u + 0.64, v + 0.3, v + 0.36, depth - 0.02, depth + 0.5)
        lbox(F, i, ladder_u + 0.56, ladder_u + 0.64, v + 1.0, v + 1.06, depth - 0.02, depth + 0.5)


def cellar_bulkhead(F, u0, u1, out=0.85, h=0.62, leaf='wood_green'):
    """Sloping cellar doors against the foot of a wall, on a brick kerb."""
    for u in (u0 - 0.1, u1):
        extrude(F, 'stone', [(0, 0), (out + 0.06, 0), (out + 0.06, 0.14), (0.0, h + 0.05)], u, u + 0.1)
    extrude(F, 'stone', [(out, 0), (out + 0.06, 0), (out + 0.06, 0.14), (out, 0.14)], u0, u1)
    sl = math.atan2(h - 0.12, out)
    L = math.hypot(out, h - 0.12)
    m = (u0 + u1) / 2
    Fs = F @ Matrix.Translation((0, h, 0)) @ Matrix.Rotation(sl, 4, 'X')      # a frame lying on the slope, w running down it
    for a, b in ((u0, m - 0.008), (m + 0.008, u1)):
        lbox(Fs, leaf, a, b, -0.02, 0.025, 0.0, L)
        for w in (0.15, L - 0.15):
            lbox(Fs, 'iron', a + 0.02, b - 0.02, 0.025, 0.033, w - 0.022, w + 0.022)
    tube('iron', [Fs @ Vector((m - 0.1, 0.03, L * 0.55)), Fs @ Vector((m - 0.1, 0.07, L * 0.6)), Fs @ Vector((m - 0.1, 0.03, L * 0.65))], 0.008, 4)
    tube('iron', [Fs @ Vector((m + 0.1, 0.03, L * 0.55)), Fs @ Vector((m + 0.1, 0.07, L * 0.6)), Fs @ Vector((m + 0.1, 0.03, L * 0.65))], 0.008, 4)


def back_stair(F, u0, u1, rise, width=0.9, landing=1.3, post='wood_fence', tread='wood_fence'):
    """An outside service stair running up along the wall from u0 to a landing ending at u1: stringers, open
    treads, posts and a handrail on the open side, cross-braced underneath."""
    run = (u1 - landing) - u0
    n = max(3, int(round(rise / 0.2)))
    going = run / n
    step = rise / (n + 1)
    for k in range(n):
        u = u0 + k * going
        v = (k + 1) * step
        cbox(F, tread, u - 0.02, u + going + 0.03, v - 0.04, v, 0.04, width, b=0.006)
    for w in (0.02, width - 0.04):          # stringers
        extrude(F, post, [(u0 - 0.05, 0.0), (u0 + 0.2, 0.0), (u1 - landing + 0.1, rise - 0.26), (u1 - landing + 0.1, rise - 0.04), (u1 - landing - 0.12, rise - 0.04)], w, w + 0.05, axis='w')
    ul = u1 - landing
    cbox(F, tread, ul, u1, rise - 0.05, rise, 0.0, width + 0.04, b=0.006)       # the landing
    for u in (ul + 0.05, u1 - 0.07):
        for w in (0.05, width - 0.07):
            cbox(F, post, u - 0.045, u + 0.045, 0, rise - 0.05, w - 0.045 + 0.045, w + 0.045 + 0.045, b=0.006)
    lbox(F, post, ul, u1, rise - 0.2, rise - 0.05, width - 0.03, width + 0.02)
    lbox(F, post, u1 - 0.05, u1, rise - 0.2, rise - 0.05, 0.02, width)
    rod(post, F @ Vector((ul + 0.05, 0.1, width - 0.0)), F @ Vector((u1 - 0.07, rise - 0.25, width - 0.0)), 0.03, 4)   # brace
    # balustrade on the open side and across the end of the landing
    posts = [(u0 + 0.1, step)] + [(u0 + k * going + going / 2, (k + 1) * step) for k in range(3, n, 4)] + [(ul + 0.05, rise), (u1 - 0.05, rise)]
    for u, v in posts:
        cbox(F, post, u - 0.035, u + 0.035, v - 0.05, v + 0.95, width - 0.04, width + 0.03, b=0.006)
    for (ua, va), (ub, vb) in zip(posts, posts[1:]):
        for dv in (0.92, 0.5):
            extrude(F, post, [(ua, va + dv - 0.035), (ub, vb + dv - 0.035), (ub, vb + dv + 0.035), (ua, va + dv + 0.035)], width - 0.03, width + 0.02, axis='w')
    cbox(F, post, u1 - 0.05, u1 + 0.02, rise - 0.05, rise + 0.95, 0.02, 0.09, b=0.006)
    for dv in (0.92, 0.5):
        lbox(F, post, u1 - 0.04, u1 + 0.01, rise + dv - 0.035, rise + dv + 0.035, 0.05, width)
    return ul, u1


def handcart(x, z, rot=0.0, tipped=True):
    """A costermonger's two-wheeled handcart, resting on its shafts."""
    tilt = -0.2 if tipped else 0.0
    F = Matrix.Translation((x, 0.52, z)) @ Matrix.Rotation(rot, 4, 'Y') @ Matrix.Rotation(tilt, 4, 'Z')
    m = 'wood_green'
    cbox(F, m, -0.75, 0.75, 0.0, 0.035, -0.42, 0.42, b=0.006)                      # bed
    for s in (-1, 1):
        cbox(F, m, -0.75, 0.75, 0.035, 0.26, s * 0.42 - 0.012, s * 0.42 + 0.012, b=0.005)
        for u in (-0.7, -0.25, 0.25, 0.7):
            cbox(F, 'crate_wood', u - 0.025, u + 0.025, 0.0, 0.3, s * 0.435 - 0.012 + 0.012 * s, s * 0.435 + 0.012 + 0.012 * s, b=0.004)
        rod('crate_wood', F @ Vector((0.6, -0.03, s * 0.36)), F @ Vector((1.85, -0.03, s * 0.3)), 0.025, 6)   # shafts
    cbox(F, m, -0.762, -0.738, 0.035, 0.26, -0.42, 0.42, b=0.005)
    rod('crate_wood', F @ Vector((1.8, -0.03, -0.32)), F @ Vector((1.8, -0.03, 0.32)), 0.02, 6)
    rod('iron', F @ Vector((-0.1, -0.06, -0.56)), F @ Vector((-0.1, -0.06, 0.56)), 0.025, 6)        # axle
    for s in (-1, 1):
        for u in (-0.3, 0.1):
            rod('iron', F @ Vector((u, 0.0, s * 0.3)), F @ Vector((-0.1, -0.06, s * 0.3)), 0.012, 4)
        wheel(F @ Matrix.Translation((-0.1, -0.06, s * 0.52)), 0.46, spokes=10)
    for u in (0.7,):   # the prop leg under the shafts end of the bed
        rod('crate_wood', F @ Vector((u, 0.0, 0.0)), F @ Vector((u + 0.05, -0.32, 0.0)), 0.02, 5)
    return F


def wheel(F, r, spokes=12, wd=0.05, mat='wood_red'):
    """A spoked cart wheel in the frame's u-v plane, its axle along w."""
    n = 16
    for k in range(n):
        a0, a1 = k / n * math.tau, (k + 1) / n * math.tau
        for (ri, ro, ma, w) in ((r - 0.055, r - 0.008, mat, wd / 2), (r - 0.008, r, 'iron', wd / 2 + 0.004)):
            p = [(ri * math.cos(a0), ri * math.sin(a0)), (ri * math.cos(a1), ri * math.sin(a1)), (ro * math.cos(a1), ro * math.sin(a1)), (ro * math.cos(a0), ro * math.sin(a0))]
            extrude(F, ma, p, -w, w, axis='w', caps=True)
    for k in range(spokes):
        a = k / spokes * math.tau
        rod(mat, F @ Vector((0.05 * math.cos(a), 0.05 * math.sin(a), 0)), F @ Vector(((r - 0.05) * math.cos(a), (r - 0.05) * math.sin(a), 0)), 0.014, 4)
    cyl(mat, F @ Vector((0, 0, -0.07)), 0.14, 0.065, 0.065, seg=8, axis=F.to_3x3() @ Vector((0, 0, 1)))
    cyl('iron', F @ Vector((0, 0, 0.07)), 0.03, 0.03, 0.03, seg=6, axis=F.to_3x3() @ Vector((0, 0, 1)))


def wagon(x, z, rot=0.0, load=True):
    """A four-wheeled delivery dray, unhitched, its pole resting on the paving: plank bed with low side
    boards on bolsters, a sprung seat, small front and large hind wheels with iron tyres."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    m, e = 'wood_green', 'crate_wood'
    bed = 1.02
    cbox(F, e, -1.65, 1.55, bed, bed + 0.05, -0.68, 0.68, b=0.008)
    for s in (-1, 1):
        cbox(F, m, -1.65, 1.55, bed + 0.05, bed + 0.42, s * 0.68 - 0.02, s * 0.68 + 0.02, b=0.006)
        for u in (-1.5, -0.75, 0.0, 0.75, 1.4):
            cbox(F, e, u - 0.03, u + 0.03, bed - 0.02, bed + 0.46, s * 0.715 - 0.015, s * 0.715 + 0.015, b=0.004)
        cbox(F, e, -1.6, 1.5, bed - 0.14, bed, s * 0.42 - 0.05, s * 0.42 + 0.05, b=0.008)       # the reach timbers under the bed
    cbox(F, m, -1.67, -1.63, bed + 0.05, bed + 0.42, -0.68, 0.68, b=0.006)                       # tailboard
    cbox(F, m, 1.53, 1.57, bed + 0.05, bed + 0.62, -0.68, 0.68, b=0.006)                         # headboard
    cbox(F, e, 1.15, 1.6, bed + 0.72, bed + 0.77, -0.6, 0.6, b=0.008)                            # seat
    cbox(F, e, 1.12, 1.16, bed + 0.77, bed + 1.05, -0.6, 0.6, b=0.006)
    for s in (-1, 1):
        rod('iron', F @ Vector((1.25, bed + 0.42, s * 0.5)), F @ Vector((1.25, bed + 0.72, s * 0.5)), 0.012, 4)
        rod('iron', F @ Vector((1.5, bed + 0.42, s * 0.5)), F @ Vector((1.5, bed + 0.72, s * 0.5)), 0.012, 4)
    cbox(F, e, 1.57, 1.95, bed + 0.12, bed + 0.16, -0.5, 0.5, b=0.006)                           # footboard
    for u, r in ((1.05, 0.46), (-1.0, 0.62)):
        rod('iron', F @ Vector((u, r, -0.86)), F @ Vector((u, r, 0.86)), 0.03, 6)                # axles
        cbox(F, e, u - 0.07, u + 0.07, r + 0.03, bed - 0.14, -0.6, 0.6, b=0.008)                 # bolsters
        for s in (-1, 1):
            wheel(F @ Matrix.Translation((u, r, s * 0.8)), r, spokes=12 if r < 0.5 else 14, wd=0.06)
    # the pole, dropped
    rod(e, F @ Vector((1.1, 0.5, 0)), F @ Vector((4.3, 0.06, 0.12)), 0.04, 6)
    cbox(F @ Matrix.Translation((2.0, 0.42, 0.03)), e, -0.04, 0.04, -0.03, 0.03, -0.55, 0.55, b=0.006)
    if load:
        for u, w in ((-1.25, -0.3), (-1.25, 0.32), (-0.6, 0.0)):
            P = F @ Vector((u, 0, w)); barrel2(P.x, P.z, y=bed + 0.05, h=0.8, r=0.27)
        P = F @ Vector((0.35, 0, -0.2)); sack(P.x, P.z, y=bed + 0.05, s=0.95, rot=rot + 0.3, lying=True)
        P = F @ Vector((0.4, 0, 0.3)); sack(P.x, P.z, y=bed + 0.05, s=0.9, rot=rot - 0.4, lying=True)
        P = F @ Vector((0.45, 0, 0.05)); sack(P.x, P.z, y=bed + 0.3, s=0.9, rot=rot + 1.4, lying=True)
    return F


def a_board(x, z, name, y=0.15, rot=0.0, scale=1.0):
    """A hinged sandwich board stood on the sidewalk, a painted notice on each face."""
    u0, v0, u1, v1, wm, hm = PAPER[name]
    wm, hm = wm * scale, hm * scale
    F = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Y')
    for s in (-1, 1):
        Fs = F @ (I4 if s > 0 else Matrix.Rotation(math.pi, 4, 'Y')) @ Matrix.Translation((0, 0, 0.24)) @ Matrix.Rotation(-0.22, 4, 'X')
        cbox(Fs, 'door_wood', -wm / 2 - 0.04, wm / 2 + 0.04, 0.0, hm + 0.42, -0.012, 0.012, b=0.004)
        lquad(Fs, 'paper_atlas', [(-wm / 2, 0.36, 0.014), (wm / 2, 0.36, 0.014), (wm / 2, 0.36 + hm, 0.014), (-wm / 2, 0.36 + hm, 0.014)], facing=(0, 0, 1),
              uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def timber_stack(F, u0, n=7, length=3.2, lean=0.24, seed=3, mat='wood_fence'):
    """Scaffold planks and scantlings stood on end against the wall."""
    g = random.Random(seed)
    u = u0
    for k in range(n):
        wd = 0.14 + 0.1 * g.random()
        th = 0.035 + 0.02 * g.random()
        L = length * (0.75 + 0.3 * g.random())
        ln = lean * (0.8 + 0.4 * g.random())
        base = 0.1 + L * math.sin(ln) + (k % 2) * 0.05
        Fp = F @ Matrix.Translation((u + wd / 2, 0, base)) @ Matrix.Rotation(-ln, 4, 'X') @ Matrix.Rotation((g.random() - 0.5) * 0.08, 4, 'Z')
        cbox(Fp, mat if k % 3 else 'crate_wood', -wd / 2, wd / 2, 0, L, -th, 0, b=0.004)
        u += wd * (0.65 + 0.35 * g.random())
    return u


def ladder(F, u, length=3.4, lean=0.22, wd=0.42, mat='crate_wood'):
    Fp = F @ Matrix.Translation((u, 0, 0.08 + length * math.sin(lean))) @ Matrix.Rotation(-lean, 4, 'X')
    for s in (-1, 1):
        cbox(Fp, mat, s * wd / 2 - 0.02, s * wd / 2 + 0.02, 0, length, -0.06, -0.01, b=0.004)
    for k in range(1, int(length / 0.3)):
        rod(mat, Fp @ Vector((-wd / 2, k * 0.3, -0.035)), Fp @ Vector((wd / 2, k * 0.3, -0.035)), 0.014, 5)


def laundry_line(a, b, items, sag=0.5, seed=5):
    """A clothes line across the alley from a to b with the week's wash left out in the fog."""
    pts = wire3(a, b, sag=sag, seg=12, r=0.006, mat='rope')
    g = random.Random(seed)
    a, b = Vector(a), Vector(b)
    d = (b - a); d.y = 0; d.normalize()
    side = Vector((-d.z, 0, d.x))
    for t, kind in items:
        p = a.lerp(b, t); p.y -= sag * 4 * t * (1 - t)
        sway = (g.random() - 0.5) * 0.12
        mat = {'sheet': 'cloth_white', 'shirt': 'cloth_white', 'drawers': 'cloth_white', 'blue': 'cloth_blue', 'red': 'cloth_red', 'towel': 'cloth_white'}[kind]
        w, h = {'sheet': (1.3, 1.25), 'shirt': (0.55, 0.75), 'drawers': (0.5, 0.85), 'blue': (0.6, 0.9), 'red': (0.45, 0.55), 'towel': (0.45, 0.8)}[kind]
        F = Matrix.Translation(p) @ Matrix((d, Vector((0, 1, 0)), side)).transposed().to_4x4()
        cols = 4
        rows = [0, -h * 0.5, -h]
        grid = [[(-w / 2 + c * w / cols, y, sway * (y / -h) + 0.03 * math.sin(c * 2.1 + (y * 3)) * (y / -h + 0.3)) for c in range(cols + 1)] for y in rows]
        if kind in ('shirt', 'blue'):     # arms hanging at the sides
            for s in (-1, 1):
                cloth(F, mat, [(s * w / 2, -0.02, 0.0), (s * (w / 2 + 0.16), -0.05, 0.01), (s * (w / 2 + 0.2), -h * 0.75, sway), (s * (w / 2 + 0.03), -h * 0.7, sway)])
        if kind == 'drawers':             # two legs
            cloth(F, mat, [(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, -h * 0.4, sway * 0.4), (-w / 2, -h * 0.4, sway * 0.4)])
            for s in (-1, 1):
                x0, x1 = (s * w / 2, s * 0.04)
                cloth(F, mat, [(x0, -h * 0.4, sway * 0.4), (x1, -h * 0.4, sway * 0.4), (x1 + s * 0.02, -h, sway + 0.03 * s), (x0, -h, sway)])
        else:
            for r0, r1 in zip(grid, grid[1:]):
                for c in range(cols):
                    cloth(F, mat, [r0[c], r0[c + 1], r1[c + 1], r1[c]])
        for x in (-w / 2 + 0.05, w / 2 - 0.05):
            lbox(F, 'crate_wood', x - 0.008, x + 0.008, -0.05, 0.03, -0.012, 0.012)


def rubbish(x, z, r=0.5, seed=0, n=10, papers=True):
    """Trodden litter: scraps of paper and sacking, a broken slat or two, a bottle."""
    g = random.Random(seed)
    for k in range(n):
        a, d = g.random() * math.tau, r * g.random() ** 0.7
        px, pz = x + math.cos(a) * d, z + math.sin(a) * d
        kind = g.random()
        ro = g.random() * math.pi
        if kind < 0.45 and papers:
            s = 0.1 + 0.14 * g.random()
            F = Matrix.Translation((px, 0.012 + 0.004 * k, pz)) @ Matrix.Rotation(ro, 4, 'Y')
            pts = [(-s, 0, -s * 0.7), (s, 0.01 + 0.03 * g.random(), -s * 0.7), (s, 0.0, s * 0.7), (-s, 0.02 * g.random(), s * 0.7)]
            if g.random() < 0.3:
                sheet(F, g.choice(['newspaper', 'bill_beer', 'bill_seamen', 'bill_rooms']), pts)
            else:
                cloth(F, 'cloth_white' if g.random() < 0.6 else 'sack', pts)
        elif kind < 0.7:
            F = Matrix.Translation((px, 0.012, pz)) @ Matrix.Rotation(ro, 4, 'Y')
            cbox(F, 'crate_wood', -0.2 - 0.2 * g.random(), 0.2, 0, 0.012, -0.03, 0.03, b=0.003)
        elif kind < 0.85:
            bottle(px, pz, lying=True, rot=ro)
        else:
            F = Matrix.Translation((px, 0.0, pz)) @ Matrix.Rotation(ro, 4, 'Y')
            cbox(F, 'brick_red', -0.1, 0.1, 0, 0.06, -0.05, 0.05, b=0.006)


def weeds(x, z, y=0.0, n=7, h=0.35, r=0.2, seed=0, mat='weeds'):
    """A tuft of rank grass: a few bent blades, each two triangles seen from both sides."""
    g = random.Random(seed)
    for k in range(n):
        a = g.random() * math.tau
        d = r * g.random()
        bx, bz = x + math.cos(a) * d, z + math.sin(a) * d
        hh = h * (0.5 + 0.7 * g.random())
        lean = 0.25 * hh * (0.3 + g.random())
        wd = 0.02 + 0.02 * g.random()
        ox, oz = math.cos(a + 1.57) * wd, math.sin(a + 1.57) * wd
        tip = (bx + math.cos(a) * lean * 2.0, y + hh, bz + math.sin(a) * lean * 2.0)
        mid0 = (bx + math.cos(a) * lean * 0.6 - ox * 0.7, y + hh * 0.6, bz + math.sin(a) * lean * 0.6 - oz * 0.7)
        mid1 = (bx + math.cos(a) * lean * 0.6 + ox * 0.7, y + hh * 0.6, bz + math.sin(a) * lean * 0.6 + oz * 0.7)
        cloth(I4, mat, [(bx - ox, y, bz - oz), (bx + ox, y, bz + oz), mid1, mid0])
        cloth(I4, mat, [mid0, mid1, tip])


def plank_fence(x0, x1, z, gap=None, h=1.9, seed=7, posts=True, behind=-1):
    """A tall board fence along x at z; gap = (xa, xb) left open. The rails are on the `behind` side (z sign)."""
    g = random.Random(seed)
    x = x0 + 0.01
    while x < x1 - 0.05:
        wd = 0.17 + 0.05 * g.random()
        if x + wd > x1: wd = x1 - x
        if not (gap and x + wd > gap[0] and x < gap[1]):
            hh = h + (g.random() - 0.5) * 0.12
            F = Matrix.Translation((x + wd / 2, 0, z)) @ Matrix.Rotation((g.random() - 0.5) * 0.035, 4, 'Z') @ Matrix.Rotation((g.random() - 0.5) * 0.03, 4, 'X')
            cbox(F, 'wood_fence', -wd / 2 + 0.004, wd / 2 - 0.004, 0.02 + 0.05 * g.random(), hh, -0.014, 0.014, b=0.004)
        x += wd + 0.004 + 0.01 * g.random()
    for y in (0.42, 1.55):
        if gap:
            cbox(I4, 'wood_fence', x0, gap[0] + 0.05, y - 0.05, y + 0.05, z + behind * 0.09, z + behind * 0.015, b=0.006) if behind > 0 else \
                cbox(I4, 'wood_fence', x0, gap[0] + 0.05, y - 0.05, y + 0.05, z - 0.09, z - 0.015, b=0.006)
            cbox(I4, 'wood_fence', gap[1] - 0.05, x1, y - 0.05, y + 0.05, min(z + behind * 0.09, z + behind * 0.015), max(z + behind * 0.09, z + behind * 0.015), b=0.006)
        else:
            cbox(I4, 'wood_fence', x0, x1, y - 0.05, y + 0.05, min(z + behind * 0.09, z + behind * 0.015), max(z + behind * 0.09, z + behind * 0.015), b=0.006)
    if posts:
        for x in (x0 + 0.08, (x0 + x1) / 2 - 0.9, x1 - 0.08):
            cbox(I4, 'wood_fence', x - 0.06, x + 0.06, 0, h - 0.1, min(z + behind * 0.2, z + behind * 0.09), max(z + behind * 0.2, z + behind * 0.09), b=0.008)


def star_anchor(F, u, v):
    """A cast-iron tie-rod plate on a brick wall."""
    for k in range(5):
        a = k / 5 * math.tau + math.pi / 2
        b1, b2 = a - 0.63, a + 0.63
        extrude(F, 'iron_rust', [(u + 0.17 * math.cos(a), v + 0.17 * math.sin(a)), (u + 0.065 * math.cos(b2), v + 0.065 * math.sin(b2)), (u, v),
                                 (u + 0.065 * math.cos(b1), v + 0.065 * math.sin(b1))], 0.0, 0.02, axis='w')
    sphere('iron', F @ Vector((u, v, 0.03)), 0.028, 6)


def wall_vent(F, u, v, w=0.3, h=0.22):
    lbox(F, 'iron_rust', u - w / 2, u + w / 2, v, v + h, 0, 0.02)
    for k in range(4):
        lbox(F, 'iron', u - w / 2 + 0.03, u + w / 2 - 0.03, v + 0.035 + k * (h - 0.05) / 4, v + 0.055 + k * (h - 0.05) / 4, 0.02, 0.03)


def stove_flue(F, u, v0, top, r=0.075):
    """A sheet-iron stovepipe out through the wall and up past the roof, with a rain cap."""
    tube('tin', [F @ Vector((u, v0, 0.0)), F @ Vector((u, v0, 0.26)), F @ Vector((u, v0 + 0.14, 0.3))], r, 8)
    cyl('tin', F @ Vector((u, v0 + 0.14, 0.3)), top - v0 - 0.14, r, seg=8, cap=False)
    for vv in np.arange(v0 + 1.2, top, 1.5):
        lbox(F, 'iron', u - 0.1, u + 0.1, vv, vv + 0.03, 0.0, 0.38)
    cyl('tin', F @ Vector((u, top + 0.08, 0.3)), 0.12, r * 2.1, 0.02, seg=8)
    for a in (0, 2.1, 4.2):
        rod('iron', F @ Vector((u + r * math.cos(a), top, 0.3 + r * math.sin(a))), F @ Vector((u + r * 1.6 * math.cos(a), top + 0.09, 0.3 + r * 1.6 * math.sin(a))), 0.006, 3)


def hoarding(F, u, v, name='billboard', frame_mat='wood_fence'):
    """A bill-poster's board on the wall: a boarded back in a timber frame, the sheet pasted over it."""
    u0, v0, u1, v1, wm, hm = PAPER[name]
    a, b, c, d = u - wm / 2, u + wm / 2, v - hm / 2, v + hm / 2
    lbox(F, frame_mat, a - 0.05, b + 0.05, c - 0.05, d + 0.05, 0.0, 0.026)
    lquad(F, 'paper_atlas', [(a, c, 0.04), (b, c, 0.04), (b, d, 0.04), (a, d, 0.04)], facing=(0, 0, 1), uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    cbox(F, frame_mat, a - 0.12, b + 0.12, d + 0.0, d + 0.1, 0.0, 0.1, b=0.008)
    cbox(F, frame_mat, a - 0.12, b + 0.12, c - 0.1, c, 0.0, 0.1, b=0.008)
    for x in (a - 0.12, b + 0.02):
        cbox(F, frame_mat, x, x + 0.1, c, d, 0.0, 0.1, b=0.008)
    extrude(F, frame_mat, [(0.0, d + 0.1), (0.2, d + 0.1), (0.2, d + 0.13), (0.0, d + 0.19)], a - 0.16, b + 0.16)   # a drip board


# --- finishing -----------------------------------------------------------------------------------------------

def finish2(name):
    """Like setkit.finish(), but one object per material *and region*, with coincident points welded."""
    region('__end__')
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    tris = 0
    for reg, bms in _REG.items():
        for mat, bm in bms.items():
            if not len(bm.faces): continue
            m, scale = MATS[mat]
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
            uv = bm.loops.layers.uv.verify()
            bm.normal_update()
            for f in (bm.faces if scale else []):
                n = f.normal
                ax = max(range(3), key=lambda i: abs(n[i]))
                for loop in f.loops:
                    co = loop.vert.co
                    if ax == 0: loop[uv].uv = (co.z * (-1 if n.x > 0 else 1) / scale, co.y / scale)
                    elif ax == 1: loop[uv].uv = (co.x / scale, co.z / scale)
                    else: loop[uv].uv = (co.x * (1 if n.z > 0 else -1) / scale, co.y / scale)
            me = bpy.data.meshes.new(f'{mat}.{reg}')
            bm.to_mesh(me); bm.free()
            me.materials.append(m)
            me.calc_loop_triangles(); tris += len(me.loop_triangles)
            ob = bpy.data.objects.new(f'{mat}.{reg}', me)
            bpy.context.scene.collection.objects.link(ob)
            ob.parent = root
    root.rotation_euler = (math.pi / 2, 0, 0)
    return root, tris
