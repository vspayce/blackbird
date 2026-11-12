# The look of the cast, as far as it can be improved on the saved blends without MPFB: generated normal maps for
# the cloth (wool twill, tweed herringbone, felt), stored as packed image textures so that glTF and FBX carry them,
# and a few material corrections. Used by art/polish_humans.py.
#
# Every normal-map image is named ..._n (the Unity project's texture importer flags *_n as a normal map) and uses
# the same texture coordinates and Mapping node as the material's base-colour texture, because URP's Lit shader
# and the FBX format know only one tiling per material.
import math
import bpy
import numpy as np


def _noise(size, seed, lo, hi):
    """Tileable band-limited noise in [-1, 1]: white noise filtered in the frequency domain."""
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal((size, size)))
    fx = np.fft.fftfreq(size) * size
    r = np.sqrt(fx[None, :] ** 2 + fx[:, None] ** 2)
    band = np.exp(-((r - (lo + hi) / 2) / max(1.0, (hi - lo) / 2)) ** 2)
    n = np.real(np.fft.ifft2(f * band))
    return n / (np.abs(n).max() + 1e-9)


def height_field(kind, size, reps, seed=7):
    """A tileable height map (0..1) of woven cloth with `reps` thread ribs across the tile."""
    y, x = np.mgrid[0:size, 0:size] / size
    reps = max(4, int(reps))
    if kind == 'tweed':      # herringbone: the twill line reverses in bands
        bands = max(2, 2 * round(reps / 12))
        zig = np.abs(((x * bands) % 2.0) - 1.0)                 # triangle wave across the bands
        h = 0.5 + 0.5 * np.sin(2 * np.pi * (y * reps + zig * reps / bands * 1.0))
        h = h ** 0.8
        h += 0.35 * (0.5 + 0.5 * np.sin(2 * np.pi * x * reps * 2)) * (0.5 + 0.5 * np.sin(2 * np.pi * y * reps * 2))
        h += 0.5 * _noise(size, seed, reps * 0.5, reps * 2.5) + 0.25 * _noise(size, seed + 1, 2, 8)
    elif kind == 'felt':
        h = 0.6 * _noise(size, seed, size / 10, size / 3) + 0.5 * _noise(size, seed + 1, 4, 16)
    elif kind == 'grain':    # for a garment's own unwrap, too coarse to hold threads: the nap of the cloth and
        # the slight unevenness of its surface, with no pattern whose scale could look wrong
        h = 0.5 * _noise(size, seed, size / 7, size / 2.6) + 0.35 * _noise(size, seed + 1, size / 24, size / 9) \
            + 0.8 * _noise(size, seed + 2, 5, 14)
    elif kind == 'rib':      # faille: fine cross ribs
        h = 0.5 + 0.5 * np.sin(2 * np.pi * y * reps)
        h = h ** 0.6 + 0.2 * _noise(size, seed, reps, reps * 3)
    else:                    # wool twill: diagonal ribs over a plain weave, a little fuzz
        h = 0.5 + 0.5 * np.sin(2 * np.pi * (x + y) * reps)
        h = h ** 0.7
        h += 0.3 * (0.5 + 0.5 * np.sin(2 * np.pi * x * reps * 2)) * (0.5 + 0.5 * np.sin(2 * np.pi * y * reps * 2))
        h += 0.35 * _noise(size, seed, reps * 0.7, reps * 3) + 0.2 * _noise(size, seed + 1, 2, 7)
    h -= h.min()
    return h / (h.max() + 1e-9)


