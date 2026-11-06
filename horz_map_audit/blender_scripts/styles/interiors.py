
# ===== HORZ: интерьеры в точках сервера (coords.csv, interior 1) — комнаты, двери, окна, мебель CC0 =====
import bpy, math, json, os, random
import numpy as np
from mathutils import Vector
SCENE_I = "HORZ • Интерьеры"
PH = "/srv/blender/assets/polyhaven_cc0"
TEXD = ["/srv/blender/assets/horz_facades", PH, "/srv/blender/assets/panelka_512", "/srv/blender/assets/horz_district_tex"]


def imat(key):
    m = bpy.data.materials.get(key)
    if m: return m
    m = bpy.data.materials.new(key); m.use_nodes = True
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    for d in TEXD:
        for ext in (".png", ".jpg"):
            p = f"{d}/{key[3:] if key.startswith('ph_') else key}{ext}"
            if os.path.exists(p):
                im = bpy.data.images.load(p, check_existing=True)
                tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = im; nt.links.new(tx.outputs['Color'], b.inputs['Base Color'])
                break
        else: continue
        break
    b.inputs['Roughness'].default_value = 0.6
    if key == "fx_int_lamp":
        b.inputs['Emission Color'].default_value = (1, 0.95, 0.85, 1); b.inputs['Emission Strength'].default_value = 6.0
    return m


# окно изнутри: рама + «улица» (небо, деревья, дом напротив)
def int_window_tex():
    if os.path.exists("/srv/blender/assets/horz_facades/fx_int_window.png"): return
    S = 512; a = np.zeros((S, S, 3))
    yy = np.linspace(0, 1, S)[:, None]; a[:] = (0.55 + 0.35 * yy)[..., None] * np.array((0.62, 0.74, 0.92)) / 0.9
    r = np.random.default_rng(3)
    for k in range(9):                                       # деревья
        cx, cy, rr = r.uniform(0, S), r.uniform(330, 470), r.uniform(50, 110)
        Y, X = np.mgrid[0:S, 0:S]; m = (X - cx) ** 2 + (Y - cy) ** 2 < rr ** 2
        a[m] = np.array((0.22, 0.38, 0.18)) * r.uniform(0.8, 1.2)
    a[300:420, 300:470] = (0.80, 0.76, 0.66)                 # дом напротив
    for i in range(3):
        for j in range(2): a[315 + j * 50:345 + j * 50, 315 + i * 52:345 + i * 52] = (0.25, 0.30, 0.36)
    a[470:] = (0.30, 0.30, 0.30)
    fr = (0.95, 0.95, 0.94)
    a[:22] = fr; a[-22:] = fr; a[:, :22] = fr; a[:, -22:] = fr; a[:, 245:267] = fr; a[150:166, :245] = fr
    im = bpy.data.images.new("fx_int_window", S, S)
    im.pixels.foreach_set(np.concatenate([a[::-1], np.ones((S, S, 1))], -1).astype(np.float32).ravel())
    im.filepath_raw = "/srv/blender/assets/horz_facades/fx_int_window.png"; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)
    a = np.ones((64, 64, 3)) * 1.0
    im = bpy.data.images.new("fx_int_lamp", 64, 64); im.pixels.foreach_set(np.concatenate([a, np.ones((64, 64, 1))], -1).astype(np.float32).ravel())
    im.filepath_raw = "/srv/blender/assets/horz_facades/fx_int_lamp.png"; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)


int_window_tex()


class IM:
    def __init__(s, name): s.name = name; s.v = []; s.f = []; s.uv = []; s.mk = []
    def face(s, pts, uvs, key):
        i = len(s.v); s.v += [tuple(p) for p in pts]; s.f.append(tuple(range(i, i + len(pts)))); s.uv.append(list(uvs)); s.mk.append(key)
    def build(s, coll):
        me = bpy.data.meshes.new(s.name); keys = list(dict.fromkeys(s.mk)); me.from_pydata(s.v, [], s.f)
        for k in keys: me.materials.append(imat(k))
        uvl = me.uv_layers.new(name="UVMap")
        for pi, p in enumerate(me.polygons):
            p.material_index = keys.index(s.mk[pi])
            for j in range(p.loop_total): uvl.data[p.loop_start + j].uv = s.uv[pi][j]
        me.validate(); me.update(); o = bpy.data.objects.new(s.name, me); coll.objects.link(o); return o


