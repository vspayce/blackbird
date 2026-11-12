# Polish pass over the cast built by build_humans.py: better clips (art/humananim.py), cloth and skin detail that
# the game engines can carry (image textures only), small fixes to the models, and a fresh export.
#
#   python3 art/polish_humans.py -- [--only holmes,watson] [--clips Walk,Run] [--dry DIR] [--no-export]
#
# Opens art/humans/<name>.blend, applies everything, saves the blend and writes public/models/<name>.glb (Draco
# geometry, WebP textures: already "compressed" as far as tools/compress-models.mjs is concerned) and
# art/humans/clips.json (what clips each character has, their length, loop flag and ground speed).
# Safe to run again: actions, images, shape keys and materials are replaced by name, never duplicated.
# --dry DIR writes the blend and the GLB into DIR instead (for review renders) and leaves the repo files alone.
#
# Needs only `import bpy` (Blender as a Python module, 5.x); MPFB is not required.
import os, sys, json, math, struct, io, time
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import humananim as ha

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
CAST = ['holmes', 'watson', 'archer', 'polhaus', 'kelly', 'wilmer', 'cairo', 'brigid', 'gutman', 'wren']


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS and ARGS.index(name) + 1 < len(ARGS) else default


def log(*a):
    print('[polish]', *a, flush=True)


# --- images ------------------------------------------------------------------------------------------------------

def restore_images(name):
    """The skin and eye textures were linked from the MPFB library on the machine that built the cast, so the
    saved blends point at files that are not in the repo. The exported GLB carries them: load them from there and
    pack them, so the blends stand on their own (and the Unity export finds them)."""
    missing = [i for i in bpy.data.images if i.type == 'IMAGE' and i.size[0] == 0 and i.users]
    if not missing: return 0
    from PIL import Image
    path = os.path.join(ROOT, 'public', 'models', f'{name}.glb')
    d = open(path, 'rb').read()
    n, = struct.unpack_from('<I', d, 12)
    j = json.loads(d[20:20 + n]); b = d[20 + n + 8:]
    done = 0
    for img in missing:
        key = os.path.splitext(img.name)[0]
        gi = next((g for g in j.get('images', []) if g.get('name') in (key, img.name)), None)
        if not gi:
            log('  ! no copy of', img.name, 'in', path); continue
        bv = j['bufferViews'][gi['bufferView']]
        im = Image.open(io.BytesIO(b[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]))
        im = im.convert('RGBA').transpose(Image.FLIP_TOP_BOTTOM)
        new = bpy.data.images.new(key, im.size[0], im.size[1], alpha=False)
        new.pixels.foreach_set((np.asarray(im, dtype=np.float32) / 255.0).ravel())
        new.pack()
        for m in bpy.data.materials:
            if m.node_tree:
                for nd in m.node_tree.nodes:
                    if nd.type == 'TEX_IMAGE' and nd.image == img: nd.image = new
        old_name = img.name
        bpy.data.images.remove(img)
        new.name = key
        done += 1
    return done


# --- export ------------------------------------------------------------------------------------------------------

