# Builds the Burritt Alley / Bush Street set for The Black Bird.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_set.py -- [--render prefix]
#   (or with Blender as a Python module:  python3 art/build_set.py -- [--render prefix])
#
# Writes art/set/burritt.blend and public/models/burritt.glb. Everything is modelled in the game's own
# coordinates (Y up, metres, the alley running along -Z from Bush Street at z = 8 to the fence at z = -22),
# then turned Z-up for Blender's exporter, which turns it back. The layout matches src/world/alley.js
# (web) and Chapter1.cs (Unity), which keep the colliders and the gameplay positions; this file provides
# everything you see, the ground included. --render makes look-dev stills with art/preview_set.py.
#
# San Francisco, 1895: brick and redwood Italianate fronts with bay windows and bracketed cornices,
# cast-iron shopfronts, basalt-block paving with a cable slot, plank sidewalks, gas lamps, telegraph wires.
#
# The pieces are in art/alleykit.py and the painted textures in art/alleytex.py; art/setkit.py is the kit
# shared with the other sets. Contracts kept for the engines:
#   - Lamp_0..Lamp_6 empties at the glass of the seven gas lamps, the alley's bracket lamp last;
#   - material names by prefix: brick*, clap*, *wood*, stone*, glass_dark, glass_lit*, lamp_glass;
#   - nothing solid where the games do not have a collider (see NEW_COLLIDERS, printed at the end).
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alleykit import *  # noqa: F401,F403  (setkit's names too: bpy, bmesh, math, np, Vector, Matrix, ...)

KERB_N, KERB_F = 9.85, 20.15       # the street faces of the kerbs (near side, far side)
WALK = 0.15                        # sidewalk height
NEW_COLLIDERS = []                 # [x0, z0, x1, z1, height, what]: solid things the first set did not have


def solid(x0, z0, x1, z1, h, what):
    NEW_COLLIDERS.append((round(min(x0, x1), 2), round(min(z0, z1), 2), round(max(x0, x1), 2), round(max(z0, z1), 2), h, what))


def mass(mat, x0, x1, h, z0, z1, skip=''):
    """The sides and roof of a building the fronts do not cover. skip: faces left open, of 'n' (+z), 's' (-z),
    'e' (+x), 'w' (-x)."""
    if 'n' not in skip: lquad(I4, mat, [(x0, 0, z1), (x1, 0, z1), (x1, h, z1), (x0, h, z1)], facing=(0, 0, 1))
    if 's' not in skip: lquad(I4, mat, [(x0, 0, z0), (x1, 0, z0), (x1, h, z0), (x0, h, z0)], facing=(0, 0, -1))
    if 'e' not in skip: lquad(I4, mat, [(x1, 0, z0), (x1, 0, z1), (x1, h, z1), (x1, h, z0)], facing=(1, 0, 0))
    if 'w' not in skip: lquad(I4, mat, [(x0, 0, z0), (x0, 0, z1), (x0, h, z1), (x0, h, z0)], facing=(-1, 0, 0))
    lquad(I4, 'roof', [(x0, h - 0.02, z0), (x1, h - 0.02, z0), (x1, h - 0.02, z1), (x0, h - 0.02, z1)], facing=(0, 1, 0))


def chimney(x, z, base, h=1.5, mat='brick_brown', pots=2):
    cbox(I4, mat, x - 0.4, x + 0.4, base - 0.3, base + h, z - 0.28, z + 0.28, b=0.0)
    cbox(I4, 'stone', x - 0.46, x + 0.46, base + h, base + h + 0.1, z - 0.34, z + 0.34, b=0.02)
    for k in range(pots):
        px = x + (k - (pots - 1) / 2) * 0.36
        cyl('brick_red', (px, base + h + 0.1, z), 0.42, 0.1, 0.075, seg=8)


# --- the ground ----------------------------------------------------------------------------------------