H = 2.8; T = 0.06; DW, DH = 1.0, 2.15


class Interior:
    """Локальная система: u — вправо от игрока, v — вперёд (куда смотрит при появлении), пол z=0.
    Игрок появляется в (0, 0); входная дверь — в стене v=-2.2 за спиной."""
    def __init__(s, name, sx, sy, sz, ang_deg, height=H):
        s.name = name; s.S = Vector((sx, sy, sz - 1.0)); s.a = math.radians(ang_deg); s.H = height
        s.m = IM("int_" + name); s.rooms = []; s.items = []; s.extra_gaps = []
    def W(s, u, v, z=0.0):
        ca, sa = math.cos(s.a), math.sin(s.a)
        return (s.S.x + u * ca - v * sa, s.S.y + u * sa + v * ca, s.S.z + z)
    def room(s, nm, u0, u1, v0, v1, wall, floor, ceil="ph_white_plaster_02", wt=2.5, ft=2.0, windows=True, h=None):
        s.rooms.append(dict(nm=nm, u0=u0, u1=u1, v0=v0, v1=v1, wall=wall, floor=floor, ceil=ceil, wt=wt, ft=ft, win=windows, h=h or s.H))
    def gap(s, room, side, c, w=DW, top=DH): s.extra_gaps.append((room, side, c, w, top))
    def _gaps(s, r, side):
        out = []
        for q in s.rooms:
            if q is r: continue
            if side in ("E", "W"):
                x = r["u1"] if side == "E" else r["u0"]; xq = q["u0"] if side == "E" else q["u1"]
                if abs(x - xq) < 0.05:
                    lo, hi = max(r["v0"], q["v0"]), min(r["v1"], q["v1"])
                    if hi - lo > 1.3: out.append(((lo + hi) / 2, DW, DH))
            else:
                y = r["v1"] if side == "N" else r["v0"]; yq = q["v0"] if side == "N" else q["v1"]
                if abs(y - yq) < 0.05:
                    lo, hi = max(r["u0"], q["u0"]), min(r["u1"], q["u1"])
                    if hi - lo > 1.3: out.append(((lo + hi) / 2, DW, DH))
        for rn, sd, c, w, top in s.extra_gaps:
            if rn == r["nm"] and sd == side: out.append((c, w, top))
        return out
    def _shared(s, r, side):
        for q in s.rooms:
            if q is r: continue
            if side == "E" and abs(r["u1"] - q["u0"]) < 0.05 and min(r["v1"], q["v1"]) > max(r["v0"], q["v0"]): return True
            if side == "W" and abs(r["u0"] - q["u1"]) < 0.05 and min(r["v1"], q["v1"]) > max(r["v0"], q["v0"]): return True
            if side == "N" and abs(r["v1"] - q["v0"]) < 0.05 and min(r["u1"], q["u1"]) > max(r["u0"], q["u0"]): return True
            if side == "S" and abs(r["v0"] - q["v1"]) < 0.05 and min(r["u1"], q["u1"]) > max(r["u0"], q["u0"]): return True
        return False
    def _wall(s, r, side):
        m = s.m; h = r["h"]
        u0, u1, v0, v1 = r["u0"] + T, r["u1"] - T, r["v0"] + T, r["v1"] - T
        if side == "N": A, B = (u1, v1), (u0, v1); a0, a1 = u1, u0
        elif side == "S": A, B = (u0, v0), (u1, v0); a0, a1 = u0, u1
        elif side == "E": A, B = (u1, v0), (u1, v1); a0, a1 = v0, v1
        else: A, B = (u0, v1), (u0, v0); a0, a1 = v1, v0
        L = math.hypot(B[0] - A[0], B[1] - A[1]); gaps = []
        for c, w, top in s._gaps(r, side):
            t = (c - a0) / (a1 - a0) * L
            gaps.append((t - w / 2, t + w / 2, top))
        gaps.sort(); segs = []; cur = 0.0
        for g0, g1, top in gaps:
            segs.append((cur, g0, 0.0, h)); segs.append((g0, g1, top, h)); cur = g1
        segs.append((cur, L, 0.0, h))
        P = lambda t: (A[0] + (B[0] - A[0]) * t / L, A[1] + (B[1] - A[1]) * t / L)
        wt = r["wt"]
        for t0, t1, z0, z1 in segs:
            if t1 - t0 < 0.01: continue
            p0, p1 = P(t0), P(t1)
            m.face([s.W(*p0, z0), s.W(*p1, z0), s.W(*p1, z1), s.W(*p0, z1)], [(t0 / wt, z0 / wt), (t1 / wt, z0 / wt), (t1 / wt, z1 / wt), (t0 / wt, z1 / wt)], r["wall"])
            if z0 == 0.0:      # плинтус
                m.face([s.W(*p0, 0), s.W(*p1, 0), s.W(*p1, 0.09), s.W(*p0, 0.09)], [(0, 0), (1, 0), (1, 1), (0, 1)], "ph_dark_paneled_wood")
        # окна на наружных стенах
        if r["win"] and not s._shared(r, side) and L > 2.4 and not (r is s.rooms[0] and side == "S"):
            n = max(1, int(L / 3.2))
            for k in range(n):
                t = (k + 0.5) * L / n
                if any(g0 - 0.9 < t < g1 + 0.9 for g0, g1, _ in gaps): continue
                p0, p1 = P(t - 0.7), P(t + 0.7)
                nrm = {"N": (0, -0.02), "S": (0, 0.02), "E": (-0.02, 0), "W": (0.02, 0)}[side]
                q0 = (p0[0] + nrm[0], p0[1] + nrm[1]); q1 = (p1[0] + nrm[0], p1[1] + nrm[1])
                s.m.face([s.W(*q0, 0.9), s.W(*q1, 0.9), s.W(*q1, 2.35), s.W(*q0, 2.35)], [(0, 0), (1, 0), (1, 1), (0, 1)], "fx_int_window")
                s.m.face([s.W(q0[0] - nrm[0] * 9, q0[1] - nrm[1] * 9, 0.86), s.W(q1[0] - nrm[0] * 9, q1[1] - nrm[1] * 9, 0.86), s.W(*q1, 0.86), s.W(*q0, 0.86)][::1], [(0, 0), (1, 0), (1, 1), (0, 1)], "ph_white_plaster_rough_01")
    def place(s, key, u, v, rot_deg=0.0, z=0.0, scale=1.0):
        s.items.append((key, u, v, z, rot_deg, scale))
    def wall_item(s, key, room, side, t, gap=0.05, z=0.0, scale=1.0):
        r = next(q for q in s.rooms if q["nm"] == room); d = bpy.data.meshes[key]["dims"]; dep = d[1] * scale / 2 + gap + T
        if side == "N": u, v, rot = r["u0"] + (r["u1"] - r["u0"]) * t, r["v1"] - dep, 0
        elif side == "S": u, v, rot = r["u0"] + (r["u1"] - r["u0"]) * t, r["v0"] + dep, 180
        elif side == "E": u, v, rot = r["u1"] - dep, r["v0"] + (r["v1"] - r["v0"]) * t, -90
        else: u, v, rot = r["u0"] + dep, r["v0"] + (r["v1"] - r["v0"]) * t, 90
        s.place(key, u, v, rot, z, scale)
    def counter(s, u0, u1, v0, v1, h=1.0, top="ph_dark_paneled_wood", side="ph_wooden_panels"):
        m = s.m
        for (a, b) in (((u0, v0), (u1, v0)), ((u1, v0), (u1, v1)), ((u1, v1), (u0, v1)), ((u0, v1), (u0, v0))):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            m.face([s.W(*a, 0), s.W(*b, 0), s.W(*b, h), s.W(*a, h)], [(0, 0), (L / 2, 0), (L / 2, h / 2), (0, h / 2)], side)
        m.face([s.W(u0 - 0.03, v0 - 0.03, h), s.W(u1 + 0.03, v0 - 0.03, h), s.W(u1 + 0.03, v1 + 0.03, h), s.W(u0 - 0.03, v1 + 0.03, h)],
               [(0, 0), ((u1 - u0) / 2, 0), ((u1 - u0) / 2, (v1 - v0) / 2), (0, (v1 - v0) / 2)], top)
    def bars(s, u0, u1, v, h=2.6, step=0.14, gate=None):
        n = int((u1 - u0) / step)
        for k in range(n + 1):
            u = u0 + k * step
            if gate and gate[0] < u < gate[1]: continue
            s.m.face([s.W(u - 0.02, v, 0), s.W(u + 0.02, v, 0), s.W(u + 0.02, v, h), s.W(u - 0.02, v, h)], [(0, 0), (1, 0), (1, 1), (0, 1)], "fx_pole")
            s.m.face([s.W(u + 0.02, v, 0), s.W(u - 0.02, v, 0), s.W(u - 0.02, v, h), s.W(u + 0.02, v, h)], [(0, 0), (1, 0), (1, 1), (0, 1)], "fx_pole")
        for z in (0.05, h - 0.1):
            s.m.face([s.W(u0, v, z), s.W(u1, v, z), s.W(u1, v, z + 0.08), s.W(u0, v, z + 0.08)], [(0, 0), (1, 0), (1, 1), (0, 1)], "fx_pole")
    def finish(s, coll):
        m = s.m
        for r in s.rooms:
            u0, u1, v0, v1, h = r["u0"], r["u1"], r["v0"], r["v1"], r["h"]
            ft = r["ft"]
            m.face([s.W(u0, v0), s.W(u1, v0), s.W(u1, v1), s.W(u0, v1)], [(u0 / ft, v0 / ft), (u1 / ft, v0 / ft), (u1 / ft, v1 / ft), (u0 / ft, v1 / ft)], r["floor"])
            m.face([s.W(u0, v1, h), s.W(u1, v1, h), s.W(u1, v0, h), s.W(u0, v0, h)], [(0, 0), (1, 0), (1, 1), (0, 1)], r["ceil"])
            for sd in "NSEW": s._wall(r, sd)
            # светильник в центре
            cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
            m.face([s.W(cu - 0.35, cv - 0.35, h - 0.03), s.W(cu - 0.35, cv + 0.35, h - 0.03), s.W(cu + 0.35, cv + 0.35, h - 0.03), s.W(cu + 0.35, cv - 0.35, h - 0.03)],
                   [(0, 0), (1, 0), (1, 1), (0, 1)], "fx_int_lamp")
        # входная дверь (выход на улицу) за спиной игрока
        r0 = s.rooms[0]; v = r0["v0"] + T + 0.02
        m.face([s.W(-0.55, v, 0), s.W(0.55, v, 0), s.W(0.55, v, 2.2), s.W(-0.55, v, 2.2)], [(0.29, 0), (0.71, 0), (0.71, 0.86), (0.29, 0.86)], "fx_door_entr")
        o = m.build(coll); o["interior"] = 1; o["kind"] = "shell"
        for key, u, v, z, rot, sc in s.items:
            if key not in bpy.data.meshes: continue
            fo = bpy.data.objects.new(f"{s.name}.{key}", bpy.data.meshes[key]); coll.objects.link(fo)
            fo.location = s.W(u, v, z); fo.rotation_euler = (0, 0, s.a + math.radians(rot)); fo.scale = (sc, sc, sc)
            fo["interior"] = 1; fo["kind"] = "furniture"
        ex = s.W(0, r0["v0"] + 0.9, 1.0)
        return {"name": s.name, "spawn": [round(c, 4) for c in (s.S.x, s.S.y, s.S.z + 1.0)], "angle": round(math.degrees(s.a), 2),
                "exit_marker": [round(c, 3) for c in ex], "interior": 1, "rooms": len(s.rooms), "items": len(s.items)}


