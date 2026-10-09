# Builds Brigid O'Shaughnessy's suite at the St. Mark Hotel for Chapter III: a smaller, plainer hotel than the
# Palace, and she is packing to leave.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_stmark.py -- [--render prefix]
#
# Writes art/set/stmark.blend, public/models/stmark.glb and public/models/stmark.json (colliders, lamps, named
# places, spawn). Game coordinates, Y up, metres: the sitting room is x -4.5..4.5, z -5..5, the door to the
# corridor at the south (z = 5), two tall windows over Ellis Street at the north (z = -5), the bedroom through a
# door at the south end of the east wall.
#
# Where the Palace is damask, gilt and marble, the St. Mark is respectable and no more: striped paper over a
# varnished pine dado, painted woodwork, a flat ceiling with one plaster rose, boards under the rug, lace at
# the windows, an iron bedstead. The hotel pieces (doors, corridor, the street outside) are build_palace's.
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_hopkins as bh
from build_hopkins import *  # noqa: F401,F403
from build_palace import paper, book, into_room, hotel_materials, door_leaf, corridor, street_view  # noqa: E402

H2 = 3.8
PLACES = {}
STM = dict(wains='pine_panel', upper='paper_stripe', trim='trim_cream', frieze='trim_cream', head=None, w_h=0.95)


def lace(F, t, w, ob, ot):
    """Lace panels hung in the window reveal, between the glass and the velvet (F's normal into the room)."""
    for s in (-1, 1):
        a, b = sorted((t + s * 0.03, t + s * (w / 2 + 0.05)))
        lbox(F, 'lace', a, b, ob + 0.02, ot - 0.02, -0.1, -0.095)
    lbox(F, 'brass', t - w / 2, t + w / 2, ot - 0.06, ot - 0.03, -0.11, -0.085)


def iron_bed(x, z, rot):
    """A japanned iron bedstead with brass knobs: made up smooth, not slept in."""
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, 'iron', -0.72, 0.72, 0.36, 0.42, -0.98, 1.0)
    lbox(F, 'canvas', -0.7, 0.7, 0.42, 0.62, -0.95, 0.98)                # mattress under a white counterpane
    lbox(F, 'canvas', -0.74, 0.74, 0.3, 0.6, 0.98, 1.0)                  # its fall at the foot
    lbox(F, 'china', -0.6, 0.6, 0.62, 0.76, -0.95, -0.6)                 # the bolster
    for w, top in ((-1.0, 1.25), (1.02, 0.95)):
        for u in (-0.74, 0.74):
            cyl('iron', F @ Vector((u, 0, w)), top, 0.025, seg=6)
            sphere('brass', F @ Vector((u, top + 0.03, w)), 0.04, 8)
        for v in (0.5, top - 0.05):
            tube('iron', [F @ Vector((-0.74, v, w)), F @ Vector((0.74, v, w))], 0.016, 5)
        for k in range(7):
            u = -0.6 + k * 0.2
            tube('iron', [F @ Vector((u, 0.5, w)), F @ Vector((u, top - 0.05, w))], 0.008, 4)
    collide_local(F, -0.78, 0.78, 0, 1.3, -1.05, 1.06)


def washstand(x, z, rot):
    F = Matrix.Translation((x, 0, z)) @ Matrix.Rotation(rot, 4, 'Y')
    lbox(F, 'pine_panel', -0.45, 0.45, 0, 0.76, -0.22, 0.22)
    lbox(F, 'marble_white', -0.48, 0.48, 0.76, 0.8, -0.24, 0.24)
    lbox(F, 'marble_white', -0.48, 0.48, 0.8, 1.05, -0.24, -0.21)        # the splashback
    cyl('china', F @ Vector((0, 0.8, 0.02)), 0.1, 0.18, 0.2, seg=16)     # basin
    cyl('china', F @ Vector((0.0, 0.85, 0.02)), 0.3, 0.09, 0.06, seg=12)  # the jug standing in it
    collide_local(F, -0.48, 0.48, 0, 0.9, -0.24, 0.24)


