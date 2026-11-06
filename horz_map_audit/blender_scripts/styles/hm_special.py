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
