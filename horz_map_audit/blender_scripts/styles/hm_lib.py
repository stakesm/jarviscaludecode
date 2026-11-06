
# ===== HORZ: тестовый квартал Арзамаса — разные дома по стилям (OSM + свои текстуры) =====
import bpy, bmesh, json, math, random, os, collections
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

TEXD = ["/srv/blender/assets/horz_facades", "/srv/blender/assets/gpt_textures", "/srv/blender/assets/panelka_512", "/srv/blender/assets/horz_district_tex"]


def mat(key):
    m = bpy.data.materials.get(key)
    if m: return m
    m = bpy.data.materials.new(key); m.use_nodes = True
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    im = None
    for d in TEXD:
        p = f"{d}/{key}.png"
        if os.path.exists(p): im = bpy.data.images.load(p, check_existing=True); im.name = key; break
    if im:
        tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = im; nt.links.new(tx.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.35 if key in ("fx_gold",) else 0.8
    if key == "fx_gold": b.inputs['Metallic'].default_value = 0.9
    try: m.dff.tex_name = key
    except Exception: pass
    return m


class M:
    """Меш с явными UV: квадраты/полигоны, у каждого свой материал."""
    def __init__(s, name): s.name = name; s.v = []; s.f = []; s.uv = []; s.mk = []
    def face(s, pts, uvs, key):
        i = len(s.v); s.v += [tuple(p) for p in pts]; s.f.append(tuple(range(i, i + len(pts)))); s.uv.append(list(uvs)); s.mk.append(key)
    def quad(s, a, b, z0, z1, u0, u1, v0, v1, key, off=0.0):
        """вертикальная стена от a к b (наружу — справа)"""
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1; nx, ny = dy / L * off, -dx / L * off
        s.face([(a[0] + nx, a[1] + ny, z0), (b[0] + nx, b[1] + ny, z0), (b[0] + nx, b[1] + ny, z1), (a[0] + nx, a[1] + ny, z1)],
               [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], key)
    def poly(s, pts, z, key, tile=4.0, down=False):
        tris = tessellate_polygon([[Vector((p[0], p[1], 0)) for p in pts]])
        for t in tris:
            q = [pts[k] for k in t]
            ar = (q[1][0] - q[0][0]) * (q[2][1] - q[0][1]) - (q[2][0] - q[0][0]) * (q[1][1] - q[0][1])
            if (ar < 0) != down: q = q[::-1]
            s.face([(p[0], p[1], z) for p in q], [(p[0] / tile, p[1] / tile) for p in q], key)
    def box(s, c, sx, sy, z0, z1, ang, key, tile=2.0, bottom=False):
        ca, sa = math.cos(ang), math.sin(ang)
        P = [(c[0] + ca * x - sa * y, c[1] + sa * x + ca * y) for x, y in ((-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2))]
        for i in range(4):
            a, b = P[i], P[(i + 1) % 4]; L = math.hypot(b[0] - a[0], b[1] - a[1])
            s.quad(a, b, z0, z1, 0, L / tile, 0, (z1 - z0) / tile, key)
        s.poly(P, z1, key, tile)
        if bottom: s.poly(P, z0, key, tile, down=True)
    def build(s, coll):
        me = bpy.data.meshes.new(s.name); keys = list(dict.fromkeys(s.mk))
        me.from_pydata(s.v, [], s.f)
        for k in keys: me.materials.append(mat(k))
        uvl = me.uv_layers.new(name="UVMap")
        li = 0
        for pi, p in enumerate(me.polygons):
            p.material_index = keys.index(s.mk[pi])
            for j in range(p.loop_total): uvl.data[p.loop_start + j].uv = s.uv[pi][j]
        me.validate(); me.update()
        o = bpy.data.objects.new(s.name, me); coll.objects.link(o)
        return o, len(s.f)


# ---------- стили ----------
# tex: фасадные варианты; fh: высота этажа; bay: ширина пролёта; ground: что на 1 этаже; roof: варианты крыши
STY = {
    "panel9":  dict(tex=["fx_panel_0", "fx_panel_1", "fx_panel_2", "fx_panel_3"], fh=2.8, bay=3.2, roof=["flat"], balc=0.55, entr=True, plinth=0.9),
    "khrush":  dict(tex=["fx_khrush_0", "fx_khrush_1", "fx_khrush_2"], fh=2.75, bay=3.1, roof=["flat", "gable_low"], balc=0.45, entr=True, plinth=0.7),
    "stalin":  dict(tex=["fx_stalin_0", "fx_stalin_1", "fx_stalin_2", "fx_stalin_3", "fx_stalin_4"], fh=3.4, bay=3.6, roof=["hip"], balc=0.15, entr=True, cornice=True, plinth=1.0),
    "oldbrick": dict(tex=["fx_oldbrick_0", "fx_oldbrick_1"], fh=3.5, bay=3.4, roof=["hip", "gable"], balc=0.0, plinth=0.8, cornice=True),
    "modern":  dict(tex=["fx_modern_0", "fx_modern_1", "fx_modern_2"], fh=3.0, bay=3.0, roof=["flat"], balc=0.0, entr=True, plinth=0.5),
    "office":  dict(tex=["fx_office_0", "fx_office_1"], fh=3.3, bay=3.0, roof=["flat"], balc=0.0, plinth=0.6),
    "wood":    dict(tex=["fx_wood_0", "fx_wood_1", "fx_wood_2"], fh=2.8, bay=3.0, roof=["gable", "hip"], balc=0.0, plinth=0.6),
    "siding":  dict(tex=["fx_siding_0", "fx_siding_1", "fx_siding_2"], fh=2.9, bay=3.2, roof=["gable", "hip"], balc=0.0, plinth=0.5),
    "shop":    dict(tex=["fx_shop_0", "fx_shop_1", "fx_shop_2"], fh=3.6, bay=3.4, roof=["flat"], balc=0.0, plinth=0.0),
    "garage":  dict(tex=["pk_GarageFront"], fh=2.6, bay=3.2, roof=["flat"], balc=0.0, plinth=0.0),
    "indust":  dict(tex=["fx_prof_wall", "fx_concrete"], fh=5.0, bay=6.0, roof=["flat", "gable_low"], balc=0.0, plinth=0.6),
    "mansion": dict(tex=["fx_stalin_2", "fx_stalin_0", "fx_stalin_3", "fx_siding_0", "fx_oldbrick_0", "fx_modern_2"], fh=3.4, bay=3.8, roof=["hip"], balc=0.0, plinth=0.8, cornice=True),
    "church":  dict(tex=["fx_church"], fh=4.5, bay=3.4, roof=["hip"], balc=0.0, plinth=1.0, cornice=True),
}
ROOFT = {"flat": ["hd_roof_bitumen"], "gable_low": ["pk_Slating1", "fx_roof_2"], "gable": ["fx_roof_0", "fx_roof_1", "fx_roof_2", "fx_roof_3", "pk_RoofTiles", "pk_Slating1"],
         "hip": ["fx_roof_0", "fx_roof_1", "fx_roof_2", "fx_roof_3"]}


def area(p):
    return 0.5 * sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))


