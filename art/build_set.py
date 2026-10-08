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
