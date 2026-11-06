
# ===== свои фасадные текстуры HORZ (процедурные, 512x512 = 2 пролёта x 2 этажа) =====
import bpy, numpy as np, os
FXD = "/srv/blender/assets/horz_facades"; os.makedirs(FXD, exist_ok=True)
S = 512; C = 256


def cv(col, noise=0.06, seed=1):
    r = np.random.default_rng(seed)
    a = np.ones((S, S, 3)) * np.array(col, float)
    a *= 1 + (r.random((S, S, 1)) - 0.5) * noise
    return a


def R(a, x0, y0, x1, y1, col, mul=False):
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if mul: a[y0:y1, x0:x1] *= np.array(col)
    else: a[y0:y1, x0:x1] = np.array(col)


def glass(a, x0, y0, x1, y1, seed, tint=(0.22, 0.30, 0.38), curtains=True):
    r = np.random.default_rng(seed)
    h = int(y1 - y0)
    g = np.linspace(1.25, 0.75, h)[:, None, None] * np.array(tint)
    a[int(y0):int(y1), int(x0):int(x1)] = g
    # отражение неба — диагональная полоса
    yy, xx = np.mgrid[int(y0):int(y1), int(x0):int(x1)]
    m = ((xx - x0) + (yy - y0) * 0.6) % 90 < 22
    a[int(y0):int(y1), int(x0):int(x1)][m] *= 1.35
    if curtains and r.random() < 0.7:
        cc = r.choice([(0.78, 0.74, 0.62), (0.62, 0.48, 0.42), (0.74, 0.76, 0.74), (0.50, 0.56, 0.64), (0.82, 0.80, 0.74)])
        w = (x1 - x0) * r.uniform(0.18, 0.35)
        R(a, x0, y0, x0 + w, y1, cc); R(a, x1 - w * r.uniform(0.6, 1.0), y0, x1, y1, cc)
    if r.random() < 0.05: R(a, x0 + 3, y0 + 3, x1 - 3, y1 - 3, (0.80, 0.68, 0.42))   # горит свет / жёлтые шторы


def window(a, cx, top, w, h, seed, frame=(0.92, 0.92, 0.90), fr=7, sill=(0.75, 0.75, 0.74), kind="soviet"):
    x0, x1 = cx - w / 2, cx + w / 2; y0, y1 = top, top + h
    R(a, x0 - 4, y0 - 4, x1 + 4, y1 + 4, tuple(np.array(frame) * 0.55))       # откос
    R(a, x0, y0, x1, y1, frame)
    glass(a, x0 + fr, y0 + fr, x1 - fr, y1 - fr, seed)
    if kind in ("soviet", "stalin"):                         # импост: створка 1/3 + форточка
        xm = x0 + (x1 - x0) * 0.45
        R(a, xm - fr / 2, y0, xm + fr / 2, y1, frame)
        R(a, x0, y0 + h * 0.28, xm, y0 + h * 0.28 + fr, frame)
    elif kind == "plastic":
        xm = (x0 + x1) / 2; R(a, xm - fr / 2, y0, xm + fr / 2, y1, frame)
    R(a, x0 - 8, y1 + 2, x1 + 8, y1 + 11, sill)           # отлив


