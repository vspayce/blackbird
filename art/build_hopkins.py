# Builds the Mark Hopkins Institute of Art (the Hopkins mansion, Nob Hill, 1895).
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_hopkins.py -- [--render out]
#
# Writes art/set/hopkins.blend, public/models/hopkins.glb and
# public/models/hopkins.json (colliders, rooms, lamps, spawn and interactions
# for src/world/hopkins.js).
#
# What is known: Wright & Sanders, finished 1878 at California and Mason; a
# crenellated Gothic "castle" built of wood painted to look like stone, with
# turrets, porches, a curved drive and porte-cochere, and a tower then the
# highest point in the city. Herter Brothers interiors: a several-storey entry
# hall used as an art gallery, a pipe organ, a music room frescoed in the
# medieval manner, a Louis XIV drawing room, a dining room of weathered English
# oak, a rosewood reception room with English Gothic frescoes, a Moorish room
# and a black walnut library. From 1893 the San Francisco Art Association ran it
# as the Mark Hopkins Institute of Art.
#
# What is invented: the floor plan (no plan survives that we could find), the
# exact massing, and the school's use of each room (studio, archive, office).
#
# Layout, game coordinates (Y up, metres): the front faces +z onto the drive and
# California Street; the city falls away behind (-z) to the bay.
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setkit import *  # noqa: F401,F403

COLLIDERS = []      # [x0, y0, z0, x1, y1, z1]
LAMPS = []          # [x, y, z]
ROOMS = []          # {id, name, x0, z0, x1, z1, y}
INTERACT = []       # {id, label, pos, r, ...}

H = 5.5             # ground floor ceiling
D = 1.8             # door width
DH = 3.4            # door height
UF = 6.0            # the upper floor (level with the hall's gallery)
UC = 11.0           # its ceiling
UPPER_DOORS = []    # (x, z, axis) doorways on the upper floor, axis 'x' for walls running along x
UPPER_WINDOWS = []  # (x, z, axis) window openings in the upper storey's outer walls
STAIRS = []         # walkable stair runs: [x0, x1, z0, z1, axis, y at the low end, y at the high end]
LEVELS = []         # walkable floors above the ground: {y, rects: [[x0, x1, z0, z1]]}
HALL_H = 14.0       # the hall rises through the house
T = 0.35            # wall thickness


def outward(A, B, centre):
    """The horizontal normal of wall AB pointing away from centre."""
    r = (B - A).normalized()
    n = Vector((r.z, 0, -r.x))
    return n if n.dot((A + B) / 2 - centre) > 0 else -n


def collide(x0, y0, z0, x1, y1, z1):
    COLLIDERS.append([round(min(x0, x1), 3), round(min(y0, y1), 3), round(min(z0, z1), 3),
                      round(max(x0, x1), 3), round(max(y0, y1), 3), round(max(z0, z1), 3)])


# --- extra textures ----------------------------------------------------------------

def ashlar_tex(name, base='#9a978e', size=1024, rows=4, per_row=2):
    """Wood scored and painted to pass for dressed stone: big blocks, fine joints."""
    rng = np.random.default_rng(11)
    Hh = W = size
    yy, xx = np.mgrid[0:Hh, 0:W]
    rh = Hh / rows
    row = (yy / rh).astype(int)
    off = (row % 2) * (W / per_row / 2)
    fx = ((xx + off) % (W / per_row)) / (W / per_row)
    fy = (yy % rh) / rh
    joint = (fy < 0.015) | (fx < 0.008)
    ids = row * 31 + ((xx + off) / (W / per_row)).astype(int)
    tone = 0.92 + 0.12 * rng.random(rows * 31 + per_row + 2)[ids]
    col = hexrgb(base) * (tone * (0.9 + 0.12 * noise(Hh, W, 30, 2) + 0.06 * noise(Hh, W, 4, 3)))[..., None]
    col[joint] *= 0.55
    height = np.where(joint, 0.0, 1.0) + noise(Hh, W, 6, 4) * 0.1
    return image(name, col), normal_map(name + '_n', height * 2)


def slate_tex(name, size=512):
    Hh = W = size
    yy, xx = np.mgrid[0:Hh, 0:W]
    rows = 10
    row = (yy / (Hh / rows)).astype(int)
    off = (row % 2) * (W / 8 / 2)
    fx = ((xx + off) % (W / 8)) / (W / 8)
    fy = (yy % (Hh / rows)) / (Hh / rows)
    rng = np.random.default_rng(5)
    tone = 0.8 + 0.3 * rng.random(rows * 40)[row * 9 + ((xx + off) / (W / 8)).astype(int)]
    col = hexrgb('#3b4148') * (tone * (0.55 + 0.45 * fy) * np.where(fx < 0.03, 0.6, 1.0))[..., None]
    return image(name, col), normal_map(name + '_n', fy * 1.5)


