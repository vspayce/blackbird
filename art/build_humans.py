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
# makehuman_system_assets, suits01, skins01, skins02, eyebrows01, bodyparts05, gloves01 (CC0) and
# hats03, hair02, bodyparts06 (CC-BY, credited in CREDITS.md).
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


def bake_base_colour(obj, fn, rough=None, shaped=False):
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
        px[:, :3] = np.clip(fn(rgb, lum, h, w) if shaped else fn(rgb, lum[:, None]), 0, 1)
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


def box_blur(a, r, wrap=False):
    """Separable box blur of a 2D array, radius r texels (edges clamped, or wrapped for a tiling texture)."""
    import numpy as np
    for axis in (0, 1):
        pad = [(0, 0), (0, 0)]; pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(a, pad, mode='wrap' if wrap else 'edge'), axis=axis)
        a = (np.take(c, range(2 * r + 1, c.shape[axis]), axis=axis) - np.take(c, range(0, c.shape[axis] - 2 * r - 1), axis=axis)) / (2 * r + 1)
    return a


def weave(h, w, kind='wool', seed=3):
    """Cloth shading, about 1.0 on average: a fine twill with heathered yarn and a soft mottle, no stripes.
    tweed adds a herringbone and coloured flecks."""
    import numpy as np
    rnd = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    yarn = rnd.random((h, w)).astype(np.float32)
    mottle = box_blur(rnd.random((h, w)).astype(np.float32), 18, wrap=True)
    mottle = (mottle - mottle.mean()) / (mottle.std() + 1e-6)
    if kind == 'tweed':
        band = (x // 8) % 2
        diag = (((x + np.where(band, y, -y)) // 3) % 2).astype(np.float32)
        k = 0.84 + 0.12 * diag + 0.16 * (yarn - 0.5) + 0.05 * mottle + np.where(yarn > 0.985, 0.25, 0)
    else:
        twill = (((x + y) // 2) % 2).astype(np.float32)
        k = 0.95 + 0.05 * twill + 0.09 * (yarn - 0.5) + 0.035 * mottle
    return k / k.mean()


def reweave(obj, cloth_hex, light_hex=None, tie_hex=None, threshold=0.5, rough=0.85, kind='wool', cloth_rects=(),
            tie_rects=()):
    """Re-texture a MakeHuman suit atlas: the cloth panels (dark, unsaturated texels) become plain wool of one colour,
    keeping only the broad shading of the original (no pinstripe); light panels become linen (the shirt) and the
    patterned silk tie becomes tie_hex. cloth_rects: UV boxes (u0, v0, u1, v1) forced to cloth (a pocket square).
    Replaces split_tint for the suits."""
    import numpy as np
    cloth, light = np.array(hex01(cloth_hex), np.float32), np.array(hex01(light_hex or '#e8e2d4'), np.float32)
    def fn(rgb, lum, h, w):
        img = rgb.reshape(h, w, 3)
        l = lum.reshape(h, w)
        sat = img.max(2) - img.min(2)
        t = np.clip((l - (threshold - 0.06)) / 0.12, 0, 1); t = t * t * (3 - 2 * t)  # 1 = shirt
        for u0, v0, u1, v1 in cloth_rects: t[int(v0 * h):int(v1 * h), int(u0 * w):int(u1 * w)] = 0
        tie = np.zeros((h, w), bool)
        for u0, v0, u1, v1 in tie_rects:  # the patterned silk tie: red ground and white spots, on blue denim
            box = img[int(v0 * h):int(v1 * h), int(u0 * w):int(u1 * w)]
            tie[int(v0 * h):int(v1 * h), int(u0 * w):int(u1 * w)] = (box[..., 0] > box[..., 2] - 0.02) | (box.mean(2) > 0.55)
        tie = box_blur(tie.astype(np.float32), 3) > 0.3
        t = np.where(tie, 0, t)
        dark = (1 - t)
        # the broad folds and seams only: a masked blur of the light level over the dark panels
        m = dark + 1e-3
        broad = box_blur(l * m, 6) / box_blur(m, 6)
        shade = np.clip(broad / max(0.05, float((broad * dark).sum() / dark.sum())), 0.7, 1.25)
        wv = weave(h, w, kind)
        out = cloth * (wv * (0.8 + 0.2 * shade))[..., None] * dark[..., None] + \
            light * (0.88 + 0.12 * l / max(0.2, float(l.mean())))[..., None] * t[..., None]
        if tie_hex:
            tc = np.array(hex01(tie_hex), np.float32)
            out = np.where(tie[..., None], tc * (0.9 + 0.1 * wv)[..., None], out)
        return out.reshape(-1, 3)
    bake_base_colour(obj, fn, rough, shaped=True)
    drop_maps(obj)


def drop_maps(obj):
    """Unlink normal, bump and specular maps (the suits' carry the pinstripe and the eyebrows' a bump map that the
    glTF exporter turns into a garbage normal map)."""
    for m in obj.data.materials:
        nt, p = m.node_tree, principled(m)
        for inp in ('Normal', 'Specular IOR Level', 'Specular Tint', 'Coat Weight', 'Coat Normal'):
            if inp in p.inputs:
                for l in list(p.inputs[inp].links): nt.links.remove(l)
        for n in [n for n in nt.nodes if n.type in ('NORMAL_MAP', 'BUMP')]: nt.nodes.remove(n)
        if 'Coat Weight' in p.inputs: p.inputs['Coat Weight'].default_value = 0.0


def finish(obj, rough, cutout=False, sheen=0.0, sheen_tint=(1, 1, 1), spec=0.5):
    """A clean glTF-friendly material: the base-colour texture straight into a Principled BSDF, a set roughness, no
    clearcoat or stray maps. cutout: alpha-tested (hair, brows, lashes) through a Round node, which the glTF exporter
    writes as alphaMode MASK. sheen: the soft rim of wool and skin (KHR_materials_sheen)."""
    for m in obj.data.materials:
        nt = m.node_tree
        tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.name.lower().startswith('diffuse')), None) or \
            next((n for n in nt.nodes if n.type == 'TEX_IMAGE'), None)
        img = tex.image if tex else None
        old = principled(m)
        colour = tuple(old.inputs['Base Color'].default_value)
        for n in list(nt.nodes):
            if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        p = nt.nodes.new('ShaderNodeBsdfPrincipled')
        nt.links.new(p.outputs['BSDF'], out.inputs['Surface'])
        p.inputs['Roughness'].default_value = rough
        p.inputs['Specular IOR Level'].default_value = spec
        if sheen:
            p.inputs['Sheen Weight'].default_value = sheen
            p.inputs['Sheen Tint'].default_value = (*sheen_tint, 1)
            p.inputs['Sheen Roughness'].default_value = 0.6
        if img:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; t.name = 'diffuseTexture'
            nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
            if cutout:
                r = nt.nodes.new('ShaderNodeMath'); r.operation = 'ROUND'
                nt.links.new(t.outputs['Alpha'], r.inputs[0]); nt.links.new(r.outputs[0], p.inputs['Alpha'])
        else:
            p.inputs['Base Color'].default_value = colour
        m.blend_method = 'CLIP' if cutout else 'OPAQUE'
        m.use_backface_culling = False


def slick_hair(hair, body, keep=0.3, gap=0.004):
    """Pull hair in toward the scalp, keeping a little of its volume: hair worn short and oiled back."""
    bvh = world_mesh_bvh([body])
    for v in hair.data.vertices:
        loc, nrm, i, d = bvh.find_nearest(v.co)
        if loc is None: continue
        out = (v.co - loc).length
        v.co = loc + nrm * max(gap, out * keep)


def gigot_sleeves(ob, rig, amount):
    """The 1895 leg-o'-mutton sleeve: puff the upper sleeve out from the arm, most at the shoulder, tapering to
    fitted at the elbow."""
    names = {g.index: g.name for g in ob.vertex_groups}
    for v in ob.data.vertices:
        w = {names[g.group]: g.weight for g in v.groups}
        for side in 'lr':
            if w.get(f'upperarm_{side}', 0) + w.get(f'clavicle_{side}', 0) * 0.5 < 0.3: continue
            a, b = bone_head(rig, f'upperarm_{side}'), bone_tail(rig, f'upperarm_{side}')
            ax = (b - a).normalized()
            t = max(0.0, min(1.0, (v.co - a).dot(ax) / (b - a).length))
            foot = a + ax * (t * (b - a).length)
            out = v.co - foot
            if out.length < 1e-4: continue
            out.normalize()
            k = amount * math.sin(math.pi * min(1, 0.15 + t * 1.1)) ** 0.8 * (1 - t) ** 0.6
            if out.z > 0.3: k *= 1.2  # fuller over the top of the shoulder
            v.co += out * k


def hair_under_hat(hair, body, hat, gap=0.003):
    """Press the hair flat to the scalp wherever the hat covers it, so none of it pokes through the crown."""
    zs = [(hat.matrix_world @ v.co).z for v in hat.data.vertices]
    z_in = sorted(zs)[len(zs) // 20] - 0.004  # the band's lower edge (ignoring the curled brim)
    bvh = world_mesh_bvh([body])
    for v in hair.data.vertices:
        if v.co.z < z_in: continue
        loc, nrm, i, d = bvh.find_nearest(v.co)
        if loc is not None: v.co = loc + nrm * gap


def puff_hair(hair, body, amount):
    """Dress hair up off the scalp, most over the crown and front: a little of the 1890s pompadour."""
    bvh = world_mesh_bvh([body])
    top = max(v.co.z for v in hair.data.vertices)
    for v in hair.data.vertices:
        loc, nrm, i, d = bvh.find_nearest(v.co)
        if loc is None: continue
        k = max(0.0, 1 - (top - v.co.z) / 0.14) * (1.0 if v.co.y < loc.y + 0.02 else 0.7)
        v.co += nrm * amount * k


def eye_colour(eyes, colour, iris=None):
    """Set the eye texture; iris (hex) recolours the iris, keeping its fibres (MakeHuman's 'brown' is nearly red)."""
    import numpy as np
    path = os.path.join(USR, 'eyes', 'materials', f'{colour}_eye.png')
    img = bpy.data.images.load(path)
    if iris:
        w, h = img.size
        px = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(px); px = px.reshape(-1, 4)
        rgb = px[:, :3]
        sat = rgb.max(1) - rgb.min(1)
        k = np.clip((sat - 0.12) / 0.1, 0, 1)[:, None]  # the iris; the white and the veins are barely saturated
        lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
        ref = float(lum[k[:, 0] > 0.5].mean()) if (k > 0.5).any() else 0.4
        px[:, :3] = rgb * (1 - k) + np.array(hex01(iris), np.float32) * (lum / ref)[:, None] * k
        out = bpy.data.images.new(f'eye_{iris.strip("#")}', w, h, alpha=True)
        out.pixels.foreach_set(px.ravel()); out.pack()
        img = out
    for m in eyes.data.materials:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE': n.image = img


_tex = {}
def cloth_texture(kind, hex, size=512):
    """A small tiling cloth texture (tweed herringbone or plain wool) as an image, so it survives glTF export."""
    import numpy as np
    key = (kind, hex)
    if key in _tex: return _tex[key]
    img = bpy.data.images.new(f'{kind}_{hex.strip("#")}', size, size)
    k = weave(size, size, kind)  # tiles seamlessly
    base = np.array(hex01(hex), np.float32)
    px = np.ones((size, size, 4), np.float32)
    px[..., :3] = np.clip(base * k[..., None], 0, 1)
    img.pixels.foreach_set(px.ravel())
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
    macro.update({'gender': 1.0, 'cupsize': 0.5, 'firmness': 0.5, **c['macro']})
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


def rerest_arms_down(rig, meshes, body, clearance=0.05):
    """MakeHuman rests in an A-pose; re-rest the character standing naturally: feet under the hips and arms
    hanging straight at the sides, the hands just clear of the hips (and of a coat over them)."""
    bone = lambda b: rig.data.bones[b]
    length = lambda b: (bone(b).tail_local - bone(b).head_local).length
    bvh = world_mesh_bvh([body], ARM_GROUPS)
    for s, side in ((1, 'l'), (-1, 'r')):
        aim(rig, f'thigh_{side}', (s * 0.035, 0.0, -1))
        sh = bone(f'upperarm_{side}').head_local
        reach = length(f'upperarm_{side}') + length(f'lowerarm_{side}') + 0.5 * length(f'hand_{side}')
        z_hand = sh.z - reach * 0.97
        ring = envelope(bvh, z_hand, (0.0, bone('pelvis').head_local.y), 48) or [0.17] * 48
        hip = max(ring[12], ring[36])  # the sides, +X and -X
        x = hip + clearance
        dx = s * x - sh.x
        d = Vector((dx, -0.02, -math.sqrt(max(0.01, reach ** 2 - dx ** 2)))).normalized()
        aim(rig, f'upperarm_{side}', d)
        bpy.context.view_layer.update()
        aim_posed(rig, f'lowerarm_{side}', d + Vector((0, -0.08, 0)))  # the elbow just unlocked
        aim_posed(rig, f'hand_{side}', d + Vector((0, -0.05, 0)))
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

def world_mesh_bvh(objects, drop_groups=(), unmasked=False):
    """A BVH of the evaluated meshes in world space, optionally without faces weighted to some bones (the arms).
    unmasked: include the skin the clothes' delete groups hide."""
    hidden = [md for ob in objects for md in ob.modifiers if unmasked and md.type == 'MASK' and md.show_viewport]
    for md in hidden: md.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    verts, polys = [], []
    for ob in objects:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        idx = {g.name: g.index for g in ob.vertex_groups}
        drop = {idx[g] for g in drop_groups if g in idx}
        bad = set()
        if drop:  # (from the evaluated mesh: masks renumber the vertices)
            for v in me.vertices:
                if sum(g.weight for g in v.groups if g.group in drop) > 0.4: bad.add(v.index)
        off = len(verts)
        verts += [ob.matrix_world @ v.co for v in me.vertices]
        for p in me.polygons:
            if bad and any(i in bad for i in p.vertices): continue
            polys.append([off + i for i in p.vertices])
        ev.to_mesh_clear()
    for md in hidden: md.show_viewport = True
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
        # (take the indices first: removing a group invalidates the element references in v.groups)
        for gi in [g.group for g in v.groups]: ob.vertex_groups[gi].remove([v.index])
        tot = sum(x for x in w2.values() if x > 0) or 1
        for b, x in w2.items():
            if x > 0:
                (ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b)).add([v.index], x / tot, 'REPLACE')
    ob.parent = rig
    md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = rig


def coat_sleeves(name, suit, mat, offset=0.009):
    """Sleeves for a coat: the suit jacket's sleeves copied, pushed out over them and given the coat's cloth, with
    the suit's skin weights. The jacket sleeves underneath are deleted (nobody sees them)."""
    arm = set(g.index for g in suit.vertex_groups if g.name.startswith(('upperarm', 'lowerarm', 'hand')))
    on = [sum(g.weight for g in v.groups if g.group in arm) > 0.6 for v in suit.data.vertices]
    me = suit.data.copy(); me.name = name
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.parent = suit.parent
    for g in suit.vertex_groups: ob.vertex_groups.new(name=g.name)
    for md in suit.modifiers:
        if md.type == 'ARMATURE': m = ob.modifiers.new('Armature', 'ARMATURE'); m.object = md.object
    for bmo, keep_sleeves in ((ob, True), (suit, False)):
        bm = bmesh.new(); bm.from_mesh(bmo.data); bm.faces.ensure_lookup_table()
        sleeve = lambda f: all(on[v.index] for v in f.verts)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if sleeve(f) != keep_sleeves], context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        if keep_sleeves:
            bm.normal_update()
            for v in bm.verts: v.co += v.normal * offset
        bm.to_mesh(bmo.data); bm.free()
    me.materials.clear(); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return ob


def skirt_weights(rig, z_top, z_hem, follow=0.5):
    """Below the hips a coat skirt hangs from the pelvis. Toward the hem the front panels follow the thigh on
    their side, while the back hangs straight, the way a long coat swings."""
    y0 = bone_head(rig, 'pelvis').y
    def f(co, w):
        if co.z > z_top: return None
        front = 1 / (1 + math.exp((co.y - y0) / 0.035))  # 1 at the front, 0 at the back
        k = min(1, (z_top - co.z) / max(0.01, z_top - z_hem)) ** 1.3 * (0.02 + follow * front)
        side = 1 / (1 + math.exp(-co.x / 0.09))  # 0 = right, 1 = left
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


def head_fit(rig, body, z, gap=0.012, r0=0.104):
    """Fit a hat's crown to the head at height z: (centre, sx, sy) for lathe_obj, so a crown of radius r0 clears the
    skull (and hair pressed flat) by gap all round."""
    h = bone_head(rig, 'head')
    bvh = world_mesh_bvh([body])
    ring = envelope(bvh, z, (0.0, h.y), 32, reach=0.3)
    if not ring: return (0.0, h.y + 0.005), 0.93, 1.12
    front, back, side = ring[0], ring[16], max(ring[8], ring[24])
    cy = h.y + (back - front) / 2
    return (0.0, cy), (side + gap) / r0, ((front + back) / 2 + gap) / r0


def brow_line(top):
    """Height of the top of the eyebrows (hats sit just above them)."""
    zs = [(o.matrix_world @ v.co).z for o in bpy.data.objects if o.type == 'MESH' and 'eyebrow' in o.name.lower()
          for v in o.data.vertices]
    return max(zs) if zs else top - 0.1


def deerstalker(rig, body, mat):
    h, top = head_frame(rig, body)
    c = (0.0, h.y + 0.005)
    zb = brow_line(top) + 0.03  # the band sits a little above the brows
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
    zb = brow_line(top) + 0.035
    c, sx, sy = head_fit(rig, body, zb + 0.012)
    ob = lathe_obj('TopHat', mat, [(0.158, zb - 0.002), (0.145, zb - 0.004), (0.108, zb), (0.104, zb + 0.004),
                                   (0.1, zb + 0.07), (0.104, zb + 0.15), (0.106, zb + 0.165), (0.104, zb + 0.168),
                                   (0.002, zb + 0.17)], c, sx=sx, sy=sy, tilt=-0.06)
    for v in ob.data.vertices:  # curl the brim up at the sides
        d = math.hypot(v.co.x, v.co.y - c[1])
        if d > 0.12 and v.co.z < zb + 0.01: v.co.z += 0.9 * (abs(v.co.x) / 0.158) ** 2 * (d - 0.11)
    band = lathe_obj('HatBand', plain('band', '#050505', 0.5), [(0.1055, zb + 0.004), (0.105, zb + 0.032)], c,
                     sx=sx, sy=sy, tilt=-0.06)
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


def cane(rig, side, shaft, knob, ferrule):
    """A gentleman's walking cane held in the fist of one hand, tip on the ground a little ahead."""
    hand_tail = bone_tail(rig, f'hand_{side}')
    knuckle = bone_head(rig, f'middle_01_{side}')
    thumb = bone_head(rig, f'thumb_01_{side}')
    palm = (hand_tail + knuckle) / 2
    grip = Vector((palm.x, (palm.y + thumb.y) / 2 - 0.01, palm.z))  # inside the closed fingers
    top = grip + Vector((0, 0, thumb.z - grip.z + 0.03))
    tip = Vector((grip.x + (0.02 if side == 'l' else -0.02), grip.y - 0.16, 0.015))
    axis = (top - tip).normalized()
    me = bpy.data.meshes.new('Cane')
    parts = []
    def piece(name, mat, base, height, r0, r1, seg=10):
        bm = bmesh.new()
        rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r0, radius2=r1, depth=height,
                              matrix=Matrix.Translation(base + axis * height / 2) @ rot)
        m = bpy.data.meshes.new(name); bm.to_mesh(m); bm.free()
        o = bpy.data.objects.new(name, m); bpy.context.scene.collection.objects.link(o)
        m.materials.append(mat)
        for f in m.polygons: f.use_smooth = True
        parts.append(o)
    length = (top - tip).length
    piece('CaneShaft', shaft, tip + axis * 0.04, length - 0.06, 0.0095, 0.012)
    piece('CaneFerrule', ferrule, tip, 0.045, 0.008, 0.0095)
    piece('CaneCollar', knob, top - axis * 0.035, 0.015, 0.0135, 0.0135)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.019,
                              matrix=Matrix.Translation(top) @ Matrix.Diagonal((1, 1, 0.85, 1)))
    m = bpy.data.meshes.new('CaneKnob'); bm.to_mesh(m); bm.free()
    o = bpy.data.objects.new('CaneKnob', m); bpy.context.scene.collection.objects.link(o)
    m.materials.append(knob)
    for f in m.polygons: f.use_smooth = True
    parts.append(o)
    for o in parts:
        bind(o, rig, lambda co: {f'hand_{side}': 1.0})
    return parts


