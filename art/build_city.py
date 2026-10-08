# Builds Kearny Street for Chapter V: three blocks from Market Street north to Bush, in fog.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_city.py -- [--render prefix]
#
# Writes art/set/kearny.blend, public/models/kearny.glb and public/models/kearny.json (colliders, lamps,
# cover points, the spawn and the places the chapter uses). Game coordinates: Y up, metres. Kearny runs
# along -z from Market Street (z = 8) to Bush Street (z = -205); the roadway is x = -7..7, sidewalks to
# x = ±11, the building faces at x = ±11. Cross streets: Post (z = -55..-70), Sutter (z = -125..-140).
# The Palace Hotel stands on the south-west corner; the Alexandria (Hammett's hotel for Gutman, invented
# here as a building) at the north end on the east side.
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from setkit import *  # noqa: F401,F403

COLLIDERS, LAMPS, COVER, PLACES = [], [], [], {}
FACE = 11.0          # building faces
ROAD = 7.0           # kerb line
BLOCKS = [(8, -55), (-70, -125), (-140, -205)]   # z ranges of the three blocks (north is -z)


def collide(x0, y0, z0, x1, y1, z1):
    COLLIDERS.append([round(min(x0, x1), 3), round(min(y0, y1), 3), round(min(z0, z1), 3),
                      round(max(x0, x1), 3), round(max(y0, y1), 3), round(max(z0, z1), 3)])


def cover(x, z, kind):
    COVER.append([round(x, 2), round(z, 2), kind])


def city_materials():
    make_materials()
    t, n = stone_tex('granite_kerb', '#6a6a66'); material('granite', tex=t, nrm=n, rough=0.8, scale=2.0)
    t, n = stone_tex('flags', '#5e5a52'); material('flags', tex=t, nrm=n, rough=0.85, scale=1.6)
    material('asphalt', '#2a2724', rough=0.6)
    t, n = brick_tex('brick_dark', '#4a2e24', soot=0.5); material('brick_dark', tex=t, nrm=n, rough=0.9, scale=1.0)
    t, n = stone_tex('sandstone', '#a89874'); material('sandstone', tex=t, nrm=n, rough=0.85, scale=2.5)
    material('carriage_black', '#0c0c0e', rough=0.25, metal=0.2)
    material('awning', '#3a1a16', rough=0.95)
    material('awning_green', '#1e3426', rough=0.95)
    material('brass', '#b8903e', rough=0.3, metal=0.9)
    material('velvet_red', '#5a1014', rough=0.95)
    material('cablecar_red', '#5a1a14', rough=0.5)
    material('cablecar_cream', '#cbbf9a', rough=0.6)


def street_surface():
    z0, z1 = BLOCKS[0][0] + 10, BLOCKS[-1][1] - 15
    wbox('asphalt', -ROAD, ROAD, -0.2, -0.15, z1, z0)          # the roadway, worn wood-block paving
    for s in (-1, 1):
        wbox('flags', min(s * ROAD, s * FACE), max(s * ROAD, s * FACE), -0.15, 0.0, z1, z0)
        wbox('granite', min(s * ROAD, s * (ROAD + 0.3)), max(s * ROAD, s * (ROAD + 0.3)), -0.2, 0.0, z1, z0)
    for z in (-3.0,):  # a horse-car track down the middle (Kearny had horse cars)
        for x in (-0.75, 0.75):
            wbox('iron', x - 0.04, x + 0.04, -0.15, -0.13, z1, z0)
    # cross streets, running off into the fog either side
    for (a, b) in ((-55, -70), (-125, -140)):
        for s in (-1, 1):
            wbox('asphalt', min(s * FACE, s * 40), max(s * FACE, s * 40), -0.2, -0.15, b, a)
            wbox('flags', min(s * FACE, s * 40), max(s * FACE, s * 40), -0.15, 0.0, a - 4, a)
            wbox('flags', min(s * FACE, s * 40), max(s * FACE, s * 40), -0.15, 0.0, b, b + 4)
            collide(s * 30, 0, b, s * 31, 4, a)                 # the fog closes off the cross streets
    # the Sutter Street cable line crosses Kearny: rails and the cable slot between them
    for x0, x1 in ((-120, 120),):
        for z in (-131.0, -132.5, -134.0):
            if z == -132.5: wbox('roof', x0, x1, -0.15, -0.14, z - 0.015, z + 0.015)
            else: wbox('iron', x0, x1, -0.15, -0.13, z - 0.04, z + 0.04)
    collide(-FACE, 0, z0 - 0.5, FACE, 4, z0)                    # Market Street end
    collide(-FACE, 0, z1, FACE, 4, z1 + 0.5)                    # Bush Street end