# ================= ШАБЛОНЫ =================
F = lambda k: "hzF_" + k.lower()


def apt(I, size, style):
    """квартира/дом: прихожая -> гостиная, кухня, спальни, санузел. size 0..6"""
    wallp = {"village": "ph_wooden_panels", "econom": "ph_decrepit_wallpaper", "mid": "ph_beige_wall_001", "high": "ph_beige_wall_002", "lux": "ph_painted_plaster_wall"}[style]
    floor = {"village": "ph_wood_floor", "econom": "ph_laminate_floor", "mid": "ph_laminate_floor_02", "high": "ph_herringbone_parquet", "lux": "ph_marble_tiles"}[style]
    tile = "ph_interior_tiles" if style in ("econom", "village") else ("ph_floor_tiles_08" if style == "mid" else "ph_marble_tiles")
    k = [0.75, 0.85, 1.0, 1.08, 1.2, 1.4, 1.7][size]
    LW, LD = 5.5 * k, 4.5 * k
    I.room("hall", -1.4, 1.4, -2.2, 1.6, wallp, floor, windows=False)
    I.room("living", -1.4 - LW * 0.25, -1.4 - LW * 0.25 + LW, 1.6, 1.6 + LD, wallp, floor)
    I.room("kitchen", 1.4, 1.4 + 3.4 * k, -2.2, 1.6, "ph_square_tiles_03" if style != "village" else wallp, tile)
    if size >= 1: I.room("bath", -1.4 - 2.2 * k, -1.4, -2.2, 1.6, "ph_long_white_tiles", tile, windows=False)
    lv = I.rooms[1]
    I.wall_item(F("Sofa_01") if size < 4 else F("sofa_03"), "living", "N", 0.5)
    I.place(F("CoffeeTable_01") if size < 4 else F("modern_coffee_table_01"), (lv["u0"] + lv["u1"]) / 2, lv["v1"] - 2.2)
    I.wall_item(F("Television_01") if size < 3 else F("television_02"), "living", "S", 0.72, z=0.0)
    I.wall_item(F("ArmChair_01"), "living", "W", 0.55)
    I.wall_item(F("potted_plant_01"), "living", "E", 0.9)
    if size >= 2: I.wall_item(F("wooden_bookshelf_worn") if style != "lux" else F("modern_wooden_cabinet"), "living", "E", 0.4)
    if size >= 4: I.place(F("Chandelier_01"), (lv["u0"] + lv["u1"]) / 2, (lv["v0"] + lv["v1"]) / 2, z=lv["h"] - 1.0)
    kt = next(q for q in I.rooms if q["nm"] == "kitchen")
    I.wall_item(F("electric_stove"), "kitchen", "S", 0.3); I.wall_item(F("drawer_cabinet"), "kitchen", "S", 0.65)
    I.place(F("dining_table"), (kt["u0"] + kt["u1"]) / 2 + 0.3, kt["v1"] - 1.3, 90)
    I.wall_item(F("dining_chair_02"), "kitchen", "E", 0.6, gap=0.6)
    if size >= 2: I.wall_item(F("vintage_microwave"), "kitchen", "S", 0.85, z=0.0)
    I.wall_item(F("wall_clock"), "hall", "E", 0.5, z=1.8)
    # спальни
    nb = [0, 1, 1, 2, 2, 3, 3][size]
    u = lv["u1"]
    for b in range(nb):
        w = 4.0 * k
        I.room(f"bed{b}", u, u + w, 1.6, 1.6 + LD, wallp, floor); u += w
        I.wall_item(F("old_bed_frame") if style in ("village", "econom") else F("vintage_day_bed"), f"bed{b}", "N", 0.5)
        I.wall_item(F("ClassicNightstand_01"), f"bed{b}", "N", 0.12); I.wall_item(F("drawer_cabinet"), f"bed{b}", "S", 0.7)
    if size == 0:      # деревенский: одна большая комната без отдельной спальни
        I.wall_item(F("old_bed_frame"), "living", "E", 0.5)