def police_helmet(rig, body, mat, brass):
    h, top = head_frame(rig, body)
    zb = brow_line(top) + 0.03
    c, sx, sy = head_fit(rig, body, zb + 0.012, r0=0.112)
    ob = lathe_obj('Helmet', mat, [(0.128, zb - 0.006), (0.112, zb), (0.11, zb + 0.06), (0.1, zb + 0.13),
                                   (0.075, zb + 0.18), (0.04, zb + 0.2), (0.002, zb + 0.205)], c, sx=sx, sy=sy,
                   tilt=-0.08)
    badge = lathe_obj('Badge', brass, [(0.026, 0), (0.026, 0.004), (0.002, 0.006)], (0, 0), seg=16)
    for v in badge.data.vertices:
        v.co = Matrix.Rotation(math.pi / 2, 3, 'X') @ v.co + Vector((0, c[1] - 0.11 * sy - 0.006, zb + 0.08))
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


def buttonhole_flower(rig, front, mat, leaf, x, z, name='Gardenia'):
    """A gardenia in the left lapel's buttonhole: a cup of creamy petals in two rings and a dark leaf behind."""
    y = front(x, z) - 0.006
    bm = bmesh.new()
    for ring, (n, r, tilt, size) in enumerate(((6, 0.016, 0.9, 0.017), (5, 0.007, 0.35, 0.012))):
        for i in range(n):
            a = 2 * math.pi * (i + 0.5 * ring) / n
            M = Matrix.Translation((x + r * math.cos(a), y - 0.004 * ring - 0.002, z + r * math.sin(a))) @ \
                Matrix.Rotation(a - math.pi / 2, 4, 'Y') @ Matrix.Rotation(-tilt, 4, 'X') @ \
                Matrix.Diagonal((size * 0.75, size * 0.25, size, 1))
            bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=1, matrix=M)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    me.materials.append(mat)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=1,
                              matrix=Matrix.Translation((x - 0.012, y + 0.004, z - 0.016)) @ Matrix.Rotation(0.7, 4, 'Y') @
                              Matrix.Diagonal((0.012, 0.003, 0.026, 1)))
    lm = bpy.data.meshes.new(name + 'Leaf'); bm.to_mesh(lm); bm.free()
    lo = bpy.data.objects.new(name + 'Leaf', lm); bpy.context.scene.collection.objects.link(lo)
    lm.materials.append(leaf)
    for o in (ob, lo):
        for p in o.data.polygons: p.use_smooth = True
        bind(o, rig, lambda co: {'spine_03': 1.0})
    return ob