SIGNS_W = ['GUMP\'S · ART GOODS', 'WESTERN UNION TELEGRAPH', 'MILLINERY', 'OYSTER GROTTO', 'CIGARS · TOBACCO',
           'THE WHITE HOUSE · DRY GOODS', 'O\'FARRELL\'S SALOON']
SIGNS_E = ['NEWS DEPOT', 'J. W. TUCKER · JEWELLER', 'BAKERY & CONFECTIONERY', 'SHREVE & CO.', 'TURKISH BATHS', 'HATTER',
           'BOOKS & STATIONERY']


def block_fronts():
    """Each side of each block: three or four fronts of different heights, walls and trims."""
    walls = ['brick_red', 'brick_brown', 'brick_tan', 'clap_cream', 'brick_dark', 'clap_grey', 'sandstone', 'clap_sage']
    trims = ['trim_cream', 'trim_dark', 'trim_cream', 'trim_maroon']
    w_i = e_i = 0
    for bi, (za, zb) in enumerate(BLOCKS):
        for side in (-1, 1):
            # frame: faces the street; u runs north (toward -z)
            F = frame((side * FACE, 0, za), (0, 0, -1), (-side, 0, 0)) if side < 0 else \
                frame((side * FACE, 0, zb), (0, 0, 1), (-side, 0, 0))
            L = za - zb
            # the Palace Hotel takes the whole first block on the west; the Alexandria the last on the east
            if bi == 0 and side < 0:
                grand_front(F, 0, L, 'THE PALACE HOTEL', 'sandstone', floors=6)
                wbox('sandstone', -FACE - 30, -FACE, 0, 26, zb, za)
                PLACES['palace'] = [-FACE + 1.5, 0, za - 10]
                continue
            if bi == 2 and side > 0:
                grand_front(F, 0, L, 'THE ALEXANDRIA', 'brick_tan', floors=5)
                wbox('brick_tan', FACE, FACE + 30, 0, 22, zb, za)
                door = F @ Vector((L / 2, 0, 0))
                PLACES['alexandria'] = [round(door.x - 2.2, 2), 0, round(door.z, 2)]
                continue
            cuts = [0, L * 0.3, L * 0.55, L * 0.8, L] if (bi + side) % 2 else [0, L * 0.35, L * 0.7, L]
            for a, b in zip(cuts, cuts[1:]):
                h = [9, 12, 10, 14, 8, 11][(w_i + e_i + int(a)) % 6]
                wall = walls[(w_i * 3 + e_i + bi) % len(walls)]
                trim = trims[(w_i + e_i) % len(trims)]
                sign = (SIGNS_W if side < 0 else SIGNS_E)[(w_i if side < 0 else e_i) % 7]
                if side < 0: w_i += 1
                else: e_i += 1
                floors = tuple(f for f in (4.6, 7.8, 11.0) if f < h - 2)
                bays = (a + (b - a) / 2,) if b - a > 12 and h > 9 else ()
                front(F, a + 0.15, b - 0.15, h, wall, trim, sign, bays=bays, floors=floors or (4.6,),
                      sign_mat='sign_board_red' if (w_i + e_i) % 3 == 0 else 'sign_board')
                x_back = side * (FACE + 20)
                p0, p1 = F @ Vector((a, 0, 0)), F @ Vector((b, 0, 0))
                wbox(wall, min(side * FACE, x_back), max(side * FACE, x_back), 0, h, min(p0.z, p1.z), max(p0.z, p1.z))
                # every shop door is a recess you can stand in: cover
                n = max(2, int((b - a) / 3.2)); bw = (b - a) / n
                d = F @ Vector((a + (int(n * 0.5) + 0.5) * bw, 0, 0.2))
                cover(d.x, d.z, 'doorway')
                PLACES[sign] = [round(d.x, 2), 0, round(d.z, 2)]  # where its door is
                # awnings over some shops
                if (w_i + e_i) % 2 == 0:
                    lbox(F, 'awning' if (w_i + e_i) % 4 else 'awning_green', a + 0.6, b - 0.6, 3.0, 3.1, 0.3, 2.2)
                    for u in (a + 0.8, b - 0.8):
                        tube('iron', [F @ Vector((u, 0, 2.15)), F @ Vector((u, 3.0, 2.15))], 0.025, 6)
            collide(min(side * FACE, side * (FACE + 20)), 0, zb, max(side * FACE, side * (FACE + 20)), 20, za)