def simplify(p):
    out = []
    for i, q in enumerate(p):
        a, b = p[i - 1], p[(i + 1) % len(p)]
        cr = (q[0] - a[0]) * (b[1] - q[1]) - (q[1] - a[1]) * (b[0] - q[0])
        if math.hypot(q[0] - a[0], q[1] - a[1]) < 0.6: continue
        if abs(cr) < 0.4: continue
        out.append(q)
    return out


def obb(p):
    best = None
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]; ang = math.atan2(b[1] - a[1], b[0] - a[0])
        ca, sa = math.cos(-ang), math.sin(-ang)
        xs = [q[0] * ca - q[1] * sa for q in p]; ys = [q[0] * sa + q[1] * ca for q in p]
        A = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if best is None or A < best[0]: best = (A, ang, min(xs), max(xs), min(ys), max(ys))
    A, ang, x0, x1, y0, y1 = best
    if x1 - x0 < y1 - y0: ang += math.pi / 2; x0, x1, y0, y1 = y0, y1, -x1, -x0
    ca, sa = math.cos(ang), math.sin(ang)
    W = lambda x, y: (x * ca - y * sa, x * sa + y * ca)
    return A, ang, (x0, x1, y0, y1), W


def roof(m, p, z, kind, key, rng):
    A, ang, (x0, x1, y0, y1), W = obb(p)
    rect = abs(area(p)) / A > 0.86 and len(p) <= 8
    if kind == "flat" or not rect:
        m.poly(p, z + 0.02, key, 6.0)
        for i in range(len(p)):                                 # парапет
            a, b = p[i], p[(i + 1) % len(p)]; L = math.hypot(b[0] - a[0], b[1] - a[1])
            m.quad(a, b, z - 0.01, z + 0.6, 0, L / 3, 0, 0.2, "fx_concrete", off=0.0)
            m.quad(b, a, z, z + 0.6, 0, L / 3, 0, 0.2, "fx_concrete", off=0.25)
        if A > 150 and rng.random() < 0.8:                        # выход на крышу / вентшахта
            c = W((x0 + x1) / 2 + rng.uniform(-3, 3), (y0 + y1) / 2); m.box(c, 3.0, 2.4, z, z + 2.2, ang, "fx_concrete", 2.8)
        return
    e = 0.45; x0 -= e; x1 += e; y0 -= e; y1 += e
    pitch = {"gable_low": 0.18, "gable": 0.55, "hip": 0.42}[kind] * rng.uniform(0.85, 1.15)
    hh = (y1 - y0) / 2 * pitch * 2 if kind != "gable_low" else (y1 - y0) / 2 * pitch
    hh = min(hh, 4.2 if kind != "gable_low" else 1.6)
    ym = (y0 + y1) / 2; zr = z + hh
    ins = (y1 - y0) / 2 if kind == "hip" else 0.0
    ins = min(ins, (x1 - x0) / 2 - 0.1)
    P = lambda x, y, zz: (*W(x, y), zz)
    r0, r1 = (x0 + ins, ym), (x1 - ins, ym)
    L = (x1 - x0); sl = math.hypot((y1 - y0) / 2, hh)
    m.face([P(x0, y0, z), P(x1, y0, z), P(*r1, zr), P(*r0, zr)], [(0, 0), (L / 3, 0), ((x1 - ins - x0) / 3, sl / 3), (ins / 3, sl / 3)], key)
    m.face([P(x1, y1, z), P(x0, y1, z), P(*r0, zr), P(*r1, zr)], [(0, 0), (L / 3, 0), ((x1 - ins - x0) / 3, sl / 3), (ins / 3, sl / 3)], key)
    if kind == "hip":
        m.face([P(x1, y0, z), P(x1, y1, z), P(*r1, zr)], [(0, 0), ((y1 - y0) / 3, 0), ((y1 - y0) / 6, sl / 3)], key)
        m.face([P(x0, y1, z), P(x0, y0, z), P(*r0, zr)], [(0, 0), ((y1 - y0) / 3, 0), ((y1 - y0) / 6, sl / 3)], key)
    else:
        return ("gable", P, x0, x1, y0, y1, ym, z, zr)


