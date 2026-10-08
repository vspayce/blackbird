# Builds the realistic cast for The Black Bird with MPFB (MakeHuman for Blender).
#
#   BLENDER_USER_CONFIG=art/.blender-config /Applications/Blender.app/Contents/MacOS/Blender -b \
#       --python art/build_humans.py -- [--only holmes,watson] [--render out_dir]
#
# The separate config keeps MPFB enabled for these builds whatever your everyday
# Blender preferences say. First time only:
#   BLENDER_USER_CONFIG=art/.blender-config Blender -b --python-expr "import bpy; \
#       bpy.ops.preferences.addon_enable(module='bl_ext.blender_org.mpfb'); bpy.ops.wm.save_userpref()"
#
# Needs the MPFB extension and these MakeHuman asset packs in its user data:
# makehuman_system_assets, suits01, skins02, eyebrows01, bodyparts05 (CC0) and
# hats03, bodyparts06 (CC-BY, credited in CREDITS.md).
#
# For each character: a MakeHuman body shaped by macros and face targets, the
# game_engine rig, period clothes (MakeHuman suits recoloured, plus coats,
# capes and hats made here and fitted to the body by ray-casting its
# silhouette), re-rested arms-down, with Idle / Walk / Talk / LieBack clips.
# Exports public/models/<name>.glb and saves art/humans/<name>.blend.
import bpy, bmesh, math, os, sys, glob, random
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default

import bl_ext.blender_org.mpfb as mpfb
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.targetservice import TargetService
from bl_ext.blender_org.mpfb.services.locationservice import LocationService

SYS = os.path.join(os.path.dirname(mpfb.__file__), 'data')
USR = LocationService.get_user_data()
FPS = 30


def asset(kind, name, ext='mhclo'):
    hits = glob.glob(os.path.join(USR, kind, name, f'*.{ext}'))
    if not hits: raise FileNotFoundError(f'{kind}/{name}/*.{ext}: install the MakeHuman asset pack that has it')
    return hits[0]


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


# --- materials -------------------------------------------------------------------

def principled(m):
    return next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')


def hex01(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def bake_base_colour(obj, fn, rough=None):
    """Recolour a material's base-colour texture by rewriting its pixels (sRGB, 0-1) with fn(rgb, lum) -> rgb,
    and wire the texture straight to the shader, so the result survives glTF export."""
    import numpy as np
    for m in obj.data.materials:
        nt, p = m.node_tree, principled(m)
        tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.name.lower().startswith('diffuse')), None)
        if tex is None or tex.image is None:
            continue
        src = tex.image
        w, h = src.size
        px = np.empty(w * h * 4, dtype=np.float32)
        src.pixels.foreach_get(px)
        px = px.reshape(-1, 4)
        rgb = px[:, :3]
        lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        px[:, :3] = np.clip(fn(rgb, lum[:, None]), 0, 1)
        out = bpy.data.images.new(f'{obj.name}_{src.name}'.replace('.', '_'), w, h, alpha=True)
        out.pixels.foreach_set(px.ravel())
        out.pack()
        tex.image = out
        nt.links.new(tex.outputs['Color'], p.inputs['Base Color'])
        if rough is not None:
            for l in list(p.inputs['Roughness'].links): nt.links.remove(l)
            p.inputs['Roughness'].default_value = rough


def tint(obj, hex, keep_texture=0.35, rough=None):
    """Recolour toward a flat colour, keeping keep_texture of the texture's light and shade (weave, folds)."""
    c = hex01(hex)
    bake_base_colour(obj, lambda rgb, lum: c * ((1 - keep_texture) + keep_texture * lum / max(0.2, float(lum.mean()))),
                     rough)


def split_tint(obj, dark_hex, light_hex, threshold=0.5, rough=0.85):
    """For texture atlases holding a suit and a shirt: dark texels become the cloth colour, light ones the shirt."""
    import numpy as np
    d, l = np.array(hex01(dark_hex)), np.array(hex01(light_hex))
    def fn(rgb, lum):
        t = np.clip((lum - (threshold - 0.06)) / 0.12, 0, 1)
        t = t * t * (3 - 2 * t)
        return (d * (1 - t) + l * t) * (0.75 + 0.25 * lum / max(0.2, float(lum.mean())))
    bake_base_colour(obj, fn, rough)


def slick_hair(hair, body, keep=0.3, gap=0.004):
    """Pull hair in toward the scalp, keeping a little of its volume: hair worn short and oiled back."""
    bvh = world_mesh_bvh([body])
    for v in hair.data.vertices:
        loc, nrm, i, d = bvh.find_nearest(v.co)
        if loc is None: continue
        out = (v.co - loc).length
        v.co = loc + nrm * max(gap, out * keep)


def eye_colour(eyes, colour):
    path = os.path.join(USR, 'eyes', 'materials', f'{colour}_eye.png')
    img = bpy.data.images.load(path)
    for m in eyes.data.materials:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE': n.image = img


