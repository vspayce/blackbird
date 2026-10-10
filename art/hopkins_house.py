# The outside of the Mark Hopkins mansion (Wright & Sanders, 1875-78; the Mark Hopkins Institute of Art from
# 1893; burnt 1906), built round the interior plan in build_hopkins.py. Called from build_hopkins.main() in place
# of the old castle exterior:  hopkins_house.build(sys.modules[__name__])
#
# What the photographs show (Wikimedia Commons: "Residence of the Late Mark Hopkins" stereoview c.1878; "Mark
# Hopkins mansion, California Street, 1890s"; "Mark Hopkins mansion c1880" from California & Mason; "Hopkins Art
# Institute (Hopkins Mansion)" 1906; "Mark Hopkins mansion from Pine Street, c1890"; "...California Street
# carriage entrance"):
#   - not a crenellated castle: a redwood house in a mixed Gothic / Second Empire manner, the boards painted and
#     sanded to read as grey stone, with pilaster strips, panelled walls, belt courses and a heavy bracketed
#     cornice under steep slate roofs;
#   - along California Street, west to east: a corner pavilion with a steep hipped roof and gabled dormers; the
#     entrance porch, a stone-looking block with a pointed carriage arch, corner piers with finials and a
#     balustrade on top; a tall square tower with a steep concave mansard, gabled lucarnes with balconies, iron
#     cresting and a needle spire; a round turret carried up from the ground with a tall "candle-snuffer" cone;
#     big panelled chimneys; a very steep front gable filled with lancet panels under pierced bargeboards and a
#     finial; and at the east end a glass conservatory of pointed-arch gables round a ribbed dome;
#   - iron cresting on the ridges and mansard tops, finials on every gable and hip;
#   - the house on a terrace behind a granite retaining wall with square gate piers and an iron fence.
# The tower here stands at the back east corner, over the game's tower stair (Gutman's observatory is fixed there
# by src/cases/gutman.js); in 1878 it rose behind the porch, nearer the middle of the house.
import math, random
from setkit import *  # noqa: F401,F403

K = None                    # the build_hopkins module (its helpers, constants and lists)
EAVE = 11.8                 # the main cornice
DECK = 16.6                 # the mansard's flat top
PD = 0.6                    # how far the corner pavilion and the east gable block stand forward
OFF = 0.225                 # half the outer wall thickness (T + 0.1) / 2
TRIM = 'trim_stone'
rr = random.Random(1878)

SIDES = {  # the outer wall lines, as build_house draws them (the normal (-r.z, 0, r.x) points outward)
    'front': ((-15, 14), (15, 14)),
    'east': ((15, 14), (15, -14)),
    'back_e': ((15, -14), (7, -14)),
    'back_w': ((-7, -14), (-15, -14)),
    'west': ((-15, -14), (-15, 14)),
}
# upstairs window openings (0.9 wide), in world x or z along each wall; pairs sit 1.2 apart under one hood
UPPER = {
    'front': [(-11.0, 2), (-5.4, 2), (0.0, 2), (11.1, 2)],
    'east': [(12.0, 1), (8.0, 2), (4.4, 1), (-4.4, 1), (-10.0, 1)],
    'back_e': [(11.5, 2)],
    'back_w': [(-11.0, 2)],
    'west': [(12.0, 1), (8.0, 2), (4.0, 1), (-2.2, 2), (-10.0, 2)],
}
GROUND = {  # the ground-floor windows build_house cuts (world x or z), for their outside dressing
    'front': [-12, -6, 12],          # (x = 6 opens into the turret)
    'east': [10, 4, -4, -8, -12],
    'back_e': [13, 9],
    'back_w': [-9, -13],
    'west': [12, 8, 4, 0, -4, -10],
}
TURRET = (5.4, 14.7, 1.8)   # x, z, radius
PROJ = {  # forward-standing blocks: (t0, t1) along the side, standing out PD
    'front': [(-0.225 - PD, 8.2), (22.0, 30.225)],
    'west': [(15.5, 28.225 + PD)],
}
CONS = (15.225, 21.4, -3.0, 3.0)  # the conservatory: x0, x1, z0, z1


def side_frame(key, off=OFF):
    a, b = SIDES[key]
    A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
    r = (B - A).normalized()
    n = Vector((-r.z, 0, r.x))
    return frame(A + n * off, r, n), (B - A).length


def proj_at(key, t):
    for t0, t1 in PROJ.get(key, ()):
        if t0 < t < t1: return (t0, t1)
    return None


def dress_frame(key, t):
    """The face a window at t is dressed on: the wall's own face, or a forward block's."""
    return side_frame(key, OFF + (PD if proj_at(key, t) else 0.0))[0]


def t_of(key, c):
    """Distance along a side's wall line to world coordinate c (x on the front and back, z on the sides)."""
    a, b = SIDES[key]
    if key == 'front': return c - a[0]
    if key == 'east': return a[1] - c
    if key in ('back_e', 'back_w'): return a[0] - c
    return c - a[1]  # west


# --- primitives ----------------------------------------------------------------------------------

def poly(mat, pts):
    q = []
    for p in pts:
        p = Vector(p)
        if not q or (p - q[-1]).length > 1e-4: q.append(p)
    if len(q) > 2 and (q[0] - q[-1]).length < 1e-4: q.pop()
    if len(q) >= 3:
        bm = bm_for(mat)
        bm.faces.new([bm.verts.new(p) for p in q])


