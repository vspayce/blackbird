# Builds the character models for The Black Bird and exports them for the game.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_characters.py -- [--render preview.png]
#
# Writes art/characters.blend (open it to tweak by hand) and public/models/<name>.glb
# for everyone in CAST.
# Each character is a hierarchy of empties named <Name>_<pivot> after the pivots in
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
        e = bpy.data.objects.new(f'{name}_{p}', None)  # names are unique per .blend
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


# Face profiles (r, z) revolved for the skull; all sit on the head pivot at 1.6 m.
FACES = {
    'long': [(1e-4, 1.612), (0.03, 1.617), (0.055, 1.64), (0.068, 1.675), (0.077, 1.715), (0.083, 1.755),
             (0.085, 1.795), (0.077, 1.83), (0.055, 1.857), (1e-4, 1.868)],
    'round': [(1e-4, 1.622), (0.038, 1.627), (0.066, 1.65), (0.079, 1.69), (0.085, 1.73), (0.087, 1.77),
              (0.086, 1.8), (0.077, 1.83), (0.055, 1.852), (1e-4, 1.86)],
    'square': [(1e-4, 1.616), (0.046, 1.621), (0.071, 1.646), (0.081, 1.69), (0.085, 1.73), (0.087, 1.77),
               (0.086, 1.8), (0.077, 1.83), (0.055, 1.853), (1e-4, 1.862)],
}


