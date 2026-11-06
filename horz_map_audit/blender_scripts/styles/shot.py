import bpy, math, base64
from mathutils import Vector
sc = bpy.context.scene
cam = bpy.data.objects.get("q_cam") or bpy.data.objects.new("q_cam", bpy.data.cameras.new("q_cam"))
if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
cam.data.lens = LENS; cam.data.clip_end = 3000; cam.data.clip_start = 0.5
cam.location = Vector(POS); d = Vector(TGT) - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
sun = bpy.data.objects.get("q_sun") or bpy.data.objects.new("q_sun", bpy.data.lights.new("q_sun", 'SUN'))
if sun.name not in sc.collection.objects: sc.collection.objects.link(sun)
sun.data.energy = 3.2; sun.data.angle = 0.05; sun.rotation_euler = (math.radians(50), 0, math.radians(35))
w = bpy.data.worlds.get("q_sky") or bpy.data.worlds.new("q_sky"); w.use_nodes = True
bg = w.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (0.55, 0.68, 0.85, 1); bg.inputs[1].default_value = 0.9
sc.world = w
r = sc.render; r.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in r.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
r.resolution_x, r.resolution_y, r.resolution_percentage = 1600, 1000, 100
try: sc.eevee.taa_render_samples = 16
except Exception: pass
sc.view_settings.view_transform = 'Standard'
r.filepath = "/srv/blender/projects/horz/_shot.png"; r.image_settings.file_format = 'PNG'
bpy.ops.render.render(write_still=True)
print("B64:" + base64.b64encode(open(r.filepath, "rb").read()).decode() + ":END")
