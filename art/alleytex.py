# Textures for the Burritt Alley set (art/build_set.py): tileable PBR sets painted with numpy — colour,
# normal and roughness for brick, clapboard, basalt setts, cobbles, plank sidewalk, granite and wood —
# plus lamplit windows and one atlas of posters, handbills and painted signs whose lettering is set with
# Blender's own text curves and rasterised here (no PIL, so it builds inside a stock Blender).
#
# Every tile wraps: the noise is periodic and the normals are taken with wrapped differences.
# Roughness comes twice: <name>_r (linear grey, wired to Principled Roughness, which glTF carries) and
# <name>_ms (metallic in RGB = 0, smoothness = 1 - roughness in alpha), an unconnected node in the same
# material so that Tools/blender/export_unity.py writes it next to the FBX ready for URP's Lit shader.
import math
import bpy
import numpy as np
from setkit import image, hexrgb, FONT, MATS, material

TEX = {}    # name -> bpy image


def srgb(h):
    return hexrgb(h)


# --- periodic noise -----------------------------------------------------------------------

def tnoise(n, cells, seed, m=None):
    """Periodic value noise in 0..1 on an m x n image; cells = lattice cells across (int or (cy, cx))."""
    m = n if m is None else m
    cy, cx = (cells, cells) if isinstance(cells, int) else cells
    g = np.random.default_rng(seed).random((cy, cx)).astype(np.float32)
    ty, tx = np.arange(m) * cy / m, np.arange(n) * cx / n
    y0, x0 = ty.astype(int), tx.astype(int)
    fy, fx = (ty - y0)[:, None], (tx - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    y1, x1 = (y0 + 1) % cy, (x0 + 1) % cx
    a, b, c, d = g[y0][:, x0], g[y0][:, x1], g[y1][:, x0], g[y1][:, x1]
    return ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy).astype(np.float32)


def fbm(n, cells, seed, octaves=4, gain=0.5, m=None):
    cy, cx = (cells, cells) if isinstance(cells, int) else cells
    out, amp, tot = 0, 1.0, 0.0
    for o in range(octaves):
        out = out + amp * tnoise(n, (cy * 2 ** o, cx * 2 ** o), seed + o * 17, m)
        tot += amp; amp *= gain
    return out / tot


def white(n, seed, m=None):
    return np.random.default_rng(seed).random((n if m is None else m, n)).astype(np.float32)


def blur(a, k=1):
    """A cheap wrapped box blur, k passes."""
    for _ in range(k):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    return a


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def normal_from(height, strength):
    """Tangent-space normal map (OpenGL, +Y up) from a height field, wrapped at the edges."""
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5
    nrm = np.dstack([-gx * strength, gy * strength, np.ones_like(height)])
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    return nrm * 0.5 + 0.5


