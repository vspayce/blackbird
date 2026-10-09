# Builds Holmes's suite at the Palace Hotel for Chapter II, ransacked by Joel Cairo before Holmes came back.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_palace.py -- [--render prefix]
#
# Writes art/set/palace.blend, public/models/palace.glb and public/models/palace.json (colliders, lamps,
# named places, spawn). It borrows the Hopkins builder's furniture and finishes (that file only builds the
# mansion when run itself). Game coordinates, Y up, metres: the sitting room is x -5..5, z -6..6, the door to
# the corridor at the south (z = 6), the bay window over Market Street at the north (z = -6), the bedroom
# through a door in the east wall.
#
# The Palace is the grand hotel of the two (St. Mark: build_stmark.py, which borrows the hotel pieces here):
# crimson silk damask over mahogany, a coffered and frescoed ceiling, white marble, gilt. Outside the
# windows is a foggy morning: the fronts across the street are painted (view_* materials, which the game
# draws without its fog) on real blocks, so they shift as you walk past the glass.
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_hopkins as bh
from build_hopkins import *  # noqa: F401,F403  (the kit plus wall, lining, fireplace, sofa, rug, ...)

H2 = 4.4        # ceiling
PLACES = {}


def paper(x, z, rot, s=0.3):
    F = Matrix.Translation((x, 0.004, z)) @ Matrix.Rotation(rot, 4, 'Y')
    canvas('canvas', [F @ Vector(p) for p in ((-s / 2, 0, -s * 0.65), (s / 2, 0, -s * 0.65), (s / 2, 0, s * 0.65), (-s / 2, 0, s * 0.65))])


def book(x, y, z, rot, tilt=0.0, mat='rosewood_panel'):
    F = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, 'Y') @ Matrix.Rotation(tilt, 4, 'Z')
    lbox(F, mat, -0.12, 0.12, 0, 0.04, -0.17, 0.17)
    lbox(F, 'canvas', -0.11, 0.11, 0.004, 0.036, -0.165, 0.16)


def into_room(F, L, centre=Vector((0, 0, 0))):
    """Which side of a wall (as returned by wall()) faces the room: +1 along the frame's normal, else -1."""
    n = F.to_3x3() @ Vector((0, 0, 1))
    mid = F @ Vector((L / 2, 0, 0))
    return 1 if n.dot(centre - mid) > 0 else -1


# --- hotel finishes ------------------------------------------------------------------------------------

def damask_tex(name, ground, sheen, size=512):
    """Silk damask: an ogee medallion on a half-drop repeat, woven in the ground's own colour so it reads
    only as a change of sheen."""
    yy, xx = np.mgrid[0:size, 0:size] / size * 2
    ci = np.floor(xx).astype(int)
    fx, fy = xx % 1 - 0.5, (yy + 0.5 * ci) % 1 - 0.5
    ax = np.abs(fx)
    wdt = 0.3 * np.cos(fy * np.pi) ** 1.5 + 0.05 * np.cos(fy * 6 * np.pi)
    outline = (ax < wdt) & (ax > wdt - 0.035)
    palmette = (np.hypot(ax - 0.07 - 0.05 * (fy + 0.1), (fy + 0.05) * 1.4) < 0.07) | (np.hypot(ax, fy + 0.24) < 0.045) | \
               ((ax < 0.012) & (np.abs(fy + 0.05) < 0.22))
    m = outline | (palmette & (ax < wdt))
    weave = 0.96 + 0.04 * np.sin(np.mgrid[0:size, 0:size][1] * np.pi / 2)
    tone = (0.9 + 0.12 * noise(size, size, 60, 4)) * weave
    col = np.where(m[..., None], hexrgb(sheen), hexrgb(ground)) * tone[..., None]
    return image(name, col)


def stripe_tex(name, a, b, line, size=512):
    """Printed paper for a modest hotel: broad and narrow stripes, a pinstripe, a scatter of sprigs, faded."""
    yy, xx = np.mgrid[0:size, 0:size] / size * 4
    f = xx % 1
    col = np.where((f < 0.42)[..., None], hexrgb(a), hexrgb(b)) * np.ones((size, size, 1))
    pin = ((f > 0.44) & (f < 0.46)) | ((f > 0.96) & (f < 0.98))
    col[pin] = hexrgb(line)
    sx, sy = (f - 0.71) * 6, (yy * 2) % 1 - 0.5
    sprig = (np.hypot(sx, sy * 1.5) < 0.12) & (f > 0.5) & (f < 0.92)
    col[sprig] = hexrgb(line) * 1.2
    fade = 0.86 + 0.16 * noise(size, size, 80, 7) - 0.05 * noise(size, size, 6, 8)
    return image(name, col * fade[..., None])