def slim_animations(path, steps):
    """Rewrite the animations of a GLB for the web download. Blender's exporter writes translation, rotation and
    scale for every bone on every frame; this keeps rotations (as normalised 16-bit quaternions), the pelvis's
    translation, drops channels that never leave the bind pose, keeps one key where a channel is constant, and
    keeps every steps[clip]-th key of the slow clips (the players interpolate). Nothing else in the file changes."""
    d = open(path, 'rb').read()
    n, = struct.unpack_from('<I', d, 12)
    j = json.loads(d[20:20 + n]); bin_ = d[20 + n + 8:]
    acc, bvs = j['accessors'], j['bufferViews']
    def read(i):
        a = acc[i]; bv = bvs[a['bufferView']]
        assert a['componentType'] == 5126 and 'byteStride' not in bv
        nc = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}[a['type']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        return np.frombuffer(bin_, '<f4', a['count'] * nc, off).reshape(a['count'], nc)
    blob = bytearray()
    new_acc = []          # accessors for the animation data, all in one new buffer view
    def add(arr, ctype, typ, normalized=False, minmax=False):
        while len(blob) % 4: blob.append(0)
        a = dict(bufferView=-1, byteOffset=len(blob), componentType=ctype, count=len(arr), type=typ)
        if normalized: a['normalized'] = True
        if minmax: a['min'] = [float(arr.min())]; a['max'] = [float(arr.max())]
        blob.extend(arr.tobytes())
        new_acc.append(a)
        return len(new_acc) - 1
    nodes = j['nodes']
    for an in j.get('animations', []):
        step = steps.get(an['name'], 1)
        chans, samps, times = [], [], {}
        held = max(acc[an['samplers'][ch['sampler']]['input']]['count'] for ch in an['channels']) <= 2
        for ch in an['channels']:
            path_, node = ch['target']['path'], ch['target']['node']
            if path_ == 'scale': continue
            sm = an['samplers'][ch['sampler']]
            t = read(sm['input'])[:, 0]; v = read(sm['output'])
            const = float(np.abs(v - v[0]).max()) < 1e-5
            if held:   # a held pose (LieBack): keep both keys so the clip has a length
                idx = list(range(len(t)))
            elif const:
                rest = nodes[node].get('translation' if path_ == 'translation' else 'rotation',
                                       [0, 0, 0] if path_ == 'translation' else [0, 0, 0, 1])
                same = np.abs(v[0] - np.array(rest)).max() < 2e-5
                if path_ == 'rotation' and not same: same = np.abs(v[0] + np.array(rest)).max() < 2e-5
                if same: continue
                idx = [0]
            else:
                if path_ == 'translation' and float(np.abs(v - v[0]).max()) < 2e-4: continue
                idx = sorted(set(range(0, len(t), step)) | {len(t) - 1})
            key = (len(t), len(idx), float(t[idx[-1]]))
            if key not in times: times[key] = add(t[idx].astype('<f4'), 5126, 'SCALAR', minmax=True)
            if path_ == 'rotation':
                q = v[idx] / np.linalg.norm(v[idx], axis=1, keepdims=True)
                out = add(np.round(q * 32767).astype('<i2'), 5122, 'VEC4', normalized=True)
            else:
                out = add(v[idx].astype('<f4'), 5126, 'VEC3')
            samps.append(dict(input=('new', times[key]), output=('new', out), interpolation='LINEAR'))
            chans.append(dict(sampler=len(samps) - 1, target=ch['target']))
        an['channels'], an['samplers'] = chans, samps
    # compact: keep the accessors and buffer views something still uses, then append the new animation data
    used_acc = set()
    for m in j.get('meshes', []):
        for p in m['primitives']:
            used_acc.update(p.get('attributes', {}).values())
            if 'indices' in p: used_acc.add(p['indices'])
            for tg in p.get('targets', []): used_acc.update(tg.values())
    for sk in j.get('skins', []):
        if 'inverseBindMatrices' in sk: used_acc.add(sk['inverseBindMatrices'])
    used_bv = set(acc[i]['bufferView'] for i in used_acc if 'bufferView' in acc[i])
    for im in j.get('images', []):
        if 'bufferView' in im: used_bv.add(im['bufferView'])
    for m in j.get('meshes', []):
        for p in m['primitives']:
            ex = p.get('extensions', {}).get('KHR_draco_mesh_compression')
            if ex: used_bv.add(ex['bufferView'])
    out = bytearray(); bv_map = {}; new_bvs = []
    for i in sorted(used_bv):
        bv = dict(bvs[i]); off = bv.get('byteOffset', 0)
        while len(out) % 4: out.append(0)
        bv['byteOffset'] = len(out); out.extend(bin_[off:off + bv['byteLength']])
        bv_map[i] = len(new_bvs); new_bvs.append(bv)
    while len(out) % 4: out.append(0)
    anim_bv = len(new_bvs)
    new_bvs.append(dict(buffer=0, byteOffset=len(out), byteLength=len(blob))); out.extend(blob)
    while len(out) % 4: out.append(0)
    acc_map = {}; accs = []
    for i in sorted(used_acc):
        a = dict(acc[i])
        if 'bufferView' in a: a['bufferView'] = bv_map[a['bufferView']]
        acc_map[i] = len(accs); accs.append(a)
    base = len(accs)
    for a in new_acc:
        a['bufferView'] = anim_bv; accs.append(a)
    for m in j.get('meshes', []):
        for p in m['primitives']:
            p['attributes'] = {k: acc_map[v] for k, v in p.get('attributes', {}).items()}
            if 'indices' in p: p['indices'] = acc_map[p['indices']]
            if 'targets' in p: p['targets'] = [{k: acc_map[v] for k, v in tg.items()} for tg in p['targets']]
            ex = p.get('extensions', {}).get('KHR_draco_mesh_compression')
            if ex: ex['bufferView'] = bv_map[ex['bufferView']]
    for sk in j.get('skins', []):
        if 'inverseBindMatrices' in sk: sk['inverseBindMatrices'] = acc_map[sk['inverseBindMatrices']]
    for im in j.get('images', []):
        if 'bufferView' in im: im['bufferView'] = bv_map[im['bufferView']]
    for an in j.get('animations', []):
        for sm in an['samplers']:
            sm['input'] = base + sm['input'][1]; sm['output'] = base + sm['output'][1]
    j['accessors'], j['bufferViews'] = accs, new_bvs
    j['buffers'] = [dict(byteLength=len(out))]
    js = json.dumps(j, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    total = 12 + 8 + len(js) + 8 + len(out)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total))
        f.write(struct.pack('<I4s', len(js), b'JSON')); f.write(js)
        f.write(struct.pack('<I4s', len(out), b'BIN\0')); f.write(out)
    return len(blob)


