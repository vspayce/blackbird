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
HALL_H = 14.0       # the hall rises through the house
T = 0.35            # wall thickness


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


def painting_tex(name, seed, size=256):
    """A tonalist Californian landscape: sky, distant range, a dark foreground, a lake or a sunset."""
    rng = np.random.default_rng(seed)
    Hh, W = int(size * 0.75), size
    yy, xx = np.mgrid[0:Hh, 0:W] / np.array([Hh, W])[:, None, None]
    sky_top = rng.choice([hexrgb('#3a4a5a'), hexrgb('#5a4a3a'), hexrgb('#7a5a3a'), hexrgb('#4a5a5a')])
    sky_low = rng.choice([hexrgb('#d8b878'), hexrgb('#c89058'), hexrgb('#b8c0b0'), hexrgb('#e0c090')])
    t = np.clip(yy / 0.6, 0, 1)
    col = sky_top * (1 - t[..., None]) + sky_low * t[..., None]
    nz = noise(Hh, W, 40, seed)
    for k, (h0, c) in enumerate(((0.5, '#6a6a70'), (0.62, '#3a4030'), (0.78, '#1a1a12'))):
        ridge = h0 + 0.06 * np.sin(xx * (2 + k) * rng.uniform(0.6, 1.4) + rng.uniform(0, 6)) + 0.12 * (noise(Hh, W, 60 - k * 15, seed + k)[0:1, :] - 0.5)
        col = np.where((yy > ridge)[..., None], hexrgb(c) * (0.85 + 0.3 * nz[..., None]), col)
    if rng.random() < 0.5:  # a lake catching the sky
        lake = (yy > 0.7) & (yy < 0.82) & (np.abs(xx - 0.5) < 0.3)
        col[lake] = sky_low * 0.8
    vign = 1 - 0.5 * ((xx - 0.5) ** 2 + (yy - 0.5) ** 2)
    col *= vign[..., None] * (0.92 + 0.12 * noise(Hh, W, 3, seed + 1))[..., None]
    return image(name, col * 0.9)


