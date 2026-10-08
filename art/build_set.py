# Builds the Burritt Alley / Bush Street set for The Black Bird.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_set.py -- [--render out.png]
#
# Writes art/set/burritt.blend and public/models/burritt.glb. Everything is
# modelled in the game's own coordinates (Y up, metres, the alley running along
# -Z from Bush Street at z = 8 to the fence at z = -22), then turned Z-up for
# Blender's exporter, which turns it back. The layout matches src/world/alley.js,
# which keeps the colliders; this file only provides what you see.
#
# San Francisco, 1895: brick and timber Italianate fronts with bay windows and
# bracketed cornices, cast-iron shopfronts, gas lamps, telegraph wires.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setkit import *  # noqa: F401,F403  (bpy, bmesh, math, np, Vector, Matrix and the kit)
# --- pieces ---------------------------------------------------------------------------

def gas_lamp(x, z, h=3.7):
    """San Francisco cast-iron gas lamp: plinth, fluted column, ladder bar, lantern, crown."""
    i = 'iron'
    cyl(i, (x, 0, z), 0.12, 0.2, 0.2, seg=8)
    cyl(i, (x, 0.12, z), 0.45, 0.17, 0.12, seg=8)
    cyl(i, (x, 0.57, z), 0.06, 0.14, 0.14, seg=8)
    for k in range(8):  # flutes
        a = k * math.pi / 4
        cyl(i, (x + math.cos(a) * 0.07, 0.63, z + math.sin(a) * 0.07), h - 1.35, 0.022, 0.016, seg=5)
    cyl(i, (x, 0.63, z), h - 1.35, 0.075, 0.055, seg=10)
    yb = h - 0.72
    cyl(i, (x, yb, z), 0.06, 0.09, 0.09, seg=10)
    tube(i, [(x - 0.42, yb + 0.03, z), (x + 0.42, yb + 0.03, z)], 0.018)  # the lamplighter's ladder bar
    for s in (-1, 1): sphere(i, (x + s * 0.43, yb + 0.03, z), 0.03, 8)
    cyl(i, (x, yb + 0.06, z), 0.12, 0.05, 0.11, seg=10)
    # lantern: four tapered panes, framed
    y0, y1 = yb + 0.18, yb + 0.62
    cyl('lamp_glass', (x, y0, z), y1 - y0, 0.13, 0.2, seg=4, cap=True)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        tube(i, [(x + math.cos(a) * 0.13, y0, z + math.sin(a) * 0.13), (x + math.cos(a) * 0.2, y1, z + math.sin(a) * 0.2)], 0.012)
    cyl(i, (x, y0 - 0.03, z), 0.04, 0.15, 0.15, seg=4)
    cyl(i, (x, y1, z), 0.05, 0.23, 0.23, seg=4)
    cyl(i, (x, y1 + 0.05, z), 0.16, 0.24, 0.05, seg=4)  # crown
    cyl(i, (x, y1 + 0.21, z), 0.06, 0.04, 0.02, seg=6)
    sphere(i, (x, y1 + 0.3, z), 0.035, 8)
    return Vector((x, (y0 + y1) / 2, z))


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
    """A stepped bracket tapering down from v_top."""
    for k, (a, b, d) in enumerate(((0.0, 0.1, 1.0), (0.1, 0.22, 0.7), (0.22, 0.34, 0.45), (0.34, 0.42, 0.25))):
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
    n = int((u1 - u0) / 0.85)
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


# --- the set ---------------------------------------------------------------------------