def ground():
    region('ground')
    # the alley: cobbles either side of a runner of setts down the middle, flat (the games walk on y = 0)
    for a, b, m in ((-2.5, -0.32, 'stone_cobble'), (-0.32, 0.32, 'stone_setts'), (0.32, 2.5, 'stone_cobble')):
        for z0, z1 in ((-22, -12), (-12, -2), (-2, 8)):
            lquad(I4, m, [(a, 0, z0), (b, 0, z0), (b, 0, z1), (a, 0, z1)], facing=(0, 1, 0))
    lquad(I4, 'stone_setts', [(-2.5, 0, 8), (2.5, 0, 8), (2.5, 0, KERB_N), (-2.5, 0, KERB_N)], facing=(0, 1, 0))   # the crossing
    # Bush Street's carriageway, in lengths (each within reach of only a few lamps)
    xs = [-50, -30, -16, -5, 5, 16, 30, 50]
    for a, b in zip(xs, xs[1:]):
        lquad(I4, 'stone_setts', [(a, 0, KERB_N), (b, 0, KERB_N), (b, 0, KERB_F), (a, 0, KERB_F)], facing=(0, 1, 0))
    # the cable road: slot between its two slot irons, running rails either side, hatch plates over the conduit
    for a, b in zip(xs, xs[1:]):
        for z in (14.2, 15.8):
            lbox(I4, 'rail_steel', a, b, 0.0, 0.012, z - 0.03, z + 0.03)
        lbox(I4, 'rail_steel', a, b, 0.0, 0.01, 14.945, 14.99)
        lbox(I4, 'rail_steel', a, b, 0.0, 0.01, 15.01, 15.055)
        lquad(I4, 'slot_black', [(a, 0.007, 14.99), (b, 0.007, 14.99), (b, 0.007, 15.01), (a, 0.007, 15.01)], facing=(0, 1, 0))
    for x in np.arange(-44, 46, 11.0):
        cbox(I4, 'iron_rust', x - 0.45, x + 0.45, 0.0, 0.012, 14.7, 14.93, b=0.004)
        cbox(I4, 'iron_rust', x - 0.45, x + 0.45, 0.0, 0.012, 15.07, 15.3, b=0.004)
    # sidewalks: redwood planks behind granite kerbs; the near side is broken by the alley
    for a, b in ((-50, -30), (-30, -16), (-16, -2.7), (2.7, 16), (16, 30), (30, 50)):
        sidewalk(a, b, 8.0, KERB_N - 0.2)
    for a, b in zip(xs, xs[1:]):
        sidewalk(a, b, KERB_F + 0.2, 22.0)
    kerb(-50, -2.7, KERB_N, 1, seed=1); kerb(2.7, 50, KERB_N, 1, seed=2); kerb(-50, 50, KERB_F, -1, seed=3)
    for s in (-1, 1):       # the kerb turned in along the alley's corners
        cbox(I4, 'stone', min(s * 2.5, s * 2.7), max(s * 2.5, s * 2.7), -0.05, WALK, 8.0, KERB_N - 0.2, b=0.018)
        cbox(I4, 'stone', min(s * 2.5, s * 2.7), max(s * 2.5, s * 2.7), -0.05, WALK + 0.004, KERB_N - 0.2, KERB_N, b=0.03)
    # standing water: in the gutters, in the worn hollows of the street, down the alley's edges
    g = random.Random(1895)
    for k in range(26):
        x = -36 + 72 * g.random()
        if -3.2 < x < 3.2: continue
        blob('stone_puddle', x, KERB_N + 0.28 + 0.2 * g.random(), 0.5 + 0.9 * g.random(), seed=k, squash=0.3)
    for k in range(22):
        blob('stone_puddle', -36 + 72 * g.random(), KERB_F - 0.28 - 0.2 * g.random(), 0.5 + 0.9 * g.random(), seed=100 + k, squash=0.3)
    for k in range(34):
        x, z = -34 + 68 * g.random(), 10.9 + 8.2 * g.random()
        if abs(z - 15) < 1.1 and g.random() < 0.6: z += 2.2
        blob('stone_puddle', x, z, 0.3 + 0.6 * g.random() ** 2, seed=200 + k, squash=0.45 + 0.5 * g.random(), rot=g.random() * 3)
    for x, z, r, sq in ((-1.3, 9.0, 0.7, 0.5), (1.6, 8.6, 0.5, 0.7), (0.2, 11.2, 0.8, 0.5), (-3.9, 10.4, 0.7, 0.4)):
        blob('stone_puddle', x, z, r, seed=int(x * 7 + z), squash=sq)
    for x, z, r, sq in ((-1.7, 5.6, 0.55, 0.6), (1.2, 3.4, 0.7, 0.5), (-0.9, 0.6, 0.6, 0.8), (-1.5, -1.6, 0.5, 0.6), (1.0, -2.6, 0.45, 0.9),
                        (0.0, -5.2, 0.8, 0.5), (-1.3, -8.6, 0.75, 0.7), (1.5, -9.4, 0.5, 0.6), (-0.4, -11.6, 0.6, 0.5), (1.6, -13.2, 0.45, 0.8),
                        (-1.9, -15.3, 0.4, 0.7), (1.9, -17.0, 0.4, 0.6), (-1.8, -19.6, 0.55, 0.5), (-1.2, -21.2, 0.5, 0.4), (1.9, -21.3, 0.4, 0.5)):
        m = 'stone_puddle' if abs(x) < 0.3 - r else 'stone_puddle_alley'
        if abs(x) - r * 0.9 < 0.32:   # keep a puddle on one paving or the other (its wet picture matches what is under it)
            r = max(0.25, abs(x) - 0.36); sq = min(1.0, sq * 1.5)
        blob(m, x, z, r, seed=int(x * 13 + z * 3), squash=sq, rot=1.57)
    # iron gratings: a gully at each kerb by the alley, a drain at the alley's low end
    for x, z in ((-4.6, KERB_N + 0.22), (4.4, KERB_N + 0.22), (-9.0, KERB_F - 0.22), (15.0, KERB_F - 0.22)):
        cbox(I4, 'iron_rust', x - 0.3, x + 0.3, 0.0, 0.01, z - 0.18, z + 0.18, b=0.004)
        for k in range(7):
            lbox(I4, 'slot_black', x - 0.25 + k * 0.075, x - 0.22 + k * 0.075, 0.006, 0.014, z - 0.14, z + 0.14)
    cbox(I4, 'iron_rust', -0.25, 0.25, 0.0, 0.008, -12.6, -12.1, b=0.003)
    for k in range(6):
        lbox(I4, 'slot_black', -0.21 + k * 0.075, -0.18 + k * 0.075, 0.004, 0.0115, -12.55, -12.15)
    for x, z in ((-11.2, 9.1), (-6.0, 8.9), (8.9, 9.2), (17.5, 9.0), (-21.0, 9.1), (2.0, 20.9), (-9.5, 21.0), (13.0, 20.8), (22.5, 21.1)):
        coal_hole(x, z)
    cellar_flap(-9.7, -8.3, 8.42, 9.5)
    cellar_flap(11.4, 12.6, 8.42, 9.5)


# --- the alley ------------------------------------------------------------------------------------------