def grand_front(F, u0, u1, name, wall, floors=6):
    """A big hotel front: a rusticated ground floor, a pillared entrance with a canopy, rows of windows."""
    h = 4.5 + floors * 3.4
    lbox(F, wall, u0, u1, 0, h, -0.3, 0)
    lbox(F, 'trim_cream', u0, u1, 0, 4.4, 0, 0.12)
    for v in np.arange(0.5, 4.4, 0.55):
        lbox(F, 'trim_dark', u0, u1, v, v + 0.04, 0.12, 0.13)
    c = (u0 + u1) / 2
    # the entrance: glazed doors between columns, a canopy, the name in gilt
    lbox(F, 'glass_lit0', c - 2.5, c + 2.5, 0.2, 3.6, 0.13, 0.15)
    for k in (-1, 1):
        for d in (2.9, 3.6):
            cyl('trim_cream', F @ Vector((c + k * d, 0, 0.6)), 4.3, 0.22, seg=12)
    lbox(F, 'trim_dark', c - 4.2, c + 4.2, 4.3, 4.6, 0, 3.4)
    for k in (-1, 1):
        tube('brass', [F @ Vector((c + k * 4.0, 4.3, 3.3)), F @ Vector((c + k * 4.0, 0, 3.3))], 0.04, 8)
    text('gilt', name, F, c, 5.2, 0.15, 0.75)
    for k in (-1, 1):
        p = F @ Vector((c + k * 3.6, 3.6, 1.2))
        cyl('lamp_glass', p, 0.4, 0.15, 0.2, seg=8)
        LAMPS.append([round(p.x, 2), round(p.y + 0.2, 2), round(p.z, 2)])
    cover((F @ Vector((c, 0, 0.6))).x, (F @ Vector((c, 0, 0.6))).z, 'doorway')
    # windows: plenty of them, some lit
    for f in range(floors):
        v = 5.4 + f * 3.4
        n = int((u1 - u0) / 2.4)
        for k in range(n):
            u = u0 + (k + 0.5) * (u1 - u0) / n
            if abs(u - c) < 1.5 and f == 0: continue
            window(F, u, v, w=1.0, h=2.0, frame_mat='trim_cream', hood='cornice' if f % 2 == 0 else 'lintel')
        lbox(F, 'trim_cream', u0, u1, v - 0.5, v - 0.36, 0, 0.12)
    cornice(F, u0, u1, h, 'trim_cream', depth=0.8)


SUTTER_RUN = 112