def shop247(I):
    I.room("hall", -5, 5, -2.2, 8, "ph_painted_plaster_wall", "ph_large_grey_tiles", ft=1.2)
    for i, u in enumerate((-3.2, -0.4, 2.4)):
        for j, v in enumerate((2.0, 4.6)): I.place(F("steel_frame_shelves_02") if (i + j) % 2 else F("wooden_display_shelves_01"), u, v, 90 if j else 90)
    I.counter(-4.6, -2.6, -1.4, 0.0); I.place(F("CashRegister_01"), -3.6, -0.7, 180, z=1.0)
    I.wall_item(F("worn_metal_rack"), "hall", "N", 0.2); I.wall_item(F("worn_metal_rack"), "hall", "N", 0.8)
    I.wall_item(F("security_camera_01"), "hall", "N", 0.5, z=2.4); I.place(F("mounted_fluorescent_lights"), 0, 3, z=2.75)


def phones(I):
    I.room("hall", -4, 4, -2.2, 6, "ph_painted_plaster_wall", "ph_terrazzo_tiles", ft=1.5)
    I.counter(-1.8, 1.8, 4.0, 4.7, top="ph_marble_tiles", side="ph_wooden_panels"); I.place(F("CashRegister_01"), 0.8, 4.3, 0, z=1.0)
    for t in (0.2, 0.5, 0.8): I.wall_item(F("wooden_display_shelves_01"), "hall", "W", t)
    I.wall_item(F("television_02"), "hall", "N", 0.2, z=1.2); I.wall_item(F("potted_plant_02"), "hall", "S", 0.85)