def front_of(ob, x, z):
    """y of the front surface of ob at (x, z), from a ray cast forward-to-back."""
    bvh = world_mesh_bvh([ob])
    loc, *_ = bvh.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)), 2)
    return loc.y if loc else None


# --- phone budget ------------------------------------------------------------------

def triangles(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh(); me.calc_loop_triangles(); n = len(me.loop_triangles)
    ob.evaluated_get(dg).to_mesh_clear()
    return n


def apply_masks(ob):
    """Delete what the Mask modifiers hide (MakeHuman's helper geometry and the skin under the clothes) for good."""
    masks = [md for md in ob.modifiers if md.type == 'MASK' and md.vertex_group in ob.vertex_groups]
    if not masks: return
    drop = set()
    for md in masks:
        gi = ob.vertex_groups[md.vertex_group].index
        for v in ob.data.vertices:
            inside = any(g.group == gi and g.weight > 0 for g in v.groups)
            if inside == md.invert_vertex_group: drop.add(v.index)
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in drop], context='VERTS')
    bm.to_mesh(ob.data); bm.free()
    for md in masks: ob.modifiers.remove(md)


def decimate(ob, ratio, keep=None):
    """Collapse-decimate a skinned mesh in place (weights and UVs are interpolated). keep(world co) -> True for
    vertices to leave alone (the face)."""
    if ratio >= 1: return
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    me = ob.data
    seam = set()  # vertices on a UV island's border: keep them, or the texture tears along the seams
    if me.uv_layers.active:
        uv, first = me.uv_layers.active.data, {}
        for l in me.loops:
            u = tuple(round(x, 4) for x in uv[l.index].uv)
            if first.setdefault(l.vertex_index, u) != u: seam.add(l.vertex_index)
    mw = ob.matrix_world
    for v in me.vertices: v.select = v.index not in seam and not (keep and keep(mw @ v.co))
    for p in me.polygons: p.select = all(me.vertices[i].select for i in p.vertices)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.decimate(ratio=ratio)
    bpy.ops.object.mode_set(mode='OBJECT')