def person(name, o):
    """A figure in the house style. o: colours plus coat/hat/face/build options."""
    M = lambda part, hex, rough=0.9, metal=0.0: material(f'{name}_{part}', hex, rough, metal)
    coat, trousers = M('Coat', o['coat']), M('Trousers', o['trousers'])
    shoe, shirt = M('Shoes', '#121010', 0.35), M('Shirt', o.get('shirt', '#ddd6c8'), 0.7)
    tie, skin = M('Tie', o.get('tie', '#141414'), 0.6), M('Skin', o.get('skin', '#d2b49a'), 0.65)
    hair, dark = M('Hair', o['hair'], 0.5), M('Eyes', '#120e0c', 0.3)
    lips, hatm = M('Lips', '#a8786a', 0.6), M('Hat', o.get('hatColor', '#2b2520'), 0.85)
    brass = M('Brass', '#c9a04a', 0.35, 0.8)
    stout = o.get('build') == 'stout'
    bx, by = (1.38, 0.9) if stout else (1.25, 0.72)  # chest ellipse
    P = {k: Part() for k in ('leg_R', 'leg_L', 'torso', 'arm_R', 'arm_L', 'head')}

    # Legs: trousers and polished shoes.
    lw = 1.12 if stout else 1.0
    for side, key in ((-1, 'leg_R'), (1, 'leg_L')):
        x, L = side * 0.1, P[key]
        L.lathe(trousers, [(0.075 * lw, 0.96), (0.073 * lw, 0.8), (0.064 * lw, 0.55), (0.057 * lw, 0.3), (0.058, 0.12),
                           (0.06, 0.08)], 12, 1, 0.95, (x, 0, 0))
        L.ellipsoid(shoe, (x, -0.035, 0.04), 0.048, 0.13, 0.05, 12, 8, cut=0.0)
        L.block(shoe, (x, 0.055, 0.02), (0.075, 0.06, 0.04))  # heel

    T = P['torso']
    belly = 0.02 if stout else 0.0
    T.lathe(coat, [(0.15 + belly, 0.9), (0.152 + belly * 1.6, 1.0), (0.163 + belly * 1.8, 1.15), (0.176 + belly, 1.3),
                   (0.186, 1.42), (0.19, 1.455), (0.168, 1.49), (0.12, 1.52), (0.08, 1.538), (0.05, 1.545)], 16, bx, by)
    style = o['style']
    if style == 'tunic':
        # police tunic: short skirt, belt, a column of brass buttons, stand collar
        T.lathe(coat, [(0.168, 1.0), (0.178, 0.9), (0.19, 0.78), (0.192, 0.76)], 16, bx * 0.98, by * 1.15)
        T.lathe(M('Belt', '#141110', 0.4), [(0.158, 1.0), (0.158, 1.04)], 16, bx * 1.02, by * 1.06)
        T.block(brass, (0, -0.122, 1.02), (0.03, 0.008, 0.026))
        for i in range(6):
            T.ellipsoid(brass, (0, -0.128 + 0.004 * (i > 2), 1.46 - i * 0.075 + (0.13 if i > 2 else 0) * 0), 0.009,
                        0.006, 0.009, 6, 4)
        T.lathe(coat, [(0.058, 1.53), (0.058, 1.585)], 12)
    else:
        # long coat below the waist, open at the front
        T.lathe(coat, [(0.17 + belly, 1.02), (0.185 + belly, 0.92), (0.215, 0.72), (0.245, 0.48), (0.25, 0.44)], 18,
                1.1 * (bx / 1.25), 0.92 * (by / 0.72) ** 0.5, gap=0.22 if style == 'buttoned' else 0.45)
        T.lathe(shirt, [(0.052, 1.525), (0.05, 1.585)], 12, 1.0, 1.0)
        T.block(tie, (0, -0.05, 1.54), (0.04, 0.02, 0.035))
    if style == 'inverness':
        T.lathe(coat, [(0.07, 1.565), (0.13, 1.552), (0.2, 1.527), (0.255, 1.49), (0.29, 1.44), (0.306, 1.37),
                       (0.312, 1.25), (0.315, 1.14)], 24, 1.0, 0.8, gap=0.12)
        T.lathe(coat, [(0.074, 1.53), (0.076, 1.6), (0.082, 1.63)], 14, 1.0, 0.95, gap=1.5)
        for i in range(3):
            T.ellipsoid(tie, (0, -0.152 - i * 0.026, 1.49 - i * 0.075), 0.009, 0.006, 0.009, 6, 4)
    elif style in ('overcoat', 'buttoned'):
        # turned-down collar and lapels in a V over the chest
        T.lathe(coat, [(0.07, 1.52), (0.085, 1.555), (0.1, 1.53)], 14, 1.05, 1.0, gap=0.9)
        front = -0.72 * 0.176 * (by / 0.72)
        for s in (-1, 1):
            T.hull(coat, [(s * 0.035, front - 0.004, 1.5), (s * 0.075, front + 0.004, 1.48), (s * 0.02, front - 0.012, 1.3),
                          (s * 0.035, front - 0.012, 1.5), (s * 0.075, front + 0.012, 1.48), (s * 0.02, front - 0.002, 1.3)])
        n = 5 if style == 'buttoned' else 3
        for i in range(n):  # buttons, done up to the collar on Archer
            z = (1.47 if style == 'buttoned' else 1.28) - i * 0.085
            T.ellipsoid(tie, (0.02, front - 0.014 - 0.01 * (z < 1.0), z), 0.009, 0.006, 0.009, 6, 4)

    # Arms
    aw = 1.12 if stout else 1.0
    for side, key in ((-1, 'arm_R'), (1, 'arm_L')):
        x, A = side * (0.235 if stout else 0.222), P[key]  # meshes sit a little inside the pivot
        A.lathe(coat, [(1e-4, 1.472), (0.034, 1.467), (0.054 * aw, 1.448), (0.06 * aw, 1.4), (0.057 * aw, 1.25),
                       (0.052 * aw, 1.05), (0.05, 0.94)], 12, 1, 0.95, (x, 0, 0))
        A.lathe(shirt if style != 'tunic' else coat, [(0.046, 0.945), (0.045, 0.915)], 10, 1, 0.95, (x, 0, 0))
        hand = M('Gloves', o['gloves'], 0.6) if o.get('gloves') else skin
        A.ellipsoid(hand, (x, -0.004, 0.868), 0.026 * aw, 0.042, 0.055, 10, 6)
        A.ellipsoid(hand, (x - side * 0.006, -0.03, 0.885), 0.012, 0.013, 0.024, 6, 4)

    H = P['head']
    face = FACES[o.get('face', 'long')]
    fx, fy = (0.88, 1.08) if o.get('face', 'long') == 'long' else (0.94, 1.04)
    H.lathe(skin, [(0.044 * (1.12 if stout else 1), 1.55), (0.045 * (1.12 if stout else 1), 1.64), (0.05, 1.665)], 12)
    H.lathe(skin, face, 16, fx, fy)
    front = lambda z: -fy * next(r for r, zz in reversed(face) if zz <= z + 0.02)
    if o.get('face', 'long') == 'long':  # aquiline
        H.hull(skin, [(0, -0.088, 1.768), (-0.009, -0.085, 1.762), (0.009, -0.085, 1.762), (0, -0.117, 1.703),
                      (0, -0.101, 1.69), (-0.017, -0.083, 1.694), (0.017, -0.083, 1.694)])
    else:
        f = front(1.72)
        H.hull(skin, [(0, f + 0.004, 1.76), (-0.01, f + 0.006, 1.755), (0.01, f + 0.006, 1.755), (0, f - 0.024, 1.706),
                      (0, f - 0.012, 1.692), (-0.019, f + 0.004, 1.696), (0.019, f + 0.004, 1.696)])
    ef = front(1.748)
    for s in (-1, 1):
        H.ellipsoid(dark, (s * 0.031, ef + 0.006, 1.748), 0.009, 0.005, 0.0065, 8, 4)
        H.block(hair, (s * 0.032, ef, 1.767), (0.034, 0.008, 0.0065), (0, s * 0.18, 0))
        H.ellipsoid(skin, (s * 0.076 * fx / 0.88, 0.004, 1.735), 0.008, 0.015, 0.022, 8, 5)
    H.block(lips, (0, front(1.663) + 0.003, 1.663), (0.03, 0.006, 0.006))
    if o.get('moustache'):
        mz, mf = 1.682, front(1.682)
        H.hull(M('Moustache', o['moustache'], 0.8), [(-0.038, mf + 0.004, 1.672), (0.038, mf + 0.004, 1.672), (0, mf - 0.012, 1.688),
                                                    (-0.03, mf - 0.004, 1.69), (0.03, mf - 0.004, 1.69), (0, mf - 0.004, 1.676)])
    if o.get('sideburns'):
        for s in (-1, 1):
            H.block(hair, (s * 0.074 * fx / 0.88, -0.01, 1.71), (0.012, 0.03, 0.06))
    shell = H.lathe(hair, [(r * 1.06, 1.6 + (z - 1.6) * 1.04) for r, z in face[3:]], 16, fx, fy)
    line = o.get('hairline', 1.745)
    doomed = {v for f in shell for v in f.verts if v.co.z < line - 0.5 * v.co.y}
    bmesh.ops.delete(H.bm, geom=list(doomed), context='VERTS')

    hat = o.get('hat')
    if hat == 'deerstalker':
        H.lathe(hatm, [(0.1, 1.795), (0.102, 1.82), (0.094, 1.86), (0.072, 1.89), (0.036, 1.905), (1e-4, 1.91)], 16,
                0.95, 1.08)
        for s in (-1, 1):
            rim = [(0.084 * math.cos(t), s * (0.104 + 0.062 * math.sin(t)), 1.802 - 0.022 * math.sin(t))
                   for t in (math.pi * i / 10 for i in range(11))]
            H.fan(hatm, (0, s * 0.1, 1.804), rim)
            H.block(hatm, (s * 0.07, 0, 1.875), (0.012, 0.075, 0.05), (0, s * -0.85, 0))
        H.block(hatm, (0, 0, 1.908), (0.03, 0.012, 0.012))
    elif hat == 'bowler':
        H.lathe(hatm, [(0.093, 1.8), (0.095, 1.84), (0.088, 1.88), (0.068, 1.91), (0.035, 1.925), (1e-4, 1.928)], 16,
                0.98, 1.1)
        # brim, curled up at the sides
        H.lathe(hatm, [(0.094, 1.803), (0.135, 1.8), (0.142, 1.808)], 24, 0.98, 1.1)
        H.lathe(M('Band', '#0c0b0a', 0.5), [(0.096, 1.806), (0.097, 1.826)], 16, 0.98, 1.1)
    elif hat == 'helmet':
        H.lathe(hatm, [(0.102, 1.79), (0.102, 1.84), (0.094, 1.9), (0.072, 1.95), (0.04, 1.972), (1e-4, 1.976)], 16,
                0.96, 1.14)
        H.lathe(hatm, [(0.103, 1.792), (0.122, 1.785), (0.126, 1.79)], 20, 0.96, 1.14)
        H.ellipsoid(brass, (0, -0.112, 1.865), 0.022, 0.006, 0.026, 8, 5)
        H.ellipsoid(brass, (0, 0, 1.978), 0.012, 0.012, 0.01, 8, 4)

    return build(name.capitalize(), P)