def hotel(I):
    I.room("lobby", -6, 6, -2.2, 9, "ph_beige_wall_002", "ph_marble_tiles", ft=1.5, h=4.0)
    I.counter(-2.5, 2.5, 6.5, 7.3, top="ph_marble_tiles", side="ph_dark_paneled_wood")
    I.place(F("Chandelier_01"), 0, 3.5, z=2.6); I.place(F("Sofa_01"), -4.6, 2.5, -90); I.place(F("sofa_02"), 4.6, 2.5, 90)
    I.place(F("modern_coffee_table_01"), -3.4, 2.5); I.place(F("modern_coffee_table_01"), 3.4, 2.5)
    for u in (-5.3, 5.3): I.place(F("potted_plant_01"), u, -1.3)
    I.wall_item(F("vintage_grandfather_clock_01") if "hzF_vintage_grandfather_clock_01" in bpy.data.meshes else F("wall_clock"), "lobby", "N", 0.85, z=0 if "hzF_vintage_grandfather_clock_01" in bpy.data.meshes else 2.2)


def carsalon(I):
    I.room("hall", -10, 10, -2.2, 14, "ph_painted_plaster_wall", "ph_marble_tiles", ft=2.0, h=5.0)
    I.counter(6.0, 9.0, 1.0, 2.0, top="ph_marble_tiles", side="ph_wooden_panels")
    for p in ((7.5, 3.2), (-8.5, 12.5), (8.5, 12.5), (-8.5, -1.2)): I.place(F("potted_plant_01"), *p)
    I.place(F("modern_arm_chair_01") if "hzF_modern_arm_chair_01" in bpy.data.meshes else F("ArmChair_01"), 7.0, 4.5, 180)
    for u in (-5, 0, 5): I.place(F("mounted_fluorescent_lights"), u, 6, z=4.95)