def hip(mat, x0, x1, z0, z1, rings, deck=None):
    """A hipped / mansard roof from rings of (inset, y); an inset past half the width closes to a ridge."""
    def ring(d, y):
        dx = min(d, (x1 - x0) / 2); dz = min(d, (z1 - z0) / 2)
        return [Vector((x0 + dx, y, z0 + dz)), Vector((x1 - dx, y, z0 + dz)), Vector((x1 - dx, y, z1 - dz)), Vector((x0 + dx, y, z1 - dz))]
    R = [ring(d, y) for d, y in rings]
    for a, b in zip(R, R[1:]):
        for i in range(4):
            j = (i + 1) % 4
            poly(mat, [a[i], a[j], b[j], b[i]])
    if deck: poly(deck, R[-1])
    return R[-1]


def gable(x0, x1, z0, z1, y, rise, axis='z', ends=(True, True), ov=0.5, wall='ashlar', mat='slate'):
    """A steep pitched roof over the rectangle (overhang included) with gable walls set back ov at the ends.
    Returns the gable ends as (centre at eave level, right, out, half-width at the roof edge)."""
    out = []
    if axis == 'z':
        xm = (x0 + x1) / 2; p = rise / (xm - x0)
        poly(mat, [(x0, y, z1), (x0, y, z0), (xm, y + rise, z0), (xm, y + rise, z1)])
        poly(mat, [(x1, y, z0), (x1, y, z1), (xm, y + rise, z1), (xm, y + rise, z0)])
        for k, (z, s) in enumerate(((z0 + ov, -1), (z1 - ov, 1))):
            if not ends[k]: continue
            poly(wall, [(x0 + ov, y - 0.5, z), (x1 - ov, y - 0.5, z), (x1 - ov, y + ov * p, z), (xm, y + rise - 0.05, z),
                        (x0 + ov, y + ov * p, z)])
            out.append((Vector((xm, y, z)), Vector((-s, 0, 0)), Vector((0, 0, s)), xm - x0, rise, ov))
    else:
        zm = (z0 + z1) / 2; p = rise / (zm - z0)
        poly(mat, [(x0, y, z0), (x1, y, z0), (x1, y + rise, zm), (x0, y + rise, zm)])
        poly(mat, [(x1, y, z1), (x0, y, z1), (x0, y + rise, zm), (x1, y + rise, zm)])
        for k, (x, s) in enumerate(((x0 + ov, -1), (x1 - ov, 1))):
            if not ends[k]: continue
            poly(wall, [(x, y - 0.5, z0 + ov), (x, y - 0.5, z1 - ov), (x, y + ov * p, z1 - ov), (x, y + rise - 0.05, zm),
                        (x, y + ov * p, z0 + ov)])
            out.append((Vector((x, y, zm)), Vector((0, 0, s)), Vector((s, 0, 0)), zm - z0, rise, ov))
    return out


def barge(g, truss=True, finial=1.6):
    """Pierced bargeboards down both rakes of a gable, a hanging pendant and a finial at the apex, and the
    king-post truss across the gable's head that the photographs show."""
    c, r, n, hw, rise, ov = g
    F = frame(c, r, n)
    w = ov - 0.06
    for s in (-1, 1):
        A = Vector((s * hw, -0.05, w)); B = Vector((0, rise - 0.05, w))
        d = Vector((0, -0.42, 0))
        poly(TRIM, [F @ A, F @ B, F @ (B + d), F @ (A + d)])
        nseg = max(3, int((B - A).length / 0.7))
        for k in range(nseg):
            p0 = A.lerp(B, k / nseg) + d; p1 = A.lerp(B, (k + 1) / nseg) + d
            poly(TRIM, [F @ p0, F @ p1, F @ (p0.lerp(p1, 0.5) + Vector((0, -0.22, 0)))])  # the cusps
            if k: tube(TRIM, [F @ p0, F @ (p0 + Vector((0, -0.38, 0)))], 0.035, 4)        # drops
    top = Vector((0, rise, w))
    tube(TRIM, [F @ (top + Vector((0, -1.3, 0))), F @ (top + Vector((0, finial * 0.6, 0)))], 0.07, 4)
    cyl(TRIM, F @ (top + Vector((0, -1.5, 0))), 0.25, 0.02, 0.1, seg=4)
    cyl('iron', F @ (top + Vector((0, finial * 0.6, 0))), finial * 0.4, 0.05, 0.005, seg=4)
    if truss:  # collar and king post a little behind the bargeboards
        v = rise * 0.42
        hh = hw * (1 - v / rise) - 0.15
        lbox(F, TRIM, -hh, hh, v - 0.08, v + 0.08, w - 0.25, w - 0.1)
        lbox(F, TRIM, -0.07, 0.07, v, rise - 0.4, w - 0.25, w - 0.1)
        for s in (-1, 1):
            tube(TRIM, [F @ Vector((s * hh * 0.6, v, w - 0.18)), F @ Vector((0, v + (rise - v) * 0.45, w - 0.18))], 0.05, 4)


def crest(pts, y, step=0.6, h=0.55, closed=False):
    """Iron cresting: a rail on posts, each post tipped with a spike."""
    pts = [Vector((p[0], y, p[1])) for p in pts]
    if closed: pts = pts + pts[:1]
    for a, b in zip(pts, pts[1:]):
        L = (b - a).length
        tube('iron', [a + Vector((0, h * 0.55, 0)), b + Vector((0, h * 0.55, 0))], 0.018, 4)
        for k in range(int(L / step) + 1):
            p = a.lerp(b, k * step / L) if L else a
            tube('iron', [p, p + Vector((0, h, 0))], 0.012, 3)
            cyl('iron', p + Vector((0, h, 0)), 0.16, 0.035, 0.0, seg=4, cap=False)


def pointed(hw, spring, k=1.0, n=5):
    """A two-centred pointed arch of half-span hw: points from the left springing over the apex to the right.
    k = radius / span (1.0 equilateral, 0.55 nearly round)."""
    Rr = max(k * 2 * hw, hw * 1.001)
    cx = -hw + Rr
    apex = math.sqrt(Rr ** 2 - cx ** 2)
    a1 = math.atan2(apex, -cx)
    left = [(cx + Rr * math.cos(t), spring + Rr * math.sin(t)) for t in np.linspace(math.pi, a1, n)]
    right = [(-u, v) for u, v in reversed(left[:-1])]
    return left + right