def face_region(rig):
    """The front of the head (face, brows, eyes) and the ears' front: kept at full resolution."""
    h = bone_head(rig, 'head')
    def keep(co):
        return co.z > h.z - 0.05 and co.y < h.y + 0.015 and abs(co.x) < 0.075
    return keep


BUDGET = [  # (name contains, ratio): what to keep of each part's triangles
    ('toigo_male_suit', 0.15), ('female_suit', 0.15), ('shoes', 0.2), ('gloves', 0.2), ('bowler', 0.65),
    ('cap', 0.3), ('CoatSleeves', 0.2), ('Coat', 0.35), ('Skirt', 0.4), ('Cape', 0.4), ('TopHat', 0.6), ('Helmet', 0.6),
]


def optimise(rig, body, parts, hair_ratio=0.55, suit_ratio=None):
    keep = face_region(rig)
    apply_masks(body)
    decimate(body, 0.3, keep)
    hair = set(parts.get('_hair', []))
    for ob in [o for o in rig.children if o.type == 'MESH' and o is not body]:
        r = 1.0
        if ob.name in hair: r = hair_ratio
        for k, v in BUDGET:  # the first match
            if k in ob.name: r = v; break
        if suit_ratio and 'suit' in ob.name: r = suit_ratio
        decimate(ob, r)


# --- clips ----------------------------------------------------------------------

def aim_posed(rig, bone, direction):
    """Turn a bone, as currently posed (parents included), to point along an armature-space direction."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones[bone]
    pb.rotation_mode = 'QUATERNION'
    cur = (pb.tail - pb.head).normalized()
    R = cur.rotation_difference(Vector(direction).normalized()).to_matrix()
    M = pb.matrix.to_3x3().normalized()
    pb.rotation_quaternion = (pb.rotation_quaternion.to_matrix() @ M.inverted() @ R @ M).to_quaternion()


def key_pose(rig, frame, rot, aims=None, act=None):
    """rot: {bone: (axis, angle)} in armature space; aims: {bone: direction} applied after, parents first.
    Unspecified bones go back to rest."""
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    for b, val in rot.items():
        if b == 'pelvis_move':  # (sideways, up) in metres
            rig.pose.bones['pelvis'].location = rig.data.bones['pelvis'].matrix_local.to_3x3().inverted() @ Vector((val[0], 0, val[1]))
            continue
        q = Quaternion()
        for axis, ang in (val if isinstance(val, list) else [val]):
            q = Quaternion(axis, ang) @ q
        pose_world(rig, b, q)
    for b, d in (aims or {}).items():
        aim_posed(rig, b, d(rig) if callable(d) else d)  # a callable reads the pose so far (IK)
    if act: rig.animation_data.action = act
    for pb in rig.pose.bones:
        pb.keyframe_insert('rotation_quaternion', frame=frame)
        pb.keyframe_insert('location', frame=frame)


def clip(rig, name, frames, poses, cyclic=True):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad = rig.animation_data_create()
    ad.use_nla = False  # the clips already made must not play while this one is posed and measured
    for f, rot, *aims in poses:
        ad.action = None  # nor this one's earlier keys
        key_pose(rig, f, rot, aims[0] if aims else None, act)
    act.frame_range = (0, frames)
    track = ad.nla_tracks.new(); track.name = name
    track.strips.new(name, 0, act)
    ad.action = None
    ad.use_nla = True
    return act


X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))


GAITS = {  # frames per cycle, ground each foot covers while planted (m), share of the cycle planted, foot lift,
    # arm swing (rad), elbow bend, hip sway (m), hip turn (rad), bounce (m)
    'gent': dict(n=32, L=0.8, duty=0.6, lift=0.07, arm=0.24, elbow=-0.1, sway=0.025, turn=0.07, bounce=0.014),
    'lady': dict(n=30, L=0.5, duty=0.64, lift=0.045, arm=0.06, elbow=-0.32, sway=0.03, turn=0.035, bounce=0.007),
    'heavy': dict(n=40, L=0.62, duty=0.66, lift=0.05, arm=0.12, elbow=-0.22, sway=0.045, turn=0.05, bounce=0.01),
}


def walk_clip(rig, gait, cane, hand):
    """Walk: two steps, legs placed by IK so the planted foot stays put on the ground while the body passes over it
    (no sliding): it moves back at exactly the walking speed, which is stored on the rig as walk_speed (exported
    in the glTF extras) for the game to match. The character faces -Y."""
    g = GAITS.get(gait, GAITS['gent'])
    n, L, duty = g['n'], g['L'], g['duty']
    T = 2 * math.pi
    bone = rig.data.bones
    smooth = lambda x: (lambda t: t * t * (3 - 2 * t))(max(0.0, min(1.0, x)))
    legs = {}
    for side in 'lr':
        H, K, A = bone[f'thigh_{side}'].head_local, bone[f'calf_{side}'].head_local, bone[f'foot_{side}'].head_local
        B = bone[f'ball_{side}'].head_local
        legs[side] = dict(L1=(K - H).length, L2=(A - K).length, A=A.copy(), flen=(B - A).length,
                          fdir=(B - A).normalized())
    def foot(side, t):
        """Ankle target (armature space) and the foot's pitch (+ = toe down) at cycle time t."""
        leg = legs[side]
        ph = (t + (0.5 if side == 'r' else 0.0)) % 1.0
        z0, x = leg['A'].z, leg['A'].x * 0.8
        heel_max = 0.045 if gait != 'lady' else 0.03
        if ph < duty:  # planted: from the front of the stride to the back, heel peeling up at the end
            u = ph / duty
            y = -L / 2 + L * u
            heel = heel_max * smooth((u - 0.65) / 0.35)
            pitch = math.asin(min(0.9, heel / leg['flen'])) - 0.15 * (1 - smooth(u / 0.12))
            z = z0 + heel
        else:  # swinging through: forward in an arc, toe up again for the heel to strike
            u = (ph - duty) / (1 - duty)
            y = L / 2 - L * smooth(u)
            heel = heel_max * (1 - smooth(u / 0.35))
            z = z0 + heel + g['lift'] * math.sin(math.pi * u) ** 1.2
            pitch = math.asin(min(0.9, heel / leg['flen'])) * (1 - smooth(u / 0.35)) - 0.15 * smooth((u - 0.55) / 0.45)
        return Vector((x, y, z)), pitch
    def knee_dir(side, t):
        def f(rig):
            leg = legs[side]
            Ht = rig.pose.bones[f'thigh_{side}'].head
            At, _ = foot(side, t)
            dv = At - Ht
            d = min(dv.length, leg['L1'] + leg['L2'] - 1e-4)
            u = dv.normalized()
            fwd = Vector((0, -1, 0))
            w = (fwd - u * fwd.dot(u)).normalized()
            a = math.acos(max(-1, min(1, (leg['L1'] ** 2 + d * d - leg['L2'] ** 2) / (2 * leg['L1'] * d))))
            return u * math.cos(a) + w * math.sin(a)
        return f
    def shin_dir(side, t):
        def f(rig):
            At, _ = foot(side, t)
            return At - rig.pose.bones[f'calf_{side}'].head
        return f
    def foot_dir(side, t):
        def f(rig):
            _, pitch = foot(side, t)
            return Matrix.Rotation(pitch, 3, 'X') @ legs[side]['fdir']
        return f
    arm_l = g['arm'] * (0.55 if cane == 'l' else 1)
    arm_r = g['arm'] * (0.55 if cane == 'r' else 1)
    poses = []
    for f in range(0, n + 1, 2):
        t = f / n
        sl, sr = math.cos(T * (t - 0.5)), math.cos(T * t)  # +1: that arm fully forward
        d = {
            **hand,
            'pelvis_move': (g['sway'] * math.sin(T * (t - 0.06)), g['bounce'] * math.cos(2 * T * (t - 0.31)) - 0.022),
            'pelvis': [(Z, -g['turn'] * math.cos(T * t)), (Y, -0.035 * math.sin(T * (t - 0.06)))],
            'spine_01': [(X, -0.025 if gait == 'gent' else 0.0), (Y, 0.03 * math.sin(T * (t - 0.06)))],
            'spine_03': [(Z, 1.25 * g['turn'] * math.cos(T * t)), (Y, 0.012 * math.sin(T * (t - 0.06)))],
            'head': [(Z, -0.3 * g['turn'] * math.cos(T * t))],
            'upperarm_l': (X, -arm_l * sl), 'upperarm_r': (X, -arm_r * sr),
            'lowerarm_l': (X, g['elbow'] - 0.35 * arm_l * max(0, sl)),
            'lowerarm_r': (X, g['elbow'] - 0.35 * arm_r * max(0, sr)),
        }
        if gait == 'lady':  # hands carried a little in front and out, clear of the skirt
            d['upperarm_l'] = [(X, -arm_l * sl - 0.14), (Y, -0.06)]
            d['upperarm_r'] = [(X, -arm_r * sr - 0.14), (Y, 0.06)]
        aims = {}
        for side in 'lr':
            aims[f'thigh_{side}'] = knee_dir(side, t)
            aims[f'calf_{side}'] = shin_dir(side, t)
            aims[f'foot_{side}'] = foot_dir(side, t)
        poses.append((f, d, aims))
    clip(rig, 'Walk', n, poses)
    rig['walk_speed'] = round(L / (duty * n / FPS), 3)
    print('WALK', rig.name, rig['walk_speed'], 'm/s')