def half(a):
    """Downsample by two (box filter)."""
    h, w = a.shape[:2]
    return a.reshape(h // 2, 2, w // 2, 2, *a.shape[2:]).mean(axis=(1, 3))


def save(name, arr, data=False, alpha=None):
    if arr.ndim == 2: arr = np.repeat(arr[..., None], 3, 2)
    img = image(name, arr, alpha)
    if data: img.colorspace_settings.name = 'Non-Color'
    TEX[name] = img
    return img


def save_pbr(name, col, height=None, nstrength=3.0, rough=None, nrm_name=None, rough_name=None):
    """Colour (sRGB), and optionally a normal from the height field and a roughness map (+ Unity mask)."""
    save(name, col)
    if height is not None:
        save(nrm_name or name + '_n', normal_from(height, nstrength), data=True)
    if rough is not None:
        rn = rough_name or name + '_r'
        r = np.clip(rough, 0.03, 1)
        save(rn, r, data=True)
        save(rn[:-2] + '_ms', np.zeros(r.shape + (3,), np.float32), data=True, alpha=1 - r)


# --- brick --------------------------------------------------------------------------------

def brick_set(palettes, n=1024, rows=26, per=9):
    """Common-bond brick, a 2 m tile: stretcher courses with a header course every 13th. One layout, so the
    colours share a normal and a roughness map (brick_n, brick_r). palettes: {name: (brick, mortar, soot)}."""
    rng = np.random.default_rng(1895)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    rh = n / rows
    row = (yy / rh).astype(int)
    header = (row % 13) == 6
    bw = np.where(header, n / (per * 2), n / per).astype(np.float32)
    off = (rng.random(rows) * 0.2 - 0.1 + (np.arange(rows) % 2) * 0.5).astype(np.float32)[row] * (n / per)
    bx = ((xx + off) / bw).astype(int) % np.where(header, per * 2, per)
    fx = (xx + off) % bw
    fy = yy % rh
    wob = (fbm(n, 48, 3, 2) - 0.5) * 3.0
    joint = 2.6  # half a mortar joint, px (about 10 mm in all)
    d = np.minimum(np.minimum(fx, bw - fx), np.minimum(fy, rh - fy)) - joint + wob
    brick = sstep(0.0, 1.6, d)
    ids = row * 37 + bx
    r1, r2, r3 = (rng.random(rows * 37 + per * 2 + 2).astype(np.float32)[ids] for _ in range(3))
    # per-brick tone: most near the base, a few overburnt and dark, a few pale and sandy
    tone = 0.80 + 0.34 * r1
    tone = np.where(r2 < 0.07, tone * 0.55, tone)
    tone = np.where(r2 > 0.95, tone * 1.18, tone)
    grain = 0.90 + 0.14 * fbm(n, 96, 5, 3) + 0.10 * (white(n, 6) - 0.5)
    pits = sstep(0.80, 0.9, blur(white(n, 8), 1) * 1.6)            # chips and pits
    macro = fbm(n, 3, 9, 4)
    streak = sstep(0.55, 0.85, tnoise(n, (2, 28), 11)) * sstep(0.3, 0.7, fbm(n, 2, 12, 2))
    lime = sstep(0.62, 0.8, fbm(n, 5, 14, 3)) * 0.5                # efflorescence, pale blooms
    height = brick * (0.55 + 0.45 * sstep(0, 5, d)) * (0.86 + 0.28 * r3) + 0.10 * fbm(n, 128, 15, 2) \
        - 0.25 * pits * brick + (1 - brick) * 0.12 * white(n, 16)
    damp = sstep(0.5, 0.8, fbm(n, 4, 21, 3))
    rough = lerp(0.96, 0.86 + 0.08 * r3, brick) - 0.22 * damp * brick
    for name, (base, mortar, soot) in palettes.items():
        b = srgb(base)[None, None, :] * tone[..., None]
        b = b * np.stack([np.ones_like(r3), 0.96 + 0.08 * r3, 0.92 + 0.14 * r3], -1)
        b *= grain[..., None]
        b *= (1 - 0.35 * pits)[..., None]
        mo = srgb(mortar)[None, None, :] * (0.78 + 0.3 * fbm(n, 64, 18, 2))[..., None]
        col = lerp(mo, b, brick[..., None])
        col = lerp(col, col * 0.6 + srgb('#b9b3a4') * 0.4, (lime * brick * (0.5 if soot > 0.3 else 0.25))[..., None])
        dark = 1 - soot * (0.75 * sstep(0.25, 0.85, macro) + 0.45 * streak)
        col *= np.clip(dark, 0.25, 1)[..., None]
        col *= (1 - 0.10 * damp)[..., None]
        save(name, col)
    save('brick_n', normal_from(height, 5.5), data=True)
    save_rough('brick', rough)
    TEX['_brick_mask'] = brick


def save_rough(name, r):
    r = np.clip(r, 0.03, 1).astype(np.float32)
    save(name + '_r', r, data=True)
    save(name + '_ms', np.zeros(r.shape + (3,), np.float32), data=True, alpha=1 - r)


# --- clapboard ----------------------------------------------------------------------------

def clap_set(palettes, n=1024, boards=13):
    """Painted redwood lap siding, a 2 m tile: 150 mm boards, butt joints, nail heads, paint weathered and
    peeling along the drip edges. Shared clap_n / clap_r."""
    rng = np.random.default_rng(77)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    bh = n / boards
    row = (yy / bh).astype(int)
    f = (yy % bh) / bh                      # 0 at the top of a board (under the lap above), 1 at its drip edge
    jx = (rng.random(boards) * n).astype(np.float32)[row]
    dj = np.abs(((xx - jx + n / 2) % n) - n / 2)
    jointm = sstep(1.8, 0.6, dj)
    nail = np.zeros((n, n), np.float32)
    for dxn in (-14, 14):
        dn = np.hypot(((xx - jx - dxn + n / 2) % n) - n / 2, (f - 0.72) * bh)
        nail = np.maximum(nail, sstep(3.2, 1.6, dn))
    for kx in range(0, n, n // 5):          # studs every 400 mm: a nail in each board
        dn = np.hypot(((xx - kx - 9 + n / 2) % n) - n / 2, (f - 0.72) * bh)
        nail = np.maximum(nail, sstep(2.8, 1.4, dn))
    shadow = sstep(0.0, 0.16, f)            # the shadow under each lap
    grainw = 0.5 * tnoise(n, (boards * 6, 5), 31) + 0.5 * tnoise(n, (boards * 14, 9), 32)
    weather = fbm(n, 4, 33, 4)
    peel_n = fbm(n, (40, 24), 34, 3)
    peel = sstep(0.70, 0.79, peel_n * (0.5 + 0.62 * f) + 0.2 * sstep(0.55, 0.95, weather))
    drip = sstep(0.6, 0.9, tnoise(n, (3, 40), 35)) * sstep(0.3, 0.8, fbm(n, 3, 36, 2))
    height = f * 1.0 + 0.05 * grainw - 0.12 * peel - 0.5 * jointm + 0.2 * nail
    height = np.where(f > 0.97, height * (1 - (f - 0.97) / 0.03), height)   # the drop off the drip edge
    rough = lerp(0.62, 0.92, peel) + 0.1 * (grainw - 0.5)
    wood = srgb('#6f665a')[None, None, :] * (0.75 + 0.4 * grainw)[..., None]
    for name, paint in palettes.items():
        p = srgb(paint)[None, None, :] * (0.84 + 0.22 * weather + 0.06 * (grainw - 0.5))[..., None]
        col = lerp(p, wood, peel[..., None])
        col *= (0.50 + 0.50 * shadow)[..., None]
        col *= (1 - 0.30 * drip)[..., None]
        col *= (1 - 0.45 * jointm)[..., None]
        col = lerp(col, srgb('#3a2a20')[None, None, :], (nail * 0.8)[..., None])
        col *= (0.9 + 0.1 * sstep(0.2, 0.8, fbm(n, 2, 37, 2)))[..., None]
        save(name, col)
    save('clap_n', normal_from(height, 7.0), data=True)
    save_rough('clap', rough)


# --- basalt setts (Bush Street) --------------------------------------------------------------

def setts(name='stone_setts', n=1024, cols=32, per=16):
    """Basalt block paving, a 4 m tile: courses run across the street (along v), joints broken course to
    course, each block domed and worn, the joints dark with standing water."""
    rng = np.random.default_rng(5)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cw, L = n / cols, n / per
    col = (xx / cw).astype(int)
    off = (rng.random(cols) * L).astype(np.float32)[col]
    y2 = (yy + off) % n
    k = (y2 / L).astype(int)
    loc = y2 - k * L
    gap = (1.2 + 2.2 * rng.random((cols, per))).astype(np.float32)
    gx = (1.0 + 1.6 * rng.random(cols)).astype(np.float32)[col]
    fx = xx % cw
    dx = np.minimum(fx, cw - fx) - gx
    dy = np.minimum(loc - gap[col, k], L - loc - gap[col, (k + 1) % per])
    r = 5.0
    wob = (fbm(n, 64, 7, 2) - 0.5) * 2.5
    d = np.where((dx < r) & (dy < r), r - np.hypot(np.maximum(r - dx, 0), np.maximum(r - dy, 0)), np.minimum(dx, dy)) + wob
    stone = sstep(0.0, 2.0, d)
    ids = col * per + k
    r1, r2, r3, r4 = (rng.random(cols * per).astype(np.float32)[ids] for _ in range(4))
    dome = 1 - (1 - np.clip(d / 9.0, 0, 1)) ** 2
    tilt = ((fx / cw - 0.5) * (r3 - 0.5) + (loc / L - 0.5) * (r4 - 0.5)) * 0.5
    grain = fbm(n, 160, 8, 2)
    height = stone * (0.45 + 0.4 * dome + 0.22 * r1 + tilt) + 0.07 * grain + (1 - stone) * 0.06 * white(n, 9)
    tone = 0.72 + 0.5 * r1
    base = srgb('#44464a')[None, None, :] * tone[..., None]
    base = base * np.stack([1 + 0.10 * (r2 - 0.4), np.ones_like(r2), 1 - 0.10 * (r2 - 0.4)], -1)   # bluish to brownish
    base *= (0.82 + 0.3 * grain + 0.12 * dome)[..., None]
    muck = sstep(0.52, 0.8, fbm(n, 5, 10, 4))                      # mud and horse droppings trodden in
    base = lerp(base, srgb('#3a3022')[None, None, :] * (0.7 + 0.5 * grain)[..., None], (muck * 0.65)[..., None])
    jointc = srgb('#16130f')[None, None, :] * (0.7 + 0.6 * white(n, 11))[..., None]
    colr = lerp(jointc, base, stone[..., None])
    wet = fbm(n, 3, 12, 3)
    colr *= (0.80 + 0.2 * (1 - sstep(0.35, 0.75, wet)))[..., None]
    rough = lerp(0.10, 0.50 - 0.28 * sstep(0.35, 0.75, wet) + 0.12 * (grain - 0.5) + 0.2 * muck, stone)
    save(name, colr)
    save(name + '_n', normal_from(height, 9.0), data=True)
    save_rough(name, rough)
    # the same paving under an inch of water: darker and flat, for the puddle patches laid over it
    save(name + '_wet', colr * 0.6 + srgb('#0b0e12')[None, None, :] * 0.2)


# --- cobbles (the alley) ---------------------------------------------------------------------

def cobbles(name='stone_cobble', n=1024, cells=24):
    """Rounded cobblestones bedded in mud, a 2.5 m tile."""
    rng = np.random.default_rng(23)
    jit = (0.15 + 0.7 * rng.random((cells, cells, 2))).astype(np.float32)
    t = (np.arange(n, dtype=np.float32) + 0.5) * cells / n
    py, px = np.meshgrid(t, t, indexing='ij')
    cy, cx = py.astype(int), px.astype(int)
    f1 = np.full((n, n), 9.0, np.float32); f2 = f1.copy(); idx = np.zeros((n, n), np.int32)
    sq = (0.75 + 0.5 * rng.random((cells, cells))).astype(np.float32)   # some cobbles longer than wide
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            j, i = (cy + dj) % cells, (cx + di) % cells
            qy, qx = cy + dj + jit[j, i, 0], cx + di + jit[j, i, 1]
            dd = np.hypot((py - qy) * sq[j, i], (px - qx) / sq[j, i])
            nearer = dd < f1
            f2 = np.where(nearer, f1, np.minimum(f2, dd))
            idx = np.where(nearer, j * cells + i, idx)
            f1 = np.where(nearer, dd, f1)
    edge = f2 - f1
    r1, r2, r3 = (rng.random(cells * cells).astype(np.float32)[idx] for _ in range(3))
    mudlevel = 0.07 + 0.2 * fbm(n, 4, 24, 3) ** 1.5                    # how deep the cobbles sit in the mud
    rad = 0.5 + 0.14 * r3                                        # each cobble a rounded stone within its cell
    inset = np.minimum(rad - f1, edge * 1.6 - mudlevel * 0.5)
    stone = sstep(0.0, 0.07, inset)
    dome = np.sqrt(np.clip(1 - (f1 / rad) ** 2, 0, 1)) * np.clip(inset / 0.12, 0, 1) ** 0.5
    grain = fbm(n, 150, 25, 2)
    height = stone * (0.35 + 0.65 * dome) * (0.8 + 0.4 * r1) + 0.06 * grain + (1 - stone) * (0.05 * fbm(n, 60, 26, 2))
    pal = np.stack([srgb('#3f3f40'), srgb('#47423b'), srgb('#35373b'), srgb('#4c463c')])
    base = pal[(r2 * 3.999).astype(int)] * (0.8 + 0.3 * r1)[..., None]
    base *= (0.62 + 0.3 * grain + 0.38 * dome)[..., None]
    mud = srgb('#1c1711')[None, None, :] * (0.7 + 0.7 * fbm(n, 40, 27, 3))[..., None]
    straw = sstep(0.83, 0.9, tnoise(n, (220, 30), 28) * (0.6 + 0.6 * fbm(n, 6, 29, 2)))
    mud = lerp(mud, srgb('#6b5a34')[None, None, :], (straw * 0.6)[..., None])
    colr = lerp(mud, base, stone[..., None])
    slime = sstep(0.5, 0.8, fbm(n, 5, 30, 3))
    colr = lerp(colr, colr * srgb('#6d7a5a')[None, None, :] * 1.6, (slime * 0.25 * stone)[..., None])
    wet = fbm(n, 3, 31, 3)
    colr *= (0.78 + 0.22 * (1 - sstep(0.35, 0.7, wet)))[..., None]
    rough = lerp(0.14 + 0.2 * fbm(n, 30, 32, 2), 0.66 - 0.3 * sstep(0.35, 0.7, wet) + 0.14 * (grain - 0.5), stone)
    save(name, colr)
    save(name + '_n', normal_from(height, 9.0), data=True)
    save_rough(name, rough)
    save(name + '_wet', colr * 0.6 + srgb('#0b0d10')[None, None, :] * 0.2)


# --- plank sidewalk ------------------------------------------------------------------------------

def planks(name='wood_walk', n=1024, boards=10, base='#5c5247', seed=41, joints=1, nails=3, wet=True, gapw=2.2):
    """Boards running along v (across the sidewalk), a 2 m tile: grey weathered redwood, butt joints,
    nail heads along the stringers, wet in the gaps."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    bw = n / boards
    b = (xx / bw).astype(int)
    fx = xx % bw
    edge = np.minimum(fx, bw - fx)
    gap = sstep(gapw, gapw * 0.4, edge)
    jy = (rng.random((boards, joints)) * n).astype(np.float32)
    jm = np.zeros((n, n), np.float32); seg = np.zeros((n, n), np.int32)
    for j in range(joints):
        dj = np.abs(((yy - jy[b, j] + n / 2) % n) - n / 2)
        jm = np.maximum(jm, sstep(gapw, gapw * 0.4, dj))
        seg += (yy > jy[b, j]).astype(np.int32)
    ids = b * (joints + 1) + seg % (joints + 1)
    r1, r2 = (rng.random(boards * (joints + 2)).astype(np.float32)[ids] for _ in range(2))
    sh = (r2 * n).astype(int)
    g1 = tnoise(n, (5, boards * 22), seed + 1); g2 = tnoise(n, (9, boards * 60), seed + 2)
    grain = 0.6 * g1 + 0.4 * g2
    grain = np.take_along_axis(grain, ((yy.astype(int) + sh) % n), 0)       # each board its own length of grain
    knots = sstep(0.86, 0.93, fbm(n, (14, 22), seed + 3, 2))
    nl = np.zeros((n, n), np.float32)
    for kv in range(nails):
        for sx in (0.22, 0.78):
            dn = np.hypot(fx - sx * bw, ((yy - (kv + 0.5) * n / nails + n / 2) % n) - n / 2)
            nl = np.maximum(nl, sstep(3.6, 1.8, dn))
    cup = 1 - ((fx / bw - 0.5) * 2) ** 2
    wear = fbm(n, 4, seed + 4, 3)
    height = (0.5 + 0.12 * cup + 0.10 * grain + 0.25 * (r1 - 0.5) - 0.25 * knots) * (1 - np.maximum(gap, jm)) - 0.08 * nl
    tone = 0.74 + 0.42 * r1
    colr = srgb(base)[None, None, :] * (tone * (0.72 + 0.5 * grain))[..., None]
    colr = lerp(colr, colr * srgb('#8a7f72')[None, None, :] * 2.0, (sstep(0.5, 0.85, wear) * 0.3)[..., None])   # worn pale
    colr *= (1 - 0.55 * knots)[..., None]
    colr = lerp(colr, srgb('#2a1a12')[None, None, :], (nl * 0.85)[..., None])
    colr *= (1 - 0.88 * np.maximum(gap, jm))[..., None]
    wetm = sstep(0.4, 0.75, fbm(n, 3, seed + 5, 3)) if wet else np.zeros((n, n), np.float32)
    colr *= (1 - 0.22 * wetm)[..., None]
    rough = np.clip(0.78 - 0.4 * wetm + 0.15 * (grain - 0.5), 0.2, 1) * (1 - 0.6 * np.maximum(gap, jm)) if wet \
        else 0.8 + 0.15 * (grain - 0.5)
    save(name, colr)
    save(name + '_n', normal_from(height, 6.0), data=True)
    if wet: save_rough(name, rough)


# --- granite and dressed stone -----------------------------------------------------------------------

def granite(name='stone', n=512, base='#605e59', seed=51, speck=0.22, tool=0.0, wet=0.35):
    w1 = blur(white(n, seed), 1); w2 = white(n, seed + 1)
    sp = (w1 - 0.5) * 2.2 * speck + (sstep(0.93, 0.97, w2) - sstep(0.93, 0.97, white(n, seed + 2)) * 1.2) * speck
    macro = fbm(n, 4, seed + 3, 4)
    stain = sstep(0.5, 0.85, fbm(n, 3, seed + 4, 3))
    colr = srgb(base)[None, None, :] * (0.86 + 0.2 * macro + sp)[..., None]
    colr = lerp(colr, colr * srgb('#6a5f4c')[None, None, :] * 1.7, (stain * 0.35)[..., None])
    yy = np.mgrid[0:n, 0:n][0].astype(np.float32)
    tl = np.sin(yy / n * math.pi * 2 * 64) * tool
    height = 0.5 * blur(white(n, seed + 5), 1) + 0.3 * fbm(n, 40, seed + 6, 2) + tl
    wetm = sstep(0.4, 0.75, fbm(n, 3, seed + 7, 3))
    save(name, colr * (1 - 0.15 * wetm * (wet > 0))[..., None])
    save(name + '_n', normal_from(height, 2.2), data=True)
    save_rough(name, 0.78 - wet * wetm + 0.1 * (w1 - 0.5))


# --- wood -------------------------------------------------------------------------------------------------

def wood(name, base, n=512, boards=6, seed=61, contrast=0.4, gapw=1.6, paint=None, soot=0.0):
    """Vertical boards, grain running up them. paint: a colour worn through to the wood on the edges."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    bw = n / boards
    b = (xx / bw).astype(int)
    fx = xx % bw
    edge = np.minimum(fx, bw - fx)
    gap = sstep(gapw, gapw * 0.3, edge)
    r1 = rng.random(boards).astype(np.float32)[b]
    sh = (rng.random(boards) * n).astype(int)[b]
    grain = 0.55 * tnoise(n, (4, boards * 18), seed + 1) + 0.45 * tnoise(n, (8, boards * 48), seed + 2)
    grain = np.take_along_axis(grain, ((yy.astype(int) + sh) % n), 0)
    knots = sstep(0.87, 0.94, fbm(n, (10, 16), seed + 3, 2))
    colr = srgb(base)[None, None, :] * ((0.8 + 0.3 * r1) * (1 - contrast / 2 + contrast * grain))[..., None]
    colr *= (1 - 0.5 * knots)[..., None]
    height = (0.5 + 0.12 * grain + 0.2 * (r1 - 0.5) - 0.2 * knots) * (1 - gap)
    rough = 0.8 + 0.15 * (grain - 0.5)
    if paint:
        worn = sstep(0.5, 0.7, fbm(n, (10, 30), seed + 4, 3) + 0.35 * sstep(bw * 0.25, 0, edge))
        p = srgb(paint)[None, None, :] * (0.85 + 0.2 * fbm(n, 5, seed + 5, 3))[..., None]
        colr = lerp(p, colr, worn[..., None])
        height = height + 0.06 * (1 - worn)
        rough = lerp(0.55, rough, worn)
    colr *= (1 - 0.85 * gap)[..., None]
    if soot: colr *= (1 - soot * sstep(0.3, 0.8, fbm(n, 3, seed + 6, 3)))[..., None]
    save(name, colr)
    save(name + '_n', normal_from(height, 4.0), data=True)
    return rough


def metal_sheet(name, base, n=256, seed=71, rust='#5a3620', amount=0.5):
    """Painted or galvanised sheet going to rust."""
    r = sstep(0.45, 0.75, fbm(n, 5, seed, 4)) * amount + sstep(0.8, 0.95, white(n, seed + 1)) * 0.2
    r = np.clip(r, 0, 1)
    colr = lerp(srgb(base)[None, None, :] * (0.85 + 0.25 * fbm(n, 8, seed + 2, 3))[..., None],
                srgb(rust)[None, None, :] * (0.6 + 0.8 * fbm(n, 30, seed + 3, 3))[..., None], r[..., None])
    save(name, colr)
    save(name + '_n', normal_from(fbm(n, 40, seed + 4, 3) + 0.5 * r, 2.0), data=True)


def stripes(name, a, b, n=256, bands=4, seed=81):
    """Awning canvas: broad stripes, faded and water-stained."""
    xx = np.mgrid[0:n, 0:n][1].astype(np.float32)
    s = sstep(-0.08, 0.08, np.sin(xx / n * math.pi * 2 * bands))
    colr = lerp(srgb(a)[None, None, :], srgb(b)[None, None, :], s[..., None])
    colr = colr * (0.75 + 0.3 * fbm(n, 4, seed, 4))[..., None]
    weave = 0.5 + 0.5 * np.sin(np.mgrid[0:n, 0:n][0] * 2.2) * np.sin(xx * 2.2)
    save(name, colr * (0.94 + 0.06 * weave)[..., None])


# --- windows with a lamp behind them ------------------------------------------------------------------------

def lit_windows(n=256):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n      # yy: 0 at the top
    warm = np.array([1.0, 0.62, 0.27], np.float32)

    def bars(v, cross=True):
        m = (np.abs(yy - 0.5) < 0.022)
        if cross: m = m | (np.abs(xx - 0.5) < 0.014)
        v = v.copy(); v[m] *= 0.12
        return v

    # 0: lace curtains parted, a lamp low in the room
    glow = 0.45 + 0.55 * np.exp(-((xx - 0.55) ** 2 * 5 + (yy - 0.7) ** 2 * 6))
    part = np.clip((np.abs(xx - 0.5) - 0.08) * 3.2, 0, 1) ** 0.6
    lace = 0.8 + 0.2 * np.sin(xx * 150 + np.sin(yy * 20) * 2) * np.sin(yy * 130)
    fold = 0.85 + 0.15 * np.sin(xx * 46)
    v = glow * lerp(1.0, 0.55 * lace * fold, part)
    save('glass_lit0', (bars(v)[..., None] * warm)[:, :, :3])
    # 1: a holland blind pulled most of the way down, lamplight through it, and a man's shadow on the blind
    blind = np.where(yy < 0.82, 0.62 + 0.25 * np.exp(-((xx - 0.4) ** 2 * 6 + (yy - 0.55) ** 2 * 5)), 0.9)
    blind = blind * (0.94 + 0.06 * np.sin(yy * 240))
    head = np.hypot((xx - 0.66) / 0.062, (yy - 0.44) / 0.085) < 1
    hat = (np.hypot((xx - 0.66) / 0.066, (yy - 0.385) / 0.07) < 1) & (yy < 0.39) | (np.abs(xx - 0.66) < 0.1) & (np.abs(yy - 0.39) < 0.011)
    neck = (np.abs(xx - 0.66) < 0.035) & (yy > 0.5) & (yy < 0.56)
    body = (np.abs(xx - 0.66) < np.minimum(0.05 + (yy - 0.535) * 2.2, 0.17 + (yy - 0.6) * 0.1)) & (yy > 0.535) & (yy < 0.82)
    sh = blur((head | hat | neck | body).astype(np.float32), 5)
    blind = blind * (1 - 0.62 * sh * (yy < 0.82))
    save('glass_lit1', (bars(blind, cross=False)[..., None] * np.array([1.0, 0.7, 0.36], np.float32)))
    # 2: a saloon or chop-house front: a cafe curtain on a brass rod to head height, gas globes in the room beyond
    room = 0.16 + 0.10 * (1 - yy)
    for lx, ly, s_, amp in ((0.22, 0.2, 60, 0.9), (0.52, 0.16, 70, 0.8), (0.82, 0.22, 55, 0.9), (0.38, 0.3, 500, 1.0), (0.7, 0.28, 600, 1.0), (0.12, 0.33, 700, 0.8)):
        room = room + amp * np.exp(-((xx - lx) ** 2 + (yy - ly) ** 2) * s_) * (0.5 if s_ < 100 else 1.0)
    fig = np.zeros((n, n), np.float32)                      # men at the bar, soft shapes against the light
    for fx_, w_, h_ in ((0.27, 0.04, 0.2), (0.33, 0.035, 0.17), (0.66, 0.045, 0.22), (0.9, 0.035, 0.16)):
        fig = np.maximum(fig, ((np.abs(xx - fx_) < w_ * (0.6 + 0.6 * np.clip((yy - (0.55 - h_)) * 6, 0, 1))) & (yy > 0.55 - h_)).astype(np.float32))
        fig = np.maximum(fig, (np.hypot((xx - fx_) / (w_ * 0.55), (yy - (0.55 - h_)) / 0.045) < 1).astype(np.float32))
    room = room * (1 - 0.38 * blur(fig, 9))
    curtain = (0.42 + 0.035 * np.sin(xx * 210 + 2.5 * np.sin(yy * 7)) + 0.02 * np.sin(xx * 77)) * (0.85 + 0.15 * blur(white(n, 3), 2)) * (0.75 + 0.5 * np.exp(-((xx - 0.5) ** 2) * 3))
    v = np.where(yy > 0.56, curtain, room)
    v = np.where(np.abs(yy - 0.56) < 0.007, 0.75, v)        # the brass rod
    v = v * (0.9 + 0.1 * fbm(n, 6, 4, 3))
    save('glass_lit2', np.clip(v, 0, 1.2)[..., None] * np.array([1.0, 0.66, 0.30], np.float32))
    # 3: a dim back room: one candle behind a dirty pane
    v = 0.10 + 0.5 * np.exp(-((xx - 0.3) ** 2 * 14 + (yy - 0.68) ** 2 * 16))
    v = v * (0.7 + 0.3 * fbm(n, 6, 5, 3))
    save('glass_lit3', bars(v)[..., None] * np.array([1.0, 0.55, 0.22], np.float32))
    # 4: obscured glass with the light of a room behind it: door lights, side lights, transoms
    v = (0.34 + 0.3 * np.exp(-((xx - 0.5) ** 2 * 2.5 + (yy - 0.35) ** 2 * 3))) * (0.85 + 0.15 * blur(white(n, 7), 1)) * (0.9 + 0.1 * fbm(n, 5, 8, 3))
    save('glass_lit4', v[..., None] * np.array([1.0, 0.64, 0.29], np.float32))


# --- lettering rasterised from Blender's text curves ---------------------------------------------------------

_TXT = {}
def text_tris(s):
    """Triangles (k,3,2) of string s set in the game's face at cap height ~0.7, and its bounds."""
    if s in _TXT: return _TXT[s]
    cu = bpy.data.curves.new('rt', 'FONT')
    cu.body = s
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.size = 1.0; cu.resolution_u = 3
    ob = bpy.data.objects.new('rt', cu)
    bpy.context.scene.collection.objects.link(ob)
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    me.calc_loop_triangles()
    co = np.array([v.co[:2] for v in me.vertices], np.float32).reshape(-1, 2)
    tri = np.array([t.vertices[:] for t in me.loop_triangles], np.int32).reshape(-1, 3)
    bpy.data.meshes.remove(me)
    t = co[tri] if len(tri) else np.zeros((0, 3, 2), np.float32)
    bounds = (co[:, 0].min(), co[:, 0].max()) if len(co) else (0, 0)
    _TXT[s] = (t, bounds)
    return _TXT[s]


def draw_text(mask, s, cx, cy, h, maxw=None, align='c', squeeze=1.0):
    """Rasterise s into mask (float 0..1, row 0 at the top): letters h pixels tall (cap height), centred on
    (cx, cy), narrowed to fit maxw. Returns the width drawn."""
    tris, (x0, x1) = text_tris(s)
    if not len(tris): return 0
    sy = h / 0.70
    sx = sy * squeeze
    if maxw and (x1 - x0) * sx > maxw: sx = maxw / (x1 - x0)
    wpx = (x1 - x0) * sx
    ox = {'c': cx - wpx / 2, 'l': cx, 'r': cx - wpx}[align] - x0 * sx
    oy = cy + 0.35 * sy
    P = np.empty_like(tris)
    P[..., 0] = tris[..., 0] * sx + ox
    P[..., 1] = oy - tris[..., 1] * sy
    H, W = mask.shape
    for a, b, c in P:
        xa, xb = int(max(0, math.floor(min(a[0], b[0], c[0])))), int(min(W, math.ceil(max(a[0], b[0], c[0])) + 1))
        ya, yb = int(max(0, math.floor(min(a[1], b[1], c[1])))), int(min(H, math.ceil(max(a[1], b[1], c[1])) + 1))
        if xa >= xb or ya >= yb: continue
        gx = np.arange(xa, xb, dtype=np.float32)[None, :] + 0.5
        gy = np.arange(ya, yb, dtype=np.float32)[:, None] + 0.5
        e0 = (b[0] - a[0]) * (gy - a[1]) - (b[1] - a[1]) * (gx - a[0])
        e1 = (c[0] - b[0]) * (gy - b[1]) - (c[1] - b[1]) * (gx - b[0])
        e2 = (a[0] - c[0]) * (gy - c[1]) - (a[1] - c[1]) * (gx - c[0])
        ins = ((e0 >= 0) & (e1 >= 0) & (e2 >= 0)) | ((e0 <= 0) & (e1 <= 0) & (e2 <= 0))
        mask[ya:yb, xa:xb][ins] = 1.0
    return wpx


class Sheet:
    """A poster or painted board drawn at twice its final size, then reduced."""
    def __init__(self, w, h, paper):
        self.w, self.h = w * 2, h * 2
        self.rgb = np.empty((self.h, self.w, 3), np.float32); self.rgb[:] = srgb(paper)

    def rect(self, x0, y0, x1, y1, colour, alpha=1.0):
        a = [int(round(v * 2)) for v in (x0, y0, x1, y1)]
        self.rgb[a[1]:a[3], a[0]:a[2]] = lerp(self.rgb[a[1]:a[3], a[0]:a[2]], srgb(colour), alpha)

    def border(self, inset, t, colour):
        w, h = self.w / 2, self.h / 2
        self.rect(inset, inset, w - inset, inset + t, colour); self.rect(inset, h - inset - t, w - inset, h - inset, colour)
        self.rect(inset, inset, inset + t, h - inset, colour); self.rect(w - inset - t, inset, w - inset, h - inset, colour)

    def text(self, s, y, h, colour, x=None, maxw=None, align='c', squeeze=1.0, shadow=None):
        m = np.zeros((self.h, self.w), np.float32)
        cx = (self.w / 2 if x is None else x * 2)
        mw = (self.w * 0.9 if maxw is None else maxw * 2)
        if shadow:
            ms = np.zeros_like(m)
            draw_text(ms, s, cx + h * 0.16, y * 2 + h * 0.16, h * 2, mw, align, squeeze)
            self.rgb[:] = lerp(self.rgb, srgb(shadow), ms[..., None])
        draw_text(m, s, cx, y * 2, h * 2, mw, align, squeeze)
        self.rgb[:] = lerp(self.rgb, srgb(colour), m[..., None])

    def rule(self, y, t, colour, inset=0.1):
        w = self.w / 2
        self.rect(w * inset, y - t / 2, w * (1 - inset), y + t / 2, colour)

    def done(self, age=0.5, seed=0, fade=0.0, folds=True, kind='paper'):
        rgb = half(self.rgb)
        h, w = rgb.shape[:2]
        n = max(h, w)
        N = 1 << (n - 1).bit_length()
        st = fbm(N, 4, 90 + seed, 4)[:h, :w]
        fine = fbm(N, 40, 91 + seed, 3)[:h, :w]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        if kind == 'paper':
            rgb = lerp(rgb, np.full(3, rgb.mean(), np.float32) * 0.5 + rgb * 0.5 + 0.02, fade * (0.5 + 0.5 * fine)[..., None])
            rgb = rgb * (1 - age * 0.45 * sstep(0.35, 0.8, st))[..., None] * np.array([1.0, 0.96, 0.86], np.float32)
            edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
            rgb *= (0.72 + 0.28 * sstep(0, 0.04 * n + 3, edge + 6 * (fine - 0.5)))[..., None]
            if folds:
                for fr in (0.33, 0.66):
                    rgb *= (1 - 0.18 * np.exp(-((yy - h * fr) / 1.2) ** 2))[..., None]
                rgb *= (1 - 0.12 * np.exp(-((xx - w * 0.5) / 1.2) ** 2))[..., None]
            rain = sstep(0.6, 0.9, tnoise(N, (2, 40), 92 + seed)[:h, :w]) * age
            rgb *= (1 - 0.10 * rain)[..., None]
        else:  # painted board or enamel: weathered paint, grime in the corners
            rgb = rgb * (0.8 + 0.25 * st)[..., None]
            chip = sstep(0.7, 0.8, fbm(N, 24, 93 + seed, 3)[:h, :w]) * age
            rgb = lerp(rgb, srgb('#4a4036') * (0.6 + 0.6 * fine)[..., None], (chip * 0.7)[..., None])
        return np.clip(rgb, 0, 1)


def paper_atlas(size=2048):
    """Posters, handbills, painted boards and enamel plates, packed into one square image. Returns
    {name: (u0, v0, u1, v1, width_m, height_m)} with v up, for fitting quads to."""
    INK, RED, BLUE = '#1a1410', '#7a1c12', '#1d2c4a'
    items = []   # (name, rgb, width_m)

    def add(name, sheet_rgb, width_m): items.append((name, sheet_rgb, width_m))

    # the hoarding at the dead end (alley.js / Chapter1: "the billboard")
    s = Sheet(1280, 640, '#cdbf9a')
    s.border(14, 6, RED); s.border(26, 2, INK)
    s.text("DR. HALLORAN'S", 150, 120, RED, shadow='#3a2a1c')
    s.text('CELEBRATED ELIXIR', 290, 78, INK)
    s.rule(356, 4, INK, 0.2)
    s.text('Cures every ailment known to science', 418, 44, INK)
    s.rect(330, 480, 950, 578, RED)
    s.text('25 CENTS · ALL DRUGGISTS', 530, 46, '#e6d9b4', maxw=580)
    add('billboard', s.done(0.7, 1, 0.25, folds=False), 3.4)

    s = Sheet(300, 560, '#d8c58f')
    s.border(8, 4, INK)
    s.text('TIVOLI', 64, 62, RED); s.text('OPERA HOUSE', 124, 26, INK)
    s.rule(152, 3, INK)
    s.text('TO-NIGHT', 190, 30, INK)
    s.text('THE', 240, 22, RED); s.text('MIKADO', 300, 66, RED, shadow='#2a1c12')
    s.text('or, The Town of Titipu', 356, 17, INK)
    s.rule(384, 2, INK)
    s.text('Every Evening at Eight', 414, 19, INK)
    s.text('Admission 25 & 50 Cents', 448, 19, INK)
    s.text('EDDY STREET near MARKET', 500, 16, INK)
    add('bill_tivoli', s.done(0.6, 2, 0.2), 0.62)

    s = Sheet(260, 340, '#d9d2bd')
    s.border(6, 3, INK)
    s.text('$500', 62, 70, INK); s.text('REWARD', 130, 44, INK)
    s.rule(164, 3, INK)
    for k, line in enumerate(('Will be paid for information', 'leading to the arrest of the', 'persons who robbed the', 'Oakland mail on June 9th.')):
        s.text(line, 192 + k * 24, 14, INK)
    s.text('P. CROWLEY', 298, 18, INK); s.text('Chief of Police', 320, 12, INK)
    add('bill_reward', s.done(0.5, 3, 0.1), 0.46)

    s = Sheet(300, 430, '#c9b37e')
    s.rect(0, 0, 300, 96, BLUE)
    s.text('PACIFIC MAIL', 36, 30, '#e6dcc0'); s.text('STEAMSHIP COMPANY', 72, 16, '#e6dcc0')
    s.text('FOR', 128, 18, INK); s.text('HONGKONG', 176, 46, RED)
    s.text('via Honolulu & Yokohama', 222, 16, INK)
    s.rule(246, 2, INK)
    s.text('The Steamer', 274, 16, INK); s.text('LA PALOMA', 318, 40, BLUE)
    s.text('Sails from Brannan St. Wharf', 368, 14, INK); s.text('SATURDAY at Noon', 396, 18, RED)
    add('bill_paloma', s.done(0.65, 4, 0.2), 0.56)

    s = Sheet(280, 400, '#cfc7a5')
    s.border(7, 5, RED)
    s.text('AUCTION', 66, 60, RED)
    s.text('BY ORDER OF THE EXECUTORS', 116, 13, INK)
    s.text('Household Furniture', 160, 24, INK); s.text('Pianos · Carpets · Plate', 196, 20, INK)
    s.text('and a quantity of', 232, 14, INK); s.text('FINE OLD WINES', 266, 28, INK)
    s.rule(296, 2, INK)
    s.text('SATURDAY · 10 A.M.', 326, 24, RED); s.text('318 Pine Street', 362, 17, INK)
    add('bill_auction', s.done(0.55, 5, 0.15), 0.5)

    s = Sheet(340, 250, '#d5c9a2')
    s.border(6, 3, INK)
    s.text('GRAND', 44, 28, INK); s.text('MASQUERADE BALL', 96, 36, RED, maxw=300)
    s.text("Mechanics' Pavilion", 146, 22, INK)
    s.text('Thanksgiving Eve', 182, 18, INK); s.text('Gentlemen $1 · Ladies Free', 216, 15, INK)
    add('bill_ball', s.done(0.7, 6, 0.3), 0.62)

    s = Sheet(200, 260, '#d6ceb4')
    s.text('ROOMS', 56, 52, INK); s.text('TO LET', 116, 36, INK)
    s.rule(146, 2, INK); s.text('By the Day or Week', 172, 15, INK); s.text('Enquire Within', 204, 17, RED); s.text('25 Cts. & Upward', 234, 13, INK)
    add('bill_rooms', s.done(0.5, 7, 0.1), 0.3)

    s = Sheet(200, 260, '#c8bc92')
    s.text('WANTED', 50, 44, RED); s.rule(84, 2, INK)
    s.text('ABLE SEAMEN', 116, 22, INK); s.text('& Firemen', 148, 18, INK)
    s.text('for the China run', 180, 15, INK); s.text('Apply Pier 40', 220, 20, INK)
    add('bill_seamen', s.done(0.7, 8, 0.25), 0.3)

    s = Sheet(220, 280, '#d0c8ae')
    s.border(5, 3, BLUE)
    s.text('FOR MAYOR', 44, 20, INK); s.text('SUTRO', 104, 60, BLUE)
    s.text("The People's Choice", 158, 16, INK); s.rule(182, 2, INK)
    s.text('No Fare Above', 212, 16, INK); s.text('5 CENTS', 250, 30, RED)
    add('bill_sutro', s.done(0.8, 9, 0.35), 0.34)

    s = Sheet(220, 150, '#c9be9c')
    s.text('STEAM BEER', 36, 30, INK, maxw=200); s.text('5¢', 86, 40, RED); s.text('Free Lunch', 130, 14, INK)
    add('bill_beer', s.done(0.5, 10, 0.1, folds=False), 0.36)

    s = Sheet(360, 520, '#bdb49a')     # a newspaper, trodden into the gutter
    s.text('THE MORNING CALL', 42, 30, INK, maxw=330); s.rule(66, 2, INK, 0.04); s.rule(72, 1, INK, 0.04)
    s.text('SAN FRANCISCO, THURSDAY MORNING', 86, 9, INK)
    s.text('SUTRO DEFIES THE OCTOPUS', 120, 18, INK, maxw=330)
    rng = np.random.default_rng(4)
    for c in range(4):
        x0 = 14 + c * 85
        for r in range(60):
            if rng.random() < 0.06: continue
            s.rect(x0, 146 + r * 6, x0 + 60 + rng.random() * 16, 148 + r * 6, '#3a342c', 0.75)
    add('newspaper', s.done(1.0, 11, 0.3), 0.42)

    # painted boards and enamel plates
    def board(name, lines, w, h, ground, ink, width_m, rim=None, age=0.4, seed=20):
        s = Sheet(w, h, ground)
        if rim: s.border(5, 4, rim)
        n = len(lines)
        for k, (line, size) in enumerate(lines):
            s.text(line, h * (k + 0.5) / n + (2 if n == 1 else 0), size, ink, maxw=w * 0.84, shadow=None)
        add(name, s.done(age, seed, kind='board'), width_m)

    board('plate_burritt', [('BURRITT ST.', 40)], 400, 90, '#16223a', '#e8e4d6', 0.75, rim='#e8e4d6', age=0.25, seed=21)
    board('plate_bush', [('BUSH ST.', 40)], 400, 90, '#16223a', '#e8e4d6', 0.75, rim='#e8e4d6', age=0.25, seed=22)
    board('sign_rooms', [('ROOMS', 60), ('25¢ · 50¢', 34)], 320, 200, '#e2d8bc', '#1a1410', 0.8, rim='#7a1c12', seed=23)
    board('sign_oysters', [('OYSTERS', 52), ('in every style', 26)], 360, 180, '#142a20', '#d9b24a', 0.9, rim='#d9b24a', seed=24)
    board('sign_baths', [('BATHS', 60), ('HOT & COLD 25¢', 26)], 320, 180, '#e2d8bc', '#16223a', 0.8, rim='#16223a', seed=25)
    board('sign_cigars', [('CIGARS', 64)], 380, 120, '#5a1712', '#d9b24a', 0.95, rim='#d9b24a', seed=26)
    board('sign_loans', [('MONEY LOANED', 40), ('Watches · Jewelry', 24)], 380, 150, '#101010', '#d9b24a', 0.95, rim='#d9b24a', seed=27)
    board('sign_livery', [('HORSES BOARDED', 36), ('BY THE DAY OR MONTH', 22)], 420, 130, '#e2d8bc', '#1a1410', 1.2, rim='#1a1410', age=0.6, seed=28)
    board('sign_nobills', [('POST NO BILLS', 44)], 440, 80, '#d8d0b8', '#1a1410', 1.1, age=0.7, seed=29)
    board('sign_lunch', [('FREE LUNCH', 44), ('with every glass', 24)], 340, 150, '#e2d8bc', '#7a1c12', 0.7, rim='#1a1410', seed=30)
    board('sign_deliveries', [('DELIVERIES', 40)], 380, 80, '#2b3329', '#d8cdb0', 0.8, age=0.6, seed=31)
    board('sign_stair', [('LODGINGS', 44), ('UPSTAIRS', 30)], 300, 150, '#d8cdb0', '#2a1a14', 0.6, rim='#2a1a14', age=0.6, seed=32)
    board('crate_holtz', [('J. HOLTZ & SON', 30), ('S. F.', 26)], 280, 110, '#7c6444', '#1e1812', 0.5, age=0.8, seed=33)
    board('crate_fragile', [('GLASS', 44), ('WITH CARE', 26)], 240, 120, '#7c6444', '#5a1410', 0.42, age=0.8, seed=34)
    board('crate_tea', [('FINEST OOLONG', 28), ('CANTON', 34)], 260, 120, '#7c6444', '#1e1812', 0.45, age=0.8, seed=35)

    # pack in rows, tallest first
    atlas = np.zeros((size, size, 3), np.float32); atlas[:] = srgb('#6c6250')
    uv = {}
    x = y = rowh = 0
    pad = 6
    for name, rgb, wm in sorted(items, key=lambda it: -it[1].shape[0]):
        h, w = rgb.shape[:2]
        if x + w + pad > size: x, y, rowh = 0, y + rowh + pad, 0
        if y + h > size: raise RuntimeError('paper atlas is full at ' + name)
        atlas[y:y + h, x:x + w] = rgb
        # bleed a 2 px margin so mip-maps do not pull in the neighbour
        atlas[y:y + h, x + w:x + w + 3] = rgb[:, -1:]
        atlas[y + h:y + h + 3, x:x + w + 3] = atlas[y + h - 1:y + h, x:x + w + 3]
        uv[name] = (x / size, 1 - (y + h) / size, (x + w) / size, 1 - y / size, wm, wm * h / w)
        x += w + pad; rowh = max(rowh, h)
    save('paper_atlas', atlas)
    return uv


# --- materials -----------------------------------------------------------------------------------------------

def pbr(name, tex=None, nrm=None, rough_tex=None, rough=0.8, metal=0.0, scale=1.0, color='#808080', nstrength=1.0):
    """A Principled material from this module's images: colour, normal, roughness (+ the Unity mask node)."""
    material(name, color, rough=rough, metal=metal, tex=TEX[tex] if tex else None, nrm=TEX[nrm] if nrm else None, scale=scale)
    m = MATS[name][0]
    nt = m.node_tree
    p = nt.nodes['Principled BSDF']
    for nd in nt.nodes:
        if nd.type == 'NORMAL_MAP': nd.inputs['Strength'].default_value = nstrength
    if rough_tex:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = TEX[rough_tex + '_r']; t.label = 'roughness'
        nt.links.new(t.outputs['Color'], p.inputs['Roughness'])
        u = nt.nodes.new('ShaderNodeTexImage'); u.image = TEX[rough_tex + '_ms']; u.label = 'unity metallic-smoothness'
        u.location = (-600, -600)
    return name


def lit(name, tex, strength=2.2):
    """An emissive pane whose picture is fitted to its quad (scale None)."""
    material(name, '#000000', rough=0.3, emit_tex=TEX[tex], emit_strength=strength, scale=None)
    return name
