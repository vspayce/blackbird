# Builds the character models for The Black Bird and exports them for the game.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_characters.py -- [--render preview.png]
#
# Writes art/holmes.blend (open it to tweak by hand) and public/models/holmes.glb.
# Each character is a hierarchy of empties named like the pivots in
# src/game/figure.js (body > hips > leg_R/leg_L/torso > arm_R/arm_L/head), with
# rigid meshes parented to them, so the game's procedural animation drives them.
# Blender is Z-up and the character faces -Y; the glTF export turns that into
# the game's Y-up, facing +Z. Units are metres, modelled at 1.8 m tall
# (the game scales body by height / 1.8).
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RENDER = args[args.index('--render') + 1] if '--render' in args else None

# Pivots in world space, matching figure.js at 1.8 m.
PIVOTS = {
    'hips': (0, 0, 0.92), 'torso': (0, 0, 0.92),
    'leg_R': (-0.1, 0, 0.92), 'leg_L': (0.1, 0, 0.92),
    'arm_R': (-0.24, 0, 1.50), 'arm_L': (0.24, 0, 1.50),
    'head': (0, 0, 1.60),
}
TREE = {'body': None, 'hips': 'body', 'leg_R': 'hips', 'leg_L': 'hips', 'torso': 'hips',
        'arm_R': 'torso', 'arm_L': 'torso', 'head': 'torso'}


def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1]