def hands(rig, curl=0.32, grip=None):
    """Relaxed hands: fingers curled a little at each joint, more toward the little finger; the thumb in toward the
    palm. grip: a side ('l' or 'r') whose fingers close round something (a cane). Merged into every pose."""
    out = {}
    for side in 'lr':
        k_in = rig.data.bones[f'index_01_{side}'].head_local
        k_out = rig.data.bones[f'pinky_01_{side}'].head_local
        axis = (k_in - k_out).normalized()
        fwd = (rig.data.bones[f'middle_01_{side}'].tail_local - rig.data.bones[f'middle_01_{side}'].head_local)
        palm = axis.cross(fwd).normalized()  # which way the fingers fold
        if palm.dot(rig.data.bones[f'thumb_01_{side}'].head_local - rig.data.bones[f'middle_01_{side}'].head_local) < 0:
            axis = -axis
        c = 1.25 if grip == side else curl
        for i, f in enumerate(('index', 'middle', 'ring', 'pinky')):
            spread = 1 + 0.12 * i
            for j, k in ((1, 0.8), (2, 1.0), (3, 0.7)):
                out[f'{f}_0{j}_{side}'] = (axis, c * k * spread)
        out[f'thumb_02_{side}'] = (axis, 0.25 if grip != side else 0.6)
    return out


