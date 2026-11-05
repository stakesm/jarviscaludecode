import csv, zipfile, collections, re
Z=zipfile.ZipFile("/srv/blender/mapkit/HORZ_MOBILE_mapkit.zip")
mods=set()
for p in ("br_map_00.bpc","br_map_01.bpc","br_map_02.bpc"):
    with Z.open("packs/"+p) as f: mods|={i.filename[:-4].lower() for i in zipfile.ZipFile(f).infolist() if i.filename.endswith('.mod')}
base={re.sub(r'_\d+$','',m) for m in mods}
rows=list(csv.reader(open("/srv/blender/mapkit/out/models_audit.csv",encoding='utf-8-sig'),delimiter=';'))[1:]
miss=[r for r in rows if r[4].startswith('НЕТ ФАЙЛА')]
near=[r[1] for r in miss if r[1].lower() in base or any(m.startswith(r[1].lower()+'_') for m in mods)]
print("отсутствующих:",len(miss),"похожих по имени (суффикс _N):",len(near), near[:10])
pref=collections.Counter(re.match(r'[A-Za-z]+_?',r[1]).group(0) if re.match(r'[A-Za-z]+_?',r[1]) else '?' for r in miss)
print("префиксы отсутствующих:", pref.most_common(12))
ide=collections.Counter(r[3] for r in miss); print("по IDE:", ide.most_common(12))
txd=collections.Counter(r[2] for r in miss); print("по TXD:", txd.most_common(10))