CAST = {
    # Lean, pale, black hair swept back; Inverness cape and travelling cap.
    'holmes': dict(style='inverness', coat='#4a4539', trousers='#2b2927', hair='#141110', hat='deerstalker',
                   hatColor='#6b6250', skin='#d2b49a'),
    # Stocky army doctor: brown overcoat, bowler, moustache.
    'watson': dict(style='overcoat', build='stout', face='round', coat='#5a4632', trousers='#3b3128', hair='#6b4b2e',
                   moustache='#6b4b2e', hat='bowler', hatColor='#2a211a', skin='#d8b49a', tie='#5a2a22'),
    # Big, slow police sergeant: grey overcoat, black bowler, heavy moustache, gloves.
    'polhaus': dict(style='overcoat', build='stout', face='square', coat='#2f3238', trousers='#25262a', hair='#3a2a1e',
                    moustache='#3a2a1e', sideburns=True, hat='bowler', hatColor='#1b1c20', gloves='#2a2420',
                    skin='#cfa588'),
    # Young beat constable: navy tunic, brass buttons, helmet.
    'kelly': dict(style='tunic', face='square', coat='#1d2740', trousers='#1d2740', hair='#7a4a2a', hat='helmet',
                  hatColor='#1a2238', skin='#e0bca0', hairline=1.73),
    # The victim: coat buttoned to the collar (a clue), hat lying apart in the alley.
    'archer': dict(style='buttoned', build='stout', face='square', coat='#3d3a33', trousers='#2b2925', hair='#4a3324',
                   moustache='#4a3324', skin='#c8a890', tie='#3a1a14'),
}