def make_clips(rig, gait='gent', cane=None):
    """gait: 'gent' (the default), 'lady' (a shorter, gliding step with the arms held in, for a long skirt) or
    'heavy' (the fat man's slow roll). cane: the hand holding one, which swings less and keeps its grip."""
    hand = hands(rig, grip=cane)
    T = 2 * math.pi
    def merge(d):
        return {**hand, **d}
    # Idle: breathing, and the weight shifting slowly from one leg to the other with the hips and shoulders
    # answering it; the head looks about now and then. 6 s.
    n = 180
    clip(rig, 'Idle', n, [(f, merge({
        'pelvis_move': (0.018 * math.sin(T * f / n), 0.0),
        'pelvis': (Y, -0.025 * math.sin(T * f / n)),
        'thigh_l': (Y, 0.02 * math.sin(T * f / n)), 'thigh_r': (Y, 0.02 * math.sin(T * f / n)),
        'spine_01': (Y, 0.012 * math.sin(T * f / n)),
        'spine_02': [(X, -0.012 * math.sin(T * f / 60)), (Y, 0.01 * math.sin(T * f / n))],
        'spine_03': (X, -0.018 * math.sin(T * f / 60)),
        'clavicle_l': (Y, -0.01 * math.sin(T * f / 60)), 'clavicle_r': (Y, 0.01 * math.sin(T * f / 60)),
        'upperarm_l': (X, 0.02 * math.sin(T * f / n + 1)), 'upperarm_r': (X, -0.02 * math.sin(T * f / n + 2)),
        'lowerarm_l': (X, -0.06 - 0.02 * math.sin(T * f / 60)), 'lowerarm_r': (X, -0.06 - 0.02 * math.sin(T * f / 60)),
        'neck_01': (X, 0.01 * math.sin(T * f / 60)),
        'head': [(Z, 0.09 * math.sin(T * f / n) ** 3), (X, 0.025 * math.sin(T * f / 90))],
    })) for f in range(0, n + 1, 10)])

    walk_clip(rig, gait, cane, hand)

    # Talk: weight on one leg, the head nodding and turning with the sense, and two gestures: the right hand
    # opens out toward the listener, then both hands make a small point together. 6 s.
    n = 180
    def gesture(f, at, length):
        t = (f - at) / length
        return math.sin(math.pi * t) ** 2 if 0 <= t <= 1 else 0.0
    poses = []
    for f in range(0, n + 1, 6):
        g1, g2 = gesture(f, 10, 80), gesture(f, 100, 70)
        poses.append((f, merge({
            'pelvis_move': (0.012, 0.0), 'pelvis': (Y, -0.02),
            'spine_02': (X, -0.01 * math.sin(T * f / 60)),
            'spine_03': [(X, -0.02 * g1 - 0.015 * math.sin(T * f / 60)), (Z, 0.04 * g1 - 0.03 * g2)],
            'neck_01': (X, -0.03 * math.sin(T * f / 45)),
            'head': [(X, -0.05 * math.sin(T * f / 45) - 0.04 * g2), (Z, 0.08 * math.sin(T * f / n) - 0.05 * g1),
                     (Y, 0.04 * g2)],
            'upperarm_r': [(X, -0.32 * g1 - 0.18 * g2), (Y, 0.08 * g1)],
            'lowerarm_r': (X, -0.15 - 1.0 * g1 - 0.7 * g2),
            'hand_r': (Y, 0.9 * g1 + 0.3 * g2),
            'upperarm_l': (X, -0.12 * g2), 'lowerarm_l': (X, -0.1 - 0.6 * g2), 'hand_l': (Y, -0.3 * g2),
        })))
    clip(rig, 'Talk', n, poses)

    # LieBack: a single pose for the body in the alley (the game lays the figure down).
    clip(rig, 'LieBack', 1, [(0, {
        **hands(rig, 0.45), 'thigh_l': (Y, -0.06), 'thigh_r': (Y, 0.09), 'head': (Y, 0.35),
    }, {  # arms fallen loose at his sides, a little away from the body, elbows soft (the game lays him on his
        # back, so 'down' here is along the ground and -Y is up off it)
        'upperarm_l': (0.32, 0.04, -1), 'lowerarm_l': (0.38, -0.1, -1), 'hand_l': (0.36, -0.05, -1),
        'upperarm_r': (-0.4, 0.04, -1), 'lowerarm_r': (-0.5, -0.06, -1), 'hand_r': (-0.45, 0.0, -1),
    }), (1, {
        **hands(rig, 0.45), 'thigh_l': (Y, -0.06), 'thigh_r': (Y, 0.09), 'head': (Y, 0.35),
    }, {  # arms fallen loose at his sides, a little away from the body, elbows soft (the game lays him on his
        # back, so 'down' here is along the ground and -Y is up off it)
        'upperarm_l': (0.32, 0.04, -1), 'lowerarm_l': (0.38, -0.1, -1), 'hand_l': (0.36, -0.05, -1),
        'upperarm_r': (-0.4, 0.04, -1), 'lowerarm_r': (-0.5, -0.06, -1), 'hand_r': (-0.45, 0.0, -1),
    })])

    # Aim: the right arm straight out at the front (a pistol), the body turned a little behind it
    aim = ({**hands(rig, grip='r'), 'spine_03': (Z, 0.15), 'head': (Z, -0.1)},
           {'upperarm_r': (-0.12, -1, 0.08), 'lowerarm_r': (-0.05, -1, 0.06), 'hand_r': (0, -1, 0.04)})
    clip(rig, 'Aim', 1, [(0, *aim), (1, *aim)])
    # HandsUp: both hands raised beside the head
    up = ({**hands(rig, 0.12), 'spine_03': (X, 0.04)},
          {'upperarm_l': (0.55, 0.05, 0.85), 'lowerarm_l': (0.05, 0.05, 1), 'upperarm_r': (-0.55, 0.05, 0.85), 'lowerarm_r': (-0.05, 0.05, 1)})
    clip(rig, 'HandsUp', 1, [(0, *up), (1, *up)])
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
        hair=['elvs_grump_hair'], hair_color='#0d0b0a', eyebrows='eyebrow012', eyes='grey', slick=True, hair_ratio=0.22,
        clothes=['toigo_male_suit_3', 'shoes06'], suit='#121212', shoes='#0b0a0a',
        coat='frock', coat_color='#141414', hat='tophat', chain=True, hand_clearance=0.07,
        cane='l',  # in the left hand, so the right is free to gesture
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
        suit='#8a7656', suit_kind='tweed', shirt='#e8e2d4', split=0.5, tie='#4a2418', shoes='#2a1c12',
        moustache='#5a3f28', bowler='#3b2a1c',
    ),
    # Big, heavy police sergeant: grey overcoat, black bowler, heavy moustache.
    'polhaus': dict(
        height=1.86,
        macro=dict(age=0.68, muscle=0.62, weight=0.78, height=0.62, proportions=0.5),
        face={'head/head-square': 0.6, 'chin/chin-width-incr': 0.5, 'chin/chin-prominent-incr': 0.2,
              'nose/nose-volume-incr': 0.4, 'nose/nose-scale-horiz-incr': 0.3, 'eyebrows/eyebrows-trans-down': 0.3,
              'neck/neck-scale-horiz-incr': 0.5, 'cheek/l-cheek-volume-incr': 0.4, 'cheek/r-cheek-volume-incr': 0.4},
        hair=['short01'], hair_color='#2e2219', eyebrows='eyebrow001', eyes='brownlight', iris='#4a3220',
        clothes=['toigo_male_suit_3', 'shoes06', 'grinsegold_moustache', 'culturalibre_cl_bowler_hat'],
        suit='#2a2a2c', shoes='#0e0c0b', moustache='#2e2219', bowler='#141414',
        coat='overcoat', coat_color='#3a3c40', hand_clearance=0.085,
    ),
    # Young beat constable: navy tunic, brass buttons, belt, helmet.
    'kelly': dict(
        height=1.8,
        macro=dict(age=0.42, muscle=0.55, weight=0.42, height=0.58, proportions=0.6),
        face={'head/head-oval': 0.3, 'nose/nose-point-up': 0.2, 'nose/nose-scale-horiz-decr': 0.1,
              'chin/chin-height-decr': 0.1, 'cheek/l-cheek-volume-incr': 0.2, 'cheek/r-cheek-volume-incr': 0.2},
        hair=['short02'], hair_color='#7a3f1f', eyebrows='eyebrow006', eyes='lightblue', slick=True,
        clothes=['toigo_male_suit_3', 'shoes06'], suit='#1a2238', shirt='#1d263e', tie='#1a2238', shoes='#0b0a0a',
        tunic=True, hat='helmet',
    ),
    # The victim: overcoat buttoned to the collar (a clue), hat lying apart in the alley.
    'archer': dict(
        height=1.8,
        macro=dict(age=0.6, muscle=0.6, weight=0.6, height=0.58, proportions=0.55),
        face={'head/head-square': 0.4, 'chin/chin-prominent-incr': 0.3, 'nose/nose-scale-vert-decr': 0.2,
              'mouth/mouth-scale-horiz-incr': 0.2},
        hair=['short02'], hair_color='#4a3324', eyebrows='eyebrow003', eyes='brownlight', iris='#4a3220',
        clothes=['toigo_male_suit_3', 'shoes06', 'grinsegold_moustache'],
        suit='#2b2925', shoes='#120f0d', moustache='#4a3324',
        coat='buttoned', coat_color='#3d3a33', hem=0.12, hand_clearance=0.085,
    ),
    # Chapter IV. Kasper Gutman, the Fat Man (as Hammett describes him): flabbily fat, bulbous pink cheeks,
    # a black cutaway coat, black waistcoat, grey striped trousers.
    'gutman': dict(
        height=1.78,
        macro=dict(age=0.72, muscle=0.25, weight=1.0, height=0.5, proportions=0.4),
        face={'head/head-round': 0.8, 'head/head-fat-incr': 1.0, 'neck/neck-double-incr': 1.0,
              'neck/measure-neck-circ-incr': 0.8, 'cheek/l-cheek-volume-incr': 0.8, 'cheek/r-cheek-volume-incr': 0.8,
              'chin/chin-prominent-decr': 0.3, 'nose/nose-volume-incr': 0.3, 'eyebrows/eyebrows-trans-down': 0.2,
              'torso/measure-waist-circ-incr': 1.0, 'torso/torso-scale-depth-incr': 0.8,
              'stomach/stomach-pregnant-incr': 0.7, 'hip/hip-scale-depth-incr': 0.6, 'hip/hip-scale-horiz-incr': 0.5,
              'mouth/mouth-lowerlip-volume-incr': 0.5, 'mouth/mouth-upperlip-volume-incr': 0.3,
              'eyes/l-eye-bag-incr': 0.5, 'eyes/r-eye-bag-incr': 0.5, 'cheek/l-cheek-trans-down': 0.3,
              'cheek/r-cheek-trans-down': 0.3},
        # "dark ringlets thinly covering his broad scalp"
        hair=['short02'], slick=True, hair_color='#2a2420', eyebrows='eyebrow001', eyes='brownlight', iris='#3a2618',
        skin='middleage_caucasian_male', skin_tone='#fff0ea',
        clothes=['toigo_male_suit_3', 'shoes06'], suit='#121212', shirt='#e8e2d4', shoes='#0b0a0a',
        coat='frock', cutaway=1.3, coat_color='#151515', hand_clearance=0.16, chain=True, gait='heavy',
    ),
    # Wilmer Cook, the gunsel: a small, young, pale man with a cap and an overcoat too good for him.
    'wilmer': dict(
        height=1.66,
        macro=dict(age=0.3, muscle=0.5, weight=0.38, height=0.3, proportions=0.6),
        face={'head/head-oval': 0.3, 'nose/nose-scale-horiz-decr': 0.2, 'mouth/mouth-scale-horiz-decr': 0.2,
              'eyebrows/eyebrows-trans-down': 0.4, 'chin/chin-prominent-incr': 0.2},
        hair=['short02'], hair_color='#4a3a28', eyebrows='eyebrow006', eyes='lightblue', slick=True,
        clothes=['toigo_male_suit_3', 'shoes06', 'elvs_male_flat_cap1'], suit='#2a2a2c', shoes='#16120e',
        coat='overcoat', coat_color='#2c2e30', hand_clearance=0.085, cap='#3a3632',
    ),
    # Joel Cairo, the Levantine (Hammett): small-boned, dark, glossy black hair, rings, a tight black coat, gardenia.
    'cairo': dict(
        height=1.7,
        macro=dict(age=0.45, muscle=0.3, weight=0.42, height=0.4, proportions=0.65),
        face={'head/head-oval': 0.5, 'head/head-scale-horiz-decr': 0.15, 'nose/nose-hump-incr': 0.7,
              'nose/nose-scale-vert-incr': 0.4, 'nose/nose-point-down': 0.35, 'nose/nose-volume-incr': 0.2,
              'eyebrows/eyebrows-angle-up': 0.3, 'eyebrows/eyebrows-trans-down': 0.15,
              'eyes/l-eye-eyefold-down': 0.35, 'eyes/r-eye-eyefold-down': 0.35, 'eyes/l-eye-bag-incr': 0.3,
              'eyes/r-eye-bag-incr': 0.3, 'mouth/mouth-scale-horiz-decr': 0.2, 'mouth/mouth-lowerlip-volume-incr': 0.35,
              'mouth/mouth-upperlip-volume-incr': 0.2, 'chin/chin-prominent-decr': 0.2,
              'cheek/l-cheek-volume-incr': 0.2, 'cheek/r-cheek-volume-incr': 0.2},
        hair=['elvs_grump_hair'], hair_ratio=0.22, hair_color='#070606', eyebrows='eyebrow001', eyes='brownlight',
        iris='#2a1a10', slick=True, skin='middleage_caucasian_male', skin_tone='#e8cdb0',
        clothes=['toigo_male_suit_3', 'shoes06'], suit='#141218', shirt='#ece6d8', tie='#3a1830', shoes='#0b0a0a',
        coat='frock', coat_color='#18161c', hand_clearance=0.06, gardenia=True,
    ),
    # Mr. Tobias Wren, keeper of the Art Association's collection (invented): thin, elderly, ink on his fingers.
    'wren': dict(
        height=1.74,
        macro=dict(age=0.88, muscle=0.3, weight=0.25, height=0.45, proportions=0.6),
        face={'head/head-oval': 0.5, 'head/head-scale-horiz-decr': 0.2, 'nose/nose-scale-vert-incr': 0.3,
              'nose/nose-point-down': 0.3, 'cheek/l-cheek-volume-decr': 0.4, 'cheek/r-cheek-volume-decr': 0.4},
        hair=['short02'], hair_color='#b8b4ac', eyebrows='eyebrow003', eyes='grey', skin='old_caucasian_male',
        clothes=['toigo_male_suit_3', 'shoes06', 'grinsegold_moustache'], suit='#2a2622', shoes='#120f0d',
        moustache='#c8c4bc', hand_clearance=0.06,
    ),
    # Chapter III. Brigid O'Shaughnessy, "Miss Wonderly" (Hammett): tall, pliantly slender, dark red hair,
    # cobalt-blue eyes; here in an 1895 walking dress of blue, a fitted bodice over a long flared skirt.
    'brigid': dict(
        height=1.7,
        macro=dict(gender=0.0, age=0.47, muscle=0.4, weight=0.36, height=0.62, proportions=0.9, cupsize=0.5,
                   firmness=0.6),
        # a heart-shaped face: high cheekbones, a small chin and neat jaw, full lips, large eyes under arched brows
        face={'head/head-invertedtriangular': 0.45, 'head/head-oval': 0.4, 'head/head-scale-horiz-decr': 0.12,
              'chin/chin-width-decr': 0.6, 'chin/chin-height-decr': 0.25, 'chin/chin-jaw-drop-decr': 0.3,
              'chin/chin-prominent-decr': 0.15, 'cheek/l-cheek-bones-incr': 0.55, 'cheek/r-cheek-bones-incr': 0.55,
              'cheek/l-cheek-volume-decr': 0.2, 'cheek/r-cheek-volume-decr': 0.2,
              'nose/nose-scale-horiz-decr': 0.4, 'nose/nose-scale-vert-decr': 0.15, 'nose/nose-point-up': 0.25,
              'nose/nose-width1-decr': 0.3, 'nose/nose-nostrils-width-decr': 0.3,
              'mouth/mouth-upperlip-volume-incr': 0.5, 'mouth/mouth-lowerlip-volume-incr': 0.45,
              'mouth/mouth-cupidsbow-incr': 0.5, 'mouth/mouth-scale-horiz-decr': 0.1, 'mouth/mouth-angles-up': 0.15,
              'eyes/r-eye-scale-incr': 0.1, 'eyes/l-eye-scale-incr': 0.1, 'eyes/r-eye-corner2-up': 0.25,
              'eyes/l-eye-corner2-up': 0.25, 'eyes/r-eye-eyefold-down': 0.2, 'eyes/l-eye-eyefold-down': 0.2,
              'eyebrows/eyebrows-angle-up': 0.35, 'eyebrows/eyebrows-trans-up': 0.25,
              'forehead/forehead-scale-vert-decr': 0.2, 'neck/neck-scale-horiz-decr': 0.35,
              'neck/measure-neck-height-incr': 0.3, 'torso/measure-waist-circ-decr': 0.6,
              'torso/measure-shoulder-dist-decr': 0.3, 'torso/measure-hips-circ-incr': 0.2},
        # dark red hair dressed up off the neck, as an 1895 lady wore it
        hair=['elvs_50s_updo'], hair_color='#3c130b', hair_ratio=0.7, eyebrows='eyebrow009', brows='#4a1a0e',
        eyes='deepblue', iris='#2440a8',
        skin='toigo_light_skin_with_natural_makeup', clothes=['toigo_female_suit', 'shoes01', 'toigo_gloves_short'],
        # a clear cornflower-to-cobalt blue that stays blue under warm gaslight; the gloves a lighter kid blue
        top='#2a4590', shirt='#efe9dc', shoes='#14100d', gloves='#4f78d8',
        gown='#2f4f9e', bell=0.2, bell_back=0.45, skirt_follow=0.45, sleeves=0.02, hand_clearance=0.13,
        gait='lady',
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
    rerest_arms_down(rig, meshes, body, c.get('hand_clearance', 0.05))

    suit = parts.get('toigo_male_suit_3')
    if suit:
        # re-texture the suit for 1895: the atlas holds jacket, trousers, shirt and tie; plain wool (no pinstripe),
        # linen, and a dark silk tie
        reweave(suit, c['suit'], c.get('shirt', '#e8e2d4'), c.get('tie', '#141216'), c.get('split', 0.42),
                kind=c.get('suit_kind', 'wool'), cloth_rects=[(0.812, 0.533, 0.895, 0.56)],  # no pocket square
                tie_rects=[(0.84, 0.74, 0.94, 0.975)])
    for p in parts.values():
        if c.get('top') and 'female_suit' in p.name:
            reweave(p, c['top'], c.get('shirt', '#ece6d8'), None, 0.55, 0.9)
            if c.get('sleeves'): gigot_sleeves(p, rig, c['sleeves'])
    for h in c.get('hair', []):
        if c.get('slick'): slick_hair(parts[h], body)
        if c.get('puff'): puff_hair(parts[h], body, c['puff'])
    eye_colour(parts['low-poly'], c.get('eyes', 'grey'), c.get('iris'))
    hair_hex = c['hair_color']
    for p in parts.values():
        if p.name.endswith(tuple(h for h in c.get('hair', []))): tint(p, hair_hex, keep_texture=0.6)
        if 'shoes' in p.name: tint(p, c['shoes'], keep_texture=0.3)
        if 'moustache' in p.name: tint(p, c.get('moustache', hair_hex), keep_texture=0.45)
        if 'eyebrow' in p.name: tint(p, c.get('brows', c.get('moustache', hair_hex)), keep_texture=0.3)
        if 'eyelashes' in p.name: tint(p, '#1a1410', keep_texture=0.2)
        if 'bowler' in p.name: tint(p, c.get('bowler', '#141414'), keep_texture=0.3)
        if 'cap' in p.name and c.get('cap'): tint(p, c['cap'], keep_texture=0.5)
        if 'gloves' in p.name: tint(p, c.get('gloves', '#141210'), keep_texture=0.35)
    # clean materials for the game: no clearcoat, no stray bump/normal maps, hair and brows alpha-tested
    for p in parts.values():
        n = p.name
        if n.endswith(tuple(c.get('hair', []))) or 'moustache' in n or 'beard' in n: finish(p, 0.55, cutout=True)
        elif 'eyebrow' in n or 'eyelashes' in n: finish(p, 0.8, cutout=True)
        elif n.endswith('low-poly'): finish(p, 0.12)
        elif 'shoes' in n: finish(p, 0.32)
        # (no sheen on cloth: a grey sheen turns black wool brown and blue silk lavender under warm lamps)
        elif 'gloves' in n: finish(p, 0.6)
        elif 'bowler' in n or 'cap' in n: finish(p, 0.7)
        elif 'suit' in n: finish(p, 0.85)
        else: finish(p, 0.75)
    if c.get('skin_tone'):  # a multiply over the skin texture: Cairo's Levantine olive
        tone = [x for x in hex01(c['skin_tone'])]
        bake_base_colour(body, lambda rgb, lum: rgb * tone)
    finish(body, c.get('skin_rough', 0.5), sheen=0.25, sheen_tint=(1.0, 0.55, 0.45))

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
            return 0.16 + c.get('cutaway', 0.55) * ((z_waist - z) / (z_waist - z_knee)) ** 1.5
        coat = long_coat('Coat', rig, sources, wool, z_neck, z_knee - 0.04, offset=0.01, flare=0.03, collar=False,
                         gap=opening)
        transfer_weights(coat, body, rig, skirt_weights(rig, bone_head(rig, 'thigh_l').z + 0.05, z_knee))
        coat_sleeves('CoatSleeves', parts['toigo_male_suit_3'], wool)
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
        coat_sleeves('CoatSleeves', parts['toigo_male_suit_3'], wool, 0.012)
        zs = [z_neck - 0.06 - i * 0.1 for i in range(5 if done_up else 3)]
        if not done_up: zs = [z_waist + 0.02 - i * 0.1 for i in range(3)]
        cols = [front_of(coat, 0.035, z) for z in zs]
        buttons(rig, plain(f'{name}_horn', '#15110d', 0.4), [0.035] * len(zs), [y - 0.004 for y in cols], zs)
    if c.get('gown'):
        # an 1895 walking skirt: from the waist to the floor, flaring like a bell, hiding the trousers of the suit
        silk = fabric(f'{name}_faille', c['gown'], 'wool', rough=0.65, scale=10)
        z_waist = bone_head(rig, 'spine_01').z + 0.05
        z_floor = bone_head(rig, 'foot_l').z - 0.02
        centre = (0.0, bone_head(rig, 'pelvis').y)
        bvh = world_mesh_bvh([body], ARM_GROUPS, unmasked=True)  # fitted to the body: the jacket's basque falls over it
        z_hip = bone_head(rig, 'thigh_l').z - 0.04
        ring = lambda z: smooth_ring([x + 0.03 for x in envelope(bvh, z, centre, 48)], 3)
        hip = ring(z_hip)
        rows = []
        for i in range(9):  # fitted from the waist over the hips
            z = z_waist - (z_waist - z_hip) * i / 8
            rows.append((z, [max(a, b * (0.7 + 0.3 * i / 8)) for a, b in zip(ring(z), hip)]))
        steps = int((z_hip - z_floor) / 0.04)
        bell, back = c.get('bell', 0.24), c.get('bell_back', 0.35)
        for i in range(1, steps + 1):  # then a bell, widening toward the hem, more behind than in front
            t = i / steps
            z = z_hip - (z_hip - z_floor) * t
            rows.append((z, [r + bell * t ** 1.4 * (1 + back * (1 - math.cos(2 * math.pi * k / 48)) / 2)
                             for k, r in enumerate(hip)]))
        skirt = garment('Skirt', silk, rows, centre, seg=48)
        transfer_weights(skirt, body, rig, skirt_weights(rig, bone_head(rig, 'thigh_l').z + 0.05, z_floor,
                                                         c.get('skirt_follow', 0.5)))
    if c.get('gardenia'):
        suitm = parts['toigo_male_suit_3']
        bvh = world_mesh_bvh([o for o in rig.children if o.type == 'MESH' and o.name in ('Coat', suitm.name)])
        def surf(x, z):
            loc, *_ = bvh.ray_cast(Vector((x, -1, z)), Vector((0, 1, 0)), 2)
            return loc.y if loc else -0.12
        buttonhole_flower(rig, surf, plain(f'{name}_petal', '#f3eedf', 0.55), plain(f'{name}_leaf', '#1f3a1c', 0.5),
                          0.085, bone_head(rig, 'spine_03').z + 0.1)
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
    if c.get('cane'):
        cane(rig, c['cane'], plain(f'{name}_ebony', '#0f0b09', 0.22), plain(f'{name}_silver', '#cfcfcf', 0.25, 1.0),
             plain(f'{name}_brass', '#b08a3e', 0.35, 1.0))
    if c.get('hat') == 'tophat':
        top_hat(rig, body, plain(f'{name}_silk', '#0a0a0a', 0.38))
    if c.get('hat') == 'deerstalker':
        deerstalker(rig, body, fabric(f'{name}_cap', c.get('cap', c['tweed']), 'tweed', scale=3))
    hats = [o for o in rig.children if o.type == 'MESH' and any(k in o.name for k in ('TopHat', 'Helmet', 'Deerstalker',
                                                                                       'bowler', 'flat_cap'))]
    for hat in hats:
        for hname in c.get('hair', []): hair_under_hat(parts[hname], body, hat)

    # phone budget: drop the hidden skin, thin out everything but the face
    before = sum(triangles(o) for o in rig.children if o.type == 'MESH')
    h, top = head_frame(rig, body)  # (measured before decimation)
    parts['_hair'] = [parts[x].name for x in c.get('hair', [])]
    # with no coat over it the jacket shows: give it more of the budget
    optimise(rig, body, parts, c.get('hair_ratio', 0.55), None if c.get('coat') or c.get('gown') else 0.25)
    parts.pop('_hair')
    rows = sorted(((triangles(o), o.name) for o in rig.children if o.type == 'MESH'), reverse=True)
    print('TRIS', name, before, '->', sum(n for n, _ in rows), ' '.join(f'{nm}:{n}' for n, nm in rows))

    # scale to the character's height (top of the head; the game expects metres)
    s = c['height'] / top
    rig.scale = (s, s, s)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for o in rig.children:
        o.select_set(True)
    make_clips(rig, c.get('gait', 'gent'), c.get('cane'))

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
    for o in [rig] + list(rig.children):  # only walk_speed goes to the game in the glTF extras, not MPFB's notes
        for k in [k for k in o.keys() if k.startswith(('MPFB', 'Mh'))]: del o[k]
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for o in rig.children: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', f'{name}.glb'), export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True, export_animations=True,
                              export_animation_mode='NLA_TRACKS', export_image_format='JPEG',
                              export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                              export_jpeg_quality=85, export_cameras=False, export_lights=False, export_extras=True)
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
    rig.animation_data.action = None
    for t in rig.animation_data.nla_tracks: t.mute = True
    for pb in rig.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
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
    # the open-handed gesture of the Talk clip, and the far side of the walk
    for tag, track, frame, loc in (('talk', 'Talk', 50, (0.9, -3.2, 1.3)), ('walk2', 'Walk', 26, (-2.6, -3.0, 1.1))):
        for t in rig.animation_data.nla_tracks: t.mute = t.name != track
        scene.frame_set(frame)
        cam.location = loc
        cam.rotation_euler = (Vector((0, 0, 1.0)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = os.path.join(out, f'{name}_{tag}.png')
        bpy.ops.render.render(write_still=True)


only = arg('--only')
out = arg('--render')
for name, c in CAST.items():
    if only and name not in only.split(','): continue
    rig, body = build(name, c)
    if out: render(rig, body, out, name)
