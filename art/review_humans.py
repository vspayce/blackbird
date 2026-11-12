# Review renders of the cast: stills (front, three-quarter, face) and contact sheets of every clip, so the models
# and the animation can be judged by eye. Cycles on the CPU at low resolution (no GPU needed).
#
#   python3 art/review_humans.py -- --out /tmp/cast --only holmes,watson [--tag after] [--stills] [--clips Walk,Idle]
#                                   [--frames 8] [--size 220x360] [--samples 10] [--views side,front]
#                                   [--src DIR]   (blends from a polish_humans.py --dry DIR run)
#
# Writes <out>/<tag>_<name>_stills.png and <out>/<tag>_<name>_<Clip>.png.
import os, sys, math, json, struct, io
import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CAST = ['holmes', 'watson', 'archer', 'polhaus', 'kelly', 'wilmer', 'cairo', 'brigid', 'gutman', 'wren']


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS and ARGS.index(name) + 1 < len(ARGS) else default


def restore_images(name):
    """The skin and eye textures were linked from the MPFB library on the build machine and are not in the blend;
    the exported GLB carries them. Load any missing image from there."""
    from PIL import Image
    missing = [i for i in bpy.data.images if i.type == 'IMAGE' and i.size[0] == 0]
    if not missing: return
    path = os.path.join(ROOT, 'public', 'models', f'{name}.glb')
    d = open(path, 'rb').read()
    n, = struct.unpack_from('<I', d, 12)
    j = json.loads(d[20:20 + n]); b = d[20 + n + 8:]
    import numpy as np
    for img in missing:
        key = os.path.splitext(img.name)[0]
        for gi in j.get('images', []):
            if gi.get('name') in (key, img.name) or gi.get('name', '').replace('Human_', '').replace('_png', '') == key:
                bv = j['bufferViews'][gi['bufferView']]
                im = Image.open(io.BytesIO(b[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]))
                im = im.convert('RGBA').transpose(Image.FLIP_TOP_BOTTOM)
                new = bpy.data.images.new(img.name + '_restored', im.size[0], im.size[1], alpha=False)
                new.pixels.foreach_set((np.asarray(im, dtype=np.float32) / 255.0).ravel())
                for m in bpy.data.materials:
                    if m.node_tree:
                        for nd in m.node_tree.nodes:
                            if nd.type == 'TEX_IMAGE' and nd.image == img: nd.image = new
                break