def dome(m, c, z, r, rng, key="fx_gold"):
    """луковичная глава: барабан + луковица + крест"""
    seg = 8
    prof = [(r * 0.75, 0), (r * 0.75, r * 1.6), (r * 1.0, r * 1.9), (r * 1.05, r * 2.4), (r * 0.75, r * 2.9), (r * 0.3, r * 3.3), (0.06, r * 3.6)]
    for k in range(len(prof) - 1):
        (ra, za), (rb, zb) = prof[k], prof[k + 1]
        kk = "fx_church" if k == 0 else key
        for i in range(seg):
            a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
            m.face([(c[0] + ra * math.cos(a0), c[1] + ra * math.sin(a0), z + za), (c[0] + ra * math.cos(a1), c[1] + ra * math.sin(a1), z + za),
                    (c[0] + rb * math.cos(a1), c[1] + rb * math.sin(a1), z + zb), (c[0] + rb * math.cos(a0), c[1] + rb * math.sin(a0), z + zb)],
                   [(i / seg, 0), ((i + 1) / seg, 0), ((i + 1) / seg, 1), (i / seg, 1)], kk)
    zt = z + r * 3.6
    m.box(c, 0.12, 0.12, zt, zt + 1.6, 0, "fx_gold", 1); m.box((c[0], c[1]), 0.9, 0.1, zt + 1.0, zt + 1.12, 0, "fx_gold", 1)


