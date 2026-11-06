
# ===== HORZ: полная карта v3 — 10 городов из OSM, у каждого свой набор стилей, свои текстуры =====
import bpy, json, math, random, collections
import numpy as np
SCENE = "HORZ • Карта v3 (стили городов)"
HALF = 3000.0; BASE = 10.0; WATER = 9.0
random.seed(11)
import time; T0 = time.time()

# город -> реальная основа, центр (lat, lon) СДВИНУТ к плотной застройке, размер, место на карте, профиль
def _sh(la, lo, dx, dy): return (la + dy / 110574.0, lo + dx / (111320.0 * math.cos(math.radians(la))))
TOWNS = [
    ("Нижегородск", "Кстово", _sh(56.1467, 44.1981, 100, -200), (1500, 1100), (-1875, 2100), "modern"),
    ("Арзамас", "Арзамас", _sh(55.3949, 43.8399, -900, -800), (1500, 1500), (200, 850), "center"),
    ("Батырево", "Батырево", _sh(55.0637, 47.6167, -100, 200), (900, 900), (1500, 1750), "mining"),
    ("Рублёвка", "Барвиха", _sh(55.7380, 37.2700, 100, 100), (900, 600), (-1150, 520), "mansion"),
    ("Лыткарино", "Лыткарино", (55.5785, 37.9030), (650, 800), (-2050, -80), "industry"),
    ("Береговой", "Николина Гора", _sh(55.6820, 37.0820, 100, 200), (600, 450), (-2150, -680), "elite"),
    ("Гарель", "Шатовка", _sh(55.2740, 43.6950, 300, -100), (900, 600), (2100, -150), "village"),
    ("Корякино", "Ленинское", _sh(55.2469, 43.8596, 0, -100), (800, 600), (525, -880), "village"),
    ("Бусаево", "Вад", _sh(55.5330, 44.1950, 400, -200), (900, 700), (-500, -1380), "village"),
    ("Южный", "Выкса", _sh(55.3170, 42.1830, 100, 200), (1300, 1250), (1850, -1820), "gov"),
]
REGIONS = [(g, r, ll, wh, t, k) for g, r, ll, wh, t, k in TOWNS]
RECTS = {g: (tx - w / 2, tx + w / 2, ty - h / 2, ty + h / 2) for g, r, ll, (w, h), (tx, ty), k in TOWNS}
# особые места вне городов (рельеф под ними ровный)
SPOTS = {"port": (-420, -60), "wedding": (2130, 1330), "autodrome": (-250, -2420), "army": (-600, 2440), "factory": (2620, 650),
         "towers": [(-2600, -1800), (100, 2750), (2800, 450), (900, -2650), (-1350, -1150)]}
FLATS = [(SPOTS["army"], 230, 180), (SPOTS["autodrome"], 150, 100), (SPOTS["factory"], 90, 80), (SPOTS["wedding"], 60, 60), ((-1250, -1950), 100, 100)] + [(t, 25, 25) for t in SPOTS["towers"]]

# ---------- вода и рельеф ----------
RIVERS = [([(-3150, 1150), (-1900, 1190), (-1000, 1150), (-640, 880), (-600, 300), (-560, -120), (-200, -330), (600, -330),
            (1300, -480), (1600, -760), (2050, -810), (2700, -800), (3150, -700)], 140),
          ([(-1080, 3150), (-1010, 2300), (-980, 1600), (-1000, 1150)], 110)]
LAKES = [((525, -1450), 210), ((2380, 1600), 230), ((-1250, -1950), 300)]
ISLANDS = [((-1250, -1950), 125, "fsin")]
RIV = [(catmull(pts, n=16), w) for pts, w in RIVERS]


def seg_d(px, py, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / max(1e-9, dx * dx + dy * dy)))
    return math.hypot(px - a[0] - dx * t, py - a[1] - dy * t)


def wdist(x, y):
    d = 1e9
    for pts, w in RIV:
        for a, b in zip(pts, pts[1:]):
            if abs(x - a[0]) < 600 and abs(y - a[1]) < 600: d = min(d, seg_d(x, y, a, b) - w / 2)
    for (cx, cy), r in LAKES: d = min(d, math.hypot(x - cx, y - cy) - r)
    for (cx, cy), r, k in ISLANDS:
        di = math.hypot(x - cx, y - cy)
        if di < r: d = r - di
    return d


def town_of(x, y, pad=0.0):
    for g, (x0, x1, y0, y1) in RECTS.items():
        if x0 - pad <= x <= x1 + pad and y0 - pad <= y <= y1 + pad: return g
    return None


def town_dist(x, y):
    d = 1e9
    for x0, x1, y0, y1 in RECTS.values():
        dx = max(x0 - x, 0, x - x1); dy = max(y0 - y, 0, y - y1); d = min(d, math.hypot(dx, dy))
    for (cx, cy), hw_, hh_ in FLATS:
        dx = max(abs(x - cx) - hw_, 0); dy = max(abs(y - cy) - hh_, 0); d = min(d, math.hypot(dx, dy))
    return d


def gz(x, y):
    hills = 6 * math.sin(x / 520.0 + 0.4) * math.cos(y / 610.0) + 3 * math.sin((x + y) / 260.0) + 1.5 * math.cos(x / 120.0 - y / 170.0)
    hills += 12 * max(0.0, (max(abs(x), abs(y)) - 2600) / 400)
    t = min(1.0, town_dist(x, y) / 150.0)
    z = BASE + max(0.0, hills + 4) * t * (t * (3 - 2 * t))
    wd = wdist(x, y)
    if wd < 0: return WATER - 4.0
    if wd < 40:
        k = wd / 40.0; return (WATER - 4.0) + (z - WATER + 4.0) * (k * k * (3 - 2 * k))
    return z


def road_z(x, y):
    z = gz(x, y); wd = wdist(x, y)
    if wd < 45: z = max(z, WATER + 6.0 - max(0.0, wd) * 0.12)
    return z


# ---------- сцена/коллекции/куски ----------
sc = bpy.data.scenes.get(SCENE) or bpy.data.scenes.new(SCENE)
bpy.context.window.scene = sc
for o in list(sc.objects): bpy.data.objects.remove(o)
for me in list(bpy.data.meshes):
    if me.users == 0 and me.name.startswith("v3_"): bpy.data.meshes.remove(me)
ROOT = bpy.data.collections.get("HORZ_v3") or bpy.data.collections.new("HORZ_v3")
if ROOT.name not in sc.collection.children: sc.collection.children.link(ROOT)
LAYER_RU = {"bld": "Здания", "road": "Улицы", "props": "Улицы-детали", "trees": "Деревья", "hw": "Трассы", "terrain": "Рельеф", "water": "Вода",
            "forest": "Лес", "buildings": "Заведения"}


def lcoll(layer):
    n = "v3 • " + LAYER_RU.get(layer, layer)
    c = bpy.data.collections.get(n) or bpy.data.collections.new(n)
    if c.name not in ROOT.children: ROOT.children.link(c)
    return c


