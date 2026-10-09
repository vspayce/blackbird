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


def text(mat, s, F, u, v, w, size, align='CENTER', extrude=0.0):
    """Lettering on the plane w of frame F. Flat by default: the sides of extruded letters were three quarters
    of their triangles (Kearny's signs alone came to 28k) and nobody sees 8 mm of depth from the pavement."""
    w = w + (0.006 if not extrude else 0.0)  # flat letters float just off the board rather than z-fight with it
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


def gas_lamp(x, z, h=3.7, y=0.0):
    """San Francisco cast-iron gas lamp: plinth, fluted column, ladder bar, lantern, crown. y: ground height.
    About 300 triangles: a street has dozens, so the flutes are the column's eight facets, not eight rods."""
    i = 'iron'
    cyl(i, (x, 0 + y, z), 0.12, 0.2, 0.2, seg=8)
    cyl(i, (x, 0.12 + y, z), 0.45, 0.17, 0.12, seg=8)
    cyl(i, (x, 0.57 + y, z), 0.06, 0.14, 0.14, seg=8)
    cyl(i, (x, 0.63 + y, z), h - 1.35, 0.085, 0.06, seg=8, cap=False)
    yb = h - 0.72
    cyl(i, (x, yb + y, z), 0.06, 0.09, 0.09, seg=8)
    tube(i, [(x - 0.42, yb + 0.03 + y, z), (x + 0.42, yb + 0.03 + y, z)], 0.018, 4)  # the lamplighter's ladder bar
    for s in (-1, 1): sphere(i, (x + s * 0.43, yb + 0.03 + y, z), 0.03, 4)
    cyl(i, (x, yb + 0.06 + y, z), 0.12, 0.05, 0.11, seg=8)
    # lantern: four tapered panes, framed
    y0, y1 = yb + 0.18, yb + 0.62
    cyl('lamp_glass', (x, y0 + y, z), y1 - y0, 0.13, 0.2, seg=4, cap=True)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        tube(i, [(x + math.cos(a) * 0.13, y0 + y, z + math.sin(a) * 0.13), (x + math.cos(a) * 0.2, y1 + y, z + math.sin(a) * 0.2)], 0.012, 4)
    cyl(i, (x, y0 - 0.03 + y, z), 0.04, 0.15, 0.15, seg=4)
    cyl(i, (x, y1 + y, z), 0.05, 0.23, 0.23, seg=4)
    cyl(i, (x, y1 + 0.05 + y, z), 0.16, 0.24, 0.05, seg=4)  # crown
    cyl(i, (x, y1 + 0.21 + y, z), 0.1, 0.04, 0.01, seg=6)  # the finial
    return Vector((x, (y0 + y1) / 2 + y, z))