def export_glb(rig, name, meta, path):
    """As build_humans.py exports (glTF binary, Y up, one animation per NLA track, walk_speed in the extras), then
    the animations are slimmed and tools/compress-models.mjs makes the textures WebP and the geometry Draco.
    Called after the blend is saved: what it changes here (smaller images) is not kept."""
    import subprocess
    for o in [rig] + list(rig.children):
        for k in [k for k in o.keys() if k.startswith(('MPFB', 'Mh'))]: del o[k]
    for img in bpy.data.images:
        if img.size[0] == 0: continue
        n = img.name.lower()
        cap = 2048 if 'skin' in n else 1024 if 'suit' in n and not n.endswith('_n') else 512
        if img.size[0] > cap: img.scale(cap, int(cap * img.size[1] / img.size[0]))
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for o in rig.children: o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=True, export_animations=True, export_animation_mode='NLA_TRACKS',
                              export_image_format='AUTO', export_jpeg_quality=92,
                              export_cameras=False, export_lights=False, export_extras=True,
                              export_morph=True, export_morph_normal=False, export_morph_animation=False)
    raw = os.path.getsize(path)
    anim = slim_animations(path, {k: m.get('web_step', 1) for k, m in meta.items()})
    env = dict(os.environ, MODELS_DIR=os.path.dirname(path))
    r = subprocess.run(['node', os.path.join(ROOT, 'tools', 'compress-models.mjs'), name], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    if r.returncode: log('  ! compress-models failed (run `npm install`, then `npm run compress`):', r.stderr.strip()[-300:])
    log(name, 'glb %.2f MB raw, animations %.0f KB, %.2f MB compressed' % (raw / 1048576, anim / 1024, os.path.getsize(path) / 1048576))
    return os.path.getsize(path)


# --- one character -----------------------------------------------------------------------------------------------

def polish(name, dry=None, clips=None, export=True):
    t0 = time.time()
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, 'art', 'humans', f'{name}.blend'))
    rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
    got = restore_images(name)
    if got: log(name, 'restored', got, 'textures from the GLB')
    try:
        import humanlook
        humanlook.polish_look(rig, name, log)
    except ImportError:
        pass
    meta, c = ha.make_all_clips(rig, name, clips, log)
    for kind in ('walk', 'run'):
        if kind in c.gaits: log(name, kind, f"{c.gaits[kind]['v']:.2f} m/s, planted foot drifts {ha.foot_slide(c, kind) * 1000:.1f} mm")
    blend = os.path.join(dry, f'{name}.blend') if dry else os.path.join(ROOT, 'art', 'humans', f'{name}.blend')
    bpy.context.preferences.filepaths.save_version = 0   # no .blend1 beside the blends
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True, copy=bool(dry))
    size = None
    if export:
        glb = os.path.join(dry, f'{name}.glb') if dry else os.path.join(ROOT, 'public', 'models', f'{name}.glb')
        size = export_glb(rig, name, meta, glb)
    log(name, 'done in %.0f s' % (time.time() - t0), 'glb %.2f MB' % (size / 1048576) if size else '')
    return meta


if __name__ == '__main__':
    only = (arg('--only') or ','.join(CAST)).split(',')
    dry = arg('--dry')
    if dry: os.makedirs(dry, exist_ok=True)
    clips = [x for x in (arg('--clips') or '').split(',') if x] or None
    mpath = os.path.join(dry or os.path.join(ROOT, 'art', 'humans'), 'clips.json')
    allmeta = json.load(open(mpath)) if os.path.exists(mpath) else {}
    for name in only:
        meta = polish(name, dry, clips, '--no-export' not in ARGS)
        if clips: allmeta.setdefault(name, {}).update(meta)
        else: allmeta[name] = meta
    json.dump(allmeta, open(mpath, 'w'), indent=1, sort_keys=True)