def relink(ob, layer):      # перекрывает relink из fm_core: заведения — в нашу коллекцию
    for u in list(ob.users_collection): u.objects.unlink(ob)
    lcoll(layer).objects.link(ob); ob["layer"] = layer


def sec_of(x, y):
    i = int(max(0, min(11, (x + HALF) // 500))); j = int(max(0, min(11, (y + HALF) // 500))); return i, j


CH = {}
def chunk(x, y, layer):
    i, j = sec_of(x, y); k = (layer, i, j)
    if k not in CH: CH[k] = M(f"v3_{layer}_S{i:02d}_{j:02d}")
    return CH[k]


# ---------- глобальные индексы: дороги (для расстояний) и здания ----------
GR = collections.defaultdict(list); RID = [0]
def add_road_idx(p, w):
    RID[0] += 1; ri = RID[0]
    for a, b in zip(p, p[1:]):
        for gx in range(int(min(a[0], b[0]) // 40) - 1, int(max(a[0], b[0]) // 40) + 2):
            for gy in range(int(min(a[1], b[1]) // 40) - 1, int(max(a[1], b[1]) // 40) + 2): GR[(gx, gy)].append((a, b, w, ri))
    return ri


def road_d(x, y, excl=-1):
    best = 1e9
    for a, b, w, ri in GR.get((int(x // 40), int(y // 40)), []):
        if ri == excl: continue
        best = min(best, seg_d(x, y, a, b) - w / 2)
    return best


BG = collections.defaultdict(list)
def pin(x, y, P):
    c = False; j = len(P) - 1
    for i in range(len(P)):
        if (P[i][1] > y) != (P[j][1] > y) and x < (P[j][0] - P[i][0]) * (y - P[i][1]) / (P[j][1] - P[i][1] + 1e-12) + P[i][0]: c = not c
        j = i
    return c


def in_bld(x, y, pad=4.0):
    gx0, gy0 = int(x // 30), int(y // 30)
    for gx in range(gx0 - 2, gx0 + 3):
        for gy in range(gy0 - 2, gy0 + 3):
            for P in BG.get((gx, gy), []):
                if any(pin(x + ox, y + oy, P) for ox, oy in ((0, 0), (pad, 0), (-pad, 0), (0, pad), (0, -pad))): return True
    return False


def add_bld(p):
    cx = sum(q[0] for q in p) / len(p); cy = sum(q[1] for q in p) / len(p); BG[(int(cx // 30), int(cy // 30))].append(p)


# ---------- профили городов: какой стиль выбрать ----------
def pick(t, A, rng, ctr_d, kind):
    b = t.get("building", "yes"); lv = t.get("building:levels")
    try: lv = int(float(str(lv).split(";")[0]))
    except (TypeError, ValueError): lv = None
    nm = (t.get("name") or "").lower()
    if b in ("church", "cathedral", "chapel") or any(k in nm for k in ("церков", "собор", "часовн", "храм")):
        return "church", lv or (3 if A > 150 else 2)
    if b in ("garages", "garage", "carport"): return "garage", 1
    if b in ("shed", "hut", "barn", "greenhouse", "farm_auxiliary", "cowshed"): return ("garage", 1) if A < 60 else ("indust", 1)
    if b in ("industrial", "warehouse", "service", "construction", "factory", "hangar"): return ("indust", 1) if A > 60 else ("garage", 1)
    if b in ("retail", "commercial", "kiosk", "supermarket"):
        return (rng.choice(["shop", "shop", "modern"]) if kind in ("modern", "gov", "elite") else "shop"), lv or rng.choice([1, 1, 2])
    if b in ("school", "kindergarten", "college", "university", "hospital", "government", "public", "civic", "office"):
        st = {"gov": ["office", "stalin", "modern"], "modern": ["panel9", "office", "modern"], "center": ["stalin", "khrush", "panel9"]}.get(kind, ["khrush", "stalin", "oldbrick"])
        return rng.choice(st), lv or (2 if b == "kindergarten" else 3)
    small = A < 160 and (lv or 1) <= 2
    if b in ("house", "detached", "semidetached_house", "bungalow", "cabin") or (b == "yes" and small):
        if A < 22: return "garage", 1
        if kind in ("mansion", "elite"): return ("mansion", lv or rng.choice([2, 2, 3])) if A > 60 else ("siding", 1)
        if kind in ("village", "mining"): return rng.choice(["wood", "wood", "wood", "siding", "oldbrick"]), lv or rng.choice([1, 1, 1, 2])
        if kind == "center": return rng.choice(["wood", "wood", "siding", "oldbrick"] if ctr_d < 450 else ["wood", "siding", "siding"]), lv or rng.choice([1, 1, 2])
        return rng.choice(["siding", "siding", "wood", "mansion"]), lv or rng.choice([1, 2, 2])
    # многоэтажное/неизвестное
    if lv is None:
        if kind == "modern": lv = 2 if A < 250 else rng.choice([5, 5, 9, 9, 12, 16])
        elif kind == "industry": lv = 2 if A < 250 else rng.choice([5, 5, 9, 9, 12])
        elif kind == "gov": lv = 2 if A < 200 else rng.choice([3, 5, 9, 12])
        elif kind in ("mansion", "elite"): lv = rng.choice([2, 3]) if A < 900 else rng.choice([3, 5, 9])
        elif kind in ("village", "mining"): lv = 1 if A < 300 else rng.choice([2, 2, 3, 5])
        else: lv = 2 if A < 300 else (rng.choice([2, 3, 4]) if ctr_d < 350 else rng.choice([5, 5, 5, 9]))
    if kind in ("mansion", "elite") and lv <= 3 and A < 900: return "mansion", lv
    if lv >= 12: return rng.choice(["modern", "panel9"] if kind != "gov" else ["modern", "modern", "office"]), lv
    if lv >= 9: return rng.choice(["panel9", "panel9", "modern"] if kind not in ("gov", "elite") else ["modern", "panel9", "office"]), lv
    if lv >= 6: return rng.choice(["panel9", "stalin", "modern"]), lv
    if lv == 5: return rng.choice(["khrush", "khrush", "panel9"] if kind != "gov" else ["panel9", "khrush", "office"]), lv
    if lv >= 3:
        if kind == "center": return (rng.choice(["stalin", "stalin", "oldbrick", "khrush"]) if ctr_d < 450 else rng.choice(["khrush", "stalin"])), lv
        if kind == "gov": return rng.choice(["stalin", "office", "stalin"]), lv
        return rng.choice(["khrush", "khrush", "stalin"]), lv
    if kind == "center": return (rng.choice(["oldbrick", "stalin", "shop"]) if ctr_d < 400 else rng.choice(["oldbrick", "siding"])), lv
    if kind in ("village", "mining"): return rng.choice(["oldbrick", "khrush", "indust", "wood"]), lv
    if kind == "gov": return rng.choice(["stalin", "office", "shop", "oldbrick"]), lv
    return rng.choice(["oldbrick", "shop", "khrush", "siding"]), lv


# ---------- дорожные ленты ----------
ROADW = {"motorway": 16, "trunk": 15, "primary": 13, "secondary": 11, "tertiary": 9, "residential": 7, "unclassified": 6.5,
         "living_street": 6, "service": 4.5, "pedestrian": 6, "footway": 2.2, "track": 3.5, "path": 1.6, "cycleway": 2.0}
for k in ("motorway", "trunk", "primary", "secondary", "tertiary"): ROADW[k + "_link"] = ROADW[k] * 0.7
ASPH = {"motorway": "fx_asphalt", "trunk": "fx_asphalt", "primary": "fx_asphalt", "secondary": "fx_asphalt", "tertiary": "fx_asphalt_old",
        "residential": "fx_asphalt_old", "unclassified": "fx_asphalt_old", "living_street": "fx_asphalt_yard", "service": "fx_asphalt_yard",
        "pedestrian": "sidewalk_brick_paver_01", "footway": "fx_sidewalk", "cycleway": "fx_sidewalk", "track": "fx_dirt", "path": "fx_dirt"}
for k in ("motorway", "trunk", "primary", "secondary", "tertiary"): ASPH[k + "_link"] = ASPH[k]
ORDER = ["path", "track", "footway", "cycleway", "service", "living_street", "unclassified", "residential", "pedestrian",
         "tertiary_link", "tertiary", "secondary_link", "secondary", "primary_link", "primary", "trunk_link", "trunk", "motorway_link", "motorway"]
ZR, ZS = 0.10, 0.24


def norms(p):
    n = len(p); nr = []
    for i in range(n):
        a = p[max(0, i - 1)]; b = p[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1; nr.append((-dy / L, dx / L))
    return nr


def dense(p, step=4.0):
    out = [p[0]]
    for a, b in zip(p, p[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); k = max(1, int(L / step))
        for j in range(1, k + 1): out.append((a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k))
    return out


def strip(m, p, nr, o0, o1, z0, z1, key, tile, keep=None, zf=None):
    acc = 0.0
    for i in range(len(p) - 1):
        a, b = p[i], p[i + 1]; L = math.hypot(b[0] - a[0], b[1] - a[1]); (n0x, n0y), (n1x, n1y) = nr[i], nr[i + 1]
        za = zf(*a) if zf else 0.0; zb = zf(*b) if zf else 0.0
        if keep is None or keep(i):
            m.face([(a[0] + n0x * o0, a[1] + n0y * o0, za + z0), (a[0] + n0x * o1, a[1] + n0y * o1, za + z1),
                    (b[0] + n1x * o1, b[1] + n1y * o1, zb + z1), (b[0] + n1x * o0, b[1] + n1y * o0, zb + z0)],
                   [(o0 / tile, acc / tile), (o1 / tile, acc / tile), (o1 / tile, (acc + L) / tile), (o0 / tile, (acc + L) / tile)], key)
        acc += L


def clip_runs(p, x0, x1, y0, y1):
    runs, cur = [], []
    for q in p:
        if x0 <= q[0] <= x1 and y0 <= q[1] <= y1: cur.append(q)
        else:
            if len(cur) >= 2: runs.append(cur)
            cur = []
    if len(cur) >= 2: runs.append(cur)
    return runs


# ---------- деревья ----------
def ring(m, c, z0, z1, r0, r1, rot, key, seg=6):
    for i in range(seg):
        a0, a1 = rot + 2 * math.pi * i / seg, rot + 2 * math.pi * (i + 1) / seg
        if r1 > 0.01:
            m.face([(c[0] + r0 * math.cos(a0), c[1] + r0 * math.sin(a0), z0), (c[0] + r0 * math.cos(a1), c[1] + r0 * math.sin(a1), z0),
                    (c[0] + r1 * math.cos(a1), c[1] + r1 * math.sin(a1), z1), (c[0] + r1 * math.cos(a0), c[1] + r1 * math.sin(a0), z1)],
                   [(i / 2, 0), ((i + 1) / 2, 0), ((i + 1) / 2, 1), (i / 2, 1)], key)
        else:
            m.face([(c[0] + r0 * math.cos(a0), c[1] + r0 * math.sin(a0), z0), (c[0] + r0 * math.cos(a1), c[1] + r0 * math.sin(a1), z0), (c[0], c[1], z1)],
                   [(i / 2, 0), ((i + 1) / 2, 0), ((i + 0.5) / 2, 1)], key)


def tree(m, x, y, z, rr, spruce=None):
    h = rr.uniform(6, 13); spruce = rr.random() < 0.25 if spruce is None else spruce
    m.box((x, y), 0.35, 0.35, z, z + h * 0.45, rr.random(), "hd_bark", 1.0)
    if spruce:
        for j in range(3): ring(m, (x, y), z + h * (0.2 + j * 0.24), z + h * (0.55 + j * 0.2), 2.4 - j * 0.6, 0.0, rr.random(), "hd_foliage", 7)
    else:
        r = rr.uniform(2.2, 3.6); rot = rr.random(); z0, z1 = z + h * 0.4, z + h; zm = z0 + (z1 - z0) * 0.45
        ring(m, (x, y), z0, zm, r * 0.45, r, rot, "hd_foliage"); ring(m, (x, y), zm, z0 + (z1 - z0) * 0.8, r, r * 0.7, rot, "hd_foliage")
        ring(m, (x, y), z0 + (z1 - z0) * 0.8, z1, r * 0.7, 0.0, rot, "hd_foliage")


# ---------- заведения (готовые модели из fm_assets) ----------
PLANS = {
    "Нижегородск": ["Ж/д вокзал", "Порт", "Склад", "ГИБДД", "Больница", "ЗАГС", "Магазин 24/7", "Магазин 24/7", "Салон связи", "Автосалон"],
    "Арзамас": ["Больница", "Полиция", "ППС", "КПЗ", "Банк", "Почта", "СМИ", "Автовокзал", "Инкассация", "Курьер", "Оружейный", "Аксессуары",
                "Одежда", "Аптека", "Аренда", "Магазин 24/7", "Магазин 24/7", "Магазин 24/7", "Ресторан", "Бар", "Клуб", "Отель", "Рынок",
                "Пожарная", "База ОПГ", "Паркинг", "АЗС"],
    "Батырево": ["База ОПГ", "Казино", "Военкомат", "Шахта", "Магазин 24/7", "АЗС"],
    "Рублёвка": ["Магазин 24/7"],
    "Лыткарино": ["Автошкола", "Больница", "База ОПГ", "СТО", "Стайлинг", "Шиномонтаж", "Автомойка", "Механик", "Магазин 24/7"],
    "Береговой": ["Ресторан"],
    "Гарель": ["Склад", "Автосалон", "Лесопилка", "Магазин 24/7"],
    "Корякино": ["Ферма", "Магазин 24/7", "Лотерея"],
    "Бусаево": ["Таксопарк", "Магазин 24/7", "Аптека"],
    "Южный": ["Правительство", "Суд", "Банк", "ФБР", "Аукцион", "Автобусный парк", "Дальнобой", "Автопрокат", "Паркинг", "Магазин 24/7", "Одежда", "АЗС"],
}
for vt in {v for L in PLANS.values() for v in L}:
    key, fn, cat = VENUES[vt]; asset(key, fn, meta={"venue": vt, "category": cat})


def bbl(key):
    me = bpy.data.meshes[key]; xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    return min(xs), max(xs), min(ys), max(ys)


def rect_poly(ox, oy, ang, bb, pad=0.0):
    c, s = math.cos(ang), math.sin(ang)
    return [(ox + c * lx - s * ly, oy + s * lx + c * ly) for lx, ly in ((bb[0] - pad, bb[2] - pad), (bb[1] + pad, bb[2] - pad), (bb[1] + pad, bb[3] + pad), (bb[0] - pad, bb[3] + pad))]


ENTR = []; VEN = []; DOORS = []; YARDS = []; PRIV = []
stat = collections.Counter()

# ================= ГОРОДА =================
for game, real, (lat0, lon0), (w, h), (tx, ty), kind in TOWNS:
    J = json.load(open(f"/srv/blender/projects/horz/osm/reg_{real}.json"))
    N = {e["id"]: e for e in J["elements"] if e["type"] == "node"}
    Wy = [e for e in J["elements"] if e["type"] == "way"]
    kx = 111320.0 * math.cos(math.radians(lat0)); x0, x1, y0, y1 = RECTS[game]
    def xy(n): return ((n["lon"] - lon0) * kx + tx, (n["lat"] - lat0) * 110574.0 + ty)
    def wp(wy): return [xy(N[i]) for i in wy.get("nodes", []) if i in N]
    def inside(q, pad=0.0): return x0 + pad <= q[0] <= x1 - pad and y0 + pad <= q[1] <= y1 - pad
    # дороги
    troads = []
    for wy in Wy:
        hw = (wy.get("tags") or {}).get("highway")
        if hw not in ROADW or hw in ("path", "track", "cycleway"): continue
        for run in clip_runs(wp(wy), x0, x1, y0, y1):
            run = [q for q in run if wdist(*q) > 4]
            if len(run) < 2: continue
            ri = add_road_idx(run, ROADW[hw]) if hw not in ("footway", "service") else -1
            troads.append((hw, run, ri))
    # заведения вдоль крупных улиц, дверью к улице
    plan = list(PLANS.get(game, [])); major = [(p, ROADW[hw]) for hw, p, ri in troads if hw in ("primary", "secondary", "tertiary", "residential", "unclassified", "living_street")]
    random.shuffle(major); major.sort(key=lambda m: min(math.hypot(q[0] - tx, q[1] - ty) for q in m[0]))
    VR = []
    for pts, rw in major:
        for a, b in zip(pts, pts[1:]):
            if not plan: break
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 30: continue
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            for side in (1, -1):
                if not plan: break
                key = VENUES[plan[0]][0]; bb = bbl(key)
                nx, ny = -uy * side, ux * side; mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                off = rw / 2 + 4.0 - bb[2]; ox, oy = mx + nx * off, my + ny * off
                ang = math.atan2(-ny, -nx) + math.pi / 2
                poly = rect_poly(ox, oy, ang, bb, 1.0)
                if not all(inside(q, 5) for q in poly) or any(wdist(*q) < 15 for q in poly): continue
                if any(road_d(*q) < 1.0 for q in poly[2:]): continue
                if any(math.hypot(ox - q[0], oy - q[1]) < 120 and (any(pin(px, py, q[2]) for px, py in poly) or any(pin(px, py, poly) for px, py in q[2])) for q in VR): continue
                vt = plan.pop(0)
                o = inst(key, ox, oy, BASE + 0.05, ang, "buildings", game, {"venue": vt})
                door = o.matrix_world @ Vector(ANCH.get(key, {}).get("door", (0, -2, 0.3)))
                ENTR.append({"type": "venue", "venue": vt, "town": game, "x": round(door.x, 3), "y": round(door.y, 3), "z": round(door.z + 1.0, 3), "object": o.name})
                VR.append((ox, oy, rect_poly(ox, oy, ang, bb, 3.0))); add_bld(rect_poly(ox, oy, ang, bb, 0.5)); stat["заведения"] += 1
    if plan: print(game, "не влезли:", plan)
    VEN += VR
    # здания OSM
    nb0 = stat["здания"]
    for wy in Wy:
        t = wy.get("tags") or {}
        if "building" not in t or t.get("building") in ("roof", "grandstand", "ruins"): continue
        p = wp(wy)
        if len(p) < 4 or p[0] != p[-1]: continue
        p = simplify(p[:-1])
        if len(p) < 3 or not all(inside(q, 2) for q in p): continue
        A = abs(area(p))
        if A < 8 or A > 25000: continue
        cx = sum(q[0] for q in p) / len(p); cy = sum(q[1] for q in p) / len(p)
        if wdist(cx, cy) < 10: continue
        if any(math.hypot(cx - q[0], cy - q[1]) < 120 and (pin(cx, cy, q[2]) or any(pin(px, py, q[2]) for px, py in p)) for q in VR): continue
        rng = random.Random(wy["id"])
        sty, lv = pick(t, A, rng, math.hypot(cx - tx, cy - ty), kind)
        lv = max(1, min(lv, 25))
        nd = len(DOORS)
        house(chunk(cx, cy, "bld"), p, sty, lv, rng, road_d, t.get("name", ""))
        for d in DOORS[nd:]: ENTR.append({"type": "apartments", "town": game, "x": d[0], "y": d[1], "z": BASE + 1.0, "style": d[2], "levels": d[3]})
        add_bld(p); stat["здания"] += 1; stat[sty] += 1
        if sty in ("wood", "siding", "oldbrick", "mansion") and A < 420 and lv <= 3:
            PRIV.append((p, sty, A)); ENTR.append({"type": "house", "town": game, "x": round(cx, 2), "y": round(cy, 2), "z": BASE + 1.0, "style": sty})
    # добор частного сектора вдоль улиц (там, где OSM пустой): деревни, Рублёвка, Береговой, Батырево
    if kind in ("village", "mining", "mansion", "elite"):
        rng = random.Random(sum(map(ord, game))); add = 0
        for hw, p, ri in troads:
            if hw not in ("residential", "unclassified", "living_street", "tertiary"): continue
            pd = dense(p, 2.0); acc = 0.0; nxt = rng.uniform(5, 20)
            step = 34 if kind in ("mansion", "elite") else 24
            for i in range(len(pd) - 1):
                a, b = pd[i], pd[i + 1]; L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1; acc += L
                if acc < nxt: continue
                nxt = acc + step * rng.uniform(0.85, 1.25)
                ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
                for side in (1, -1):
                    if rng.random() < 0.15: continue
                    nx, ny = -uy * side, ux * side
                    if kind in ("mansion", "elite"): W_, D_, sb_ = rng.uniform(14, 22), rng.uniform(11, 16), rng.uniform(14, 20)
                    else: W_, D_, sb_ = rng.uniform(7, 11), rng.uniform(6, 9), rng.uniform(6, 10)
                    off = ROADW[hw] / 2 + sb_ + D_ / 2; cx, cy = a[0] + nx * off, a[1] + ny * off
                    poly = [(cx + ux * sx * W_ / 2 + nx * sy * D_ / 2, cy + uy * sx * W_ / 2 + ny * sy * D_ / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                    if not all(inside(q, 4) for q in poly) or any(wdist(*q) < 12 for q in poly): continue
                    if in_bld(cx, cy, max(W_, D_) * 0.5 + 6) or any(road_d(*q) < 3 for q in poly): continue
                    if any(math.hypot(cx - q[0], cy - q[1]) < 120 and pin(cx, cy, q[2]) for q in VR): continue
                    sty = ("mansion" if kind in ("mansion", "elite") else rng.choice(["wood", "wood", "wood", "siding", "oldbrick"]))
                    lv = rng.choice([2, 2, 3]) if sty == "mansion" else rng.choice([1, 1, 1, 2])
                    r2 = random.Random(int(cx * 13 + cy * 7))
                    house(chunk(cx, cy, "bld"), poly, sty, lv, r2, road_d); add_bld(poly)
                    PRIV.append((poly, sty, W_ * D_)); ENTR.append({"type": "house", "town": game, "x": round(cx, 2), "y": round(cy, 2), "z": BASE + 1.0, "style": sty})
                    stat["добор"] += 1; stat[sty] += 1; add += 1
    # улицы
    for hw, p, ri in troads:
        zi = ORDER.index(hw); wdt = ROADW[hw]; key = ASPH[hw]
        p = dense(p); nr = norms(p); m = chunk(p[0][0], p[0][1], "road")
        if hw == "footway": strip(m, p, nr, -wdt / 2, wdt / 2, 0.05, 0.05, key, 2.0); continue
        zr = ZR + zi * 0.003
        strip(m, p, nr, -wdt / 2, wdt / 2, zr, zr, key, 6.0 if key.startswith("fx_asph") else 2.0)
        if hw in ("pedestrian", "service"): continue
        rng = random.Random(ri * 7 + 1)
        swalk = kind in ("center", "modern", "gov", "industry") or hw in ("primary", "secondary", "tertiary")
        for side in (1, -1):
            def ok(i, side=side):
                mx = (p[i][0] + p[i + 1][0]) / 2 + (nr[i][0] + nr[i + 1][0]) / 2 * side * (wdt / 2 + 1.6)
                my = (p[i][1] + p[i + 1][1]) / 2 + (nr[i][1] + nr[i + 1][1]) / 2 * side * (wdt / 2 + 1.6)
                return road_d(mx, my, ri) > 1.8 and not in_bld(mx, my, 0.3)
            o0, o1 = side * wdt / 2, side * (wdt / 2 + (3.2 if swalk else 1.6))
            a_, b_ = (o0, o1) if side > 0 else (o1, o0)
            if swalk:
                strip(m, p, nr, a_, b_, ZS, ZS, "fx_sidewalk", 2.0, ok)
                if side > 0: strip(m, p, nr, o0, o0, zr, ZS, "fx_curb", 1.0, ok)
                else: strip(m, p, nr, o0, o0, ZS, zr, "fx_curb", 1.0, ok)
            else:
                strip(m, p, nr, a_, b_, 0.04, 0.04, "fx_dirt", 3.0, ok)       # обочина
            if hw in ("primary", "secondary", "tertiary", "residential", "unclassified") and (side > 0 or hw in ("primary", "secondary")):
                acc = 0.0; nxt = rng.uniform(5, 20); pm = chunk(p[0][0], p[0][1], "props")
                for i in range(len(p) - 1):
                    L = math.hypot(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1])
                    if acc + L >= nxt and ok(i):
                        x = p[i][0] + nr[i][0] * side * (wdt / 2 + 0.6); y = p[i][1] + nr[i][1] * side * (wdt / 2 + 0.6)
                        if not in_bld(x, y, 0.5):
                            zb = ZS if swalk else 0.04; hp = 8.0 if hw in ("primary", "secondary") else 6.5
                            ax, ay = -nr[i][0] * side, -nr[i][1] * side; an = math.atan2(ay, ax)
                            if kind in ("village", "mining") and hw not in ("primary", "secondary"):     # деревянный столб
                                pm.box((x, y), 0.22, 0.22, zb, zb + 7.5, 0, "hd_bark", 1.0)
                                pm.box((x + ax * 0.5, y + ay * 0.5), 1.0, 0.08, zb + 6.6, zb + 6.7, an, "fx_pole", 1.0)
                                pm.box((x + ax * 0.9, y + ay * 0.9), 0.4, 0.25, zb + 6.35, zb + 6.6, an, "fx_lampglass", 1.0, bottom=True)
                            else:
                                pm.box((x, y), 0.18, 0.18, zb, zb + hp, 0, "fx_pole", 1.0)
                                pm.box((x + ax * 0.8, y + ay * 0.8), 1.7, 0.1, zb + hp - 0.15, zb + hp, an, "fx_pole", 1.0)
                                pm.box((x + ax * 1.6, y + ay * 1.6), 0.6, 0.3, zb + hp - 0.35, zb + hp - 0.12, an, "fx_lampglass", 1.0, bottom=True)
                            stat["фонари"] += 1
                        nxt += 32 if hw in ("primary", "secondary") else 40
                    acc += L
            if hw in ("primary", "secondary", "tertiary") and side > 0 and len(p) > 30 and rng.random() < 0.6:
                i = len(p) // 2
                if ok(i):
                    x = p[i][0] + nr[i][0] * (wdt / 2 + 2.4); y = p[i][1] + nr[i][1] * (wdt / 2 + 2.4)
                    if not in_bld(x, y, 2.0):
                        pm = chunk(x, y, "props"); ang = math.atan2(nr[i][1], nr[i][0]) + math.pi / 2; zb = ZS if swalk else 0.04
                        pm.box((x, y), 4.0, 1.5, zb + 2.4, zb + 2.55, ang, "fx_pole", 1.0, bottom=True)
                        pm.box((x + nr[i][0] * 0.7, y + nr[i][1] * 0.7), 4.0, 0.08, zb, zb + 2.4, ang, "fx_busstop", 4.0)
                        pm.box((x, y), 3.0, 0.4, zb + 0.4, zb + 0.5, ang, "hz_furn_dark", 1.0)
                        stat["остановки"] += 1
        if hw in ("primary", "secondary", "tertiary"):
            strip(m, p, nr, -0.08, 0.08, zr + 0.01, zr + 0.01, "fx_marking", 1.0, keep=(lambda i: (i % 3) != 2) if hw == "tertiary" else None)
            if hw != "tertiary":
                for s_ in (1, -1):
                    o = s_ * (wdt / 2 - 0.5); strip(m, p, nr, min(o, o + s_ * 0.12), max(o, o + s_ * 0.12), zr + 0.01, zr + 0.01, "fx_marking", 1.0)
        stat["улицы"] += 1
    # заборы частных домов
    for p, sty, A in PRIV:
        rng = random.Random(int(p[0][0] * 31 + p[0][1] * 17))
        Ab, ang, (bx0, bx1, by0, by1), Wf = obb(p)
        e = rng.uniform(3.5, 7.0) * (1.6 if sty == "mansion" else 1.0); bx0 -= e; bx1 += e; by0 -= e * 0.8; by1 += e * 1.4
        corners = [Wf(bx0, by0), Wf(bx1, by0), Wf(bx1, by1), Wf(bx0, by1)]
        if sty == "mansion": fkey, fh = rng.choice(["pk_BrickWall1", "fx_fence_prof_2", "fx_fence_prof_1"]), 2.6
        else:
            fkey = rng.choice(["fx_fence_wood", "fx_fence_wood", "fx_fence_prof_0", "fx_fence_prof_1", "fx_fence_prof_2"]); fh = 1.5 if fkey == "fx_fence_wood" else 1.9
        gate = rng.randrange(4); pm = chunk(p[0][0], p[0][1], "props")
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]; L = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(L / 2.5))
            for j in range(n):
                pa = (a[0] + (b[0] - a[0]) * j / n, a[1] + (b[1] - a[1]) * j / n); pb = (a[0] + (b[0] - a[0]) * (j + 1) / n, a[1] + (b[1] - a[1]) * (j + 1) / n)
                mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
                if road_d(mx, my) < 1.0 or in_bld(mx, my, 0.6) or (k == gate and j == n // 2) or not inside((mx, my), 1) or wdist(mx, my) < 3: continue
                lu = L / n / (2.0 if fkey.startswith("fx_") else 3.0)
                pm.quad(pa, pb, 0, fh, 0, lu, 0, 1 if fkey.startswith("fx_") else fh / 3, fkey); pm.quad(pb, pa, 0, fh, 0, lu, 0, 1 if fkey.startswith("fx_") else fh / 3, fkey)
        stat["заборы"] += 1
        if sty != "mansion" and A < 140 and rng.random() < 0.6:
            pm.box(Wf((bx0 + bx1) / 2 - 3, by1 - 6), 6.0, 4.0, 0.0, 0.06, ang, "fx_dirt", 4.0)
    PRIV.clear()
    for a, b, L in YARDS:
        dx, dy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        A1 = (a[0] + dy * 0.3, a[1] - dx * 0.3); B1 = (b[0] + dy * 0.3, b[1] - dx * 0.3); A2 = (a[0] + dy * 9, a[1] - dx * 9); B2 = (b[0] + dy * 9, b[1] - dx * 9)
        if all(inside(q) for q in (A2, B2)):
            pm = chunk(a[0], a[1], "props")
            pm.face([(*A1, 0.07), (*A2, 0.07), (*B2, 0.07), (*B1, 0.07)], [(0, 0), (0, 1.5), (L / 6, 1.5), (L / 6, 0)], "fx_asphalt_yard")
            for k in range(max(1, int(L / 22))):
                t = (k + 0.5) / max(1, int(L / 22)) * L; c = (a[0] + dx * t + dy * 2.6 + dx * 2.2, a[1] + dy * t - dx * 2.6 + dy * 2.2)
                pm.box(c, 1.6, 0.45, 0.4, 0.48, math.atan2(dy, dx), "hz_furn_dark", 1.0)
    YARDS.clear()
    # деревья в городе
    rr = random.Random(len(game) * 101); tries = int(w * h / (720 * 720) * 2600)
    for k in range(tries):
        x, y = rr.uniform(x0 + 5, x1 - 5), rr.uniform(y0 + 5, y1 - 5)
        d = road_d(x, y)
        if d < 4.5 or (d > 9 and rr.random() < 0.55) or wdist(x, y) < 6 or in_bld(x, y): continue
        if any(math.hypot(x - q[0], y - q[1]) < 120 and pin(x, y, q[2]) for q in VR): continue
        tree(chunk(x, y, "trees"), x, y, 0.0, rr); stat["деревья"] += 1
    # площадка города: трава ровно на BASE (поверх рельефа, чуть выше)
    st = 25.0
    for gx in np.arange(x0, x1 - 0.1, st):
        for gy in np.arange(y0, y1 - 0.1, st):
            ex, ey = min(gx + st, x1), min(gy + st, y1)
            if wdist((gx + ex) / 2, (gy + ey) / 2) < 2: continue
            chunk(gx + 1, gy + 1, "ground_" + game).face([(gx, gy, 0), (ex, gy, 0), (ex, ey, 0), (gx, ey, 0)],
                [(gx / 14, gy / 14), (ex / 14, gy / 14), (ex / 14, ey / 14), (gx / 14, ey / 14)], "fx_grass")
    print(game, "← OSM", real, "| зданий:", stat["здания"] - nb0)

# ================= МЕЖДУ ГОРОДАМИ =================
ring_pts = []
for k in range(64):
    a = k / 64 * 2 * math.pi; rr_ = 2780 / max(abs(math.cos(a)), abs(math.sin(a))) * 0.97
    ring_pts.append((math.cos(a) * min(rr_, 2780), math.sin(a) * min(rr_, 2780)))
ring_pts.append(ring_pts[0])
HWAYS = [catmull(ring_pts, n=6)]
for g, (x0, x1, y0, y1) in RECTS.items():
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; q = min(HWAYS[0], key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
    HWAYS.append([(max(x0, min(x1, q[0])), max(y0, min(y1, q[1]))), q])
links = [("Арзамас", "Батырево"), ("Арзамас", "Рублёвка"), ("Арзамас", "Корякино"), ("Корякино", "Южный"), ("Корякино", "Бусаево"),
         ("Гарель", "Южный"), ("Гарель", "Арзамас"), ("Рублёвка", "Лыткарино"), ("Лыткарино", "Береговой"), ("Нижегородск", "Арзамас"), ("Бусаево", "Береговой")]
for a, b in links:
    ra, rb = RECTS[a], RECTS[b]; ca = ((ra[0] + ra[1]) / 2, (ra[2] + ra[3]) / 2); cb = ((rb[0] + rb[1]) / 2, (rb[2] + rb[3]) / 2)
    pa = (max(ra[0], min(ra[1], cb[0])), max(ra[2], min(ra[3], cb[1]))); pb = (max(rb[0], min(rb[1], ca[0])), max(rb[2], min(rb[3], ca[1])))
    L = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
    if L < 20: continue
    nx, ny = -(pb[1] - pa[1]) / L, (pb[0] - pa[0]) / L; ph = random.random() * 6
    HWAYS.append(catmull([(pa[0] + (pb[0] - pa[0]) * t + nx * 90 * math.sin(math.pi * t) * math.sin(ph), pa[1] + (pb[1] - pa[1]) * t + ny * 90 * math.sin(math.pi * t) * math.sin(ph)) for t in np.linspace(0, 1, 6)], n=8))
for hp in HWAYS:
    p = dense(hp, 6.0); p = [q for q in p if not town_of(q[0], q[1], -2) and not any(abs(q[0] - c[0]) < a_ + 8 and abs(q[1] - c[1]) < b_ + 8 for c, a_, b_ in FLATS)]
    if len(p) < 2: continue
    nr = norms(p); W_ = 12.0
    # режем на куски по секторам, чтобы объекты были небольшие
    for s0 in range(0, len(p) - 1, 40):
        pp = p[s0:s0 + 41]; nn = nr[s0:s0 + 41]; m = chunk(pp[0][0], pp[0][1], "hw")
        strip(m, pp, nn, -W_ / 2, W_ / 2, 0.15, 0.15, "fx_asphalt", 6.0, zf=road_z)
        strip(m, pp, nn, -W_ / 2 - 2.0, -W_ / 2, 0.05, 0.15, "fx_dirt", 3.0, zf=road_z)
        strip(m, pp, nn, W_ / 2, W_ / 2 + 2.0, 0.15, 0.05, "fx_dirt", 3.0, zf=road_z)
        strip(m, pp, nn, -0.08, 0.08, 0.16, 0.16, "fx_marking", 1.0, keep=lambda i: i % 2 == 0, zf=road_z)
        for s_ in (1, -1):
            o = s_ * (W_ / 2 - 0.4); strip(m, pp, nn, min(o, o + s_ * 0.15), max(o, o + s_ * 0.15), 0.16, 0.16, "fx_marking", 1.0, zf=road_z)
        # ограждение на мостах
        for i in range(len(pp) - 1):
            if wdist(*pp[i]) < 40:
                for s_ in (1, -1):
                    a = (pp[i][0] + nn[i][0] * s_ * (W_ / 2 + 0.4), pp[i][1] + nn[i][1] * s_ * (W_ / 2 + 0.4)); b = (pp[i + 1][0] + nn[i + 1][0] * s_ * (W_ / 2 + 0.4), pp[i + 1][1] + nn[i + 1][1] * s_ * (W_ / 2 + 0.4))
                    za = road_z(*a); m.face([(a[0], a[1], za), (b[0], b[1], za), (b[0], b[1], za + 1.1), (a[0], a[1], za + 1.1)], [(0, 0), (2, 0), (2, 1), (0, 1)], "fx_pole")
                    m.face([(b[0], b[1], za), (a[0], a[1], za), (a[0], a[1], za + 1.1), (b[0], b[1], za + 1.1)], [(0, 0), (2, 0), (2, 1), (0, 1)], "fx_pole")
                c = ((pp[i][0] + pp[i + 1][0]) / 2, (pp[i][1] + pp[i + 1][1]) / 2); zc = road_z(*c)
                m.box(c, 6.2, W_ + 1.2, zc - 1.0, zc + 0.12, math.atan2(nn[i][1], nn[i][0]) + math.pi / 2, "fx_concrete", 3.0, bottom=True)
                if i % 5 == 0 and gz(*c) < WATER: m.box(c, 2.0, W_ * 0.7, gz(*c), zc - 1.0, math.atan2(nn[i][1], nn[i][0]) + math.pi / 2, "fx_concrete", 3.0)
    for k in range(0, len(p) - 1, 80):
        add_road_idx(p[k:k + 81], 16.0)
    stat["трассы"] += 1

# ================= ОСОБЫЕ МЕСТА (вне городов) =================
def bboxl(key):
    me = bpy.data.meshes[key]; xs = [v.co.x for v in me.vertices]; ys = [v.co.y for v in me.vertices]
    return min(xs), max(xs), min(ys), max(ys)


def fixed(key, x, y, ang, label="", layer="buildings", z=None):
    zz = gz(x, y) + 0.05 if z is None else z
    o = inst(key, x, y, zz, ang, layer, "special", {"venue": label} if label else None)
    bb = bboxl(key); add_bld(rect_poly(x, y, ang, bb, 1.0))
    if label:
        door = o.matrix_world @ Vector(ANCH.get(key, {}).get("door", (0, -2, 0.3)))
        ENTR.append({"type": "special", "venue": label, "x": round(door.x, 2), "y": round(door.y, 2), "z": round(door.z + 1.0, 2), "object": o.name})
    stat["спецобъекты"] += 1
    return o


def V(vt):
    key, fn, cat = VENUES[vt]; asset(key, fn, meta={"venue": vt, "category": cat}); return key


def bank_point(near, extra=30.0):
    """точка на берегу реки рядом с near; n — от воды к суше, t — вдоль берега"""
    best = None
    for pts, w in RIV:
        for a, b in zip(pts, pts[1:]):
            d = seg_d(near[0], near[1], a, b)
            if best is None or d < best[0]: best = (d, a, b, w)
    d, a, b, w = best; L = math.hypot(b[0] - a[0], b[1] - a[1]); tx, ty = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    nx, ny = -ty, tx
    if (near[0] - a[0]) * nx + (near[1] - a[1]) * ny < 0: nx, ny = -nx, -ny
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    return mx + nx * (w / 2 + extra), my + ny * (w / 2 + extra), nx, ny, tx, ty


asset("hzS_pier", v_pier, {"berth": (5.5, -70, 2.3)}); asset("hzS_crane", v_crane); asset("hzF_i_containers", v_container_stack)
# порт: 2 причала с кранами на реке у Арзамаса
for off in (-70, 70):
    bx, by, nx, ny, tx, ty = bank_point(SPOTS["port"])
    ang = math.atan2(ny, nx) - math.pi / 2
    fixed("hzS_pier", bx + tx * off, by + ty * off, ang, "Причал", "props", z=BASE - 1.5)
    fixed("hzS_crane", bx + tx * off + nx * 16, by + ty * off + ny * 16, ang, "", "props", z=BASE + 0.05)
    fixed("hzF_i_containers", bx + tx * off + nx * 40, by + ty * off + ny * 40, ang, "", "props", z=BASE + 0.05)
asset("hzS_cyard", v_container_yard)
bx, by, nx, ny, tx, ty = bank_point(SPOTS["port"])
fixed("hzS_cyard", bx + nx * 90, by + ny * 90, math.atan2(ny, nx) - math.pi / 2, "Контейнерная площадка", "props", z=BASE + 0.05)
asset("hzS_wedding", v_wedding); fixed("hzS_wedding", *SPOTS["wedding"], 0.3, "Свадебная зона", "props", z=BASE + 0.05)
asset("hzS_track", v_track); fixed("hzS_track", *SPOTS["autodrome"], 0.15, "Автодром", "props", z=BASE + 0.05)
asset("hzS_celltower", v_celltower)
for i, (x, y) in enumerate(SPOTS["towers"]): fixed("hzS_celltower", x, y, 0.0, f"Вышка связи {i + 1}", "props")
asset("hzS_wall100", lambda k: v_wall(k, 100)); asset("hzS_watch", v_tower_watch)


def compound(cx, cy, W, Dd, ang, gate_side=0):
    c, s = math.cos(ang), math.sin(ang)
    P = lambda lx, ly: (cx + c * lx - s * ly, cy + s * lx + c * ly)
    for side in range(4):
        L_ = W if side % 2 == 0 else Dd
        for k in range(int(L_ // 100)):
            t = -L_ / 2 + 50 + k * 100
            if side == gate_side and abs(t) < 60: continue
            lx, ly = [(t, -Dd / 2), (W / 2, t), (t, Dd / 2), (-W / 2, t)][side]
            x, y = P(lx, ly); fixed("hzS_wall100", x, y, ang + (math.pi / 2 if side % 2 else 0), "", "props", z=BASE + 0.05)
    for lx, ly in ((-W / 2, -Dd / 2), (W / 2, -Dd / 2), (W / 2, Dd / 2), (-W / 2, Dd / 2)):
        x, y = P(lx, ly); fixed("hzS_watch", x, y, ang, "", "props", z=BASE + 0.05)


ax_, ay_ = SPOTS["army"]; compound(ax_, ay_, 400, 300, 0.0)
fixed(V("Армия"), ax_, ay_ - 100, 0.0, "Армия", z=BASE + 0.05)
asset("hzS_barracks", lambda k: b_admin(k, W=40, D=12, floors=2, wall='pk_WhiteBricks', sg='sg_generic', sg_w=0.01))
for i in range(3): fixed("hzS_barracks", ax_ - 110 + i * 110, ay_ + 60, 0.0, "Казарма", z=BASE + 0.05)
asset("hzS_hangar", v_hangar); fixed("hzS_hangar", ax_ + 130, ay_ - 40, 0.0, "Ангар", z=BASE + 0.05)
(fx_, fy_), fr_, _k = ISLANDS[0]
compound(fx_, fy_, 200, 200, 0.0)
fixed(V("ФСИН"), fx_, fy_ - 40, 0.0, "ФСИН", z=BASE + 0.05)
for i in range(2): fixed("hzS_barracks", fx_ - 45 + i * 90, fy_ + 50, 0.0, "Барак", z=BASE + 0.05)
asset("hzS_abfactory", v_factory); fixed("hzS_abfactory", *SPOTS["factory"], 0.4, "Заброшенный завод", z=BASE + 0.05)
# площадки под спецобъектами: асфальт/бетон
for nm, (x, y), w_, h_ in (("army", SPOTS["army"], 400, 300), ("autodrome", SPOTS["autodrome"], 260, 160), ("factory", SPOTS["factory"], 140, 120),
                           ("fsin", ISLANDS[0][0], 200, 200), ("port", (bx + nx * 70, by + ny * 70), 150, 120)):
    m = chunk(x, y, "terrain")
    m.face([(x - w_ / 2, y - h_ / 2, BASE + 0.02), (x + w_ / 2, y - h_ / 2, BASE + 0.02), (x + w_ / 2, y + h_ / 2, BASE + 0.02), (x - w_ / 2, y + h_ / 2, BASE + 0.02)],
           [(0, 0), (w_ / 8, 0), (w_ / 8, h_ / 8), (0, h_ / 8)], "fx_asphalt_yard" if nm != "fsin" else "fx_concrete")

# рельеф 12x12 секторов, 20 м
for i in range(12):
    for j in range(12):
        X0, Y0 = -HALF + i * 500, -HALF + j * 500; st = 20.0; n = 25; m = chunk(X0 + 1, Y0 + 1, "terrain")
        Z = [[gz(X0 + a * st, Y0 + b * st) - 0.06 for a in range(n + 1)] for b in range(n + 1)]
        for b in range(n):
            for a in range(n):
                xs, ys = X0 + a * st, Y0 + b * st
                if town_of(xs + st / 2, ys + st / 2, -st): continue          # под городом — своя площадка
                zc = (Z[b][a] + Z[b][a + 1] + Z[b + 1][a + 1] + Z[b + 1][a]) / 4
                key = "fx_dirt" if zc < WATER + 0.8 else "fx_grass"
                m.face([(xs, ys, Z[b][a]), (xs + st, ys, Z[b][a + 1]), (xs + st, ys + st, Z[b + 1][a + 1]), (xs, ys + st, Z[b + 1][a])],
                       [(xs / 14, ys / 14), ((xs + st) / 14, ys / 14), ((xs + st) / 14, (ys + st) / 14), (xs / 14, (ys + st) / 14)], key)
# вода
for pts, wv in RIV:
    p = dense(pts, 12.0); nr = norms(p)
    for s0 in range(0, len(p) - 1, 30):
        strip(chunk(p[s0][0], p[s0][1], "water"), p[s0:s0 + 31], nr[s0:s0 + 31], -(wv + 30) / 2, (wv + 30) / 2, WATER, WATER, "hd_water", 14.0)
for (cx, cy), r in LAKES:
    chunk(cx, cy, "water").poly([(cx + (r + 12) * math.cos(t), cy + (r + 12) * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 48, endpoint=False)], WATER, "hd_water", 14.0)
# лес между городами
rr = random.Random(5); nf = 0; tries = 0
while nf < 7000 and tries < 120000:
    tries += 1
    x, y = rr.uniform(-2950, 2950), rr.uniform(-2950, 2950)
    if math.sin(x / 360) + math.cos(y / 310) + math.sin((x + y) / 520) < 0.3: continue
    if town_dist(x, y) < 40 or wdist(x, y) < 20 or road_d(x, y) < 10: continue
    tree(chunk(x, y, "forest"), x, y, gz(x, y) - 0.1, rr, spruce=rr.random() < 0.55); nf += 1
stat["лес"] = nf

# ================= В ОБЪЕКТЫ =================
faces = 0
TOWN_LAYERS = {"bld", "road", "props", "trees"}
for (layer, i, j), m in CH.items():
    if not m.f: continue
    lay = "terrain" if layer.startswith("ground_") else layer
    o, n = m.build(lcoll(lay)); faces += n
    if layer in TOWN_LAYERS or layer.startswith("ground_"): o.location.z = BASE
    o["sector"] = f"S_{i:02d}_{j:02d}"; o["layer"] = lay
import time; print("время:", round(time.time() - T0, 1), "с")
json.dump(ENTR, open("/srv/blender/projects/horz/osm/entrances_v3.json", "w"), ensure_ascii=False, indent=0)
print(dict(stat))
print("граней:", faces, "| объектов:", len(sc.objects), "| входов:", len(ENTR))