def normal_image(name, h, slope, mask=None):
    """Tangent-space normal map (OpenGL convention, +Y up) from a tileable height map, scaled so that the
    surface's RMS slope is `slope`; mask (0..1, same size) flattens it where the cloth is not this cloth.
    Packed, non-colour."""
    size = h.shape[0]
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1))
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0))
    k = slope / (math.sqrt(float((dx * dx + dy * dy).mean())) + 1e-9)
    if mask is not None: dx = dx * mask; dy = dy * mask
    n = np.stack([-dx * k, -dy * k, np.ones_like(h)], axis=-1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    px = np.ones((size, size, 4), dtype=np.float32)
    px[..., :3] = n * 0.5 + 0.5
    old = bpy.data.images.get(name)
    if old: bpy.data.images.remove(old)
    img = bpy.data.images.new(name, size, size, alpha=False, is_data=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


def linen_mask(img, size):
    """1 where the garment's texture is cloth, 0 where it is white linen (the shirt in the suit's atlas)."""
    w, hgt = img.size
    if not w: return None
    a = np.empty(w * hgt * 4, dtype=np.float32); img.pixels.foreach_get(a)
    a = a.reshape(hgt, w, 4)[::max(1, hgt // size), ::max(1, w // size), :3][:size, :size]
    if a.shape[0] != size or a.shape[1] != size: return None
    white = (a.mean(axis=2) > 0.6) & ((a.max(axis=2) - a.min(axis=2)) < 0.14)
    m = 1.0 - white.astype(np.float32)
    for _ in range(2):
        m = (m + np.roll(m, 1, 0) + np.roll(m, -1, 0) + np.roll(m, 1, 1) + np.roll(m, -1, 1)) / 5
    return m


def metres_per_uv(objs, mat):
    """How many metres of cloth one unit of UV covers, for the faces that use this material (median)."""
    vals = []
    for o in objs:
        me = o.data
        if not me.uv_layers or mat.name not in [m.name for m in me.materials if m]: continue
        idx = [i for i, m in enumerate(me.materials) if m and m.name == mat.name]
        uv = me.uv_layers.active.data
        for p in list(me.polygons)[::max(1, len(me.polygons) // 400)]:
            if p.material_index not in idx: continue
            ls = list(p.loop_indices)
            a, b = ls[0], ls[1]
            d3 = (me.vertices[me.loops[a].vertex_index].co - me.vertices[me.loops[b].vertex_index].co).length * o.matrix_world.to_scale().x
            d2 = (uv[a].uv - uv[b].uv).length
            if d2 > 1e-6 and d3 > 1e-6: vals.append(d3 / d2)
    return float(np.median(vals)) if vals else 1.0


def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None) if m.node_tree else None


def set_normal(m, img, strength=1.0):
    """Wire img as the material's normal map, on the same coordinates as its base-colour texture."""
    nt = m.node_tree
    p = principled(m)
    for n in [n for n in nt.nodes if n.name.startswith('BB_Normal')]: nt.nodes.remove(n)
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.name = 'BB_NormalTex'; tex.image = img
    tex.location = (p.location.x - 520, p.location.y - 420)
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.name = 'BB_NormalMap'
    nm.inputs['Strength'].default_value = strength
    nm.location = (p.location.x - 220, p.location.y - 420)
    nt.links.new(tex.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    base = p.inputs['Base Color']
    if base.is_linked:
        src = base.links[0].from_node
        if src.type == 'TEX_IMAGE' and src.inputs['Vector'].is_linked:
            nt.links.new(src.inputs['Vector'].links[0].from_socket, tex.inputs['Vector'])
    return tex


def fabric_of(mname, cname):
    """(kind, rib period in metres, RMS slope) for a material, or None to leave it alone."""
    n = mname.lower()
    if any(k in n for k in ('hair', 'eyebrow', 'eyelash', 'moustache', 'beard', 'low-poly', 'body', 'shoes', 'silk',
                            'brass', 'gold', 'silver', 'ebony', 'horn', 'belt', 'badge', 'petal', 'leaf', 'band',
                            'gloves')):
        return None
    if 'tweed' in n or n.endswith('_cap'): return ('tweed', 0.0045, 0.22)
    if 'wool' in n: return ('wool', 0.0035, 0.16)
    if 'faille' in n: return ('rib', 0.003, 0.1)
    if 'felt' in n: return ('felt', 0.004, 0.07)
    if 'bowler' in n: return ('grain', 0.004, 0.035)
    if 'flat_cap' in n: return ('grain', 0.005, 0.16)
    if 'suit' in n: return ('grain', 0.0035, 0.17 if cname == 'watson' else 0.13)
    return None


def refit_coat(rig, log=print):
    """The coat's skirt was weighted to follow the thighs by half, so a leg swinging forward came through the
    cloth. Below the hips each half of the skirt now goes with the thigh on its side (more at the front, where
    the leg pushes the cloth, less at the back, where it hangs), blending across the middle."""
    from humananim import world_co
    done = []
    for o in rig.children:
        if o.type != 'MESH' or o.name not in ('Coat', 'Skirt'): continue
        co = world_co(o)
        B = rig.data.bones
        z_top = B['thigh_l'].head_local.z + 0.05
        z_hem = float(co[:, 2].min())
        y0 = B['pelvis'].head_local.y
        vg = {n: (o.vertex_groups.get(n) or o.vertex_groups.new(name=n)) for n in ('pelvis', 'thigh_l', 'thigh_r')}
        for i in range(len(co)):
            x, y, z = co[i]
            if z > z_top: continue
            front = 1 / (1 + math.exp((y - y0) / 0.035))
            k = min(1.0, (z_top - z) / max(0.01, z_top - z_hem) * 1.6) ** 1.1 * (0.5 + 0.38 * front)
            side = 1 / (1 + math.exp(-x / 0.045))
            if o.name == 'Skirt':   # a long bell skirt: the knees carry the cloth, the hem far below them sways less
                z_knee = B['calf_l'].head_local.z
                if z > z_knee: k = (z_top - z) / (z_top - z_knee)
                else: k = 1.0 - 0.6 * (z_knee - z) / max(0.01, z_knee - z_hem)
                k *= 0.42 + 0.45 * front
                side = 1 / (1 + math.exp(-x / 0.07))
            for g in list(o.data.vertices[i].groups): o.vertex_groups[g.group].remove([i])
            for nme, w in (('pelvis', 1 - k), ('thigh_l', k * side), ('thigh_r', k * (1 - side))):
                if w > 1e-4: vg[nme].add([i], float(w), 'REPLACE')
        done.append(o.name)
    return done


def tuck_under(rig, log=print):
    """Cloth under cloth: where the suit lies under the coat, draw it in a little (along its normals, smoothly
    toward the edges of the covered part), so that it does not come through when the two bend differently.
    Done once (marked on the object): the UVs and the topology are untouched."""
    from mathutils.bvhtree import BVHTree
    from mathutils import Vector
    covers = [o for o in rig.children if o.type == 'MESH' and o.name in ('Coat', 'CoatSleeves', 'Cape', 'Skirt')]
    if not covers: return 0
    verts, polys = [], []
    for o in covers:
        base = len(verts)
        verts += [o.matrix_world @ v.co for v in o.data.vertices]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    bvh = BVHTree.FromPolygons(verts, polys)
    moved = 0
    for o in rig.children:
        if o.type != 'MESH' or 'suit' not in o.name or o.get('bb_tucked'): continue
        me = o.data
        sc = o.matrix_world.to_scale().x
        n3 = o.matrix_world.to_3x3().normalized()
        m = np.zeros(len(me.vertices), dtype=np.float32)
        for v in me.vertices:
            p = o.matrix_world @ v.co; n = (n3 @ v.normal).normalized()
            hit = bvh.ray_cast(p + n * 0.0005, n, 0.07)
            if hit[0] is not None: m[v.index] = 1.0
        ea = np.empty(len(me.edges) * 2, dtype=np.int32); me.edges.foreach_get('vertices', ea); ea = ea.reshape(-1, 2)
        for _ in range(3):   # soften the border of the covered region
            acc = np.zeros_like(m); cnt = np.zeros_like(m)
            np.add.at(acc, ea[:, 0], m[ea[:, 1]]); np.add.at(acc, ea[:, 1], m[ea[:, 0]])
            np.add.at(cnt, ea[:, 0], 1); np.add.at(cnt, ea[:, 1], 1)
            m = np.minimum(m, 0.5 * m + 0.5 * acc / np.maximum(cnt, 1))
        for v in me.vertices:
            if m[v.index] > 0.01:
                v.co = v.co - v.normal * (0.013 * float(m[v.index]) / sc)
                moved += 1
        o['bb_tucked'] = 1
        me.update()
    return moved


def add_blink(rig, log=print):
    """Shape keys 'Blink' (both eyes), 'BlinkL' and 'BlinkR' on the head mesh and on the eyelashes: the upper lid
    turns down over the eyeball about the eye's own axis, the lower lid comes up a little to meet it. Built from
    where the vertices are (the faces were thinned, so there is no topology to rely on). Replaced if present."""
    from humananim import world_co
    body = next((o for o in rig.children if o.type == 'MESH' and o.name == 'Human'), None)
    eyes = next((o for o in rig.children if o.type == 'MESH' and o.name.endswith('low-poly')), None)
    lash = next((o for o in rig.children if o.type == 'MESH' and 'eyelashes' in o.name), None)
    if not body or not eyes: return []
    ev = world_co(eyes)
    info = {}
    bco = world_co(body)
    for side, sel in (('L', ev[:, 0] > 0), ('R', ev[:, 0] < 0)):
        c = (ev[sel].min(0) + ev[sel].max(0)) / 2
        r = float((ev[sel].max(0) - ev[sel].min(0)).mean() / 2)
        rel = bco - c
        d = np.linalg.norm(rel, axis=1)
        near = (d < 1.4 * r) & (d > 0.9 * r) & (rel[:, 1] < -0.55 * r) & (np.abs(rel[:, 0]) < 0.6 * r)
        phi = np.arctan2(rel[:, 2], -rel[:, 1])
        up = phi[near & (phi > 0.02)]; lo = phi[near & (phi < -0.02)]
        if len(up) < 3 or len(lo) < 3: return []
        pu, pl = float(np.percentile(up, 8)), float(np.percentile(lo, 92))
        if lash is not None:   # the lashes grow from the lid margins: their roots say where the margins are
            lr = world_co(lash) - c
            ld = np.linalg.norm(lr, axis=1)
            lphi = np.arctan2(lr[:, 2], -lr[:, 1])
            mine = (ld < 2.2 * r) & (np.abs(lr[:, 0]) < 0.7 * r)
            for sign in (1, -1):
                mm = mine & (lphi * sign > 0)
                if mm.sum() >= 4:
                    roots = lphi[mm][np.argsort(ld[mm])[:max(3, int(mm.sum() * 0.35))]]
                    if sign > 0: pu = float(np.median(roots))
                    else: pl = float(np.median(roots))
        log('   eye', side, 'lid margins at', round(pu, 2), round(pl, 2), 'rad')
        info[side] = (c, r, pu, pl, (ev[sel].max(0) - ev[sel].min(0)) / 2)
    def displaced(co, sides):
        out = co.copy()
        for side in sides:
            c, r, pu, pl, rv = info[side]
            rel = co - c
            d = np.linalg.norm(rel, axis=1)
            phi = np.arctan2(rel[:, 2], -rel[:, 1])
            sm = lambda x: np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))
            lat = 1 - sm((np.abs(rel[:, 0]) - 1.0 * r) / (0.9 * r))
            rad = 1 - sm((d - 1.3 * r) / (0.7 * r))
            front = (rel[:, 1] < -0.3 * r)
            gap = pu - pl
            wu = (1 - sm((phi - pu) / 0.5)) * (phi > pu - 0.06) * lat * rad * front
            wl = (1 - sm((pl - phi) / 0.5)) * (phi < pl + 0.06) * lat * rad * front
            ang = gap * 0.95 * wu - gap * 0.16 * wl          # + turns a point in front of the eye downward
            ca, sa = np.cos(ang), np.sin(ang)
            y = rel[:, 1] * ca - rel[:, 2] * sa
            z = rel[:, 1] * sa + rel[:, 2] * ca
            new = np.stack([rel[:, 0], y, z], axis=1)
            # keep the closing lid outside the eyeball
            nd = np.linalg.norm(new / (rv * 1.13), axis=1)     # the eyeball is not quite a sphere
            push = np.where((np.abs(ang) > 0.02) & (nd < 1.0) & (new[:, 1] < 0), 1.0 / np.maximum(nd, 1e-6), 1.0)
            moved = np.abs(ang) > 1e-5
            res = c + new * push[:, None]
            moved &= np.isfinite(res).all(axis=1)   # (a vertex at the eye's very centre has no direction)
            out[moved] = res[moved]
        return out
    made = []
    for o in (body, lash):
        if o is None: continue
        me = o.data
        if not me.shape_keys: o.shape_key_add(name='Basis', from_mix=False)
        co = world_co(o)
        M = np.array(o.matrix_world); Minv = np.linalg.inv(M)
        for key, sides in (('Blink', 'LR'), ('BlinkL', 'L'), ('BlinkR', 'R')):
            old = me.shape_keys.key_blocks.get(key)
            if old: o.shape_key_remove(old)
            kb = o.shape_key_add(name=key, from_mix=False)
            new = displaced(co, sides)
            loc = new @ Minv[:3, :3].T + Minv[:3, 3]
            kb.data.foreach_set('co', loc.astype(np.float32).ravel())
            kb.value = 0.0
            made.append(f'{o.name}:{key}')
        o.active_shape_key_index = 0
    return made


def polish_look(rig, cname, log=print):
    objs = [o for o in rig.children if o.type == 'MESH']
    coats = refit_coat(rig, log)
    tucked = tuck_under(rig, log)
    if coats or tucked: log(cname, 'coat skirt re-weighted' if coats else '', f'{tucked} suit vertices drawn in under the coat' if tucked else '')
    mats = {m.name: m for o in objs for m in o.data.materials if m}
    made = []
    for m in mats.values():
        fab = fabric_of(m.name, cname)
        p = principled(m)
        if not fab or not p: continue
        kind, period, slope = fab
        base = p.inputs['Base Color']
        scale = 1.0
        atlas = False
        if base.is_linked and base.links[0].from_node.type == 'TEX_IMAGE':
            tex = base.links[0].from_node
            if tex.inputs['Vector'].is_linked and tex.inputs['Vector'].links[0].from_node.type == 'MAPPING':
                scale = float(tex.inputs['Vector'].links[0].from_node.inputs['Scale'].default_value[0])
            else:
                atlas = True     # one unwrap for the whole garment: the weave is baked across all of it
        mpu = metres_per_uv(objs, m)
        tile_m = mpu / scale                       # metres of cloth across one repeat of the texture
        size = 512 if atlas else 256
        if atlas and kind not in ('grain', 'felt'): kind = 'grain'
        reps = min(tile_m / period, size / 5.0)    # no finer than the texture can hold
        mask = linen_mask(base.links[0].from_node.image, size) if atlas and 'suit' in m.name else None
        short = m.name.split('_', 1)[-1].replace('Human.', '').replace('.', '_')
        img = normal_image(f'{cname}_{short}_n', height_field(kind, size, reps, seed=len(m.name)), slope, mask)
        set_normal(m, img, 1.0)
        made.append(f'{img.name}({kind})')
    # skin: a touch less plastic
    for m in mats.values():
        if 'body' in m.name.lower():
            p = principled(m)
            if p:
                p.inputs['Roughness'].default_value = max(p.inputs['Roughness'].default_value, 0.55)
                if 'Subsurface Weight' in p.inputs: p.inputs['Subsurface Weight'].default_value = 0.0
    keys = add_blink(rig, log)
    if keys: log(cname, 'shape keys:', ', '.join(keys))
    if made: log(cname, 'normal maps:', ', '.join(made))
    return made
