
import bpy, bmesh, os, re, struct, zipfile, colorsys
from mathutils import Quaternion, Vector, Matrix
K = "/srv/blender/mapkit/kit/maps/data/"
# 1) габариты моделей из коллизий
bounds = {}
Z = zipfile.ZipFile("/srv/blender/mapkit/HORZ_MOBILE_mapkit.zip")
with Z.open("packs/br_collision.bpc") as f:
    zz = zipfile.ZipFile(f)
    for info in zz.infolist():
        d = zz.read(info)
        k = d.find(b'CLST')
        while k >= 0:
            name = d[k + 8:k + 32].split(b'\0')[0].decode('latin1').lower()
            if d[k + 32:k + 36] == b'CED2':
                mn = struct.unpack('<3f', d[k + 52:k + 64]); mx = struct.unpack('<3f', d[k + 64:k + 76])
                if all(abs(v) < 2000 for v in mn + mx) and all(mx[i] >= mn[i] for i in range(3)):
                    bounds[name] = (mn, mx)
            k = d.find(b'CLST', k + 8)
print("габаритов из коллизий:", len(bounds))
# 2) какие IPL реально грузятся
cfg = open(K + "config.dat", encoding='utf-8', errors='replace').read()
ipls = [l.split(None, 1)[1].strip().replace('\\', '/') for l in cfg.splitlines() if l.startswith('IPL ')]
files = {}
for root, ds, fs in os.walk(K + "maps"):
    for fn in fs:
        files[os.path.relpath(os.path.join(root, fn), K + "maps").lower()] = os.path.join(root, fn)
sc = bpy.data.scenes.get("HORZ • Карта (макет)") or bpy.data.scenes.new("HORZ • Карта (макет)")
col = sc.collection
for o in list(col.objects):
    bpy.data.objects.remove(o)
tot = miss = 0
groups = [p for p in ipls if 'interior' not in p.lower() and 'event' not in p.lower()]
for gi, p in enumerate(groups):
    rel = p.split('MAPS/', 1)[-1].lower() if 'MAPS/' in p else p.lower()
    path = files.get(rel)
    if not path:
        print("нет файла", p); continue
    bm = bmesh.new(); sec = None; n = 0
    for line in open(path, encoding='utf-8', errors='replace'):
        l = line.strip()
        if l in ('inst', 'end', 'cull', 'pick', 'path', 'grge', 'enex', 'occl', 'mult', 'zone', 'cars', 'jump', 'auzo', 'tcyc'):
            sec = l; continue
        if sec != 'inst':
            continue
        q = [x.strip() for x in l.split(',')]
        if len(q) < 10:
            continue
        try:
            name = q[1].lower(); pos = Vector(map(float, q[3:6])); qx, qy, qz, qw = map(float, q[6:10])
        except ValueError:
            continue
        b = bounds.get(name)
        if b is None:
            miss += 1
            b = ((-1, -1, 0), (1, 1, 2))
        mn, mx = Vector(b[0]), Vector(b[1])
        size = mx - mn
        if max(size) < 1.0:
            continue  # мелочь не показываем
        rot = Quaternion((qw, qx, qy, qz)).conjugated().to_matrix().to_4x4()
        m = Matrix.Translation(pos) @ rot @ Matrix.Translation((mn + mx) / 2) @ Matrix.Diagonal((*size, 1))
        bmesh.ops.create_cube(bm, size=1.0, matrix=m)
        n += 1
    nm = os.path.splitext(os.path.basename(path))[0]
    me = bpy.data.meshes.get(nm) or bpy.data.meshes.new(nm)
    bm.to_mesh(me); bm.free()
    mat = bpy.data.materials.get("map_" + nm) or bpy.data.materials.new("map_" + nm)
    r, g, bb = colorsys.hsv_to_rgb((gi * 0.137) % 1, 0.45, 0.85)
    mat.diffuse_color = (r, g, bb, 1)
    me.materials.clear(); me.materials.append(mat)
    ob = bpy.data.objects.new(nm, me); col.objects.link(ob)
    tot += n
    print(f"{nm}: {n}")
print("всего коробок:", tot, "без габаритов (взяты 2x2x2):", miss)
bpy.context.window.scene = sc