_tex = {}
def cloth_texture(kind, hex, size=512):
    """A small tiling cloth texture (tweed herringbone or plain wool) as an image, so it survives glTF export."""
    key = (kind, hex)
    if key in _tex: return _tex[key]
    img = bpy.data.images.new(f'{kind}_{hex.strip("#")}', size, size)
    base = srgb(hex)
    rnd = random.Random(7)
    px = [0.0] * (size * size * 4)
    noise = [rnd.random() for _ in range(size * size)]
    for y in range(size):
        for x in range(size):
            n = noise[y * size + x]
            if kind == 'tweed':
                band = (x // 8) % 2
                diag = ((x + (y if band else -y)) // 3) % 2
                k = 0.78 + 0.16 * diag + 0.22 * (n - 0.5) + (0.18 if n > 0.985 else 0)  # flecks
            else:
                k = 0.9 + 0.12 * (n - 0.5) + 0.04 * ((x + y) % 2)
            i = (y * size + x) * 4
            px[i:i + 4] = [min(1, base[0] * k), min(1, base[1] * k), min(1, base[2] * k), 1]
    img.pixels = px
    img.pack()
    _tex[key] = img
    return img


def fabric(name, hex, kind='wool', rough=0.95, scale=6.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = principled(m)
    p.inputs['Roughness'].default_value = rough
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = cloth_texture(kind, hex)
    uv = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, 1)
    nt.links.new(uv.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], tex.inputs['Vector'])
    nt.links.new(tex.outputs['Color'], p.inputs['Base Color'])
    m.use_backface_culling = False
    return m


def plain(name, hex, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = principled(m)
    p.inputs['Base Color'].default_value = srgb(hex) + [1]
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    return m


# --- body -------------------------------------------------------------------------

def make_body(c):
    macro = TargetService.get_default_macro_info_dict()
    macro.update(gender=1.0, cupsize=0.5, firmness=0.5, **c['macro'])
    macro['race'] = {'caucasian': 1.0, 'asian': 0.0, 'african': 0.0}
    body = HumanService.create_human(macro_detail_dict=macro)
    for k, w in c.get('face', {}).items():
        TargetService.load_target(body, os.path.join(SYS, 'targets', k + '.target.gz'), weight=w)
    HumanService.add_builtin_rig(body, 'game_engine')
    HumanService.set_character_skin(asset('skins', c.get('skin', 'middleage_caucasian_male'), 'mhmat'), body,
                                    skin_type='GAMEENGINE')
    parts = {}
    for kind, name in [('eyes', 'low-poly'), ('eyebrows', c.get('eyebrows', 'eyebrow012')), ('eyelashes', 'eyelashes01'),
                       ] + [('hair', h) for h in c.get('hair', [])]:
        parts[name] = HumanService.add_mhclo_asset(asset(kind, name), body, asset_type=kind.capitalize(),
                                                   subdiv_levels=0, material_type='MAKESKIN')
    for name in c.get('clothes', []):
        parts[name] = HumanService.add_mhclo_asset(asset('clothes', name), body, asset_type='Clothes',
                                                   subdiv_levels=0, material_type='MAKESKIN')
    TargetService.bake_targets(body)
    return body, body.parent, parts


def pose_world(rig, bone, R):
    """Rotate a pose bone by a rotation R given in armature space (at rest)."""
    M = rig.data.bones[bone].matrix_local.to_3x3()
    pb = rig.pose.bones[bone]
    pb.rotation_mode = 'QUATERNION'
    pb.rotation_quaternion = (M.inverted() @ R.to_matrix() @ M).to_quaternion()


def aim(rig, bone, direction):
    b = rig.data.bones[bone]
    cur = (b.tail_local - b.head_local).normalized()
    pose_world(rig, bone, cur.rotation_difference(Vector(direction).normalized()))


def rerest_arms_down(rig, meshes):
    """MakeHuman rests in an A-pose; re-rest the character with the arms hanging, so garments and clips start relaxed."""
    for s, side in ((1, 'l'), (-1, 'r')):
        aim(rig, f'upperarm_{side}', (s * 0.12, 0.02, -1))
        aim(rig, f'thigh_{side}', (s * 0.035, 0.0, -1))
    bpy.context.view_layer.update()
    for s, side in ((1, 'l'), (-1, 'r')):
        # a slight natural bend at the elbow, palms toward the thighs
        pose_world(rig, f'lowerarm_{side}', Quaternion((1, 0, 0), -0.12))
    bpy.context.view_layer.update()
    # bake the posed shape into each mesh (only the armature deforming), then make that pose the rest pose
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in meshes:
        saved = [(md, md.show_viewport) for md in ob.modifiers if md.type != 'ARMATURE']
        for md, _ in saved: md.show_viewport = False
        dg.update()
        ev = ob.evaluated_get(dg).to_mesh()
        assert len(ev.vertices) == len(ob.data.vertices), ob.name
        co = [0.0] * (len(ev.vertices) * 3)
        ev.vertices.foreach_get('co', co)
        ob.evaluated_get(dg).to_mesh_clear()
        ob.data.vertices.foreach_set('co', co)
        ob.data.update()
        for md, vis in saved: md.show_viewport = vis
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)


# --- fitted garments --------------------------------------------------------------

def world_mesh_bvh(objects, drop_groups=()):
    """A BVH of the evaluated meshes in world space, optionally without faces weighted to some bones (the arms)."""
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys = [], []
    for ob in objects:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        idx = {g.name: g.index for g in ob.vertex_groups}
        drop = {idx[g] for g in drop_groups if g in idx}
        bad = set()
        if drop:
            src = ob.data
            for v in src.vertices:
                if sum(g.weight for g in v.groups if g.group in drop) > 0.4: bad.add(v.index)
        off = len(verts)
        verts += [ob.matrix_world @ v.co for v in me.vertices]
        for p in me.polygons:
            if bad and any(i in bad for i in p.vertices): continue
            polys.append([off + i for i in p.vertices])
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def hull2d(pts):
    pts = sorted(set(pts))
    if len(pts) < 3: return pts
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def ray_polygon(c, d, poly):
    best = 0.0
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = d[0] * ey - d[1] * ex
        if abs(den) < 1e-9: continue
        t = ((a[0] - c[0]) * ey - (a[1] - c[1]) * ex) / den
        u = ((a[0] - c[0]) * d[1] - (a[1] - c[1]) * d[0]) / den
        if t > 0 and -1e-6 <= u <= 1 + 1e-6: best = max(best, t)
    return best


def envelope(bvh, z, centre, seg, reach=0.7):
    """Radii, one per angle, of the convex outline of the body slice at height z (front is -Y)."""
    hits = []
    for j in range(seg * 2):
        a = 2 * math.pi * j / (seg * 2)
        d = Vector((math.cos(a), math.sin(a), 0))
        o = Vector((centre[0], centre[1], z)) + d * reach
        loc, nrm, i, dist = bvh.ray_cast(o, -d, reach)
        if loc: hits.append((loc.x, loc.y))
    if len(hits) < 3: return None
    poly = hull2d(hits)
    out = []
    for j in range(seg):
        a = -math.pi / 2 + 2 * math.pi * j / seg
        out.append(ray_polygon(centre, (math.cos(a), math.sin(a)), poly))
    return out


def smooth_ring(r, k=2):
    for _ in range(k):
        r = [(r[i - 1] + 2 * r[i] + r[(i + 1) % len(r)]) / 4 for i in range(len(r))]
    return r


def garment(name, mat, rows, centre, seg=48, gap=0.0, thickness=0.006, uv_scale=1.0):
    """rows: [(z, [radius per angle])] top to bottom. Builds a cloth shell, open at the front by gap radians,
    or by gap(z) when the opening changes with height."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new()
    grid = []
    gapf = gap if callable(gap) else (lambda z: gap)
    n = seg if not callable(gap) and gap <= 0 else seg + 1
    for z, radii in rows:
        g = gapf(z)
        a0 = -math.pi / 2 + g / 2
        span = 2 * math.pi - g
        row = []
        for j in range(n):
            t = j / seg
            a = a0 + span * t
            # radii are sampled from the front (-Y) round; look up by angle
            jj = ((a + math.pi / 2) / (2 * math.pi)) * len(radii)
            i0 = int(math.floor(jj)) % len(radii); f = jj - math.floor(jj)
            r = radii[i0] * (1 - f) + radii[(i0 + 1) % len(radii)] * f
            row.append(bm.verts.new((centre[0] + r * math.cos(a), centre[1] + r * math.sin(a), z)))
        grid.append(row)
    for i in range(len(grid) - 1):
        for j in range(seg):
            k = (j + 1) % n
            f = bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][k], grid[i][k]))
            f.smooth = True
            for loop, (jj, ii) in zip(f.loops, ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))):
                loop[uvl].uv = (jj / seg * 3.0 * uv_scale, -grid[ii][0].co.z * 1.5 * uv_scale)
    for v in [v for v in bm.verts if not v.link_faces]: bm.verts.remove(v)
    bm.normal_update()
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    if thickness:
        sol = ob.modifiers.new('Thickness', 'SOLIDIFY'); sol.thickness = thickness; sol.offset = 1
        with bpy.context.temp_override(object=ob, active_object=ob):
            bpy.ops.object.modifier_apply(modifier=sol.name)
    return ob


def bone_head(rig, b): return rig.matrix_world @ rig.data.bones[b].head_local
def bone_tail(rig, b): return rig.matrix_world @ rig.data.bones[b].tail_local


ARM_GROUPS = [f'{p}_{s}' for s in 'lr' for p in ('upperarm', 'lowerarm', 'hand', 'thumb_01', 'thumb_02', 'thumb_03',
              'index_01', 'index_02', 'index_03', 'middle_01', 'middle_02', 'middle_03', 'ring_01', 'ring_02',
              'ring_03', 'pinky_01', 'pinky_02', 'pinky_03')]


def bind(ob, rig, weights):
    """weights(vertex co) -> {bone: w}. Parent to the rig with an armature modifier."""
    for v in ob.data.vertices:
        for b, w in weights(v.co).items():
            if w <= 0: continue
            g = ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)
            g.add([v.index], w, 'REPLACE')
    ob.parent = rig
    md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = rig


def transfer_weights(ob, src, rig, extra=None):
    """Copy skin weights from the nearest surface of src (the body), then let extra(co, weights) adjust them."""
    for g in src.vertex_groups:
        if g.name in rig.data.bones and g.name not in ob.vertex_groups: ob.vertex_groups.new(name=g.name)
    dt = ob.modifiers.new('Weights', 'DATA_TRANSFER')
    dt.object = src; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}
    dt.vert_mapping = 'POLYINTERP_NEAREST'; dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=dt.name)
    names = {g.index: g.name for g in ob.vertex_groups}
    arms = set(ARM_GROUPS)
    for v in ob.data.vertices:
        # coats and capes hang from the torso; never let a hand or forearm drag them about
        w = {names[g.group]: g.weight for g in v.groups if names[g.group] not in arms}
        w2 = extra(v.co, w) if extra else None
        if w2 is None:
            if len(w) == len(v.groups): continue
            w2 = w or {'spine_01': 1.0}
        for g in list(v.groups): ob.vertex_groups[g.group].remove([v.index])
        tot = sum(x for x in w2.values() if x > 0) or 1
        for b, x in w2.items():
            if x > 0:
                (ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)).add([v.index], x / tot, 'REPLACE')
    ob.parent = rig
    md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = rig


def skirt_weights(rig, z_top, z_hem):
    """Below the hips, a coat skirt follows the pelvis and, more toward the hem, the thigh on its side."""
    def f(co, w):
        if co.z > z_top: return None
        k = min(1, (z_top - co.z) / max(0.01, z_top - z_hem)) * 0.45
        side = 1 / (1 + math.exp(-co.x / 0.07))  # 0 = right, 1 = left
        return {'pelvis': 1 - k, 'thigh_l': k * side, 'thigh_r': k * (1 - side)}
    return f


def long_coat(name, rig, sources, mat, z_neck, z_hem, flare=0.06, gap=0.0, offset=0.018, include_arms=False,
              collar=True):
    """A coat body fitted round the torso (and arms, for a cloak), flaring to the hem."""
    centre = (0.0, (bone_head(rig, 'spine_02').y + bone_head(rig, 'pelvis').y) / 2)
    bvh = world_mesh_bvh(sources, () if include_arms else ARM_GROUPS)
    z_hip = bone_head(rig, 'thigh_l').z
    rows, prev = [], None
    steps = int((z_neck - z_hem) / 0.035)
    for i in range(steps + 1):
        z = z_neck - (z_neck - z_hem) * i / steps
        r = envelope(bvh, z, centre, 48)
        if r is None: r = prev
        r = [x + offset for x in r]
        if prev and z < z_hip:  # never tuck back in below the hips; let it fall and flare
            t = (z_hip - z) / (z_hip - z_hem)
            r = [max(a, b * 0.985) + flare * 0.025 * (1 + t) / (steps / 10) for a, b in zip(r, prev)]
        r = smooth_ring(r, 3)
        rows.append((z, r)); prev = r
    if collar:  # a stand collar round the neck
        rn = rows[0][1]
        rows.insert(0, (z_neck + 0.05, [x * 0.97 for x in rn]))
    return garment(name, mat, rows, centre, seg=44, gap=gap)


def cape(name, rig, sources, mat, z_top, z_hem, offset=0.025):
    """Inverness cape: hangs from the shoulders over the arms."""
    centre = (0.0, bone_head(rig, 'spine_03').y)
    bvh = world_mesh_bvh(sources)
    rows, prev = [], None
    steps = int((z_top - z_hem) / 0.02)
    for i in range(steps + 1):
        z = z_top - (z_top - z_hem) * i / steps
        r = envelope(bvh, z, centre, 64, reach=0.9)
        if r is None: r = prev
        r = [x + offset + 0.012 * i / steps for x in r]
        if prev: r = [max(a, b * 0.995) for a, b in zip(r, prev)]
        r = smooth_ring(r, 4)
        rows.append((z, r)); prev = r
    return garment(name, mat, rows, centre, seg=64, gap=0.05)


def lathe_obj(name, mat, prof, centre, seg=32, sx=1.0, sy=1.0, tilt=0.0):
    rows = [(z, [r * math.hypot(sx * math.cos(2 * math.pi * j / 64 - math.pi / 2),
                                 sy * math.sin(2 * math.pi * j / 64 - math.pi / 2)) for j in range(64)]) for r, z in prof]
    ob = garment(name, mat, rows, centre, seg=seg, thickness=0.004)
    if tilt:
        for v in ob.data.vertices:
            v.co = Matrix.Rotation(tilt, 3, 'X') @ (v.co - Vector((centre[0], centre[1], prof[0][1]))) + \
                   Vector((centre[0], centre[1], prof[0][1]))
    return ob


def head_frame(rig, body):
    """Centre and size of the skull top, measured from the body mesh around the head bone."""
    h = bone_head(rig, 'head')
    top = max((body.matrix_world @ v.co).z for v in body.data.vertices if (body.matrix_world @ v.co - h).length < 0.3)
    return h, top


def deerstalker(rig, body, mat):
    h, top = head_frame(rig, body)
    c = (0.0, h.y + 0.005)
    zb = top - 0.075  # the band sits a little above the brows
    crown = lathe_obj('Deerstalker', mat, [(0.106, zb), (0.108, zb + 0.03), (0.1, zb + 0.06), (0.078, zb + 0.085),
                                           (0.04, zb + 0.1), (0.002, zb + 0.104)], c, sx=0.94, sy=1.1, tilt=-0.12)
    bm = bmesh.new(); bm.from_mesh(crown.data)
    for s in (-1, 1):  # front and back peaks
        rim = [(0.09 * math.cos(t), c[1] + s * (0.11 + 0.065 * math.sin(t)), zb + 0.005 - 0.03 * math.sin(t))
               for t in (math.pi * i / 12 for i in range(13))]
        vc = bm.verts.new((0, c[1] + s * 0.105, zb + 0.008))
        vs = [bm.verts.new(p) for p in rim]
        for a, b in zip(vs, vs[1:]): bm.faces.new((vc, a, b)).smooth = True
    for s in (-1, 1):  # ear flaps tied up over the crown
        x0 = s * 0.098
        quad = [bm.verts.new(p) for p in ((x0, c[1] - 0.04, zb + 0.02), (x0, c[1] + 0.04, zb + 0.02),
                                         (s * 0.06, c[1] + 0.035, zb + 0.095), (s * 0.06, c[1] - 0.035, zb + 0.095))]
        bm.faces.new(quad).smooth = True
    bm.to_mesh(crown.data); bm.free()
    bind(crown, rig, lambda co: {'head': 1.0})
    return crown


def top_hat(rig, body, mat):
    """A silk top hat, brim curled up at the sides."""
    h, top = head_frame(rig, body)
    c = (0.0, h.y + 0.005)
    zb = top - 0.085
    ob = lathe_obj('TopHat', mat, [(0.17, zb - 0.002), (0.152, zb - 0.004), (0.108, zb), (0.104, zb + 0.004),
                                   (0.1, zb + 0.07), (0.104, zb + 0.15), (0.106, zb + 0.165), (0.104, zb + 0.168),
                                   (0.002, zb + 0.17)], c, sx=0.93, sy=1.12, tilt=-0.06)
    for v in ob.data.vertices:  # curl the brim up at the sides
        d = math.hypot(v.co.x, v.co.y - c[1])
        if d > 0.12 and v.co.z < zb + 0.01: v.co.z += 0.9 * (abs(v.co.x) / 0.17) ** 2 * (d - 0.11)
    band = lathe_obj('HatBand', plain('band', '#050505', 0.5), [(0.1015, zb + 0.004), (0.101, zb + 0.032)], c,
                     sx=0.94, sy=1.13, tilt=-0.06)
    for o in (ob, band): bind(o, rig, lambda co: {'head': 1.0})
    return ob


def watch_chain(rig, coat_front, mat, z):
    """A gold watch chain looped across the waistcoat between two pockets."""
    pts = [(x, coat_front(x, z - 0.02 - 0.05 * math.cos(x / 0.11 * math.pi / 2)) , z - 0.02 - 0.05 * math.cos(x / 0.11 * math.pi / 2))
           for x in [i / 12 * 0.22 - 0.11 for i in range(13)]]
    cu = bpy.data.curves.new('Chain', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0025; cu.bevel_resolution = 1
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, (x, y, zz) in zip(sp.points, pts): p.co = (x, y - 0.006, zz, 1)
    ob = bpy.data.objects.new('Chain', cu); bpy.context.scene.collection.objects.link(ob)
    cu.materials.append(mat)
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob], selected_editable_objects=[ob]):
        bpy.ops.object.convert(target='MESH')
    ob = bpy.context.scene.objects['Chain']
    bind(ob, rig, lambda co: {'spine_01': 1.0})
    return ob


def police_helmet(rig, body, mat, brass):
    h, top = head_frame(rig, body)
    c = (0.0, h.y + 0.005)
    zb = top - 0.07
    ob = lathe_obj('Helmet', mat, [(0.128, zb - 0.006), (0.112, zb), (0.11, zb + 0.06), (0.1, zb + 0.13),
                                   (0.075, zb + 0.18), (0.04, zb + 0.2), (0.002, zb + 0.205)], c, sx=0.95, sy=1.12,
                   tilt=-0.08)
    badge = lathe_obj('Badge', brass, [(0.026, 0), (0.026, 0.004), (0.002, 0.006)], (0, 0), seg=16)
    for v in badge.data.vertices:
        v.co = Matrix.Rotation(math.pi / 2, 3, 'X') @ v.co + Vector((0, c[1] - 0.122, zb + 0.08))
    bind(ob, rig, lambda co: {'head': 1.0}); bind(badge, rig, lambda co: {'head': 1.0})
    return ob


def buttons(rig, mat, xs, ys, zs, name='Buttons'):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    for x, y, z in zip(xs, ys, zs):
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=0.009,
                                  matrix=Matrix.Translation((x, y, z)) @ Matrix.Diagonal((1, 0.5, 1, 1)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    bind(ob, rig, lambda co: {'spine_03' if co.z > bone_head(rig, 'spine_03').z else 'spine_02': 1.0})
    return ob


def front_of(ob, x, z):
    """y of the front surface of ob at (x, z), from a ray cast forward-to-back."""
    bvh = world_mesh_bvh([ob])
    loc, *_ = bvh.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)), 2)
    return loc.y if loc else None


# --- clips ----------------------------------------------------------------------

def aim_posed(rig, bone, direction):
    """Turn a bone, as currently posed (parents included), to point along an armature-space direction."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[bone]
    cur = (pb.tail - pb.head).normalized()
    R = cur.rotation_difference(Vector(direction).normalized()).to_matrix()
    M = pb.matrix.to_3x3().normalized()
    pb.rotation_quaternion = (pb.rotation_quaternion.to_matrix() @ M.inverted() @ R @ M).to_quaternion()


def key_pose(rig, frame, rot, aims=None):
    """rot: {bone: (axis, angle)} in armature space; aims: {bone: direction} applied after, parents first.
    Unspecified bones go back to rest."""
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for b, val in rot.items():
        if b == 'pelvis_z':
            rig.pose.bones['pelvis'].location = rig.data.bones['pelvis'].matrix_local.to_3x3().inverted() @ Vector((0, 0, val))
            continue
        q = Quaternion()
        for axis, ang in (val if isinstance(val, list) else [val]):
            q = Quaternion(axis, ang) @ q
        pose_world(rig, b, q)
    for b, d in (aims or {}).items():
        aim_posed(rig, b, d)
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        pb.keyframe_insert('location', frame=frame)


def clip(rig, name, frames, poses, cyclic=True):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = act
    for f, rot, *aims in poses:
        key_pose(rig, f, rot, aims[0] if aims else None)
    act.frame_range = (0, frames)
    track = rig.animation_data.nla_tracks.new(); track.name = name
    track.strips.new(name, 0, act)
    rig.animation_data.action = None
    return act


X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


def make_clips(rig, gait=1.0):
    # Idle: slow breathing and a little weight shift. 4 s.
    clip(rig, 'Idle', 120, [(f, {
        'spine_02': (X, -0.012 * math.sin(2 * math.pi * f / 120)),
        'spine_03': (X, -0.018 * math.sin(2 * math.pi * f / 120)),
        'pelvis': (Y, 0.01 * math.sin(2 * math.pi * f / 120 + 1)),
        'head': (Z, 0.03 * math.sin(2 * math.pi * f / 120 * 0.5)),
    }) for f in range(0, 121, 10)])

    # Walk: one stride each side in 1.1 s. Forward swing is a negative turn about X (the character faces -Y).
    n = 33
    poses = []
    for f in range(0, n + 1, 3):
        p = 2 * math.pi * f / n
        s = math.sin(p)
        knee = lambda ph: max(0.0, math.sin(ph - 0.9)) ** 1.5 * 0.65 + 0.06
        poses.append((f, {
            'thigh_l': (X, -0.32 * s * gait), 'thigh_r': (X, 0.32 * s * gait),
            'calf_l': (X, knee(p + math.pi) * gait), 'calf_r': (X, knee(p) * gait),
            'foot_l': (X, -0.15 * max(0, math.sin(p + math.pi - 1.2))), 'foot_r': (X, -0.15 * max(0, math.sin(p - 1.2))),
            'upperarm_l': (X, 0.28 * s * gait), 'upperarm_r': (X, -0.28 * s * gait),
            'lowerarm_l': (X, -0.15 - 0.12 * max(0, -s)), 'lowerarm_r': (X, -0.15 - 0.12 * max(0, s)),
            'pelvis': (Z, 0.08 * s * gait), 'spine_03': (Z, -0.1 * s * gait),
            'spine_01': (X, -0.03),
            'pelvis_z': 0.018 * abs(math.cos(p)) - 0.01,
        }))
    clip(rig, 'Walk', n, poses)

    # Talk: idle plus a nod and an open-handed gesture of the right forearm. 3 s.
    clip(rig, 'Talk', 90, [(f, {
        'spine_03': (X, -0.015 * math.sin(2 * math.pi * f / 90)),
        'head': [(X, -0.06 * math.sin(2 * math.pi * f / 45)), (Z, 0.06 * math.sin(2 * math.pi * f / 90))],
        'upperarm_r': (X, -0.25 - 0.08 * math.sin(2 * math.pi * f / 90)),
        'lowerarm_r': (X, -0.9 - 0.25 * math.sin(2 * math.pi * f / 45)),
        'hand_r': (Y, 0.4),
    }) for f in range(0, 91, 5)])

    # LieBack: a single pose for the body in the alley (the game lays the figure down).
    clip(rig, 'LieBack', 1, [(0, {
        'thigh_l': (Y, -0.06), 'thigh_r': (Y, 0.09), 'head': (Y, 0.35),
    }, {  # arms flung out flat on the cobbles (the game lays him on his back, so 'down' here is along the ground)
        'upperarm_l': (0.85, 0.12, -0.5), 'lowerarm_l': (0.95, 0.15, -0.1), 'hand_l': (0.95, 0.2, -0.05),
        'upperarm_r': (-0.8, 0.12, -0.6), 'lowerarm_r': (-0.9, 0.2, -0.35), 'hand_r': (-0.85, 0.25, -0.3),
    }), (1, {
        'thigh_l': (Y, -0.06), 'thigh_r': (Y, 0.09), 'head': (Y, 0.35),
    }, {  # arms flung out flat on the cobbles (the game lays him on his back, so 'down' here is along the ground)
        'upperarm_l': (0.85, 0.12, -0.5), 'lowerarm_l': (0.95, 0.15, -0.1), 'hand_l': (0.95, 0.2, -0.05),
        'upperarm_r': (-0.8, 0.12, -0.6), 'lowerarm_r': (-0.9, 0.2, -0.35), 'hand_r': (-0.85, 0.25, -0.3),
    })])
    for pb in rig.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)