def sutter_view():
    """Sutter Street running away from Kearny either way, so you can look down it: fronts on both sides, paving,
    lamps, fading into the fog. You can walk only a little way down it; the cable car runs its length."""
    za, zb = -125, -140
    walls = ['brick_red', 'clap_cream', 'brick_brown', 'clap_grey', 'brick_tan', 'clap_sage']
    k = 0
    for side in (-1, 1):
        x = side * FACE
        while abs(x) < SUTTER_RUN:
            w = 14 + (k * 7) % 9
            x1 = x + side * w
            h = [9, 12, 8, 11, 10][k % 5]
            wall, trim = walls[k % len(walls)], ['trim_cream', 'trim_dark'][k % 2]
            # the block south of Sutter (z > -125) faces -z onto it; the block north (z < -140) faces +z.
            # (r x up must equal the outward normal, or the front comes out mirrored.)
            for zf, facing in ((za, -1), (zb, 1)):
                if facing < 0:
                    F = frame((max(x, x1), 0, zf), (-1, 0, 0), (0, 0, -1))
                    wbox(wall, min(x, x1), max(x, x1), 0, h, zf, zf + 12)
                else:
                    F = frame((min(x, x1), 0, zf), (1, 0, 0), (0, 0, 1))
                    wbox(wall, min(x, x1), max(x, x1), 0, h, zf - 12, zf)
                front(F, 0.1, w - 0.1, h, wall, trim, '', floors=tuple(f for f in (4.6, 7.8) if f < h - 2))
            if k % 2 == 0:
                for zl in (za - 0.6, zb + 0.6):
                    LAMPS.append(list(gas_lamp((x + x1) / 2, zl)))
            x = x1; k += 1
    for s_ in (-1, 1):
        wbox('asphalt', min(s_ * 40, s_ * (SUTTER_RUN + 10)), max(s_ * 40, s_ * (SUTTER_RUN + 10)), -0.2, -0.15, zb, za)
        for zf in (za, zb):
            wbox('flags', min(s_ * 40, s_ * (SUTTER_RUN + 10)), max(s_ * 40, s_ * (SUTTER_RUN + 10)), -0.15, 0.0,
                 zf - 0.01 if zf == za else zf, zf + 0.01 if zf == zb else zf)
    PLACES['sutter'] = [ROAD + 2.0, 0, za - 2.6]  # on the Sutter Street sidewalk, at the corner


def street_furniture():
    # gas lamps along both kerbs every 16 m; telegraph poles; hitching posts; a cab rank; newspaper boxes
    for (za, zb) in BLOCKS:
        z = za - 4
        while z > zb + 2:
            for s in (-1, 1):
                x = s * (ROAD + 0.7)
                LAMPS.append(list(gas_lamp(x, z)))
                collide(x - 0.2, 0, z - 0.2, x + 0.2, 3.5, z + 0.2)
                cover(x - s * 0.2, z, 'lamp')
            z -= 16
    for (za, zb) in BLOCKS:
        for z in (za - 12, zb + 14):
            cyl('door_wood', (-ROAD - 0.4, 0, z), 9, 0.14, 0.1, seg=8)
            wbox('door_wood', -ROAD - 1.4, -ROAD + 0.6, 8.3, 8.45, z - 0.07, z + 0.07)
            collide(-ROAD - 0.6, 0, z - 0.2, -ROAD - 0.2, 9, z + 0.2)
            cover(-ROAD - 0.1, z, 'pole')
    for (za, zb) in BLOCKS:  # wires along the west side, sagging between poles
        wire((-ROAD - 1.2, 8.3, za - 12), (-ROAD - 1.2, 8.3, zb + 14), sag=1.2, seg=16)
    # two hacks waiting at a stand on the east side of the second block, and one parked on the first
    for (z, rot) in ((-82, 0.0), (-92, 0.0), (-20, math.pi)):
        hack(ROAD - 1.4, z, rot)
        cover(ROAD - 3.0, z, 'cab')
    # newspaper boxes and a fire alarm box
    for z in (-30, -100, -160):
        wbox('trim_dark', ROAD + 1.5, ROAD + 2.1, 0, 1.1, z - 0.3, z + 0.3)
        collide(ROAD + 1.5, 0, z - 0.3, ROAD + 2.1, 1.1, z + 0.3)
    PLACES['jeweller'] = jeweller_window()