def arch(F, hw, spring, top, w=0.0, k=0.6, wall='ashlar', mould=True, n=5):
    """Fill the spandrels of a pointed opening of half-span hw up to `top`, with a moulding round the arch."""
    P = pointed(hw, spring, k, n)
    m = len(P) // 2
    poly(wall, [F @ Vector((u, v, w)) for u, v in P[:m + 1]] + [F @ Vector((0, top, w)), F @ Vector((-hw, top, w))])
    poly(wall, [F @ Vector((u, v, w)) for u, v in P[m:]] + [F @ Vector((hw, top, w)), F @ Vector((0, top, w))])
    if mould:
        tube(TRIM, [F @ Vector((u, v + 0.06, w + 0.08)) for u, v in P], 0.1, 4)
    return P


def pair_hood(F, c, v, w=0.9, gap=1.2):
    """A pointed hood mould over a pair of lancets, with a roundel in the head between them."""
    hw = gap / 2 + w / 2 + 0.25
    P = pointed(hw, v, 0.62, 4)
    tube(TRIM, [F @ Vector((c + u, y, 0.14)) for u, y in P], 0.07, 4)
    apex = P[len(P) // 2][1]
    nrm = (F.to_3x3() @ Vector((0, 0, 1))).normalized()
    ctr = F @ Vector((c, (v + 0.75 + apex) / 2, 0.06))
    cyl(TRIM, ctr, 0.08, 0.3, seg=8, axis=nrm)
    cyl('glass_dark', ctr + nrm * 0.08, 0.01, 0.2, seg=8, axis=nrm)


# --- the walls -----------------------------------------------------------------------------------

def upper_storey():
    """The upper storey's outer walls (5.5 to the cornice), with the upstairs windows the rooms are lined round."""
    UF = K.UF
    for key in SIDES:
        a, b = SIDES[key]
        opens = []
        for c, nwin in UPPER[key]:
            for d in ((-0.6, 0.6) if nwin == 2 else (0.0,)):
                opens.append(t_of(key, c) + (d if key in ('front', 'west') else -d))
        K.wall(a, b, K.H, EAVE, [(t, 0.9, UF + 0.9, UF + 3.3) for t in opens], mat='ashlar', thick=K.T + 0.1)
        Fl, L = side_frame(key, 0.0)
        for t in opens:
            K.lancet(dress_frame(key, t), t, UF + 0.9, 0.9, 2.4, glass='glass_clear')
            p = Fl @ Vector((t, 0, 0))
            K.UPPER_WINDOWS.append((round(p.x, 3), round(p.z, 3)))
        for c, nwin in UPPER[key]:
            if nwin == 2: pair_hood(dress_frame(key, t_of(key, c)), t_of(key, c), UF + 3.3)
        # the forward blocks: a second skin PD thick, with the same windows through it
        for t0, t1 in PROJ.get(key, ()):
            Fp, _ = side_frame(key, OFF + PD / 2)
            A = Fp @ Vector((t0, 0, 0)); B = Fp @ Vector((t1, 0, 0))
            ops = [(t - t0, 0.9, UF + 0.9, UF + 3.3) for t in opens if t0 < t < t1]
            ops += [(t_of(key, c) - t0, 1.2, 1.2, 4.0) for c in GROUND[key] if t0 < t_of(key, c) < t1]
            K.wall((A.x, A.z), (B.x, B.z), -0.1, EAVE, ops, mat='ashlar', thick=PD)
    # the hall's back wall where it shows above the solarium roof, and the strips of wall the side wings'
    # eaves sit on over the solarium
    Fh = frame((7, 0, -6.2), (-1, 0, 0), (0, 0, -1))
    lbox(Fh, 'ashlar', 0, 14, K.H, 14.1, 0, 0.12)
    for u in (3.0, 7.0, 11.0):
        K.lancet(Fh @ Matrix.Translation((0, 0, 0.12)), u, 9.0, 0.8, 2.6, glass='glass_dark')
    lbox(Fh, TRIM, 0, 14, 8.0, 8.2, 0.1, 0.3)
    for x in (-7, 7):
        wbox('ashlar', x - 0.225, x + 0.225, 10.9, EAVE, -14.2, -6.2)


def bracket_cornice(F, u0, u1, y, depth=0.55):
    lbox(F, TRIM, u0 - 0.1, u1 + 0.1, y - 0.18, y + 0.02, 0, depth)
    lbox(F, TRIM, u0, u1, y - 0.42, y - 0.18, 0, 0.16)
    lbox(F, TRIM, u0, u1, y - 0.85, y - 0.72, 0, 0.1)
    k = u0 + 0.4
    while k < u1 - 0.2:
        lbox(F, TRIM, k - 0.07, k + 0.07, y - 0.72, y - 0.18, 0, depth * 0.75)
        k += 1.0


def facade_detail():
    """Plinth, belt course, pilaster strips, the bracketed cornice, and the ground-floor windows' dressing."""
    tx, tz, trr = TURRET
    for key in SIDES:
        Fo, L = side_frame(key)
        runs = [(-0.25, 13.6), (16.4, L + 0.25)] if key == 'front' else [(-0.25, L + 0.25)]
        for u0, u1 in runs:
            lbox(Fo, 'ashlar', u0, u1, -0.1, 0.8, 0, 0.16)
            lbox(Fo, TRIM, u0, u1, 0.8, 0.92, 0, 0.2)
        lbox(Fo, TRIM, -0.25, L + 0.25, K.H - 0.05, K.H + 0.25, 0, 0.18)   # belt course
        lbox(Fo, TRIM, -0.25, L + 0.25, K.H - 0.28, K.H - 0.18, 0, 0.1)
        if key != 'back_e':  # (the back east wall carries the tower)
            bracket_cornice(Fo, -0.25, L + 0.25, EAVE)
        # pilaster strips: at the corners, and between the bays
        us = [0.25, L - 0.25]
        if key == 'front': us += [11.6]
        if key == 'west': us += [6.6, 13.8]
        if key == 'east': us += [6.6, 13.8, 19.0, 22.6]
        if key in ('back_w', 'back_e'): us += [4.0]
        for u in us:
            lbox(Fo, 'ashlar', u - 0.24, u + 0.24, 0.92, K.H - 0.28, 0, 0.12)
            lbox(Fo, 'ashlar', u - 0.2, u + 0.2, K.H + 0.25, EAVE - 0.85, 0, 0.1)
            lbox(Fo, TRIM, u - 0.28, u + 0.28, K.H - 0.6, K.H - 0.28, 0, 0.16)  # capitals
        for c in GROUND[key]:
            K.window_surround(dress_frame(key, t_of(key, c)), t_of(key, c), 1.2, 1.2, 2.8)
        Fp, _ = side_frame(key, OFF + PD)
        for t0, t1 in PROJ.get(key, ()):
            lbox(Fp, 'ashlar', t0 - 0.05, t1 + 0.05, -0.1, 0.8, 0, 0.16)
            lbox(Fp, TRIM, t0 - 0.05, t1 + 0.05, 0.8, 0.92, 0, 0.2)
            lbox(Fp, TRIM, t0 - 0.05, t1 + 0.05, K.H - 0.05, K.H + 0.25, 0, 0.18)
            lbox(Fp, TRIM, t0 - 0.05, t1 + 0.05, K.H - 0.28, K.H - 0.18, 0, 0.1)
            bracket_cornice(Fp, t0 - 0.05, t1 + 0.05, EAVE)
            for u in (t0 + 0.3, t1 - 0.3):
                lbox(Fp, 'ashlar', u - 0.28, u + 0.28, 0.92, K.H - 0.28, 0, 0.14)
                lbox(Fp, 'ashlar', u - 0.24, u + 0.24, K.H + 0.25, EAVE - 0.85, 0, 0.12)
                lbox(Fp, TRIM, u - 0.32, u + 0.32, K.H - 0.6, K.H - 0.28, 0, 0.18)
    K.front_door()
    # the rear cornice where the tower does not stand
    Fo, L = side_frame('back_e')
    bracket_cornice(Fo, 7.0, L + 0.25, EAVE)


# --- roofs -----------------------------------------------------------------------------------------

def dormer(c, r, n, w=1.5, h=2.1, lit=False):
    """A gabled lucarne on a steep slope: its face at c (bottom centre), standing out along n."""
    F = frame(c, r, n)
    lbox(F, 'ashlar', -w / 2, w / 2, 0, h, -2.2, 0)
    K.lancet(F, 0, 0.3, 0.55, h - 1.0, lit=lit)
    for s in (-1, 1):
        poly('slate', [F @ Vector((s * (w / 2 + 0.2), h, 0.25)), F @ Vector((0, h + 1.0, 0.25)),
                       F @ Vector((0, h + 1.0, -2.2)), F @ Vector((s * (w / 2 + 0.2), h, -2.2))])
    poly('ashlar', [F @ Vector((-w / 2, h, 0)), F @ Vector((w / 2, h, 0)), F @ Vector((0, h + 1.0, 0))])
    barge((F @ Vector((0, h, 0)), F.to_3x3() @ Vector((1, 0, 0)), n, w / 2 + 0.2, 1.0, 0.25), truss=False, finial=0.9)


def chimney(x, z, y0, y1, w=1.5, d=0.8):
    wbox('ashlar', x - w / 2, x + w / 2, y0, y1, z - d / 2, z + d / 2)
    wbox(TRIM, x - w / 2 - 0.1, x + w / 2 + 0.1, y1 - 1.2, y1 - 1.0, z - d / 2 - 0.1, z + d / 2 + 0.1)
    wbox(TRIM, x - w / 2 - 0.15, x + w / 2 + 0.15, y1, y1 + 0.25, z - d / 2 - 0.15, z + d / 2 + 0.15)
    for s in (-1, 1):  # sunk panels
        wbox('ashlar', x + s * w / 4 - 0.25, x + s * w / 4 + 0.25, y0 + 1.2, y1 - 1.5, z - d / 2 - 0.05, z + d / 2 + 0.05)
    for k in range(3):
        cyl('brick_red', (x + (k - 1) * w / 3.2, y1 + 0.25, z), 0.6, 0.13, 0.11, seg=6)


def roofs():
    E = EAVE
    # the main roof: a steep mansard over the front and middle of the house, flat on top with cresting
    deck = hip('slate', -15.725, 15.725, -7.2, 14.725, [(0, E), (2.8, DECK)], deck='roof')
    crest([(p.x, p.z) for p in deck], DECK, closed=True)
    # the west corner pavilion: a taller hipped roof, steep then flatter, with a ridge of cresting and finials
    top = hip('slate', -15.725 - PD, -6.3, 1.0, 14.725 + PD, [(-0.15, E - 0.1), (0.5, E + 1.0), (2.3, E + 5.6), (5.0, E + 8.2)])
    x = (top[0].x + top[1].x) / 2
    crest([(x, top[0].z), (x, top[3].z)], E + 8.2, step=0.5)
    for zz in (top[0].z, top[3].z):
        tube('iron', [(x, E + 8.2, zz), (x, E + 9.8, zz)], 0.04, 4)
        cyl('iron', (x, E + 9.2, zz), 0.25, 0.12, 0.02, seg=4)
    dormer(Vector((-11.0 - PD / 2, E + 0.6, 14.725 + PD - 0.75)), (1, 0, 0), (0, 0, 1), lit=True)
    dormer(Vector((-15.725 - PD + 0.75, E + 0.6, 8.0)), (0, 0, 1), (-1, 0, 0))
    # the front gable over the porch
    g = gable(-4.5, 4.5, 6.0, 14.725, E, 7.0, axis='z')
    barge(g[1])
    c = Vector((0, E + 2.7, 14.25))
    cyl(TRIM, c, 0.14, 1.05, seg=16, axis=(0, 0, 1))
    cyl('stained', c + Vector((0, 0, 0.14)), 0.02, 0.85, seg=16, axis=(0, 0, 1))
    for k in range(4):
        a = k * math.pi / 4
        tube(TRIM, [c + Vector((math.cos(a) * 0.85, math.sin(a) * 0.85, 0.17)), c + Vector((-math.cos(a) * 0.85, -math.sin(a) * 0.85, 0.17))], 0.035, 4)
    # the great east gable on California Street: very steep, filled with lancet panels
    g = gable(6.5, 15.725, 0.0, 14.725 + PD, E, 9.0, axis='z')
    barge(g[1], finial=2.2)
    F = frame((11.1125, 0, 14.25 + PD), (1, 0, 0), (0, 0, 1))
    p = 9.0 / 4.6125
    lbox(F, TRIM, -3.6, 3.6, E + 0.25, E + 0.45, 0, 0.12)
    for k in range(-2, 3):
        u = k * 1.15
        hmax = E + (4.1 - abs(u) - 0.55) * p - 0.9
        if hmax - (E + 0.6) < 0.8: continue
        lit = k in (-1, 1)
        K.lancet(F, u, E + 0.6, 0.62, hmax - (E + 0.6), lit=lit)
    # the back west wing: a gable to the bay
    g = gable(-15.725, -6.275, -14.725, -3.0, E, 7.0, axis='z')
    barge(g[0])
    Fb = frame((-11.0, 0, -14.25), (-1, 0, 0), (0, 0, -1))
    K.lancet(Fb, -0.6, E + 0.5, 0.6, 2.2, lit=True); K.lancet(Fb, 0.6, E + 0.5, 0.6, 2.2)
    # a cross gable on the west side, over the bedroom
    g = gable(-15.725, -11.0, -5.6, 1.2, E, 5.6, axis='x', ends=(True, False))
    barge(g[0])
    Fw = frame((-15.25, 0, -2.2), (0, 0, 1), (-1, 0, 0))
    K.lancet(Fw, 0, E + 0.5, 0.7, 2.0)
    # lean-to between the solarium and the tower
    poly('slate', [(6.275, E, -14.725), (6.275, E, -7.0), (8.0, E + 1.4, -7.0), (8.0, E + 1.4, -14.725)])
    # lucarnes on the mansard
    dormer(Vector((15.725 - 0.3, E + 0.1, -4.6)), (0, 0, -1), (1, 0, 0), lit=True)
    for x in (-3.6, 3.6):
        dormer(Vector((x, E + 0.1, -7.2 + 0.3)), (-1, 0, 0), (0, 0, -1), lit=x > 0)
    # chimneys, panelled, with pots
    for (x, z, y0, y1) in ((9.4, 8.6, 15.5, 22.6), (-11.15, 9.6, 18.0, 22.4), (-9.0, -4.2, 16.0, 21.4),
                           (2.2, -2.6, 18.0, 21.8), (-3.4, 6.4, 18.0, 21.6)):
        chimney(x, z, y0, y1)


# --- the turret, the tower, the porch, the conservatory ---------------------------------------------

def turret():
    """The round turret on California Street: carried up from the ground, windows on three storeys, a corbelled
    cornice and a tall candle-snuffer roof with a finial."""
    x, z, r = TURRET
    zw = 14.0 + OFF   # below the cornice the turret stops at the wall face: the rooms are behind it
    def band(mat, y0, h, r0, r1=None):
        r1 = r0 if r1 is None else r1
        a0 = math.asin(max(-1.0, min(1.0, (zw - z) / min(r0, r1))))
        A = np.linspace(a0, math.pi - a0, 13)
        for p, q in zip(A, A[1:]):
            poly(mat, [(x + math.cos(p) * r0, y0, z + math.sin(p) * r0), (x + math.cos(q) * r0, y0, z + math.sin(q) * r0),
                       (x + math.cos(q) * r1, y0 + h, z + math.sin(q) * r1), (x + math.cos(p) * r1, y0 + h, z + math.sin(p) * r1)])
    band('ashlar', -0.1, EAVE + 0.1, r)
    cyl('ashlar', (x, EAVE, z), 14.2 - EAVE, r, seg=16, cap=False)
    band('ashlar', -0.1, 0.95, r + 0.14)                                   # plinth
    band(TRIM, 0.8, 0.12, r + 0.18)
    band(TRIM, K.H - 0.05, 0.3, r + 0.16)                                  # belt
    band(TRIM, EAVE - 0.4, 0.4, r + 0.12, r + 0.3)                         # corbel ring at the cornice
    cyl(TRIM, (x, EAVE, z), 0.2, r + 0.32, seg=16)
    cyl(TRIM, (x, 13.6, z), 0.55, r + 0.08, r + 0.4, seg=16)               # the turret's own cornice
    # the roof: a little flare, then a long cone
    for (y0, h, r0, r1) in ((14.15, 0.5, r + 0.55, r + 0.25), (14.65, 3.2, r + 0.25, r * 0.72),
                            (17.85, 3.6, r * 0.72, r * 0.33), (21.45, 3.4, r * 0.33, 0.03)):
        cyl('slate', (x, y0, z), h, r0, r1, seg=16, cap=False)
    tube('iron', [(x, 24.7, z), (x, 27.0, z)], 0.04, 4)
    for y, s in ((25.3, 0.14), (26.0, 0.1)):
        sphere('iron', (x, y, z), s, 6)
    # windows on three storeys, across the half that faces the street
    for k, a_deg in enumerate((15, 62, 118, 165)):
        a = math.radians(a_deg)
        o = Vector((x + math.cos(a) * (r + 0.02), 0, z + math.sin(a) * (r + 0.02)))
        n = Vector((math.cos(a), 0, math.sin(a)))
        F = frame(o, Vector((-n.z, 0, n.x)), n)
        K.lancet(F, 0, 1.4, 0.7, 2.6, lit=k == 2)
        K.lancet(F, 0, K.UF + 0.9, 0.7, 2.4, lit=k == 1)
        K.lancet(F, 0, EAVE + 0.35, 0.5, 0.9, lit=False)
    K.collide(x - r, 0, zw, x + r, 14, z + r)


def tower():
    """The tower over the tower stair: a square shaft, a glazed belvedere (Gutman's observatory), and a steep
    concave mansard with lucarnes, iron cresting, a needle spire and a flag."""
    tx0, tx1, tz0, tz1 = 8, 15, -14, -7
    ty = 22.0
    T = K.T
    cx, cz = (tx0 + tx1) / 2, (tz0 + tz1) / 2
    for (a, b) in (((tx0, tz1), (tx1, tz1)), ((tx1, tz1), (tx1, tz0)), ((tx1, tz0), (tx0, tz0)), ((tx0, tz0), (tx0, tz1))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        r = (B - A).normalized(); n = K.outward(A, B, Vector((cx, 0, cz)))
        F = frame(A, r, n); L = (B - A).length
        lbox(F, 'ashlar', 0, L, 11.0, ty, -T / 2, T / 2)
        Fo = F @ Matrix.Translation((0, 0, T / 2))
        for u in (0.25, L - 0.25):  # corner pilasters
            lbox(Fo, 'ashlar', u - 0.3, u + 0.3, EAVE, ty - 0.3, 0, 0.14)
        lbox(Fo, TRIM, -0.1, L + 0.1, EAVE + 0.0, EAVE + 0.25, 0, 0.2)
        lbox(Fo, TRIM, 0, L, 16.6, 16.8, 0, 0.14)
        for v, h, lit in ((12.6, 3.0, False), (17.3, 3.4, True)):
            K.lancet(Fo, L / 2 - 0.6, v, 0.8, h, lit=lit)
            K.lancet(Fo, L / 2 + 0.6, v, 0.8, h)
            pair_hood(Fo, L / 2, v + h, w=0.8)
        bracket_cornice(Fo, -0.1, L + 0.1, ty + 0.05, depth=0.7)          # the belvedere's balcony line
        # the belvedere: glass all round between piers (Gutman's observatory)
        for k in range(4):
            u = 0.4 + k * (L - 0.8) / 4
            lbox(F, 'glass_clear', u + 0.25, u + (L - 0.8) / 4 - 0.25, ty, ty + 2.6, -0.02, 0.02)
            lbox(F, 'ashlar', u - 0.25, u + 0.25, ty, ty + 2.6, -T / 2, T / 2)
        lbox(F, 'ashlar', L - 0.65, L, ty, ty + 2.6, -T / 2, T / 2)
        lbox(F, 'ashlar', 0, L, ty + 2.6, ty + 3.0, -T / 2, T / 2 + 0.1)
        bracket_cornice(Fo, -0.1, L + 0.1, ty + 3.15, depth=0.5)
        for k in range(4):  # pointed heads over the belvedere's lights
            u = 0.4 + k * (L - 0.8) / 4 + (L - 0.8) / 8
            P = pointed((L - 0.8) / 8 - 0.25, ty + 2.0, 0.6, 3)
            tube(TRIM, [Fo @ Vector((u + a_, b_, 0.05)) for a_, b_ in P], 0.06, 4)
    wbox('ashlar', tx0, tx1, ty - 0.2, ty, tz0, tz1)  # observatory floor slab
    wbox('oak_panel', tx0 + 0.2, tx1 - 0.2, ty + 2.85, ty + 2.95, tz0 + 0.2, tz1 - 0.2)  # its ceiling
    # the mansard: steep and concave, then a flat top inside cresting
    m0 = ty + 3.2
    top = hip('slate', tx0 - 0.5, tx1 + 0.5, tz0 - 0.5, tz1 + 0.5,
              [(0, m0), (0.45, m0 + 1.9), (1.0, m0 + 4.4), (1.45, m0 + 6.4)], deck='roof')
    crest([(p.x, p.z) for p in top], m0 + 6.4, step=0.45, h=0.7, closed=True)
    for (c, r, n) in (((cx, m0, tz1 + 0.5), (1, 0, 0), (0, 0, 1)), ((cx, m0, tz0 - 0.5), (-1, 0, 0), (0, 0, -1)),
                      ((tx1 + 0.5, m0, cz), (0, 0, -1), (1, 0, 0)), ((tx0 - 0.5, m0, cz), (0, 0, 1), (-1, 0, 0))):
        c = Vector(c) - Vector(n) * 0.25
        dormer(c, r, n, w=1.6, h=2.2, lit=n[2] > 0)
        # a little iron balcony before each lucarne
        F = frame(c, r, n)
        lbox(F, TRIM, -1.0, 1.0, -0.05, 0.08, 0, 0.6)
        tube('iron', [F @ Vector((-1.0, 0.75, 0.6)), F @ Vector((1.0, 0.75, 0.6))], 0.02, 4)
        for u in np.linspace(-1.0, 1.0, 9):
            tube('iron', [F @ Vector((u, 0.08, 0.6)), F @ Vector((u, 0.75, 0.6))], 0.01, 3)
    # the needle spire on the corner toward the street, and the flag
    sx, sz = tx1 - 0.2, tz1 - 0.2
    cyl('slate', (sx, m0 + 5.0, sz), 5.5, 0.45, 0.02, seg=8, cap=False)
    tube('iron', [(sx, m0 + 10.3, sz), (sx, m0 + 12.0, sz)], 0.03, 4)
    tube('iron', [(cx, m0 + 6.4, cz), (cx, m0 + 11.0, cz)], 0.035, 4)
    poly('cablecar_red', [(cx, m0 + 10.9, cz), (cx + 1.6, m0 + 10.7, cz + 0.2), (cx + 1.6, m0 + 9.9, cz + 0.25), (cx, m0 + 10.1, cz)])
    # inside the observatory: a floor, a telescope on its tripod
    K.floor('parquet', tx0 + 0.3, tx1 - 0.3, tz0 + 0.3, tz1 - 0.3, y=ty)
    for k in range(3):
        a = k * 2 * math.pi / 3
        tube('brass', [(cx + math.cos(a) * 0.5, ty, cz - 1.5 + math.sin(a) * 0.5), (cx, ty + 1.3, cz - 1.5)], 0.02)
    tube('brass', [(cx, ty + 1.3, cz - 1.0), (cx, ty + 1.6, cz - 2.4)], 0.07, 12)
    K.collide(cx - 0.6, ty, cz - 2.2, cx + 0.6, ty + 1.6, cz - 0.9)
    for (a0, a1, b0, b1) in ((tx0, tx1, tz0, tz0 + 0.3), (tx0, tx1, tz1 - 0.3, tz1), (tx0, tx0 + 0.3, tz0, tz1), (tx1 - 0.3, tx1, tz0, tz1)):
        K.collide(a0, ty, b0, a1, ty + 3, b1)
    K.INTERACT.append(dict(id='down', label='Down the stair', pos=[tx0 + 1.2, ty + 1.0, tz1 - 1.2], r=1.2, to='tower_foot'))
    K.INTERACT.append(dict(id='telescope', label='The telescope', pos=[cx, ty + 1.4, cz - 1.6], r=1.6))
    K.LAMPS.append([cx, ty + 2.4, cz])


def porch():
    """The entrance porch / porte-cochere: corner piers, pointed arches on the three open sides (the drive runs
    through it along x), an entablature, and a balustrade with finials on top."""
    xa, za, zb = 3.05, 14.25, 20.0
    top = 5.1
    piers = [(s * 2.65, z) for s in (-1, 1) for z in (14.65, 19.6)]
    for x, z in piers:
        wbox('ashlar', x - 0.4, x + 0.4, -0.05, top, z - 0.4, z + 0.4)
        wbox(TRIM, x - 0.48, x + 0.48, -0.05, 0.5, z - 0.48, z + 0.48)
        wbox(TRIM, x - 0.46, x + 0.46, 2.45, 2.65, z - 0.46, z + 0.46)
        K.collide(x - 0.4, 0, z - 0.4, x + 0.4, top, z + 0.4)
    wbox('ashlar', -xa, xa, top, top + 0.75, za, zb)
    wbox(TRIM, -xa - 0.15, xa + 0.15, top + 0.75, top + 0.95, za, zb + 0.15)
    wbox('stone', -2.25, 2.25, top - 0.05, top, za, zb - 0.4)
    # the arches: front, and both sides
    arch(frame((0, 0, zb), (1, 0, 0), (0, 0, 1)), 2.25, 2.65, top, k=0.58)
    arch(frame((0, 0, zb - 0.8), (1, 0, 0), (0, 0, 1)), 2.25, 2.65, top, k=0.58, mould=False)
    for s in (-1, 1):
        F = frame((s * xa, 0, (za + 0.8 + zb - 0.8) / 2 + 0.4 - 0.4), (0, 0, -s), (s, 0, 0))
        arch(F, 2.075, 2.65, top, k=0.6)
        arch(F @ Matrix.Translation((0, 0, -0.8)), 2.075, 2.65, top, k=0.6, mould=False)
    # balustrade and finials
    y = top + 0.95
    for a, b in (((-xa, zb), (xa, zb)), ((-xa, za + 0.3), (-xa, zb)), ((xa, za + 0.3), (xa, zb))):
        A, B = Vector((a[0], y, a[1])), Vector((b[0], y, b[1]))
        tube(TRIM, [A + Vector((0, 0.8, 0)), B + Vector((0, 0.8, 0))], 0.08, 4)
        n = int((B - A).length / 0.32)
        for k in range(1, n):
            cyl(TRIM, A.lerp(B, k / n), 0.8, 0.07, 0.05, seg=4)
    for x, z in piers:
        if z > 15:
            K.pinnacle(x, y, z, h=2.0, r=0.26)
        else:
            cyl(TRIM, (x, y, z), 0.9, 0.2, seg=4)
    K.LAMPS.append([0, 4.2, (za + zb) / 2])
    sphere('lamp_glass', (0, 4.3, (za + zb) / 2), 0.18, 10)
    tube('iron', [(0, top - 0.05, (za + zb) / 2), (0, 4.45, (za + zb) / 2)], 0.02)
    wbox('stone', -xa, xa, -0.05, 0.1, za, zb)


def conservatory():
    """The glass conservatory at the east end: a stone base, glazed walls, pointed glass barrel roofs crossing
    under a ribbed dome with a lantern and spire."""
    x0, x1, z0, z1 = CONS
    xc, zc = (x0 + x1) / 2, (z0 + z1) / 2
    hx, hz = (x1 - x0) / 2, (z1 - z0) / 2
    y0 = 0.7
    sp = K.H                  # where the arches spring
    wbox('ashlar', x0, x1 + 0.15, -0.1, y0, z0 - 0.15, z1 + 0.15)
    wbox(TRIM, x0, x1 + 0.2, y0, y0 + 0.1, z0 - 0.2, z1 + 0.2)
    # glazed walls on the three open sides, iron mullions, stone corner piers
    for (a, b) in (((x0, z1), (x1, z1)), ((x1, z1), (x1, z0)), ((x1, z0), (x0, z0))):
        A, B = Vector((a[0], 0, a[1])), Vector((b[0], 0, b[1]))
        r = (B - A).normalized(); n = Vector((-r.z, 0, r.x)); L = (B - A).length
        F = frame(A, r, n)
        lbox(F, 'glass_cons', 0, L, y0 + 0.1, sp, -0.02, 0.02)
        for k in range(1, 6):
            u = k * L / 6
            lbox(F, 'iron', u - 0.04, u + 0.04, y0 + 0.1, sp, -0.05, 0.05)
            if k in (2, 4): lbox(F, 'glass_lit0', u - L / 6 + 0.08, u - 0.08, y0 + 0.5, sp - 0.6, 0.03, 0.04)
        lbox(F, 'iron', 0, L, 3.2, 3.28, -0.05, 0.05)
        lbox(F, TRIM, -0.1, L + 0.1, sp - 0.1, sp + 0.25, 0, 0.3)
    for (x, z) in ((x1, z0), (x1, z1), (x0 + 0.2, z0), (x0 + 0.2, z1)):
        wbox('ashlar', x - 0.25, x + 0.25, y0, sp + 0.25, z - 0.25, z + 0.25)
        K.pinnacle(x, sp + 0.25, z, h=1.6, r=0.2)
    # crossing pointed barrels; their ends are pointed glass gables with mullions
    P = pointed(hz, sp, 0.55, 5)
    for (u0, v0), (u1, v1) in zip(P, P[1:]):
        poly('glass_cons', [(x0, v0, zc + u0), (x1, v0, zc + u0), (x1, v1, zc + u1), (x0, v1, zc + u1)])
    poly('glass_cons', [(x1, v, zc + u) for u, v in P])
    tube('iron', [(x1 + 0.05, v, zc + u) for u, v in P], 0.08, 4)
    for xr in (x0 + 0.3, xc):
        tube('iron', [(xr, v + 0.03, zc + u) for u, v in P], 0.04, 4)
    for u in np.linspace(-hz + 0.8, hz - 0.8, 5):
        hgt = sp + math.sqrt(max(0, (0.55 * 2 * hz) ** 2 - (abs(u) + 0.55 * 2 * hz - hz) ** 2)) - 0.1
        tube('iron', [(x1 + 0.05, sp, zc + u), (x1 + 0.05, hgt, zc + u)], 0.03, 4)
    Q = pointed(hx, sp, 0.55, 5)
    for (u0, v0), (u1, v1) in zip(Q, Q[1:]):
        poly('glass_cons', [(xc + u0, v0, z0), (xc + u0, v0, z1), (xc + u1, v1, z1), (xc + u1, v1, z0)])
    for zz, s in ((z0, -1), (z1, 1)):
        poly('glass_cons', [(xc + u, v, zz) for u, v in Q])
        tube('iron', [(xc + u, v, zz + s * 0.05) for u, v in Q], 0.08, 4)
        for u in np.linspace(-hx + 0.8, hx - 0.8, 5):
            hgt = sp + math.sqrt(max(0, (0.55 * 2 * hx) ** 2 - (abs(u) + 0.55 * 2 * hx - hx) ** 2)) - 0.1
            tube('iron', [(xc + u, sp, zz + s * 0.05), (xc + u, hgt, zz + s * 0.05)], 0.03, 4)
    # the dome at the crossing, ribbed, with a lantern and a spire
    prof = [(2.3, 9.6), (2.35, 10.4), (2.05, 11.5), (1.45, 12.4), (0.7, 13.0), (0.25, 13.25)]
    for (r0, ya), (r1, yb) in zip(prof, prof[1:]):
        cyl('glass_cons', (xc, ya, zc), yb - ya, r0, r1, seg=12, cap=False)
    for k in range(8):
        a = k * math.pi / 4
        tube('iron', [(xc + math.cos(a) * (r + 0.04), y, zc + math.sin(a) * (r + 0.04)) for r, y in prof], 0.05, 4)
    cyl(TRIM, (xc, 9.4, zc), 0.3, 2.45, seg=12)
    cyl(TRIM, (xc, 13.2, zc), 0.7, 0.32, 0.28, seg=8)
    cyl('slate', (xc, 13.9, zc), 2.0, 0.34, 0.02, seg=8, cap=False)
    tube('iron', [(xc, 15.8, zc), (xc, 17.2, zc)], 0.03, 4)
    K.collide(x0, 0, z0 - 0.3, x1 + 0.3, sp, z1 + 0.3)


# --- the whole shell --------------------------------------------------------------------------------

def build(hb):
    """Build the house's outside round build_hopkins's interior (hb is that module)."""
    global K
    K = hb
    material(TRIM, '#b6ae9c', rough=0.7)
    material('glass_cons', '#5e6c76', rough=0.12, metal=0.55)
    before = {m: len(bm.faces) for m, bm in BM.items()}
    upper_storey()
    facade_detail()
    roofs()
    turret()
    tower()
    porch()
    conservatory()
    K.veranda(-15.225 - 0.3, -5.6, 1.2)
    tris = 0
    for m, bm in BM.items():
        bm.faces.ensure_lookup_table()
        for i in range(before.get(m, 0), len(bm.faces)):
            tris += len(bm.faces[i].verts) - 2
    print(f'hopkins_house: {tris} triangles')
    return tris
