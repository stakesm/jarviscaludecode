import os, zipfile, struct, collections, csv, json
K="/srv/blender/mapkit/kit/maps/data/"
Z=zipfile.ZipFile("/srv/blender/mapkit/HORZ_MOBILE_mapkit.zip")
cfg=open(K+"config.dat",encoding='utf-8',errors='replace').read().splitlines()
act_ide=[l.split(None,1)[1].strip().replace('\\','/') for l in cfg if l.startswith('IDE ')]
act_ipl=[l.split(None,1)[1].strip().replace('\\','/') for l in cfg if l.startswith('IPL ')]
files={}
for root,ds,fs in os.walk(K+"maps"):
    for fn in fs: files[os.path.relpath(os.path.join(root,fn),K+"maps").lower()]=os.path.join(root,fn)
def res(p):
    r=p.split('MAPS/',1)[-1].lower() if 'MAPS/' in p.upper() else None
    return files.get(r) if r else None
ide={}; ide_missing_files=[]
for p in act_ide:
    path=res(p)
    if path is None:
        if '/MAPS/' in p.upper(): ide_missing_files.append(p)
        continue
    sec=None
    for line in open(path,encoding='utf-8',errors='replace'):
        l=line.split('#')[0].strip()
        if l in('objs','tobj','anim','txdp','2dfx','path','hier','cars','peds','weap','end'): sec=l; continue
        q=[x.strip() for x in l.split(',')]
        if sec in('objs','tobj','anim') and len(q)>=3 and q[0].isdigit():
            ide[int(q[0])]=(q[1],q[2],os.path.basename(path))
mods={}
for p in ("br_map_00.bpc","br_map_01.bpc","br_map_02.bpc"):
    with Z.open("packs/"+p) as f:
        for i in zipfile.ZipFile(f).infolist():
            if i.filename.lower().endswith('.mod'): mods.setdefault(i.filename[:-4].lower(),p)
cols={}
with Z.open("packs/br_collision.bpc") as f:
    zz=zipfile.ZipFile(f)
    for info in zz.infolist():
        d=zz.read(info); k=d.find(b'CLST')
        while k>=0:
            cols.setdefault(d[k+8:k+32].split(b'\0')[0].decode('latin1').lower(), info.filename); k=d.find(b'CLST',k+8)
rows={}; per_ipl=collections.defaultdict(collections.Counter); ipl_missing_files=[]
for p in act_ipl:
    path=res(p)
    if path is None: ipl_missing_files.append(p); continue
    sec=None; ipl=os.path.basename(path)
    for line in open(path,encoding='utf-8',errors='replace'):
        l=line.split('#')[0].strip()
        if l in('inst','end','cull','pick','path','grge','enex','occl','mult','zone','cars','jump','auzo','tcyc'): sec=l; continue
        q=[x.strip() for x in l.split(',')]
        if sec!='inst' or len(q)<10 or not q[0].lstrip('-').isdigit(): continue
        mid=int(q[0]); ipl_name=q[1]
        r=rows.get(mid)
        if r is None:
            if mid in ide: name,txd,src=ide[mid]
            else: name,txd,src=ipl_name,'','(нет в IDE)'
            n=name.lower()
            if mid not in ide: st='НЕТ ОПИСАНИЯ В IDE'
            elif n in mods: st='ЕСТЬ .mod (формат не читается)'
            else: st='НЕТ ФАЙЛА МОДЕЛИ В АРХИВЕ'
            r=rows[mid]={'id':mid,'model':name,'txd':txd,'ide':src,'status':st,'pack':mods.get(n,''),'col':'да' if n in cols else 'нет','inst':0,'ipl':collections.Counter()}
        r['inst']+=1; r['ipl'][ipl]+=1; per_ipl[ipl][r['status']]+=1
out="/srv/blender/mapkit/out/models_audit.csv"
with open(out,'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f,delimiter=';')
    w.writerow(['id','модель','txd','IDE','статус','пак','коллизия','экземпляров','IPL'])
    for r in sorted(rows.values(),key=lambda r:(r['status'],-r['inst'])):
        w.writerow([r['id'],r['model'],r['txd'],r['ide'],r['status'],r['pack'],r['col'],r['inst'],', '.join(f"{k}:{v}" for k,v in r['ipl'].most_common())])
S=collections.Counter(); I=collections.Counter()
for r in rows.values(): S[r['status']]+=1; I[r['status']]+=r['inst']
print("УНИКАЛЬНЫЕ МОДЕЛИ:", dict(S)); print("ЭКЗЕМПЛЯРЫ:", dict(I))
print("коллизия у моделей без .mod:", collections.Counter(r['col'] for r in rows.values() if r['status'].startswith('НЕТ ФАЙЛА')))
print("IDE из config, нет в архиве:", ide_missing_files)
print("IPL из config, нет в архиве:", ipl_missing_files)
print("PER_IPL"); 
for k,v in sorted(per_ipl.items()): print(k, dict(v))
miss=sorted([r for r in rows.values() if r['status']!='ЕСТЬ .mod (формат не читается)'],key=lambda r:-r['inst'])
print("TOP_MISSING"); 
for r in miss[:25]: print(r['id'],r['model'],r['txd'],r['ide'],r['status'],r['col'],r['inst'])
used=set(r['model'].lower() for r in rows.values()); print(".mod в архиве всего:",len(mods)," из них используется IPL:",len(used&set(mods)))