def marble_tex(name, size=1024, tiles=2):
    """Black and white marble squares with veining."""
    Hh = W = size
    yy, xx = np.mgrid[0:Hh, 0:W]
    t = ((yy * tiles // Hh) + (xx * tiles // W)) % 2 if tiles > 1 else np.zeros((Hh, W), int)
    vein = np.abs(np.sin((xx + noise(Hh, W, 40, 1) * 300 + yy * 0.6) / 18))
    vein = np.clip(1 - vein * 4, 0, 1) * noise(Hh, W, 80, 2)
    white = np.array([0.88, 0.86, 0.82]) * (1 - 0.25 * vein[..., None])
    black = np.array([0.07, 0.07, 0.08]) + 0.15 * vein[..., None]
    col = np.where(t[..., None] == 0, white, black)
    seam = ((yy % (Hh // tiles)) < 2) | ((xx % (W // tiles)) < 2)
    col[seam] *= 0.6
    return image(name, col)


def parquet_tex(name, base='#5a3a22', size=1024):
    """Herringbone oak."""
    Hh = W = size
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    s = 64
    a = ((xx + yy) // s).astype(int)
    b = ((xx - yy) // s).astype(int)
    pick = (a + b) % 2
    plank = np.where(pick == 0, (xx - yy) % (s * 0.5), (xx + yy) % (s * 0.5))
    seam = (plank < 2.0)
    rng = np.random.default_rng(3)
    tone = 0.8 + 0.3 * rng.random(4096)[(a * 37 + b * 11) % 4096]
    grain = 0.9 + 0.1 * noise(Hh, W, 4, 5)
    col = hexrgb(base) * (tone * grain)[..., None]
    col[seam] *= 0.5
    return image(name, col), normal_map(name + '_n', np.where(seam, 0.0, 1.0))


def panel_tex(name, base, size=512):
    """Raised wood panelling: stiles, rails and fielded panels, with inlaid dark lines (ebony stringing)."""
    Hh = W = size
    yy, xx = np.mgrid[0:Hh, 0:W] / size
    fx, fy = (xx * 2) % 1, yy % 1
    inner = (fx > 0.14) & (fx < 0.86) & (fy > 0.12) & (fy < 0.88)
    bevel = np.minimum(np.minimum(fx - 0.14, 0.86 - fx), np.minimum(fy - 0.12, 0.88 - fy))
    grain = 0.85 + 0.2 * noise(Hh, W, 3, 7) + 0.1 * np.sin(yy * 300 + noise(Hh, W, 20, 8) * 8)
    col = hexrgb(base) * grain[..., None]
    string = inner & (bevel < 0.02) & (bevel > 0.012)
    col[string] = hexrgb('#0c0806')
    height = np.where(inner, np.clip(bevel * 20, 0, 1), 0.0)
    return image(name, col), normal_map(name + '_n', height * 3)


def fresco_tex(name, ground, ink, size=512, motif='gothic'):
    """Stencilled wall decoration: a diaper of quatrefoils (Gothic), stars (Moorish) or fleurs (Louis)."""
    Hh = W = size
    yy, xx = np.mgrid[0:Hh, 0:W] / size * 4
    fx, fy = xx % 1 - 0.5, yy % 1 - 0.5
    r = np.hypot(fx, fy)
    a = np.arctan2(fy, fx)
    if motif == 'gothic':
        shape = r < 0.22 + 0.08 * np.cos(4 * a)
        ring = np.abs(r - (0.3 + 0.06 * np.cos(4 * a))) < 0.025
        m = shape ^ (r < 0.12) | ring
    elif motif == 'moorish':
        star = r < 0.2 + 0.12 * np.cos(8 * a)
        lattice = (np.abs(np.abs(fx) - np.abs(fy)) < 0.03) & (r > 0.25)
        m = star ^ (r < 0.1) | lattice
    else:
        m = (r < 0.12 + 0.1 * np.abs(np.cos(1.5 * a))) & (fy < 0.15)
    aged = 0.85 + 0.2 * noise(Hh, W, 50, 9)
    col = np.where(m[..., None], hexrgb(ink), hexrgb(ground)) * aged[..., None]
    return image(name, col)


def books_tex(name, size=512):
    """Shelves of bound volumes: spines in leathers and cloths, gilt bands, the odd gap."""
    rng = np.random.default_rng(17)
    Hh = W = size
    col = np.zeros((Hh, W, 3), np.float32)
    shelves = 4
    sh = Hh // shelves
    palette = [hexrgb(c) for c in ('#5a1e18', '#2b3a2a', '#3a2a1a', '#6b4a2a', '#1e2638', '#4a3a2a', '#702a1a', '#2a2a2a')]
    for s in range(shelves):
        y0 = s * sh
        col[y0:y0 + 6] = hexrgb('#24160c')  # shelf edge
        x = 2
        while x < W:
            w = rng.integers(7, 18)
            h = int(sh * rng.uniform(0.65, 0.92))
            c = palette[rng.integers(len(palette))] * rng.uniform(0.7, 1.2)
            if rng.random() < 0.04:
                x += w; continue
            col[y0 + sh - h:y0 + sh, x:x + w - 1] = c
            for band in (0.12, 0.2, 0.8):
                yb = y0 + sh - int(h * band)
                col[yb:yb + 2, x:x + w - 1] = hexrgb('#b08a3e')
            x += w
        col[y0 + 6:y0 + sh][col[y0 + 6:y0 + sh].sum(-1) == 0] = hexrgb('#0d0806')
    return image(name, col * (0.9 + 0.1 * noise(Hh, W, 3, 2))[..., None])


def stained_tex(name, size=256):
    """Leaded glass: diamond quarries in muted amber and pale glass, a border of deeper jewel colours."""
    rng = np.random.default_rng(23)
    H = W = size
    yy, xx = np.mgrid[0:H, 0:W] / size
    a, b = (xx + yy) * 8, (xx - yy) * 8
    cell = (np.floor(a).astype(int) * 31 + np.floor(b).astype(int) * 17) % 97
    lead = (np.abs(a - np.round(a)) < 0.06) | (np.abs(b - np.round(b)) < 0.06)
    pale = np.array([hexrgb('#c8b88a'), hexrgb('#b8a46a'), hexrgb('#d0c49c'), hexrgb('#a89458')])
    col = pale[cell % 4] * (0.8 + 0.3 * rng.random(97)[cell])[..., None]
    jewel = np.array([hexrgb('#6a1a14'), hexrgb('#1e3a6a'), hexrgb('#2a5a34'), hexrgb('#8a6a1a')])
    edge = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy)) < 0.09
    col[edge] = jewel[(cell % 4)][edge]
    col[lead | (np.abs(np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy)) - 0.09) < 0.012)] = 0.04
    return image(name, col * (0.85 + 0.2 * noise(H, W, 8, 2))[..., None])


def hopkins_materials():
    make_materials()
    t, n = ashlar_tex('ashlar'); material('ashlar', tex=t, nrm=n, rough=0.85, scale=2.4)
    t, n = slate_tex('slate'); material('slate', tex=t, nrm=n, rough=0.7, scale=1.6)
    t = marble_tex('marble'); material('marble', tex=t, rough=0.18, scale=1.6)
    t = marble_tex('marble_white', tiles=1); material('marble_white', tex=t, rough=0.2, scale=3.0)
    t, n = parquet_tex('parquet'); material('parquet', tex=t, nrm=n, rough=0.35, scale=2.0)
    for nm, base in (('oak_panel', '#5a3c22'), ('walnut_panel', '#2e1c12'), ('rosewood_panel', '#4a1e16'),
                     ('ebony_panel', '#1a1210')):
        t, n = panel_tex(nm, base); material(nm, tex=t, nrm=n, rough=0.45, scale=1.4)
    for nm, g, i, m in (('fresco_gothic', '#6a4a2a', '#b08a4a', 'gothic'), ('fresco_moorish', '#1e3a4a', '#c8a050', 'moorish'),
                        ('fresco_louis', '#c8bca0', '#a08048', 'louis'), ('fresco_red', '#5a1a14', '#a0703a', 'gothic'),
                        ('fresco_green', '#2a3a2a', '#9a8a5a', 'gothic')):
        material(nm, tex=fresco_tex(nm, g, i, motif=m), rough=0.9, scale=1.2)
    material('books', tex=books_tex('books'), rough=0.8, scale=2.0)
    material('stained', '#000000', emit_tex=stained_tex('stained'), emit_strength=1.1, rough=0.3, scale=1.2)
    material('gilt_frame', '#b08a3a', rough=0.35, metal=0.9)
    material('plaster', '#4a3a2c', rough=0.9)  # bare wall cores: dark, in case any shows
    material('plaster_cast', '#e6e0d2', rough=0.7)
    material('velvet_red', '#5a1014', rough=0.95)
    material('velvet_green', '#1e3a2a', rough=0.95)
    material('brass', '#b8903e', rough=0.3, metal=0.9)
    material('organ_pipe', '#c9a44a', rough=0.25, metal=1.0)
    material('grass', '#1c2a16', rough=1.0)
    material('gravel', '#5a564c', rough=1.0)
    material('granite', '#6a6a66', rough=0.8)
    material('palm', '#1e3a1a', rough=0.8)
    material('glass_clear', '#0c1218', rough=0.04, metal=0.6)
    material('canvas', '#d8d0bc', rough=0.95)
    material('candle', '#000000', emit='#ffc070', emit_strength=5.0)


# --- building blocks -----------------------------------------------------------------

def wall(a, b, y0, y1, openings=(), mat='plaster', thick=T, solid=True):
    """A straight wall from a to b ((x, z) pairs) with openings [(t from a in metres, width, bottom, top)]."""
    a, b = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
    d = b - a
    L = d.length
    r = d.normalized()
    n = Vector((-r.z, 0, r.x))
    F = frame(a, r, n)
    cuts = sorted(openings)
    u = 0.0
    for t, w, ob, ot in cuts + [(L + 10, 0, 0, 0)]:
        u1 = min(L, t - w / 2)
        if u1 > u:
            lbox(F, mat, u, u1, y0, y1, -thick / 2, thick / 2)
            if solid: collide_seg(F, u, u1, y0, y1, thick)
        if t > L: break
        if ob > y0:
            lbox(F, mat, t - w / 2, t + w / 2, y0, ob, -thick / 2, thick / 2)
            if solid and ob > 0.5: collide_seg(F, t - w / 2, t + w / 2, y0, ob, thick)
        if ot < y1:
            lbox(F, mat, t - w / 2, t + w / 2, ot, y1, -thick / 2, thick / 2)
            if solid: collide_seg(F, t - w / 2, t + w / 2, ot, y1, thick)  # above a door: solid to anyone up a stair
        u = t + w / 2
    return F, L


def collide_local(F, u0, u1, v0, v1, w0, w1):
    """Collider round a box given in a piece's own frame. Takes all eight corners: two opposite corners alone
    collapse to a sliver when the piece is turned off the axes (an angled wingback you could walk through)."""
    ps = [F @ Vector((u, v, w)) for u in (u0, u1) for v in (v0, v1) for w in (w0, w1)]
    collide(min(p.x for p in ps), min(p.y for p in ps), min(p.z for p in ps),
            max(p.x for p in ps), max(p.y for p in ps), max(p.z for p in ps))


def collide_seg(F, u0, u1, v0, v1, thick):
    p0 = F @ Vector((u0, v0, -thick / 2)); p1 = F @ Vector((u1, v1, thick / 2))
    collide(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z)


def lining(F, L, side, openings, y_top, wains='oak_panel', upper='fresco_gothic', frieze='gilt_frame', w_h=1.3, thick=T,
           curtains=None, head='gothic', trim='trim_dark'):
    """Dress one face of a wall: panelled wainscot, a dado rail, decorated upper wall, a cornice.
    side = +1 for the face the frame's normal points to, -1 for the other."""
    off = side * (thick / 2)
    Fs = F @ Matrix.Translation((0, 0, off)) if side > 0 else F @ Matrix.Translation((L, 0, off)) @ Matrix.Rotation(math.pi, 4, 'Y')
    ops = sorted(openings) if side > 0 else sorted([(L - t, w, b, tp) for t, w, b, tp in openings])
    u = 0.0
    for t, w, ob, ot in ops + [(L + 10, 0, 0, 0)]:
        u1 = min(L, t - w / 2)
        if u1 > u:
            lbox(Fs, wains, u, u1, 0, w_h, 0, 0.03)
            lbox(Fs, trim, u, u1, w_h, w_h + 0.08, 0, 0.06)
            lbox(Fs, upper, u, u1, w_h + 0.08, y_top - 0.5, 0, 0.012)
            lbox(Fs, frieze, u, u1, y_top - 0.5, y_top - 0.42, 0, 0.05)
            lbox(Fs, trim, u, u1, y_top - 0.42, y_top, 0, 0.14)
            lbox(Fs, trim, u, u1, 0, 0.18, 0, 0.05)  # skirting
        if t > L: break
        # door or window surround
        lbox(Fs, trim, t - w / 2 - 0.12, t - w / 2, max(0, ob - 0.05), ot + 0.12, 0, 0.06)
        lbox(Fs, trim, t + w / 2, t + w / 2 + 0.12, max(0, ob - 0.05), ot + 0.12, 0, 0.06)
        lbox(Fs, trim, t - w / 2 - 0.12, t + w / 2 + 0.12, ot, ot + 0.12, 0, 0.06)
        if head == 'gothic':  # a pointed Gothic head over the opening
            for s in (-1, 1):
                lbox(Fs, 'trim_dark', t + s * w / 4 - w / 4 - 0.02, t + s * w / 4 + w / 4 + 0.02, ot + 0.12 + w * 0.12, ot + 0.24 + w * 0.12,
                     0, 0.05, rot=0)
        elif head == 'cornice':  # a classical frieze and moulded cornice over the architrave
            lbox(Fs, trim, t - w / 2 - 0.12, t + w / 2 + 0.12, ot + 0.12, ot + 0.36, 0, 0.04)
            lbox(Fs, trim, t - w / 2 - 0.22, t + w / 2 + 0.22, ot + 0.36, ot + 0.44, 0, 0.12)
            lbox(Fs, 'gilt_frame', t - w / 2 - 0.2, t + w / 2 + 0.2, ot + 0.33, ot + 0.36, 0, 0.07)
        if ot + 0.12 < y_top - 0.5:
            lbox(Fs, upper, t - w / 2 - 0.12, t + w / 2 + 0.12, ot + 0.12, y_top - 0.5, 0, 0.012)
        if ob > 0.3:  # under a window: panelling, and curtains drawn back either side
            lbox(Fs, wains, t - w / 2, t + w / 2, 0, ob, 0, 0.03)
            if curtains: drapes(Fs, t, w, ob, ot, curtains)
        u = t + w / 2


def window_glass(F, t, w, ob, ot, lit=False):
    """Glass in a wall opening (set in the wall's middle) with glazing bars and a pointed top light."""
    g = 'glass_lit1' if lit else 'glass_clear'
    lbox(F, g, t - w / 2, t + w / 2, ob, ot, -0.01, 0.01)
    for k in (-1, 0, 1):
        lbox(F, 'trim_dark', t + k * w / 3 - 0.02, t + k * w / 3 + 0.02, ob, ot, -0.04, 0.04) if k else \
            lbox(F, 'trim_dark', t - 0.025, t + 0.025, ob, ot, -0.04, 0.04)
    lbox(F, 'trim_dark', t - w / 2, t + w / 2, ob + (ot - ob) * 0.62, ob + (ot - ob) * 0.62 + 0.05, -0.04, 0.04)


def floor(mat, x0, x1, z0, z1, y=0.0):
    wbox(mat, x0, x1, y - 0.1, y, z0, z1)


def coffered_ceiling(x0, x1, z0, z1, y, beam='oak_panel', field='fresco_gothic', step=1.6):
    wbox(field, x0, x1, y, y + 0.1, z0, z1)
    nx, nz = max(1, int((x1 - x0) / step)), max(1, int((z1 - z0) / step))
    for i in range(nx + 1):
        x = x0 + i * (x1 - x0) / nx
        wbox(beam, x - 0.1, x + 0.1, y - 0.35, y, z0, z1)
    for k in range(nz + 1):
        z = z0 + k * (z1 - z0) / nz
        wbox(beam, x0, x1, y - 0.35, y, z - 0.1, z + 0.1)


def gasolier(x, y_ceiling, z, arms=6, drop=1.6, r=0.7):
    """A brass gas chandelier: a rod, a central body and arms ending in glass globes."""
    y = y_ceiling - drop
    tube('brass', [(x, y_ceiling, z), (x, y, z)], 0.02)
    sphere('brass', (x, y, z), 0.09, 10)
    for k in range(arms):
        a = 2 * math.pi * k / arms
        p = (x + math.cos(a) * r, y + 0.1, z + math.sin(a) * r)
        tube('brass', [(x, y, z), (x + math.cos(a) * r * 0.6, y - 0.08, z + math.sin(a) * r * 0.6), p], 0.012)
        sphere('lamp_glass', (p[0], p[1] + 0.08, p[2]), 0.07, 8)
    LAMPS.append([x, y, z])


def column(x, z, y0, y1, r=0.22, mat='marble_white'):
    cyl('trim_dark', (x, y0, z), 0.3, r * 1.4, r * 1.3, seg=12)
    cyl(mat, (x, y0 + 0.3, z), y1 - y0 - 0.6, r, r * 0.9, seg=14)
    cyl('gilt_frame', (x, y1 - 0.3, z), 0.3, r * 0.95, r * 1.5, seg=12)
    collide(x - r, y0, z - r, x + r, y1, z + r)


def chair(x, z, rot, mat='velvet_red'):
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, mat, -0.25, 0.25, 0.42, 0.52, -0.25, 0.25)
    lbox(F, mat, -0.25, 0.25, 0.52, 1.05, 0.2, 0.27)
    for a in (-0.22, 0.22):
        for b in (-0.22, 0.22):
            lbox(F, 'walnut_panel', a - 0.025, a + 0.025, 0, 0.45, b - 0.025, b + 0.025)


def table(x, z, w, d, h=0.76, mat='walnut_panel', cloth=None):
    wbox(cloth or mat, x - w / 2, x + w / 2, h - 0.05, h, z - d / 2, z + d / 2)
    for a in (-1, 1):
        for b in (-1, 1):
            wbox(mat, x + a * (w / 2 - 0.08) - 0.04, x + a * (w / 2 - 0.08) + 0.04, 0, h - 0.05, z + b * (d / 2 - 0.08) - 0.04,
                 z + b * (d / 2 - 0.08) + 0.04)
    collide(x - w / 2, 0, z - d / 2, x + w / 2, h, z + d / 2)


def bust(x, y, z):
    """A plaster cast on a pedestal: the art school's drawing models."""
    cyl('plaster_cast', (x, 0, z), y, 0.22, 0.2, seg=10)
    cyl('plaster_cast', (x, y, z), 0.12, 0.17, 0.12, seg=10)
    cyl('plaster_cast', (x, y + 0.12, z), 0.12, 0.06, 0.06, seg=8)
    sphere('plaster_cast', (x, y + 0.32, z), 0.12, 12)
    collide(x - 0.25, 0, z - 0.25, x + 0.25, y + 0.4, z + 0.25)


def bookcase_run(F, u0, u1, h=3.6):
    lbox(F, 'books', u0, u1, 0.6, h - 0.3, 0.02, 0.04)
    lbox(F, 'walnut_panel', u0, u1, 0, 0.6, 0, 0.45)
    lbox(F, 'walnut_panel', u0 - 0.05, u1 + 0.05, h - 0.3, h, 0, 0.5)
    n = max(1, int((u1 - u0) / 1.0))
    for k in range(n + 1):
        u = u0 + k * (u1 - u0) / n
        lbox(F, 'walnut_panel', u - 0.04, u + 0.04, 0.6, h - 0.3, 0, 0.45)


def palm(x, z, h=2.6):
    cyl('barrel_wood', (x, 0, z), 0.5, 0.3, 0.26, seg=12)  # tub
    cyl('door_wood', (x, 0.5, z), h - 0.5, 0.06, 0.045, seg=6)
    for k in range(9):
        a = 2 * math.pi * k / 9
        tip = Vector((x + math.cos(a) * 1.1, h - 0.5, z + math.sin(a) * 1.1))
        mid = Vector((x + math.cos(a) * 0.6, h + 0.15, z + math.sin(a) * 0.6))
        base = Vector((x, h, z))
        bm = bm_for('palm')
        side = Vector((-math.sin(a), 0, math.cos(a))) * 0.18
        vs = [bm.verts.new(p) for p in (base, mid - side, tip, mid + side)]
        bm.faces.new(vs)
    collide(x - 0.3, 0, z - 0.3, x + 0.3, h, z + 0.3)


def organ(F, u0, u1, h):
    """The pipe organ: a carved case and ranks of gilt pipes rising in towers."""
    lbox(F, 'oak_panel', u0, u1, 0, 2.0, 0, 0.9)
    lbox(F, 'walnut_panel', u0 - 0.1, u1 + 0.1, 2.0, 2.2, 0, 1.0)
    n = 23
    for k in range(n):
        u = u0 + 0.2 + k * (u1 - u0 - 0.4) / (n - 1)
        rel = abs(k - (n - 1) / 2) / ((n - 1) / 2)
        ph = (h - 3.0) * (0.55 + 0.45 * (1 - rel) ** 0.6) * (1 if k % 4 else 1.08)
        cyl('organ_pipe', F @ Vector((u, 2.2, 0.5)), ph, 0.075, seg=10)
        cyl('organ_pipe', F @ Vector((u, 2.2, 0.5)), 0.25, 0.04, 0.075, seg=10)
    lbox(F, 'walnut_panel', (u0 + u1) / 2 - 0.9, (u0 + u1) / 2 + 0.9, 0.7, 1.0, 0.9, 1.4)  # keyboard desk
    lbox(F, 'ebony_panel', (u0 + u1) / 2 - 0.8, (u0 + u1) / 2 + 0.8, 1.0, 1.05, 0.9, 1.25)


def merlons(F, u0, u1, y, w, depth=0.5, step=0.9, mat='ashlar'):
    k = u0
    while k < u1 - 0.1:
        lbox(F, mat, k, min(u1, k + step * 0.55), y, y + 0.7, -depth / 2 + w, depth / 2 + w)
        k += step


def gable_roof(x0, x1, z0, z1, y, rise, ridge_along='x', mat='slate'):
    """A steep pitched roof with gable ends; the gable triangles are ashlar."""
    bm = bm_for(mat)
    if ridge_along == 'x':
        zm = (z0 + z1) / 2
        p = [(x0, y, z0), (x1, y, z0), (x1, y + rise, zm), (x0, y + rise, zm), (x0, y, z1), (x1, y, z1)]
        v = [bm.verts.new(q) for q in p]
        bm.faces.new((v[0], v[1], v[2], v[3])); bm.faces.new((v[3], v[2], v[5], v[4]))
        ga = bm_for('ashlar')
        for x in (x0, x1):
            ga.faces.new([ga.verts.new(q) for q in ((x, y, z0), (x, y + rise, zm), (x, y, z1))])
    else:
        xm = (x0 + x1) / 2
        p = [(x0, y, z0), (x0, y, z1), (xm, y + rise, z1), (xm, y + rise, z0), (x1, y, z0), (x1, y, z1)]
        v = [bm.verts.new(q) for q in p]
        bm.faces.new((v[0], v[1], v[2], v[3])); bm.faces.new((v[3], v[2], v[5], v[4]))
        ga = bm_for('ashlar')
        for z in (z0, z1):
            ga.faces.new([ga.verts.new(q) for q in ((x0, y, z), (xm, y + rise, z), (x1, y, z))])


def turret(x, z, r, y0, y1, spire):
    cyl('ashlar', (x, y0, z), y1 - y0, r, seg=16)
    for k in range(10):  # crenellated parapet ring
        a = 2 * math.pi * k / 10
        F = Matrix.Translation((x + math.cos(a) * r, y1, z + math.sin(a) * r)) @ Matrix.Rotation(-a + math.pi / 2, 4, 'Y')
        lbox(F, 'ashlar', -0.3, 0.3, 0, 0.7, -0.25, 0.25)
    cyl('slate', (x, y1, z), spire, r * 0.85, 0.02, seg=16)
    sphere('iron', (x, y1 + spire + 0.1, z), 0.1, 8)
    tube('iron', [(x, y1 + spire, z), (x, y1 + spire + 1.0, z)], 0.02)
    for k in range(5):  # slit windows climbing the turret
        a = math.pi / 2 + (k - 2) * 0.6
        yy = y0 + 2.0 + k * (y1 - y0 - 3) / 5
        F = Matrix.Translation((x + math.cos(a) * r, yy, z + math.sin(a) * r)) @ Matrix.Rotation(-a + math.pi / 2, 4, 'Y')
        lbox(F, 'glass_lit2' if k == 2 else 'glass_dark', -0.18, 0.18, 0, 1.1, 0.0, 0.04)
        lbox(F, 'trim_cream', -0.25, 0.25, 1.1, 1.25, 0, 0.08)


def lancet(F, u, v, w, h, lit=False, glass=None):
    """A pointed-arch window on an exterior face: glass, stone surround, a drip mould and a pointed head."""
    g = glass or ('glass_lit1' if lit else 'glass_dark')
    lbox(F, g, u - w / 2, u + w / 2, v, v + h, 0.0, 0.03)
    lbox(F, 'trim_cream', u - w / 2 - 0.12, u - w / 2, v, v + h, 0, 0.12)
    lbox(F, 'trim_cream', u + w / 2, u + w / 2 + 0.12, v, v + h, 0, 0.12)
    lbox(F, 'trim_cream', u - w / 2 - 0.18, u + w / 2 + 0.18, v - 0.12, v, 0, 0.18)
    lbox(F, 'trim_cream', u - 0.03, u + 0.03, v, v + h, 0, 0.06)
    # the pointed head: two leaning stones meeting at the apex, glass behind
    hh = w * 0.75
    bm = bm_for(g)
    p = [F @ Vector(q) for q in ((u - w / 2, v + h, 0.01), (u + w / 2, v + h, 0.01), (u, v + h + hh, 0.01))]
    bm.faces.new([bm.verts.new(q) for q in p])
    for s in (-1, 1):
        a = F @ Vector((u + s * (w / 2 + 0.06), v + h, 0.08))
        b = F @ Vector((u, v + h + hh + 0.1, 0.08))
        tube('trim_cream', [a, b], 0.08, seg=4)
    lbox(F, 'trim_cream', u - w / 2 - 0.3, u + w / 2 + 0.3, v + h + hh + 0.12, v + h + hh + 0.22, 0, 0.2)


# --- the house -------------------------------------------------------------------------

def rooms():
    """Room rectangles and finishes. x across the front, z from the back (-14) to the front (+14)."""
    R = {
        'vestibule': dict(name='Vestibule', x0=-3, x1=3, z0=10, z1=14, wains='oak_panel', upper='fresco_red',
                          floor='marble', ceil=H),
        'hall': dict(name='The Grand Hall', x0=-7, x1=7, z0=-6, z1=10, wains='ebony_panel', upper='fresco_red',
                     floor='marble', ceil=HALL_H),
        'library': dict(name='The Library', x0=-15, x1=-7, z0=2, z1=14, wains='walnut_panel', upper='fresco_green',
                        floor='parquet', ceil=H),
        'moorish': dict(name='The Moorish Room', x0=-15, x1=-7, z0=-6, z1=2, wains='rosewood_panel', upper='fresco_moorish',
                        floor='parquet', ceil=H),
        'reception': dict(name="The Director's Room", x0=-15, x1=-7, z0=-14, z1=-6, wains='rosewood_panel',
                          upper='fresco_gothic', floor='parquet', ceil=H),
        'music': dict(name='The Music Room', x0=7, x1=15, z0=2, z1=14, wains='oak_panel', upper='fresco_gothic',
                      floor='parquet', ceil=H),
        'studio': dict(name='The Life Class', x0=7, x1=15, z0=-6, z1=2, wains='oak_panel', upper='plaster',
                       floor='parquet', ceil=H),
        'tower': dict(name='The Tower Stair', x0=7, x1=15, z0=-14, z1=-6, wains='oak_panel', upper='fresco_louis',
                      floor='marble', ceil=H),
        'solarium': dict(name='The Solarium', x0=-7, x1=7, z0=-14, z1=-6, wains='trim_cream', upper='trim_cream',
                         floor='marble', ceil=H),
    }
    for k, r in R.items():
        ROOMS.append(dict(id=k, name=r['name'], x0=r['x0'], z0=r['z0'], x1=r['x1'], z1=r['z1'], y=0))
    return R


def build_house():
    R = rooms()

    # floors
    for r in R.values():
        floor(r['floor'], r['x0'], r['x1'], r['z0'], r['z1'])

    # --- outer walls (ashlar outside, lined inside), with windows ---
    WIN = (1.2, 1.2, 4.0)  # width, sill, head
    def outer(a, b, wins, doors=(), lit=()):
        ops = [(t, WIN[0], WIN[1], WIN[2]) for t in wins] + [(t, D + 0.6, 0, DH + 0.4) for t in doors]
        F, L = wall(a, b, -0.1, H, ops, mat='ashlar', thick=T + 0.1)
        for i, t in enumerate(wins):
            window_glass(F, t, WIN[0], WIN[1], WIN[2], lit=(i in lit))
        return F, L, ops
    walls = {}
    walls['front_w'] = outer((-15, 14), (-3, 14), [3, 9], lit=(1,))
    walls['front_e'] = outer((3, 14), (15, 14), [3, 9])
    walls['vest'] = outer((-3, 14), (3, 14), [], doors=[3])
    walls['west'] = outer((-15, -14), (-15, 14), [4, 10, 14, 18, 22, 26])
    walls['east'] = outer((15, 14), (15, -14), [4, 10, 18, 22, 26], lit=(2,))
    walls['back_w'] = outer((-7, -14), (-15, -14), [2, 6])
    walls['back_e'] = outer((15, -14), (7, -14), [2, 6])

    # --- inner walls with doors ---
    def inner(a, b, doors, mat='plaster', top=H, upper=()):
        """Doors at the ground floor (doors) and at the gallery / upper floor (upper)."""
        ops = [(t, D, 0, DH) for t in doors]
        F, L = wall(a, b, 0, top, ops + [(t, D, UF, UF + DH) for t in upper], mat=mat)
        for t in doors:
            door_leaves(F, t, D, DH, 1)
        for t in upper:
            door_leaves(F @ Matrix.Translation((0, UF, 0)), t, D, DH, 1)
            p = F @ Vector((t, 0, 0))
            UPPER_DOORS.append((p.x, p.z))
        return F, L, ops
    walls['vest_w'] = inner((-3, 10), (-3, 14), [])
    walls['vest_e'] = inner((3, 14), (3, 10), [])
    walls['vest_hall'] = inner((-3, 10), (3, 10), [3])
    Fv, _ = wall((-3, 10), (3, 10), H, HALL_H, [(3, D, UF, UF + DH)], mat='plaster')  # over the vestibule, to the sitting room
    door_leaves(Fv @ Matrix.Translation((0, UF, 0)), 3, D, DH, 1)
    UPPER_DOORS.append((0, 10))
    walls['hall_front_w'] = inner((-7, 10), (-3, 10), [], top=HALL_H)
    walls['hall_front_e'] = inner((3, 10), (7, 10), [], top=HALL_H)
    walls['hall_w'] = inner((-7, -6), (-7, 10), [12, 4], top=HALL_H, upper=[2, 14])  # library, Moorish room; upstairs
    walls['hall_e'] = inner((7, 10), (7, -6), [4, 12], top=HALL_H, upper=[2, 14])    # music room, life class; upstairs
    walls['hall_back'] = inner((7, -6), (-7, -6), [7], top=HALL_H)       # to the solarium
    walls['lib_moor'] = inner((-15, 2), (-7, 2), [4])
    walls['moor_rec'] = inner((-15, -6), (-7, -6), [4])
    walls['mus_stu'] = inner((7, 2), (15, 2), [4])
    walls['stu_tow'] = inner((7, -6), (15, -6), [4])
    walls['sol_w'] = inner((-7, -14), (-7, -6), [4])                     # solarium to Director's room
    walls['sol_e'] = inner((7, -6), (7, -14), [4])                       # solarium to tower stair

    # linings: each room dresses the faces that look into it
    def dress(key, side, room):
        F, L, ops = walls[key]
        r = R[room]
        top = r['ceil'] if r['ceil'] < HALL_H else 5.6
        lining(F, L, side, ops, top, wains=r['wains'], upper=r['upper'])
    for key, side, room in [
        ('front_w', -1, 'library'), ('front_e', -1, 'music'), ('vest', -1, 'vestibule'), ('west', -1, 'library'),
        ('west', -1, 'moorish'), ('west', -1, 'reception'), ('east', -1, 'music'), ('east', -1, 'studio'),
        ('east', -1, 'tower'), ('back_w', -1, 'reception'), ('back_e', -1, 'tower'),
        ('vest_w', 1, 'vestibule'), ('vest_e', 1, 'vestibule'), ('vest_hall', -1, 'vestibule'), ('vest_hall', 1, 'hall'),
        ('hall_front_w', 1, 'hall'), ('hall_front_e', 1, 'hall'), ('hall_front_w', -1, 'library'), ('hall_front_e', -1, 'music'),
        ('hall_w', -1, 'hall'), ('hall_w', 1, 'library'), ('hall_e', -1, 'hall'), ('hall_e', 1, 'music'),
        ('hall_back', -1, 'hall'), ('hall_back', 1, 'solarium'),
        ('lib_moor', 1, 'library'), ('lib_moor', -1, 'moorish'), ('moor_rec', 1, 'moorish'), ('moor_rec', -1, 'reception'),
        ('mus_stu', -1, 'music'), ('mus_stu', 1, 'studio'), ('stu_tow', -1, 'studio'), ('stu_tow', 1, 'tower'),
        ('sol_w', 1, 'solarium'), ('sol_w', -1, 'reception'), ('sol_e', -1, 'solarium'), ('sol_e', 1, 'tower'),
    ]:
        # long walls span several rooms; dress only the stretch that belongs to this room
        F, L, ops = walls[key]
        r = R[room]
        a = F @ Vector((0, 0, 0)); b = F @ Vector((L, 0, 0))
        r_dir = (b - a).normalized()
        def t_of(x, z): return (Vector((x, 0, z)) - a).dot(r_dir)
        ts = sorted([t_of(r['x0'], r['z0']), t_of(r['x1'], r['z1']), t_of(r['x0'], r['z1']), t_of(r['x1'], r['z0'])])
        t0, t1 = max(0, ts[0]), min(L, ts[-1])
        if t1 - t0 < 0.5: continue
        sub_ops = [(t - t0, w, ob, ot) for t, w, ob, ot in ops if t0 < t < t1]
        Fsub = F @ Matrix.Translation((t0, 0, 0))
        top = r['ceil'] if r['ceil'] < HALL_H else 5.6
        if room == 'solarium' and key not in ('hall_back',): continue
        outer_wall = key in ('front_w', 'front_e', 'vest', 'west', 'east', 'back_w', 'back_e')
        thick = T + 0.1 if outer_wall else T
        curtains = ('velvet_green' if room in ('library', 'studio', 'tower') else 'velvet_red') if outer_wall else None
        lining(Fsub, t1 - t0, side, sub_ops, top, wains=r['wains'], upper=r['upper'], thick=thick, curtains=curtains)

    # ceilings
    for k, r in R.items():
        if k in ('hall', 'solarium'): continue
        coffered_ceiling(r['x0'], r['x1'], r['z0'], r['z1'], r['ceil'],
                         beam='walnut_panel' if k == 'library' else 'oak_panel',
                         field={'moorish': 'fresco_moorish', 'library': 'fresco_green'}.get(k, 'fresco_gothic'))
        gasolier((r['x0'] + r['x1']) / 2, r['ceil'] - 0.35, (r['z0'] + r['z1']) / 2, drop=1.4)
    return R, walls


def build_hall(R):
    """The great hall: three storeys, a gallery on columns, the grand stair, a stained-glass skylight, and the
    Art Association's pictures hung frame to frame."""
    x0, x1, z0, z1 = -7, 7, -6, 10
    gy = 6.0  # gallery floor
    # The grand stair. One main flight rises from the hall to a landing against the back wall, then two side
    # flights climb left and right to platforms at gallery level, where the gallery runs forward along both sides
    # and across the front. Dimensions are walking dimensions: 0.3 m treads, 0.2 m risers, a 1.4 m landing.
    zf, zl = -0.1, -4.6        # foot and head of the main flight
    zb = -6.0                  # the back wall
    xl, xs = 3.2, 5.6          # landing half-width; where each side flight arrives
    n_main, n_side = 15, 8
    rise = (gy / 2) / n_main
    for k in range(n_main):    # the main flight, solid
        wbox('marble_white', -2.2, 2.2, 0, (k + 1) * rise, zf - (k + 1) * 0.3, zf - k * 0.3)
    wbox('marble_white', -xl, xl, gy / 2 - 0.3, gy / 2, zb, zl)       # the landing, a slab you can walk under
    for s_ in (-1, 1):
        for k in range(n_side):  # the side flights: steps on a stringer, open beneath
            xa, xb = s_ * (xl + k * 0.3), s_ * (xl + (k + 1) * 0.3)
            top = gy / 2 + (k + 1) * (gy / 2) / n_side
            wbox('marble_white', min(xa, xb), max(xa, xb), top - 0.45, top, zb, zl)
        wbox('oak_panel', min(s_ * xs, s_ * 7), max(s_ * xs, s_ * 7), gy - 0.4, gy, zb, zl)   # arrival platform
        wbox('parquet', min(s_ * xs, s_ * 7), max(s_ * xs, s_ * 7), gy, gy + 0.02, zb, zl)
    # gallery: forward along both sides from the platforms, and across the front, on marble columns
    for (a0, a1, b0, b1) in ((x0, x1, z1 - 2, z1), (x0, x0 + 2, zl, z1), (x1 - 2, x1, zl, z1)):
        wbox('oak_panel', a0, a1, gy - 0.4, gy, b0, b1)
        wbox('parquet', a0, a1, gy, gy + 0.02, b0, b1)
    for x in (-5, -1.7, 1.7, 5):
        column(x, z1 - 2, 0, gy - 0.4)
    for z in (5.5, 1.5, -2.5):
        column(x0 + 2, z, 0, gy - 0.4); column(x1 - 2, z, 0, gy - 0.4)
    # balustrades: the gallery's inner edge, and the open side of the landing and side flights (facing the hall)
    def balustrade(pts):
        for A, B in zip(pts, pts[1:]):
            A, B = Vector(A), Vector(B)
            tube('oak_panel', [A + Vector((0, 1.0, 0)), B + Vector((0, 1.0, 0))], 0.05, 6)
            n = max(1, int((B - A).length / 0.25))
            for k in range(n + 1):
                cyl('oak_panel', A.lerp(B, k / n), 1.0, 0.03, seg=6, cap=False)
    balustrade([(x0 + 2, gy, zl), (x0 + 2, gy, z1 - 2), (x1 - 2, gy, z1 - 2), (x1 - 2, gy, zl)])
    for s_ in (-1, 1):
        balustrade([(s_ * 2.2, gy / 2, zl), (s_ * xl, gy / 2, zl), (s_ * 5.0, gy / 2 + (5.0 - xl) / (xs - xl) * (gy / 2), zl)])
        # newel posts and the handrail of the main flight
        cyl('walnut_panel', (s_ * 2.3, 0, zf), 1.3, 0.1, 0.08, seg=8)
        sphere('brass', (s_ * 2.3, 1.38, zf), 0.09, 8)
        tube('walnut_panel', [(s_ * 2.3, 1.0, zf), (s_ * 2.3, gy / 2 + 1.0, zl)], 0.045)
    # walkable: the game follows these heights
    STAIRS.append([-2.2, 2.2, zl, zf, 'z', gy / 2, 0.0])
    STAIRS.append([-xl, xl, zb, zl, 'z', gy / 2, gy / 2])
    STAIRS.append([-xs, -xl, zb, zl, 'x', gy, gy / 2])
    STAIRS.append([xl, xs, zb, zl, 'x', gy / 2, gy])
    LEVELS.append(dict(y=gy, rects=[[x0, x1, z1 - 2, z1], [x0, x0 + 2, zl, z1], [x1 - 2, x1, zl, z1],
                                    [-7, -xs, zb, zl], [xs, 7, zb, zl]]))
    # colliders (each only counts at the height it stands at, so floors above and below don't interfere)
    for s_ in (-1, 1):
        collide(min(s_ * 2.2, s_ * 2.3), 0, zl, max(s_ * 2.2, s_ * 2.3), gy / 2 + 1.0, zf)          # main flight's sides
        collide(min(s_ * xl, s_ * 7), 0, zb, max(s_ * xl, s_ * 7), gy / 2 - 0.2, zl)               # under the side flights
        collide(min(s_ * 2.2, s_ * 5.0), gy / 2, zl - 0.05, max(s_ * 2.2, s_ * 5.0), gy + 1.5, zl + 0.1)  # open side, railed
    collide(x0 + 1.95, gy, z1 - 2.05, x1 - 1.95, gy + 1.0, z1 - 1.95)
    for xx in (x0 + 2, x1 - 2):
        collide(xx - 0.05, gy, zl, xx + 0.05, gy + 1.0, z1 - 2)
    # pictures: three tiers of them in gilt frames on the hall walls (the Association's collection)
    hang = [(frame((x0 + 0.18, 0, z1), (0, 0, -1), (1, 0, 0)), 16), (frame((x1 - 0.18, 0, z0), (0, 0, 1), (-1, 0, 0)), 16)]
    idx = 0
    for F, L in hang:
        for u in (2.0, 6.0, 10.0, 14.0):
            if abs(u - 4) < 1.4 or abs(u - 12) < 1.4: continue  # leave the doors clear
            if F is hang[0][0] and u in (6.0, 10.0): continue    # the hall fireplace
            frame_painting(F, u, 1.9, 1.6, 1.2, idx); idx += 1
        for u in (5.5, 8.5, 11.5):  # (the gallery doors are at u = 2 and 14)
            frame_painting(F, u, 7.4, 1.8, 1.3, idx); idx += 1
            frame_painting(F, u, 9.2, 1.1, 0.8, idx + 3); idx += 1
        for u in (2.0, 14.0):
            frame_painting(F, u, 10.2, 1.4, 1.0, idx); idx += 1
    Ff = frame((x0, 0, z1 - 0.18), (1, 0, 0), (0, 0, -1))
    for u in (3.0, 11.0):
        frame_painting(Ff, u, 7.5, 2.4, 1.7, idx); idx += 1
    # a large canvas over the stair landing
    Fb = frame((x1, 0, z0 + 0.18), (-1, 0, 0), (0, 0, 1))
    frame_painting(Fb, 7, 7.2, 4.0, 2.6, 5)
    # hall walls above the gallery: frescoed, with a frieze at the top
    centre = Vector(((x0 + x1) / 2, 0, (z0 + z1) / 2))
    for (a, b) in (((x0, z0), (x0, z1)), ((x1, z1), (x1, z0)), ((x0, z1), (x1, z1)), ((x1, z0), (x0, z0))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        rr = (B - A).normalized(); nn = Vector((-rr.z, 0, rr.x))
        if nn.dot(centre - A) < 0: nn = -nn  # face into the hall
        F = frame(A, rr, nn)
        L = (B - A).length
        Fi = F @ Matrix.Translation((0, 0, T / 2 + 0.01))
        # leave the gallery doorways open: find the doors on this wall
        cuts = sorted((F.inverted() @ Vector((dx, 0, dz))).x for dx, dz in UPPER_DOORS
                      if abs((F.inverted() @ Vector((dx, 0, dz))).z) < 0.3 and 0 < (F.inverted() @ Vector((dx, 0, dz))).x < L)
        u = 0.0
        for c in cuts + [L + 10]:
            if min(L, c - D / 2 - 0.15) > u:
                lbox(Fi, 'fresco_red', u, min(L, c - D / 2 - 0.15), gy + 0.1, HALL_H - 1.0, 0, 0.01)
            if c > L: break
            lbox(Fi, 'fresco_red', c - D / 2 - 0.15, c + D / 2 + 0.15, gy + DH + 0.15, HALL_H - 1.0, 0, 0.01)
            for side in (-1, 1):  # door surround
                lbox(Fi, 'trim_dark', c + side * D / 2 - 0.15 * (side < 0), c + side * D / 2 + 0.15 * (side > 0), gy, gy + DH + 0.15, 0, 0.06)
            lbox(Fi, 'trim_dark', c - D / 2 - 0.15, c + D / 2 + 0.15, gy + DH, gy + DH + 0.15, 0, 0.06)
            u = c + D / 2 + 0.15
        lbox(Fi, 'gilt_frame', 0, L, HALL_H - 1.0, HALL_H - 0.85, 0, 0.06)
        lbox(Fi, 'walnut_panel', 0, L, HALL_H - 0.85, HALL_H, 0, 0.3)
    # ceiling with a stained-glass skylight, and two great gasoliers
    wbox('walnut_panel', x0, x1, HALL_H, HALL_H + 0.3, z0, z1)
    wbox('stained', -3.5, 3.5, HALL_H - 0.02, HALL_H, 0, 6)
    for x in (-3.5, 3.5):
        tube('walnut_panel', [(x, HALL_H - 0.05, 0), (x, HALL_H - 0.05, 6)], 0.08)
    gasolier(0, HALL_H, 7.5, arms=10, drop=5.0, r=1.1)
    gasolier(0, HALL_H, 1.0, arms=10, drop=4.5, r=1.1)
    # benches for the visitors
    for z in (6.0, 3.0):
        wbox('velvet_red', -1.6, 1.6, 0.4, 0.5, z - 0.35, z + 0.35)
        wbox('walnut_panel', -1.6, 1.6, 0, 0.4, z - 0.3, z + 0.3)
        collide(-1.6, 0, z - 0.35, 1.6, 0.5, z + 0.35)


def furnish(R):
    # --- the library: walnut bookcases on every wall, a reading table, the school's records ---
    r = R['library']
    for F, u0, u1 in ((frame((-14.8, 0, 13.8), (0, 0, -1), (1, 0, 0)), 0.6, 4.0), (frame((-14.8, 0, 13.8), (0, 0, -1), (1, 0, 0)), 4.8, 9.6),
                      (frame((-14.8, 0, 13.65), (1, 0, 0), (0, 0, -1)), 0.5, 1.9),                       (frame((-7.2, 0, 2.2), (0, 0, 1), (-1, 0, 0)), 0.3, 1.0), (frame((-7.2, 0, 2.2), (0, 0, 1), (-1, 0, 0)), 3.6, 7.5)):
        bookcase_run(F, u0, u1)
    table(-11, 8, 3.2, 1.4, cloth='velvet_green')
    for x in (-12, -10):
        chair(x, 9.1, math.pi); chair(x, 6.9, 0)
    # a lectern with the great atlas, and the archive boxes Holmes will want
    wbox('walnut_panel', -13.3, -12.7, 0, 1.1, 3.4, 4.0)
    wbox('canvas', -13.4, -12.6, 1.1, 1.18, 3.3, 4.1)
    collide(-13.4, 0, 3.3, -12.6, 1.2, 4.1)
    INTERACT.append(dict(id='archive', label='The school\'s archive', pos=[-13.0, 1.1, 3.7], r=1.8))

    # --- the Moorish room: horseshoe arches, divans, brass lamps, a tiled floor in the centre ---
    r = R['moorish']
    for x in (-13.5, -8.5):
        wbox('velvet_red', x - 0.6, x + 0.6, 0, 0.45, -4.5, 0.5)
        collide(x - 0.6, 0, -4.5, x + 0.6, 0.45, 0.5)
    table(-11, -2, 1.0, 1.0, h=0.45, mat='brass')
    for z in (-5.5, 1.5):
        for x in (-13, -9):
            tube('brass', [(x, H - 0.3, z), (x, 3.4, z)], 0.01)
            sphere('candle', (x, 3.3, z), 0.12, 8)
    Fm = frame((-15 + T / 2, 0, -6), (0, 0, 1), (1, 0, 0))
    for u in (2.0, 6.0):  # horseshoe arch niches
        lbox(Fm, 'trim_cream', u - 0.8, u + 0.8, 1.2, 1.3, 0, 0.1)
        cyl('trim_cream', Fm @ Vector((u, 2.8, 0.05)), 0.1, 0.85, axis=Fm.to_3x3() @ Vector((0, 0, 1)), seg=16)

    # --- the Director's room (the old reception room): rosewood, a desk, the curator's chair ---
    table(-11, -10, 2.2, 1.1, mat='rosewood_panel', cloth='velvet_green')
    chair(-11, -11.0, 0, mat='velvet_green'); chair(-11, -8.8, math.pi, mat='velvet_green')
    INTERACT.append(dict(id='curator', label='The curator\'s desk', pos=[-11, 0.8, -10], r=2.0))

    # --- the music room: the organ, a grand piano, rows of chairs for the Association's concerts ---
    Fo = frame((14.8, 0, 3), (0, 0, 1), (-1, 0, 0))
    organ(Fo, 1.0, 10.0, H)
    collide(13.3, 0, 3, 15, 2.2, 13)
    for row in range(3):
        for k in range(4):
            chair(8.3 + row * 1.2, 4.0 + k * 1.1, -math.pi / 2)

    # --- the life class (the old oak dining room): easels in a ring round a model's dais, plaster casts ---
    wbox('velvet_red', 10.3, 11.7, 0, 0.4, -2.7, -1.3)
    collide(10.3, 0, -2.7, 11.7, 0.4, -1.3)
    for k in range(6):
        a = math.pi * (0.15 + k * 0.14)
        easel(11 + math.cos(a) * 3.0, -2 + math.sin(a) * 3.0 - 0.6, -a - math.pi / 2, k)
    for (x, z) in ((14.2, -5.2), (14.2, 1.2), (8.0, 1.2)):
        bust(x, 1.1, z)

    # --- the tower stair: a spiral stair rising out of sight (the climb is a door in the game) ---
    cx, cz = 11, -10
    cyl('walnut_panel', (cx, 0, cz), H, 0.15, seg=10)
    for k in range(16):
        a = k * 0.45
        y = 0.2 + k * 0.33
        F = Matrix.Translation((cx, y, cz)) @ Matrix.Rotation(-a, 4, 'Y')
        lbox(F, 'oak_panel', 0.15, 1.6, -0.05, 0.05, -0.25, 0.25)
    collide(cx - 1.7, 0, cz - 1.7, cx + 1.7, H, cz + 1.7)
    INTERACT.append(dict(id='tower', label='Climb the tower', pos=[cx - 1.9, 1.0, cz + 0.8], r=1.6, to='tower_room'))

    # --- the solarium: an iron-and-glass conservatory looking over the city ---
    for x in (-6.5, 6.5):
        for z in (-13.5, -9.5, -6.8):
            if (x, z) in ((6.5, -6.8),): continue
            palm(x * 0.85, z)
    for (x, z, rot) in ((-2, -10, 0.3), (2, -10, -0.3), (0, -12, 0)):
        chair(x, z, rot, mat='velvet_green')
    table(0, -10.8, 1.0, 1.0, h=0.7, mat='trim_cream')


def build_solarium_glass():
    """Replace the solarium's outer wall with glass: iron mullions, a glazed lean-to roof."""
    x0, x1, z = -7, 7, -14
    wbox('glass_clear', x0, x1, 0.6, H + 1.0, z - 0.03, z + 0.03)
    wbox('ashlar', x0, x1, -0.1, 0.6, z - 0.2, z + 0.2)
    collide(x0, 0, z - 0.2, x1, H, z + 0.2)
    for k in range(15):
        x = x0 + k * (x1 - x0) / 14
        wbox('iron', x - 0.03, x + 0.03, 0.6, H + 1.0, z - 0.06, z + 0.06)
    for y in (2.6, 4.6):
        wbox('iron', x0, x1, y - 0.03, y + 0.03, z - 0.06, z + 0.06)
    # glazed roof sloping up from the glass wall to the house
    bm = bm_for('glass_clear')
    q = [(x0, H + 1.0, z), (x1, H + 1.0, z), (x1, H + 2.5, -6), (x0, H + 2.5, -6)]
    bm.faces.new([bm.verts.new(p) for p in q])
    for k in range(8):
        x = x0 + k * (x1 - x0) / 7
        tube('iron', [(x, H + 1.0, z), (x, H + 2.5, -6)], 0.03, 4)
    INTERACT.append(dict(id='view', label='The view over the city', pos=[0, 1.6, -13.0], r=2.5))


def build_exterior():
    """The castle outside: ashlar walls, upper storey, roofs and gables, turrets, the tower, the porte-cochere,
    the drive, the lawn and the granite wall on California Street."""
    # upper storey (seen from outside only): walls above the ground floor with lancet windows
    up0, up1 = H, 11.0
    for (a, b) in (((-15, 14), (15, 14)), ((15, 14), (15, -14)), ((15, -14), (7, -14)), ((-7, -14), (-15, -14)), ((-15, -14), (-15, 14))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        r = (B - A).normalized(); n = outward(A, B, Vector((0, 0, 0)))
        F = frame(A, r, n)
        L = (B - A).length
        ks = []
        k = 2.0
        while k < L - 1.5:
            ks.append(k); k += 3.0
        # the wall itself, with an opening behind each lancet so the rooms upstairs have windows
        Fw, _ = wall(a, b, up0, up1, [(t if (B - A).dot(r) > 0 else t, 0.9, UF + 0.9, UF + 3.3) for t in ks], mat='ashlar', thick=T + 0.1)
        Fo = F @ Matrix.Translation((0, 0, T / 2 + 0.05))
        lbox(Fo, 'trim_cream', 0, L, up0 - 0.1, up0 + 0.15, 0, 0.2)  # string course
        for k in ks:
            lancet(Fo, k, UF + 0.9, 0.9, 2.4, glass='glass_clear')  # clear: the rooms upstairs look out over the city
            p = F @ Vector((k, 0, 0))
            UPPER_WINDOWS.append((p.x, p.z))
        merlons(Fo, 0, L, up1, 0.0)
    wbox('ashlar', -7, 7, H, up1, -6.25, -6.18)  # the hall's back wall above the solarium roof, outside face
    # the hall's clerestory and roof rising above the house
    for (a, b) in (((-7, 10), (7, 10)), ((7, 10), (7, -6)), ((7, -6), (-7, -6)), ((-7, -6), (-7, 10))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        r = (B - A).normalized(); n = outward(A, B, Vector((0, 0, 0)))
        F = frame(A, r, n); L = (B - A).length
        lbox(F, 'ashlar', 0, L, up1, HALL_H + 0.3, -T / 2, T / 2)
    gable_roof(-15.4, 15.4, -14.4, 14.4, up1 + 0.7, 7.5, ridge_along='x')
    gable_roof(-7.4, 7.4, -6.4, 10.4, HALL_H + 0.3, 5.0, ridge_along='z')
    # cross gables over the front wings
    for x in (-11, 11):
        gable_roof(x - 3.4, x + 3.4, 8.0, 14.6, up1 + 0.7, 5.5, ridge_along='z')
    # round turrets at the front corners
    for x in (-15, 15):
        turret(x, 14, 2.4, -0.1, 15.5, 7.0)
    # the tower, at the back corner over the stair, with a glazed observatory and a spire
    tx0, tx1, tz0, tz1 = 8, 15, -14, -7
    ty = 22.0
    for (a, b) in (((tx0, tz1), (tx1, tz1)), ((tx1, tz1), (tx1, tz0)), ((tx1, tz0), (tx0, tz0)), ((tx0, tz0), (tx0, tz1))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        r = (B - A).normalized(); n = outward(A, B, Vector(((tx0 + tx1) / 2, 0, (tz0 + tz1) / 2)))
        F = frame(A, r, n); L = (B - A).length
        lbox(F, 'ashlar', 0, L, up1, ty, -T / 2, T / 2)
        Fo = F @ Matrix.Translation((0, 0, T / 2))
        for v in (13.0, 17.0):
            lancet(Fo, L / 2, v, 0.8, 2.0, lit=v == 17.0)
        # observatory: glass all round between piers
        for k in range(4):
            u = 0.4 + k * (L - 0.8) / 4
            lbox(F, 'glass_clear', u + 0.25, u + (L - 0.8) / 4 - 0.25, ty, ty + 2.6, -0.02, 0.02)
            lbox(F, 'ashlar', u - 0.25, u + 0.25, ty, ty + 2.6, -T / 2, T / 2)
        lbox(F, 'ashlar', L - 0.65, L, ty, ty + 2.6, -T / 2, T / 2)
        lbox(Fo, 'trim_cream', 0, L, ty - 0.2, ty, 0, 0.3)
        lbox(F, 'ashlar', 0, L, ty + 2.6, ty + 3.4, -T / 2, T / 2 + 0.1)
        merlons(Fo, 0, L, ty + 3.4, 0.05)
    wbox('ashlar', tx0, tx1, ty - 0.2, ty, tz0, tz1)  # observatory floor
    cyl('slate', ((tx0 + tx1) / 2, ty + 3.4, (tz0 + tz1) / 2), 10.0, 4.6, 0.05, seg=4)
    tube('iron', [((tx0 + tx1) / 2, ty + 13.4, (tz0 + tz1) / 2), ((tx0 + tx1) / 2, ty + 15.0, (tz0 + tz1) / 2)], 0.03)
    # inside the observatory: a floor, a telescope on its tripod, a bench
    floor('parquet', tx0 + 0.3, tx1 - 0.3, tz0 + 0.3, tz1 - 0.3, y=ty)
    cx, cz = (tx0 + tx1) / 2, (tz0 + tz1) / 2
    for k in range(3):
        a = k * 2 * math.pi / 3
        tube('brass', [(cx + math.cos(a) * 0.5, ty, cz - 1.5 + math.sin(a) * 0.5), (cx, ty + 1.3, cz - 1.5)], 0.02)
    tube('brass', [(cx, ty + 1.3, cz - 1.0), (cx, ty + 1.6, cz - 2.4)], 0.07, 12)
    collide(cx - 0.6, ty, cz - 2.2, cx + 0.6, ty + 1.6, cz - 0.9)
    for (a0, a1, b0, b1) in ((tx0, tx1, tz0, tz0 + 0.3), (tx0, tx1, tz1 - 0.3, tz1), (tx0, tx0 + 0.3, tz0, tz1), (tx1 - 0.3, tx1, tz0, tz1)):
        collide(a0, ty, b0, a1, ty + 3, b1)
    INTERACT.append(dict(id='down', label='Down the stair', pos=[tx0 + 1.2, ty + 1.0, tz1 - 1.2], r=1.2, to='tower_foot'))
    INTERACT.append(dict(id='telescope', label='The telescope', pos=[cx, ty + 1.4, cz - 1.6], r=1.6))
    LAMPS.append([cx, ty + 2.4, cz])

    # the porte-cochere: pointed arches on stone piers sheltering the front door
    pz0, pz1 = 14, 20
    for x in (-3.2, 3.2):
        for z in (pz0 + 0.3, pz1 - 0.3):
            wbox('ashlar', x - 0.4, x + 0.4, 0, 4.6, z - 0.4, z + 0.4)
            collide(x - 0.4, 0, z - 0.4, x + 0.4, 4.6, z + 0.4)
    wbox('ashlar', -3.6, 3.6, 4.6, 6.2, pz0, pz1)
    Fp = frame((-3.6, 0, pz1), (1, 0, 0), (0, 0, 1))
    merlons(Fp, 0, 7.2, 6.2, 0.0)
    for s in (-1, 1):  # the pointed arch over the carriage way, front face
        tube('trim_cream', [(s * 2.8, 4.0, pz1 + 0.05), (0, 4.55, pz1 + 0.05)], 0.12, 4)
    wbox('stone', -3, 3, -0.05, 0.12, pz0, pz1 - 0.1)
    LAMPS.append([0, 4.2, (pz0 + pz1) / 2])
    sphere('lamp_glass', (0, 4.3, (pz0 + pz1) / 2), 0.18, 10)
    tube('iron', [(0, 4.6, (pz0 + pz1) / 2), (0, 4.45, (pz0 + pz1) / 2)], 0.02)
    # front steps and door
    for k in range(3):
        wbox('stone', -2.2, 2.2, 0, 0.0, 14.0 + k * 0.01, 14.4)
    lbox(frame((-0.9, 0, 14.05), (1, 0, 0), (0, 0, 1)), 'door_wood', 0, 1.8, 0, DH_FRONT, 0, 0.06) if False else None

    # the grounds, the street and the neighbours are built by build_grounds()



# --- the Association's pictures: real paintings (public domain), see art/paintings/credits.json ----------

PICTURES = []


def load_pictures():
    d = os.path.join(ROOT, 'art', 'paintings')
    for c in json.load(open(os.path.join(d, 'credits.json'))):
        img = bpy.data.images.load(os.path.join(d, c['file']))
        w, h = img.size
        k = 512 / max(w, h)
        if k < 1: img.scale(max(1, int(w * k)), max(1, int(h * k)))
        img.pack()
        name = 'pic_' + os.path.splitext(c['file'])[0][:24]
        material(name, '#808080', rough=0.55, tex=img, scale=None)
        PICTURES.append((name, w / h))
    # old silvering, faintly lit by what it reflects: a sharp metal mirror flares every gas jet into bloom, and with
    # no environment map a metal one shows black
    material('mirror', '#5a6268', rough=0.45, metal=0.2, emit='#2e353a', emit_strength=1.0)
    material('liner', '#2a2018', rough=0.6)


def frame_painting(F, u, v, w, h, idx, depth=0.0):
    """A real painting, at its true proportions inside a w x h space, in a liner and a deep gilt frame.
    F is a wall frame (w = 0 at the wall face); u is the centre, v the bottom."""
    mat, aspect = PICTURES[idx % len(PICTURES)]
    if w / h > aspect: w = h * aspect
    else: h = w / aspect
    v0 = v
    corners = [F @ Vector(p) for p in ((u - w / 2, v0, depth + 0.035), (u + w / 2, v0, depth + 0.035),
                                         (u + w / 2, v0 + h, depth + 0.035), (u - w / 2, v0 + h, depth + 0.035))]
    canvas(mat, corners)
    lw, fw = 0.05, 0.11 + 0.03 * (w > 1.5)
    for a, b, c_, d in ((u - w / 2 - lw, u - w / 2, v0 - lw, v0 + h + lw), (u + w / 2, u + w / 2 + lw, v0 - lw, v0 + h + lw),
                        (u - w / 2, u + w / 2, v0 - lw, v0), (u - w / 2, u + w / 2, v0 + h, v0 + h + lw)):
        lbox(F, 'liner', a, b, c_, d, depth, depth + 0.045)
    W, H = w / 2 + lw, h + lw
    for a, b, c_, d in ((u - W - fw, u - W, v0 - lw - fw, v0 + H + fw), (u + W, u + W + fw, v0 - lw - fw, v0 + H + fw),
                        (u - W, u + W, v0 - lw - fw, v0 - lw), (u - W, u + W, v0 + H, v0 + H + fw)):
        lbox(F, 'gilt_frame', a, b, c_, d, depth, depth + 0.09)
        if w > 1.2:  # the moulded lip, on the big gallery frames only: a hundred small frames' worth was 10k triangles
            lbox(F, 'gilt_frame', a + 0.02, b - 0.02, c_ + 0.02, d - 0.02, depth + 0.09, depth + 0.11)
    # a picture light's brass hood on the big ones
    if w > 1.7:
        lbox(F, 'brass', u - 0.4, u + 0.4, v0 + H + fw + 0.12, v0 + H + fw + 0.2, depth, depth + 0.25)


def easel(x, z, rot, idx):
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    for s in (-0.3, 0.3):
        tube('oak_panel', [F @ Vector((s, 0, 0.2)), F @ Vector((s * 0.3, 1.9, 0))], 0.02)
    tube('oak_panel', [F @ Vector((0, 0, -0.5)), F @ Vector((0, 1.7, 0.02))], 0.02)
    lbox(F, 'oak_panel', -0.4, 0.4, 0.85, 0.9, -0.05, 0.08)
    if idx % 3:
        mat, a = PICTURES[(idx * 5) % len(PICTURES)]
        w = 0.7; h = min(0.75, w / a)
        canvas(mat, [F @ Vector(p) for p in ((-w / 2, 0.9, 0.06), (w / 2, 0.9, 0.06), (w / 2, 0.9 + h, 0.06), (-w / 2, 0.9 + h, 0.06))])
        lbox(F, 'canvas', -w / 2, w / 2, 0.9, 0.9 + h, 0.02, 0.055)
    else:
        lbox(F, 'canvas', -0.35, 0.35, 0.9, 1.55, 0.02, 0.05)
    collide(x - 0.45, 0, z - 0.45, x + 0.45, 1.8, z + 0.45)


# --- textures for furnishing ---------------------------------------------------------------

def rug_tex(name, field, border, accent, size=512, seed=0):
    """A Persian carpet: guard stripes, a border of rosettes, a field of small motifs and a central medallion."""
    H, W = int(size * 1.4), size
    yy, xx = np.mgrid[0:H, 0:W]
    u, v = xx / W, yy / H
    col = np.zeros((H, W, 3), np.float32) + hexrgb(field)
    b = np.minimum(np.minimum(u, 1 - u) * W, np.minimum(v, 1 - v) * H)
    col[(b > 18) & (b < 64)] = hexrgb(border)
    col[(b > 22) & (b < 26)] = hexrgb(accent)
    col[(b > 56) & (b < 60)] = hexrgb(accent)
    ros = ((b > 26) & (b < 56)) & ((np.sin(u * 60) * np.sin(v * 84)) > 0.6)
    col[ros] = hexrgb(accent)
    col[b < 18] = hexrgb('#d8c8a8')  # fringe-side guard
    fu, fv = (u * 10) % 1 - 0.5, (v * 14) % 1 - 0.5
    motif = (np.abs(fu) + np.abs(fv) < 0.22) & (b > 70)
    col[motif] = hexrgb(border) * 1.2
    r = np.hypot((u - 0.5) * 1.0, (v - 0.5) * 0.72)
    a = np.arctan2(v - 0.5, u - 0.5)
    med = r < 0.13 + 0.03 * np.cos(8 * a)
    col[med] = hexrgb(border)
    col[med & (r < 0.1 + 0.02 * np.cos(8 * a))] = hexrgb(accent)
    col[med & (r < 0.05)] = hexrgb(field)
    wear = 0.8 + 0.25 * noise(H, W, 30, seed) + 0.08 * noise(H, W, 2, seed + 1)
    return image(name, col * wear[..., None])


def interior_materials():
    load_pictures()
    for i, (f, b, a) in enumerate((('#5a1a14', '#1e2a40', '#8a6a3a'), ('#1e2a40', '#5a1a14', '#a89878'),
                                   ('#4a3018', '#243024', '#8a6a3a'), ('#341212', '#18182a', '#7a5a30'))):
        material(f'rug{i}', tex=rug_tex(f'rug{i}', f, b, a, seed=i), rough=0.95, scale=None)
    material('coals', '#000000', emit='#ff6020', emit_strength=4.0)
    material('firebox', '#0a0806', rough=0.9)
    material('marble_black', '#141414', rough=0.15)
    material('clock_face', '#e8e0cc', rough=0.4)
    material('globe', '#7a6a48', rough=0.5)


# --- pieces of furniture ------------------------------------------------------------------------

def rug(x0, x1, z0, z1, idx, y=0.006):
    canvas(f'rug{idx % 4}', [(x0, y, z1), (x1, y, z1), (x1, y, z0), (x0, y, z0)])


def fireplace(F, u, mat='marble_white', w=2.0, h=1.4, mirror=True):
    """A chimney-piece on a wall frame: a breast, a surround and shelf, the grate with live coals,
    a brass fender, an overmantel mirror, a clock and candlesticks."""
    d = 0.45
    lbox(F, 'plaster', u - w / 2 - 0.3, u + w / 2 + 0.3, 0, 5.0, 0, d - 0.1)       # the breast
    lbox(F, mat, u - w / 2, u - w / 2 + 0.28, 0, h, d - 0.1, d + 0.05)              # jambs
    lbox(F, mat, u + w / 2 - 0.28, u + w / 2, 0, h, d - 0.1, d + 0.05)
    lbox(F, mat, u - w / 2, u + w / 2, h - 0.3, h, d - 0.1, d + 0.05)              # lintel
    lbox(F, mat, u - w / 2 - 0.12, u + w / 2 + 0.12, h, h + 0.08, d - 0.1, d + 0.22)  # shelf
    lbox(F, 'firebox', u - w / 2 + 0.28, u + w / 2 - 0.28, 0, h - 0.3, d - 0.12, d - 0.1)
    lbox(F, 'marble_black', u - w / 2 - 0.1, u + w / 2 + 0.1, 0, 0.03, d - 0.1, d + 0.55)  # hearth
    # the grate and its coals
    lbox(F, 'iron', u - 0.35, u + 0.35, 0.1, 0.38, d - 0.08, d + 0.02)
    lbox(F, 'coals', u - 0.3, u + 0.3, 0.22, 0.36, d - 0.07, d)
    for k in range(5):
        lbox(F, 'iron', u - 0.3 + k * 0.15 - 0.01, u - 0.3 + k * 0.15 + 0.01, 0.1, 0.45, d + 0.0, d + 0.03)
    lbox(F, 'brass', u - w / 2 + 0.1, u + w / 2 - 0.1, 0.03, 0.15, d + 0.4, d + 0.45)  # fender
    p = F @ Vector((u, 0.5, d + 0.5))
    LAMPS.append([round(p.x, 3), round(p.y, 3), round(p.z, 3)])  # firelight (one of the moving lights may take it)
    if mirror:
        mw, mh = w + 0.2, 1.6
        canvas('mirror', [F @ Vector(q) for q in ((u - mw / 2, h + 0.3, d - 0.05), (u + mw / 2, h + 0.3, d - 0.05),
                                                   (u + mw / 2, h + 0.3 + mh, d - 0.05), (u - mw / 2, h + 0.3 + mh, d - 0.05))])
        for a, b, c_, e in ((u - mw / 2 - 0.1, u - mw / 2, h + 0.2, h + 0.4 + mh), (u + mw / 2, u + mw / 2 + 0.1, h + 0.2, h + 0.4 + mh),
                            (u - mw / 2, u + mw / 2, h + 0.2, h + 0.3), (u - mw / 2, u + mw / 2, h + 0.3 + mh, h + 0.45 + mh)):
            lbox(F, 'gilt_frame', a, b, c_, e, d - 0.1, d)
    # a bracket clock and a pair of candlesticks on the shelf
    c = F @ Vector((u, h + 0.08, d + 0.08))
    lbox(F, 'walnut_panel', u - 0.15, u + 0.15, h + 0.08, h + 0.45, d - 0.02, d + 0.16)
    nrm = (F.to_3x3() @ Vector((0, 0, 1))).normalized()
    cyl('clock_face', F @ Vector((u, h + 0.3, d + 0.16)), 0.01, 0.1, seg=16, axis=nrm)
    for s in (-1, 1):
        q = F @ Vector((u + s * (w / 2 - 0.2), h + 0.08, d + 0.08))
        cyl('brass', q, 0.3, 0.05, 0.02, seg=8)
        cyl('candle', q + Vector((0, 0.3, 0)), 0.12, 0.012, seg=6)
    collide_local(F, u - w / 2 - 0.3, u + w / 2 + 0.3, 0, 1.5, 0, d + 0.55)


def drapes(F, t, w, ob, ot, mat='velvet_red'):
    """Velvet curtains drawn back to either side of a window, with a fringed valance and tiebacks.
    F faces into the room (w = 0 at the lining)."""
    top = ot + 0.45
    for s in (-1, 1):
        u0 = t + s * (w / 2 - 0.1)
        u1 = t + s * (w / 2 + 0.55)
        bm = bm_for(mat)
        cols, rows = 10, 3
        vs = []
        for j in range(rows + 1):
            v = top - (top - 0.02) * j / rows
            pinch = 0.6 if j == 2 else 1.0  # gathered at the tieback
            row = []
            for i in range(cols + 1):
                uu = u0 + (u1 - u0) * (i / cols) ** (1 / pinch) if s > 0 else u0 + (u1 - u0) * (i / cols) ** (1 / pinch)
                ww = 0.06 + 0.05 * math.sin(i * math.pi * 0.9) ** 2
                row.append(bm.verts.new(F @ Vector((uu, v, ww))))
            vs.append(row)
        for j in range(rows):
            for i in range(cols):
                f = bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
                f.smooth = True
        lbox(F, 'gilt_frame', (u0 + u1) / 2 - 0.08, (u0 + u1) / 2 + 0.08, 1.15, 1.22, 0.05, 0.18)  # tieback
    lbox(F, mat, t - w / 2 - 0.65, t + w / 2 + 0.65, top - 0.35, top + 0.05, 0.02, 0.2)  # valance
    lbox(F, 'gilt_frame', t - w / 2 - 0.65, t + w / 2 + 0.65, top - 0.4, top - 0.35, 0.02, 0.21)  # fringe
    lbox(F, 'brass', t - w / 2 - 0.7, t + w / 2 + 0.7, top + 0.05, top + 0.09, 0.05, 0.12)       # pole


def door_leaves(F, t, w, h, side, thick=T):
    """Panelled double doors folded back flat against the wall either side of the opening (on side +1/-1 of F)."""
    lw = w / 2
    w0, w1 = sorted((side * (thick / 2 + 0.04), side * (thick / 2 + 0.1)))
    for s in (-1, 1):
        u0, u1 = sorted((t + s * w / 2, t + s * (w / 2 + lw)))
        lbox(F, 'walnut_panel', u0 + 0.02, u1 - 0.02, 0, h - 0.05, w0, w1)
        for (v0, v1) in ((0.2, 1.1), (1.3, h - 0.3)):
            lbox(F, 'walnut_panel', u0 + 0.14, u1 - 0.14, v0, v1, min(w0, w1) - 0.02 if side < 0 else w1, w0 if side < 0 else w1 + 0.02)
        sphere('brass', F @ Vector(((u0 + u1) / 2 + s * (lw / 2 - 0.12), 1.05, side * (thick / 2 + 0.12))), 0.03, 6)


def sofa(x, z, rot, mat='velvet_red', L=2.1):
    """A camelback sofa: a deep seat, a back rising to a hump, rolled arms, turned legs."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, mat, -L / 2, L / 2, 0.3, 0.48, -0.42, 0.4)
    lbox(F, mat, -L / 2 + 0.1, L / 2 - 0.1, 0.48, 0.58, -0.38, 0.3)  # cushion
    n = 9
    for k in range(n):
        a = -L / 2 + 0.1 + k * (L - 0.2) / n
        hump = 0.95 + 0.18 * math.sin(math.pi * (k + 0.5) / n)
        lbox(F, mat, a, a + (L - 0.2) / n + 0.01, 0.48, hump, 0.3, 0.44)
    lbox(F, 'walnut_panel', -L / 2, L / 2, 0.3, 0.36, 0.38, 0.46)
    for s in (-1, 1):
        cyl(mat, F @ Vector((s * (L / 2 - 0.08), 0.68, -0.42)), 0.82, 0.12, seg=10, axis=F.to_3x3() @ Vector((0, 0, 1)))
        lbox(F, mat, min(s * L / 2, s * (L / 2 - 0.16)), max(s * L / 2, s * (L / 2 - 0.16)), 0.3, 0.68, -0.42, 0.4)
        for zz in (-0.36, 0.36):
            cyl('walnut_panel', F @ Vector((s * (L / 2 - 0.08), 0, zz)), 0.3, 0.035, 0.025, seg=6)
    collide_local(F, -L / 2, L / 2, 0, 1.0, -0.45, 0.46)


def wingback(x, z, rot, mat='velvet_green'):
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, mat, -0.4, 0.4, 0.3, 0.5, -0.35, 0.35)
    lbox(F, mat, -0.4, 0.4, 0.5, 1.25, 0.25, 0.38)
    for s in (-1, 1):
        lbox(F, mat, s * 0.36 - 0.05, s * 0.36 + 0.05, 0.5, 1.15, -0.1, 0.35)
        lbox(F, mat, s * 0.36 - 0.06, s * 0.36 + 0.06, 0.5, 0.7, -0.35, 0.2)
        for zz in (-0.3, 0.3):
            cyl('walnut_panel', F @ Vector((s * 0.33, 0, zz)), 0.3, 0.03, 0.025, seg=6)
    collide_local(F, -0.42, 0.42, 0, 1.25, -0.37, 0.4)


def pedestal_table(x, z, lamp=True, r=0.4):
    cyl('walnut_panel', (x, 0, z), 0.08, 0.28, 0.22, seg=12)
    cyl('walnut_panel', (x, 0.08, z), 0.6, 0.05, 0.07, seg=10)
    cyl('walnut_panel', (x, 0.68, z), 0.04, r, r, seg=20)
    if lamp:  # an oil lamp with a frosted globe
        cyl('brass', (x, 0.72, z), 0.2, 0.08, 0.04, seg=10)
        sphere('lamp_glass', (x, 1.0, z), 0.1, 10)
        cyl('lamp_glass', (x, 1.08, z), 0.14, 0.03, 0.025, seg=8)
    collide(x - r, 0, z - r, x + r, 0.75, z + r)


def fern(x, z, s=1.0):
    cyl('brass', (x, 0, z), 0.45 * s, 0.2 * s, 0.28 * s, seg=12)
    for k in range(10):
        a = 2 * math.pi * k / 10
        tip = Vector((x + math.cos(a) * 0.7 * s, 0.15 * s, z + math.sin(a) * 0.7 * s))
        mid = Vector((x + math.cos(a) * 0.35 * s, 0.85 * s, z + math.sin(a) * 0.35 * s))
        base = Vector((x, 0.45 * s, z))
        side = Vector((-math.sin(a), 0, math.cos(a))) * 0.1 * s
        bm = bm_for('palm')
        bm.faces.new([bm.verts.new(p) for p in (base, mid - side, tip, mid + side)])
    collide(x - 0.3 * s, 0, z - 0.3 * s, x + 0.3 * s, 0.5 * s, z + 0.3 * s)


def longcase_clock(x, z, rot):
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, 'walnut_panel', -0.3, 0.3, 0, 0.5, -0.2, 0.2)
    lbox(F, 'walnut_panel', -0.22, 0.22, 0.5, 1.7, -0.15, 0.15)
    lbox(F, 'glass_dark', -0.12, 0.12, 0.7, 1.55, 0.15, 0.16)
    cyl('brass', F @ Vector((0, 0.9, 0.12)), 0.01, 0.09, seg=12, axis=F.to_3x3() @ Vector((0, 0, 1)))  # pendulum bob
    lbox(F, 'walnut_panel', -0.3, 0.3, 1.7, 2.3, -0.2, 0.2)
    cyl('clock_face', F @ Vector((0, 2.0, 0.2)), 0.01, 0.2, seg=20, axis=F.to_3x3() @ Vector((0, 0, 1)))
    lbox(F, 'walnut_panel', -0.34, 0.34, 2.3, 2.4, -0.23, 0.23)
    for s in (-1, 0, 1):
        sphere('brass', F @ Vector((s * 0.25, 2.5, 0)), 0.04, 6)
    collide_local(F, -0.3, 0.3, 0, 2.4, -0.2, 0.2)


def amphora(x, y, z, s=1.0, mat='plaster_cast'):
    prof = [(0.08, 0), (0.14, 0.05), (0.22, 0.35), (0.2, 0.55), (0.08, 0.72), (0.07, 0.85), (0.11, 0.9)]
    for (r0, h0), (r1, h1) in zip(prof, prof[1:]):
        cyl(mat, (x, y + h0 * s, z), (h1 - h0) * s, r0 * s, r1 * s, seg=14, cap=False)
    for side in (-1, 1):
        tube(mat, [(x + side * 0.08 * s, y + 0.82 * s, z), (x + side * 0.2 * s, y + 0.8 * s, z), (x + side * 0.18 * s, y + 0.55 * s, z)], 0.015 * s)


def plinth(x, z, h=1.0, w=0.45, mat='marble_white'):
    wbox(mat, x - w / 2, x + w / 2, 0, h, z - w / 2, z + w / 2)
    wbox(mat, x - w / 2 - 0.05, x + w / 2 + 0.05, h, h + 0.06, z - w / 2 - 0.05, z + w / 2 + 0.05)
    collide(x - w / 2, 0, z - w / 2, x + w / 2, h, z + w / 2)


def umbrella_stand(x, z):
    cyl('brass', (x, 0, z), 0.6, 0.15, 0.16, seg=12)
    for k in range(4):
        a = k * 1.6
        tube('ebony_panel', [(x + math.cos(a) * 0.06, 0.05, z + math.sin(a) * 0.06), (x + math.cos(a) * 0.1, 0.95, z + math.sin(a) * 0.1)], 0.012, 6)
        sphere('brass' if k % 2 else 'gilt_frame', (x + math.cos(a) * 0.1, 0.97, z + math.sin(a) * 0.1), 0.025, 6)
    collide(x - 0.17, 0, z - 0.17, x + 0.17, 0.6, z + 0.17)


def globe(x, z):
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube('walnut_panel', [(x + math.cos(a) * 0.3, 0, z + math.sin(a) * 0.3), (x, 0.55, z)], 0.025, 6)
    sphere('globe', (x, 0.9, z), 0.32, 16)
    tube('brass', [(x - 0.1, 0.55, z - 0.3), (x + 0.1, 1.25, z + 0.3)], 0.012)
    pts = [(x + 0.36 * math.cos(t), 0.9 + 0.36 * math.sin(t), z) for t in np.linspace(-1.2, 4.3, 14)]
    tube('brass', pts, 0.012, 4)
    collide(x - 0.35, 0, z - 0.35, x + 0.35, 1.2, z + 0.35)


def library_ladder(x0, x1, z, lean=-0.9):
    tube('brass', [(x0, 3.0, z), (x1, 3.0, z)], 0.02)
    lx = (x0 + x1) / 2
    for s in (-0.22, 0.22):
        tube('oak_panel', [(lx + s, 3.0, z), (lx + s * 1.1, 0.02, z + lean)], 0.025)
    for k in range(1, 10):
        t = k / 10
        y = 3.0 * (1 - t); zz = z + lean * t
        tube('oak_panel', [(lx - 0.22, y, zz), (lx + 0.22, y, zz)], 0.015)


def card_catalogue(x, z, rot):
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, 'oak_panel', -0.6, 0.6, 0, 1.2, -0.25, 0.25)
    for i in range(6):
        for j in range(4):
            u = -0.5 + i * 0.2; v = 0.15 + j * 0.25
            lbox(F, 'oak_panel', u - 0.08, u + 0.08, v, v + 0.18, 0.25, 0.27)
            sphere('brass', F @ Vector((u, v + 0.09, 0.29)), 0.012, 4)
    collide_local(F, -0.6, 0.6, 0, 1.2, -0.25, 0.27)


def grand_piano(x, z, rot):
    """A grand: the curved case, three turned legs, the lid propped open, the music desk and a bench."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    outline = [(-0.75, 0)] + [(-0.75 + 1.5 * t, 0) for t in (0.33, 0.66, 1.0)] + \
              [(0.75 - 0.35 * (1 - math.cos(a)), 1.9 * math.sin(a)) for a in np.linspace(0.2, math.pi / 2, 7)] + \
              [(-0.45, 2.0), (-0.75, 1.6)]
    bm = bm_for('ebony_panel')
    for y0, y1 in ((0.7, 1.0),):
        bot = [bm.verts.new(F @ Vector((u, y0, w))) for u, w in outline]
        top = [bm.verts.new(F @ Vector((u, y1, w))) for u, w in outline]
        bm.faces.new(top)
        bm.faces.new(bot[::-1])
        for i in range(len(outline)):
            j = (i + 1) % len(outline)
            bm.faces.new((bot[i], bot[j], top[j], top[i]))
    lid = [F @ Vector((u, 1.02, w)) for u, w in outline]
    hinge_u = -0.75
    lid = [Vector((p.x, p.y + max(0, (F.inverted() @ p).x - hinge_u) * 0.55, p.z)) for p in lid]
    bm.faces.new([bm.verts.new(p) for p in lid])
    for (u, w) in ((-0.6, 0.15), (0.6, 0.15), (0.0, 1.8)):
        cyl('ebony_panel', F @ Vector((u, 0, w)), 0.7, 0.06, 0.05, seg=8)
    lbox(F, 'clock_face', -0.7, 0.7, 0.92, 0.96, -0.2, 0.0)  # the keys
    lbox(F, 'ebony_panel', -0.4, 0.4, 1.0, 1.35, 0.15, 0.18)
    lbox(F, 'ebony_panel', -0.45, 0.45, 0.42, 0.5, -0.75, -0.45)  # bench
    for s in (-1, 1):
        lbox(F, 'ebony_panel', s * 0.4 - 0.03, s * 0.4 + 0.03, 0, 0.42, -0.72, -0.48)
    collide_local(F, -0.8, 0.8, 0, 1.4, -0.8, 2.05)


def sconce(F, u, v, w=0.0):
    """A gas bracket on the wall: a brass arm and a frosted tulip shade."""
    a = F @ Vector((u, v, w)); b = F @ Vector((u, v + 0.1, w + 0.3))
    tube('brass', [a, b], 0.015, 6)
    lbox(F, 'brass', u - 0.06, u + 0.06, v - 0.1, v + 0.1, w, w + 0.03)
    sphere('lamp_glass', b + Vector((0, 0.08, 0)), 0.07, 8)


def ceiling_bosses(x0, x1, z0, z1, y, step=1.6):
    nx, nz = max(1, int((x1 - x0) / step)), max(1, int((z1 - z0) / step))
    for i in range(nx + 1):
        for k in range(nz + 1):
            sphere('gilt_frame', (x0 + i * (x1 - x0) / nx, y - 0.38, z0 + k * (z1 - z0) / nz), 0.07, 6)


def stair_runner():
    """A red runner with brass rods up the main flight of the grand stair."""
    rise, zf = 3.0 / 15, -0.1
    for k in range(15):
        y = (k + 1) * rise
        z = zf - k * 0.3
        wbox('velvet_red', -1.0, 1.0, y, y + 0.012, z - 0.3, z)
        wbox('velvet_red', -1.0, 1.0, y - rise, y, z - 0.012, z)
        tube('brass', [(-1.05, y + 0.012, z - 0.29), (1.05, y + 0.012, z - 0.29)], 0.01, 4)


# --- ground levels -------------------------------------------------------------------------
# The house stands on a terrace (y = 0) behind a granite retaining wall; California Street runs below it.
# The game walks Holmes over these levels with GROUND (exported in hopkins.json).

# Orientation: the lot is on the south side of California Street between Powell and Mason (999 California), so
# the house faces north (+z); +x is west (Mason Street, the hill falling away toward Pine), -x is east (Stanford's
# house, toward Powell). On California Street the terrace is only about a metre above the sidewalk, behind a low
# granite wall with an iron fence; the tall retaining walls are on Mason and Pine, where the ground drops.
STREET_Y = -1.0
WALL_Z0, WALL_Z1 = 25.4, 26.0
SZ = WALL_Z1 - 30.3  # the street's features were laid out for a fence at z = 30.3; they move with it
RAMPS = [  # x0, x1, z0, z1, y at z0, y at z1
    (-14.5, -9.5, 22.0, WALL_Z1, 0.0, STREET_Y),   # east carriage gate
    (9.5, 14.5, 22.0, WALL_Z1, 0.0, STREET_Y),     # west carriage gate
    (-1.6, 1.6, 24.4, WALL_Z1, 0.0, STREET_Y),     # the front steps
]


def ground(x, z):
    for x0, x1, z0, z1, y0, y1 in RAMPS:
        if x0 <= x <= x1 and z0 <= z <= z1:
            return y0 + (y1 - y0) * (z - z0) / (z1 - z0)
    return STREET_Y if z > WALL_Z1 else 0.0


# --- extra textures for the outside ---------------------------------------------------------

def foliage_tex(name, base='#22341c', size=256):
    n = noise(size, size, 4, 1) * 0.6 + noise(size, size, 16, 2) * 0.4
    col = hexrgb(base) * (0.55 + 0.9 * n)[..., None]
    return image(name, col), normal_map(name + '_n', n * 3)


def flowers_tex(name, size=256):
    rng = np.random.default_rng(9)
    col = hexrgb('#1e2e18') * (0.6 + 0.8 * noise(size, size, 6, 3))[..., None]
    for _ in range(900):
        y, x = rng.integers(0, size, 2)
        c = [hexrgb('#a02030'), hexrgb('#d8c8b0'), hexrgb('#c87830'), hexrgb('#6a3a8a')][rng.integers(4)]
        col[max(0, y - 2):y + 2, max(0, x - 2):x + 2] = c
    return image(name, col)


def cobble_tex(name, size=512):
    rng = np.random.default_rng(4)
    yy, xx = np.mgrid[0:size, 0:size]
    rows = 10
    rh = size / rows
    row = (yy / rh).astype(int)
    off = (row % 2) * 20
    w = 44
    fx = ((xx + off) % w) / w
    fy = (yy % rh) / rh
    inside = (fx > 0.08) & (fx < 0.92) & (fy > 0.1) & (fy < 0.9)
    ids = row * 50 + ((xx + off) // w).astype(int)
    tone = 0.6 + 0.5 * rng.random(rows * 50 + 60)[ids]
    col = np.where(inside[..., None], hexrgb('#5a5650') * tone[..., None], hexrgb('#1c1a16'))
    bump = np.where(inside, np.sin(np.clip(fx, 0, 1) * np.pi) * np.sin(np.clip(fy, 0, 1) * np.pi), 0)
    return image(name, col * (0.85 + 0.2 * noise(size, size, 5, 6))[..., None]), normal_map(name + '_n', bump * 3)


def flags_tex(name, size=512):
    yy, xx = np.mgrid[0:size, 0:size]
    seam = ((yy % 128) < 3) | ((xx % 170) < 3)
    col = hexrgb('#6e6a62') * (0.8 + 0.3 * noise(size, size, 40, 2) + 0.1 * noise(size, size, 4, 3))[..., None]
    col[seam] *= 0.55
    return image(name, col), normal_map(name + '_n', np.where(seam, 0.0, 1.0))


def brownstone_tex(name):
    return ashlar_tex(name, base='#6a4a3a', rows=5, per_row=2)


def exterior_materials():
    t, n = foliage_tex('hedge'); material('hedge', tex=t, nrm=n, rough=0.95, scale=1.2)
    t, n = foliage_tex('cypress', '#16261a'); material('cypress', tex=t, nrm=n, rough=0.95, scale=1.5)
    material('flowers', tex=flowers_tex('flowers'), rough=0.95, scale=1.5)
    t, n = cobble_tex('cobbles'); material('cobbles', tex=t, nrm=n, rough=0.55, scale=2.5)
    t, n = flags_tex('flags'); material('flags', tex=t, nrm=n, rough=0.8, scale=2.0)
    t, n = brownstone_tex('brownstone'); material('brownstone', tex=t, nrm=n, rough=0.85, scale=2.4)
    material('bronze', '#5a4a2a', rough=0.4, metal=0.9)
    material('water', '#0a1418', rough=0.05, metal=0.7)
    material('paint_white', '#d8d2c2', rough=0.7)
    material('carriage_black', '#0c0c0e', rough=0.25, metal=0.2)
    material('cablecar_red', '#5a1a14', rough=0.5)
    material('cablecar_cream', '#cbbf9a', rough=0.6)


# --- the castle's detail ---------------------------------------------------------------------

def quoins(x, z, y0, y1, sx, sz):
    """Alternating long and short corner stones up a corner at (x, z); sx, sz point outward."""
    k = 0
    y = y0
    while y < y1 - 0.2:
        a = 0.9 if k % 2 == 0 else 0.5
        wbox('trim_cream', min(x, x - sx * a), max(x, x - sx * a), y, y + 0.36, min(z, z + sz * 0.06), max(z, z + sz * 0.06))
        wbox('trim_cream', min(x, x + sx * 0.06), max(x, x + sx * 0.06), y, y + 0.36, min(z, z - sz * (1.4 - a)), max(z, z - sz * (1.4 - a)))
        y += 0.42; k += 1


def front_door():
    """The front entrance under the porte-cochere: clustered colonettes, a moulded pointed arch with a stained-glass
    tympanum, a stone threshold, and oak double doors standing open into the vestibule."""
    F = frame((0, 0, 14 + (T + 0.1) / 2), (1, 0, 0), (0, 0, 1))  # the outer face of the front wall, door centred at u = 0
    w, h = 2.4, 3.8                                             # the opening in the wall
    for s in (-1, 1):
        for k in range(3):  # stepped jambs of colonettes
            u = s * (w / 2 + 0.12 + k * 0.16)
            c = F @ Vector((u, 0.12, 0.08 + k * 0.1))
            cyl('trim_cream', c, h - 0.5, 0.07, seg=8)
            cyl('trim_cream', c, 0.18, 0.11, 0.1, seg=8)                       # base
            cyl('trim_cream', c + Vector((0, h - 0.62, 0)), 0.2, 0.08, 0.12, seg=8)  # capital
    # the moulded pointed arch: three orders springing from the capitals, a hood mould over them
    spring = h - 0.42
    for k in range(3):
        half = w / 2 + 0.12 + k * 0.16
        apex = spring + half * 1.1
        for s in (-1, 1):
            pts = [F @ Vector((s * half * math.cos(t), spring + (apex - spring) * math.sin(t), 0.1 + k * 0.1))
                   for t in np.linspace(0, math.pi / 2, 7)]
            tube('trim_cream', pts, 0.08, seg=6)
    half = w / 2 + 0.6
    apex = spring + half * 1.1
    for s in (-1, 1):
        pts = [F @ Vector((s * half * math.cos(t), spring + (apex - spring) * math.sin(t), 0.42)) for t in np.linspace(0, math.pi / 2, 8)]
        tube('trim_cream', pts, 0.07, seg=4)
        lbox(F, 'trim_cream', s * half - 0.12, s * half + 0.12, spring - 0.35, spring, 0, 0.45)  # label stops
    # the tympanum: the wall above the door filled with stained glass inside the arch
    bm = bm_for('stained')
    rim = [F @ Vector((w / 2 * math.cos(t), spring + w / 2 * 1.1 * math.sin(t), 0.02)) for t in np.linspace(0, math.pi, 13)]
    c = bm.verts.new(F @ Vector((0, spring + 0.1, 0.02)))
    vs = [bm.verts.new(p) for p in rim]
    for a_, b_ in zip(vs, vs[1:]):
        bm.faces.new((c, b_, a_))
    lbox(F, 'trim_cream', -w / 2, w / 2, spring, spring + 0.12, 0, 0.12)  # transom
    # threshold
    lbox(F, 'marble_white', -w / 2 - 0.2, w / 2 + 0.2, -0.05, 0.06, -0.45, 0.35)
    # double doors folded back inside, against the vestibule's side walls
    for s in (-1, 1):
        lw = 1.15
        x = s * (w / 2 - 0.06)
        G = frame((x, 0, 14 - (T + 0.1) / 2), (0, 0, -1), (-s, 0, 0))
        lbox(G, 'oak_panel', 0.02, lw, 0, spring - 0.05, 0, 0.07)
        for (v0, v1) in ((0.25, 1.2), (1.45, spring - 0.35)):
            lbox(G, 'oak_panel', 0.15, lw - 0.13, v0, v1, 0.07, 0.09)
        sphere('brass', G @ Vector((lw - 0.12, 1.1, 0.1)), 0.035, 6)
    # a lantern hanging in the doorway's arch
    tube('iron', [F @ Vector((0, apex - 0.2, 0.6)), F @ Vector((0, apex - 0.7, 0.6))], 0.015)
    cyl('lamp_glass', F @ Vector((0, apex - 1.05, 0.6)), 0.35, 0.09, 0.13, seg=6)


def pinnacle(x, y, z, h=1.8, r=0.22):
    """A Gothic pinnacle: a square shaft with a gablet band and a spirelet with a finial."""
    cyl('ashlar', (x, y, z), h * 0.45, r, r, seg=4)
    cyl('trim_cream', (x, y + h * 0.45, z), 0.12, r * 1.25, r * 1.25, seg=4)
    cyl('ashlar', (x, y + h * 0.45 + 0.12, z), h * 0.55, r * 1.05, 0.02, seg=4)
    sphere('trim_cream', (x, y + h + 0.15, z), 0.07, 6)


def buttress(F, u, y1, depth=0.6, w=0.5):
    """A stepped buttress on a facade frame, rising to y1 with a pinnacle above the parapet."""
    lbox(F, 'ashlar', u - w / 2, u + w / 2, -0.1, y1 * 0.45, 0, depth)
    lbox(F, 'trim_cream', u - w / 2 - 0.03, u + w / 2 + 0.03, y1 * 0.45, y1 * 0.45 + 0.12, 0, depth + 0.05)
    lbox(F, 'ashlar', u - w / 2 + 0.05, u + w / 2 - 0.05, y1 * 0.45 + 0.12, y1, 0, depth * 0.65)
    lbox(F, 'trim_cream', u - w / 2, u + w / 2, y1, y1 + 0.12, 0, depth * 0.7)
    p = F @ Vector((u, y1 + 0.12, depth * 0.35))
    pinnacle(p.x, p.y, p.z)


def window_surround(F, u, v, w, h):
    """The outside dressing of a ground-floor window: jambs, sill, a pointed hood mould on label stops."""
    lbox(F, 'trim_cream', u - w / 2 - 0.16, u - w / 2, v, v + h, 0, 0.14)
    lbox(F, 'trim_cream', u + w / 2, u + w / 2 + 0.16, v, v + h, 0, 0.14)
    lbox(F, 'trim_cream', u - w / 2 - 0.25, u + w / 2 + 0.25, v - 0.14, v, 0, 0.22)
    hh = w * 0.6
    for s in (-1, 1):
        a = F @ Vector((u + s * (w / 2 + 0.16), v + h, 0.1))
        b = F @ Vector((u, v + h + hh, 0.1))
        tube('trim_cream', [a, b], 0.09, seg=4)
        lbox(F, 'trim_cream', u + s * (w / 2 + 0.2) - 0.08, u + s * (w / 2 + 0.2) + 0.08, v + h - 0.25, v + h, 0, 0.2)  # label stop
    # tracery in the head: a quatrefoil
    c = F @ Vector((u, v + h + hh * 0.45, 0.06))
    nrm = (F.to_3x3() @ Vector((0, 0, 1))).normalized()
    cyl('trim_cream', c, 0.05, w * 0.2, seg=12, axis=nrm, cap=True)
    cyl('glass_dark', c + nrm * 0.05, 0.01, w * 0.13, seg=12, axis=nrm, cap=True)


def bargeboard(x0, x1, z, y, rise, out):
    """Carved bargeboards along a gable's two rakes, with a hanging finial at the apex."""
    xm = (x0 + x1) / 2
    for a, b in (((x0, y), (xm, y + rise)), ((x1, y), (xm, y + rise))):
        A = Vector((a[0], a[1] - 0.1, z + out)); B = Vector((b[0], b[1] - 0.1, z + out))
        tube('trim_dark', [A, B], 0.11, seg=4)
        n = int((B - A).length / 0.6)
        for k in range(1, n):
            p = A.lerp(B, k / n)
            tube('trim_dark', [p, p + Vector((0, -0.35, 0))], 0.035, seg=4)  # dropped tracery
    top = Vector((xm, y + rise - 0.1, z + out))
    tube('trim_dark', [top + Vector((0, 0.9, 0)), top + Vector((0, -1.0, 0))], 0.06, seg=6)
    sphere('trim_dark', top + Vector((0, -1.05, 0)), 0.1, 6)


def chimney_stack(x, z, y0, y1, n=3):
    for k in range(n):
        cx = x + (k - (n - 1) / 2) * 0.55
        cyl('brick_red', (cx, y0, z), y1 - y0, 0.2, 0.2, seg=8)
        cyl('trim_cream', (cx, y1, z), 0.12, 0.28, 0.26, seg=8)
        cyl('iron', (cx, y1 + 0.12, z), 0.35, 0.12, 0.1, seg=8)
    wbox('ashlar', x - n * 0.32, x + n * 0.32, y0 - 1.0, y0 + 0.6, z - 0.4, z + 0.4)


def cresting(x0, x1, y, z):
    """Iron cresting along a ridge: a rail with fleurs at intervals."""
    tube('iron', [(x0, y + 0.25, z), (x1, y + 0.25, z)], 0.015, 4)
    for x in np.arange(x0, x1, 0.4):
        tube('iron', [(x, y, z), (x, y + 0.42, z)], 0.012, 4)
        sphere('iron', (x, y + 0.45, z), 0.03, 4)


def dormer(x, y, z, facing, w=1.4, h=1.8):
    """A small gabled dormer window on a roof slope."""
    F = frame((x, y, z), (1, 0, 0) if facing[2] else (0, 0, -facing[0]), facing)
    lbox(F, 'ashlar', -w / 2, w / 2, 0, h, -0.6, 0)
    lancet(F, 0, 0.3, 0.6, 1.0, lit=rnd.random() < 0.3)
    bm = bm_for('slate')
    for s in (-1, 1):
        q = [F @ Vector(p) for p in ((s * (w / 2 + 0.15), h, 0.15), (0, h + 0.8, 0.15), (0, h + 0.8, -1.4), (s * (w / 2 + 0.15), h, -1.4))]
        bm.faces.new([bm.verts.new(p) for p in q])


def veranda(x, z0, z1, depth=3.0, h=3.6):
    """A Gothic veranda along the west side: clustered iron columns, pointed arches, a lead roof."""
    xo = x - depth
    wbox('flags', xo, x, -0.1, 0.05, z0, z1)
    n = int((z1 - z0) / 2.4)
    for k in range(n + 1):
        z = z0 + k * (z1 - z0) / n
        for dz in (-0.07, 0.07):
            cyl('iron', (xo + 0.2, 0.05, z + dz), h - 0.05, 0.05, seg=8)
        cyl('iron', (xo + 0.2, h - 0.3, z), 0.3, 0.1, 0.16, seg=8)
        collide(xo + 0.05, 0, z - 0.15, xo + 0.35, h, z + 0.15)
        if k < n:
            za = z; zb = z0 + (k + 1) * (z1 - z0) / n
            zm = (za + zb) / 2
            for a, b in (((xo + 0.2, h - 0.6, za), (xo + 0.2, h - 0.1, zm)), ((xo + 0.2, h - 0.1, zm), (xo + 0.2, h - 0.6, zb))):
                tube('iron', [a, b], 0.04, 4)
            # a railing between the columns, open at the steps in the middle
            if abs((za + zb) / 2 - (z0 + z1) / 2) > 1.2:
                tube('iron', [(xo + 0.2, 0.9, za), (xo + 0.2, 0.9, zb)], 0.025, 4)
                for zz in np.arange(za + 0.15, zb, 0.15):
                    tube('iron', [(xo + 0.2, 0.05, zz), (xo + 0.2, 0.9, zz)], 0.008, 4)
    bm = bm_for('slate')
    q = [(xo - 0.3, h, z0 - 0.3), (xo - 0.3, h, z1 + 0.3), (x, h + 1.2, z1 + 0.3), (x, h + 1.2, z0 - 0.3)]
    bm.faces.new([bm.verts.new(p) for p in q])
    wbox('trim_cream', xo - 0.35, xo - 0.2, h - 0.25, h, z0 - 0.3, z1 + 0.3)
    zm = (z0 + z1) / 2
    collide(xo - 0.1, 0, z0, xo + 0.3, 1.0, zm - 1.0)  # the railing, with a gap at the steps
    collide(xo - 0.1, 0, zm + 1.0, xo + 0.3, 1.0, z1)
    for k in range(2):
        wbox('flags', xo - 0.4 - k * 0.35, xo - k * 0.35, -0.1, 0.05 - (k + 1) * 0.0, (z0 + z1) / 2 - 1, (z0 + z1) / 2 + 1)
    LAMPS.append([xo + 1.2, h - 0.5, (z0 + z1) / 2])
    tube('iron', [(xo + 1.2, h, (z0 + z1) / 2), (xo + 1.2, h - 0.35, (z0 + z1) / 2)], 0.015)
    sphere('lamp_glass', (xo + 1.2, h - 0.5, (z0 + z1) / 2), 0.14, 10)


def castle_detail():
    up1 = 11.0
    # plinth all round
    for (a, b) in (((-15, 14), (15, 14)), ((15, 14), (15, -14)), ((15, -14), (7, -14)), ((-7, -14), (-15, -14)), ((-15, -14), (-15, 14))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        r = (B - A).normalized(); n = outward(A, B, Vector((0, 0, 0)))
        F = frame(A, r, n) @ Matrix.Translation((0, 0, T / 2 + 0.05))
        L = (B - A).length
        # broken where the front door is (the front wall's door spans x = -1.2 .. 1.2)
        runs = [(-0.2, 13.8), (16.2, L + 0.2)] if a == (-15, 14) and b == (15, 14) else [(-0.2, L + 0.2)]
        for u0, u1 in runs:
            lbox(F, 'ashlar', u0, u1, -0.1, 0.7, 0, 0.18)
            lbox(F, 'trim_cream', u0, u1, 0.7, 0.82, 0, 0.12)
    front_door()
    # quoins at the corners
    for (x, z, sx, sz) in ((-15.22, 14.22, -1, 1), (15.22, 14.22, 1, 1), (15.22, -14.22, 1, -1), (-15.22, -14.22, -1, -1)):
        quoins(x, z, 0.8, up1, sx, sz)
    # exterior surrounds for the ground-floor windows, and buttresses between the bays
    front = frame((-15, 0, 14 + T / 2 + 0.05), (1, 0, 0), (0, 0, 1))
    for u in (3, 9, 21, 27):
        window_surround(front, u, 1.2, 1.2, 2.8)
    for u in (6, 24):
        buttress(front, u, up1)
    west = frame((-15 - T / 2 - 0.05, 0, 14), (0, 0, -1), (-1, 0, 0))
    for u in (2, 6, 10, 14, 18, 24):  # u runs from the front corner (z = 14) toward the back
        window_surround(west, u, 1.2, 1.2, 2.8)
    for u in (8, 21):
        buttress(west, u, up1)
    east = frame((15 + T / 2 + 0.05, 0, -14), (0, 0, 1), (1, 0, 0))
    for u in (2, 6, 10, 18, 24):  # u runs from the back corner (z = -14) toward the front
        window_surround(east, u, 1.2, 1.2, 2.8)
    for u in (14, 21):
        buttress(east, u, up1)
    # the west veranda, outside the library and the Moorish room
    veranda(-15.2 - 0.35, -4.5, 11.5)
    # bargeboards and finials on the front cross gables, a rose window in each
    for x in (-11, 11):
        bargeboard(x - 3.4, x + 3.4, 14.6, up1 + 0.7, 5.5, 0.05)
        c = Vector((x, up1 + 2.6, 14.62))
        cyl('trim_cream', c, 0.15, 1.0, seg=24, axis=(0, 0, 1))
        cyl('stained', c + Vector((0, 0, 0.15)), 0.02, 0.85, seg=24, axis=(0, 0, 1))
        for k in range(8):
            a = k * math.pi / 4
            tube('trim_cream', [c + Vector((0, 0, 0.18)), c + Vector((math.cos(a) * 0.85, math.sin(a) * 0.85, 0.18))], 0.03, 4)
    # chimneys through the main roof
    for (x, z) in ((-8, 4), (8, 4), (-10, -9), (4, -10)):
        chimney_stack(x, z, up1 + 5.5, up1 + 9.0)
    # cresting along the ridges
    cresting(-15.4, 15.4, up1 + 8.2, 0)
    tube('iron', [(0, 14.3 + 5.0, -6.4), (0, 14.3 + 5.0, 10.4)], 0.015, 4)
    # dormers on the side slopes of the main roof
    for x in (-9, -3, 3, 9):
        dormer(x, up1 + 2.8, -9.2, (0, 0, -1))
    # machicolations under the turret parapets
    for x in (-15, 15):
        for k in range(14):
            a = 2 * math.pi * k / 14
            F = Matrix.Translation((x + math.cos(a) * 2.55, 15.0, 14 + math.sin(a) * 2.55)) @ Matrix.Rotation(-a + math.pi / 2, 4, 'Y')
            lbox(F, 'trim_cream', -0.12, 0.12, -0.5, 0.0, -0.1, 0.2)
        cyl('trim_cream', (x, 14.9, 14), 0.15, 2.65, seg=20)
    # the tower: pinnacles at its corners and a flag
    for (x, z) in ((8, -7), (15, -7), (15, -14), (8, -14)):
        pinnacle(x, 25.4, z, h=2.6, r=0.3)
    flag_x, flag_z = 11.5, -10.5
    tube('iron', [(flag_x, 35.4, flag_z), (flag_x, 39.0, flag_z)], 0.03)
    bm = bm_for('cablecar_red')
    pts = [(flag_x, 38.9, flag_z), (flag_x + 1.6, 38.7, flag_z + 0.2), (flag_x + 1.6, 37.9, flag_z + 0.25), (flag_x, 38.1, flag_z)]
    bm.faces.new([bm.verts.new(p) for p in pts])


# --- grounds, street and neighbours ------------------------------------------------------------

def brougham(x, z, rot):
    """A closed carriage waiting under the porte-cochere (unhitched; the horses are round at the stable)."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, 'carriage_black', -0.7, 0.7, 0.75, 2.05, -0.9, 0.7)
    lbox(F, 'carriage_black', -0.75, 0.75, 2.05, 2.12, -0.95, 0.75)
    lbox(F, 'carriage_black', -0.6, 0.6, 0.85, 1.5, 0.7, 1.6)  # the driver's box and boot
    lbox(F, 'carriage_black', -0.5, 0.5, 1.5, 1.65, 1.2, 1.7)
    for s in (-1, 1):
        lbox(F, 'glass_lit2', s * 0.71 - 0.005, s * 0.71 + 0.005, 1.35, 1.85, -0.65, 0.05)
        lbox(F, 'brass', s * 0.72 - 0.01, s * 0.72 + 0.01, 1.1, 1.15, 0.1, 0.25)  # door handle
        for (zz, r) in ((-0.65, 0.55), (1.15, 0.42)):
            c = F @ Vector((s * 0.82, r, zz))
            ax = (F.to_3x3() @ Vector((1, 0, 0))).normalized()
            pts = [c + (F.to_3x3() @ Vector((0, math.sin(t) * r, math.cos(t) * r))) for t in np.linspace(0, 2 * math.pi, 17)]
            tube('carriage_black', pts, 0.03, 4)
            for t in np.linspace(0, math.pi, 7)[:-1]:
                d = F.to_3x3() @ Vector((0, math.sin(t) * r, math.cos(t) * r))
                tube('carriage_black', [c - d, c + d], 0.012, 4)
            cyl('brass', c - ax * 0.06, 0.12, 0.06, seg=8, axis=ax)
        # carriage lamps
        p = F @ Vector((s * 0.72, 1.7, 0.75))
        cyl('lamp_glass', p, 0.18, 0.06, 0.07, seg=6)
    tube('carriage_black', [F @ Vector((-0.2, 0.6, 1.6)), F @ Vector((-0.3, 0.55, 4.0))], 0.035)  # the shafts, resting
    tube('carriage_black', [F @ Vector((0.2, 0.6, 1.6)), F @ Vector((0.3, 0.55, 4.0))], 0.035)
    lo, hi = F @ Vector((-0.9, 0, -1.0)), F @ Vector((0.9, 2.1, 1.8))
    collide(min(lo.x, hi.x), 0, min(lo.z, hi.z), max(lo.x, hi.x), 2.1, max(lo.z, hi.z))


def fountain(x, z):
    cyl('granite', (x, 0, z), 0.5, 2.6, 2.7, seg=24)
    cyl('water', (x, 0.42, z), 0.03, 2.4, seg=24)
    cyl('granite', (x, 0.45, z), 1.2, 0.35, 0.25, seg=12)
    cyl('granite', (x, 1.65, z), 0.18, 1.1, 1.0, seg=16)
    cyl('water', (x, 1.78, z), 0.02, 0.95, seg=16)
    cyl('granite', (x, 1.83, z), 0.8, 0.15, 0.12, seg=10)
    cyl('granite', (x, 2.6, z), 0.12, 0.5, 0.45, seg=12)
    sphere('granite', (x, 2.85, z), 0.16, 8)
    collide(x - 2.6, 0, z - 2.6, x + 2.6, 0.6, z + 2.6)
    INTERACT.append(dict(id='fountain', label='The fountain', pos=[x, 0.8, z + 2.7], r=1.8))


def cypress(x, z, h=5.0, y=0.0):
    cyl('cypress', (x, y, z), h, 0.7, 0.05, seg=10)
    cyl('door_wood', (x, y, z), 0.4, 0.12, seg=6)


def hedge(x0, x1, z0, z1, h=0.9):
    wbox('hedge', x0, x1, -0.05, h, z0, z1)
    collide(x0, 0, z0, x1, h, z1)


def urn(x, y, z, s=1.0):
    cyl('iron', (x, y, z), 0.12 * s, 0.22 * s, 0.14 * s, seg=12)
    cyl('iron', (x, y + 0.12 * s, z), 0.35 * s, 0.16 * s, 0.3 * s, seg=12)
    cyl('iron', (x, y + 0.47 * s, z), 0.05 * s, 0.32 * s, 0.32 * s, seg=12)
    sphere('hedge', (x, y + 0.62 * s, z), 0.3 * s, 8)


def gate_pier(x, z, h):
    """A square granite gate pier with a moulded cap and a pyramid on top (as in the photographs)."""
    wbox('granite', x - 0.5, x + 0.5, STREET_Y, h, z - 0.5, z + 0.5)
    wbox('stone', x - 0.6, x + 0.6, h, h + 0.2, z - 0.6, z + 0.6)
    bm = bm_for('granite')
    c = [(x - 0.52, h + 0.2, z - 0.52), (x + 0.52, h + 0.2, z - 0.52), (x + 0.52, h + 0.2, z + 0.52), (x - 0.52, h + 0.2, z + 0.52)]
    for a, b in zip(c, c[1:] + c[:1]):
        bm.faces.new([bm.verts.new(p) for p in (a, b, (x, h + 0.85, z))])
    collide(x - 0.5, STREET_Y, z - 0.5, x + 0.5, h, z + 0.5)


def iron_gate_leaf(xh, s, z, y0, L=2.3, ang=1.3):
    """An iron gate leaf hinged at xh, closing toward s (+1/-1), standing open ang radians into the grounds."""
    d = Vector((s * math.cos(ang) * L, 0, -math.sin(ang) * L))
    A = Vector((xh, y0, z))
    tube('iron', [A + Vector((0, 0.1, 0)), A + d + Vector((0, 0.1, 0))], 0.025, 4)
    tube('iron', [A + Vector((0, 1.9, 0)), A + d + Vector((0, 1.7, 0))], 0.025, 4)
    for k in range(int(L / 0.14) + 1):
        p = A + d * (k / (L / 0.14))
        top = 2.0 - 0.3 * (k / (L / 0.14))
        tube('iron', [p + Vector((0, 0.1, 0)), p + Vector((0, top, 0))], 0.012, 4)
        sphere('iron', p + Vector((0, top + 0.05, 0)), 0.03, 4)


def street_and_neighbours():
    # the low granite wall along California Street with its coping and iron fence, the gates and the steps
    wall_top = 0.45
    segs = [(-40, -14.5), (-9.5, -1.6), (1.6, 9.5), (14.5, 40)]
    for a0, a1 in segs:
        wbox('granite', a0, a1, STREET_Y - 0.3, wall_top, WALL_Z0, WALL_Z1)
        wbox('trim_cream', a0, a1, wall_top, wall_top + 0.14, WALL_Z0 - 0.1, WALL_Z1 + 0.1)
        collide(a0, STREET_Y, WALL_Z0, a1, wall_top, WALL_Z1)
        # rustication on the street face: horizontal channels
        for y in np.arange(STREET_Y + 0.5, 0.5, 0.55):
            wbox('trim_dark', a0, a1, y, y + 0.04, WALL_Z1, WALL_Z1 + 0.02)
        # a railing of iron spears on the parapet
        for x in np.arange(a0 + 0.2, a1, 0.25):
            tube('iron', [(x, wall_top + 0.14, (WALL_Z0 + WALL_Z1) / 2), (x, wall_top + 1.35, (WALL_Z0 + WALL_Z1) / 2)], 0.012, 4)
            cyl('iron', (x, wall_top + 1.35, (WALL_Z0 + WALL_Z1) / 2), 0.12, 0.03, 0.0, seg=4, cap=False)
        for y in (wall_top + 0.35, wall_top + 1.2):
            tube('iron', [(a0, y, (WALL_Z0 + WALL_Z1) / 2), (a1, y, (WALL_Z0 + WALL_Z1) / 2)], 0.018, 4)
        collide(a0, wall_top, WALL_Z0, a1, wall_top + 1.4, WALL_Z1)
        # square piers along the fence between the gates
        k = a0 + 6.0
        while k < a1 - 3.0:
            gate_pier(k, (WALL_Z0 + WALL_Z1) / 2, 1.3)
            k += 6.0
    for x in (-14.5, -9.5, -1.6, 1.6, 9.5, 14.5):
        gate_pier(x, (WALL_Z0 + WALL_Z1) / 2, 1.9 if abs(x) > 2 else 1.6)
    for x in (-14.5, -9.5, 9.5, 14.5):
        LAMPS.append([x, 3.1, (WALL_Z0 + WALL_Z1) / 2])
        cyl('iron', (x, 2.7, (WALL_Z0 + WALL_Z1) / 2), 0.15, 0.08, seg=6)
        cyl('lamp_glass', (x, 2.85, (WALL_Z0 + WALL_Z1) / 2), 0.45, 0.14, 0.18, seg=6)
    # the carriage gates stand open, folded back against the cheek walls
    for (xh, s) in ((-14.1, 1), (-9.9, -1), (9.9, 1), (14.1, -1)):
        iron_gate_leaf(xh, s, WALL_Z0 - 0.1, ground(xh, WALL_Z0 - 0.1))
    # ramps up through the gates, with cheek walls; the front steps
    for x0, x1, z0, z1, y0, y1 in RAMPS:
        if x1 - x0 > 4:  # carriage ramp: a sloping gravel slab
            bm = bm_for('gravel')
            q = [(x0, y0 - 0.02, z0), (x1, y0 - 0.02, z0), (x1, y1 - 0.02, z1), (x0, y1 - 0.02, z1)]
            bm.faces.new([bm.verts.new(p) for p in q[::-1]])
        else:  # stone steps
            n = 12
            for k in range(n):
                za = z0 + (z1 - z0) * k / n; zb = z0 + (z1 - z0) * (k + 1) / n
                yk = y0 + (y1 - y0) * (k + 0.5) / n
                wbox('stone', x0, x1, STREET_Y - 0.2, yk, za, zb)
        for x in (x0, x1):
            s = -1 if x == x0 else 1
            wbox('granite', min(x, x + s * 0.35), max(x, x + s * 0.35), STREET_Y - 0.2, 0.9, z0, z1)
            collide(min(x, x + s * 0.35), STREET_Y, z0, max(x, x + s * 0.35), 0.9, z1)
    # California Street: flagged sidewalks, the granite kerb, cobbles and the cable car slot
    wbox('flags', -80, 80, STREET_Y - 0.3, STREET_Y, WALL_Z1, 33.3 + SZ)
    wbox('granite', -80, 80, STREET_Y - 0.3, STREET_Y, 33.3 + SZ, 33.5 + SZ)
    wbox('cobbles', -80, 80, STREET_Y - 0.45, STREET_Y - 0.15, 33.5 + SZ, 45.5 + SZ)
    wbox('granite', -80, 80, STREET_Y - 0.3, STREET_Y, 45.5 + SZ, 45.7 + SZ)
    wbox('flags', -80, 80, STREET_Y - 0.3, STREET_Y, 45.7 + SZ, 49.0 + SZ)
    for z in (38.6 + SZ, 39.4 + SZ, 40.6 + SZ, 41.4 + SZ):  # rails for the up and down tracks
        wbox('iron', -80, 80, STREET_Y - 0.15, STREET_Y - 0.13, z - 0.04, z + 0.04)
    for z in (39.0 + SZ, 41.0 + SZ):  # the cable slots
        wbox('roof', -80, 80, STREET_Y - 0.15, STREET_Y - 0.14, z - 0.015, z + 0.015)
    # street lamps on both sidewalks
    for x in (-30, -12, 6, 24):
        LAMPS.append(list(gas_lamp(x, 32.6 + SZ, y=STREET_Y)))
    for x in (-21, -3, 15, 33):
        LAMPS.append(list(gas_lamp(x, 46.3 + SZ, y=STREET_Y)))
    for (x, z) in ((-30, 32.6 + SZ), (-12, 32.6 + SZ), (6, 32.6 + SZ), (24, 32.6 + SZ), (-21, 46.3 + SZ), (-3, 46.3 + SZ), (15, 46.3 + SZ), (33, 46.3 + SZ)):
        collide(x - 0.2, STREET_Y, z - 0.2, x + 0.2, STREET_Y + 3.5, z + 0.2)
    # a California Street cable car, standing on the down track at the end of its run
    cable_car(22, STREET_Y, 41.0 + SZ)
    # hitching posts on the far kerb
    for x in (-7, -5.5):
        cyl('iron', (x, STREET_Y, 45.9 + SZ), 1.0, 0.05, 0.04, seg=8)
        sphere('iron', (x, STREET_Y + 1.05, 45.9 + SZ), 0.07, 8)
    # the street ends: invisible walls so you stay on this block
    collide(-60, STREET_Y, WALL_Z1, -59, 3, 50 + SZ); collide(66, STREET_Y, WALL_Z1, 67, 3, 50 + SZ)
    collide(40.2, STREET_Y, WALL_Z0 - 0.4, 66, 3, WALL_Z1)  # (Mason Street falls away below the corner)
    collide(-60, STREET_Y, 49.0 + SZ, 67, 3, 49.3 + SZ)

    # across California and Mason Streets to the north-west: James Flood's brownstone (1886), its bronze fence
    flood(58.5, 98.5, 49.3 + SZ)
    # straight across California Street: two big Italianates (invented; the photographs do not show them)
    for (x0, x1, wall) in ((-44, -18, 'paint_white'), (-12, 14, 'brownstone')):
        mansion(frame((x1, STREET_Y + 1.2, 49.3 + SZ + 3.0), (-1, 0, 0), (0, 0, -1)), x1 - x0, 16, 11.0, wall=wall, lit_p=0.35, portico=4)
    # next door to the east (-x), toward Powell: Leland Stanford's house; to the west (+x) Mason Street falls
    # toward Pine below the terrace's tall retaining wall, with the Colton house beyond it
    with mirrored_x():
        stanford(44, -16, 18)
        mason_street()
    # Pine Street side: the terrace ends at a tall granite retaining wall
    wbox('granite', -41, 41, -7.0, 0.9, -18.3, -17.5)
    wbox('stone', -41.1, 41.1, 0.9, 1.05, -18.4, -17.4)
    collide(-41, -1.0, -18.3, 41, 2.0, -17.5)

def cable_car(x, y, z):
    L, W = 7.5, 2.4
    wbox('cablecar_red', x - L / 2, x + L / 2, y + 0.6, y + 1.3, z - W / 2, z + W / 2)
    wbox('cablecar_cream', x - L / 2, x + L / 2, y + 1.3, y + 2.6, z - W / 2 + 0.05, z + W / 2 - 0.05)
    for k in range(7):  # windows
        xx = x - L / 2 + 0.6 + k * (L - 1.2) / 6
        for s in (-1, 1):
            wbox('glass_lit0' if k % 2 else 'glass_dark', xx - 0.35, xx + 0.35, y + 1.45, y + 2.3, z + s * (W / 2 - 0.04) - 0.01, z + s * (W / 2 - 0.04) + 0.01)
    wbox('cablecar_red', x - L / 2 - 0.2, x + L / 2 + 0.2, y + 2.6, y + 2.75, z - W / 2 - 0.1, z + W / 2 + 0.1)
    wbox('cablecar_cream', x - L / 2 + 0.5, x + L / 2 - 0.5, y + 2.75, y + 3.0, z - 0.6, z + 0.6)  # clerestory
    for s in (-1, 1):
        for xx in (x - L / 2 + 1.0, x + L / 2 - 1.0):
            cyl('iron', (xx, y + 0.35, z + s * 0.8), 0.15, 0.35, seg=12, axis=(0, 0, 1))
    F = frame((x - 1.5, y + 1.95, z + W / 2 + 0.01), (1, 0, 0), (0, 0, 1))
    text('gilt', 'CALIFORNIA ST. R.R.', F, 1.5, 0, 0, 0.28)
    collide(x - L / 2, y, z - W / 2, x + L / 2, y + 3, z + W / 2)


def italianate_front(F, L, h, lit_p=0.3, trim='trim_cream'):
    """A big Italianate house front (for the neighbours), in facade frame F: tall windows with pediments,
    a bracketed cornice and a roof balustrade."""
    for fv in (1.4, 5.4) if h > 9 else (1.4,):
        for u in np.arange(1.8, L - 1.0, 2.6):
            lit = rnd.random() < lit_p
            lbox(F, 'glass_lit1' if lit else 'glass_dark', u - 0.55, u + 0.55, fv, fv + 2.6, 0, 0.02)
            lbox(F, trim, u - 0.7, u + 0.7, fv - 0.12, fv, 0, 0.15)
            lbox(F, trim, u - 0.7, u - 0.55, fv, fv + 2.6, 0, 0.08)
            lbox(F, trim, u + 0.55, u + 0.7, fv, fv + 2.6, 0, 0.08)
            bm = bm_for(trim)  # a pediment
            q = [F @ Vector(p) for p in ((u - 0.85, fv + 2.7, 0.15), (u + 0.85, fv + 2.7, 0.15), (u, fv + 3.15, 0.15))]
            bm.faces.new([bm.verts.new(p) for p in q])
    lbox(F, trim, 0, L, h - 0.9, h - 0.6, 0, 0.12)
    lbox(F, trim, -0.2, L + 0.2, h - 0.2, h, 0, 0.6)
    for u in np.arange(0.5, L, 0.9):
        lbox(F, trim, u - 0.07, u + 0.07, h - 0.6, h - 0.2, 0, 0.45)
    # a balustrade along the roof
    for u in np.arange(0.3, L, 0.35):
        cyl(trim, F @ Vector((u, h, 0.3)), 0.6, 0.06, seg=6)
    lbox(F, trim, 0, L, h + 0.6, h + 0.7, 0.1, 0.5)
    return F


def flood(x0, x1, z):
    y0 = STREET_Y + 1.0
    wbox('brownstone', x0, x1, y0 - 5, y0 + 13, z + 6, z + 24)
    italianate_front(frame((x1, y0, z + 6), (-1, 0, 0), (0, 0, -1)), x1 - x0, 13, lit_p=0.35)
    # the portico: four columns and an entablature over the steps
    xc = (x0 + x1) / 2
    for dx in (-2.2, -0.75, 0.75, 2.2):
        cyl('brownstone', (xc + dx, STREET_Y + 1.0, z + 4.6), 4.2, 0.28, 0.24, seg=12)
    wbox('brownstone', xc - 3, xc + 3, STREET_Y + 5.2, STREET_Y + 6.0, z + 4.0, z + 6.0)
    for k in range(6):
        wbox('brownstone', xc - 2.4 + k * 0.05, xc + 2.4 - k * 0.05, STREET_Y, STREET_Y + 1.0 - k * 0.16, z + 2.6 + k * 0.3, z + 6.0)
    # the bronze fence on its brownstone base, all along the sidewalk
    wbox('brownstone', x0 - 2, x1 + 2, STREET_Y, STREET_Y + 0.55, z, z + 0.4)
    for x in np.arange(x0 - 2, x1 + 2, 0.18):
        if abs(x - xc) < 1.6: continue
        tube('bronze', [(x, STREET_Y + 0.55, z + 0.2), (x, STREET_Y + 1.8, z + 0.2)], 0.018, 4)
        sphere('bronze', (x, STREET_Y + 1.85, z + 0.2), 0.035, 4)
    for y in (STREET_Y + 0.75, STREET_Y + 1.65):
        tube('bronze', [(x0 - 2, y, z + 0.2), (xc - 1.6, y, z + 0.2)], 0.025, 4)
        tube('bronze', [(xc + 1.6, y, z + 0.2), (x1 + 2, y, z + 0.2)], 0.025, 4)
    for x in np.arange(x0 - 2, x1 + 2.1, 3.0):
        wbox('bronze', x - 0.15, x + 0.15, STREET_Y + 0.55, STREET_Y + 2.0, z + 0.05, z + 0.35)
    INTERACT.append(dict(id='flood', label="Flood's bronze fence", pos=[x0 + 2.5, STREET_Y + 1.2, z - 0.4], r=2.2))
    # a garden behind the fence
    for x in np.arange(x0 - 1, x1 + 1, 4.0):
        cypress(x, z + 1.6, 4.0, STREET_Y)


def hip_roof(x0, x1, z0, z1, y, rise, mat='slate'):
    """A low hipped roof behind a cornice, the Italianate kind (the neighbours'; the castle has its gables)."""
    bm = bm_for(mat)
    i = min(x1 - x0, z1 - z0) / 2 * 0.95
    v = [bm.verts.new(q) for q in ((x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1),
                                   (x0 + i, y + rise, z0 + i), (x1 - i, y + rise, z0 + i),
                                   (x1 - i, y + rise, z1 - i), (x0 + i, y + rise, z1 - i))]
    for f in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[k] for k in f])


def mansion(F, L, D, h, wall='paint_white', trim='trim_cream', lit_p=0.4, portico=0, veranda=None):
    """A big Nob Hill Italianate in frame F (u along the front, w out of it, D deep behind it): a rusticated
    basement, two tall storeys with pedimented windows, quoins, a belt course, a bracketed cornice and roof
    balustrade, a hipped slate roof with chimneys. portico: columns across the middle of the front (the
    Colton house's two-storey Corinthian one, or a porch); veranda: (u0, u1) of a columned veranda."""
    lbox(F, wall, 0, L, -1.2, h, -D, 0)
    lbox(F, 'stone', -0.15, L + 0.15, -1.2, 1.0, 0, 0.16)                       # the basement
    for v in np.arange(-0.9, 1.0, 0.45):
        lbox(F, 'trim_dark', -0.15, L + 0.15, v, v + 0.04, 0.16, 0.17)
    lbox(F, trim, -0.1, L + 0.1, 4.7, 4.95, 0, 0.18)                             # belt course
    for u in (0.0, L):                                                           # quoins
        for k, v in enumerate(np.arange(1.0, h - 1.0, 0.6)):
            a = 0.55 if k % 2 else 0.35
            lbox(F, trim, u - a if u else -0.05, u + 0.05 if u else a, v, v + 0.5, 0, 0.08)
    italianate_front(F, L, h, lit_p=lit_p, trim=trim)
    if portico:
        c = L / 2
        cols = [c + (k - (portico - 1) / 2) * 2.0 for k in range(portico)]
        top = h - 1.0 if portico > 4 else 4.6
        for u in cols:
            cyl(trim, F @ Vector((u, 1.0, 2.6)), top - 1.6, 0.3, 0.26, seg=10)
            lbox(F, trim, u - 0.4, u + 0.4, 1.0, 1.3, 2.2, 3.0)                   # base
            lbox(F, trim, u - 0.42, u + 0.42, top - 0.6, top - 0.35, 2.18, 3.02)  # capital
        a, b = cols[0] - 0.8, cols[-1] + 0.8
        lbox(F, trim, a, b, top - 0.35, top + 0.5, 0, 3.2)                        # entablature
        if portico > 4:  # a pediment over it
            bm = bm_for(trim)
            q = [F @ Vector(p) for p in ((a, top + 0.5, 3.2), (b, top + 0.5, 3.2), (c, top + 2.3, 3.2))]
            bm.faces.new([bm.verts.new(p) for p in q])
        else:  # a balustrade on the porch roof
            for u in np.arange(a + 0.2, b, 0.3):
                cyl(trim, F @ Vector((u, top + 0.5, 3.0)), 0.55, 0.05, seg=5)
            lbox(F, trim, a, b, top + 1.05, top + 1.15, 2.8, 3.2)
        for k in range(6):                                                        # the steps up to it
            lbox(F, 'stone', a + 0.6, b - 0.6, -1.2, -1.2 + (k + 1) * 0.37, 3.2 + (5 - k) * 0.4, 3.6 + (5 - k) * 0.4)
    if veranda:
        a, b = veranda
        for u in np.arange(a, b + 0.01, (b - a) / max(1, round((b - a) / 2.4))):
            cyl(trim, F @ Vector((u, 1.0, 2.4)), 3.4, 0.14, 0.12, seg=8)
        lbox(F, trim, a - 0.2, b + 0.2, 4.4, 4.75, 0, 2.6)
        lbox(F, 'stone', a - 0.2, b + 0.2, -1.2, 1.0, 0, 2.6)                    # its raised floor
        for u in np.arange(a, b, 0.25):
            cyl(trim, F @ Vector((u, 1.0, 2.45)), 0.75, 0.04, seg=5)
        lbox(F, trim, a, b, 1.75, 1.85, 2.35, 2.55)
    # the roof and its chimneys
    corners = [F @ Vector(p) for p in ((-0.4, 0, 0.4), (L + 0.4, 0, 0.4), (L + 0.4, 0, -D - 0.4), (-0.4, 0, -D - 0.4))]
    xs, zs = [p.x for p in corners], [p.z for p in corners]
    hip_roof(min(xs), max(xs), min(zs), max(zs), h + 0.7, 3.2)
    for t in (0.2, 0.8):
        p = F @ Vector((L * t, 0, -D * 0.5))
        wbox('brick_red', p.x - 0.45, p.x + 0.45, h + 1.0, h + 4.6, p.z - 0.3, p.z + 0.3)
        wbox(trim, p.x - 0.55, p.x + 0.55, h + 4.6, h + 4.8, p.z - 0.4, p.z + 0.4)


def stanford(x0, z0, z1):
    """Leland Stanford's house next door (1876, California and Powell), seen over the garden wall: a long pale
    Italianate whose side, with a veranda along it, faces the Hopkins lawn (-x); its front faces California
    Street (+z) behind a porch. (It was a flat box with windows painted on one side.)"""
    L = z1 - z0
    # r x up = out: the side faces -x with u running from z0 to z1, the front faces +z
    mansion(frame((x0, 0, z0), (0, 0, 1), (-1, 0, 0)), L, 20, 11.0, lit_p=0.45, veranda=(L * 0.3, L * 0.7))
    F = frame((x0, 0, z1), (1, 0, 0), (0, 0, 1))
    italianate_front(F, 20, 11.0, lit_p=0.5)
    lbox(F, 'stone', 6, 14, -1.2, 1.0, 0, 3.0)
    for u in (6.6, 9.0, 11.0, 13.4):
        cyl('trim_cream', F @ Vector((u, 1.0, 2.6)), 3.4, 0.16, 0.13, seg=8)
    lbox(F, 'trim_cream', 6, 14, 4.4, 4.8, 0, 3.0)
    # the garden wall between the two lots, with a coping and the tops of shrubs over it
    wbox('brick_red', x0 - 3.2, x0 - 2.8, -0.2, 1.9, z0 - 4, WALL_Z0)
    wbox('stone', x0 - 3.3, x0 - 2.7, 1.9, 2.05, z0 - 4, WALL_Z0)
    collide(x0 - 3.3, -0.2, z0 - 4, x0 - 2.7, 2.05, WALL_Z0)
    collide(x0 - 0.3, -1.2, z0, x0 + 20, 11.0, z1 + 3.0)   # the house itself


def colton(x0, z0, z1):
    """The Colton house across Mason Street (1872, California and Taylor; Huntington's from 1892): white, with
    the two-storey Corinthian portico everyone called the finest on the hill. Front to California Street."""
    W = x0 + 26
    mansion(frame((x0, 0, z1), (1, 0, 0), (0, 0, 1)), 26, z1 - z0, 11.0, lit_p=0.3, portico=6)
    italianate_front(frame((W, 0, z1), (0, 0, -1), (1, 0, 0)), z1 - z0, 11.0, lit_p=0.3)  # its side, toward us
    wbox('grass', x0 - 12, W + 12, -1.35, -1.2, z0 - 10, z1 + 8)
    for z in np.arange(z0 - 6, z1 + 6, 4.5):
        cypress(W + 5.5, z, 5.0, -1.2)


def mason_street():
    """Mason Street down the west side of the terrace (built at -x, then mirrored to +x by the caller): it falls
    from California Street toward Pine below the terrace's tall granite retaining wall; the Colton house beyond."""
    zn, zs, drop = WALL_Z0, -40.0, 7.0
    def y_at(z): return STREET_Y - drop * (zn - z) / (zn - zs) if z < zn else STREET_Y
    for (x0, x1, mat, dy) in ((-58, -44, 'cobbles', -0.15), (-44, -41, 'flags', 0.0), (-61, -58, 'flags', 0.0)):
        bm = bm_for(mat)
        q = [(x0, y_at(zs) + dy, zs), (x0, y_at(zn) + dy, zn), (x1, y_at(zn) + dy, zn), (x1, y_at(zs) + dy, zs)]
        bm.faces.new([bm.verts.new(p) for p in q])
    z = zn
    while z > -17.5:  # the retaining wall, stepping down with the street
        za = max(-17.5, z - 4.0)
        wbox('granite', -41, -40.2, y_at(za) - 0.3, 0.9, za, z)
        for y in np.arange(y_at(za) + 0.6, 0.6, 0.6):
            wbox('trim_dark', -41.02, -41.0, y, y + 0.04, za, z)
        z = za
    wbox('stone', -41.1, -40.1, 0.9, 1.05, -17.5, WALL_Z0)
    collide(-41, -8.0, -17.5, -40.2, 2.0, WALL_Z0)
    for z in (-12, 4, 20):
        LAMPS.append(list(gas_lamp(-43.4, z, y=y_at(z))))
    colton(-90, -16, 16)

def grounds_garden():
    # lawn in pieces, leaving the ramps open
    wbox('grass', -40, 40, -0.2, -0.05, -17.5, 22.0)
    xs = [-40, -14.85, -9.15, -1.95, 1.95, 9.15, 14.85, 40]
    for a, b in zip(xs[0::2], xs[1::2]):
        wbox('grass', a, b, -0.2, -0.05, 22.0, WALL_Z0)
    # the drive: a gravel loop from gate to porte-cochere to gate
    curve = [(-12 + 24 * t, 22.0 - 5.0 * math.sin(math.pi * t)) for t in np.linspace(0, 1, 33)]
    bm = bm_for('gravel')
    for a, b in zip(curve, curve[1:]):
        A, B = Vector((a[0], -0.04, a[1])), Vector((b[0], -0.04, b[1]))
        d = (B - A).normalized(); side = Vector((-d.z, 0, d.x)) * 2.4
        q = [A - side, B - side, B + side, A + side]
        bm.faces.new([bm.verts.new(p) for p in q])
    wbox('gravel', -4, 4, -0.045, -0.04, 14, 20)
    # lamps on posts along the outer edge of the drive
    for k in range(3, len(curve) - 3, 7):
        (ax, az), (bx, bz) = curve[k], curve[k + 1]
        d = Vector((bx - ax, 0, bz - az)).normalized()
        out = Vector((d.z, 0, -d.x))  # toward the house side of the loop
        p = Vector((ax, 0, az)) - out * 3.0
        LAMPS.append(list(gas_lamp(p.x, p.z, h=3.2)))
        collide(p.x - 0.2, 0, p.z - 0.2, p.x + 0.2, 3.2, p.z + 0.2)
    # a fountain in the turning circle, flower beds and clipped hedges
    fountain(-24, 16.0)
    for (x0, x1, z0, z1) in ((-30, -18, 20, 22), (18, 30, 20, 22), (-30, -18, 10, 12), (18, 30, 10, 12)):
        wbox('flowers', x0, x1, -0.05, 0.25, z0, z1)
        wbox('granite', x0 - 0.15, x1 + 0.15, -0.05, 0.3, z0 - 0.15, z0)
        wbox('granite', x0 - 0.15, x1 + 0.15, -0.05, 0.3, z1, z1 + 0.15)
    for (x0, x1, z0, z1) in ((-38, -17, 23.6, 24.6), (17, 38, 23.6, 24.6), (-38, -37, -16, WALL_Z0), (37, 38, -16, WALL_Z0)):
        hedge(x0, x1, z0, z1, 1.2)
    for (x, z) in ((-34, 22), (34, 22), (-34, 8), (34, 8), (-34, -6), (34, -6), (-24, -14), (24, -14), (-28, 2), (28, 2)):
        cypress(x, z, 6.0)
        collide(x - 0.7, 0, z - 0.7, x + 0.7, 6, z + 0.7)
    # urns on pedestals flanking the porch, stone benches by the fountain
    for x in (-4.6, 4.6):
        wbox('granite', x - 0.4, x + 0.4, 0, 1.0, 20.6, 21.4)
        urn(x, 1.0, 21.0)
        collide(x - 0.4, 0, 20.6, x + 0.4, 1.0, 21.4)
    for x in (-5.0, 5.0):
        wbox('granite', x - 1.0, x + 1.0, 0.42, 0.5, 22.9, 23.4)
        for dx in (-0.8, 0.8):
            wbox('granite', x + dx - 0.12, x + dx + 0.12, 0, 0.42, 23.0, 23.3)
        collide(x - 1.0, 0, 22.9, x + 1.0, 0.5, 23.4)
    # the carriage waiting under the porte-cochere
    brougham(-8.2, 19.2, math.pi / 2 - 0.45)  # drawn up on the drive, clear of the door


def build_grounds():
    exterior_materials()
    grounds_garden()
    street_and_neighbours()


DH_FRONT = 3.4



# --- the upper floor ------------------------------------------------------------------------------

UPPER_ROOMS = {
    'sitting': dict(name='The Front Sitting Room', rect=(-7, 7, 10, 14), wains='oak_panel', upper='fresco_louis', curtains='velvet_red'),
    'antique': dict(name='The Antique Room', rect=(-15, -7, 2, 14), wains='oak_panel', upper='studio_wall', curtains='velvet_green'),
    'bedroom': dict(name="Mrs. Hopkins's Bedroom", rect=(-15, -7, -6, 2), wains='rosewood_panel', upper='fresco_louis', curtains='velvet_red'),
    'prints': dict(name='The Print Room', rect=(-15, -7, -14, -6), wains='walnut_panel', upper='fresco_gothic', curtains='velvet_green'),
    'painting': dict(name='The Painting Studio', rect=(7, 15, 2, 14), wains='oak_panel', upper='studio_wall', curtains='velvet_green'),
    'sculpture': dict(name='The Sculpture Studio', rect=(7, 15, -6, 2), wains='oak_panel', upper='studio_wall', curtains=None),
    'landing': dict(name='The Tower Landing', rect=(7, 15, -14, -6), wains='oak_panel', upper='fresco_louis', curtains='velvet_red'),
}
EXTERIOR_LINES = (('x', -15), ('x', 15), ('z', 14), ('z', -14))


def upper_wall(a, b, doors=(), windows=(), mat='plaster', thick=T):
    """A wall on the upper floor, from the floor slab to the ceiling, with doors and windows at t (metres from a)."""
    ops = [(t, D, UF, UF + DH) for t in doors] + [(t, 0.9, UF + 0.9, UF + 3.3) for t in windows]
    F, _ = wall(a, b, UF - 0.5, UC, ops, mat=mat, thick=thick)
    for t in doors:
        door_leaves(F @ Matrix.Translation((0, UF, 0)), t, D, DH, 1, thick=thick)
        p = F @ Vector((t, 0, 0)); UPPER_DOORS.append((p.x, p.z))
    for t in windows:
        p = F @ Vector((t, 0, 0)); UPPER_WINDOWS.append((p.x, p.z))
    return F


def line_upper_room(key):
    """Panel, paper and curtain an upper room's four walls, leaving its doors and windows open."""
    room = UPPER_ROOMS[key]
    x0, x1, z0, z1 = room['rect']
    centre = Vector(((x0 + x1) / 2, 0, (z0 + z1) / 2))
    for (ax, az), (bx, bz) in (((x0, z0), (x1, z0)), ((x1, z0), (x1, z1)), ((x1, z1), (x0, z1)), ((x0, z1), (x0, z0))):
        A, B = Vector((ax, 0, az)), Vector((bx, 0, bz))
        rr = (B - A).normalized(); L = (B - A).length
        n_in = Vector((-rr.z, 0, rr.x))
        if n_in.dot(centre - A) < 0: n_in = -n_in
        on_ext = (ax == bx and ax in (-15, 15)) or (az == bz and az in (-14, 14)) or \
                 (ax == bx and abs(ax) == 7 and max(az, bz) <= -6)
        thick = T + 0.1 if on_ext else T
        F = frame(Vector((ax, UF, az)), rr, n_in)
        ops = []
        for (px, pz) in UPPER_DOORS + UPPER_WINDOWS:
            q = Vector((px, 0, pz)) - A
            t = q.dot(rr)
            if abs(q.dot(n_in)) < 0.3 and 0.5 < t < L - 0.5:
                is_door = (px, pz) in UPPER_DOORS
                ops.append((t, D, 0, DH) if is_door else (t, 0.9, 0.9, 3.3))
        lining(F, L, 1, ops, UC - UF, wains=room['wains'], upper=room['upper'], thick=thick,
               curtains=room['curtains'] if on_ext else None)


def statue(x, z, rot=0.0, h=1.7):
    """A plaster cast of a classical figure on its pedestal (the antique class drew from these)."""
    plinth(x, z, 0.9, 0.6, 'plaster_cast')
    F = Matrix.Translation((x, 0.96, z)) @ Matrix.Rotation(rot, 4, 'Y')
    k = h / 1.7
    cyl('plaster_cast', F @ Vector((0, 0, 0)), 0.75 * k, 0.24 * k, 0.17 * k, seg=12)          # draped legs
    cyl('plaster_cast', F @ Vector((0, 0.75 * k, 0)), 0.55 * k, 0.15 * k, 0.19 * k, seg=12)   # torso
    sphere('plaster_cast', F @ Vector((0, 1.38 * k, 0.02)), 0.12 * k, 12)                    # head
    cyl('plaster_cast', F @ Vector((0, 1.28 * k, 0)), 0.1 * k, 0.05 * k, seg=8)              # neck
    tube('plaster_cast', [F @ Vector((0.17 * k, 1.22 * k, 0)), F @ Vector((0.26 * k, 0.95 * k, 0.1 * k)),
                          F @ Vector((0.2 * k, 0.75 * k, 0.16 * k))], 0.05 * k, 8)
    tube('plaster_cast', [F @ Vector((-0.17 * k, 1.22 * k, 0)), F @ Vector((-0.3 * k, 1.35 * k, -0.05 * k)),
                          F @ Vector((-0.28 * k, 1.6 * k, -0.04 * k))], 0.05 * k, 8)


def donkey(x, z, rot):
    """A drawing donkey: the low bench students straddle, with a board propped at the front."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, 'oak_panel', -0.15, 0.15, 0.42, 0.47, -0.55, 0.55)
    for zz in (-0.45, 0.45):
        lbox(F, 'oak_panel', -0.14, 0.14, 0, 0.42, zz - 0.04, zz + 0.04)
    lbox(F, 'oak_panel', -0.25, 0.25, 0.47, 1.1, -0.62, -0.58)
    lbox(F, 'canvas', -0.24, 0.24, 0.6, 1.05, -0.58, -0.57)


def four_poster(x, z, rot):
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, 'rosewood_panel', -0.85, 0.85, 0.3, 0.6, -1.0, 1.1)
    lbox(F, 'canvas', -0.8, 0.8, 0.6, 0.78, -0.95, 1.05)                 # the mattress and sheets
    lbox(F, 'velvet_red', -0.82, 0.82, 0.62, 0.8, -0.6, 1.08)            # the coverlet
    lbox(F, 'clock_face', -0.7, -0.05, 0.78, 0.95, -0.95, -0.6)  # pillows
    lbox(F, 'clock_face', 0.05, 0.7, 0.78, 0.95, -0.95, -0.6)
    lbox(F, 'rosewood_panel', -0.85, 0.85, 0.3, 1.6, -1.05, -0.98)     # headboard
    for (u, w) in ((-0.85, -1.0), (0.85, -1.0), (-0.85, 1.1), (0.85, 1.1)):
        cyl('rosewood_panel', F @ Vector((u, 0, w)), 2.6, 0.06, 0.05, seg=8)
    lbox(F, 'rosewood_panel', -0.92, 0.92, 2.6, 2.85, -1.07, 1.17)      # tester
    for s in (-1, 1):                                                    # hangings, drawn back at the foot
        lbox(F, 'velvet_red', s * 0.88 - 0.03, s * 0.88 + 0.03, 0.4, 2.6, -1.0, -0.2)
        lbox(F, 'velvet_red', s * 0.88 - 0.03, s * 0.88 + 0.03, 0.4, 2.6, 0.85, 1.12)
    collide_local(F, -0.9, 0.9, 0, 2.85, -1.05, 1.15)


def cabinet(x, z, rot, w=1.2, h=2.2, d=0.55, mat='rosewood_panel', drawers=0):
    """A wardrobe, or (drawers > 0) a plan chest of wide shallow drawers."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, mat, -w / 2, w / 2, 0, h, -d / 2, d / 2)
    if drawers:
        for k in range(drawers):
            v = 0.1 + k * (h - 0.15) / drawers
            lbox(F, mat, -w / 2 + 0.04, w / 2 - 0.04, v, v + (h - 0.15) / drawers - 0.02, d / 2, d / 2 + 0.015)
            lbox(F, 'brass', -0.12, 0.12, v + 0.05, v + 0.08, d / 2 + 0.015, d / 2 + 0.035)
    else:
        for s in (-1, 1):
            lbox(F, mat, s * w / 4 - w / 4 + 0.03, s * w / 4 + w / 4 - 0.03, 0.15, h - 0.25, d / 2, d / 2 + 0.02)
            sphere('brass', F @ Vector((s * 0.06, h / 2, d / 2 + 0.04)), 0.025, 6)
        lbox(F, mat, -w / 2 - 0.05, w / 2 + 0.05, h, h + 0.12, -d / 2 - 0.04, d / 2 + 0.04)
    collide_local(F, -w / 2, w / 2, 0, h, -d / 2, d / 2 + 0.04)


def modelling_stand(x, z, idx):
    """A sculptor's stand: a tripod, a turntable and a clay bust under way."""
    for k in range(3):
        a = 2 * math.pi * k / 3
        tube('oak_panel', [(x + math.cos(a) * 0.35, 0, z + math.sin(a) * 0.35), (x, 1.0, z)], 0.03, 6)
    cyl('oak_panel', (x, 1.0, z), 0.06, 0.3, seg=14)
    cyl('clay', (x, 1.06, z), 0.18, 0.13, 0.1, seg=10)
    if idx % 2: sphere('clay', (x, 1.36, z), 0.13, 10)
    else: cyl('clay', (x, 1.24, z), 0.3, 0.12, 0.06, seg=8)
    collide(x - 0.35, 0, z - 0.35, x + 0.35, 1.5, z + 0.35)


class mirrored_x:
    """Build something, then mirror everything made inside the block across x = 0: geometry (faces turned back
    the right way out), colliders, lamps and interactions."""
    def __enter__(self):
        self.v = {m: len(bm.verts) for m, bm in BM.items()}
        self.f = {m: len(bm.faces) for m, bm in BM.items()}
        self.nc, self.nl, self.ni = len(COLLIDERS), len(LAMPS), len(INTERACT)
    def __exit__(self, *exc):
        for m, bm in BM.items():
            bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
            for v in bm.verts[self.v.get(m, 0):]:
                v.co.x = -v.co.x
            bmesh.ops.reverse_faces(bm, faces=list(bm.faces[self.f.get(m, 0):]))
        for c in COLLIDERS[self.nc:]:
            c[0], c[3] = -c[3], -c[0]
        for l in LAMPS[self.nl:]:
            l[0] = -l[0]
        for i in INTERACT[self.ni:]:
            i['pos'][0] = -i['pos'][0]


class lifted:
    """Build furniture with the ground-floor helpers, then raise everything made inside the block by dy:
    geometry, colliders and lamps."""
    def __init__(self, dy): self.dy = dy
    def __enter__(self):
        self.counts = {m: len(bm.verts) for m, bm in BM.items()}
        self.nc, self.nl = len(COLLIDERS), len(LAMPS)
    def __exit__(self, *exc):
        for m, bm in BM.items():
            bm.verts.ensure_lookup_table()
            for v in bm.verts[self.counts.get(m, 0):]:
                v.co.y += self.dy
        for c in COLLIDERS[self.nc:]:
            c[1] += self.dy; c[4] += self.dy
        for l in LAMPS[self.nl:]:
            l[1] += self.dy


def build_upper():
    material('studio_wall', '#a89e8a', rough=0.95)
    material('clay', '#6a5a48', rough=0.9)
    # the partitions and the walls not already there
    upper_wall((-15, 2), (-7, 2), doors=[4])
    upper_wall((-15, -6), (-7, -6), doors=[4])
    upper_wall((7, 2), (15, 2), doors=[4])
    upper_wall((7, -6), (15, -6), doors=[4])
    upper_wall((-7, 10), (-7, 14), doors=[2])
    upper_wall((7, 14), (7, 10), doors=[2])
    # over the solarium's glass roof the back rooms have outside walls with a window onto it
    for a, b in (((-7, -14), (-7, -6)), ((7, -6), (7, -14))):
        F = upper_wall(a, b, windows=[4], mat='ashlar', thick=T + 0.1)
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        n = outward(A, B, Vector((a[0] * 2, 0, -10)))
        Fo = frame(A, (B - A).normalized(), n) @ Matrix.Translation((0, 0, (T + 0.1) / 2))
        lancet(Fo, 4, UF + 0.9, 0.9, 2.4, glass='glass_clear')
    # floors, ceilings, lamps; the walkable areas
    rects = []
    for key, room in UPPER_ROOMS.items():
        x0, x1, z0, z1 = room['rect']
        floor('parquet', x0, x1, z0, z1, y=UF)
        coffered_ceiling(x0, x1, z0, z1, UC, beam='oak_panel', field=room['upper'] if 'fresco' in room['upper'] else 'trim_cream')
        gasolier((x0 + x1) / 2, UC - 0.35, (z0 + z1) / 2, drop=1.4)
        ceiling_bosses(x0, x1, z0, z1, UC)
        rects.append([x0, x1, z0, z1])
        ROOMS.append(dict(id=key, name=room['name'], x0=x0, z0=z0, x1=x1, z1=z1, y=UF))
    LEVELS.append(dict(y=UF, rects=rects))
    for key in UPPER_ROOMS:
        line_upper_room(key)
    with lifted(UF):
        furnish_upper()


def furnish_upper():
    """Upstairs furniture, laid out at floor level 0 (build_upper lifts it to the upper floor)."""
    Y = 0.0
    # the front sitting room: a fire, a sofa and chairs looking out over California Street
    fireplace(frame((-7, Y, 10 + T / 2), (1, 0, 0), (0, 0, 1)), 2.6, mat='marble_white', w=1.8)
    sofa(1.5, 11.6, 0, 'velvet_red', 2.2)
    for x in (-1.6, 4.4):
        wingback(x, 12.2, facing(x, 12.2, x, 14), 'velvet_red')
    pedestal_table(1.5, 12.8, lamp=True, r=0.35)
    rug(-3.5, 5.5, 10.6, 13.6, 1)
    # the antique room: casts of classical figures, students' donkeys and easels round them
    for (x, z, rot) in ((-11, 11.5, math.pi), (-13.5, 5.0, math.pi / 2), (-8.5, 5.0, -math.pi / 2)):
        statue(x, z, rot)
    for (x, z, tx, tz) in ((-11, 8.8, -11, 11.5), (-12.2, 7.6, -13.5, 5.0), (-9.8, 7.6, -8.5, 5.0), (-11, 4.6, -13.5, 5.0)):
        donkey(x, z, facing(x, z, tx, tz) + math.pi)
    for (x, z) in ((-14.2, 13.2), (-7.9, 13.2)):
        bust(x, 1.2, z)
    # Mrs. Hopkins's bedroom, kept as she left it: the four-poster, a wardrobe, a dressing table, the fire
    four_poster(-12.6, -2.2, math.pi / 2)
    cabinet(-8.0, -4.6, -math.pi / 2, w=1.4)
    cabinet(-14.5, 1.0, math.pi / 2, w=1.0, h=0.8, d=0.5, drawers=3)  # dressing table
    canvas('mirror', [(-14.72, Y + 0.95, 0.55), (-14.72, Y + 0.95, 1.45), (-14.72, Y + 1.9, 1.45), (-14.72, Y + 1.9, 0.55)])
    fireplace(frame((-15, Y, 2 - T / 2), (1, 0, 0), (0, 0, -1)), 1.6, mat='marble_white', w=1.6)
    sofa(-9.0, -0.4, -math.pi / 2, 'velvet_green', 1.6)
    rug(-14.2, -10.0, -4.2, 0.2, 2)
    # the print room: plan chests, a long table of prints laid out, portfolios
    for x in (-13.8, -11.4):
        cabinet(x, -13.4, 0, w=2.0, h=1.0, d=0.9, mat='walnut_panel', drawers=6)
    table(-11, -9.5, 3.2, 1.2, mat='walnut_panel', cloth='velvet_green')
    for k, x in enumerate((-12.0, -10.6, -9.4)):
        mat, a = PICTURES[(k * 7 + 2) % len(PICTURES)]
        w = 0.8; h = w / a
        canvas(mat, [(x - w / 2, Y + 0.765, -9.5 + h / 2), (x + w / 2, Y + 0.765, -9.5 + h / 2),
                     (x + w / 2, Y + 0.765, -9.5 - h / 2), (x - w / 2, Y + 0.765, -9.5 - h / 2)])
    INTERACT.append(dict(id='prints', label='Engravings laid out on the table', pos=[-11, UF + 0.9, -9.5], r=2.0))
    # the painting studio: easels round a model's throne, a still life, canvases stacked against the walls
    wbox('velvet_red', 10.3, 11.7, Y, Y + 0.4, 9.3, 10.7)
    collide(10.3, Y, 9.3, 11.7, Y + 0.4, 10.7)
    chair(11, 10.0, math.pi, 'velvet_red')
    for k in range(7):
        a = math.pi * (1.1 + k * 0.13)
        x, z = 11 + math.cos(a) * 3.0, 10 + math.sin(a) * 3.0
        easel(x, z, facing(x, z, 11, 10) + math.pi, k + 3)
    table(13.6, 4.0, 1.2, 0.8, mat='oak_panel', cloth='velvet_green')
    amphora(13.4, Y + 0.76, 4.0, 0.5, 'clay'); sphere('cablecar_red', (13.9, Y + 0.84, 3.8), 0.06, 8)
    sphere('cablecar_cream', (13.75, Y + 0.84, 4.25), 0.06, 8)
    for k in range(4):  # canvases leaning against the partition
        F = Matrix.Translation((8.2 + k * 0.25, Y, 2.35)) @ Matrix.Rotation(-0.25, 4, 'X')
        lbox(F, 'canvas', 0, 0.9 - k * 0.1, 0, 1.1 - k * 0.1, 0, 0.03)
    INTERACT.append(dict(id='studio', label="The model's throne", pos=[11, UF + 0.5, 10], r=2.0))
    # the sculpture studio: modelling stands, clay, a plaster figure, sacks of plaster
    for k, (x, z) in enumerate(((9.0, -3.5), (11.0, -1.5), (13.0, -3.5), (11.0, -4.8))):
        modelling_stand(x, z, k)
    statue(13.8, 0.8, math.pi * 0.75, h=1.8)
    for (x, z) in ((7.8, 1.2), (8.4, 1.3)):
        wbox('canvas', x - 0.25, x + 0.25, Y, Y + 0.45, z - 0.2, z + 0.2)
    # the tower landing: the spiral stair carries on up; a bench and pictures
    cx, cz = 11, -10
    cyl('walnut_panel', (cx, Y, cz), UC - UF, 0.15, seg=10)
    for k in range(14):
        a = k * 0.45 + 1.0
        F = Matrix.Translation((cx, Y + 0.2 + k * 0.33, cz)) @ Matrix.Rotation(-a, 4, 'Y')
        lbox(F, 'oak_panel', 0.15, 1.6, -0.05, 0.05, -0.25, 0.25)
    collide(cx - 1.7, Y, cz - 1.7, cx + 1.7, UC - UF, cz + 1.7)
    INTERACT.append(dict(id='tower2', label='Climb the tower', pos=[cx - 1.9, UF + 1.0, cz + 0.8], r=1.6, to='tower_room'))
    INTERACT.append(dict(id='bedroom', label="Mrs. Hopkins's bed", pos=[-12.6, UF + 0.9, -0.8], r=2.0))
    INTERACT.append(dict(id='casts', label='The antique casts', pos=[-11, UF + 1.0, 8.5], r=2.2))
    tw = frame((15 - (T + 0.1) / 2, Y, -6), (0, 0, -1), (-1, 0, 0))
    frame_painting(tw, 2.5, 1.6, 1.4, 1.1, 9)



def facing(x, z, tx, tz):
    """Rotation for a chair at (x, z) whose front (local -z) looks toward (tx, tz)."""
    return math.atan2(-(tx - x), -(tz - z))


def dress_rooms(R):
    """Fireplaces, rugs, furniture and the small things, room by room."""
    # vestibule: an umbrella stand of canes and sticks, a fern, a runner
    umbrella_stand(-2.4, 13.3)
    fern(2.4, 13.3, 0.9)
    rug(-1.2, 1.2, 10.5, 13.5, 3)
    # the grand hall: a fireplace on the west wall, the long-case clock, vases on plinths, ferns, the stair runner
    fireplace(frame((-7 + T / 2, 0, 10), (0, 0, -1), (1, 0, 0)), 8.0, mat='marble_white', w=2.4, h=1.6)
    longcase_clock(6.45, 9.2, -math.pi / 2)
    for (x, z) in ((-6.2, 3.6), (6.2, 3.6), (-6.2, -4.4), (6.2, -4.4)):
        plinth(x, z, 1.0)
        amphora(x, 1.06, z, 0.9)
    for x in (-4.2, 4.2):  # either side of the stair's foot, clear of the way under the landing
        fern(x, 0.6, 1.1)
    stair_runner()
    rug(-2.2, 2.2, 1.2, 7.8, 0)
    sofa(-4.0, 4.2, math.pi / 2, 'velvet_red', 2.0)
    sofa(4.0, 4.2, -math.pi / 2, 'velvet_red', 2.0)
    hf = frame((x0 := -7 + T / 2 + 0.05, 0, 10), (0, 0, -1), (1, 0, 0))
    for u in (5.2, 10.8):
        sconce(hf, u, 2.4, 0.04)
    # the library: the fire, wingbacks drawn up to it, the globe, a rolling ladder, the card catalogue, a rug
    fireplace(frame((-15, 0, 14 - (T + 0.1) / 2), (1, 0, 0), (0, 0, -1)), 5.7, mat='marble_black', w=2.0)
    for (x, z) in ((-10.6, 11.4), (-8.0, 11.4)):
        wingback(x, z, facing(x, z, -9.3, 13.5), 'velvet_green')
    pedestal_table(-9.3, 11.2, lamp=True, r=0.3)
    rug(-13.6, -8.4, 4.6, 11.6, 0)
    globe(-8.0, 4.0)
    library_ladder(-14.6, -13.0, 13.3)
    card_catalogue(-7.55, 12.6, -math.pi / 2)
    # the Moorish room: a rug, ferns in the corners
    rug(-13.0, -9.0, -4.8, 0.8, 1)
    fern(-14.2, 1.2, 0.9); fern(-7.9, -5.2, 0.9)
    # the director's room: the fire, armchairs, a rug, pictures either side of the window
    fireplace(frame((-15, 0, -6 - T / 2), (1, 0, 0), (0, 0, -1)), 1.9, mat='marble_white', w=1.8)
    rug(-13.6, -8.4, -12.8, -7.6, 2)
    wingback(-13.2, -8.4, facing(-13.2, -8.4, -11, -10), 'velvet_red')
    dw = frame((-15 + (T + 0.1) / 2, 0, -6), (0, 0, -1), (1, 0, 0))
    frame_painting(dw, 1.9, 1.8, 1.3, 1.1, 3)
    frame_painting(dw, 6.4, 1.8, 1.3, 1.1, 11)
    # the music room: the fire, the grand piano by the window, a rug under the chairs, music stands
    fireplace(frame((7, 0, 2 + T / 2), (1, 0, 0), (0, 0, 1)), 5.7, mat='oak_panel', w=1.8)
    grand_piano(9.4, 10.0, math.pi * 0.85)
    rug(7.8, 12.2, 3.4, 8.6, 2)
    for z in (9.0, 12.4):
        tube('brass', [(12.6, 0, z), (12.6, 1.1, z)], 0.012, 6)
        wbox('brass', 12.35, 12.85, 1.05, 1.4, z - 0.02, z + 0.02)
    mw = frame((7 + T / 2, 0, 14), (0, 0, -1), (1, 0, 0))
    frame_painting(mw, 1.8, 2.0, 1.6, 1.2, 14)
    # the life class: a fire for the model, a screen, a rug on the dais, the students' stools
    fireplace(frame((7, 0, -6 + T / 2), (1, 0, 0), (0, 0, 1)), 1.6, mat='oak_panel', w=1.6, mirror=False)
    sw = frame((15 - (T + 0.1) / 2, 0, -6), (0, 0, 1), (-1, 0, 0))
    for (u, idx) in ((2.5, 16), (6.5, 20)):
        frame_painting(sw, u + 1.0, 3.6, 1.0, 0.8, idx)
    # the tower stair: pictures going up, a fern
    tw = frame((7 + T / 2, 0, -14), (0, 0, 1), (1, 0, 0))
    frame_painting(tw, 3.0, 1.8, 1.4, 1.1, 22)
    fern(8.0, -6.8, 1.0)
    # the solarium: rugs on the marble and more ferns
    rug(-3.0, 3.0, -12.6, -8.0, 3)
    for x in (-5.5, 5.5):
        fern(x, -12.8, 1.2)
    # gilt bosses at the coffer crossings
    for k, r in R.items():
        if k in ('hall', 'solarium'): continue
        ceiling_bosses(r['x0'], r['x1'], r['z0'], r['z1'], r['ceil'])


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hopkins_materials()
    interior_materials()
    R, walls = build_house()
    build_hall(R)
    furnish(R)
    dress_rooms(R)
    build_solarium_glass()
    import hopkins_house; hopkins_house.build(sys.modules[__name__])  # the house's outside (art/hopkins_house.py)
    build_upper()
    build_grounds()
    root = finish('Hopkins')
    for k, p in enumerate(LAMPS):
        e = bpy.data.objects.new(f'Lamp_{k}', None)
        bpy.context.scene.collection.objects.link(e)
        e.location = p; e.parent = root
    os.makedirs(os.path.join(ROOT, 'art', 'set'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'art', 'set', 'hopkins.blend'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', 'hopkins.glb'), export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True, export_image_format='JPEG',
                              export_jpeg_quality=85, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=7, export_cameras=False, export_lights=False)
    with open(os.path.join(ROOT, 'public', 'models', 'hopkins.json'), 'w') as f:
        json.dump(dict(colliders=COLLIDERS, lamps=[[round(v, 3) for v in p] for p in LAMPS], rooms=ROOMS,
                       interact=INTERACT, spawn=dict(pos=[-4.0, STREET_Y, round(47.4 + SZ, 2)], yaw=math.pi),
                       ground=dict(street=STREET_Y, wall=WALL_Z1, ramps=RAMPS, stairs=STAIRS, levels=LEVELS),
                       hall=[-7, 7, -6, 10],
                       tower=dict(top=hopkins_house.TOWER_TOP, foot=[9.2, 0, -8.6])), f, separators=(',', ':'))
    if RENDER: preview(RENDER)


def preview(path):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.world = bpy.data.worlds.new('W'); sc.world.color = (0.03, 0.035, 0.05)
    sun = bpy.data.objects.new('Moon', bpy.data.lights.new('Moon', 'SUN'))
    sun.data.energy = 0.8; sun.rotation_euler = (0.9, 0.2, -0.6)
    sc.collection.objects.link(sun)
    for k, (x, y, z) in enumerate(LAMPS):
        l = bpy.data.objects.new(f'L{k}', bpy.data.lights.new(f'L{k}', 'POINT'))
        l.data.energy = 600 if y > 6 else 350; l.data.color = (1, 0.72, 0.42)
        l.location = (x, -z, y)
        sc.collection.objects.link(l)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 22
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    shots = [('drive', (-14, 1.7, 28), (0, 7, 8)), ('hall', (0, 1.7, 9.2), (0, 5.0, -4)), ('library', (-8, 1.7, 13), (-14, 2, 4)),
             ('music', (8, 1.7, 2.6), (14, 3, 10)), ('studio', (8, 1.7, -5.5), (12, 1.5, 0)), ('solarium', (0, 1.7, -7), (0, 2.5, -14))]
    for tag, eye, look in shots:
        e = Vector((eye[0], -eye[2], eye[1])); t = Vector((look[0], -look[2], look[1]))
        cam.location = e
        cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f'{path}_{tag}.png'
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':  # (other set builders import this file for its furniture)
    main()