def hack(x, z, rot):
    """A one-horse hansom-style cab, waiting (the horses are left to the imagination of the fog)."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, 'carriage_black', -0.65, 0.65, 0.75, 2.0, -0.8, 0.7)
    lbox(F, 'carriage_black', -0.7, 0.7, 2.0, 2.07, -0.85, 0.75)
    lbox(F, 'carriage_black', -0.4, 0.4, 2.07, 2.6, 0.5, 0.9)              # the driver's perch behind
    for s in (-1, 1):
        lbox(F, 'glass_lit2', s * 0.66 - 0.005, s * 0.66 + 0.005, 1.3, 1.8, -0.6, 0.0)
        c = F @ Vector((s * 0.78, 0.7, 0.1))
        ax = (F.to_3x3() @ Vector((1, 0, 0))).normalized()
        pts = [c + (F.to_3x3() @ Vector((0, math.sin(t) * 0.7, math.cos(t) * 0.7))) for t in np.linspace(0, 2 * math.pi, 19)]
        tube('carriage_black', pts, 0.03, 4)
        for t in np.linspace(0, math.pi, 7)[:-1]:
            d = F.to_3x3() @ Vector((0, math.sin(t) * 0.7, math.cos(t) * 0.7))
            tube('carriage_black', [c - d, c + d], 0.012, 4)
        p = F @ Vector((s * 0.7, 1.7, -0.75))
        cyl('lamp_glass', p, 0.18, 0.06, 0.07, seg=6)
    for s in (-0.25, 0.25):
        tube('carriage_black', [F @ Vector((s, 0.6, -0.8)), F @ Vector((s * 1.2, 0.5, -3.2))], 0.035)
    lo, hi = F @ Vector((-0.9, 0, -1.0)), F @ Vector((0.9, 2.6, 1.0))
    collide(min(lo.x, hi.x), 0, min(lo.z, hi.z), max(lo.x, hi.x), 2.6, max(lo.z, hi.z))


def jeweller_window():
    """The jeweller's plate glass on the west side of the first block, with a lamp behind it: the window Holmes
    watches the street in. Returns where to stand."""
    z = -21.5  # beside the jeweller's door, east side of the first block, across from the Palace
    wbox('glass_lit1', FACE - 0.21, FACE - 0.18, 0.7, 2.6, z - 1.6, z + 1.6)
    for k in range(3):  # trays of rings and watches on velvet in the window
        wbox('velvet_red', FACE - 0.8, FACE - 0.22, 0.7 + k * 0.5, 0.74 + k * 0.5, z - 1.4, z + 1.4)
        for j in range(8):
            sphere('gilt', (FACE - 0.5, 0.78 + k * 0.5, z - 1.2 + j * 0.34), 0.03, 6)
    return [FACE - 1.6, 0, z]


SUTTER_Z = -132.5


def cable_car():
    """A Sutter Street cable car (a grip car, open at the ends, closed in the middle), built at the origin facing +x.
    It is its own object, 'CableCar', which the game runs along Sutter Street."""
    L, W = 8.0, 2.5
    wbox('cablecar_red', -L / 2, L / 2, 0.55, 1.15, -W / 2, W / 2)                 # the body, red below
    wbox('cablecar_cream', -L / 2 + 1.6, L / 2 - 1.6, 1.15, 2.6, -W / 2 + 0.05, W / 2 - 0.05)
    for k in range(6):  # windows of the closed saloon
        x = -L / 2 + 2.0 + k * (L - 4.0) / 5
        for s_ in (-1, 1):
            wbox('glass_lit0' if k % 2 else 'glass_lit1', x - 0.3, x + 0.3, 1.4, 2.25, s_ * (W / 2 - 0.04) - 0.01, s_ * (W / 2 - 0.04) + 0.01)
    for s_ in (-1, 1):  # open end sections: benches facing out, posts, a running board
        xa, xb = s_ * (L / 2 - 1.6), s_ * L / 2
        wbox('door_wood', min(xa, xb), max(xa, xb), 1.15, 1.22, -W / 2 + 0.2, W / 2 - 0.2)
        for z in (-W / 2 + 0.08, W / 2 - 0.08):
            for x in (xa, (xa + xb) / 2, xb):
                tube('iron', [(x, 1.15, z), (x, 2.75, z)], 0.025, 6)
        wbox('door_wood', min(xa, xb), max(xa, xb), 0.45, 0.5, -W / 2 - 0.25, W / 2 + 0.25)
    wbox('cablecar_red', -L / 2 - 0.15, L / 2 + 0.15, 2.6, 2.75, -W / 2 - 0.12, W / 2 + 0.12)   # roof
    wbox('cablecar_cream', -L / 2 + 1.0, L / 2 - 1.0, 2.75, 2.95, -0.6, 0.6)                    # clerestory
    for s_ in (-1, 1):
        for x in (-L / 2 + 1.1, L / 2 - 1.1):
            cyl('iron', (x, 0.35, s_ * 0.8), 0.12, 0.35, seg=12, axis=(0, 0, 1))
    tube('iron', [(0.4, 0.5, 0), (0.4, 1.9, 0)], 0.04)                                   # the grip lever
    sphere('brass', (0.4, 1.95, 0), 0.06, 8)
    for s_ in (-1, 1):  # headlamps at both ends, and the bell
        cyl('lamp_glass', (s_ * (L / 2 + 0.05), 2.0, 0), 0.2, 0.12, axis=(1, 0, 0), seg=10)
    sphere('brass', (0.0, 2.85, 0), 0.12, 10)
    F = frame((-1.6, 1.85, W / 2 - 0.04), (1, 0, 0), (0, 0, 1))
    text('gilt', 'SUTTER ST.', F, 0, 0, 0.0, 0.3)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    city_materials()
    street_surface()
    block_fronts()
    sutter_view()
    street_furniture()
    root = finish('Kearny')
    import setkit
    setkit.BM.clear()  # the street is done; the cable car is a separate object the game moves
    cable_car()
    car = finish('CableCar')
    car.location = (-SUTTER_RUN, -SUTTER_Z, 0)  # parked at the west end of its run (Blender: y = -z)
    for k, p in enumerate(LAMPS):
        e = bpy.data.objects.new(f'Lamp_{k}', None)
        bpy.context.scene.collection.objects.link(e)
        e.location = p; e.parent = root
    os.makedirs(os.path.join(ROOT, 'art', 'set'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'art', 'set', 'kearny.blend'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', 'kearny.glb'), export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True, export_image_format='JPEG',
                              export_jpeg_quality=85, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=7, export_cameras=False, export_lights=False)
    with open(os.path.join(ROOT, 'public', 'models', 'kearny.json'), 'w') as f:
        json.dump(dict(colliders=COLLIDERS, lamps=[[round(v, 3) for v in p] for p in LAMPS], cover=COVER,
                       places=PLACES, spawn=dict(pos=[-8.6, 0, -2.0], yaw=0.0),
                       cablecar=dict(z=SUTTER_Z, x0=-SUTTER_RUN, x1=SUTTER_RUN, speed=4.5, period=75, length=8.0, width=2.5)),
                  f, separators=(',', ':'))
    if RENDER: preview(RENDER)


def preview(path):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.world = bpy.data.worlds.new('W'); sc.world.color = (0.06, 0.07, 0.09)
    for k, (x, y, z) in enumerate(LAMPS[::3]):
        l = bpy.data.objects.new(f'L{k}', bpy.data.lights.new(f'L{k}', 'POINT'))
        l.data.energy = 300; l.data.color = (1, 0.72, 0.42); l.location = (x, -z, y)
        sc.collection.objects.link(l)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 24
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    for tag, eye, look in (('south', (0, 1.7, 2), (0, 3, -40)), ('alex', (0, 1.7, -150), (10, 5, -172)),
                           ('sutter', (9.0, 1.7, -127.6), (70, 2.5, -133))):
        e = Vector((eye[0], -eye[2], eye[1])); t = Vector((look[0], -look[2], look[1]))
        cam.location = e; cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f'{path}_{tag}.png'
        bpy.ops.render.render(write_still=True)


main()
