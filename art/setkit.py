# Shared kit for the set builders (art/build_set.py, art/build_hopkins.py): numpy
# textures, materials, and boxes/cylinders/lettering gathered into one mesh per
# material with world-space UVs. Everything is modelled in the game's own
# coordinates (Y up, metres); finish() turns it Z-up for Blender's exporter.
import bpy, bmesh, math, os, sys, random
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
RENDER = ARGS[ARGS.index('--render') + 1] if '--render' in ARGS else None
FONT = os.path.join(ROOT, 'art', 'fonts', 'IMFellEnglishSC-Regular.ttf')
rnd = random.Random(1895)
UP = Vector((0, 1, 0))


# --- textures (numpy, sRGB 0..1) ---------------------------------------------------

def image(name, rgb, alpha=None):
    h, w, _ = rgb.shape
    img = bpy.data.images.new(name, w, h, alpha=alpha is not None)
    px = np.ones((h, w, 4), np.float32)
    px[..., :3] = np.clip(rgb, 0, 1)
    if alpha is not None: px[..., 3] = alpha
    img.pixels.foreach_set(px[::-1].ravel())  # Blender images start at the bottom row
    img.pack()
    return img


def normal_map(name, height, strength=4.0):
    gy, gx = np.gradient(height.astype(np.float32))
    n = np.dstack([-gx * strength, gy * strength, np.ones_like(height)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    img = image(name, n * 0.5 + 0.5)
    img.colorspace_settings.name = 'Non-Color'
    return img


def noise(h, w, scale, seed):
    """Smooth value noise in 0..1."""
    g = np.random.default_rng(seed).random((h // scale + 2, w // scale + 2))
    y = np.linspace(0, h / scale, h, endpoint=False)
    x = np.linspace(0, w / scale, w, endpoint=False)
    y0, x0 = y.astype(int), x.astype(int)
    fy, fx = (y - y0)[:, None], (x - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


def brick_tex(name, base, size=1024, rows=13, per_row=5, mortar='#8a8478', soot=0.0):
    """Running-bond brick, one metre square. Returns (colour, normal)."""
    rng = np.random.default_rng(abs(hash(name)) % 2 ** 32)
    H = W = size
    rh = H / rows
    col = np.zeros((H, W, 3), np.float32)
    height = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    row = (yy / rh).astype(int)
    off = (row % 2) * (W / per_row / 2)
    bx = ((xx + off) / (W / per_row)).astype(int)
    fy = (yy % rh) / rh
    fx = ((xx + off) % (W / per_row)) / (W / per_row)
    m = 0.075
    inside = (fy > m) & (fy < 1 - m) & (fx > m * 0.35) & (fx < 1 - m * 0.35)
    ids = row * 97 + bx
    tint = rng.random(rows * 97 + per_row + 2)[ids]
    tone = 0.78 + 0.32 * tint
    hue = np.stack([tone, tone * (0.97 + 0.06 * tint), tone * (0.95 + 0.08 * rng.random(rows * 97 + per_row + 2)[ids])], -1)
    grain = noise(H, W, 6, 3)[..., None] * 0.18 + noise(H, W, 40, 4)[..., None] * 0.12
    col[:] = hexrgb(mortar) * (0.85 + 0.25 * noise(H, W, 3, 5)[..., None])
    b = hexrgb(base) * hue * (0.9 + grain)
    col[inside] = b[inside]
    # rounded brick edges for the normal map
    edge = np.minimum(np.minimum(fy - m, 1 - m - fy) * rh, np.minimum(fx - m * 0.35, 1 - m * 0.35 - fx) * (W / per_row))
    height[:] = np.clip(edge / 6, 0, 1) * inside + noise(H, W, 5, 6) * 0.15
    if soot:
        col *= (1 - soot * noise(H, W, 120, 9)[..., None])
    return image(name, col), normal_map(name + '_n', height * 3)


def clapboard_tex(name, paint, size=512, boards=7):
    """Painted lap siding, one metre square."""
    H = W = size
    yy = np.mgrid[0:H, 0:W][0]
    f = (yy % (H / boards)) / (H / boards)
    shade = 0.62 + 0.38 * np.clip(f * 1.4, 0, 1)  # dark under each lap
    weather = 0.85 + 0.2 * noise(H, W, 64, 2) - 0.1 * noise(H, W, 8, 3)
    col = hexrgb(paint) * (shade * weather)[..., None]
    height = np.clip(f, 0, 1)
    return image(name, col), normal_map(name + '_n', height * 2)


def stone_tex(name, base, size=512):
    H = W = size
    col = hexrgb(base) * (0.8 + 0.25 * noise(H, W, 30, 1) + 0.1 * noise(H, W, 4, 2))[..., None]
    return image(name, col), normal_map(name + '_n', noise(H, W, 6, 3) * 2)


def window_lit_tex(name, size=256, seed=0):
    """Lamplight behind lace curtains: a warm glow with drapes at the sides and a sash bar."""
    H = W = size
    yy, xx = np.mgrid[0:H, 0:W] / size
    rng = np.random.default_rng(seed)
    glow = 0.55 + 0.45 * np.exp(-((xx - 0.5) ** 2 * 3 + (yy - 0.55 + 0.2 * rng.random()) ** 2 * 4))
    drape = np.clip(1 - np.abs(xx - 0.5) * 2.2, 0, 1) ** 0.3
    lace = 0.85 + 0.15 * np.sin(xx * 160) * np.sin(yy * 140)
    v = glow * (0.35 + 0.65 * drape) * lace
    col = np.stack([v * 1.0, v * 0.66, v * 0.32], -1)
    bar = (np.abs(yy - 0.5) < 0.02) | (np.abs(xx - 0.5) < 0.015)
    col[bar] *= 0.15
    return image(name, col)


def wood_tex(name, base, size=512, planks=6):
    H = W = size
    xx = np.mgrid[0:H, 0:W][1]
    f = (xx % (W / planks)) / (W / planks)
    seam = np.where((f < 0.04) | (f > 0.96), 0.5, 1.0)
    grain = 0.85 + 0.15 * noise(H, W, 3, 7) + 0.1 * noise(H, W, 50, 8)
    col = hexrgb(base) * (seam * grain)[..., None]
    return image(name, col), normal_map(name + '_n', seam * 1.0)


# --- materials ----------------------------------------------------------------------

MATS = {}
def material(name, color='#808080', rough=0.8, metal=0.0, tex=None, nrm=None, scale=1.0, emit=None, emit_tex=None,
             emit_strength=1.0):
    """scale: metres per texture repeat (UVs are world-space)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = list(hexrgb(color) ** 2.2) + [1]
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if tex:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = tex
        nt.links.new(t.outputs['Color'], p.inputs['Base Color'])
    if nrm:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = nrm
        nm = nt.nodes.new('ShaderNodeNormalMap')
        nt.links.new(t.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    if emit or emit_tex:
        p.inputs['Emission Strength'].default_value = emit_strength
        if emit_tex:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = emit_tex
            nt.links.new(t.outputs['Color'], p.inputs['Emission Color'])
        else:
            p.inputs['Emission Color'].default_value = list(hexrgb(emit) ** 2.2) + [1]
    MATS[name] = (m, scale)
    return name


def make_materials():
    bt, bn = brick_tex('brick_red', '#7a3a28', soot=0.35)
    material('brick_red', tex=bt, nrm=bn, rough=0.9, scale=1.0)
    bt, bn = brick_tex('brick_brown', '#5e3b2c', soot=0.3)
    material('brick_brown', tex=bt, nrm=bn, rough=0.9, scale=1.0)
    bt, bn = brick_tex('brick_tan', '#9a7b5a', mortar='#a49c8a', soot=0.25)
    material('brick_tan', tex=bt, nrm=bn, rough=0.9, scale=1.0)
    for nm, paint in (('clap_cream', '#c9b98f'), ('clap_sage', '#7d8a6c'), ('clap_grey', '#7a8088'), ('clap_ochre', '#a8834a')):
        t, n = clapboard_tex(nm, paint)
        material(nm, tex=t, nrm=n, rough=0.85, scale=1.0)
    t, n = stone_tex('stone', '#8f8a7e')
    material('stone', tex=t, nrm=n, rough=0.85, scale=1.5)
    material('trim_cream', '#d8cdb0', rough=0.6)
    material('trim_dark', '#2b3329', rough=0.6)
    material('trim_maroon', '#4a2420', rough=0.6)
    material('iron', '#16171a', rough=0.45, metal=0.7)
    material('glass_dark', '#0a0e13', rough=0.06, metal=0.5)
    for i in range(3):
        material(f'glass_lit{i}', '#000000', rough=0.3, emit_tex=window_lit_tex(f'lit{i}', seed=i), emit_strength=2.2,
                 scale=1.0)
    t, n = wood_tex('door_wood', '#3a2618')
    material('door_wood', tex=t, nrm=n, rough=0.7, scale=1.2)
    t, n = wood_tex('crate_wood', '#6e5638', planks=4)
    material('crate_wood', tex=t, nrm=n, rough=0.9, scale=0.9)
    t, n = wood_tex('barrel_wood', '#5a4026', planks=10)
    material('barrel_wood', tex=t, nrm=n, rough=0.8, scale=1.0)
    material('sign_board', '#1d2a22', rough=0.5)
    material('sign_board_red', '#3d1612', rough=0.5)
    material('gilt', '#c79a3e', rough=0.3, metal=0.9)
    material('paint_faded', '#b9ad8f', rough=1.0)
    material('lamp_glass', '#000000', rough=0.2, emit='#ffcf8a', emit_strength=6.0)
    material('roof', '#1a1918', rough=0.9)
    material('tin', '#4c4e4a', rough=0.55, metal=0.6)


# --- geometry: one bmesh per material, world-space UVs --------------------------------

BM = {}
def bm_for(mat):
    if mat not in BM: BM[mat] = bmesh.new()
    return BM[mat]


def frame(o, r, n):
    """A local frame: origin o, right r, up (Y), out n. Returns a 4x4 (local u,v,w -> world x,y,z)."""
    r, n = Vector(r).normalized(), Vector(n).normalized()
    M = Matrix((r, UP, n)).transposed().to_4x4()
    M.translation = Vector(o)
    return M


def lbox(F, mat, u0, u1, v0, v1, w0, w1, rot=0.0):
    """Box in a facade frame F. rot turns it about the vertical through its centre."""
    c = Vector(((u0 + u1) / 2, (v0 + v1) / 2, (w0 + w1) / 2))
    S = Matrix.Diagonal((abs(u1 - u0), abs(v1 - v0), abs(w1 - w0), 1))
    M = F @ Matrix.Translation(c) @ Matrix.Rotation(rot, 4, 'Y') @ S
    bmesh.ops.create_cube(bm_for(mat), size=1.0, matrix=M)


def wbox(mat, x0, x1, y0, y1, z0, z1):
    lbox(Matrix.Identity(4), mat, x0, x1, y0, y1, z0, z1)


def cyl(mat, base, height, r0, r1=None, seg=12, axis=UP, cap=True):
    """Cylinder/cone from base along axis."""
    r1 = r0 if r1 is None else r1
    axis = Vector(axis).normalized()
    rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
    M = Matrix.Translation(Vector(base) + axis * height / 2) @ rot
    bmesh.ops.create_cone(bm_for(mat), cap_ends=cap, segments=seg, radius1=r0, radius2=r1, depth=height, matrix=M)
    for f in bm_for(mat).faces[-(seg + 2):]: f.smooth = True


def sphere(mat, c, r, seg=10):
    bmesh.ops.create_uvsphere(bm_for(mat), u_segments=seg, v_segments=max(4, seg // 2), radius=r,
                              matrix=Matrix.Translation(Vector(c)))


def tube(mat, pts, r, seg=6):
    """A thin rod through points (wires, rails, scrolls)."""
    for a, b in zip(pts, pts[1:]):
        a, b = Vector(a), Vector(b)
        d = b - a
        if d.length < 1e-4: continue
        cyl(mat, a, d.length, r, seg=seg, axis=d, cap=False)


def text(mat, s, F, u, v, w, size, align='CENTER', extrude=0.008):
    cu = bpy.data.curves.new('t', 'FONT')
    cu.body = s
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.size = size
    cu.align_x = align
    cu.align_y = 'CENTER'
    cu.extrude = extrude
    cu.resolution_u = 2  # signs are read from metres away; keep the letters light
    ob = bpy.data.objects.new('t', cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = F @ Matrix.Translation((u, v, w + extrude))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    # the font's letters have rough, inked edges: thousands of points each. Thin them out.
    tmp = bpy.data.objects.new('t', me)
    bpy.context.scene.collection.objects.link(tmp)
    dec = tmp.modifiers.new('thin', 'DECIMATE'); dec.ratio = 0.08
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    me2.transform(F @ Matrix.Translation((u, v, w + extrude)))
    bm_for(mat).from_mesh(me2)
    bpy.data.objects.remove(tmp); bpy.data.meshes.remove(me); bpy.data.meshes.remove(me2)


def finish(name):
    """Turn the per-material bmeshes into objects with world-space UVs, under one root."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for mat, bm in BM.items():
        m, scale = MATS[mat]
        uv = bm.loops.layers.uv.verify()
        bm.normal_update()
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in f.loops:
                co = loop.vert.co
                if ax == 0: loop[uv].uv = (co.z * (-1 if n.x > 0 else 1) / scale, co.y / scale)
                elif ax == 1: loop[uv].uv = (co.x / scale, co.z / scale)
                else: loop[uv].uv = (co.x * (1 if n.z > 0 else -1) / scale, co.y / scale)
        me = bpy.data.meshes.new(mat)
        bm.to_mesh(me); bm.free()
        me.materials.append(m)
        ob = bpy.data.objects.new(mat, me)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = root
    # game coordinates (Y up) -> Blender (Z up): +90 degrees about X
    root.rotation_euler = (math.pi / 2, 0, 0)
    return root