def build_suite():
    floor('boards', -4.5, 4.5, -5, 5)
    wbox('ceiling_plain', -4.5, 4.5, H2, H2 + 0.1, -5, 5)
    cyl('plaster_cast', (0, H2 - 0.05, 0), 0.05, 0.38, 0.28, seg=20)  # the one plaster rose
    spec = {
        'south': ((4.5, 5), (-4.5, 5), [(4.5, 1.4, 0, 2.7)]),             # the corridor door
        'east': ((4.5, -5), (4.5, 5), [(7.4, 1.5, 0, 2.7)]),              # the bedroom door
        'west': ((-4.5, 5), (-4.5, -5), []),
        'north': ((-4.5, -5), (4.5, -5), [(2.6, 1.3, 0.7, 3.1), (6.4, 1.3, 0.7, 3.1)]),  # the windows
    }
    for key, (a, b, ops) in spec.items():
        F, L = wall(a, b, 0, H2, ops, mat='plaster')
        side = into_room(F, L)
        lining(F, L, side, ops, H2, curtains='velvet_green' if key == 'north' else None, **STM)
        if key == 'south':
            lining(F, L, -side, ops, 3.2, **STM)
        for t, w, ob, ot in ops:
            if ob > 0.3:
                window_glass(F, t, w, ob, ot)
                Fs = F @ Matrix.Translation((L, 0, -T / 2)) @ Matrix.Rotation(math.pi, 4, 'Y') if side < 0 else \
                    F @ Matrix.Translation((0, 0, T / 2))
                lace(Fs, L - t if side < 0 else t, w, ob, ot)
    corridor(-4.5, 4.5, 5.0, 2.0, 3.2, 0.0, 'paper_stripe', 'pine_panel', 'trim_cream', 'velvet_green', None)
    door_leaf((-0.65, 4.7), (-0.985, -0.17), 1.3, 2.65, mat='door_wood')   # her door, left open
    # the bedroom beyond: the bed made and not slept in, the wardrobe standing open and empty
    PLACES['door'] = [0, 0, 4.4]
    PLACES['bedroom'] = [4.0, 1.4, 2.4]
    floor('boards', 4.675, 8.6, -1.3, 4.9)
    wbox('ceiling_plain', 4.675, 8.7, H2, H2 + 0.1, -1.3, 4.9)
    for a, b, ops in (((8.6, -1.3), (8.6, 4.9), [(2.2, 1.2, 0.8, 2.9)]), ((4.675, -1.2), (8.6, -1.2), []),
                      ((8.6, 4.8), (4.675, 4.8), [])):
        F, L = wall(a, b, 0, H2, ops, mat='plaster', solid=False)
        side = into_room(F, L, Vector((6.6, 0, 1.8)))
        lining(F, L, side, ops, H2, curtains='velvet_green' if ops else None, **STM)
        for t, w, ob, ot in ops:
            window_glass(F, t, w, ob, ot)
            canvas('view_sky', [F @ Vector(p) for p in ((t - w, ob - 0.5, -side * 0.6), (t + w, ob - 0.5, -side * 0.6),
                                                        (t + w, ot + 0.5, -side * 0.6), (t - w, ot + 0.5, -side * 0.6))])  # an airshaft
    door_leaf((4.72, 3.1), (0.94, -0.34), 1.4, 2.65, mat='door_wood')     # the bedroom door, ajar
    iron_bed(7.4, 3.3, -math.pi / 2)
    washstand(8.3, -0.3, -math.pi / 2)
    cabinet(6.0, -0.9, 0.0, w=1.1, mat='pine_panel')
    for s in (-1, 1):
        door_leaf((6.0 + s * 0.55, -0.6), (s * 0.5, 0.87), 0.52, 1.85, mat='pine_panel', thick=0.03)
    pedestal_table(8.2, 1.6, lamp=True, r=0.28)
    LAMPS.append([8.2, 1.2, 1.6])
    collide(4.7, 0, -1.4, 8.7, H2, 4.9)