def brick(a, col, mortar, bw=24, bh=9, seed=2, var=0.12):
    r = np.random.default_rng(seed)
    a[:] = np.array(mortar)
    for j in range(0, S, bh):
        off = (bw // 2) if (j // bh) % 2 else 0
        for i in range(-off, S, bw):
            c = np.array(col) * (1 + (r.random() - 0.5) * var * 2)
            a[j + 1:j + bh - 1, max(0, i + 1):max(0, i + bw - 1)] = c
    a *= 1 + (r.random((S, S, 1)) - 0.5) * 0.08


def save(name, a):
    im = bpy.data.images.get(name) or bpy.data.images.new(name, S, S)
    if im.size[0] != S: im.scale(S, S)
    px = np.concatenate([np.clip(a[::-1], 0, 1), np.ones((S, S, 1))], -1).astype(np.float32)
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = f"{FXD}/{name}.png"; im.file_format = 'PNG'; im.save(); im.filepath = im.filepath_raw
    return name


def cells():
    for bx in range(2):
        for fy in range(2): yield bx * C, fy * C, bx * 2 + fy


T = []
# --- панельки (9-эт.) ---
for i, col in enumerate([(0.80, 0.80, 0.77), (0.82, 0.75, 0.62), (0.68, 0.74, 0.80), (0.83, 0.71, 0.66)]):
    a = cv(col, 0.07, 10 + i)
    for x, y, k in cells():
        window(a, x + 128, y + 62, 120, 132, 100 + i * 7 + k, kind="soviet" if (i + k) % 3 else "plastic", frame=(0.93, 0.93, 0.91) if (i + k) % 3 else (0.97, 0.97, 0.97))
    for k in range(3):
        R(a, 0, k * C - 2, S, k * C + 2, tuple(np.array(col) * 0.55)); R(a, k * C - 2, 0, k * C + 2, S, tuple(np.array(col) * 0.6))
    T.append(save(f"fx_panel_{i}", a))
# --- хрущёвка кирпичная (силикатная/красная) и панельная ---
for i, (col, mor) in enumerate([((0.84, 0.82, 0.76), (0.70, 0.69, 0.66)), ((0.62, 0.32, 0.24), (0.72, 0.68, 0.62))]):
    a = cv((0, 0, 0)); brick(a, col, mor, seed=20 + i)
    for x, y, k in cells(): window(a, x + 128, y + 58, 112, 140, 200 + i * 5 + k, frame=(0.88, 0.88, 0.86) if k % 2 else (0.55, 0.40, 0.28))
    T.append(save(f"fx_khrush_{i}", a))
a = cv((0.72, 0.72, 0.70), 0.10, 30)
for x, y, k in cells():
    window(a, x + 128, y + 58, 112, 140, 300 + k)
for k in range(3): R(a, 0, k * C - 3, S, k * C + 3, (0.45, 0.45, 0.44))
R(a, C - 2, 0, C + 2, S, (0.5, 0.5, 0.49))
T.append(save("fx_khrush_2", a))
# --- сталинка: штукатурка, высокие окна, сандрики, тяга между этажами ---
for i, col in enumerate([(0.88, 0.76, 0.46), (0.86, 0.64, 0.58), (0.90, 0.88, 0.82), (0.68, 0.80, 0.68), (0.80, 0.60, 0.38)]):
    a = cv(col, 0.05, 40 + i); tr = tuple(np.clip(np.array(col) * 1.12 + 0.08, 0, 1))
    for x, y, k in cells():
        R(a, x + 128 - 66, y + 20, x + 128 + 66, y + 34, tr); R(a, x + 128 - 60, y + 34, x + 128 + 60, y + 40, tuple(np.array(col) * 0.7))   # сандрик
        R(a, x + 128 - 62, y + 40, x + 128 + 62, y + 232, tr)                                  # наличник
        window(a, x + 128, y + 50, 98, 168, 400 + i * 4 + k, frame=(0.95, 0.94, 0.90), kind="stalin")
        R(a, x + 128 - 40, y + 236, x + 128 + 40, y + 250, tr)                                 # фартук
    for k in range(3): R(a, 0, k * C - 5, S, k * C + 5, tr); R(a, 0, k * C + 5, S, k * C + 8, tuple(np.array(col) * 0.75))
    T.append(save(f"fx_stalin_{i}", a))
# --- старый красный кирпич 19 в., арочные окна ---
for i, col in enumerate([(0.60, 0.28, 0.20), (0.48, 0.22, 0.17)]):
    a = cv((0, 0, 0)); brick(a, col, (0.62, 0.55, 0.48), bw=22, bh=8, seed=50 + i, var=0.18)
    for x, y, k in cells():
        cx, top, w, h = x + 128, y + 60, 96, 150
        yy, xx = np.mgrid[0:S, 0:S]
        arch = ((xx - cx) ** 2 + (yy - (top + 48)) ** 2 < (w / 2 + 12) ** 2) & (yy < top + 48)
        a[arch] = (0.85, 0.82, 0.76)
        R(a, cx - w / 2 - 12, top + 48, cx + w / 2 + 12, top + h + 6, (0.85, 0.82, 0.76))
        glass(a, cx - w / 2 + 6, top + 20, cx + w / 2 - 6, top + h, 500 + k)
        R(a, cx - 3, top + 20, cx + 3, top + h, (0.9, 0.9, 0.88)); R(a, cx - w / 2, top + 60, cx + w / 2, top + 66, (0.9, 0.9, 0.88))
        arch2 = ((xx - cx) ** 2 + (yy - (top + 48)) ** 2 < (w / 2 - 6) ** 2) & (yy < top + 48) & (yy > top + 6)
        g = a.copy(); glass(g, 0, 0, S, S, 9, curtains=False); a[arch2] = g[arch2]
    T.append(save(f"fx_oldbrick_{i}", a))
# --- современный ЖК: стекло до пола + цветной простенок ---
for i, col in enumerate([(0.20, 0.36, 0.62), (0.70, 0.40, 0.28), (0.55, 0.57, 0.58)]):
    a = cv((0.88, 0.88, 0.86), 0.04, 60 + i)
    for x, y, k in cells():
        R(a, x + 8, y + 6, x + C - 8, y + 70, col)
        R(a, x + 8, y + 76, x + C - 8, y + 250, (0.75, 0.76, 0.76)); glass(a, x + 12, y + 80, x + C - 12, y + 246, 600 + i * 4 + k, tint=(0.18, 0.28, 0.36))
        R(a, x + C // 2 - 2, y + 80, x + C // 2 + 2, y + 246, (0.75, 0.76, 0.76))
    T.append(save(f"fx_modern_{i}", a))
# --- офис/администрация: ленточное остекление ---
for i, col in enumerate([(0.78, 0.78, 0.76), (0.70, 0.66, 0.60)]):
    a = cv(col, 0.05, 70 + i)
    for y in (0, C):
        glass(a, 0, y + 70, S, y + 220, 700 + i + y, tint=(0.20, 0.32, 0.36), curtains=False)
        for xx in range(0, S, 64): R(a, xx - 3, y + 70, xx + 3, y + 220, (0.30, 0.32, 0.33))
    T.append(save(f"fx_office_{i}", a))
# --- деревянный дом (брус/вагонка) с резными наличниками ---
for i, (col, nal) in enumerate([((0.48, 0.33, 0.20), (0.92, 0.92, 0.88)), ((0.36, 0.52, 0.38), (0.95, 0.95, 0.92)), ((0.40, 0.52, 0.66), (0.95, 0.93, 0.85))]):
    a = cv(col, 0.05, 80 + i); r = np.random.default_rng(80 + i)
    for j in range(0, S, 16):
        a[j:j + 16] *= 0.9 + 0.2 * r.random(); a[j + 14:j + 16] *= 0.6
    for x, y, k in cells():
        cx, top = x + 128, y + 70
        R(a, cx - 64, top - 14, cx + 64, top + 150, nal)
        for t in range(26): R(a, cx - 64 + t * 2.4, top - 14 - t, cx + 64 - t * 2.4, top - 13 - t, nal)        # «кокошник»
        R(a, cx - 74, top + 150, cx + 74, top + 162, nal)
        window(a, cx, top, 98, 136, 800 + i * 4 + k, frame=nal, kind="soviet")
        R(a, cx - 90, top, cx - 66, top + 136, tuple(np.array(nal) * 0.85)); R(a, cx + 66, top, cx + 90, top + 136, tuple(np.array(nal) * 0.85))   # ставни
    T.append(save(f"fx_wood_{i}", a))
# --- сайдинг (частный дом новый) ---
for i, col in enumerate([(0.86, 0.80, 0.62), (0.72, 0.82, 0.70), (0.72, 0.80, 0.88)]):
    a = cv(col, 0.03, 90 + i)
    for j in range(0, S, 12): a[j + 10:j + 12] *= 0.82
    for x, y, k in cells(): window(a, x + 128, y + 70, 110, 120, 900 + k, frame=(0.98, 0.98, 0.98), kind="plastic")
    T.append(save(f"fx_siding_{i}", a))
# --- первый этаж: магазин (витрина + фриз), 2 пролёта x 1 этаж (полная высота текстуры = 1 этаж) ---
for i, col in enumerate([(0.62, 0.12, 0.12), (0.12, 0.30, 0.55), (0.18, 0.45, 0.22)]):
    a = cv((0.62, 0.62, 0.60), 0.05, 95 + i)
    R(a, 0, 0, S, 110, col); R(a, 0, 104, S, 112, (0.2, 0.2, 0.2))
    for bx in range(2):
        x = bx * C
        R(a, x + 14, 124, x + C - 14, 470, (0.25, 0.25, 0.26)); glass(a, x + 22, 132, x + C - 22, 462, 950 + bx, tint=(0.30, 0.36, 0.38), curtains=False)
        R(a, x + C // 2 - 3, 132, x + C // 2 + 3, 462, (0.25, 0.25, 0.26))
    R(a, 0, 470, S, S, (0.42, 0.42, 0.42))
    T.append(save(f"fx_shop_{i}", a))
# --- подъезд: дверь (1 пролёт x 1 этаж) ---
a = cv((0.66, 0.66, 0.64), 0.05, 99)
R(a, 150, 90, 362, 512, (0.20, 0.28, 0.24)); R(a, 166, 106, 346, 512, (0.30, 0.42, 0.36))
R(a, 186, 130, 326, 250, (0.25, 0.3, 0.32)); R(a, 300, 300, 318, 330, (0.8, 0.8, 0.7))
R(a, 120, 30, 392, 80, (0.20, 0.30, 0.55)); R(a, 140, 44, 372, 66, (0.92, 0.92, 0.92))
T.append(save("fx_door_entr", a))
# --- крыши: профлист/кровельное железо ---
for i, col in enumerate([(0.24, 0.42, 0.30), (0.50, 0.22, 0.18), (0.48, 0.52, 0.56), (0.30, 0.34, 0.45)]):
    a = cv(col, 0.06, 110 + i)
    for xx in range(0, S, 32): a[:, xx:xx + 6] *= 0.72; a[:, xx + 6:xx + 10] *= 1.15
    T.append(save(f"fx_roof_{i}", a))
# --- балконы: окрашенный металл/стекло, купол-золото, побелка церкви ---
for i, col in enumerate([(0.80, 0.80, 0.78), (0.45, 0.55, 0.70), (0.70, 0.45, 0.35)]):
    a = cv(col, 0.06, 120 + i)
    for xx in range(0, S, 24): a[:, xx:xx + 3] *= 0.75
    T.append(save(f"fx_balc_{i}", a))
a = cv((0.9, 0.9, 0.9)); glass(a, 0, 0, S, S, 130, tint=(0.35, 0.45, 0.50)); [R(a, xx, 0, xx + 8, S, (0.95, 0.95, 0.95)) for xx in range(0, S, 128)]
T.append(save("fx_balc_glass", a))
a = cv((0.95, 0.72, 0.25), 0.15, 131); T.append(save("fx_gold", a))
a = cv((0.93, 0.92, 0.88), 0.04, 132)
for x, y, k in cells():
    yy, xx = np.mgrid[0:S, 0:S]; cx, top = x + 128, y + 60
    m = ((xx - cx) ** 2 + (yy - (top + 40)) ** 2 < 40 ** 2) & (yy < top + 40); a[m] = (0.22, 0.28, 0.34)
    R(a, cx - 40, top + 40, cx + 40, top + 170, (0.22, 0.28, 0.34))
    R(a, cx - 52, top - 10, cx - 44, top + 176, (0.98, 0.98, 0.96)); R(a, cx + 44, top - 10, cx + 52, top + 176, (0.98, 0.98, 0.96))
T.append(save("fx_church", a))
a = cv((0.55, 0.56, 0.55), 0.10, 133)
for j in range(0, S, 64): R(a, 0, j, S, j + 3, (0.40, 0.40, 0.40))
T.append(save("fx_plinth", a))
a = cv((0.60, 0.62, 0.62), 0.05, 134)
for xx in range(0, S, 20): a[:, xx:xx + 4] *= 0.78
T.append(save("fx_prof_wall", a))
a = cv((0.66, 0.66, 0.64), 0.12, 135)
r_ = np.random.default_rng(5)
for k in range(60):
    x, y = r_.integers(0, S, 2); R(a, x, y, x + r_.integers(10, 60), y + r_.integers(10, 60), tuple(np.array((0.66, 0.66, 0.64)) * r_.uniform(0.9, 1.08)))
T.append(save("fx_concrete", a))
print("текстур:", len(T))