def setup_scene(samples):
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ('LIGHT', 'CAMERA') or o.name.startswith('Review'): bpy.data.objects.remove(o)
    def light(n, loc, e, size=2.0, col=(1, 1, 1)):
        ld = bpy.data.lights.new('Review' + n, 'AREA'); ld.energy, ld.size, ld.color = e, size, col
        lo = bpy.data.objects.new('Review' + n, ld); lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 1.2)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        sc.collection.objects.link(lo)
    light('Key', (2.2, -3.2, 3.4), 420, 2.5, (1.0, 0.95, 0.88))
    light('Fill', (-3, -2.5, 1.8), 110, 3, (0.85, 0.9, 1.0))
    light('Rim', (-0.8, 3.2, 3.0), 320, 2)
    w = bpy.data.worlds.new('ReviewW'); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs[0].default_value = (0.11, 0.115, 0.125, 1)
    w.node_tree.nodes['Background'].inputs[1].default_value = 1.0
    me = bpy.data.meshes.new('ReviewFloor')
    me.from_pydata([(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new('ReviewFloor', me); sc.collection.objects.link(fl)
    m = bpy.data.materials.new('ReviewFloorM'); m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.23, 0.225, 0.22, 1); p.inputs['Roughness'].default_value = 0.9
    me.materials.append(m)
    cam = bpy.data.objects.new('ReviewCam', bpy.data.cameras.new('ReviewCam')); sc.collection.objects.link(cam)
    sc.camera = cam
    sc.render.engine = 'CYCLES'
    c = sc.cycles
    c.device = 'CPU'; c.samples = samples; c.use_adaptive_sampling = False
    c.max_bounces = 3; c.diffuse_bounces = 1; c.glossy_bounces = 2; c.transparent_max_bounces = 12
    c.use_denoising = True
    try: c.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.render.threads_mode = 'FIXED'; sc.render.threads = int(arg('--threads', 3))
    sc.render.use_persistent_data = True
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'Standard'
    sc.render.film_transparent = False
    return cam


def shoot(cam, loc, look, lens, res, path):
    sc = bpy.context.scene
    cam.location = loc; cam.data.lens = lens
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    from PIL import Image
    return Image.open(path).convert('RGB')


def sheet(rows, labels, title, path):
    from PIL import Image, ImageDraw
    w = sum(i.size[0] for i in rows[0]); h = sum(r[0].size[1] for r in rows) + 18
    out = Image.new('RGB', (w, h), (16, 16, 18))
    d = ImageDraw.Draw(out)
    d.text((4, 3), title, fill=(235, 220, 170))
    y = 18
    for r, row in enumerate(rows):
        x = 0
        for k, im in enumerate(row):
            out.paste(im, (x, y))
            if r == 0 and labels: d.text((x + 3, y + 2), labels[k], fill=(200, 200, 200))
            x += im.size[0]
        y += row[0].size[1]
    out.save(path)
    return path


def play(rig, act):
    ad = rig.animation_data_create()
    ad.use_nla = False
    ad.action = act
    if act and hasattr(ad, 'action_slot') and act.slots and ad.action_slot is None:
        ad.action_slot = act.slots[0]


def review(name, out, tag, do_stills, clips, nframes, size, samples, views):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(arg('--src') or os.path.join(ROOT, 'art', 'humans'), f'{name}.blend'))
    restore_images(name)
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    cam = setup_scene(samples)
    sc = bpy.context.scene
    tmp = os.path.join(out, f'_cell_{os.getpid()}.png')
    head = rig.matrix_world @ rig.data.bones['head'].head_local
    top = max((rig.matrix_world @ rig.data.bones['head'].tail_local).z + 0.12, 1.7)
    if do_stills:
        play(rig, None)
        for pb in rig.pose.bones:
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
        sc.frame_set(0)
        act = bpy.data.actions.get('Idle')
        if act: play(rig, act); sc.frame_set(int(act.frame_range[0]))
        mid = top / 2
        ims = [shoot(cam, (0, -3.5, mid), (0, 0, mid), 50, (360, 600), tmp),
               shoot(cam, (1.95, -2.9, mid + 0.1), (0, 0, mid), 50, (360, 600), tmp),
               shoot(cam, (-2.1, 2.7, mid + 0.2), (0, 0, mid), 50, (360, 600), tmp),
               shoot(cam, (0.26, -1.05, head.z + 0.1), (0, head.y, head.z + 0.085), 85, (600, 600), tmp),
               shoot(cam, (0.5, -0.9, head.z - 0.62), (0.26, head.y - 0.1, head.z - 0.8), 85, (420, 600), tmp)]
        sheet([ims], None, f'{name} [{tag}] front / three-quarter / back / face / hand', os.path.join(out, f'{tag}_{name}_stills.png'))
    for cn in clips:
        act = bpy.data.actions.get(cn)
        if not act: print('no clip', cn); continue
        play(rig, act)
        f0, f1 = act.frame_range
        n = nframes if f1 - f0 > 2 else 1
        frames = [f0 + (f1 - f0) * k / n for k in range(n)] if n > 1 else [f0]
        if n > 1 and not cn.startswith(('Walk', 'Run', 'Idle', 'Talk', 'Guard', 'Notes', 'KneelIdle', 'ThinkIdle')):
            frames = [f0 + (f1 - f0) * k / (n - 1) for k in range(n)]
        lying = cn.startswith('Lie')
        rows = []
        for view in views:
            row = []
            for f in frames:
                sc.frame_set(int(f), subframe=f - int(f))
                pel = rig.matrix_world @ rig.pose.bones['pelvis'].head
                if lying:   # the game lays him on his back: look down the body's front
                    loc, look = {'side': (0, -3.6, 0.95), 'front': (3.6, 0.05, 0.95), 'q': (2.2, -2.6, 1.7)}.get(view, (0, -3.6, 0.95)), (0, 0.05 if view == 'front' else 0, 0.95)
                else:
                    cz = top / 2
                    loc = {'side': (3.7, pel.y, cz), 'front': (0, -3.7, cz), 'back': (0, 3.7, cz),
                           'q': (2.4, -2.8, cz + 0.3)}[view]
                    look = (0, pel.y if view == 'side' else 0, cz)
                row.append(shoot(cam, loc, look, 50, size, tmp))
            rows.append(row)
        sheet(rows, [f'{f:.0f}' for f in frames], f'{name} {cn} [{tag}]  {f1 - f0:.0f} frames @ {sc.render.fps} fps',
              os.path.join(out, f'{tag}_{name}_{cn}.png'))
    if os.path.exists(tmp): os.remove(tmp)


if __name__ == '__main__':
    out = arg('--out', '/tmp/cast'); os.makedirs(out, exist_ok=True)
    only = (arg('--only') or ','.join(CAST)).split(',')
    size = tuple(int(x) for x in arg('--size', '200x330').split('x'))
    clips = [c for c in (arg('--clips') or '').split(',') if c]
    for name in only:
        review(name, out, arg('--tag', 'now'), '--stills' in ARGS, clips, int(arg('--frames', 8)), size,
               int(arg('--samples', 10)), (arg('--views') or 'side,front').split(','))
