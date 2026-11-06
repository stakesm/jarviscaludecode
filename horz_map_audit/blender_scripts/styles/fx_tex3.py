
# ===== HORZ: фасады v2 — фото-основа CC0 (Poly Haven) + окна/швы/грязь, 1024px; имена fx_* те же =====
import bpy, numpy as np, os
PH = "/srv/blender/assets/polyhaven_cc0"; FXD = "/srv/blender/assets/horz_facades"
S = 1024; C = S // 2            # тайл = 2 пролёта x 2 этажа
_cache = {}


def load(name):
    if name in _cache: return _cache[name]
    im = bpy.data.images.load(f"{PH}/{name}.jpg"); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3].copy(); bpy.data.images.remove(im)
    _cache[name] = a; return a


def base(name, tile_m, phys_w, phys_h, tint=None, keep=0.0, rot=False, bright=1.0, con=1.0):
    """фото-материал, растянутый по физическому размеру: tile_m — сколько метров в одном повторе фото"""
    a = load(name)
    if rot: a = np.ascontiguousarray(np.rot90(a))
    h, w = a.shape[:2]
    ys = (np.arange(S) * (phys_h / S) / tile_m * h).astype(int) % h
    xs = (np.arange(S) * (phys_w / S) / tile_m * w).astype(int) % w
    o = a[ys][:, xs] * bright
    if tint is not None:
        lum = o.mean(-1, keepdims=True); lum = lum / max(1e-4, float(lum.mean())); lum = 1 + (lum - 1) * con
        o = o * keep + (1 - keep) * lum * np.array(tint)
    return o


def R(a, x0, y0, x1, y1, col, alpha=1.0):
    x0, y0, x1, y1 = [int(round(v)) for v in (x0, y0, x1, y1)]
    x0, y0 = max(0, x0), max(0, y0)
    if x1 <= x0 or y1 <= y0: return
    a[y0:y1, x0:x1] = a[y0:y1, x0:x1] * (1 - alpha) + np.array(col) * alpha


def shade(a, x0, y0, x1, y1, k):
    x0, y0, x1, y1 = [int(round(v)) for v in (x0, y0, x1, y1)]
    a[max(0, y0):y1, max(0, x0):x1] *= k


def grad_v(a, x0, y0, x1, y1, k0, k1):
    x0, y0, x1, y1 = [int(round(v)) for v in (x0, y0, x1, y1)]
    g = np.linspace(k0, k1, max(1, y1 - y0))[:, None, None]
    a[y0:y1, x0:x1] *= g


rng = np.random.default_rng(42)
SKY = np.array((0.62, 0.72, 0.84)); INT = np.array((0.10, 0.11, 0.12))


def glass(a, x0, y0, x1, y1, seed, tint=(0.30, 0.38, 0.46), interior=True):
    r = np.random.default_rng(seed); x0, y0, x1, y1 = [int(round(v)) for v in (x0, y0, x1, y1)]
    h, w = y1 - y0, x1 - x0
    if h <= 2 or w <= 2: return
    yy = np.linspace(0, 1, h)[:, None]; xx = np.linspace(0, 1, w)[None, :]
    refl = np.clip(0.55 - yy * 0.5 + 0.15 * np.sin((xx * 2.2 + yy * 1.3) * 3.1), 0, 1)[..., None]
    col = INT * (1 - refl) + (SKY * 0.85 + np.array(tint) * 0.15) * refl
    if interior and r.random() < 0.75:                         # шторы/тюль
        cc = np.array(r.choice([(0.82, 0.78, 0.66), (0.70, 0.56, 0.48), (0.78, 0.80, 0.78), (0.58, 0.62, 0.68), (0.86, 0.84, 0.78), (0.62, 0.52, 0.40)]))
        cw = r.uniform(0.15, 0.32)
        m = ((xx < cw) | (xx > 1 - cw * r.uniform(0.5, 1.1))) & (yy > 0.02)
        col = np.where(m[..., None], cc * (0.75 + 0.25 * np.sin(xx * 90)[..., None] ** 2) * (1 - refl * 0.4) + refl * SKY * 0.3, col)
    if interior and r.random() < 0.06: col = col * 0.4 + np.array((0.95, 0.80, 0.50)) * 0.6
    a[y0:y1, x0:x1] = col