def stained_tex(name, size=256):
    rng = np.random.default_rng(23)
    Hh = W = size
    cells = (noise(Hh, W, 18, 3) * 6).astype(int)
    pal = np.array([hexrgb(c) for c in ('#7a1a14', '#1a3a7a', '#c8a030', '#2a6a3a', '#5a2a6a', '#d8c890')])
    col = pal[(cells + (np.mgrid[0:Hh, 0:W][0] // 32)) % len(pal)]
    lead = np.abs(np.gradient(cells.astype(float))[0]) + np.abs(np.gradient(cells.astype(float))[1]) > 0
    col[lead] = 0.05
    return image(name, col)


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
    for i in range(8):
        material(f'painting{i}', tex=painting_tex(f'painting{i}', 40 + i), rough=0.5, scale=1.0)
    material('stained', '#000000', emit_tex=stained_tex('stained'), emit_strength=1.4, rough=0.3, scale=2.0)
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
        u = t + w / 2
    return F, L


def collide_seg(F, u0, u1, v0, v1, thick):
    p0 = F @ Vector((u0, v0, -thick / 2)); p1 = F @ Vector((u1, v1, thick / 2))
    collide(p0.x, p0.y, p0.z, p1.x, p1.y, p1.z)


def lining(F, L, side, openings, y_top, wains='oak_panel', upper='fresco_gothic', frieze='gilt_frame', w_h=1.3, thick=T):
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
            lbox(Fs, 'trim_dark', u, u1, w_h, w_h + 0.08, 0, 0.06)
            lbox(Fs, upper, u, u1, w_h + 0.08, y_top - 0.5, 0, 0.012)
            lbox(Fs, frieze, u, u1, y_top - 0.5, y_top - 0.42, 0, 0.05)
            lbox(Fs, 'trim_dark', u, u1, y_top - 0.42, y_top, 0, 0.14)
            lbox(Fs, 'trim_dark', u, u1, 0, 0.18, 0, 0.05)  # skirting
        if t > L: break
        # door or window surround
        lbox(Fs, 'trim_dark', t - w / 2 - 0.12, t - w / 2, max(0, ob - 0.05), ot + 0.12, 0, 0.06)
        lbox(Fs, 'trim_dark', t + w / 2, t + w / 2 + 0.12, max(0, ob - 0.05), ot + 0.12, 0, 0.06)
        lbox(Fs, 'trim_dark', t - w / 2 - 0.12, t + w / 2 + 0.12, ot, ot + 0.12, 0, 0.06)
        # a pointed Gothic head over the opening
        for s in (-1, 1):
            lbox(Fs, 'trim_dark', t + s * w / 4 - w / 4 - 0.02, t + s * w / 4 + w / 4 + 0.02, ot + 0.12 + w * 0.12, ot + 0.24 + w * 0.12,
                 0, 0.05, rot=0)
        if ot + 0.12 < y_top - 0.5:
            lbox(Fs, upper, t - w / 2 - 0.12, t + w / 2 + 0.12, ot + 0.12, y_top - 0.5, 0, 0.012)
        if ob > 0.3:  # under a window: panelling
            lbox(Fs, wains, t - w / 2, t + w / 2, 0, ob, 0, 0.03)
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


def frame_painting(F, u, v, w, h, idx, depth=0.0):
    """A painting in a deep gilt frame on a wall face (w = 0 at the face)."""
    lbox(F, f'painting{idx % 8}', u - w / 2, u + w / 2, v, v + h, depth, depth + 0.03)
    fw = 0.09
    for a, b, c, d in ((u - w / 2 - fw, u - w / 2, v - fw, v + h + fw), (u + w / 2, u + w / 2 + fw, v - fw, v + h + fw),
                       (u - w / 2, u + w / 2, v - fw, v), (u - w / 2, u + w / 2, v + h, v + h + fw)):
        lbox(F, 'gilt_frame', a, b, c, d, depth, depth + 0.07)


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


def easel(x, z, rot, idx):
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    for s in (-0.3, 0.3):
        tube('oak_panel', [F @ Vector((s, 0, 0.2)), F @ Vector((s * 0.3, 1.9, 0))], 0.02)
    tube('oak_panel', [F @ Vector((0, 0, -0.5)), F @ Vector((0, 1.7, 0.02))], 0.02)
    lbox(F, 'oak_panel', -0.4, 0.4, 0.85, 0.9, -0.05, 0.08)
    lbox(F, f'painting{idx % 8}' if idx % 3 else 'canvas', -0.35, 0.35, 0.9, 1.55, 0.02, 0.05)
    collide(x - 0.45, 0, z - 0.45, x + 0.45, 1.8, z + 0.45)


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


def lancet(F, u, v, w, h, lit=False):
    """A pointed-arch window on an exterior face: glass, stone surround, a drip mould and a pointed head."""
    g = 'glass_lit1' if lit else 'glass_dark'
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
    D = 1.8  # door width
    DH = 3.4

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
    def inner(a, b, doors, mat='plaster', top=H):
        ops = [(t, D, 0, DH) for t in doors]
        F, L = wall(a, b, 0, top, ops, mat=mat)
        return F, L, ops
    walls['vest_w'] = inner((-3, 10), (-3, 14), [])
    walls['vest_e'] = inner((3, 14), (3, 10), [])
    walls['vest_hall'] = inner((-3, 10), (3, 10), [3])
    walls['hall_front_w'] = inner((-7, 10), (-3, 10), [], top=HALL_H)
    walls['hall_front_e'] = inner((3, 10), (7, 10), [], top=HALL_H)
    walls['hall_w'] = inner((-7, -6), (-7, 10), [12, 4], top=HALL_H)     # to library, Moorish room
    walls['hall_e'] = inner((7, 10), (7, -6), [4, 12], top=HALL_H)       # to music room, life class
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
        thick = T + 0.1 if key in ('front_w', 'front_e', 'vest', 'west', 'east', 'back_w', 'back_e') else T
        lining(Fsub, t1 - t0, side, sub_ops, top, wains=r['wains'], upper=r['upper'], thick=thick)

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
    # gallery: a balcony round three sides on marble columns
    for (a0, a1, b0, b1) in ((x0, x1, z1 - 2, z1), (x0, x0 + 2, z0, z1), (x1 - 2, x1, z0, z1)):
        wbox('oak_panel', a0, a1, gy - 0.4, gy, b0, b1)
        wbox('parquet', a0, a1, gy, gy + 0.02, b0, b1)
    for x in (-5, -1.7, 1.7, 5):
        column(x, z1 - 2, 0, gy - 0.4)
    for z in (5.5, 1.5, -2.5):
        column(x0 + 2, z, 0, gy - 0.4); column(x1 - 2, z, 0, gy - 0.4)
    # balustrade along the gallery edge
    edge = [((x0 + 2, z1 - 2), (x1 - 2, z1 - 2)), ((x0 + 2, z0), (x0 + 2, z1 - 2)), ((x1 - 2, z1 - 2), (x1 - 2, z0))]
    for a, b in edge:
        A, B = Vector((a[0], gy, a[1])), Vector((b[0], gy, b[1]))
        tube('oak_panel', [A + Vector((0, 1.0, 0)), B + Vector((0, 1.0, 0))], 0.05, 6)
        n = int((B - A).length / 0.25)
        for k in range(n + 1):
            p = A.lerp(B, k / n)
            cyl('oak_panel', p, 1.0, 0.03, seg=6, cap=False)
    # the grand stair: rising from the back of the hall in one flight, then splitting to the gallery
    steps = 18
    for k in range(steps):
        y = (k + 1) * (gy / 2) / steps
        z = -1.0 - k * 0.3
        wbox('marble_white', -2.2, 2.2, 0, y, z - 0.3, z)
    wbox('marble_white', -3.2, 3.2, 0, gy / 2, -6.0, -6.4 + 1.0)  # landing against the back wall
    for s in (-1, 1):
        for k in range(steps):
            y = gy / 2 + (k + 1) * (gy / 2) / steps
            x = s * (3.2 + k * 0.2)
            wbox('marble_white', min(x, x + s * 0.2), max(x, x + s * 0.2), y - 0.25, y, -6.0, -4.6)
    for s in (-1, 1):  # newel posts and the handrail of the main flight
        cyl('walnut_panel', (s * 2.3, 0, -0.8), 1.3, 0.1, 0.08, seg=8)
        sphere('brass', (s * 2.3, 1.38, -0.8), 0.09, 8)
        tube('walnut_panel', [(s * 2.3, 1.2, -0.8), (s * 2.3, gy / 2 + 1.0, -6.1)], 0.045)
    collide(-2.4, 0, -6.4, 2.4, gy, -0.9)
    # pictures: three tiers of them in gilt frames on the hall walls (the Association's collection)
    hang = [(frame((x0 + 0.18, 0, z1), (0, 0, -1), (1, 0, 0)), 16), (frame((x1 - 0.18, 0, z0), (0, 0, 1), (-1, 0, 0)), 16)]
    idx = 0
    for F, L in hang:
        for u in (2.0, 6.0, 10.0, 14.0):
            if abs(u - 4) < 1.4 or abs(u - 12) < 1.4: continue  # leave the doors clear
            frame_painting(F, u, 1.9, 1.6, 1.2, idx); idx += 1
        for u in (2.5, 5.5, 8.5, 11.5, 14.0):
            frame_painting(F, u, 7.4, 1.8, 1.3, idx); idx += 1
            frame_painting(F, u, 9.2, 1.1, 0.8, idx + 3); idx += 1
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
        lbox(Fi, 'fresco_red', 0, L, gy + 0.1, HALL_H - 1.0, 0, 0.01)
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
                      (frame((-14.8, 0, 13.65), (1, 0, 0), (0, 0, -1)), 0.5, 1.9), (frame((-14.8, 0, 13.65), (1, 0, 0), (0, 0, -1)), 4.1, 7.6),
                      (frame((-7.2, 0, 2.2), (0, 0, 1), (-1, 0, 0)), 0.3, 1.0), (frame((-7.2, 0, 2.2), (0, 0, 1), (-1, 0, 0)), 3.6, 7.5)):
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
    Fr = frame((-14.8, 0, -6.2), (0, 0, -1), (1, 0, 0))
    frame_painting(Fr, 4, 1.8, 2.2, 1.6, 6)
    INTERACT.append(dict(id='curator', label='The curator\'s desk', pos=[-11, 0.8, -10], r=2.0))

    # --- the music room: the organ, a grand piano, rows of chairs for the Association's concerts ---
    Fo = frame((14.8, 0, 3), (0, 0, 1), (-1, 0, 0))
    organ(Fo, 1.0, 10.0, H)
    collide(13.3, 0, 3, 15, 2.2, 13)
    wbox('ebony_panel', 9.0, 11.0, 0.7, 1.0, 9.5, 11.0)  # grand piano (a blunt one)
    wbox('ebony_panel', 9.0, 9.4, 0.7, 1.6, 9.5, 11.0)
    for a in ((9.2, 9.7), (10.8, 9.7), (9.2, 10.8)):
        wbox('ebony_panel', a[0] - 0.05, a[0] + 0.05, 0, 0.7, a[1] - 0.05, a[1] + 0.05)
    collide(9.0, 0, 9.5, 11.0, 1.0, 11.0)
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
        r = (B - A).normalized(); n = Vector((r.z, 0, -r.x))
        F = frame(A, r, n)
        L = (B - A).length
        lbox(F, 'ashlar', 0, L, up0, up1, -T / 2 - 0.05, T / 2 + 0.05)
        Fo = F @ Matrix.Translation((0, 0, T / 2 + 0.05))
        lbox(Fo, 'trim_cream', 0, L, up0 - 0.1, up0 + 0.15, 0, 0.2)  # string course
        k = 2.0
        while k < L - 1.5:
            lancet(Fo, k, up0 + 1.0, 0.9, 2.4, lit=rnd.random() < 0.25)
            k += 3.0
        merlons(Fo, 0, L, up1, 0.0)
    wbox('ashlar', -7, 7, H, up1, -6.25, -6.18)  # the hall's back wall above the solarium roof, outside face
    # the hall's clerestory and roof rising above the house
    for (a, b) in (((-7, 10), (7, 10)), ((7, 10), (7, -6)), ((7, -6), (-7, -6)), ((-7, -6), (-7, 10))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        r = (B - A).normalized(); n = Vector((r.z, 0, -r.x))
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
        r = (B - A).normalized(); n = Vector((r.z, 0, -r.x))
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

    # grounds: lawn, the curving gravel drive, the granite retaining wall and gate on California Street
    wbox('grass', -40, 40, -0.2, -0.05, -17.5, 30)  # behind the house the hill drops away below a terrace
    curve = [(-12 + 24 * t, 0, 28 - 22 * (1 - (2 * t - 1) ** 2) * 0.6) for t in np.linspace(0, 1, 25)]
    bm = bm_for('gravel')
    for a, b in zip(curve, curve[1:]):
        A, B = Vector(a), Vector(b)
        d = (B - A).normalized(); side = Vector((-d.z, 0, d.x)) * 2.4
        q = [A - side + Vector((0, -0.04, 0)), B - side + Vector((0, -0.04, 0)), B + side + Vector((0, -0.04, 0)),
             A + side + Vector((0, -0.04, 0))]
        bm.faces.new([bm.verts.new(p) for p in q])
    wbox('gravel', -4, 4, -0.045, -0.04, 14, 22)
    # granite wall along the street, with a gate either side for the drive
    for (a0, a1) in ((-40, -14.5), (-9.5, 9.5), (14.5, 40)):
        wbox('granite', a0, a1, -0.2, 1.1, 29.5, 30.3)
        collide(a0, 0, 29.5, a1, 1.1, 30.3)
        wbox('granite', a0, a1, 1.1, 1.25, 29.4, 30.4)
    for x in (-14.5, -9.5, 9.5, 14.5):
        wbox('granite', x - 0.45, x + 0.45, -0.2, 2.4, 29.45, 30.35)
        sphere('lamp_glass', (x, 2.75, 29.9), 0.2, 10)
        LAMPS.append([x, 2.75, 29.9])
        collide(x - 0.45, 0, 29.45, x + 0.45, 2.4, 30.35)
    # side and back boundaries (the hill falls away; a low wall and the drop)
    collide(-40, 0, -17.5, -39, 2, 30); collide(39, 0, -17.5, 40, 2, 30); collide(-40, 0, -17.8, 40, 2, -17.2)
    for (a, b) in (((-40, -17.5), (-40, 29.5)), ((40, -17.5), (40, 29.5))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        r = (B - A).normalized(); n = Vector((r.z, 0, -r.x))
        lbox(frame(A, r, n), 'granite', 0, (B - A).length, -0.2, 0.9, -0.3, 0.3)
    # the terrace edge behind the house: a stone balustrade, then the drop and the city
    wbox('granite', -40, 40, -6.0, 0.2, -17.8, -17.2)
    wbox('granite', -40, 40, 0.85, 1.0, -17.65, -17.35)
    for x in np.arange(-39.5, 40, 0.5):
        cyl('granite', (x, 0.2, -17.5), 0.65, 0.07, 0.05, seg=6)
    # a few clipped shrubs and two cast-iron urns flanking the porch
    for (x, z) in ((-20, 18), (20, 18), (-22, 4), (22, 4), (-24, -20), (24, -20)):
        sphere('palm', (x, 0.8, z), 1.1, 10)
    for x in (-4.5, 4.5):
        cyl('iron', (x, 0, 21), 0.8, 0.25, 0.35, seg=10)
        sphere('palm', (x, 1.0, 21), 0.45, 8)


DH_FRONT = 3.4


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hopkins_materials()
    R, walls = build_house()
    build_hall(R)
    furnish(R)
    build_solarium_glass()
    build_exterior()
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
                       interact=INTERACT, spawn=dict(pos=[-11.0, 0, 26.8], yaw=math.atan2(11.0, -9.8)),
                       tower=dict(top=[11.5, 22.0, -9.5], foot=[9.2, 0, -8.6])), f, separators=(',', ':'))
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


main()