def hotel_materials():
    t = damask_tex('damask_red', '#5c1416', '#7a2622'); material('damask_red', tex=t, rough=0.6, scale=0.9)
    t = stripe_tex('paper_stripe', '#7f8a6c', '#b8b08e', '#4e5a42'); material('paper_stripe', tex=t, rough=0.9, scale=0.6)
    t, n = panel_tex('pine_panel', '#6e4a2a'); material('pine_panel', tex=t, nrm=n, rough=0.4, scale=1.1)
    material('trim_mahog', '#3a1a10', rough=0.35)
    material('ceiling_plain', '#b8ae98', rough=0.95)
    material('lace', '#e8e2d4', rough=0.9)  # the game draws it sheer
    material('china', '#e8e4dc', rough=0.25)
    if 'carriage_black' not in bpy.data.materials:
        material('carriage_black', '#0c0c0e', rough=0.25, metal=0.2)
    if 'leather_black' not in bpy.data.materials:
        material('leather_black', '#16110d', 0.45)
    # gas globes in a room: frosted and dimmer than a street lamp's naked flame, or the gasolier blooms to a sun
    bpy.data.materials['lamp_glass'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 2.2


# --- doors ------------------------------------------------------------------------------------------------

def door_leaf(hinge, d, w, h, mat='walnut_panel', thick=0.05):
    """A four-panelled door leaf hinged at hinge (x, z) and lying along the direction d (x, z): its moulded
    panels on both faces, a brass knob and escutcheon each side. Collides."""
    F = Matrix.Translation((hinge[0], 0, hinge[1])) @ Matrix.Rotation(math.atan2(-d[1], d[0]), 4, 'Y')
    lbox(F, mat, 0.01, w - 0.01, 0.01, h - 0.01, -thick / 2, thick / 2)
    for s in (-1, 1):
        w0, w1 = sorted((s * thick / 2, s * (thick / 2 + 0.014)))
        for (a, b) in ((0.12, w / 2 - 0.05), (w / 2 + 0.05, w - 0.12)):
            for (v0, v1) in ((0.18, 1.0), (1.2, h - 0.18)):
                lbox(F, mat, a, b, v0, v1, w0, w1)
        k = F @ Vector((w - 0.08, 1.0, s * (thick / 2 + 0.045)))
        sphere('brass', k, 0.03, 8)
        lbox(F, 'brass', w - 0.11, w - 0.05, 0.9, 1.1, *sorted((s * thick / 2, s * (thick / 2 + 0.008))))
    cyl('brass', F @ Vector((w - 0.08, 1.0, -thick / 2 - 0.045)), thick + 0.09, 0.008, seg=6,
        axis=F.to_3x3() @ Vector((0, 0, 1)))
    collide_local(F, 0, w, 0, h, -thick / 2 - 0.05, thick / 2 + 0.05)


# --- the corridor outside the suite door -----------------------------------------------------------------

def corridor(x0, x1, z_wall, depth, h, door_x, paper_mat, wains, trim, carpet, head):
    """A stretch of hotel corridor behind the suite's door (the wall at z_wall, the corridor beyond it in +z),
    so a camera behind Holmes at the door sees a corridor, not the void: walls dressed like the room's, the
    door to the suite opposite shut, a runner, a gas bracket. Closed at both ends."""
    zf, zb = z_wall + T / 2, z_wall + T / 2 + depth
    floor('parquet', x0, x1, z_wall, zb)
    wbox('ceiling_plain', x0, x1, h, h + 0.1, z_wall, zb + T / 2)
    wbox(carpet, x0 + 0.3, x1 - 0.3, 0.0, 0.008, zf + 0.35, zb - 0.35)
    wbox('gilt_frame', x0 + 0.3, x1 - 0.3, 0.0, 0.01, zf + 0.33, zf + 0.37)
    wbox('gilt_frame', x0 + 0.3, x1 - 0.3, 0.0, 0.01, zb - 0.37, zb - 0.33)
    opp = [(x1 - door_x + 1.0, 1.2, 0, 2.6)]
    F, L = wall((x1, zb + T / 2), (x0, zb + T / 2), 0, h, opp, mat='plaster')
    lining(F, L, into_room(F, L, Vector((door_x, 0, z_wall))), opp, h, wains=wains, upper=paper_mat, trim=trim,
           frieze=trim, head=head)
    door_leaf((door_x - 1.0 + 0.6, zb + 0.05), (-1, 0), 1.2, 2.6)  # the suite across the corridor, shut
    lbox(Matrix.Translation((door_x - 1.0, 1.75, zb)), 'brass', -0.09, 0.09, -0.05, 0.05, 0.008, 0.019)  # its number
    for xe, a, b in ((x0, (x0, zb), (x0, z_wall)), (x1, (x1, z_wall), (x1, zb))):
        F, L = wall(a, b, 0, h, [], mat='plaster')
        lining(F, L, into_room(F, L, Vector(((x0 + x1) / 2, 0, (zf + zb) / 2))), [], h, wains=wains, upper=paper_mat,
               trim=trim, frieze=trim)
    s = frame((x0 + 1.2, 0, zb), (1, 0, 0), (0, 0, -1))
    sconce(s, 0.0, 1.9)
    LAMPS.append([round(x0 + 1.2, 3), 2.1, round(zb - 0.35, 3)])


# --- the street outside ------------------------------------------------------------------------------------

def paint_fronts(name, style, size=1024):
    """Eight fronts across the street in a 4 x 2 atlas, painted as they look on a foggy morning. Returns
    (cell width, cell height) in metres and each front's height. 'market': tall stone and brick commercial
    blocks (Market Street); 'ellis': three-storey wooden Italianates with bay windows (Ellis Street)."""
    CW, CH = (14.0, 28.0) if style == 'market' else (10.0, 20.0)
    cw, ch = size // 4, size // 2
    ppm = cw / CW
    rng = np.random.default_rng(7 if style == 'market' else 8)
    img = np.zeros((size, size, 3), np.float32)
    heights = []
    fog = hexrgb('#a3abb2')

    def R(c, x0, x1, y0, y1, col):
        a, b = int(round(x0 * ppm)), int(round(x1 * ppm))
        r0, r1 = ch - int(round(y1 * ppm)), ch - int(round(y0 * ppm))
        c[max(0, r0):max(0, r1), max(0, a):max(0, b)] = col

    def sash(c, x, y, w, h, trim):
        R(c, x - 0.1, x + w + 0.1, y - 0.12, y + h + 0.1, trim)                  # surround
        R(c, x - 0.2, x + w + 0.2, y - 0.2, y - 0.1, trim * 0.9)                 # sill
        a, b = int(round(x * ppm)), int(round((x + w) * ppm))
        r0, r1 = ch - int(round((y + h) * ppm)), ch - int(round(y * ppm))
        g = np.linspace(0.55, 0.22, max(1, r1 - r0))[:, None, None]             # the sky in the glass
        c[r0:r1, a:b] = hexrgb('#5d6a78') * g / 0.4
        pick = rng.random()
        if pick < 0.3:   # a blind pulled half down
            R(c, x, x + w, y + h * rng.uniform(0.4, 0.75), y + h, hexrgb('#c9bd9c'))
        elif pick < 0.38:  # lamplight still on in an office
            R(c, x, x + w, y, y + h, hexrgb('#c89a58'))
        R(c, x, x + w, y + h / 2 - 0.03, y + h / 2 + 0.03, trim * 0.8)          # meeting rail
        R(c, x + w / 2 - 0.02, x + w / 2 + 0.02, y, y + h, trim * 0.8)
        R(c, x - 0.1, x + w + 0.1, y - 0.12, y - 0.07, trim * 0.6)              # the shadow under the sill

    for k in range(8):
        c = np.zeros((ch, cw, 3), np.float32)
        if style == 'market':
            h = float(rng.choice([17.5, 20.5, 24.0, 21.0]))
            wall = hexrgb(['#a89878', '#7a4a36', '#c2b69a', '#8a8a84', '#5e3b2c', '#9a7b5a', '#b0a488', '#6e4a3a'][k])
            trim = hexrgb(['#d8cdb0', '#c8bea4', '#8a7a62', '#d8cdb0'][k % 4])
            c[:] = wall
            if k in (1, 4, 7):  # brick: coursing
                c[(np.arange(ch) % 3 == 0)] *= 0.86
            R(c, 0, CW, 0, 4.6, hexrgb('#2a2622'))                             # shopfronts
            nb = 3
            for i in range(nb):
                a = 0.4 + i * (CW - 0.8) / nb
                R(c, a + 0.25, a + (CW - 0.8) / nb - 0.25, 0.5, 3.4, hexrgb('#b08850') if rng.random() < 0.6 else hexrgb('#46505a'))
                R(c, a, a + 0.25, 0, 4.6, trim * 0.7)                          # cast-iron piers
            R(c, 0, CW, 3.6, 4.4, hexrgb(['#1d2a22', '#3d1612', '#2a2a2a'][k % 3]))  # sign band
            for i in range(10):                                                # gilt lettering, too far to read
                R(c, 2 + i * 1.0, 2.6 + i * 1.0, 3.8, 4.2, hexrgb('#b8944a'))
            if k % 2:  # a striped awning let down
                for i in range(int(CW / 0.5)):
                    R(c, i * 0.5, i * 0.5 + 0.25, 3.0, 3.6, hexrgb('#5a2a22'))
                    R(c, i * 0.5 + 0.25, i * 0.5 + 0.5, 3.0, 3.6, hexrgb('#b8ac90'))
            R(c, 0, CW, 4.4, 4.9, trim)
            fl = 5.4
            while fl + 2.4 < h - 1.5:
                n = 5
                for i in range(n):
                    sash(c, 0.9 + i * (CW - 1.8) / n + 0.35, fl, 1.1, 2.2, trim)
                R(c, 0, CW, fl - 0.45, fl - 0.3, trim)                          # belt course
                fl += 3.6
            if k % 3 == 0:  # a sign painted on the brick
                R(c, 1.5, CW - 1.5, h - 4.2, h - 2.6, hexrgb('#d8d0b8') * 0.85)
                for i in range(8):
                    R(c, 2.2 + i * 1.2, 2.9 + i * 1.2, h - 3.8, h - 3.0, hexrgb('#3a2a20'))
            R(c, 0, CW, h - 1.3, h, trim)                                       # cornice
            for i in range(int(CW / 0.6)):
                R(c, i * 0.6 + 0.2, i * 0.6 + 0.35, h - 1.3, h - 0.9, trim * 0.55)  # brackets
            R(c, 0, CW, h - 0.25, h, trim * 1.05)
        else:
            h = float(rng.choice([10.5, 11.5, 12.5, 13.0]))
            wall = hexrgb(['#c9b98f', '#9aa38a', '#b8b0a0', '#a8834a', '#8a9098', '#c4a88a', '#7d8a6c', '#b4a27e'][k])
            trim = hexrgb(['#e6dcc4', '#d8cdb0', '#f0e8d4', '#5a4a3a'][k % 4])
            c[:] = wall
            c[(np.arange(ch) % 4 == 0)] *= 0.82                                # lap siding
            shop = k % 3 == 0
            if shop:
                R(c, 0, CW, 0, 3.8, hexrgb('#2a2622'))
                R(c, 0.4, CW - 0.4, 0.5, 3.0, hexrgb('#a88850'))
                R(c, 0, CW, 3.0, 3.8, hexrgb('#1d2a22'))
                for i in range(6):
                    R(c, 1.5 + i * 1.1, 2.1 + i * 1.1, 3.2, 3.6, hexrgb('#b8944a'))
            else:  # a stoop up to a recessed door
                R(c, 0.6, 2.2, 1.2, 3.8, trim)
                R(c, 0.8, 2.0, 1.2, 3.5, hexrgb('#3a2618'))
                for i in range(5):
                    R(c, 0.4 - i * 0.05, 2.4 + i * 0.05, i * 0.24, i * 0.24 + 0.24, hexrgb('#8a8478') * (0.9 + 0.03 * i))
                R(c, 0, CW, 0, 1.0, wall * 0.7)                                # the basement
            R(c, 0, CW, 3.8, 4.1, trim)
            # the bay: a lighter projecting band with its three sashes, shaded at its edges
            bx0, bx1 = (4.0, 8.6) if not shop else (2.6, 7.4)
            R(c, bx0 - 0.15, bx0, 4.1, h - 1.0, wall * 0.62)
            R(c, bx1, bx1 + 0.15, 4.1, h - 1.0, wall * 0.75)
            R(c, bx0, bx1, 4.1, h - 1.0, wall * 1.08)
            fl = 4.7
            while fl + 2.0 < h - 1.2:
                for i in range(3):
                    sash(c, bx0 + 0.25 + i * (bx1 - bx0 - 0.5) / 3 + 0.1, fl, (bx1 - bx0 - 0.5) / 3 - 0.2, 1.9, trim)
                if not shop:
                    sash(c, 1.0, fl, 0.9, 1.9, trim)
                R(c, bx0, bx1, fl - 0.5, fl - 0.35, trim)
                fl += 3.1
            R(c, 0, CW, h - 1.0, h, trim)                                       # bracketed cornice
            for i in range(int(CW / 0.7)):
                R(c, i * 0.7 + 0.25, i * 0.7 + 0.4, h - 1.0, h - 0.5, trim * 0.55)
            R(c, 0, 0.25, 0, h, trim * 0.95); R(c, CW - 0.25, CW, 0, h, trim * 0.95)  # corner boards
        # weather, then the fog between us and it: more of it higher up, where it hangs
        yy = np.linspace(1, 0, ch)[:, None, None] * CH / max(h, 1)
        c *= (0.86 + 0.18 * noise(ch, cw, 9, k)[..., None] - 0.06 * noise(ch, cw, 2, k + 9)[..., None])
        hz = np.clip(0.3 + 0.18 * yy, 0, 0.7)
        c = c * (1 - hz) + fog * hz
        r, q = k // 4, k % 4
        img[r * ch:(r + 1) * ch, q * cw:(q + 1) * cw] = c
        heights.append(h)
    return image(name, img * 0.88), (CW, CH), heights


def paint_sky(name, w=512, h=256):
    """Fog lying over the city: a pale haze, brighter low down, with the ghost of a skyline in it."""
    yy, xx = np.mgrid[0:h, 0:w]
    t = yy / h  # 0 at the top
    col = hexrgb('#7d8790') * (1 - t[..., None]) + hexrgb('#b4bcc2') * t[..., None]
    rng = np.random.default_rng(5)
    x = 0
    while x < w:  # rooftops and a spire or two, barely there
        bw, bh = rng.integers(14, 40), rng.integers(10, 50)
        col[h - bh:, x:x + bw] = col[h - bh:, x:x + bw] * 0.9 + hexrgb('#8a939b') * 0.1
        if rng.random() < 0.08:
            col[h - bh - 40:h - bh, x + bw // 2 - 2:x + bw // 2 + 2] *= 0.92
        x += bw
    col *= (0.96 + 0.06 * noise(h, w, 40, 3))[..., None]
    return image(name, col)


def paint_street(name, kind, w=256, h=512):
    """The street from our kerb (bottom) to theirs (top): flags, granite kerbs, the roadway, rails if any."""
    yy, xx = np.mgrid[0:h, 0:w]
    v = 1 - yy / h
    col = np.zeros((h, w, 3), np.float32) + hexrgb('#4a4c4e')
    col *= (0.85 + 0.25 * noise(h, w, 3, 2))[..., None]
    for a, b in ((0.0, 0.12), (0.88, 1.0)):
        side = (v >= a) & (v < b)
        col[side] = (hexrgb('#6a6862') * (0.9 + 0.1 * ((xx // 16 + yy // 16) % 2))[..., None])[side]
    for e in (0.12, 0.88):
        col[np.abs(v - e) < 0.006] = hexrgb('#8a8a86')
    if kind == 'market':  # the cable-car slots and rails up the middle of Market Street
        for c in (0.36, 0.42, 0.58, 0.64):
            col[np.abs(v - c) < 0.0025] = hexrgb('#2a2a2a')
    col[(np.abs(v - 0.5) < 0.2) & (noise(h, w, 20, 5) > 0.72)] *= 0.8  # wet patches
    return image(name, col)


def street_view(style, z_face, z_wall, x0, x1, y_street, seed=1):
    """The fronts across the street (their faces at about z_face, looking +z at us), the street down to our
    own wall at z_wall, and the fog behind. Painted, lit by the material itself, no game fog."""
    t, (CW, CH), heights = paint_fronts('view_fronts', style)
    material('view_fronts', '#000000', rough=1.0, emit_tex=t, emit_strength=1.0, scale=None)
    material('view_sky', '#000000', rough=1.0, emit_tex=paint_sky('view_sky'), emit_strength=1.0, scale=None)
    material('view_street', '#000000', rough=1.0, emit_tex=paint_street('view_street', style), emit_strength=0.8, scale=None)
    material('view_roof', '#000000', rough=1.0, emit='#5a6066', emit_strength=1.0, scale=None)
    rng = random.Random(seed)
    x, i = x0, 0
    while x < x1:
        k = (i * 3 + seed) % 8
        w = CW * rng.uniform(0.72, 1.0)
        h = heights[k]
        zf = z_face - rng.choice((0.0, 0.0, 0.9, 1.8))
        q, r = k % 4, k // 4
        u0, u1 = q / 4, q / 4 + w / CW / 4
        vb = 1 - (r + 1) / 2
        vt = vb + h / CH / 2
        y0, y1 = y_street, y_street + h
        canvas('view_fronts', [(x, y0, zf), (x + w, y0, zf), (x + w, y1, zf), (x, y1, zf)],
               uv=((u0, vb), (u1, vb), (u1, vt), (u0, vt)))
        for xs in (x, x + w):  # the flanks, where a neighbour is set back
            canvas('view_fronts', [(xs, y0, zf - 12), (xs, y0, zf), (xs, y1, zf), (xs, y1, zf - 12)],
                   uv=((u0 + 0.001, vb), (u0 + 0.004, vb), (u0 + 0.004, vt), (u0 + 0.001, vt)))
        canvas('view_roof', [(x, y1, zf), (x + w, y1, zf), (x + w, y1, zf - 12), (x, y1, zf - 12)])
        x += w; i += 1
    canvas('view_street', [(x0, y_street, z_wall), (x1, y_street, z_wall), (x1, y_street, z_face), (x0, y_street, z_face)])
    zs = z_face - 70
    canvas('view_sky', [(x0 - 120, y_street, zs), (x1 + 120, y_street, zs), (x1 + 120, y_street + 110, zs),
                        (x0 - 120, y_street + 110, zs)])
    # lamp posts along the far kerb: the gas long out, iron in the fog
    for k in range(4):
        gas_lamp(x0 + 8 + k * (x1 - x0 - 16) / 3, z_face + 3.2, y=y_street)


# --- the Palace suite ------------------------------------------------------------------------------------

PAL = dict(wains='rosewood_panel', upper='damask_red', trim='trim_mahog', frieze='gilt_frame', head='cornice')


def build_suite():
    # floor, ceiling, and the walls with their openings: (t from the wall's start, width, bottom, top)
    floor('parquet', -5, 5, -6, 6)
    coffered_ceiling(-5, 5, -6, 6, H2, beam='trim_cream', field='fresco_louis', step=1.7)
    ceiling_bosses(-5, 5, -6, 6, H2, step=1.7)
    cyl('gilt_frame', (0, H2 - 0.42, 0), 0.08, 0.45, 0.3, seg=20)   # the ceiling rose the gasolier hangs from
    spec = {
        'south': ((5, 6), (-5, 6), [(5, 1.6, 0, 3.0)]),                                    # the corridor door
        'east': ((5, -6), (5, 6), [(8.5, 1.8, 0, 3.0)]),                                   # the bedroom door
        'west': ((-5, 6), (-5, -6), []),
        'north': ((-5, -6), (5, -6), [(1.3, 1.1, 0.8, 3.2), (5, 4.0, 0, H2 - 0.6), (8.7, 1.1, 0.8, 3.2)]),  # windows, the bay
    }
    for key, (a, b, ops) in spec.items():
        F, L = wall(a, b, 0, H2, ops, mat='plaster')
        side = into_room(F, L)
        lining(F, L, side, ops, H2, curtains='velvet_red' if key == 'north' else None, **PAL)
        if key == 'south':  # its corridor face
            lining(F, L, -side, ops, 3.8, **PAL)
        for t, w, ob, ot in ops:
            if ob > 0.3: window_glass(F, t, w, ob, ot)
    # the bay itself: a centre window and two angled sides, under a lowered soffit
    bay_out = 1.2
    pts = [(-2.0, -6), (-1.3, -6 - bay_out), (1.3, -6 - bay_out), (2.0, -6)]
    for a, b in zip(pts, pts[1:]):
        L = (Vector((b[0], 0, b[1])) - Vector((a[0], 0, a[1]))).length
        op = [(L / 2, L - 0.35, 0.7, 3.3)]
        F, _ = wall(a, b, 0, H2 - 0.6, op, mat='plaster')
        window_glass(F, L / 2, L - 0.35, 0.7, 3.3)
        lining(F, L, into_room(F, L), op, H2 - 0.6, curtains='velvet_red', **PAL)
    floor('parquet', -2.0, 2.0, -6 - bay_out, -6)
    wbox('trim_cream', -2.0, 2.0, H2 - 0.6, H2, -6 - bay_out - 0.1, -6)
    # a window seat along the bay, buttoned velvet on a mahogany box
    wbox('trim_mahog', -1.1, 1.1, 0, 0.36, -7.0, -6.62)
    wbox('velvet_red', -1.08, 1.08, 0.36, 0.46, -7.0, -6.6)
    for k in range(3):
        wbox('velvet_red', -0.9 + k * 0.62, -0.42 + k * 0.62, 0.46, 0.78, -7.02, -6.9)   # bolsters against the sill
    collide(-1.1, 0, -7.05, 1.1, 0.5, -6.6)
    # the corridor outside the door
    corridor(-5.0, 5.0, 6.0, 2.6, 3.8, 0.0, 'damask_red', 'rosewood_panel', 'trim_mahog', 'velvet_red', 'cornice')
    door_leaf((-0.75, 5.7), (-0.985, -0.17), 1.5, 2.95)        # the suite door, standing open
    # the bedroom beyond its door: turned over, seen through the door but not entered
    PLACES['door'] = [0, 0, 5.2]
    PLACES['bedroom'] = [4.2, 1.4, 2.5]
    floor('parquet', 5.175, 9.5, -1.2, 6)
    wbox('ceiling_plain', 5.175, 9.7, H2, H2 + 0.1, -1.2, 6)
    for a, b, ops in (((9.6, -1.2), (9.6, 6), [(3.6, 1.4, 0.8, 3.2)]), ((5.175, -1.1), (9.6, -1.1), []),
                      ((9.6, 5.9), (5.175, 5.9), [])):
        F, L = wall(a, b, 0, H2, ops, mat='plaster', solid=False)
        lining(F, L, into_room(F, L, Vector((7.4, 0, 2.4))), ops, H2, curtains='velvet_red' if ops else None, **PAL)
        for t, w, ob, ot in ops:
            window_glass(F, t, w, ob, ot)
            canvas('view_sky', [F @ Vector(p) for p in ((t - w, ob - 0.5, -0.6), (t + w, ob - 0.5, -0.6),
                                                        (t + w, ot + 0.5, -0.6), (t - w, ot + 0.5, -0.6))])  # the light well
    door_leaf((5.22, 3.35), (0.94, -0.34), 1.7, 2.95)          # the bedroom door, ajar
    four_poster(7.6, 4.0, -math.pi / 2)
    cabinet(9.2, 0.3, -math.pi / 2, w=1.2)
    for s in (-1, 1):  # the wardrobe's doors left open
        door_leaf((8.95, 0.3 + s * 0.6), (-0.5, s * 0.87), 0.58, 1.9, mat='rosewood_panel', thick=0.03)
    for (x, z) in ((6.5, 1.0), (7.2, 0.4), (8.4, 1.8)):  # clothes turned out on the floor
        wbox('velvet_green', x - 0.3, x + 0.3, 0, 0.05, z - 0.2, z + 0.25)
    pedestal_table(8.9, 5.3, lamp=True, r=0.3)
    LAMPS.append([8.9, 1.2, 5.3])
    collide(5.2, 0, -1.2, 9.7, H2, 6)


def furnish_suite():
    # the fireplace on the west wall, sconces either side of it, a sofa and wingbacks round it, a rug
    fireplace(frame((-5 + T / 2, 0, 0), (0, 0, 1), (1, 0, 0)), 0.0, mat='marble_white', w=1.9)
    for z in (-1.75, 1.75):
        sconce(frame((-5 + T / 2 + 0.03, 0, z), (0, 0, 1), (1, 0, 0)), 0.0, 2.1)
        LAMPS.append([-4.0, 2.3, z])  # out from the wall, or the light is a hot spot on the paper
    rug(-3.6, 1.4, -2.6, 2.6, 0)
    sofa(-0.6, 0, -math.pi / 2, 'velvet_red', 2.2)
    for (x, z) in ((-3.0, 2.0), (-3.0, -2.0)):
        wingback(x, z, facing(x, z, -4.6, 0), 'velvet_green')
    pedestal_table(-1.9, 0, lamp=True, r=0.35)
    # the sofa's seat cushion slit open, stuffing on the rug
    for k in range(9):
        sphere('canvas', (-0.5 + (k % 3) * 0.12, 0.52 + (k // 3) * 0.03, -0.4 + (k % 4) * 0.25), 0.05 + (k % 2) * 0.02, 6)
    PLACES['cushion'] = [-0.6, 0.6, 0]
    # the writing desk by the east wall: drawers pulled out, papers everywhere, its lamp still burning
    F = Matrix.Translation((3.6, 0, -3.8)) @ Matrix.Rotation(-math.pi / 2, 4, 'Y')
    lbox(F, 'walnut_panel', -0.75, 0.75, 0.72, 0.78, -0.35, 0.35)
    lbox(F, 'velvet_green', -0.6, 0.6, 0.78, 0.785, -0.28, 0.25)    # the leather writing surface
    for s in (-1, 1):  # the pedestals of drawers either side of the kneehole
        lbox(F, 'walnut_panel', min(s * 0.4, s * 0.75), max(s * 0.4, s * 0.75), 0, 0.72, -0.33, 0.33)
    for k, out in enumerate((0.25, 0.4, 0.15)):  # drawers hanging open
        lbox(F, 'walnut_panel', 0.42, 0.73, 0.12 + k * 0.2, 0.3 + k * 0.2, 0.33, 0.33 + out)
        sphere('brass', F @ Vector((0.575, 0.21 + k * 0.2, 0.35 + out)), 0.02, 6)
    lbox(F, 'walnut_panel', -0.73, -0.42, 0.12, 0.3, 0.33, 0.6)
    cyl('brass', F @ Vector((-0.55, 0.785, -0.2)), 0.25, 0.06, 0.03, seg=10)  # a student lamp
    sphere('lamp_glass', F @ Vector((-0.55, 1.1, -0.2)), 0.08, 10)
    p = F @ Vector((-0.55, 1.15, -0.2)); LAMPS.append([round(p.x, 3), 1.15, round(p.z, 3)])
    collide(3.2, 0, -4.6, 4.1, 0.8, -3.0)
    chair(2.8, -3.8, math.pi / 2 + 0.9, 'velvet_red')  # pushed back hard
    for k in range(14):
        paper(2.0 + (k * 0.37) % 2.2, -4.8 + (k * 0.61) % 2.6, k * 0.7)
    PLACES['desk'] = [3.6, 0.9, -3.8]
    # books pulled from the case by the door and dropped
    bookcase_run(frame((-5 + T / 2, 0, 5.8), (0, 0, -1), (1, 0, 0)), 0.2, 1.8, h=2.4)
    for k in range(7):
        book(-4.1 + (k % 3) * 0.35, 0.0, 4.6 - k * 0.25, k * 0.9, tilt=(k % 2) * 0.3)
    PLACES['books'] = [-4.0, 0.5, 4.4]
    # a chair knocked over
    F = Matrix.Translation((1.8, 0.25, 2.6)) @ Matrix.Rotation(1.57, 4, 'Z') @ Matrix.Rotation(0.6, 4, 'Y')
    lbox(F, 'velvet_red', -0.25, 0.25, -0.05, 0.05, -0.25, 0.25)
    lbox(F, 'velvet_red', -0.25, 0.25, 0.05, 0.55, 0.2, 0.27)
    collide(1.4, 0, 2.2, 2.3, 0.6, 3.0)
    # the side table by the door with the salver: Cairo's card on it
    table(2.0, 5.3, 0.9, 0.5, h=0.85, mat='walnut_panel')
    cyl('brass', (2.0, 0.85, 5.3), 0.02, 0.18, seg=16)
    paper(2.0, 5.3, 0.3, 0.1)
    PLACES['salver'] = [2.0, 1.0, 5.3]
    sconce(frame((2.0, 0, 6 - T / 2 - 0.03), (-1, 0, 0), (0, 0, -1)), 0.0, 2.0)   # lighting the salver
    LAMPS.append([2.0, 2.25, 5.45])
    # a gilt console and pier glass on the east wall, between the desk and the bedroom door
    F = frame((5 - T / 2, 0, -0.6), (0, 0, 1), (-1, 0, 0))
    lbox(F, 'gilt_frame', -0.6, 0.6, 0.78, 0.84, 0.0, 0.42)
    lbox(F, 'marble_white', -0.62, 0.62, 0.84, 0.88, 0.0, 0.44)
    for u in (-0.52, 0.52):
        lbox(F, 'gilt_frame', u - 0.03, u + 0.03, 0, 0.78, 0.33, 0.39)
    lbox(F, 'gilt_frame', -0.5, 0.5, 1.0, 3.4, 0.0, 0.05)
    lbox(F, 'mirror', -0.42, 0.42, 1.08, 3.3, 0.05, 0.06)
    collide_local(F, -0.62, 0.62, 0, 0.9, 0, 0.44)
    # a long-case clock, a fern, pictures, a gasolier
    longcase_clock(-4.55, -4.8, math.pi / 2)
    fern(4.4, -5.2, 1.0)
    gasolier(0, H2 - 0.42, 0, drop=1.0)
    frame_painting(frame((5 - T / 2, 0, -6), (0, 0, 1), (-1, 0, 0)), 2.6, 1.6, 1.3, 1.0, 4)
    frame_painting(frame((-5 + T / 2, 0, 6), (0, 0, -1), (1, 0, 0)), 9.0, 1.5, 1.6, 1.2, 12)
    PLACES['window'] = [0, 1.6, -6.4]
    # Market Street below the bay: the far side is about 36 m off; the suite is on the third floor
    street_view('market', -42.0, -7.4, -40.0, 40.0, -10.0, seed=1)
    from build_city import hack
    hack(-6.0, -38.0, math.pi / 2, y=-10.0)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hopkins_materials()
    interior_materials()
    hotel_materials()
    build_suite()
    furnish_suite()
    root = finish('Palace')
    for k, p in enumerate(bh.LAMPS):
        e = bpy.data.objects.new(f'Lamp_{k}', None)
        bpy.context.scene.collection.objects.link(e)
        e.location = p; e.parent = root
    os.makedirs(os.path.join(ROOT, 'art', 'set'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'art', 'set', 'palace.blend'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', 'palace.glb'), export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True, export_image_format='JPEG',
                              export_jpeg_quality=85, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=7, export_cameras=False, export_lights=False)
    with open(os.path.join(ROOT, 'public', 'models', 'palace.json'), 'w') as f:
        json.dump(dict(colliders=bh.COLLIDERS, lamps=[[round(v, 3) for v in p] for p in bh.LAMPS], places=PLACES,
                       spawn=dict(pos=[0, 0, 5.0], yaw=math.pi)), f, separators=(',', ':'))
    if RENDER: preview(RENDER)


def preview(path):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.world = bpy.data.worlds.new('W'); sc.world.color = (0.03, 0.035, 0.05)
    for k, (x, y, z) in enumerate(bh.LAMPS):
        l = bpy.data.objects.new(f'L{k}', bpy.data.lights.new(f'L{k}', 'POINT'))
        l.data.energy = 250; l.data.color = (1, 0.72, 0.42); l.location = (x, -z, y)
        sc.collection.objects.link(l)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 20
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    for tag, eye, look in (('room', (0.5, 1.7, 5.4), (-0.5, 1.2, -4)), ('desk', (-2, 1.7, 1), (3.6, 0.8, -4))):
        e = Vector((eye[0], -eye[2], eye[1])); t = Vector((look[0], -look[2], look[1]))
        cam.location = e; cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f'{path}_{tag}.png'
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