def house(m, p, sty, levels, rng, road_d, name=""):
    S_ = STY[sty]; fh = S_["fh"] * rng.uniform(0.96, 1.04); tex = rng.choice(S_["tex"])
    p = p if area(p) > 0 else p[::-1]
    H = levels * fh; edges = []
    shop_gf = sty in ("stalin", "khrush", "panel9", "oldbrick", "modern") and rng.random() < 0.55
    gtex = rng.choice(STY["shop"]["tex"])
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]; L = math.hypot(b[0] - a[0], b[1] - a[1])
        nb = max(1, round(L / S_["bay"])); u1 = nb / 2.0           # текстура = 2 пролёта
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); dx, dy = b[0] - a[0], b[1] - a[1]
        street = road_d(mid[0] + dy / L * 6, mid[1] - dx / L * 6) < 9 if L > 0 else False
        z0 = 0.0
        if sty == "shop" or (shop_gf and street and L > 7):
            m.quad(a, b, 0, fh, 0, nb / 2.0, 0, 1, gtex if sty != "shop" else tex); z0 = fh
            if L > 9 and rng.random() < 0.7:                      # вывеска над витриной
                sg = rng.choice(["sv_shop247", "sv_pharmacy", "sv_bar", "sv_clothes", "sv_phone", "sv_restaurant", "sv_market", "sv_post", "sv_bank", "sv_cash"])
                t = rng.uniform(0.25, 0.75); w = min(6.0, L * 0.5)
                c = (a[0] + dx * t, a[1] + dy * t); ux, uy = dx / L, dy / L
                m.quad((c[0] - ux * w / 2, c[1] - uy * w / 2), (c[0] + ux * w / 2, c[1] + uy * w / 2), fh - 0.95, fh - 0.15, 0, 1, 0, 1, sg, off=0.12)
            if sty == "shop":
                if levels > 1: m.quad(a, b, fh, H, 0, u1, 0, (levels - 1) / 2.0, rng.choice(["fx_office_0", "fx_panel_0"]))
                edges.append((a, b, L, street)); continue
        if H > z0: m.quad(a, b, z0, H, 0, u1, z0 / fh / 2.0, levels / 2.0, tex)
        if S_.get("plinth") and z0 == 0: m.quad(a, b, 0, S_["plinth"], 0, L / 3, 0, S_["plinth"] / 3, "fx_plinth", off=0.06)
        if S_.get("cornice"): m.quad(a, b, H - 0.15, H + 0.55, 0, L / 3, 0, 0.25, "fx_church" if sty == "church" else "pk_WhiteBricks", off=0.35)
        edges.append((a, b, L, street))
    # торцы карниза — простая полоса сверху
    # подъезды: на длинной «дворовой» стороне
    if S_.get("entr") and levels >= 3:
        cand = sorted([e for e in edges if e[2] > 10], key=lambda e: (e[3], -e[2]))
        if cand:
            a, b, L, st = cand[0]; n = max(1, int(L / 22)); dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            YARDS.append((a, b, L))
            ang = math.atan2(dy, dx)
            for k in range(n):
                t = (k + 0.5) / n * L; c = (a[0] + dx * t, a[1] + dy * t)
                m.quad((c[0] - dx * 0.9, c[1] - dy * 0.9), (c[0] + dx * 0.9, c[1] + dy * 0.9), 0, 2.7, 0, 1, 0, 0.92, "fx_door_entr", off=0.08)
                DOORS.append((round(c[0] + dy * 1.5, 2), round(c[1] - dx * 1.5, 2), sty, levels))
                cc = (c[0] + dy * 0.9, c[1] - dx * 0.9)
                m.box(cc, 2.6, 1.8, 2.75, 2.95, ang, "fx_concrete", 2.0, bottom=True)      # козырёк
                m.box((cc[0] + dy * 0.3, cc[1] - dx * 0.3), 2.0, 1.2, 0, 0.18, ang, "fx_concrete", 2.0)   # крыльцо
    # балконы
    if S_["balc"] > 0 and levels >= 3:
        btex = rng.choice(["fx_balc_0", "fx_balc_1", "fx_balc_2"])
        for a, b, L, st in sorted(edges, key=lambda e: -e[2])[:2]:
            if L < 12: continue
            nb = max(1, round(L / S_["bay"])); dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L; ang = math.atan2(dy, dx)
            per = rng.choice([2, 3]); ph = rng.randrange(per)
            for k in range(nb):
                if k % per != ph: continue
                t = (k + 0.5) * L / nb; c0 = (a[0] + dx * t, a[1] + dy * t)
                for f in range(1, levels):
                    if rng.random() > S_["balc"] + 0.35: continue
                    z = f * fh; c = (c0[0] + dy * 0.6, c0[1] - dx * 0.6)
                    w = L / nb * 0.85
                    glazed = rng.random() < 0.45
                    m.box(c, w, 1.2, z - 0.05, z + 0.1, ang, "fx_concrete", 2.0, bottom=True)
                    m.quad((c[0] + dy * 0.6 - dx * w / 2, c[1] - dx * 0.6 - dy * w / 2), (c[0] + dy * 0.6 + dx * w / 2, c[1] - dx * 0.6 + dy * w / 2),
                           z + 0.1, z + (2.5 if glazed else 1.05), 0, w / 3, 0, (2.4 if glazed else 0.95) / 3, "fx_balc_glass" if glazed else btex)
                    if glazed: m.box(c, w, 1.2, z + 2.5, z + 2.6, ang, btex, 2.0)
    # детали фасада как в российских городах: кондиционеры, тарелки, водостоки
    if sty in ("panel9", "khrush", "stalin", "modern", "oldbrick", "shop", "office") and levels >= 2:
        for a, b, L, st in edges:
            if L < 6: continue
            dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L; ang = math.atan2(dy, dx)
            nb = max(1, round(L / S_["bay"]))
            for k in range(nb):
                for f in range(1, levels):
                    rv = rng.random()
                    t = (k + 0.5) * L / nb + (S_["bay"] * 0.33 if rv < 0.5 else -S_["bay"] * 0.33)
                    if rv < 0.07:            # кондиционер
                        c = (a[0] + dx * t + dy * 0.2, a[1] + dy * t - dx * 0.2); z = f * fh + rng.uniform(0.3, 1.4)
                        m.box(c, 0.8, 0.32, z, z + 0.55, ang, "fx_ac", 0.8)
                    elif rv < 0.095:         # спутниковая тарелка
                        c = (a[0] + dx * t + dy * 0.35, a[1] + dy * t - dx * 0.35); z = f * fh + rng.uniform(1.6, 2.2)
                        m.box(c, 0.62, 0.08, z - 0.31, z + 0.31, ang, "fx_dish", 0.62)
                        m.box((a[0] + dx * t + dy * 0.15, a[1] + dy * t - dx * 0.15), 0.05, 0.35, z - 0.05, z + 0.05, ang, "fx_pole", 1.0)
            # водосточная труба на углу
            if sty in ("stalin", "oldbrick", "khrush") and rng.random() < 0.6:
                c = (a[0] + dx * 0.25 + dy * 0.12, a[1] + dy * 0.25 - dx * 0.12)
                m.box(c, 0.14, 0.14, 0.0, H - 0.1, ang, "fx_pole", 1.0)
    # крыша
    rk = rng.choice(S_["roof"])
    if levels <= 2 and sty in ("stalin", "khrush"): rk = "hip"
    g = roof(m, p, H + (0.55 if S_.get("cornice") else 0), rk, rng.choice(ROOFT[rk]), rng)
    if g:   # фронтоны
        _, P, x0, x1, y0, y1, ym, z, zr = g
        m.face([P(x0, y1, z), P(x0, y0, z), P(x0, ym, zr)], [(0, 0), ((y1 - y0) / 2, 0), ((y1 - y0) / 4, (zr - z) / 2)], tex if sty in ("wood", "siding") else "fx_prof_wall")
        m.face([P(x1, y0, z), P(x1, y1, z), P(x1, ym, zr)], [(0, 0), ((y1 - y0) / 2, 0), ((y1 - y0) / 4, (zr - z) / 2)], tex if sty in ("wood", "siding") else "fx_prof_wall")
    if sty == "church":
        A, ang, (x0, x1, y0, y1), W = obb(p)
        cx, cy = W((x0 + x1) / 2, (y0 + y1) / 2); r = min(x1 - x0, y1 - y0) * 0.16
        zt = H + 0.55 + (y1 - y0) / 2 * 0.42 * 0.8
        dome(m, (cx, cy), zt - 0.5, max(1.2, r), rng)
        if A > 220 and "собор" in name.lower():
            for sx in (-1, 1):
                for sy in (-1, 1):
                    q = W((x0 + x1) / 2 + sx * (x1 - x0) * 0.28, (y0 + y1) / 2 + sy * (y1 - y0) * 0.28)
                    dome(m, q, zt - 1.6, max(0.8, r * 0.55), rng, rng.choice(["fx_gold", "fx_roof_0", "fx_roof_3"]))
    return H