def material(name, hex, rough=0.85, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = srgb(hex)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    m.diffuse_color = srgb(hex)
    m.use_backface_culling = False  # exported as doubleSided, like the old figures
    return m


class Part:
    """One rigid mesh per pivot, built in world space with a material per face."""
    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def mi(self, m):
        if m not in self.mats: self.mats.append(m)
        return self.mats.index(m)

    def lathe(self, m, prof, seg=16, sx=1, sy=1, at=(0, 0, 0), gap=0.0, smooth=True):
        """Revolve [(r, z)] around a vertical axis. gap (radians) leaves the front (-Y) open."""
        bm, idx = self.bm, self.mi(m)
        wrap = gap <= 0
        n = seg if wrap else seg + 1
        a0 = -math.pi / 2 + gap / 2
        span = 2 * math.pi - gap
        rows = []
        for r, z in prof:
            if r < 1e-3:  # a pole: one vertex closes the end
                rows.append([bm.verts.new((at[0], at[1], at[2] + z))] * n)
                continue
            rows.append([bm.verts.new((at[0] + r * math.cos(a) * sx, at[1] + r * math.sin(a) * sy, at[2] + z))
                         for a in (a0 + span * j / seg for j in range(n))])
        faces = []
        for i in range(len(rows) - 1):
            for j in range(seg):
                k = (j + 1) % n
                vs = list(dict.fromkeys([rows[i][j], rows[i][k], rows[i + 1][k], rows[i + 1][j]]))
                if len(vs) < 3: continue
                f = bm.faces.new(vs)
                f.material_index, f.smooth = idx, smooth
                faces.append(f)
        return faces

    def ellipsoid(self, m, c, rx, ry, rz, seg=12, rings=8, cut=None):
        prof = [(math.sin(math.pi * i / rings) * (i not in (0, rings)), -math.cos(math.pi * i / rings))
                for i in range(rings + 1)]
        faces = self.lathe(m, [(r, z * rz) for r, z in prof], seg, rx, ry, c)
        if cut:  # flatten anything below a plane (soles of shoes)
            for f in faces:
                for v in f.verts:
                    v.co.z = max(v.co.z, cut)
        return faces

    def hull(self, m, pts, smooth=False):
        bm, idx = self.bm, self.mi(m)
        vs = [bm.verts.new(p) for p in pts]
        out = bmesh.ops.convex_hull(bm, input=vs)
        for g in out['geom']:
            if isinstance(g, bmesh.types.BMFace):
                g.material_index, g.smooth = idx, smooth
        for v in out.get('geom_interior', []) + out.get('geom_unused', []):
            if isinstance(v, bmesh.types.BMVert) and v.is_valid and not v.link_faces:
                bm.verts.remove(v)

    def block(self, m, c, size, rot=(0, 0, 0)):
        R = (Matrix.Rotation(rot[2], 3, 'Z') @ Matrix.Rotation(rot[1], 3, 'Y') @ Matrix.Rotation(rot[0], 3, 'X'))
        pts = [Vector(c) + R @ Vector((sx * size[0] / 2, sy * size[1] / 2, sz * size[2] / 2))
               for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
        self.hull(m, pts)

    def fan(self, m, centre, rim):
        bm, idx = self.bm, self.mi(m)
        c = bm.verts.new(centre)
        vs = [bm.verts.new(p) for p in rim]
        for a, b in zip(vs, vs[1:]):
            f = bm.faces.new((c, a, b))
            f.material_index, f.smooth = idx, True


def build(name, parts):
    """Turn {pivot: Part} into the empty hierarchy + meshes, all in a collection."""
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    root = bpy.data.objects.new(name, None)
    col.objects.link(root)
    empties = {}
    for p, parent in TREE.items():
        e = bpy.data.objects.new(p, None)
        e.empty_display_size = 0.06
        col.objects.link(e)
        e.parent = empties[parent] if parent else root
        world = Vector(PIVOTS.get(p, (0, 0, 0)))
        parent_world = Vector(PIVOTS.get(parent, (0, 0, 0))) if parent else Vector()
        e.location = world - parent_world
        empties[p] = e
    for p, part in parts.items():
        me = bpy.data.meshes.new(f'{name}_{p}')
        bmesh.ops.recalc_face_normals(part.bm, faces=part.bm.faces[:])
        bmesh.ops.translate(part.bm, verts=part.bm.verts[:], vec=-Vector(PIVOTS[p]))
        part.bm.to_mesh(me)
        part.bm.free()
        for m in part.mats: me.materials.append(m)
        ob = bpy.data.objects.new(f'{name}_{p}_mesh', me)
        col.objects.link(ob)
        ob.parent = empties[p]
    return root, col


def holmes():
    tweed = material('Holmes_Tweed', '#4a4539', 0.95)
    hatm = material('Holmes_Deerstalker', '#6b6250', 0.95)
    trousers = material('Holmes_Trousers', '#2b2927', 0.9)
    shoe = material('Holmes_Shoes', '#121010', 0.35)
    shirt = material('Holmes_Shirt', '#ddd6c8', 0.7)
    cravat = material('Holmes_Cravat', '#141414', 0.6)
    skin = material('Holmes_Skin', '#d2b49a', 0.65)
    hair = material('Holmes_Hair', '#141110', 0.5)
    dark = material('Holmes_Eyes', '#120e0c', 0.3)
    lips = material('Holmes_Lips', '#a8786a', 0.6)

    P = {k: Part() for k in ('leg_R', 'leg_L', 'torso', 'arm_R', 'arm_L', 'head')}

    # Legs: narrow trousers and long, polished shoes.
    for side, key in ((-1, 'leg_R'), (1, 'leg_L')):
        x, L = side * 0.1, P[key]
        L.lathe(trousers, [(0.075, 0.96), (0.073, 0.8), (0.064, 0.55), (0.057, 0.3), (0.058, 0.12), (0.06, 0.08)],
                12, 1, 0.95, (x, 0, 0))
        L.ellipsoid(shoe, (x, -0.035, 0.04), 0.048, 0.135, 0.05, 12, 8, cut=0.0)
        L.block(shoe, (x, 0.055, 0.02), (0.075, 0.06, 0.04))  # heel

    T = P['torso']
    # Frock coat body, lean and narrow-waisted.
    T.lathe(tweed, [(0.15, 0.9), (0.152, 1.0), (0.163, 1.15), (0.176, 1.3), (0.178, 1.42), (0.15, 1.49),
                    (0.09, 1.53), (0.05, 1.545)], 16, 1.25, 0.72)
    # Long coat below the waist, open at the front so the legs read when walking.
    T.lathe(tweed, [(0.17, 1.02), (0.185, 0.92), (0.215, 0.72), (0.245, 0.48), (0.25, 0.44)], 18, 1.1, 0.92,
            gap=0.45)
    # Inverness cape over the shoulders, buttoned at the throat.
    T.lathe(tweed, [(0.07, 1.565), (0.13, 1.552), (0.2, 1.527), (0.255, 1.49), (0.29, 1.44), (0.306, 1.37), (0.312, 1.25),
                    (0.315, 1.14)],
            24, 1.0, 0.8, gap=0.12)
    # Turned-up collar, open at the front over the shirt.
    T.lathe(tweed, [(0.074, 1.53), (0.076, 1.6), (0.082, 1.63)], 14, 1.0, 0.95, gap=1.5)
    T.lathe(shirt, [(0.052, 1.525), (0.05, 1.585)], 12, 1.0, 1.0)
    T.block(cravat, (0, -0.05, 1.54), (0.04, 0.02, 0.035))
    for i in range(3):  # cape buttons
        T.ellipsoid(cravat, (0, -0.152 - i * 0.026, 1.49 - i * 0.075), 0.009, 0.006, 0.009, 6, 4)

    # Arms: long sleeves, white cuffs, slender hands.
    for side, key in ((-1, 'arm_R'), (1, 'arm_L')):
        x, A = side * 0.24, P[key]
        A.lathe(tweed, [(0.03, 1.515), (0.058, 1.49), (0.062, 1.42), (0.058, 1.25), (0.052, 1.05), (0.05, 0.94)],
                12, 1, 0.95, (x, 0, 0))
        A.lathe(shirt, [(0.046, 0.945), (0.045, 0.915)], 10, 1, 0.95, (x, 0, 0))
        A.ellipsoid(skin, (x, -0.004, 0.868), 0.026, 0.042, 0.055, 10, 6)
        A.ellipsoid(skin, (x - side * 0.006, -0.03, 0.885), 0.012, 0.013, 0.024, 6, 4)  # thumb

    H = P['head']
    H.lathe(skin, [(0.044, 1.55), (0.045, 1.64), (0.05, 1.665)], 12)  # neck
    # A long, narrow face: high forehead, strong jaw, pointed chin.
    face = [(1e-4, 1.612), (0.03, 1.617), (0.055, 1.64), (0.068, 1.675), (0.077, 1.715), (0.083, 1.755),
            (0.085, 1.795), (0.077, 1.83), (0.055, 1.857), (1e-4, 1.868)]
    H.lathe(skin, face, 16, 0.88, 1.08)
    # Aquiline nose.
    H.hull(skin, [(0, -0.088, 1.768), (-0.009, -0.085, 1.762), (0.009, -0.085, 1.762), (0, -0.117, 1.703),
                  (0, -0.101, 1.69), (-0.017, -0.083, 1.694), (0.017, -0.083, 1.694)])
    for s in (-1, 1):
        H.ellipsoid(dark, (s * 0.031, -0.084, 1.748), 0.009, 0.005, 0.0065, 8, 4)  # deep-set eyes
        H.block(hair, (s * 0.032, -0.09, 1.767), (0.034, 0.008, 0.0065), (0, s * 0.18, 0))  # brows
        H.ellipsoid(skin, (s * 0.074, 0.004, 1.735), 0.008, 0.015, 0.022, 8, 5)  # ears
    H.block(lips, (0, -0.072, 1.663), (0.03, 0.006, 0.006))
    # Black hair swept back: a shell over the skull, cut at a slanted hairline.
    shell = H.lathe(hair, [(r * 1.06, 1.6 + (z - 1.6) * 1.04) for r, z in face[3:]], 16, 0.88, 1.08)
    doomed = {v for f in shell for v in f.verts if v.co.z < 1.745 - 0.5 * v.co.y}
    bmesh.ops.delete(H.bm, geom=list(doomed), context='VERTS')
    # Deerstalker: crown, a peak front and back, ear flaps tied over the top.
    H.lathe(hatm, [(0.1, 1.795), (0.102, 1.82), (0.094, 1.86), (0.072, 1.89), (0.036, 1.905), (1e-4, 1.91)],
            16, 0.95, 1.08)
    for s in (-1, 1):
        rim = [(0.084 * math.cos(t), s * (0.104 + 0.062 * math.sin(t)), 1.802 - 0.022 * math.sin(t))
               for t in (math.pi * i / 10 for i in range(11))]
        H.fan(hatm, (0, s * 0.1, 1.804), rim)
        H.block(hatm, (s * 0.07, 0, 1.875), (0.012, 0.075, 0.05), (0, s * -0.85, 0))  # flaps
    H.block(hatm, (0, 0, 1.908), (0.03, 0.012, 0.012))  # the tie

    return build('Holmes', P)


def preview(path, target):
    scene = bpy.context.scene
    cam = bpy.data.cameras.new('PreviewCam')
    cam.lens = 70
    co = bpy.data.objects.new('PreviewCam', cam)
    scene.collection.objects.link(co)
    co.location = (2.2, -4.2, 1.35)
    co.rotation_euler = (Vector((0, 0, 1.0)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = co
    for nm, loc, e in (('Key', (2, -3, 4), 300), ('Fill', (-3, -2, 2), 80), ('Rim', (0, 3, 3), 250)):
        ld = bpy.data.lights.new(nm, 'AREA')
        ld.energy, ld.size = e, 2
        lo = bpy.data.objects.new(nm, ld)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        scene.collection.objects.link(lo)
    scene.world = scene.world or bpy.data.worlds.new('World')
    scene.world.color = (0.05, 0.05, 0.06)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = 900, 1200
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# --- main -----------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
root, col = holmes()

os.makedirs(os.path.join(ROOT, 'public', 'models'), exist_ok=True)
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', 'holmes.glb'), export_format='GLB',
                          use_selection=True, export_yup=True, export_apply=True, export_cameras=False,
                          export_lights=False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'art', 'holmes.blend'))
if RENDER: preview(RENDER, root)