# --- cast -------------------------------------------------------------------------

CAST = {
    'holmes': dict(
        height=1.86,
        macro=dict(age=0.62, muscle=0.5, weight=0.28, height=0.75, proportions=0.75),
        face={'head/head-oval': 0.6, 'head/head-scale-horiz-decr': 0.35, 'head/head-scale-vert-incr': 0.15,
              'nose/nose-hump-incr': 0.8, 'nose/nose-scale-vert-incr': 0.45, 'nose/nose-point-down': 0.35,
              'nose/nose-scale-horiz-decr': 0.3, 'nose/nose-trans-forward': 0.3, 'chin/chin-prominent-incr': 0.45,
              'chin/chin-height-incr': 0.3, 'cheek/l-cheek-bones-incr': 0.5, 'cheek/r-cheek-bones-incr': 0.5,
              'cheek/l-cheek-volume-decr': 0.6, 'cheek/r-cheek-volume-decr': 0.6,
              'forehead/forehead-scale-vert-incr': 0.45, 'mouth/mouth-upperlip-volume-decr': 0.5,
              'mouth/mouth-lowerlip-volume-decr': 0.35, 'eyebrows/eyebrows-trans-down': 0.35,
              'eyebrows/eyebrows-angle-down': 0.2, 'neck/neck-scale-vert-incr': 0.3},
        hair=['short02'], hair_color='#0d0b0a', eyebrows='eyebrow012', slick=True, eyes='grey',
        clothes=['toigo_male_suit_3', 'shoes06'], suit='#121212', shoes='#0b0a0a',
        coat='frock', coat_color='#141414', hat='tophat', chain=True,
    ),
    # Stocky army doctor in a light tweed suit, brown bowler, moustache.
    'watson': dict(
        height=1.76,
        macro=dict(age=0.6, muscle=0.55, weight=0.62, height=0.5, proportions=0.6),
        face={'head/head-round': 0.4, 'head/head-scale-horiz-incr': 0.15, 'nose/nose-scale-horiz-incr': 0.2,
              'nose/nose-volume-incr': 0.2, 'chin/chin-width-incr': 0.3, 'cheek/l-cheek-volume-incr': 0.3,
              'cheek/r-cheek-volume-incr': 0.3, 'eyebrows/eyebrows-trans-down': 0.1, 'neck/neck-scale-horiz-incr': 0.3},
        hair=['short04'], hair_color='#5a3f28', eyebrows='eyebrow010', eyes='brownlight',
        clothes=['toigo_male_suit_3', 'shoes06', 'grinsegold_moustache', 'culturalibre_cl_bowler_hat'],
        suit='#7a6a52', shirt='#e8e2d4', split=0.5, shoes='#2a1c12', moustache='#5a3f28', bowler='#3b2a1c',
    ),
    # Big, heavy police sergeant: grey overcoat, black bowler, heavy moustache.
    'polhaus': dict(
        height=1.86,
        macro=dict(age=0.68, muscle=0.62, weight=0.78, height=0.62, proportions=0.5),
        face={'head/head-square': 0.6, 'chin/chin-width-incr': 0.5, 'chin/chin-prominent-incr': 0.2,
              'nose/nose-volume-incr': 0.4, 'nose/nose-scale-horiz-incr': 0.3, 'eyebrows/eyebrows-trans-down': 0.3,
              'neck/neck-scale-horiz-incr': 0.5, 'cheek/l-cheek-volume-incr': 0.4, 'cheek/r-cheek-volume-incr': 0.4},
        hair=['short01'], hair_color='#2e2219', eyebrows='eyebrow001', eyes='brown',
        clothes=['toigo_male_suit_3', 'shoes06', 'grinsegold_moustache', 'culturalibre_cl_bowler_hat'],
        suit='#2a2a2c', shoes='#0e0c0b', moustache='#2e2219', bowler='#141414',
        coat='overcoat', coat_color='#3a3c40',
    ),
    # Young beat constable: navy tunic, brass buttons, belt, helmet.
    'kelly': dict(
        height=1.8,
        macro=dict(age=0.42, muscle=0.55, weight=0.42, height=0.58, proportions=0.6),
        face={'head/head-oval': 0.3, 'nose/nose-point-up': 0.2, 'nose/nose-scale-horiz-decr': 0.1,
              'chin/chin-height-decr': 0.1, 'cheek/l-cheek-volume-incr': 0.2, 'cheek/r-cheek-volume-incr': 0.2},
        hair=['short03'], hair_color='#7a3f1f', eyebrows='eyebrow006', eyes='lightblue', slick=True,
        clothes=['toigo_male_suit_3', 'shoes06'], suit='#1a2238', shirt='#1d263e', shoes='#0b0a0a',
        tunic=True, hat='helmet',
    ),
    # The victim: overcoat buttoned to the collar (a clue), hat lying apart in the alley.
    'archer': dict(
        height=1.8,
        macro=dict(age=0.6, muscle=0.6, weight=0.6, height=0.58, proportions=0.55),
        face={'head/head-square': 0.4, 'chin/chin-prominent-incr': 0.3, 'nose/nose-scale-vert-decr': 0.2,
              'mouth/mouth-scale-horiz-incr': 0.2},
        hair=['short02'], hair_color='#4a3324', eyebrows='eyebrow003', eyes='brown',
        clothes=['toigo_male_suit_3', 'shoes06', 'grinsegold_moustache'],
        suit='#2b2925', shoes='#120f0d', moustache='#4a3324',
        coat='buttoned', coat_color='#3d3a33', hem=0.12,
    ),
}


