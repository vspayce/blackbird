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


def build_suite():
    # floor, ceiling, and the walls with their openings: (t from the wall's start, width, bottom, top)
    floor('parquet', -5, 5, -6, 6)
    coffered_ceiling(-5, 5, -6, 6, H2, beam='trim_cream', field='fresco_louis', step=1.7)
    ceiling_bosses(-5, 5, -6, 6, H2, step=1.7)
    spec = {
        'south': ((5, 6), (-5, 6), [(5, 1.6, 0, 3.0)]),                                    # the corridor door
        'east': ((5, -6), (5, 6), [(8.5, 1.8, 0, 3.0)]),                                   # the bedroom door
        'west': ((-5, 6), (-5, -6), []),
        'north': ((-5, -6), (5, -6), [(1.3, 1.1, 0.8, 3.2), (5, 4.0, 0, H2 - 0.6), (8.7, 1.1, 0.8, 3.2)]),  # windows, the bay
    }
    for key, (a, b, ops) in spec.items():
        F, L = wall(a, b, 0, H2, ops, mat='plaster')
        side = into_room(F, L)
        lining(F, L, side, ops, H2, wains='oak_panel', upper='fresco_louis', curtains='velvet_red' if key == 'north' else None)
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
        lining(F, L, into_room(F, L), op, H2 - 0.6, wains='oak_panel', upper='fresco_louis', curtains='velvet_red')
    floor('parquet', -2.0, 2.0, -6 - bay_out, -6)
    wbox('trim_cream', -2.0, 2.0, H2 - 0.6, H2, -6 - bay_out - 0.1, -6)
    # the bedroom beyond its door: dim, turned over, seen but not entered
    PLACES['door'] = [0, 0, 5.2]
    PLACES['bedroom'] = [4.2, 1.4, 2.5]
    wbox('parquet', 5.2, 9.5, -0.1, 0, -1, 6)
    wbox('plaster', 9.5, 9.7, 0, H2, -1, 6)
    wbox('plaster', 5.2, 9.5, 0, H2, -1.2, -1)
    wbox('plaster', 5.2, 9.5, H2, H2 + 0.1, -1, 6)
    four_poster(7.5, 3.5, -math.pi / 2)
    cabinet(9.2, 0.5, -math.pi / 2, w=1.2)
    for (x, z) in ((6.5, 1.0), (7.2, 0.4), (8.5, 1.6)):  # clothes turned out on the floor
        wbox('velvet_green', x - 0.3, x + 0.3, 0, 0.05, z - 0.2, z + 0.25)
    collide(5.2, 0, -1.2, 9.7, H2, 6)


def furnish_suite():
    # the fireplace on the west wall, a sofa and wingbacks round it, a rug
    fireplace(frame((-5 + T / 2, 0, 0), (0, 0, 1), (1, 0, 0)), 0.0, mat='marble_white', w=1.9)
    rug(-3.6, 1.4, -2.6, 2.6, 0)
    sofa(-0.6, 0, -math.pi / 2, 'velvet_red', 2.2)
    for (x, z) in ((-3.0, 2.0), (-3.0, -2.0)):
        wingback(x, z, facing(x, z, -4.6, 0), 'velvet_green')
    pedestal_table(-1.9, 0, lamp=True, r=0.35)
    # the sofa's seat cushion slit open, stuffing on the rug
    for k in range(9):
        sphere('canvas', (-0.5 + (k % 3) * 0.12, 0.52 + (k // 3) * 0.03, -0.4 + (k % 4) * 0.25), 0.05 + (k % 2) * 0.02, 6)
    PLACES['cushion'] = [-0.6, 0.6, 0]
    # the writing desk by the east wall: drawers pulled out, papers everywhere
    F = Matrix.Translation((3.6, 0, -3.8)) @ Matrix.Rotation(-math.pi / 2, 4, 'Y')
    lbox(F, 'walnut_panel', -0.75, 0.75, 0.72, 0.78, -0.35, 0.35)
    for s in (-1, 1):  # the pedestals of drawers either side of the kneehole
        lbox(F, 'walnut_panel', min(s * 0.4, s * 0.75), max(s * 0.4, s * 0.75), 0, 0.72, -0.33, 0.33)
    for k, out in enumerate((0.25, 0.4, 0.15)):  # drawers hanging open
        lbox(F, 'walnut_panel', 0.42, 0.73, 0.12 + k * 0.2, 0.3 + k * 0.2, 0.33, 0.33 + out)
    lbox(F, 'walnut_panel', -0.73, -0.42, 0.12, 0.3, 0.33, 0.6)
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
    # a long-case clock, a fern, pictures, sconces, a gasolier
    longcase_clock(-4.55, -4.8, math.pi / 2)
    fern(4.4, -5.2, 1.0)
    gasolier(0, H2 - 0.2, 0, drop=1.2)
    frame_painting(frame((5 - T / 2, 0, -6), (0, 0, 1), (-1, 0, 0)), 2.6, 1.6, 1.3, 1.0, 4)
    frame_painting(frame((-5 + T / 2, 0, 6), (0, 0, -1), (1, 0, 0)), 9.0, 1.5, 1.6, 1.2, 12)
    PLACES['window'] = [0, 1.6, -6.4]
    # Market Street below the window: across the way, lit fronts in the fog
    for k in range(9):
        x = -24 + k * 6
        h = 10 + (k * 7) % 9
        wbox(['brick_red', 'clap_cream', 'brick_brown', 'brick_tan'][k % 4], x, x + 5.6, -12, h, -40, -34)
        for j in range(3):
            for i in range(2):
                wbox('glass_lit0' if (k + i + j) % 3 else 'glass_dark', x + 0.8 + i * 2.6, x + 2.0 + i * 2.6, -8 + j * 4, -6.2 + j * 4, -34.05, -34.0)
    wbox('roof', -40, 40, -12.2, -12, -60, -8)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hopkins_materials()
    interior_materials()
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
                       spawn=dict(pos=[0, 0, 5.0], yaw=0.0)), f, separators=(',', ':'))
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


main()
