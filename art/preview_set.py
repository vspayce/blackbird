# Look-dev renders of the Burritt Alley set, for judging the art without an engine.
#
#   blender -b --python art/preview_set.py -- <out prefix> [shot ...] [--res 960x540] [--samples 24] [--nofog]
#   (or, with Blender as a Python module:  python3 art/preview_set.py -- ...)
#
# Opens art/set/burritt.blend (which carries no lights: lighting lives in the engines), adds temporary
# gaslights at the Lamp_* markers, the police lantern, a cold fog/moon fill and volumetric fog, and renders
# the named shots with Cycles on the CPU from the player's eye height. Nothing is saved back to the .blend.
import os, sys, math
import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def opt(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


RES = [int(v) for v in opt('--res', '960x540').split('x')]
SAMPLES = int(opt('--samples', '24'))
FOG = '--nofog' not in ARGS
FLAT = '--flat' in ARGS      # an even grey daylight with no fog: for checking the modelling, not the mood
skip = set()
for k, a in enumerate(ARGS):
    if a in ('--res', '--samples'): skip.update((k, k + 1))
    if a in ('--nofog', '--flat'): skip.add(k)
POS = [a for k, a in enumerate(ARGS) if k not in skip]
OUT = POS[0] if POS else '/tmp/burritt'
WANT = POS[1:]

# eye, look-at, lens (mm) — in the game's coordinates (Y up, alley along -Z)
SHOTS = {
    'mouth':   ((1.5, 1.65, 15.5), (-0.6, 2.3, 4.0), 24),     # from Bush Street, looking into the alley
    'mouth2':  ((-6.5, 1.65, 13.5), (0.5, 2.6, 5.0), 24),     # the alley mouth and its lamp, from up the street
    'alley':   ((0.4, 1.65, 3.0), (-0.2, 2.2, -12.0), 22),    # just inside, looking down the alley
    'mid':     ((0.9, 1.65, -6.0), (-0.6, 1.6, -18.0), 24),   # past the lamp, toward the fence
    'body':    ((-0.9, 1.65, -14.2), (0.5, 0.5, -20.0), 24),  # where Archer lies
    'back':    ((0.3, 1.65, -18.0), (-0.2, 2.6, 4.0), 24),    # from the body, back out to the street
    'east':    ((-2.0, 1.65, 12.2), (26.0, 3.2, 14.5), 24),   # along Bush Street, +x
    'west':    ((3.0, 1.65, 12.6), (-26.0, 3.2, 14.5), 24),   # along Bush Street, -x
    'far':     ((0.0, 1.65, 10.2), (-4.0, 4.0, 22.0), 22),    # across the street to the far side
    'near':    ((9.0, 1.65, 18.5), (-2.0, 3.4, 8.0), 22),     # the near fronts from across the street
    'up':      ((0.6, 1.65, -3.0), (-1.6, 9.0, -5.5), 20),    # up at the fire escape and wires
    'shop':    ((8.0, 1.65, 11.6), (8.3, 2.0, 8.0), 20),      # a shopfront, close
    'livery':  ((-16.0, 1.65, 13.0), (-25.0, 2.2, 21.0), 24),   # the livery stable and the dray before it
    'walk':    ((-5.5, 1.65, 9.0), (-12.5, 0.6, 8.8), 24),     # along the near sidewalk
    'saloon':  ((17.0, 1.65, 13.8), (21.0, 3.0, 8.0), 22),     # the Golden Eagle
    'air1':    ((7.0, 9.0, 19.0), (-1.0, 1.0, 4.0), 20),        # from above: the alley mouth and the near fronts
    'air2':    ((1.6, 7.5, 6.0), (-0.8, 0.0, -12.0), 18),      # from above: down the alley
    'air3':    ((-1.5, 6.0, -8.0), (0.8, 0.0, -21.0), 18),     # from above: the dead end
    'air4':    ((-2.0, 7.0, 10.0), (4.0, 4.0, 22.0), 16),      # from above: the far fronts
    'air5':    ((2.0, 3.0, 13.0), (-14.0, 5.5, 8.0), 20),      # near fronts, west
    'air6':    ((-2.0, 3.0, 13.0), (16.0, 5.0, 8.0), 20),      # near fronts, east
    'props':   ((1.2, 1.65, -1.0), (-1.6, 0.8, -4.5), 28),    # alley clutter, close
}


def G(p):  # game -> Blender
    return Vector((p[0], -p[2], p[1]))


def setup():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, 'art', 'set', 'burritt.blend'))
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    cy = sc.cycles
    cy.device = 'CPU'
    cy.samples = SAMPLES
    cy.use_adaptive_sampling = False
    cy.use_denoising = True
    cy.max_bounces = 3; cy.diffuse_bounces = 2; cy.glossy_bounces = 2; cy.transmission_bounces = 1
    cy.volume_bounces = 0
    cy.caustics_reflective = False; cy.caustics_refractive = False
    cy.sample_clamp_indirect = 3.0; cy.sample_clamp_direct = 0
    try: cy.volume_step_rate = 4.0; cy.volume_max_steps = 64
    except Exception: pass
    sc.render.threads_mode = 'FIXED'; sc.render.threads = 3
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    try: sc.view_settings.view_transform = 'AgX'
    except Exception: sc.view_settings.view_transform = 'Filmic'
    try: sc.view_settings.look = 'AgX - Medium High Contrast'
    except Exception: pass
    sc.view_settings.exposure = 2.6

    # the night: a dim blue sky, thick with fog
    w = bpy.data.worlds.new('Night'); sc.world = w; w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    bg.inputs['Color'].default_value = (0.09, 0.15, 0.26, 1); bg.inputs['Strength'].default_value = 2.0
    if FLAT:
        bg.inputs['Color'].default_value = (0.6, 0.65, 0.7, 1); bg.inputs['Strength'].default_value = 1.2
        sc.view_settings.exposure = 0.3
    if FOG and not FLAT:
        vol = nt.nodes.new('ShaderNodeVolumeScatter')
        vol.inputs['Color'].default_value = (0.62, 0.78, 1.0, 1)
        vol.inputs['Density'].default_value = 0.022
        vol.inputs['Anisotropy'].default_value = 0.35
        nt.links.new(vol.outputs['Volume'], nt.nodes['World Output'].inputs['Volume'])

    def light(name, kind, loc, energy, color, **kw):
        d = bpy.data.lights.new(name, kind); d.energy = energy; d.color = color
        for k, v in kw.items(): setattr(d, k, v)
        o = bpy.data.objects.new(name, d); sc.collection.objects.link(o); o.location = loc
        return o

    for o in bpy.data.objects:   # the lantern glass is modelled solid: let the flame's light out through it
        if o.name.startswith('lamp_glass'): o.visible_shadow = False
    for m in bpy.data.materials:   # lit windows: the engines set their own glow; keep them from burning out here
        p = m.node_tree.nodes.get('Principled BSDF') if m.node_tree else None
        if p and m.name.startswith('glass_lit'): p.inputs['Emission Strength'].default_value *= 0.3
        if p and m.name.startswith('lamp_glass'): p.inputs['Emission Strength'].default_value = 3.0
    moon = light('Moon', 'SUN', (0, 0, 30), 0.25, (0.5, 0.66, 1.0), angle=0.3)
    moon.rotation_euler = (Vector((0, 0, 0)) - G((-6, 14, 8))).to_track_quat('-Z', 'Y').to_euler()
    for o in list(bpy.data.objects):
        if o.name.startswith('Lamp_'):
            p = o.matrix_world.translation
            bracket = p.z < 3.3
            light('Gas_' + o.name, 'POINT', p, 70 if bracket else 120, (1.0, 0.7, 0.42), shadow_soft_size=0.09)
    # the police lantern on the cobbles by the body, and a stand-in for Archer (preview only)
    light('Lantern', 'POINT', G((-0.9, 0.42, -17.8)), 14, (1.0, 0.7, 0.4), shadow_soft_size=0.05)
    me = bpy.data.meshes.new('archer')
    import bmesh
    bm = bmesh.new()
    for c, s in (((0.5, 0.16, -19.2), (0.28, 0.14, 0.85)), ((0.5, 0.17, -20.2), (0.34, 0.16, 0.5)),
                 ((0.5, 0.15, -20.75), (0.12, 0.12, 0.13))):
        from mathutils import Matrix
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=1.0,
                                  matrix=Matrix.Translation(G(c)) @ Matrix.Diagonal((s[0], s[2], s[1], 1)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('ArcherStandIn', me); sc.collection.objects.link(ob)
    m = bpy.data.materials.new('standin'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.02, 0.02, 0.025, 1)
    me.materials.append(m)

    cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
    sc.collection.objects.link(cam); sc.camera = cam
    cam.data.sensor_width = 36; cam.data.clip_start = 0.05; cam.data.clip_end = 300
    return sc, cam


def main():
    sc, cam = setup()
    for tag in (WANT or list(SHOTS)):
        eye, look, lens = SHOTS[tag]
        cam.data.lens = lens
        cam.location = G(eye)
        cam.rotation_euler = (G(look) - G(eye)).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f'{OUT}_{tag}.png'
        bpy.ops.render.render(write_still=True)
        print('rendered', sc.render.filepath, flush=True)


main()