def build():
    make_materials()

    # building masses (behind the fronts): the alley pair, the rest of the near side, the far side
    masses = [
        (-14, -2.5, 12, -22, 8, 'brick_red'), (2.5, 14, 9, -22, 8, 'brick_brown'),
        (-28, -14, 10, -6, 8, 'clap_cream'), (14, 28, 11, -6, 8, 'brick_tan'),
        (-30, -18, 9, 22, 30, 'clap_grey'), (-18, -6, 13, 22, 30, 'brick_red'), (-6, 6, 10, 22, 30, 'clap_sage'),
        (6, 18, 12, 22, 30, 'brick_tan'), (18, 30, 8, 22, 30, 'clap_ochre'),
    ]
    for x0, x1, h, z0, z1, m in masses:
        wbox(m, x0, x1, 0, h, z0, z1)
        wbox('roof', x0 + 0.05, x1 - 0.05, h, h + 0.05, z0 + 0.05, z1 - 0.05)

    # --- Bush Street, near side (fronts face +z at z = 8) ---
    F = frame((0, 0, 8), (1, 0, 0), (0, 0, 1))
    front(F, -14, -2.5, 12, 'brick_red', 'trim_cream', 'J. HOLTZ & SON · HARDWARE', bays=(-11.2, -5.6))
    front(F, 2.5, 14, 9, 'brick_brown', 'trim_cream', 'CHOP HOUSE · OYSTERS', bays=(8.3,), floors=(4.6,),
          sign_mat='sign_board_red', lit=True)
    front(F, -28, -14, 10, 'clap_cream', 'trim_dark', 'DRUGS & CHEMICALS', bays=(-24.5, -17.5), floors=(4.6, 7.8))
    front(F, 14, 28, 11, 'brick_tan', 'trim_cream', 'THE GOLDEN EAGLE · SALOON', bays=(21,), floors=(4.6, 7.8),
          sign_mat='sign_board_red', lit=True)

    # --- Bush Street, far side (fronts face -z at z = 22) ---
    G = lambda x1: frame((x1, 0, 22), (-1, 0, 0), (0, 0, -1))
    far = [(-18, 9, 'clap_grey', 'trim_cream', 'PIONEER LIVERY STABLE', (3.5,), (4.6,)),
           (-6, 13, 'brick_red', 'trim_cream', 'THE BELVEDERE', (3.2, 8.8), (4.6, 7.8, 11.0)),
           (6, 10, 'clap_sage', 'trim_cream', 'FRENCH LAUNDRY', (6.0,), (4.6, 7.8)),
           (18, 12, 'brick_tan', 'trim_dark', 'HIBERNIA SAVINGS', (), (4.6, 7.8)),
           (30, 8, 'clap_ochre', 'trim_dark', 'TOBACCO & CIGARS', (6.0,), (4.6,))]
    for x1, h, wall, trim, sign, bays, floors in far:
        Fg = G(x1)
        front(Fg, 0, 12, h, wall, trim, sign, bays=bays, floors=floors,
              sign_mat='sign_board_red' if 'BELVEDERE' in sign else 'sign_board',
              lit=True if 'BELVEDERE' in sign else None)  # the saloon where Thursby drinks is open all night

    # --- the alley walls ---
    L = frame((-2.5, 0, 8), (0, 0, -1), (1, 0, 0))   # left wall faces +x; u runs from the street toward the fence
    R = frame((2.5, 0, -22), (0, 0, 1), (-1, 0, 0))  # right wall faces -x; u runs from the fence toward the street
    alley_wall(L, 0, 30, 12, (4.2, 7.8, 11.4),
               [(2.5, 4.4, 'win'), (6.0, 4.4, 'lit'), (9.5, 4.4, 'shut'), (21.0, 4.4, 'win'), (25.0, 4.4, 'shut'),
                (2.5, 8.0, 'win'), (6.0, 8.0, 'win'), (9.5, 8.0, 'win'), (17.0, 8.0, 'lit'), (21.0, 8.0, 'win'),
                (25.0, 8.0, 'win'), (14.5, 1.4, 'barred'), (24.5, 1.4, 'barred')], door=18.0)
    alley_wall(R, 0, 30, 9, (4.2, 7.8),
               [(9.0, 4.4, 'win'), (13.0, 4.4, 'shut'), (20.5, 4.4, 'lit'), (25.5, 4.4, 'win'), (13.0, 1.4, 'barred'),
                (24.0, 1.4, 'barred'), (9.0, 7.4, 'win'), (20.5, 7.4, 'win'), (25.5, 7.4, 'shut')], door=7.0)
    fire_escape(L, 10.5, 14.5, (4.0, 7.6, 11.2), 13.4)
    # a ghost of an old painted advertisement, high on the left wall
    text('paint_faded', 'BUSH STREET', L, 17.5, 10.2, 0.0, 0.7, extrude=0.002)
    text('paint_faded', 'STEAM LAUNDRY', L, 17.5, 9.3, 0.0, 0.7, extrude=0.002)
    drainpipe(-2.38, 2.0, 11.6, 1)
    drainpipe(2.38, -9.0, 8.6, -1)
    drainpipe(-2.38, -20.5, 11.6, 1)
    # telegraph wires across the alley and along the street
    for z, y in ((-2.0, 7.0), (-13.0, 6.6), (4.5, 7.6)):
        wire((-2.45, y, z), (2.45, y + 0.2, z), sag=0.35)
    for x0, x1 in ((-30, -10), (-10, 10), (10, 30)):
        wire((x0, 7.0, 9.4), (x1, 7.0, 9.4), sag=0.9)
        wire((x0, 7.3, 9.6), (x1, 7.3, 9.6), sag=0.9)
    for x in (-10, 10):  # telegraph poles at the kerb
        cyl('door_wood', (x, 0, 9.5), 7.8, 0.12, 0.09, seg=8)
        wbox('door_wood', x - 0.9, x + 0.9, 7.2, 7.32, 9.44, 9.56)
        for dx in (-0.7, -0.25, 0.25, 0.7):
            cyl('trim_cream', (x + dx, 7.32, 9.5), 0.1, 0.03, 0.02, seg=6)

    # lamps: Bush Street posts at the kerbs, the bracket lamp in the alley
    lamps = [gas_lamp(-3.6, 9.6), gas_lamp(13.0, 9.6), gas_lamp(-19.0, 9.6), gas_lamp(7.0, 20.6), gas_lamp(-13.0, 20.6),
             gas_lamp(24.0, 20.6)]
    lamps.append(bracket_lamp(-2.5, 3.35, -8, out=1))

    # alley clutter (positions match the colliders in alley.js)
    crate(-1.9, 0.45, -3.5, 0.9)
    crate(-1.95, 1.25, -3.4, 0.7, rot=0.3)
    crate(1.95, 0.4, -11.5, 0.8)
    barrel(2.0, -6.2); barrel(1.95, -7.1)
    ash_can(-2.0, -13.0)
    return lamps


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lamps = build()
    root = finish('Burritt')
    # empties marking lamp glass, for the game's halos and lights
    for k, p in enumerate(lamps):
        e = bpy.data.objects.new(f'Lamp_{k}', None)
        bpy.context.scene.collection.objects.link(e)
        e.location = p
        e.parent = root
    os.makedirs(os.path.join(ROOT, 'art', 'set'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'art', 'set', 'burritt.blend'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', 'burritt.glb'), export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True, export_image_format='JPEG',
                              export_jpeg_quality=85, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=7, export_cameras=False, export_lights=False)
    if RENDER: preview(RENDER)


def preview(path):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.world = bpy.data.worlds.new('W'); sc.world.color = (0.02, 0.025, 0.035)
    sun = bpy.data.objects.new('Moon', bpy.data.lights.new('Moon', 'SUN'))
    sun.data.energy = 0.6; sun.rotation_euler = (0.9, 0.2, -0.6)
    sc.collection.objects.link(sun)
    for k, (x, y, z) in enumerate([(-3.6, 3.4, 9.6), (-1.85, 3.0, -8), (13, 3.4, 9.6), (7, 3.4, 20.6)]):
        l = bpy.data.objects.new(f'L{k}', bpy.data.lights.new(f'L{k}', 'POINT'))
        l.data.energy = 300; l.data.color = (1, 0.7, 0.4)
        l.location = (x, -z, y)  # game -> Blender
        sc.collection.objects.link(l)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 26
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    shots = [('street', (6, 1.7, 17), (-3, 3.5, 6)), ('alley', (0.3, 1.7, 6), (0, 2.8, -10)),
             ('far', (-1, 1.7, 11), (2, 4, 22)), ('lamp', (-1.8, 1.8, 12.4), (-3.6, 2.8, 9.6))]
    for tag, eye, look in shots:
        e = Vector((eye[0], -eye[2], eye[1])); t = Vector((look[0], -look[2], look[1]))
        cam.location = e
        cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f'{path}_{tag}.png'
        bpy.ops.render.render(write_still=True)


main()
