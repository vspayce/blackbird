# Builds Brigid O'Shaughnessy's suite at the St. Mark Hotel for Chapter III: a smaller, plainer hotel than the
# Palace, and she is packing to leave.
#
#   /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
#       --python art/build_stmark.py -- [--render prefix]
#
# Writes art/set/stmark.blend, public/models/stmark.glb and public/models/stmark.json (colliders, lamps, named
# places, spawn). Game coordinates, Y up, metres: the sitting room is x -4.5..4.5, z -5..5, the door to the
# corridor at the south (z = 5), two tall windows over Ellis Street at the north (z = -5), the bedroom through a
# door in the east wall.
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_hopkins as bh
from build_hopkins import *  # noqa: F401,F403
from build_palace import paper, book, into_room  # noqa: E402  (build_palace only builds when run itself)

H2 = 3.8
PLACES = {}


def build_suite():
    floor('parquet', -4.5, 4.5, -5, 5)
    wbox('plaster', -4.5, 4.5, H2, H2 + 0.1, -5, 5)
    for x in (-1.5, 1.5):  # a plain moulded ceiling: two plaster beams
        wbox('trim_cream', x - 0.12, x + 0.12, H2 - 0.18, H2, -5, 5)
    spec = {
        'south': ((4.5, 5), (-4.5, 5), [(4.5, 1.4, 0, 2.7)]),             # the corridor door
        'east': ((4.5, -5), (4.5, 5), [(3.2, 1.5, 0, 2.7)]),              # the bedroom door
        'west': ((-4.5, 5), (-4.5, -5), []),
        'north': ((-4.5, -5), (4.5, -5), [(2.6, 1.3, 0.7, 3.1), (6.4, 1.3, 0.7, 3.1)]),  # the windows
    }
    for key, (a, b, ops) in spec.items():
        F, L = wall(a, b, 0, H2, ops, mat='plaster')
        lining(F, L, into_room(F, L), ops, H2, wains='walnut_panel', upper='fresco_louis', w_h=1.0,
               curtains='velvet_green' if key == 'north' else None)
        for t, w, ob, ot in ops:
            if ob > 0.3: window_glass(F, t, w, ob, ot)
    # the bedroom beyond: the bed stripped, a wardrobe standing open
    PLACES['door'] = [0, 0, 4.4]
    PLACES['bedroom'] = [4.0, 1.4, -1.8]
    wbox('parquet', 4.7, 8.5, -0.1, 0, -5, 1)
    wbox('plaster', 8.5, 8.7, 0, H2, -5, 1)
    wbox('plaster', 4.7, 8.5, 0, H2, 1, 1.2)
    wbox('plaster', 4.7, 8.5, 0, H2, -5.2, -5)
    wbox('plaster', 4.7, 8.5, H2, H2 + 0.1, -5, 1)
    four_poster(7.0, -3.0, -math.pi / 2)
    cabinet(8.2, 0.2, -math.pi / 2, w=1.2)
    collide(4.7, 0, -5.2, 8.7, H2, 1.2)


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
    # the writing desk under the east window: letters, a hotel bill
    F = Matrix.Translation((3.6, 0, -2.2)) @ Matrix.Rotation(-math.pi / 2, 4, 'Y')
    lbox(F, 'rosewood_panel', -0.6, 0.6, 0.72, 0.77, -0.3, 0.3)
    for s in (-1, 1):
        lbox(F, 'rosewood_panel', min(s * 0.55, s * 0.6), max(s * 0.55, s * 0.6), 0, 0.72, -0.28, 0.28)
    lbox(F, 'rosewood_panel', -0.6, 0.6, 0.77, 1.05, 0.2, 0.3)       # a low gallery of pigeonholes
    collide(3.25, 0, -2.85, 3.95, 0.8, -1.55)
    chair(2.9, -2.2, math.pi / 2, 'velvet_green')
    for k in range(4):
        paper(3.55 + (k % 2) * 0.12, -2.45 + k * 0.15, 0.2 + k * 0.4, 0.16)
    PLACES['desk'] = [3.6, 0.9, -2.2]
    # the steamer trunk, lid up, half packed, in the middle of the floor by the bedroom door
    F = Matrix.Translation((2.4, 0, 1.6)) @ Matrix.Rotation(0.25, 4, 'Y')
    lbox(F, 'leather_black', -0.5, 0.5, 0, 0.6, -0.3, 0.3)
    lbox(F, 'canvas', -0.46, 0.46, 0.4, 0.59, -0.26, 0.26)            # linen folded inside
    G = F @ Matrix.Translation((0, 0.6, 0.3)) @ Matrix.Rotation(-1.75, 4, 'X')
    lbox(G, 'leather_black', -0.5, 0.5, 0, 0.08, 0, 0.6)               # the lid, thrown back
    for u in (-0.42, 0.42):
        lbox(F, 'brass', u - 0.03, u + 0.03, 0, 0.6, -0.31, 0.31)
    paper(2.25, 1.32, 0.25, 0.14)                                       # the steamer label, pasted on the end
    collide(1.8, 0, 1.15, 3.0, 0.7, 2.1)
    PLACES['trunk'] = [2.4, 0.7, 1.6]
    # a hatbox and a carpet bag by the door: she meant to be gone by noon
    cyl('canvas', (3.2, 0, 3.8), 0.32, 0.22, seg=16)
    lbox(Matrix.Translation((2.4, 0, 4.0)), 'velvet_red', -0.3, 0.3, 0, 0.35, -0.12, 0.12)
    # a pier glass between the windows, a fern, sconces, a small gasolier
    F = frame((0, 0, -5 + T / 2), (0, 0, 1), (1, 0, 0))
    lbox(F, 'gilt_frame', -0.42, 0.42, 0.5, 2.9, 0, 0.05)
    lbox(F, 'mirror', -0.36, 0.36, 0.56, 2.84, 0.05, 0.06)
    fern(-3.9, -4.4, 0.9)
    gasolier(0, H2, 0, arms=4, drop=1.0, r=0.5)
    for z in (-2.5, 2.5):
        sconce(frame((-4.5 + T / 2, 0, z), (0, 0, 1), (1, 0, 0)), 0.0, 1.8)
    frame_painting(frame((-4.5 + T / 2, 0, -2.5), (0, 0, 1), (1, 0, 0)), 0.0, 2.3, 0.9, 0.7, 6)
    frame_painting(frame((4.5 - T / 2, 0, 3.6), (0, 0, -1), (-1, 0, 0)), 0.0, 1.8, 1.0, 0.8, 9)
    PLACES['window'] = [-1.9, 1.6, -5.0]
    PLACES['brigid'] = [-1.6, 0, -3.6]
    # Ellis Street below the windows: brick fronts across the way, lit in the fog
    for k in range(7):
        x = -18 + k * 6
        h = 8 + (k * 5) % 7
        wbox(['brick_red', 'clap_cream', 'brick_brown', 'brick_tan'][k % 4], x, x + 5.6, -10, h, -30, -25)
        for j in range(3):
            for i in range(2):
                wbox('glass_lit0' if (k + i + j) % 3 else 'glass_dark', x + 0.8 + i * 2.6, x + 2.0 + i * 2.6,
                     -6 + j * 3.5, -4.4 + j * 3.5, -25.05, -25.0)
    wbox('roof', -30, 30, -10.2, -10, -50, -6)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    hopkins_materials()
    interior_materials()
    if 'leather_black' not in bpy.data.materials:
        material('leather_black', '#16110d', 0.45)
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
                       spawn=dict(pos=[0, 0, 4.0], yaw=0.0)), f, separators=(',', ':'))
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