def tidy(name):
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.data.materials:
            for m in o.data.materials:
                if m and not m.name.startswith(name.capitalize()):
                    m.name = f'{name.capitalize()}_{m.name}'


def build(name, c):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    random.seed(1)
    body, rig, parts = make_body(c)
    rig.name = f'{name.capitalize()}_rig'
    meshes = [o for o in rig.children if o.type == 'MESH']
    rerest_arms_down(rig, meshes)

    suit = parts.get('toigo_male_suit_3')
    if suit:
        # recolour the suit for 1895: the atlas holds jacket, shirt and tie; dark goes to wool, light to linen
        split_tint(suit, c['suit'], c.get('shirt', '#e8e2d4'), c.get('split', 0.42))
    for h in c.get('hair', []):
        if c.get('slick'): slick_hair(parts[h], body)
    eye_colour(parts['low-poly'], c.get('eyes', 'grey'))
    for p in parts.values():
        if p.name.endswith(tuple(h for h in c.get('hair', []))): tint(p, c['hair_color'], keep_texture=0.6, rough=0.55)
        if 'shoes' in p.name: tint(p, c['shoes'], keep_texture=0.3, rough=0.35)
        if 'moustache' in p.name: tint(p, c.get('moustache', c['hair_color']), keep_texture=0.7, rough=0.6)
        if 'bowler' in p.name: tint(p, c.get('bowler', '#141414'), keep_texture=0.3, rough=0.5)

    sources = [body] + [p for p in parts.values() if 'suit' in p.name]
    if c.get('coat') == 'inverness':
        tweed = fabric(f'{name}_tweed', c['tweed'], 'tweed', scale=5)
        z_neck = bone_head(rig, 'neck_01').z + 0.01
        z_knee = bone_head(rig, 'calf_l').z
        coat = long_coat('Coat', rig, sources, tweed, z_neck - 0.02, z_knee - 0.12, include_arms=True, gap=0.0)
        transfer_weights(coat, body, rig, skirt_weights(rig, bone_head(rig, 'thigh_l').z + 0.05, z_knee - 0.12))
        cp = cape('Cape', rig, sources + [coat], tweed, z_neck - 0.015, bone_head(rig, 'lowerarm_l').z - 0.06)
        transfer_weights(cp, body, rig, lambda co, w: {
            'spine_03': 0.7, 'clavicle_l': 0.15 * (co.x > 0) + 0.05, 'clavicle_r': 0.15 * (co.x < 0) + 0.05})
        cols = [front_of(coat, 0.0, z) for z in (z_neck - 0.08, z_neck - 0.2, z_neck - 0.32)]
        buttons(rig, plain(f'{name}_horn', '#14100c', 0.4), [0.0] * 3, [y - 0.004 for y in cols],
                [z_neck - 0.08, z_neck - 0.2, z_neck - 0.32])
    if c.get('coat') == 'frock':
        # knee-length black frock coat worn open: a V over the waistcoat, cut away below the waist
        wool = fabric(f'{name}_wool', c['coat_color'], 'wool', rough=0.85, scale=8)
        z_neck = bone_head(rig, 'neck_01').z - 0.03
        z_waist = bone_head(rig, 'spine_02').z
        z_knee = bone_head(rig, 'calf_l').z
        def opening(z):  # radians open at the front: a V to the waist button, then cut away toward the hem
            if z > z_waist: return 0.16 + 1.1 * ((z - z_waist) / (z_neck - z_waist)) ** 1.3
            return 0.16 + 0.55 * ((z_waist - z) / (z_waist - z_knee)) ** 1.5
        coat = long_coat('Coat', rig, sources, wool, z_neck, z_knee - 0.04, offset=0.01, flare=0.03, collar=False,
                         gap=opening)
        transfer_weights(coat, body, rig, skirt_weights(rig, bone_head(rig, 'thigh_l').z + 0.05, z_knee))
        if c.get('chain'):
            bvh = world_mesh_bvh([o for o in sources if 'suit' in o.name] or [body])
            def surf(x, z):
                loc, *_ = bvh.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)), 2)
                return loc.y if loc else -0.12
            watch_chain(rig, surf, plain(f'{name}_gold', '#d4a94a', 0.3, 1.0), z_waist + 0.02)
    if c.get('coat') in ('overcoat', 'buttoned'):
        # a knee-length overcoat with a turned-down collar; Archer's is buttoned to the throat
        wool = fabric(f'{name}_wool', c['coat_color'], 'wool', rough=0.95, scale=8)
        z_neck = bone_head(rig, 'neck_01').z - 0.025
        z_waist = bone_head(rig, 'spine_02').z
        z_knee = bone_head(rig, 'calf_l').z
        done_up = c['coat'] == 'buttoned'
        def opening(z):
            if z > z_waist: return 0.03 if done_up else 0.1 + 0.7 * ((z - z_waist) / (z_neck - z_waist)) ** 1.5
            return 0.03 + 0.25 * ((z_waist - z) / (z_waist - z_knee)) ** 1.5
        z_hem = z_knee + c.get('hem', -0.1)
        coat = long_coat('Coat', rig, sources, wool, z_neck, z_hem, offset=0.016, flare=0.04, collar=done_up,
                         gap=opening)
        transfer_weights(coat, body, rig, skirt_weights(rig, bone_head(rig, 'thigh_l').z + 0.05, z_knee))
        zs = [z_neck - 0.06 - i * 0.1 for i in range(5 if done_up else 3)]
        if not done_up: zs = [z_waist + 0.02 - i * 0.1 for i in range(3)]
        cols = [front_of(coat, 0.035, z) for z in zs]
        buttons(rig, plain(f'{name}_horn', '#15110d', 0.4), [0.035] * len(zs), [y - 0.004 for y in cols], zs)
    if c.get('tunic'):
        # police tunic: brass buttons down the front and a black belt
        suitm = [o for o in sources if 'suit' in o.name][0]
        z_waist = bone_head(rig, 'spine_01').z + 0.02
        zs = [bone_head(rig, 'neck_01').z - 0.07 - i * 0.075 for i in range(6)]
        brass = plain(f'{name}_brass', '#c9a04a', 0.3, 1.0)
        buttons(rig, brass, [0.0] * 6, [front_of(suitm, 0.0, z) - 0.004 for z in zs], zs)
        centre = (0.0, bone_head(rig, 'spine_01').y)
        bvh = world_mesh_bvh([suitm], ARM_GROUPS)
        ring = [x + 0.006 for x in smooth_ring(envelope(bvh, z_waist, centre, 48), 2)]
        belt = garment('Belt', plain(f'{name}_belt', '#0d0b09', 0.4), [(z_waist + 0.025, ring), (z_waist - 0.025, ring)],
                       centre, seg=48, thickness=0.004)
        bind(belt, rig, lambda co: {'spine_01': 1.0})
        buckle = lathe_obj('Buckle', brass, [(0.022, 0), (0.022, 0.004)], (0, 0), seg=4)
        for v in buckle.data.vertices:
            v.co = Matrix.Rotation(math.pi / 2, 3, 'X') @ v.co + Vector((0, centre[1] - ring[0] - 0.006, z_waist))
        bind(buckle, rig, lambda co: {'spine_01': 1.0})
    if c.get('hat') == 'helmet':
        police_helmet(rig, body, plain(f'{name}_felt', '#161d30', 0.8), plain(f'{name}_badge', '#c9a04a', 0.3, 1.0))
    if c.get('hat') == 'tophat':
        top_hat(rig, body, plain(f'{name}_silk', '#0a0a0a', 0.3))
    if c.get('hat') == 'deerstalker':
        deerstalker(rig, body, fabric(f'{name}_cap', c.get('cap', c['tweed']), 'tweed', scale=3))

    # scale to the character's height (top of the head; the game expects metres)
    h, top = head_frame(rig, body)
    s = c['height'] / top
    rig.scale = (s, s, s)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for o in rig.children:
        o.select_set(True)
    make_clips(rig)

    # keep phones happy: small textures, JPEG wherever there is no transparency, Draco geometry
    body_mat = body.data.materials[0]
    p = principled(body_mat)
    for l in list(p.inputs['Alpha'].links): body_mat.node_tree.links.remove(l)
    for img in bpy.data.images:
        n = img.name.lower()
        cap = 2048 if 'skinned' in n or 'skin' in n else 1024 if 'suit' in n else 512
        if img.size[0] > cap: img.scale(cap, int(cap * img.size[1] / img.size[0]))
    tidy(name)
    os.makedirs(os.path.join(ROOT, 'art', 'humans'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'art', 'humans', f'{name}.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for o in rig.children: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', f'{name}.glb'), export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True, export_animations=True,
                              export_animation_mode='NLA_TRACKS', export_image_format='JPEG',
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                              export_jpeg_quality=85, export_cameras=False, export_lights=False)
    return rig, body