def window(a, cx, top, w, h, seed, frame=(0.93, 0.93, 0.92), fr=12, kind="pvc", reveal=14, sill=True, wall_k=0.55):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, top, top + h
    # откос (тень внутрь проёма)
    shade(a, x0 - reveal, y0 - reveal, x1 + reveal, y0, wall_k + 0.1)
    shade(a, x0 - reveal, y0, x0, y1, wall_k + 0.2); shade(a, x1, y0, x1 + reveal, y1, wall_k + 0.25)
    R(a, x0, y0, x1, y1, frame)
    glass(a, x0 + fr, y0 + fr, x1 - fr, y1 - fr, seed)
    if kind == "pvc":                    # 2 створки
        xm = (x0 + x1) / 2; R(a, xm - fr / 2, y0, xm + fr / 2, y1, frame)
    elif kind == "soviet":               # старая деревянная: створка + форточка + фрамуга
        xm = x0 + (x1 - x0) * 0.42; R(a, xm - fr / 2, y0, xm + fr / 2, y1, frame)
        R(a, x0, y0 + h * 0.26, x1, y0 + h * 0.26 + fr * 0.8, frame)
    elif kind == "stalin":
        xm = (x0 + x1) / 2; R(a, xm - fr / 2, y0, xm + fr / 2, y1, frame); R(a, x0, y0 + h * 0.3, x1, y0 + h * 0.3 + fr, frame)
    # тень от рамы на стекле
    shade(a, x0 + fr, y0 + fr, x1 - fr, y0 + fr + 6, 0.6)
    if sill:
        R(a, x0 - 14, y1, x1 + 14, y1 + 12, (0.72, 0.73, 0.74)); shade(a, x0 - 14, y1 + 12, x1 + 14, y1 + 18, 0.6)
        # подтёки под окном
        r = np.random.default_rng(seed + 7)
        for k in range(int(r.integers(2, 6))):
            sx = r.uniform(x0, x1); sw = r.uniform(3, 10); L = r.uniform(30, 140)
            ys = int(y1 + 18); ye = int(min(S, y1 + 18 + L)); xs_ = int(sx); xe = int(sx + sw)
            if ye > ys: a[ys:ye, xs_:xe] *= np.linspace(0.82, 1.0, ye - ys)[:, None, None]


