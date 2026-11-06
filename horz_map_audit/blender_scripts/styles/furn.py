
# ===== мебель/пропсы из Poly Haven (CC0) -> лёгкие ассеты hzF_* для телефона =====
import bpy, os, math, json
from mathutils import Vector
MD = "/srv/blender/assets/polyhaven_models"
TARGET = {"default": 900, "Sofa_01": 1400, "sofa_02": 1400, "sofa_03": 1400, "Chandelier_01": 600, "old_bed_frame": 1200, "vintage_day_bed": 1200,
          "street_lamp_01": 500, "street_lamp_02": 500, "modular_electricity_poles": 800, "pine_tree_01": 1200, "fir_tree_01": 1200, "tree_small_02": 1200}
AC = bpy.data.collections.get("HORZ • Мебель (ассеты)") or bpy.data.collections.new("HORZ • Мебель (ассеты)")
INFO = {}
done = 0
LIMIT = globals().get('LIMIT', 8)
for mid in sorted(os.listdir(MD)):
    if done >= LIMIT: break
    key = "hzF_" + mid.lower()
    if bpy.data.meshes.get(key) and bpy.data.meshes[key].get("hz_furn"):
        me = bpy.data.meshes[key]; INFO[key] = list(me["dims"]); continue
    g = f"{MD}/{mid}/{mid}.gltf"
    if not os.path.exists(g): continue
    SK = "/srv/blender/assets/polyhaven_models/_skip.txt"; CUR = "/srv/blender/assets/polyhaven_models/_cur.txt"
    skip = open(SK).read().split() if os.path.exists(SK) else []
    if os.path.exists(CUR):
        c = open(CUR).read().strip()
        if c and c not in skip: skip.append(c); open(SK, "w").write("\n".join(skip))
    if mid in skip: continue
    open(CUR, "w").write(mid)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=g)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    if not meshes:
        for o in new: bpy.data.objects.remove(o)
        continue
    # применить трансформации, объединить
    for o in new:
        for c in list(o.users_collection): c.objects.unlink(o)
        AC.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        o.data = o.data.copy(); o.data.transform(o.matrix_world); o.matrix_world.identity()
    base = meshes[0]
    if len(meshes) > 1:
        with bpy.context.temp_override(active_object=base, selected_editable_objects=meshes, selected_objects=meshes):
            bpy.ops.object.join()
    for o in new:
        if o != base and o.name in bpy.data.objects: bpy.data.objects.remove(o)
    me = base.data
    tri = sum(len(p.vertices) - 2 for p in me.polygons)
    tgt = TARGET.get(mid, TARGET["default"])
    if tri > tgt:
        mod = base.modifiers.new("dec", 'DECIMATE'); mod.ratio = max(0.02, tgt / tri)
        with bpy.context.temp_override(object=base, active_object=base):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    me = base.data
    # начало координат — центр низа
    xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]; zs = [v.co.z for v in me.vertices]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    for v in me.vertices: v.co -= off
    # материалы: только базовый цвет (для DFF/TXD), без normal/roughness
    for m in me.materials:
        if not m or not m.use_nodes: continue
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type == 'NORMAL_MAP': nt.nodes.remove(n)
        b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if b:
            for s_ in ("Roughness", "Metallic", "Normal"):
                for l in list(b.inputs[s_].links): nt.links.remove(l)
            b.inputs["Roughness"].default_value = 0.7
    me.name = key; base.name = key
    me["hz_furn"] = 1; me["source"] = "Poly Haven CC0: " + mid
    dims = [round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3)]
    me["dims"] = dims; INFO[key] = dims
    me["tris"] = sum(len(p.vertices) - 2 for p in me.polygons)
    base.hide_render = True; base.hide_viewport = True
    done += 1
    open(CUR, 'w').write('')
    bpy.ops.outliner.orphans_purge(do_recursive=True) if False else None
if AC.name in bpy.context.scene.collection.children: bpy.context.scene.collection.children.unlink(AC)
json.dump(INFO, open("/srv/blender/assets/polyhaven_models/_furn_info.json", "w"), indent=0)
print("новых ассетов:", done, "| всего:", len(INFO))
bpy.ops.wm.save_mainfile()