def alley():
    region('alley')
    L = frame((-2.5, 0, 8), (0, 0, -1), (1, 0, 0))    # left wall faces +x; u runs from the street toward the fence (z = 8 - u)
    R = frame((2.5, 0, -22), (0, 0, 1), (-1, 0, 0))   # right wall faces -x; u runs from the fence toward the street (z = u - 22)
    HL, HR = 12.0, 8.6

    # ---- left: the side of Holtz's hardware store, three storeys of soot-dark brick ----
    holes = []
    W = lambda u, v, **k: holes.append(sash_window(L, u, v, wall_mat='brick_red', trim='trim_dark', **k))
    for u, st in ((5.0, {}), (14.6, {}), (24.6, dict(state='boarded'))):          # barred cellar-store windows
        W(u, 1.35, w=0.8, h=0.95, head='arch', bars=1, **st)
        for k in range(6):
            rod('iron', L @ Vector((u - 0.33 + k * 0.132, 1.35, -0.06)), L @ Vector((u - 0.33 + k * 0.132, 2.3, -0.06)), 0.011, 4)
        lbox(L, 'iron', u - 0.4, u + 0.4, 1.8, 1.83, -0.07, -0.05)
    f1 = [(2.6, dict(shutters='open')), (6.0, dict(state='lit0')), (9.0, dict(shutters='shut')), (11.4, {}), (13.6, dict(blind=('blind_cream', 0.6))),
          (17.0, dict(shutters='shut')), (21.0, dict(blind=('blind_green', 0.35))), (24.6, dict(shutters='open')), (28.0, {})]
    f2 = [(2.6, {}), (6.0, dict(blind=('blind_cream', 0.8))), (9.0, {}), (11.4, dict(blind=('blind_cream', 0.3))), (13.6, {}),
          (21.0, dict(shutters='open')), (24.6, dict(state='lit3')), (28.0, dict(shutters='shut'))]
    for u, kw in f1: W(u, 4.75, w=0.95, h=1.75, head='arch', **kw)
    for u, kw in f2: W(u, 8.35, w=0.95, h=1.75, head='arch', **kw)
    holes.append(plank_door(L, 18.0, w=1.15, h=2.15, wall_mat='brick_red', trim='trim_dark', leaf='wood_green', head='arch'))
    wall(L, 'brick_red', 0, 30, 0, HL, holes)
    for a, b in ((0, 17.2), (18.8, 30)):                                           # stone plinth
        extrude(L, 'stone', [(0, 0), (0.07, 0), (0.07, 0.56), (0.0, 0.64)], a, b)
    for v, gaps in ((4.15, ()), (7.75, ((14.4, 20.8),))):                          # brick string courses
        segs = [(0, 30)] if not gaps else [(0, gaps[0][0]), (gaps[0][1], 30)]
        for a, b in segs:
            extrude(L, 'brick_red', [(0, v - 0.16), (0.045, v - 0.13), (0.045, v), (0.0, v)], a, b)
    extrude(L, 'stone', [(0, HL - 0.3), (0.06, HL - 0.26), (0.1, HL - 0.1), (0.1, HL), (-0.3, HL), (-0.3, HL - 0.3)], 0, 30)   # coping
    for u in (4.0, 12.5, 19.5, 27.0):
        star_anchor(L, u, 3.8); star_anchor(L, u, 7.4)
    # the store's painted advertisement between the storeys, lamp-black and white lead
    lquad(L, 'paint_black', [(14.6, 6.72, 0.012), (20.6, 6.72, 0.012), (20.6, 8.08, 0.012), (14.6, 8.08, 0.012)], facing=(0, 0, 1))
    text('paint_faded', 'J. HOLTZ & SON', L, 17.6, 7.66, 0.016, 0.52)
    text('paint_faded', 'STOVES · TINWARE · TOOLS', L, 17.6, 7.02, 0.016, 0.3)
    poster(L, 'sign_deliveries', 18.0, 3.25, w=0.03)
    lbox(L, 'door_wood', 17.58, 18.42, 3.15, 3.35, 0.0, 0.028)
    # fire escape, with a gooseneck ladder on to the roof
    fire_escape2(L, 10.4, 14.6, (4.05, 7.65), 13.9)
    for w in (0.25, 0.7):
        rod('iron', L @ Vector((10.9, 7.65, w)), L @ Vector((10.9, HL + 0.9, w)), 0.016, 4)
        tube('iron', [L @ Vector((10.9, HL + 0.9, w)), L @ Vector((10.9, HL + 1.0, w)), L @ Vector((10.9 - 0.0, HL + 1.0, w * 0.0 - 0.25))], 0.016, 4)
    for k in range(15):
        rod('iron_rust', L @ Vector((10.9, 7.95 + k * 0.3, 0.25)), L @ Vector((10.9, 7.95 + k * 0.3, 0.7)), 0.011, 4)
    # rain leaders, vents, the gas pipe to the lamp
    drainpipe2(-2.5, 2.2, HL - 0.5, 1)
    drainpipe2(-2.5, -20.6, HL - 0.5, 1)
    wall_vent(L, 8.2, 0.75); wall_vent(L, 22.4, 0.75); wall_vent(L, 27.2, 3.4)
    tube('iron', [L @ Vector((16.0, 0.0, 0.03)), L @ Vector((16.0, 3.25, 0.03))], 0.014, 5)   # gas pipe up to the bracket
    for v in (0.9, 2.2):
        lbox(L, 'iron', 15.96, 16.04, v, v + 0.03, 0.0, 0.05)
    # ---- right: the back of the chop house, two storeys of brown brick; lodgings over, reached by an outside stair ----
    holes = []
    W = lambda u, v, **k: holes.append(sash_window(R, u, v, wall_mat='brick_brown', trim='trim_maroon', **k))
    for u in (11.0, 26.6):
        W(u, 1.35, w=0.8, h=0.95, head='lintel', bars=1)
        for k in range(6):
            rod('iron', R @ Vector((u - 0.33 + k * 0.132, 1.35, -0.06)), R @ Vector((u - 0.33 + k * 0.132, 2.3, -0.06)), 0.011, 4)
        lbox(R, 'iron', u - 0.4, u + 0.4, 1.8, 1.83, -0.07, -0.05)
    for u, kw in ((2.6, dict(shutters='shut')), (6.4, dict(blind=('blind_cream', 0.5))), (10.4, dict(state='lit0')), (14.4, dict(shutters='open')),
                  (18.6, dict(blind=('blind_green', 0.7))), (25.6, {}), (28.4, dict(blind=('blind_cream', 0.25)))):
        W(u, 5.15, w=0.95, h=1.65, head='lintel', **kw)
    holes.append(plank_door(R, 7.0, w=1.1, h=2.15, wall_mat='brick_brown', trim='trim_maroon', leaf='door_wood', head='lintel'))
    holes.append(plank_door(R, 22.55, w=0.95, h=2.05, wall_mat='brick_brown', trim='trim_maroon', leaf='wood_red', head='lintel', v0=4.2, step=0.0,
                            lit='glass_lit3'))
    wall(R, 'brick_brown', 0, 30, 0, HR, holes)
    for a, b in ((0, 6.25), (7.75, 30)):
        extrude(R, 'stone', [(0, 0), (0.06, 0), (0.06, 0.5), (0.0, 0.58)], a, b)
    extrude(R, 'brick_brown', [(0, 4.3), (0.045, 4.33), (0.045, 4.46), (0.0, 4.46)], 0, 21.9)
    extrude(R, 'brick_brown', [(0, 4.3), (0.045, 4.33), (0.045, 4.46), (0.0, 4.46)], 23.2, 30)
    extrude(R, 'stone', [(0, HR - 0.28), (0.06, HR - 0.24), (0.1, HR - 0.1), (0.1, HR), (-0.3, HR), (-0.3, HR - 0.28)], 0, 30)
    for u in (4.6, 16.4, 27.6):
        star_anchor(R, u, 4.0)
    back_stair(R, 16.3, 23.25, 4.2, width=0.92)
    solid(1.55, -5.75, 2.5, 1.3, 5.2, 'back stair')
    poster(R, 'sign_stair', 15.7, 2.2, w=0.03)
    lbox(R, 'door_wood', 15.38, 16.02, 2.02, 2.38, 0.0, 0.028)
    drainpipe2(2.5, -9.0, HR - 0.5, -1)
    drainpipe2(2.5, 6.6, HR - 0.5, -1, bottom=0.3)
    stove_flue(R, 12.6, 2.7, HR + 0.9)                     # the chop house's kitchen range
    wall_vent(R, 12.6, 0.8, w=0.4, h=0.3); wall_vent(R, 24.6, 0.72)
    hoarding(R, 2.5, 2.6)                                  # the billboard at the dead end
    # ---- bills ----
    for name, u, v, ro, sc in (('sign_nobills', 2.1, 1.75, 0.0, 1.0), ('bill_tivoli', 7.3, 1.75, 0.03, 1.0), ('bill_paloma', 8.05, 1.62, -0.04, 1.0),
                               ('bill_reward', 8.75, 1.78, 0.02, 1.0), ('bill_sutro', 7.75, 2.46, 0.06, 1.0), ('bill_auction', 9.4, 1.6, -0.02, 1.0),
                               ('bill_ball', 20.9, 1.7, 0.03, 1.0), ('bill_rooms', 21.6, 1.75, -0.07, 1.0), ('bill_seamen', 26.2, 1.6, 0.04, 1.0),
                               ('bill_beer', 26.75, 1.75, -0.03, 1.0), ('bill_paloma', 29.35, 1.7, 0.02, 1.0), ('bill_tivoli', 3.4, 1.9, -0.02, 0.9)):
        poster(L, name, u, v, w=0.01 + 0.003 * ((len(name) + int(u * 10)) % 4), rot=ro, scale=sc)
    for name, u, v, ro in (('bill_auction', 9.35, 1.7, 0.03), ('bill_sutro', 9.95, 1.85, -0.05), ('bill_ball', 14.4, 1.75, 0.02), ('bill_reward', 5.3, 1.7, -0.03),
                           ('bill_seamen', 13.6, 1.6, 0.06), ('bill_beer', 28.3, 1.9, 0.0), ('bill_rooms', 24.0, 1.75, 0.04)):
        poster(R, name, u, v, rot=ro)
    poster(L, 'plate_burritt', 0.62, 3.05, w=0.012)

    # ---- the lamp ----
    lamp = wall_lamp(-2.5, 3.35, -8, out=1)

    # ---- clutter: against the walls, where the games already have colliders or new ones are listed ----
    crate2(-1.9, 0.45, -3.5, 0.9, rot=0.04, label='crate_holtz')
    crate2(-1.95, 1.22, -3.42, 0.64, rot=0.3, label='crate_fragile')
    crate2(-2.05, 0.3, -4.45, 0.6, rot=-0.1, h=0.6, open_top=True)
    sack(-2.1, -2.75, s=0.95, rot=0.4); sack(-1.75, -2.6, s=0.8, rot=1.3, lying=True)
    solid(-2.5, -4.8, -1.4, -2.4, 1.6, 'crates and sacks (wider than the old crate collider)')
    handcart(-1.7, 4.3, rot=math.pi / 2 + 0.06)
    solid(-2.5, 2.3, -1.1, 5.2, 1.0, 'handcart')
    sack(-1.75, 4.55, y=0.5, s=0.8, rot=1.5, lying=True)
    cellar_bulkhead(L, 19.3, 20.5)
    solid(-2.5, -12.6, -1.55, -11.2, 0.7, 'cellar doors')
    ash_can2(-2.0, -13.0, lid='on', rot=0.4)
    ash_can2(-2.12, -13.72, lid='off', rot=1.1)
    solid(-2.5, -14.9, -1.6, -12.65, 0.9, 'second ash can, rubbish and a ladder')
    rubbish(-1.9, -14.4, r=0.45, seed=3, n=8)
    ladder(L, 22.6, length=3.6, lean=0.2)
    barrel2(2.0, -6.2); barrel2(1.95, -7.1, lid=False)
    barrel2(2.12, -5.2, h=0.7, r=0.26, mat='barrel_wood')                                  # under the stair
    crate2(2.08, 0.26, -3.9, 0.52, rot=0.2, label='crate_tea'); crate2(2.1, 0.25, -3.1, 0.5, rot=-0.15)
    crate2(2.1, 0.72, -3.5, 0.44, rot=0.5, open_top=True)
    sack(2.15, -1.9, s=0.9, rot=0.2); sack(2.1, -1.3, s=0.85, rot=1.9); sack(2.12, -1.6, y=0.55, s=0.75, lying=True, rot=1.57)
    bottle(1.75, -2.45); bottle(1.82, -2.3, lying=True, rot=0.8)
    crate2(1.95, 0.4, -11.5, 0.8, rot=-0.05)
    crate2(2.02, 0.19, -12.3, 0.55, h=0.38, rot=0.25, open_top=True)
    for k in range(5): bottle(1.9 + 0.09 * (k % 3), -12.38 + 0.11 * (k // 3) + 0.05 * (k % 2), y=0.06)
    solid(1.5, -12.7, 2.5, -11.0, 0.9, 'crate and bottle case (wider than the old crate collider)')
    timber_stack(R, 7.9, n=7, length=3.3, seed=3)                                         # planks stood by the kitchen door
    solid(1.75, -14.15, 2.5, -12.95, 2.5, 'stacked timber')
    rubbish(1.95, -8.3, r=0.4, seed=5, n=7); rubbish(-2.0, -17.6, r=0.35, seed=9, n=5); rubbish(1.9, -21.2, r=0.4, seed=11, n=6)
    rubbish(-1.9, 0.9, r=0.45, seed=13, n=7); rubbish(2.0, 7.0, r=0.3, seed=17, n=4)
    sheet(I4, 'newspaper', [(-1.2, 0.014, -6.9), (-0.82, 0.02, -7.08), (-0.6, 0.014, -6.55), (-0.98, 0.03, -6.38)])
    for x, z, s in ((-2.38, -16.0, 1), (-2.4, -18.9, 2), (2.38, -16.3, 3), (-2.36, -9.1, 4), (2.4, 4.0, 5), (-2.4, 6.9, 6), (2.36, -20.4, 7), (-2.3, -21.6, 8),
                    (2.3, -21.7, 9), (-2.4, -0.4, 10)):
        weeds(x, z, n=5, h=0.28, r=0.1, seed=s)
    # corner guard posts at the alley mouth
    bollard(-2.28, 8.32); bollard(2.28, 8.32)
    solid(-2.42, 8.18, -2.14, 8.46, 0.8, 'corner post'); solid(2.14, 8.18, 2.42, 8.46, 0.8, 'corner post')

    # ---- overhead: the wash, telephone wires ----
    laundry_line((-2.46, 6.3, -15.2), (2.46, 6.5, -13.6), [(0.14, 'shirt'), (0.3, 'sheet'), (0.5, 'drawers'), (0.64, 'blue'), (0.78, 'towel'), (0.9, 'red')], sag=0.45)
    laundry_line((-2.46, 9.6, 1.5), (2.46, 8.4, 2.6), [(0.2, 'towel'), (0.38, 'shirt'), (0.6, 'sheet'), (0.82, 'drawers')], sag=0.5, seed=8)
    for z, y in ((-2.0, 9.2), (-10.5, 8.9), (5.5, 9.4), (-18.0, 8.8)):
        wire3((-2.46, y + 1.4, z), (2.46, y - 0.5, z + 0.6), sag=0.3)

    # ---- the dead end: the board fence with Archer's gap, the ledge and the drop ----
    plank_fence(-2.5, 2.5, -22.0, gap=(0.35, 1.15), behind=-1)
    for x, rz, ry in ((0.5, 0.2, 0.3), (0.9, -0.15, -0.4), (0.7, 0.05, 0.1)):               # the snapped boards, out on the ledge
        F = Matrix.Translation((x, -0.2, -22.9)) @ Matrix.Rotation(ry, 4, 'Y') @ Matrix.Rotation(rz, 4, 'Z') @ Matrix.Rotation(-math.pi / 2 + 0.15, 4, 'X')
        cbox(F, 'wood_fence', -0.09, 0.09, -0.6, 0.6, -0.014, 0.014, b=0.004)
    for x in (0.38, 1.1):                                                                    # splintered stumps left in the gap
        cbox(I4, 'wood_fence', x - 0.08, x + 0.08, 0.02, 0.3 + 0.2 * (x < 1), -22.014, -21.986, b=0.004)
    poster(frame((0, 0, -21.985), (1, 0, 0), (0, 0, 1)), 'sign_nobills', -1.45, 1.3, w=0.004, rot=-0.02, scale=0.9)
    lquad(I4, 'earth', [(-3.4, -0.26, -24.5), (3.4, -0.26, -24.5), (3.4, -0.26, -22.02), (-3.4, -0.26, -22.02)], facing=(0, 1, 0))
    lquad(I4, 'stone', [(-2.5, -0.26, -22.02), (2.5, -0.26, -22.02), (2.5, 0.0, -22.02), (-2.5, 0.0, -22.02)], facing=(0, 0, -1))
    lquad(I4, 'earth', [(-9, -5.5, -33), (9, -5.5, -33), (3.4, -0.26, -24.5), (-3.4, -0.26, -24.5)], facing=(0, 1, 0))
    g = random.Random(22)
    for k in range(26):
        x, z = -2.6 + 5.2 * g.random(), -22.25 - 2.0 * g.random()
        big = not (0.5 < x < 1.4 and z > -23.8)          # low round the revolver: it must still catch the eye
        weeds(x, z, y=-0.26, n=6, h=0.5 if big else 0.2, r=0.16, seed=40 + k)
    return lamp


# --- Bush Street ---------------------------------------------------------------------------------------

def near_side():
    """Fronts face +z at z = 8; u = x."""
    region('near')
    F = frame((0, 0, 8), (1, 0, 0), (0, 0, 1))
    # A. the drug store: cream clapboard, two bays, an awning left down
    top = shopfront2(F, -28, -14, 'DRUGS & CHEMICALS', trim='trim_dark', bays=5, door=2, letters={1: 'DRUGS', 3: 'PRESCRIPTIONS'}, leaf='wood_green')
    upper_floors(F, -28, -14, top, 10.9, 'clap_cream', 'trim_dark', 2, bays=(-24.4, -17.6), head='cap', per=2.33, lit={(1, 2): 'lit3'},
                 cornice_h=0.95, states=['dark', 'dark', 'dark', 'dark', 'lit0', 'dark'])
    mass('clap_cream', -28, -14, 10.9, -6, 8, skip='n')
    awning(F, -27.5, -22.6, 3.5, mat='cloth_awning_green')
    chimney(-22, 6.5, 10.9); chimney(-16, 3.0, 10.9, pots=1)
    # B. Holtz's hardware: red brick, arched windows, a dentilled cornice; its side is the alley's left wall
    top = shopfront2(F, -14, -2.5, 'J. HOLTZ & SON · HARDWARE', trim='trim_cream', bays=4, door=1, wall_mat='brick_red', letters={2: 'STOVES', 3: 'CUTLERY'},
                     blinds=0.3)
    upper_floors(F, -14, -2.5, top, 12.0, 'brick_red', 'trim_cream', 2, head='arch', per=2.3, dentils=True, quoins=True, lit={(0, 3): 'lit0'},
                 cornice_h=1.1, cornice_d=0.7)
    mass('brick_red', -14, -2.5, 12.0, -22, 8, skip='ne')
    poster(F, 'plate_bush', -3.3, 3.05, w=0.012)
    chimney(-8, 6.2, 12.0); chimney(-4, -3.0, 12.0)
    # goods left out before the hardware store
    barrel2(-13.2, 8.62, y=WALK, h=0.8, r=0.27); crate2(-12.55, WALK + 0.3, 8.6, 0.6, rot=0.1, label='crate_holtz')
    crate2(-12.6, WALK + 0.8, 8.58, 0.42, rot=0.4)
    solid(-13.6, 8.0, -12.2, 9.0, 1.2, 'barrel and crates on the sidewalk')
    # C. the chop house: brown brick, one storey over the shop, open all night
    top = shopfront2(F, 2.5, 14, 'CHOP HOUSE · OYSTERS', trim='trim_cream', bays=4, door=2, sign_mat='sign_board_red', lit='glass_lit2', wall_mat='brick_brown',
                     leaf='wood_red', lit_bays=(0, 1, 2, 3))
    upper_floors(F, 2.5, 14, top, 8.6, 'brick_brown', 'trim_cream', 1, head='pediment', per=2.3, lit={(0, 1): 'lit0'}, cornice_h=0.9, quoins=True)
    mass('brick_brown', 2.5, 14, 8.6, -22, 8, skip='nw')
    hanging_sign(F, 3.5, 5.05, 'sign_oysters', out=1.15)
    chimney(11.0, -8.6, 8.6, h=1.8); chimney(6, 5.5, 8.6, pots=1)
    # D. the Golden Eagle: tan brick, a bay over the door, lit
    top = shopfront2(F, 14, 28, 'THE GOLDEN EAGLE · SALOON', trim='trim_dark', bays=5, door=2, sign_mat='sign_board_red', lit='glass_lit2',
                     leaf='door_wood', lit_bays=(0, 1, 2, 3))
    upper_floors(F, 14, 28, top, 11.4, 'brick_tan', 'trim_dark', 2, bays=(21.0,), head='hood', per=2.33, lit={(1, 0): 'lit1', (0, 4): 'lit3'},
                 cornice_h=1.0, states=['dark', 'lit0', 'dark', 'dark', 'dark', 'dark'])
    mass('brick_tan', 14, 28, 11.4, -6, 8, skip='n')
    a_board(15.3, 9.05, 'sign_lunch', rot=0.25)
    solid(14.9, 8.7, 15.7, 9.4, 1.0, 'sandwich board')
    chimney(17, 6.0, 11.4); chimney(25, 6.4, 11.4, pots=3)
    # its beer advertisement, painted on the side wall above the chop house's roof
    S = frame((14, 0, -6), (0, 0, 1), (-1, 0, 0))
    lquad(S, 'paint_white', [(6.2, 8.95, 0.012), (13.7, 8.95, 0.012), (13.7, 11.0, 0.012), (6.2, 11.0, 0.012)], facing=(0, 0, 1))
    text('paint_black', 'GOLDEN EAGLE', S, 9.95, 10.4, 0.016, 0.62)
    text('paint_black', 'STEAM BEER 5¢', S, 9.95, 9.5, 0.016, 0.5)
    barrel2(27.2, 8.6, y=WALK, h=0.9, r=0.3)
    solid(26.85, 8.0, 27.55, 8.95, 1.0, 'barrel by the saloon')


def far_side():
    """Fronts face -z at z = 22; u = -x."""
    region('far')
    F = frame((0, 0, 22), (-1, 0, 0), (0, 0, -1))
    # the livery stable: grey clapboard false front, carriage doors, a hayloft door and hoist
    u0, u1 = 18, 30
    H = 9.0
    holes = [(22.2, 25.8, 0, 3.5), (23.3, 24.7, 5.0, 7.0)]
    reveal(F, 'trim_cream', 22.2, 25.8, 0, 3.5, 0.15, 'lrt')
    for a, b, hinge in ((22.2, 24.0, 22.2), (24.0, 25.8, 25.8)):          # the carriage doors: boarded, cross-braced
        lbox(F, 'wood_fence', a + 0.01, b - 0.01, 0.03, 3.5, -0.15, -0.1)
        for v in (0.25, 1.75, 3.25):
            lbox(F, 'wood_fence', a + 0.03, b - 0.03, v - 0.09, v + 0.09, -0.1, -0.07)
        extrude(F, 'wood_fence', [(a + 0.05, 0.34), (a + 0.25, 0.34), (b - 0.05, 1.66), (b - 0.25, 1.66)], -0.1, -0.075, axis='w')
        extrude(F, 'wood_fence', [(a + 0.05, 3.16), (a + 0.25, 3.16), (b - 0.05, 1.84), (b - 0.25, 1.84)], -0.1, -0.075, axis='w')
        for v in (0.25, 3.25):
            s = 1 if hinge == a else -1
            lbox(F, 'iron', min(hinge, hinge + s * 0.7), max(hinge, hinge + s * 0.7), v - 0.03, v + 0.03, -0.07, -0.06)
    for a, b in ((21.95, 22.2), (25.8, 26.05)):
        lbox(F, 'trim_cream', a, b, 0, 3.75, 0, 0.04)
    lbox(F, 'trim_cream', 21.95, 26.05, 3.5, 3.75, 0, 0.05)
    holes.append(plank_door(F, 27.5, w=1.0, h=2.1, wall_mat='trim_cream', trim='trim_cream', leaf='door_wood', depth=0.1, step=0.0, head='cap', strap=False))
    holes.append(sash_window(F, 19.9, 1.1, w=1.2, h=1.5, wall_mat='clap_grey', trim='trim_cream', head='cap', depth=0.1, casing=True, sill='trim_cream', bars=2,
                state='lit3'))
    wall(F, 'clap_grey', u0, u1, 0, H - 0.2, holes)
    reveal(F, 'trim_cream', 23.3, 24.7, 5.0, 7.0, 0.1)                     # hayloft door
    lbox(F, 'wood_fence', 23.3, 24.7, 5.0, 7.0, -0.1, -0.06)
    for v in (5.25, 6.75):
        lbox(F, 'wood_fence', 23.33, 24.67, v - 0.07, v + 0.07, -0.06, -0.035)
    for a, b in ((23.15, 23.3), (24.7, 24.85)):
        lbox(F, 'trim_cream', a, b, 4.9, 7.15, 0, 0.035)
    lbox(F, 'trim_cream', 23.15, 24.85, 7.0, 7.15, 0, 0.045)
    cbox(F, 'wood_fence', 23.9, 24.1, 7.3, 7.5, -0.2, 1.3, b=0.01)         # the hoist beam and its tackle
    rod('rope', F @ Vector((24.0, 7.3, 1.15)), F @ Vector((24.0, 5.6, 1.15)), 0.012, 4)
    cyl('iron', F @ Vector((23.96, 7.2, 1.15)), 0.08, 0.09, 0.09, seg=8, axis=F.to_3x3() @ Vector((1, 0, 0)))
    tube('iron', [F @ Vector((24.0, 5.6, 1.15)), F @ Vector((24.05, 5.5, 1.15)), F @ Vector((24.0, 5.42, 1.15)), F @ Vector((23.95, 5.5, 1.15))], 0.01, 4)
    fascia(F, 18.4, 29.6, 3.95, 'PIONEER LIVERY STABLE', 'sign_board_black', 'trim_cream', h=0.62)
    for x in (u0 + 0.1, u1 - 0.1):
        lbox(F, 'trim_cream', x - 0.1, x + 0.1, 0, H - 0.2, 0, 0.035)
    cornice2(F, u0, u1, H, 'trim_cream', depth=0.4, height=0.7, brackets=1.5, panels=False)
    gable_parapet(F, u0, u1, H, 'clap_grey', 'trim_cream', rise=1.7, text_s='1878')
    mass('clap_grey', -30, -18, H, 22, 30, skip='s')
    poster(F, 'sign_livery', 20.0, 3.2, w=0.035)
    tube('iron', [(-27.2, WALK + 0.8, 20.45), (-21.0, WALK + 0.8, 20.45)], 0.022, 6)
    for x in (-27.2, -24.1, -21.0):
        hitching_post(x, 20.45)
    solid(-27.3, 20.35, -20.9, 20.55, 1.1, 'hitching rail')
    wagon(-24.0, 19.15, rot=math.pi + 0.03)
    solid(-28.4, 18.2, -22.2, 20.1, 1.9, 'delivery wagon and its pole')
    barrel2(-18.6, 21.55, y=WALK, h=0.85, r=0.29); sack(-19.3, 21.6, y=WALK, s=0.9, rot=0.5); sack(-19.85, 21.55, y=WALK, s=0.85, rot=2.0)
    solid(-20.2, 21.2, -18.25, 22.0, 1.0, 'feed barrel and sacks')
    # the Belvedere: three storeys of red brick, a saloon below, open all night (where Thursby drinks)
    top = shopfront2(F, 6, 18, 'THE BELVEDERE', trim='trim_cream', bays=4, door=1, sign_mat='sign_board_red', lit='glass_lit2', wall_mat='brick_red',
                     leaf='wood_red', lit_bays=(0, 1, 2, 3))
    upper_floors(F, 6, 18, top, 14.0, 'brick_red', 'trim_cream', 3, head='hood', per=2.4, lit={(0, 1): 'lit0', (1, 3): 'lit1', (2, 0): 'lit3'}, cornice_h=1.15,
                 cornice_d=0.75, dentils=True, pilasters=True)
    mass('brick_red', -18, -6, 14.0, 22, 30, skip='s')
    hanging_sign(F, 17.1, 5.1, 'sign_rooms', out=1.1)
    chimney(-15, 23.4, 14.0); chimney(-9, 23.6, 14.0, pots=3)
    # the French laundry: sage clapboard, two bays, right opposite the alley
    top = shopfront2(F, -6, 6, 'FRENCH LAUNDRY', trim='trim_cream', bays=4, door=2, pier='trim_cream', leaf='wood_green', bulk='wood_green', glazing=2,
                     letters={0: 'BLANCHISSERIE', 3: 'FINE LINEN'})
    upper_floors(F, -6, 6, top, 10.8, 'clap_sage', 'trim_cream', 2, bays=(-3.0, 3.0), head='pediment', per=2.4, lit={(1, 2): 'lit0'}, cornice_h=0.95,
                 states=['dark', 'dark', 'dark', 'lit3', 'dark', 'dark', 'dark', 'dark', 'dark', 'dark', 'dark', 'dark'])
    mass('clap_sage', -6, 6, 10.8, 22, 30, skip='s')
    hanging_sign(F, -5.3, 5.0, 'sign_baths', out=1.05)
    awning(F, 1.2, 5.6, 3.5, mat='cloth_awning')
    chimney(3, 23.5, 10.8, pots=1)
    # the Hibernia Savings: dressed stone below with arched windows, tan brick above
    u0, u1 = -18, -6
    holes = []
    for u in (-16.3, -13.9, -10.1, -7.7):
        holes.append((u - 0.6, u + 0.6, 1.2, 3.2))
        reveal(F, 'stone_sand', u - 0.6, u + 0.6, 1.2, 3.2, 0.3)
        pane(F, 'glass_dark', u - 0.6, u + 0.6, 1.2, 3.2, -0.3)
        lbox(F, 'trim_dark', u - 0.6, u + 0.6, 2.4, 2.46, -0.3, -0.25); lbox(F, 'trim_dark', u - 0.02, u + 0.02, 1.2, 3.2, -0.3, -0.26)
        window_head(F, 'arch', u - 0.6, u + 0.6, 3.2, 'stone_sand', stone='stone_sand')
        cbox(F, 'stone_sand', u - 0.75, u + 0.75, 1.08, 1.2, -0.1, 0.1, b=0.015)
        for k in range(7):                               # the bank's window bars
            x = u - 0.5 + k * 0.167
            rod('iron', F @ Vector((x, 1.2, -0.12)), F @ Vector((x, 3.2, -0.12)), 0.012, 4)
        for v in (1.6, 2.8):
            lbox(F, 'iron', u - 0.6, u + 0.6, v, v + 0.03, -0.135, -0.105)
    holes.append((-12.75, -11.25, 0.3, 3.3))
    reveal(F, 'stone_sand', -12.75, -11.25, 0.3, 3.3, 0.45, 'lrt')
    panel_door(F, -12.7, -12.0, 0.3, 2.4, -0.45, 'door_wood', glazed=False); panel_door(F, -12.0, -11.3, 0.3, 2.4, -0.45, 'door_wood', glazed=False, knob_right=False)
    lbox(F, 'door_wood', -12.75, -11.25, 2.7, 2.8, -0.47, -0.4); pane(F, 'glass_dark', -12.75, -11.25, 2.8, 3.3, -0.44)
    for k, (a, b) in enumerate(((0.0, 0.1), (0.1, 0.2), (0.2, 0.3))):
        cbox(F, 'stone', -13.3 + k * 0.12, -10.7 - k * 0.12, a, b, -0.45, 0.75 - k * 0.22, b=0.015)
    wall(F, 'stone_sand', u0, u1, 0, 4.4, holes)
    for v in np.arange(0.62, 4.2, 0.5):                  # rustication: channelled joints
        lbox(F, 'slot_black', u0, -12.95, v, v + 0.02, 0.0, 0.012); lbox(F, 'slot_black', -11.05, u1, v, v + 0.02, 0.0, 0.012)
    extrude(F, 'stone', [(0, 0), (0.1, 0), (0.1, 0.5), (0.0, 0.58)], u0, -13.3); extrude(F, 'stone', [(0, 0), (0.1, 0), (0.1, 0.5), (0.0, 0.58)], -10.7, u1)
    for x in (-13.05, -10.95):                           # columns by the door, and the entablature they carry
        cyl('stone_sand', F @ Vector((x, 0.3, 0.32)), 0.25, 0.26, 0.22, seg=10)
        cyl('stone_sand', F @ Vector((x, 0.55, 0.32)), 2.75, 0.19, 0.16, seg=12, cap=False)
        cbox(F, 'stone_sand', x - 0.27, x + 0.27, 3.3, 3.5, 0.05, 0.6, b=0.02)
    cbox(F, 'stone_sand', -13.4, -10.6, 3.5, 3.95, 0.0, 0.62, b=0.02)
    extrude(F, 'stone_sand', [(-13.6, 3.95), (-10.4, 3.95), (-12.0, 4.75)], 0.0, 0.66, axis='w')
    extrude(F, 'stone_sand', [(0, 4.4), (0.14, 4.4), (0.2, 4.5), (0.34, 4.56), (0.34, 4.64), (0, 4.7)], u0, -13.5)
    extrude(F, 'stone_sand', [(0, 4.4), (0.14, 4.4), (0.2, 4.5), (0.34, 4.56), (0.34, 4.64), (0, 4.7)], -10.5, u1)
    text('gilt', 'HIBERNIA SAVINGS', F, -15.2, 3.85, 0.008, 0.3); text('gilt', '& LOAN SOCIETY', F, -8.8, 3.85, 0.008, 0.3)
    upper_floors(F, u0, u1, 4.7, 12.4, 'brick_tan', 'trim_cream', 2, head='pediment', per=2.4, cornice_h=1.1, cornice_d=0.7, dentils=True, quoins=True,
                 sill='stone_sand', blinds=0.7)
    mass('brick_tan', 6, 18, 12.4, 22, 30, skip='s')
    chimney(9, 23.5, 12.4); chimney(15.5, 23.5, 12.4)
    # the tobacconist: ochre clapboard, one storey over the shop under a false front
    top = shopfront2(F, -30, -18, 'TOBACCO & CIGARS', trim='trim_dark', bays=4, door=1, pier='trim_dark', leaf='door_wood', glazing=2, letters={2: 'HAVANAS'},
                     sign_mat='sign_board_red')
    upper_floors(F, -30, -18, top, 8.2, 'clap_ochre', 'trim_dark', 1, bays=(-24.0,), head='cap', per=2.4, cornice_h=0.8, cornice_d=0.45,
                 states=['dark', 'lit0', 'dark'])
    gable_parapet(F, -30, -18, 8.2, 'clap_ochre', 'trim_dark', rise=1.3)
    mass('clap_ochre', 18, 30, 8.2, 22, 30, skip='s')
    hanging_sign(F, -18.9, 5.0, 'sign_cigars', out=1.1)
    awning(F, -29.4, -25.2, 3.5, mat='cloth_awning')


def street_ends():
    """Bush Street on past the ends of the walkable street (the games stop you at |x| = 28.5), into the fog."""
    region('ends')
    Fn = frame((0, 0, 8), (1, 0, 0), (0, 0, 1))
    Ff = frame((0, 0, 22), (-1, 0, 0), (0, 0, -1))
    lean = dict(blinds=0.3, head='cap')
    top = shopfront2(Fn, 28, 44, 'COFFEE HOUSE', trim='trim_cream', bays=4, door=1, pier='trim_cream')
    upper_floors(Fn, 28, 44, top, 10.2, 'clap_grey', 'trim_cream', 2, per=3.2, cornice_h=0.9, lit={(0, 2): 'lit0'}, **lean)
    mass('clap_grey', 28, 44, 10.2, -6, 8, skip='n')
    top = shopfront2(Fn, -44, -28, 'BOOTS & SHOES', trim='trim_cream', bays=4, door=2, wall_mat='brick_brown')
    upper_floors(Fn, -44, -28, top, 11.2, 'brick_brown', 'trim_cream', 2, per=3.2, cornice_h=1.0, lit={(1, 1): 'lit3'}, **lean)
    mass('brick_brown', -44, -28, 11.2, -6, 8, skip='n')
    top = shopfront2(Ff, 30, 46, 'ASSAY OFFICE', trim='trim_dark', bays=4, door=2, wall_mat='brick_tan')
    upper_floors(Ff, 30, 46, top, 11.6, 'brick_tan', 'trim_dark', 2, per=3.2, cornice_h=1.0, lit={(0, 1): 'lit0'}, **lean)
    mass('brick_tan', -46, -30, 11.6, 22, 30, skip='s')
    top = shopfront2(Ff, -46, -30, 'PAWNBROKER', trim='trim_cream', bays=4, door=1, wall_mat='brick_red', sign_mat='sign_board_black')
    upper_floors(Ff, -46, -30, top, 11.0, 'brick_red', 'trim_cream', 2, per=3.2, cornice_h=1.0, **lean)
    mass('brick_red', 30, 46, 11.0, 22, 30, skip='s')
    hanging_sign(Ff, -31.2, 5.1, 'sign_loans', out=1.1)
    for k, (dx, dy) in enumerate(((-0.14, 0), (0.14, 0), (0, -0.2))):     # the pawnbroker's three balls
        sphere('gilt', Ff @ Vector((-33.5 + dx, 5.4 + dy, 0.9)), 0.11, 8)
    rod('iron', Ff @ Vector((-33.5, 5.55, 0)), Ff @ Vector((-33.5, 5.55, 0.95)), 0.014, 4)
    for sx in (-1, 1):   # where Bush Street bends out of sight: lodgings across its end, closing the view
        Fe = frame((50, 0, 8), (0, 0, 1), (-1, 0, 0)) if sx > 0 else frame((-50, 0, 22), (0, 0, -1), (1, 0, 0))
        top = shopfront2(Fe, 0, 14, 'LODGINGS', trim='trim_dark', bays=4, door=1, pier='trim_dark')
        upper_floors(Fe, 0, 14, top, 12.0, 'clap_cream', 'trim_dark', 2, per=3.5, cornice_h=1.0, lit={(1, 1): 'lit0'} if sx > 0 else {(0, 2): 'lit3'}, **lean)
        lquad(I4, 'roof', [(sx * 50, 11.98, 6), (sx * 58, 11.98, 6), (sx * 58, 11.98, 24), (sx * 50, 11.98, 24)], facing=(0, 1, 0))
        for z0, z1 in ((6, 8), (22, 24)):
            lquad(I4, 'clap_cream', [(sx * 50, 0, z0), (sx * 50, 0, z1), (sx * 50, 12, z1), (sx * 50, 12, z0)], facing=(-sx, 0, 0))
        for a, b, z0, z1, m in ((44, 50, 6, 8, 'brick_brown'), (46, 50, 22, 24, 'brick_brown')):   # stop the gaps at the corners
            x0, x1 = (a, b) if sx > 0 else (-b, -a)
            zz = z1 if z0 < 10 else z0
            lquad(I4, m, [(x0, 0, zz), (x1, 0, zz), (x1, 10, zz), (x0, 10, zz)], facing=(0, 0, 1 if z0 < 10 else -1))


def furniture():
    """Lamps, poles and wires, and the street's ironmongery. Returns the lamp markers, in the order the
    engines know them."""
    region('near')
    lamps = [street_lamp(-3.6, 9.6), street_lamp(13.0, 9.6), street_lamp(-19.0, 9.6)]
    region('far')
    lamps += [street_lamp(7.0, 20.6), street_lamp(-13.0, 20.6), street_lamp(24.0, 20.6)]
    region('ends')
    street_lamp(38.0, 9.6); street_lamp(-36.0, 20.6); street_lamp(-40.0, 9.6); street_lamp(42.0, 20.6)   # unlit markers: their glass glows in the fog
    # telegraph poles along the near kerb, wires sagging from pole to pole and off into the fog
    region('near')
    rows = {}
    for x in (-48, -30, -10, 10, 30, 48):
        region('ends' if abs(x) > 20 else 'near')
        rows[x] = telegraph_pole(x, 9.5, arms=3 if abs(x) < 40 else 2)
    region('near')
    xs = sorted(rows)
    for a, b in zip(xs, xs[1:]):
        region('near' if abs(a + b) < 30 else 'ends')
        for k, (ra, rb) in enumerate(zip(rows[a], rows[b])):
            for pa, pb in zip(ra, rb):
                wire3(pa, pb, sag=0.55 + 0.12 * k, seg=8)
    region('near')
    # telephone drops from the poles to the fronts, and one pair right across the street
    for p, q in ((rows[-10][2][0], (-9.0, 8.9, 8.05)), (rows[10][2][0], (9.2, 7.6, 8.05)), (rows[10][1][3], (16.0, 9.6, 8.05)), (rows[-10][1][0], (-15.5, 9.2, 8.05))):
        wire3(p, q, sag=0.12, seg=5)
    wire3(rows[-10][0][3], (-11.0, 11.2, 21.95), sag=0.5, seg=10); wire3(rows[10][0][3], (8.5, 10.6, 21.95), sag=0.5, seg=10)
    # the fire-alarm box on the pole by the alley
    cbox(I4, 'hydrant_red', -10.13, -9.87, 1.5, 1.95, 9.62, 9.74, b=0.012)
    extrude(I4, 'hydrant_red', [(9.6, 1.95), (9.76, 1.95), (9.68, 2.05)], -10.15, -9.85)
    hydrant(5.7, 9.45)
    solid(5.5, 9.25, 5.9, 9.65, 0.9, 'hydrant')
    for x in (16.4, 18.2, 22.4, 24.2):
        hitching_post(x, 9.62)
    solid(16.3, 9.52, 24.3, 9.72, 1.1, 'hitching posts before the saloon (four, thin)')
    trough(19.2, 21.2, 9.98, 10.56)
    solid(19.1, 9.9, 21.75, 10.65, 1.0, 'horse trough and pump')
    # litter in the gutters
    rubbish(-6.5, 10.2, r=0.5, seed=31, n=6); rubbish(8.5, 10.15, r=0.4, seed=33, n=5); rubbish(3.0, 19.8, r=0.5, seed=35, n=6)
    rubbish(-15.0, 19.85, r=0.4, seed=37, n=5); rubbish(15.3, 10.2, r=0.4, seed=39, n=4)
    return lamps


def build():
    alley_materials()
    ground()
    lamp = alley()
    near_side()
    far_side()
    street_ends()
    lamps = furniture()
    return lamps + [lamp]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    lamps = build()
    root, tris = finish2('Burritt')
    # empties marking lamp glass, for the games' halos and lights
    for k, p in enumerate(lamps):
        e = bpy.data.objects.new(f'Lamp_{k}', None)
        bpy.context.scene.collection.objects.link(e)
        e.location = p
        e.parent = root
    os.makedirs(os.path.join(ROOT, 'art', 'set'), exist_ok=True)
    blend = os.path.join(ROOT, 'art', 'set', 'burritt.blend')
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    # the web's copy; tools/compress-models.mjs (npm run compress burritt) then makes the textures WebP at 1024
    bpy.ops.object.select_all(action='SELECT')
    glb = os.path.join(ROOT, 'public', 'models', 'burritt.glb')
    bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_image_format='JPEG', export_jpeg_quality=85, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=7, export_cameras=False, export_lights=False)
    print(f'burritt: {tris} triangles, {len(bpy.data.materials)} materials, {len(bpy.data.images)} images, '
          f'glb {os.path.getsize(glb) / 1048576:.2f} MB, blend {os.path.getsize(blend) / 1048576:.1f} MB')
    print('solid things the first set did not have (x0, z0, x1, z1, height):')
    for c in NEW_COLLIDERS: print('   ', c)
    if RENDER:
        import subprocess
        here = os.path.dirname(os.path.abspath(__file__))
        if bpy.app.binary_path:
            subprocess.run([bpy.app.binary_path, '-b', '--python', os.path.join(here, 'preview_set.py'), '--', RENDER])
        else:
            subprocess.run([sys.executable, os.path.join(here, 'preview_set.py'), '--', RENDER])


main()