def furnish_suite():
    # the fireplace on the west wall, a sofa facing it, a low table between
    fireplace(frame((-4.5 + T / 2, 0, 0), (0, 0, 1), (1, 0, 0)), 0.0, mat='marble_black', w=1.6, h=1.2)
    rug(-3.2, 1.6, -2.4, 2.4, 3)
    sofa(-0.4, 0.2, -math.pi / 2, 'velvet_green', 2.0)
    wingback(-2.6, -2.0, facing(-2.6, -2.0, -4.2, 0), 'velvet_red')
    table(-1.8, 0.2, 0.9, 0.55, h=0.48, mat='walnut_panel')
    collide(-2.25, 0, -0.08, -1.35, 0.5, 0.48)
    # on the table, the morning paper (Thursby), and her gloves laid beside it
    paper(-1.95, 0.1, 0.4, 0.34)
    for k in range(2):
        lbox(Matrix.Translation((-1.55, 0.48, 0.32 + k * 0.07)) @ Matrix.Rotation(0.3, 4, 'Y'), 'velvet_blue',
             -0.04, 0.04, 0, 0.012, -0.11, 0.11)
    PLACES['paper'] = [-1.8, 0.6, 0.2]
    # the grate: something burnt in it this morning, a scrap of newsprint not quite gone
    for k in range(5):
        paper(-4.05 + (k % 2) * 0.12, -0.2 + k * 0.09, k * 1.3, 0.08)
    PLACES['grate'] = [-4.0, 0.4, 0.0]
    # her walking boots set to dry on the fender: street mud caked to the ankle
    for dz in (-0.55, -0.4):
        F = Matrix.Translation((-3.75, 0, dz)) @ Matrix.Rotation(0.2, 4, 'Y')
        lbox(F, 'iron', -0.05, 0.05, 0, 0.04, -0.13, 0.12)          # sole, black with mud
        lbox(F, 'leather_black', -0.045, 0.045, 0.04, 0.2, -0.06, 0.05)  # shaft
        lbox(F, 'leather_black', -0.045, 0.045, 0.04, 0.09, 0.05, 0.12)  # toe
    PLACES['boots'] = [-3.75, 0.3, -0.5]
    for z in (-1.4, 1.4):  # gas brackets either side of the chimney-breast
        sconce(frame((-4.5 + T / 2 + 0.03, 0, z), (0, 0, 1), (1, 0, 0)), 0.0, 1.8)
        LAMPS.append([-3.6, 2.0, z])  # out from the wall, or the light is a hot spot on the paper
    # the writing desk against the east wall: letters, a hotel bill, its lamp
    F = Matrix.Translation((3.6, 0, -2.2)) @ Matrix.Rotation(-math.pi / 2, 4, 'Y')
    lbox(F, 'rosewood_panel', -0.6, 0.6, 0.72, 0.77, -0.3, 0.3)
    for s in (-1, 1):
        lbox(F, 'rosewood_panel', min(s * 0.55, s * 0.6), max(s * 0.55, s * 0.6), 0, 0.72, -0.28, 0.28)
    lbox(F, 'rosewood_panel', -0.6, 0.6, 0.77, 1.05, 0.2, 0.3)       # a low gallery of pigeonholes
    for k in range(5):
        lbox(F, 'canvas', -0.5 + k * 0.22, -0.4 + k * 0.22, 0.8, 0.95, 0.21, 0.27)  # letters in the pigeonholes
    cyl('brass', F @ Vector((-0.45, 0.77, 0.05)), 0.24, 0.05, 0.03, seg=10)     # an oil lamp
    sphere('lamp_glass', F @ Vector((-0.45, 1.08, 0.05)), 0.075, 10)
    p = F @ Vector((-0.45, 1.1, 0.05)); LAMPS.append([round(p.x, 3), 1.15, round(p.z, 3)])
    collide(3.25, 0, -2.85, 3.95, 0.8, -1.55)
    chair(2.9, -2.2, math.pi / 2, 'velvet_green')
    for k in range(4):
        paper(3.55 + (k % 2) * 0.12, -2.45 + k * 0.15, 0.2 + k * 0.4, 0.16)
    PLACES['desk'] = [3.6, 0.9, -2.2]
    frame_painting(frame((4.5 - T / 2, 0, -2.2), (0, 0, 1), (-1, 0, 0)), 0.0, 1.45, 0.8, 0.6, 9)
    # the steamer trunk, lid up, half packed, in the middle of the floor by the bedroom door
    F = Matrix.Translation((2.4, 0, 1.6)) @ Matrix.Rotation(0.25, 4, 'Y')
    lbox(F, 'leather_black', -0.5, 0.5, 0, 0.6, -0.3, 0.3)
    lbox(F, 'canvas', -0.46, 0.46, 0.4, 0.59, -0.26, 0.26)            # linen folded inside
    G = F @ Matrix.Translation((0, 0.6, 0.3)) @ Matrix.Rotation(-1.75, 4, 'X')
    lbox(G, 'leather_black', -0.5, 0.5, 0, 0.08, 0, 0.6)               # the lid, thrown back
    lbox(G, 'velvet_blue', -0.46, 0.46, 0.08, 0.09, 0.04, 0.56)        # its quilted lining
    for u in (-0.42, 0.42):
        lbox(F, 'brass', u - 0.03, u + 0.03, 0, 0.6, -0.31, 0.31)
    lbox(F, 'brass', -0.06, 0.06, 0.45, 0.58, 0.3, 0.32)               # the lock
    paper(2.25, 1.32, 0.25, 0.14)                                       # the steamer label, pasted on the end
    collide(1.8, 0, 1.15, 3.0, 0.7, 2.1)
    PLACES['trunk'] = [2.4, 0.7, 1.6]
    # a hatbox and a carpet bag by the door: she meant to be gone by noon
    cyl('canvas', (3.2, 0, 3.8), 0.32, 0.22, seg=16)
    cyl('velvet_blue', (3.2, 0.32, 3.8), 0.02, 0.225, seg=16)
    lbox(Matrix.Translation((2.4, 0, 4.0)), 'velvet_red', -0.3, 0.3, 0, 0.35, -0.12, 0.12)
    tube('brass', [(2.2, 0.35, 4.0), (2.3, 0.5, 4.0), (2.5, 0.5, 4.0), (2.6, 0.35, 4.0)], 0.012, 5)
    collide(2.05, 0, 3.55, 3.45, 0.4, 4.15)
    # her cloak on the stand by the door
    cyl('iron', (-3.6, 0, 4.3), 0.04, 0.25, seg=8)
    cyl('walnut_panel', (-3.6, 0, 4.3), 1.85, 0.03, seg=6)
    for k in range(4):
        a = k * math.pi / 2
        tube('brass', [(-3.6, 1.75, 4.3), (-3.6 + math.cos(a) * 0.15, 1.82, 4.3 + math.sin(a) * 0.15)], 0.012, 4)
    cyl('velvet_blue', (-3.6, 0.55, 4.3), 1.2, 0.3, 0.1, seg=10)
    collide(-3.85, 0, 4.05, -3.35, 1.9, 4.55)
    # breakfast sent up and hardly touched, on a small table by the window
    pedestal_table(2.7, -4.1, lamp=False, r=0.32)
    cyl('brass', (2.7, 0.72, -4.1), 0.015, 0.26, seg=16)
    cyl('china', (2.62, 0.735, -4.15), 0.16, 0.06, 0.045, seg=10)     # the teapot
    sphere('china', (2.62, 0.9, -4.15), 0.03, 6)
    for (dx, dz) in ((0.12, 0.08), (-0.05, 0.14)):
        cyl('china', (2.7 + dx, 0.735, -4.1 + dz), 0.05, 0.035, 0.04, seg=8)
    # a pier glass between the windows, a fern, a small gasolier
    F = frame((0, 0, -5 + T / 2), (1, 0, 0), (0, 0, 1))  # (it stood out from the wall edge-on, like a plank)
    lbox(F, 'gilt_frame', -0.42, 0.42, 0.5, 2.9, 0, 0.05)
    lbox(F, 'mirror', -0.36, 0.36, 0.56, 2.84, 0.05, 0.06)
    fern(-3.9, -4.4, 0.9)
    gasolier(0, H2 - 0.05, 0, arms=4, drop=1.0, r=0.5)
    frame_painting(frame((4.5 - T / 2, 0, -4.2), (0, 0, 1), (-1, 0, 0)), 0.0, 1.5, 0.5, 0.6, 3)
    PLACES['window'] = [-1.9, 1.6, -5.0]
    PLACES['brigid'] = [-1.6, 0, -3.6]
    # Ellis Street below: the St. Mark's rooms are on the second floor; across the way, wooden flats and a shop.
    # The cab waiting at the far kerb is the one Holmes remarks on.
    street_view('ellis', -24.0, -5.4, -30.0, 30.0, -5.2, seed=3)
    from build_city import hack
    hack(-2.5, -21.2, math.pi / 2, y=-5.2)
    lbox(Matrix.Translation((-2.5, -5.2 + 2.07, -21.2)), 'leather_black', -0.5, 0.5, 0, 0.35, -0.4, 0.4)  # a trunk strapped on top


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hopkins_materials()
    interior_materials()
    hotel_materials()
    t, n = wood_tex('boards', '#4e3622', planks=7); material('boards', tex=t, nrm=n, rough=0.55, scale=1.4)
    material('velvet_blue', '#22305a', rough=0.95)
    build_suite()
    furnish_suite()
    root = finish('StMark')
    for k, p in enumerate(bh.LAMPS):
        e = bpy.data.objects.new(f'Lamp_{k}', None)
        bpy.context.scene.collection.objects.link(e)
        e.location = p; e.parent = root
    os.makedirs(os.path.join(ROOT, 'art', 'set'), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, 'art', 'set', 'stmark.blend'))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, 'public', 'models', 'stmark.glb'), export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True, export_image_format='JPEG',
                              export_jpeg_quality=85, export_draco_mesh_compression_enable=True,
                              export_draco_mesh_compression_level=7, export_cameras=False, export_lights=False)
    with open(os.path.join(ROOT, 'public', 'models', 'stmark.json'), 'w') as f:
        json.dump(dict(colliders=bh.COLLIDERS, lamps=[[round(v, 3) for v in p] for p in bh.LAMPS], places=PLACES,
                       spawn=dict(pos=[0.3, 0, 1.6], yaw=math.pi)), f, separators=(',', ':'))
    if RENDER: preview(RENDER)


def preview(path):
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.world = bpy.data.worlds.new('W'); sc.world.color = (0.03, 0.035, 0.05)
    for k, (x, y, z) in enumerate(bh.LAMPS):
        l = bpy.data.objects.new(f'L{k}', bpy.data.lights.new(f'L{k}', 'POINT'))
        l.data.energy = 200; l.data.color = (1, 0.72, 0.42); l.location = (x, -z, y)
        sc.collection.objects.link(l)
    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 18
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    for tag, eye, look in (('room', (0.5, 1.7, 4.4), (-0.5, 1.2, -4)), ('fire', (2.5, 1.6, 2.5), (-4, 0.8, -0.5))):
        e = Vector((eye[0], -eye[2], eye[1])); t = Vector((look[0], -look[2], look[1]))
        cam.location = e; cam.rotation_euler = (t - e).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f'{path}_{tag}.png'
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