def render(rig, body, out, name):
    scene = bpy.context.scene
    def light(n, loc, e):
        ld = bpy.data.lights.new(n, 'AREA'); ld.energy, ld.size = e, 2
        lo = bpy.data.objects.new(n, ld); lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 1.2)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        scene.collection.objects.link(lo)
    light('Key', (2, -3, 3.5), 320); light('Fill', (-3, -2, 2), 90); light('Rim', (0, 3, 3), 280)
    scene.world = bpy.data.worlds.new('W'); scene.world.color = (0.05, 0.05, 0.06)
    scene.render.engine = 'BLENDER_EEVEE'
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scene.collection.objects.link(cam)
    scene.camera = cam
    h = bone_head(rig, 'head')
    for t in rig.animation_data.nla_tracks: t.mute = True
    scene.frame_set(0)
    shots = [('full', (1.4, -4.6, 1.15), (0, 0, 0.95), 45, (900, 1200)),
             ('face', (0.32, -0.95, h.z + 0.08), (0, h.y, h.z + 0.07), 85, (900, 900)),
             ('back', (-1.6, 4.0, 1.3), (0, 0, 0.95), 45, (900, 1200))]
    for tag, loc, look, lens, res in shots:
        cam.location = loc; cam.data.lens = lens
        cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = os.path.join(out, f'{name}_{tag}.png')
        bpy.ops.render.render(write_still=True)
    # a mid-stride frame of the walk
    for t in rig.animation_data.nla_tracks: t.mute = t.name != 'Walk'
    scene.frame_set(8)
    cam.location = (2.6, -3.0, 1.1); cam.data.lens = 45
    cam.rotation_euler = (Vector((0, 0, 0.95)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.resolution_x, scene.render.resolution_y = (900, 1200)
    scene.render.filepath = os.path.join(out, f'{name}_walk.png')
    bpy.ops.render.render(write_still=True)


only = arg('--only')
out = arg('--render')
for name, c in CAST.items():
    if only and name not in only.split(','): continue
    rig, body = build(name, c)
    if out: render(rig, body, out, name)