def grime(a, seed, k=0.12):
    r = np.random.default_rng(seed)
    g = r.random((S // 32 + 1, S // 32 + 1)); g = np.kron(g, np.ones((32, 32)))[:S, :S]
    a *= (1 - k / 2 + k * g)[..., None]


def save(name, a):
    im = bpy.data.images.get(name)
    if im is None: im = bpy.data.images.new(name, S, S)
    elif tuple(im.size) != (S, S): im.scale(S, S)
    im.pixels.foreach_set(np.concatenate([np.clip(a[::-1], 0, 1), np.ones((S, S, 1))], -1).astype(np.float32).ravel())
    im.filepath_raw = f"{FXD}/{name}.png"; im.file_format = 'PNG'; im.save(); im.filepath = im.filepath_raw; im.reload()
    return name


def cells():
    for bx in range(2):
        for fy in range(2): yield bx * C, fy * C, bx * 2 + fy


T = []
# ---- панельки 9-эт: бетонная панель (photo) + швы с герметиком + ПВХ/деревянные окна ----
PCOL = [(0.84, 0.83, 0.80), (0.86, 0.79, 0.66), (0.72, 0.78, 0.84), (0.86, 0.74, 0.70)]
for i, col in enumerate(PCOL):
    a = base("concrete_wall_008", 3.0, 6.4, 5.6, tint=col, keep=0.0, con=0.3)
    for x, y, k in cells():
        window(a, x + C / 2, y + 120, 240, 250, 100 + i * 9 + k, kind="pvc" if (k + i) % 3 else "soviet", frame=(0.95, 0.95, 0.94) if (k + i) % 3 else (0.86, 0.84, 0.80))
    for k in range(3):
        R(a, 0, k * C - 4, S, k * C + 4, tuple(np.array(col) * 0.55)); R(a, 0, k * C + 4, S, k * C + 7, tuple(np.array(col) * 0.75))
        R(a, k * C - 4, 0, k * C + 4, S, tuple(np.array(col) * 0.6))
    grime(a, 10 + i); grad_v(a, 0, 0, S, S, 1.0, 0.93)
    T.append(save(f"fx_panel_{i}", a))
# ---- хрущёвки: силикатный/красный кирпич (photo), панельная ----
for i, (src, tm) in enumerate([("whitewashed_brick", 1.6), ("red_brick_03", 1.4)]):
    a = base(src, tm, 6.2, 5.5, bright=1.05)
    for x, y, k in cells():
        window(a, x + C / 2, y + 110, 230, 270, 200 + i * 5 + k, kind="soviet" if k % 2 else "pvc", frame=(0.90, 0.90, 0.88) if k % 2 == 0 else (0.80, 0.78, 0.74))
        R(a, x + C / 2 - 135, y + 92, x + C / 2 + 135, y + 104, (0.66, 0.64, 0.60))           # перемычка
    grime(a, 20 + i, 0.08)
    T.append(save(f"fx_khrush_{i}", a))
a = base("precast_concrete_wall", 3.0, 6.2, 5.5, tint=(0.74, 0.74, 0.72), keep=0.3)
for x, y, k in cells(): window(a, x + C / 2, y + 110, 230, 270, 300 + k, kind="soviet", frame=(0.82, 0.80, 0.76))
for k in range(3): R(a, 0, k * C - 4, S, k * C + 4, (0.45, 0.45, 0.44))
R(a, C - 4, 0, C + 4, S, (0.48, 0.48, 0.47)); grime(a, 30)
T.append(save("fx_khrush_2", a))
# ---- сталинки: штукатурка (photo) + наличники, сандрики, тяги ----
SCOL = [(0.92, 0.80, 0.52), (0.88, 0.66, 0.60), (0.92, 0.90, 0.85), (0.70, 0.82, 0.70), (0.84, 0.64, 0.42)]
for i, col in enumerate(SCOL):
    a = base("white_plaster_02" if i % 2 else "plastered_wall_02", 2.5, 7.2, 6.8, tint=col, keep=0.15)
    tr = tuple(np.clip(np.array(col) * 1.1 + 0.08, 0, 1))
    for x, y, k in cells():
        cx = x + C / 2
        R(a, cx - 150, y + 44, cx + 150, y + 72, tr); shade(a, cx - 150, y + 72, cx + 150, y + 82, 0.65)      # сандрик
        R(a, cx - 132, y + 84, cx + 132, y + 440, tr); shade(a, cx - 132, y + 84, cx - 120, y + 440, 0.85)  # наличник
        window(a, cx, y + 104, 210, 320, 400 + i * 4 + k, frame=(0.96, 0.95, 0.92), kind="stalin", reveal=10)
        R(a, cx - 90, y + 452, cx + 90, y + 478, tr)                                                     # фартук
    for k in range(3):
        R(a, 0, k * C - 10, S, k * C + 10, tr); shade(a, 0, k * C + 10, S, k * C + 16, 0.7)               # межэтажная тяга
    grime(a, 40 + i, 0.08); grad_v(a, 0, 0, S, S, 1.0, 0.92)
    T.append(save(f"fx_stalin_{i}", a))
# ---- старый кирпич (купеческий) с арочными окнами ----
for i, src in enumerate(["large_red_bricks", "dark_brick_wall"]):
    a = base(src, 1.5, 6.8, 7.0)
    yy, xx = np.mgrid[0:S, 0:S]
    for x, y, k in cells():
        cx, top, w, h = x + C / 2, y + 110, 200, 320
        arch = ((xx - cx) ** 2 + (yy - (top + 100)) ** 2 < (w / 2 + 26) ** 2) & (yy < top + 100)
        a[arch] = a[arch] * 0.2 + np.array((0.86, 0.83, 0.77)) * 0.8
        R(a, cx - w / 2 - 26, top + 100, cx + w / 2 + 26, top + h + 10, (0.86, 0.83, 0.77), 0.8)
        g = a.copy(); glass(g, cx - w / 2 + 12, top + 30, cx + w / 2 - 12, top + h, 500 + k)
        inner = ((((xx - cx) ** 2 + (yy - (top + 100)) ** 2 < (w / 2 - 12) ** 2) & (yy < top + 100) & (yy > top + 12)) |
                 ((xx > cx - w / 2 + 12) & (xx < cx + w / 2 - 12) & (yy >= top + 100) & (yy < top + h)))
        a[inner] = g[inner]
        glass(a, cx - w / 2 + 12, top + 100, cx + w / 2 - 12, top + h, 520 + k)
        R(a, cx - 5, top + 20, cx + 5, top + h, (0.92, 0.92, 0.9)); R(a, cx - w / 2, top + 130, cx + w / 2, top + 140, (0.92, 0.92, 0.9))
        R(a, cx - w / 2 - 30, top + h + 10, cx + w / 2 + 30, top + h + 24, (0.80, 0.78, 0.74))
    grime(a, 50 + i, 0.1)
    T.append(save(f"fx_oldbrick_{i}", a))
# ---- современный ЖК: вентфасад + витражи ----
for i, col in enumerate([(0.24, 0.40, 0.66), (0.74, 0.44, 0.30), (0.56, 0.58, 0.60)]):
    a = base("concrete_panels", 2.4, 6.0, 6.0, tint=(0.88, 0.88, 0.86), keep=0.2)
    for x, y, k in cells():
        R(a, x + 16, y + 12, x + C - 16, y + 140, col); shade(a, x + 16, y + 140, x + C - 16, y + 148, 0.6)
        R(a, x + 16, y + 152, x + C - 16, y + 500, (0.32, 0.33, 0.34)); glass(a, x + 26, y + 160, x + C - 26, y + 492, 600 + i * 4 + k, tint=(0.25, 0.35, 0.42))
        R(a, x + C / 2 - 5, y + 160, x + C / 2 + 5, y + 492, (0.32, 0.33, 0.34)); R(a, x + 26, y + 330, x + C - 26, y + 338, (0.32, 0.33, 0.34))
    T.append(save(f"fx_modern_{i}", a))
# ---- офис / администрация: ленточное остекление ----
for i, col in enumerate([(0.80, 0.80, 0.78), (0.74, 0.68, 0.60)]):
    a = base("concrete_wall_006", 3.0, 6.0, 6.6, tint=col, keep=0.3)
    for y in (0, C):
        R(a, 0, y + 130, S, y + 450, (0.25, 0.27, 0.28)); glass(a, 0, y + 140, S, y + 440, 700 + i + y, tint=(0.22, 0.34, 0.38), interior=False)
        for xx_ in range(0, S, 128): R(a, xx_ - 5, y + 140, xx_ + 5, y + 440, (0.25, 0.27, 0.28))
        shade(a, 0, y + 450, S, y + 462, 0.7)
    grime(a, 70 + i, 0.06)
    T.append(save(f"fx_office_{i}", a))
# ---- деревянный дом: доска/вагонка (photo) + резные наличники + ставни ----
for i, (src, tint, nal) in enumerate([("weathered_plank_siding", None, (0.93, 0.92, 0.88)), ("green_rough_planks", None, (0.95, 0.95, 0.92)), ("blue_painted_planks", None, (0.95, 0.93, 0.86))]):
    a = base(src, 2.0, 6.0, 5.6)
    for x, y, k in cells():
        cx, top = x + C / 2, y + 140
        R(a, cx - 128, top - 30, cx + 128, top + 300, nal)
        for t in range(50): R(a, cx - 128 + t * 2.4, top - 30 - t, cx + 128 - t * 2.4, top - 29 - t, nal)
        for t in range(0, 240, 24): shade(a, cx - 120 + t, top - 60, cx - 112 + t, top - 34, 0.75)       # резьба
        R(a, cx - 150, top + 300, cx + 150, top + 326, nal); shade(a, cx - 150, top + 326, cx + 150, top + 334, 0.6)
        window(a, cx, top, 196, 270, 800 + i * 4 + k, frame=nal, kind="soviet", reveal=6, sill=False)
        sh = tuple(np.array(nal) * 0.8)
        R(a, cx - 182, top, cx - 132, top + 270, sh); R(a, cx + 132, top, cx + 182, top + 270, sh)
        for t in range(top, top + 270, 30): shade(a, cx - 182, t, cx - 132, t + 3, 0.7); shade(a, cx + 132, t, cx + 182, t + 3, 0.7)
    T.append(save(f"fx_wood_{i}", a))
# ---- сайдинг (новый частный дом) ----
for i, col in enumerate([(0.90, 0.84, 0.66), (0.76, 0.86, 0.74), (0.76, 0.84, 0.92)]):
    a = base("exterior_wall_cladding", 2.0, 6.4, 5.8, tint=col, keep=0.1, rot=True)
    for x, y, k in cells(): window(a, x + C / 2, y + 140, 220, 240, 900 + k, frame=(0.98, 0.98, 0.98), kind="pvc", reveal=8)
    T.append(save(f"fx_siding_{i}", a))
# ---- первый этаж: магазин (керамогранит + витрины + фриз) — полная высота текстуры = 1 этаж ----
for i, col in enumerate([(0.66, 0.14, 0.12), (0.14, 0.32, 0.58), (0.20, 0.46, 0.24)]):
    a = base("concrete_wall_006", 1.6, 6.8, 3.6, tint=(0.60, 0.60, 0.58), keep=0.3)
    R(a, 0, 0, S, 210, col); shade(a, 0, 200, S, 214, 0.4)
    for bx in range(2):
        x = bx * C
        R(a, x + 26, 240, x + C - 26, 940, (0.20, 0.21, 0.22)); glass(a, x + 40, 254, x + C - 40, 926, 950 + bx + i, tint=(0.30, 0.36, 0.38), interior=False)
        R(a, x + C / 2 - 6, 254, x + C / 2 + 6, 926, (0.20, 0.21, 0.22))
    R(a, 0, 940, S, S, (0.40, 0.40, 0.40))
    T.append(save(f"fx_shop_{i}", a))
# ---- подъездная дверь ----
a = base("concrete_wall_008", 1.8, 3.4, 3.0, tint=(0.72, 0.72, 0.70), keep=0.0, con=0.5)
R(a, 300, 180, 724, S, (0.18, 0.24, 0.22)); a2 = base("painted_metal_shutter", 1.0, 1.6, 2.4, tint=(0.24, 0.40, 0.34), keep=0.2)
a[210:, 330:694] = a2[210:, 330:694]; R(a, 370, 260, 650, 500, (0.20, 0.24, 0.26)); R(a, 600, 600, 630, 660, (0.75, 0.75, 0.70))
R(a, 240, 60, 784, 160, (0.18, 0.30, 0.56)); R(a, 270, 84, 754, 136, (0.94, 0.94, 0.94))
T.append(save("fx_door_entr", a))
# ---- крыши ----
for i, (src, tint) in enumerate([("box_profile_metal_sheet", (0.26, 0.46, 0.32)), ("corrugated_iron_02", None), ("box_profile_metal_sheet", (0.56, 0.58, 0.60)), ("box_profile_metal_sheet", (0.30, 0.34, 0.48))]):
    a = base(src, 2.0, 3.0, 3.0, tint=tint, keep=0.15); T.append(save(f"fx_roof_{i}", a))
# ---- балконы, стекло, золото, церковь, цоколь, профлист-стена, бетон ----
for i, tint in enumerate([(0.82, 0.82, 0.80), (0.46, 0.56, 0.72), (0.72, 0.46, 0.36)]):
    a = base("box_profile_metal_sheet", 1.5, 3.0, 3.0, tint=tint, keep=0.1, rot=True); grime(a, 120 + i); T.append(save(f"fx_balc_{i}", a))
a = base("white_plaster_02", 2, 3, 3, tint=(0.9, 0.9, 0.9), keep=0.3)
glass(a, 0, 0, S, S, 130, tint=(0.35, 0.45, 0.50))
for xx_ in range(0, S, 256): R(a, xx_, 0, xx_ + 14, S, (0.95, 0.95, 0.95))
R(a, 0, 500, S, 514, (0.95, 0.95, 0.95)); T.append(save("fx_balc_glass", a))
a = np.ones((S, S, 3)) * np.array((0.96, 0.74, 0.28)); a *= (0.8 + 0.4 * np.linspace(0, 1, S)[None, :, None] ** 0.5); T.append(save("fx_gold", a))
a = base("white_stucco", 2.5, 7.0, 9.0, tint=(0.95, 0.94, 0.90), keep=0.2)
yy, xx = np.mgrid[0:S, 0:S]
for x, y, k in cells():
    cx, top = x + C / 2, y + 110
    m = ((xx - cx) ** 2 + (yy - (top + 80)) ** 2 < 80 ** 2) & (yy < top + 80); a[m] = (0.20, 0.26, 0.32)
    R(a, cx - 80, top + 80, cx + 80, top + 340, (0.20, 0.26, 0.32)); glass(a, cx - 70, top + 80, cx + 70, top + 330, 140 + k, interior=False)
    R(a, cx - 104, top - 20, cx - 88, top + 352, (0.99, 0.99, 0.97)); R(a, cx + 88, top - 20, cx + 104, top + 352, (0.99, 0.99, 0.97))
T.append(save("fx_church", a))
a = base("concrete_wall_008", 2.0, 3.0, 3.0, tint=(0.52, 0.52, 0.50), keep=0.3)
for j in range(0, S, 128): R(a, 0, j, S, j + 5, (0.38, 0.38, 0.38))
T.append(save("fx_plinth", a))
a = base("box_profile_metal_sheet", 2.0, 3.0, 3.0, tint=(0.62, 0.64, 0.64), keep=0.2, rot=True); T.append(save("fx_prof_wall", a))
a = base("concrete_wall_008", 3.0, 3.0, 3.0, tint=(0.68, 0.68, 0.66), keep=0.4); T.append(save("fx_concrete", a))
# ---- земля/улица ----
a = base("asphalt_02", 4.0, 6.0, 6.0, tint=(0.24, 0.24, 0.25), keep=0.0, con=1.2); T.append(save("fx_asphalt", a))
a = base("asphalt_02", 4.0, 6.0, 6.0, tint=(0.31, 0.31, 0.31), keep=0.0, con=1.1); T.append(save("fx_asphalt_old", a))
a = base("worn_asphalt", 4.0, 6.0, 6.0, tint=(0.36, 0.35, 0.34), keep=0.0); grime(a, 3, 0.2); T.append(save("fx_asphalt_yard", a))
g1 = base("leafy_grass", 4.0, 14.0, 14.0); g2 = base("sparse_grass", 5.0, 14.0, 14.0)
_g = np.random.default_rng(5).random((5, 5)); _g = np.vstack([_g, _g[:1]]); _g = np.hstack([_g, _g[:, :1]])
_t = np.linspace(0, 5, S, endpoint=False); _i = _t.astype(int); _f = (_t - _i); _f = _f * _f * (3 - 2 * _f)
_r = _g[_i] * (1 - _f)[:, None] + _g[_i + 1] * _f[:, None]; mix = (_r[:, _i] * (1 - _f)[None, :] + _r[:, _i + 1] * _f[None, :])[..., None]
mix = 0.35 + 0.3 * mix
a = g1 * mix + g2 * (1 - mix); lum = a.mean(-1, keepdims=True) / a.mean(); a = (1 + (lum - 1) * 0.7) * np.array((0.30, 0.42, 0.18)) * 0.6 + a * 0.4; T.append(save("fx_grass", a))
a = base("dirt", 3.0, 3.0, 3.0); T.append(save("fx_dirt", a))
a = base("square_concrete_pavers", 2.0, 2.0, 2.0, bright=1.05); T.append(save("fx_sidewalk", a))
a = base("concrete_wall_008", 1.5, 1.0, 1.0, tint=(0.78, 0.78, 0.76), keep=0.3); T.append(save("fx_curb", a))
a = np.ones((S, S, 3)) * 0.9; a *= (0.8 + 0.2 * np.random.default_rng(1).random((S, S, 1))); T.append(save("fx_marking", a))
a = base("weathered_plank_siding", 2.0, 2.0, 2.0, rot=True)
a[:, :] *= 1.0; T.append(save("fx_fence_wood", a))
for i, tint in enumerate([(0.24, 0.42, 0.30), (0.46, 0.28, 0.22), (0.54, 0.56, 0.58)]):
    a = base("box_profile_metal_sheet", 1.5, 2.0, 2.0, tint=tint, keep=0.1, rot=True); T.append(save(f"fx_fence_prof_{i}", a))
a = base("green_metal_rust", 1.0, 1.0, 1.0, tint=(0.36, 0.38, 0.40), keep=0.2); T.append(save("fx_pole", a))
print("текстур v2:", len(T))