def preview(path, roots):
    scene = bpy.context.scene
    for i, r in enumerate(roots):  # line them up for the camera
        r.location.x = (i - (len(roots) - 1) / 2) * 0.85
    cam = bpy.data.cameras.new('PreviewCam')
    cam.lens = 50
    co = bpy.data.objects.new('PreviewCam', cam)
    scene.collection.objects.link(co)
    co.location = (1.2, -6.2, 1.4)
    co.rotation_euler = (Vector((0, 0, 0.95)) - co.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = co
    for nm, loc, e in (('Key', (2, -3, 4), 400), ('Fill', (-3, -2, 2), 120), ('Rim', (0, 3, 3), 300)):
        ld = bpy.data.lights.new(nm, 'AREA')
        ld.energy, ld.size = e, 3
        lo = bpy.data.objects.new(nm, ld)
        lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        scene.collection.objects.link(lo)
    scene.world = scene.world or bpy.data.worlds.new('World')
    scene.world.color = (0.05, 0.05, 0.06)
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x, scene.render.resolution_y = 1600, 900
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# --- main -----------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
os.makedirs(os.path.join(ROOT, 'public', 'models'), exist_ok=True)
roots = []
for name, look in CAST.items():
    root, col = person(name, look)
    roots.append(root)
    bpy.ops.object.select_all(action='DESELECT')
    for o in col.objects: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', f'{name}.glb'), export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True, export_cameras=False,
                              export_lights=False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'art', 'characters.blend'))
if RENDER: preview(RENDER, roots)