def garage(I):          # стайлинг / техцентр / шиномонтаж (одна точка на сервере)
    I.room("box", -8, 8, -2.2, 12, "ph_concrete_floor_painted", "ph_smooth_concrete_floor", ft=3.0, h=5.0, windows=False)
    I.wall_item(F("tool_cart"), "box", "W", 0.3); I.wall_item(F("industrial_storage_cart"), "box", "W", 0.6)
    for t in (0.2, 0.45, 0.7): I.wall_item(F("worn_metal_rack"), "box", "E", t)
    I.wall_item(F("steel_frame_shelves_02"), "box", "N", 0.2); I.wall_item(F("power_box_01"), "box", "N", 0.8, z=1.3)
    I.counter(-7.5, -5.5, -1.6, -0.6, top="fx_concrete", side="fx_prof_wall"); I.place(F("CashRegister_01"), -6.5, -1.1, 180, z=1.0)
    for u in (-4, 4): I.place(F("mounted_fluorescent_lights"), u, 5, z=4.95)


def guns(I):
    I.room("hall", -4, 4, -2.2, 7, "ph_dark_paneled_wood", "ph_rubber_tiles", ft=1.0, windows=False)
    I.counter(-3.6, 3.6, 4.3, 5.0, top="ph_dark_paneled_wood", side="fx_prof_wall"); I.place(F("CashRegister_01"), 2.5, 4.6, 0, z=1.0)
    for t in (0.2, 0.5, 0.8): I.wall_item(F("worn_metal_rack"), "hall", "N", t)
    I.wall_item(F("security_camera_02") if "hzF_security_camera_02" in bpy.data.meshes else F("security_camera_01"), "hall", "S", 0.8, z=2.4)


def accessories(I):
    I.room("hall", -4.5, 4.5, -2.2, 7, "ph_beige_wall_001", "ph_herringbone_parquet", ft=1.5)
    for t in (0.25, 0.75): I.wall_item(F("wooden_display_shelves_01"), "hall", "W", t); I.wall_item(F("wooden_display_shelves_01"), "hall", "E", t)
    I.wall_item(F("ornate_mirror_01"), "hall", "N", 0.3, z=0.6); I.wall_item(F("BarberShopChair_01"), "hall", "N", 0.7, gap=0.6)
    I.counter(-1.2, 1.2, 2.2, 2.9, top="ph_marble_tiles"); I.place(F("CashRegister_01"), 0.6, 2.55, 0, z=1.0)