def canvas(mat, corners, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    """A quad whose texture is fitted to it (a painting, a rug, a mirror), not tiled by the metre.
    Register its material with scale=None so finish() leaves these UVs alone."""
    bm = bm_for(mat)
    layer = bm.loops.layers.uv.verify()
    f = bm.faces.new([bm.verts.new(Vector(c)) for c in corners])
    for loop, t in zip(f.loops, uv):
        loop[layer].uv = t
    return f



# --- pieces ---------------------------------------------------------------------------

def bracket_lamp(x_wall, y, z, out=1):
    """Gas lamp on a scrolled iron bracket off a wall (out = +1 to stick out along +x)."""
    i = 'iron'
    wbox(i, x_wall - 0.02 * out, x_wall + 0.03 * out, y - 0.25, y + 0.25, z - 0.1, z + 0.1)
    arm = [(x_wall + out * d, y + 0.05 * math.sin(d * 4), z) for d in np.linspace(0, 0.65, 8)]
    tube(i, arm, 0.02)
    scroll = [(x_wall + out * (0.05 + 0.25 * t), y - 0.35 + 0.35 * t ** 0.5, z) for t in np.linspace(0, 1, 7)]
    tube(i, scroll, 0.015)
    lx = x_wall + out * 0.65
    tube(i, [(lx, y + 0.05, z), (lx, y - 0.1, z)], 0.012)
    y1 = y - 0.1
    cyl(i, (lx, y1 - 0.04, z), 0.04, 0.12, 0.12, seg=4)
    cyl('lamp_glass', (lx, y1 - 0.4, z), 0.36, 0.08, 0.12, seg=4)
    cyl(i, (lx, y1 - 0.44, z), 0.04, 0.09, 0.09, seg=4)
    sphere(i, (lx, y1 - 0.5, z), 0.025, 6)
    return Vector((lx, y1 - 0.22, z))


def window(F, u, v, w=0.95, h=1.75, lit=None, frame_mat='trim_cream', hood='cornice', sill='stone', shutters=False):
    """A double-hung sash window centred at u with its sill at v, on the facade plane (w=0 is the wall face)."""
    lit = rnd.random() < 0.18 if lit is None else lit
    glass = f'glass_lit{rnd.randrange(3)}' if lit else 'glass_dark'
    # the glass sits just proud of the wall face, set back inside a deeper frame
    lbox(F, glass, u - w / 2, u + w / 2, v, v + h, 0.004, 0.012)
    t = 0.07
    lbox(F, frame_mat, u - w / 2 - t, u - w / 2, v, v + h, 0, 0.07)
    lbox(F, frame_mat, u + w / 2, u + w / 2 + t, v, v + h, 0, 0.07)
    lbox(F, frame_mat, u - w / 2, u + w / 2, v + h - t, v + h, 0, 0.07)
    lbox(F, frame_mat, u - w / 2, u + w / 2, v + h / 2 - 0.03, v + h / 2 + 0.03, 0, 0.045)  # meeting rail
    lbox(F, frame_mat, u - 0.015, u + 0.015, v, v + h, 0, 0.035)  # glazing bar
    lbox(F, sill, u - w / 2 - 0.12, u + w / 2 + 0.12, v - 0.08, v, 0, 0.14)
    if hood == 'cornice':
        lbox(F, frame_mat, u - w / 2 - 0.1, u + w / 2 + 0.1, v + h, v + h + 0.22, 0, 0.06)
        lbox(F, frame_mat, u - w / 2 - 0.16, u + w / 2 + 0.16, v + h + 0.22, v + h + 0.3, 0, 0.16)
    elif hood == 'lintel':
        lbox(F, sill, u - w / 2 - 0.1, u + w / 2 + 0.1, v + h, v + h + 0.24, 0, 0.05)
        lbox(F, sill, u - 0.08, u + 0.08, v + h, v + h + 0.3, 0, 0.07)  # keystone
    if shutters:  # iron fire shutters, closed
        for s in (-1, 1):
            lbox(F, 'iron', u + s * w / 4 - w / 4, u + s * w / 4 + w / 4, v + 0.02, v + h - 0.02, 0.05, 0.08)


def corbel(F, mat, u, v_top, depth, width=0.12):
    """A stepped bracket tapering down from v_top. Two steps: there are hundreds along a street front."""
    for a, b, d in ((0.0, 0.16, 1.0), (0.16, 0.42, 0.5)):
        lbox(F, mat, u - width / 2, u + width / 2, v_top - b, v_top - a, 0, depth * d)


def bay_window(F, u, v0, v1, width=2.2, depth=0.65, wall='clap_cream', trim='trim_cream'):
    """The San Francisco bay: three-sided, from v0 up to v1, with a corbelled base and a cornice cap."""
    sw = depth * math.sqrt(2)
    fw = width - 2 * depth
    # angled sides and front as thin wall slabs
    lbox(F, wall, u - fw / 2, u + fw / 2, v0, v1, depth - 0.1, depth)
    for s in (-1, 1):
        cu = u + s * (fw / 2 + depth / 2)
        lbox(F, wall, cu - sw / 2, cu + sw / 2, v0, v1, depth / 2 - 0.05, depth / 2 + 0.05, rot=s * math.pi / 4)
    # floor plate, brackets under it, cap and cornice over it
    for v, d in ((v0, 0.12), (v1, 0.12)):
        lbox(F, trim, u - width / 2, u + width / 2, v - d, v, 0, depth + 0.06)
    for k in (-1, -0.33, 0.33, 1):
        corbel(F, trim, u + k * (width / 2 - 0.15), v0 - 0.12, depth * 0.9)
    lbox(F, trim, u - width / 2 - 0.08, u + width / 2 + 0.08, v1, v1 + 0.18, -0.02, depth + 0.16)
    floors = max(1, round((v1 - v0) / 3.2))
    fh = (v1 - v0) / floors
    for f in range(floors):
        sv = v0 + f * fh + 0.75
        hh = min(1.7, fh - 1.0)
        # front window
        Ff = F @ Matrix.Translation((0, 0, depth))
        window(Ff, u, sv, w=fw - 0.35, h=hh, frame_mat=trim, hood=None, sill=trim)
        for s in (-1, 1):
            cu = u + s * (fw / 2 + depth / 2)
            Fs = F @ Matrix.Translation((cu, 0, depth / 2 + 0.05)) @ Matrix.Rotation(s * math.pi / 4, 4, 'Y')
            window(Fs, 0, sv, w=sw - 0.3, h=hh, frame_mat=trim, hood=None, sill=trim)


def cornice(F, u0, u1, top, trim='trim_cream', depth=0.55):
    """A bracketed Italianate cornice along the top of a front."""
    lbox(F, trim, u0, u1, top - 0.9, top - 0.45, 0, 0.06)  # frieze
    lbox(F, trim, u0 - 0.1, u1 + 0.1, top - 0.45, top - 0.35, 0, 0.18)
    lbox(F, trim, u0 - 0.15, u1 + 0.15, top - 0.2, top, 0, depth)
    lbox(F, trim, u0 - 0.12, u1 + 0.12, top - 0.28, top - 0.2, 0, depth * 0.75)
    n = int((u1 - u0) / 1.0)
    for k in range(n + 1):
        u = u0 + 0.2 + k * (u1 - u0 - 0.4) / max(1, n)
        corbel(F, trim, u, top - 0.28, depth * 0.75, 0.1)


def storefront(F, u0, u1, sign, sign_mat='sign_board', door_at=0.5, iron='iron', h=3.6, lit=None):
    """Cast-iron shopfront: pilasters, plate glass over a panelled bulkhead, transoms, a recessed door, a sign."""
    n = max(2, int((u1 - u0) / 3.2))
    bw = (u1 - u0) / n
    door_bay = min(n - 1, int(n * door_at))
    lit = rnd.random() < 0.35 if lit is None else lit
    for k in range(n + 1):
        u = u0 + k * bw
        lbox(F, iron, u - 0.16, u + 0.16, 0, h, 0, 0.16)
        lbox(F, iron, u - 0.2, u + 0.2, h - 0.25, h, 0, 0.22)  # capital
        lbox(F, iron, u - 0.2, u + 0.2, 0, 0.3, 0, 0.22)  # base
    # the shopfront stands 0.3 m proud of the wall: pilasters to w = 0.3, glass at 0.2, doors set back at 0.02
    for k in range(n):
        a, b = u0 + k * bw + 0.16, u0 + (k + 1) * bw - 0.16
        if k == door_bay:  # recessed door with a glazed upper half and transom
            lbox(F, 'door_wood', a + 0.35, b - 0.35, 0, 2.5, 0.0, 0.05)
            lbox(F, 'glass_lit0' if lit else 'glass_dark', a + 0.5, b - 0.5, 1.3, 2.3, 0.05, 0.06)
            for s in (a, b - 0.35):
                lbox(F, 'door_wood', s, s + 0.35, 0, 2.6, 0.0, 0.26)
            lbox(F, 'door_wood', a, b, 2.5, 2.65, 0.0, 0.26)
            lbox(F, 'glass_dark', a, b, 2.65, h - 0.3, 0.18, 0.2)
            lbox(F, 'stone', a, b, 0, 0.12, 0.0, 0.32)
            continue
        lbox(F, 'door_wood', a, b, 0, 0.6, 0, 0.26)  # bulkhead
        lbox(F, iron, a, b, 0.6, 0.68, 0, 0.27)
        lbox(F, f'glass_lit{k % 3}' if lit else 'glass_dark', a, b, 0.68, 2.65, 0.19, 0.21)
        lbox(F, iron, a, b, 2.65, 2.72, 0, 0.26)
        lbox(F, 'glass_dark', a, b, 2.72, h - 0.3, 0.19, 0.21)
        lbox(F, iron, (a + b) / 2 - 0.02, (a + b) / 2 + 0.02, 2.72, h - 0.3, 0.19, 0.24)
        lbox(F, 'roof', a, b, 0.68, h - 0.3, 0.0, 0.02)  # the dark shop interior behind the glass
    # sign band and ledge
    lbox(F, sign_mat, u0 + 0.2, u1 - 0.2, h + 0.05, h + 0.75, 0, 0.3)
    lbox(F, 'trim_cream', u0, u1, h + 0.75, h + 0.88, 0, 0.45)
    lbox(F, 'trim_cream', u0, u1, h, h + 0.05, 0, 0.4)
    if sign:
        text('gilt', sign, F, (u0 + u1) / 2, h + 0.4, 0.3, min(0.5, (u1 - u0 - 0.8) / max(4, len(sign)) * 1.55))


def front(F, u0, u1, height, wall, trim, sign, bays=(), floors=(4.6, 7.8, 11.0), sign_mat='sign_board',
          windows_per=2.6, lit=None):
    """A whole street front in frame F between u0 and u1 (wall face at w=0)."""
    storefront(F, u0, u1, sign, sign_mat, lit=lit)
    taken = [(c - 1.3, c + 1.3) for c in bays]
    for c in bays:  # bays start above the shop sign's ledge so their corbels clear it
        bay_window(F, c, 5.0, min(height - 1.2, 5.0 + 3.2 * sum(1 for f in floors if f < height - 2)),
                   wall=wall, trim=trim)
    for fv in floors:
        if fv > height - 2.4: break
        n = int((u1 - u0) / windows_per)
        for k in range(n):
            u = u0 + (k + 0.5) * (u1 - u0) / n
            if any(a - 0.6 < u < b + 0.6 for a, b in taken): continue
            window(F, u, fv, frame_mat=trim)
        lbox(F, trim, u0, u1, fv - 0.55, fv - 0.42, 0, 0.08)  # belt course
    cornice(F, u0, u1, height, trim)


def alley_wall(F, u0, u1, height, floors, windows, door=None, base='stone'):
    """The plain brick side of a building facing the alley: base course, string courses, windows, a door."""
    lbox(F, base, u0, u1, 0, 0.55, 0, 0.06)
    for fv in floors:
        lbox(F, 'stone', u0, u1, fv - 0.5, fv - 0.38, 0, 0.05)
    for u, fv, kind in windows:
        if kind == 'barred':
            window(F, u, fv, w=0.7, h=0.9, hood='lintel', frame_mat='trim_dark', lit=False)
            for k in range(5):
                lbox(F, 'iron', u - 0.3 + k * 0.15 - 0.01, u - 0.3 + k * 0.15 + 0.01, fv, fv + 0.9, 0.06, 0.08)
        else:
            window(F, u, fv, w=0.9, h=1.6, hood='lintel', frame_mat='trim_dark', shutters=(kind == 'shut'),
                   lit=(kind == 'lit'))
    if door is not None:  # a back door: frame, transom, stone step
        lbox(F, 'trim_dark', door - 0.68, door + 0.68, 0, 2.55, 0, 0.08)
        lbox(F, 'door_wood', door - 0.55, door + 0.55, 0.15, 2.3, 0.02, 0.1)
        lbox(F, 'glass_dark', door - 0.5, door + 0.5, 2.32, 2.5, 0.06, 0.09)
        lbox(F, 'stone', door - 0.7, door + 0.7, 0, 0.15, 0, 0.45)
        lbox(F, 'stone', door - 0.75, door + 0.75, 2.55, 2.75, 0, 0.1)
        sphere('iron', F @ Vector((door + 0.4, 1.15, 0.12)), 0.035, 8)
    # coping along the roofline
    lbox(F, 'stone', u0, u1, height - 0.25, height, 0, 0.12)


def drainpipe(x, z, top, out):
    i = 'tin'
    cyl(i, (x, 0.25, z), top - 0.25, 0.055, seg=8)
    cyl(i, (x, top, z), 0.25, 0.09, 0.055, seg=8)  # hopper head
    for y in np.arange(1.2, top, 1.6):
        wbox(i, x - 0.07, x + 0.07, y, y + 0.04, z - 0.07, z + 0.07)
    tube(i, [(x, 0.25, z), (x + out * 0.18, 0.06, z)], 0.055, 8)


def fire_escape(F, u0, u1, levels, ladder_u):
    i = 'iron'
    for v in levels:
        lbox(F, i, u0, u1, v - 0.04, v, 0, 0.95)  # grating
        for k in np.arange(u0, u1 + 0.01, 0.25):
            lbox(F, i, k - 0.01, k + 0.01, v, v + 0.95, 0.92, 0.94)
        lbox(F, i, u0, u1, v + 0.93, v + 0.97, 0.9, 0.96)
        for s in (u0, u1):
            for w in np.arange(0.1, 0.95, 0.2):
                lbox(F, i, s - 0.01, s + 0.01, v, v + 0.95, w, w + 0.02)
            lbox(F, i, s - 0.02, s + 0.02, v + 0.93, v + 0.97, 0, 0.95)
        # diagonal braces down to the wall
        for s in (u0 + 0.2, u1 - 0.2):
            tube(i, [F @ Vector((s, v - 0.04, 0.9)), F @ Vector((s, v - 0.9, 0.02))], 0.015)
    for a, b in zip(levels, levels[1:]):  # ladders between platforms
        for s in (-0.22, 0.22):
            tube(i, [F @ Vector((ladder_u + s, a, 0.5)), F @ Vector((ladder_u + s, b + 0.9, 0.85))], 0.015)
        for t in np.linspace(0.05, 0.95, 9):
            p0 = F @ Vector((ladder_u - 0.22, a + t * (b + 0.9 - a), 0.5 + t * 0.35))
            p1 = F @ Vector((ladder_u + 0.22, a + t * (b + 0.9 - a), 0.5 + t * 0.35))
            tube(i, [p0, p1], 0.01)
    # the drop ladder, hooked up out of reach
    for s in (-0.22, 0.22):
        tube(i, [F @ Vector((ladder_u + s, levels[0] - 1.6, 0.9)), F @ Vector((ladder_u + s, levels[0], 0.9))], 0.015)


def wire(a, b, sag=0.6, seg=10):
    pts = []
    for k in range(seg + 1):
        t = k / seg
        p = Vector(a).lerp(Vector(b), t)
        p.y -= sag * 4 * t * (1 - t)
        pts.append(p)
    tube('iron', pts, 0.008, seg=4)


def barrel(x, z, h=0.95, r=0.32):
    cyl('barrel_wood', (x, 0, z), h / 2, r * 0.9, r, seg=16)
    cyl('barrel_wood', (x, h / 2, z), h / 2, r, r * 0.9, seg=16)
    for y in (0.08, 0.3, h - 0.3, h - 0.08):
        k = 1 - abs(y - h / 2) / (h / 2) * 0.1
        cyl('iron', (x, y - 0.02, z), 0.04, r * k + 0.008, seg=16, cap=False)


def ash_can(x, z):
    cyl('tin', (x, 0, z), 0.75, 0.27, 0.3, seg=14)
    cyl('tin', (x, 0.75, z), 0.05, 0.31, seg=14)
    cyl('tin', (x, 0.8, z), 0.03, 0.06, seg=8)


def crate(x, y, z, s, rot=0.0):
    F = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Y')
    h = s / 2
    lbox(F, 'crate_wood', -h + 0.02, h - 0.02, -h + 0.02, h - 0.02, -h + 0.02, h - 0.02)
    for a in (-1, 1):  # corner battens
        for b in (-1, 1):
            lbox(F, 'crate_wood', a * h - 0.05 * (a > 0) - 0.0 * (a < 0) - (0 if a > 0 else -0.05) - 0.05, a * h,
                 -h, h, b * h - 0.05, b * h) if False else None
    for b in (-1, 1):
        lbox(F, 'crate_wood', -h, h, -h, h, b * h - 0.03 * b, b * h + 0.01 * b) if False else None
    # slats proud of the faces, top and middle bands
    for v in (-h + 0.06, 0, h - 0.06):
        lbox(F, 'crate_wood', -h, h, v - 0.04, v + 0.04, -h - 0.01, h + 0.01)
        lbox(F, 'crate_wood', -h - 0.01, h + 0.01, v - 0.04, v + 0.04, -h, h)


def finish(name):
    """Turn the per-material bmeshes into objects with world-space UVs, under one root."""
    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    for mat, bm in BM.items():
        m, scale = MATS[mat]
        uv = bm.loops.layers.uv.verify()
        bm.normal_update()
        for f in (bm.faces if scale else []):  # scale None: UVs were fitted when the faces were made
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