def casino(I):
    I.room("hall", -9, 9, -2.2, 14, "ph_dark_paneled_wood", "ph_dirty_carpet", ft=3.0, h=4.5, windows=False)
    for u in (-5, 0, 5):
        for v in (3, 8):
            I.place(F("dining_table"), u, v, 90)
            for du in (-1.2, 1.2): I.place(F("bar_chair_round_01"), u + du, v)
    I.counter(-8.5, -6.5, 1, 11, top="ph_marble_tiles", side="ph_dark_paneled_wood")
    for v in (2, 5, 8): I.place(F("bar_chair_round_01"), -5.9, v)
    for p in ((0, 5.5), (0, 10.5)): I.place(F("Chandelier_01"), *p, z=3.3)


def kpz(I):
    I.room("corr", -2, 2, -2.2, 10, "fx_concrete", "ph_concrete_floor_painted", ft=2.0, windows=False)
    for i, v0 in enumerate((0.0, 3.4, 6.8)):
        I.room(f"cell{i}", 2, 6, v0, v0 + 3.2, "fx_concrete", "ph_concrete_floor_painted", windows=False)
        I.gap(f"cell{i}", "W", v0 + 1.6, 3.0, 2.6); I.gap("corr", "E", v0 + 1.6, 3.0, 2.6)
        I.place(F("painted_wooden_bench") if "hzF_painted_wooden_bench" in bpy.data.meshes else F("WoodenTable_01"), 5.2, v0 + 1.6, -90)
    I.wall_item(F("metal_office_desk"), "corr", "W", 0.15); I.wall_item(F("GreenChair_01"), "corr", "W", 0.3)
    I.wall_item(F("security_camera_01"), "corr", "N", 0.5, z=2.4)


# ================= СБОРКА =================
sc = bpy.data.scenes.get(SCENE_I) or bpy.data.scenes.new(SCENE_I)
for o in list(sc.objects): bpy.data.objects.remove(o)
root = bpy.data.collections.get("HORZ_interiors") or bpy.data.collections.new("HORZ_interiors")
if root.name not in sc.collection.children: sc.collection.children.link(root)
import csv
PTS = [r for r in csv.DictReader(open("/srv/blender/projects/horz/coords/coords.csv", encoding="utf-8")) if (r.get("interior") or "0") == "1"]
STY = {0: "village", 1: "econom", 2: "mid", 3: "mid", 4: "high", 5: "lux", 6: "lux"}
OUT = []; seen = set()
for r in PTS:
    x, y, z, a = float(r["x"]), float(r["y"]), float(r["z"]), float(r["angle"] or 0)
    key = (round(x, 1), round(y, 1), round(z, 1))
    nm = r["name_or_id"]
    if key in seen:
        OUT.append({"name": nm, "shared_with_previous_point": True, "spawn": [x, y, z]}); continue
    seen.add(key)
    safe = "".join(c if c.isalnum() else "_" for c in nm)[:40]
    I = Interior(safe, x, y, z, a)
    if nm.startswith("house_type_"):
        t = int(nm.split("_")[2]); apt(I, t, STY[t])
    elif "24/7" in nm: shop247(I)
    elif "Сотовый" in nm: phones(I)
    elif "Отель" in nm: hotel(I)
    elif "Автосалон" in nm: carsalon(I)
    elif any(k in nm for k in ("Стайлинг", "Технический", "Шиномонтаж")): garage(I)
    elif "оружия" in nm: guns(I)
    elif "аксессуаров" in nm: accessories(I)
    elif "Казино" in nm: casino(I)
    elif "KPZ" in nm: kpz(I)
    else: continue
    c = bpy.data.collections.get("int • " + nm) or bpy.data.collections.new("int • " + nm)
    if c.name not in root.children: root.children.link(c)
    info = I.finish(c); info["source_point"] = nm; OUT.append(info)
json.dump(OUT, open("/srv/blender/projects/horz/interiors_v1.json", "w"), ensure_ascii=False, indent=1)
print("интерьеров:", len([o for o in OUT if "rooms" in o]), "| объектов:", len(sc.objects))
for o in OUT: print(o.get("source_point", o["name"]), o.get("rooms"), o.get("items"))
