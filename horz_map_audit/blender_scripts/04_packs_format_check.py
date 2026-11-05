import zipfile, collections, struct, zlib, math
Z=zipfile.ZipFile("/srv/blender/mapkit/HORZ_MOBILE_mapkit.zip")
def ent(b):
    c=collections.Counter(b); n=len(b); return -sum(v/n*math.log2(v/n) for v in c.values())
for p in ("br_map_00.bpc","br_map_01.bpc","br_map_02.bpc"):
    with Z.open("packs/"+p) as f:
        z=zipfile.ZipFile(f); L=z.infolist()
        ext=collections.Counter(i.filename.rsplit('.',1)[-1].lower() for i in L)
        heads=collections.Counter(); ents=[]; plain=[]
        for i in L:
            d=z.read(i); heads[d[:4].hex()]+=1
            if len(ents)<200 and len(d)>5000: ents.append(ent(d[64:4160]))
            if d[:4]!=bytes.fromhex('331092ab'): plain.append((i.filename,d[:8].hex()))
        # стандартные кодеки внутри?
        d=z.read(sorted(L,key=lambda i:-i.file_size)[5])
        sig={k:d.find(v) for k,v in {'zlib':b'\x78\x9c','zstd':b'\x28\xb5\x2f\xfd','lz4f':b'\x04\x22\x4d\x18','RW clump':b'\x10\x00\x00\x00'}.items()}
        try: zlib.decompress(d[16:]); zok=True
        except Exception: zok=False
        print(p, len(L), dict(ext), "заголовки:", heads.most_common(3), "незашифрованных:", plain[:5], "энтропия(бит/байт) ср:", round(sum(ents)/len(ents),3), "zlib с 16:", zok)
for p in ("br_tex_txd.astc.bpc","br_tex_interiors.astc.bpc","br_radarmap.astc.bpc"):
    with Z.open("packs/"+p) as f:
        z=zipfile.ZipFile(f); L=z.infolist(); fm=collections.Counter(); ktx=0
        for i in L:
            d=z.read(i)
            if d[4:16]==b"\xabKTX 11\xbb\r\n\x1a\n":
                ktx+=1; ifmt,w,h=struct.unpack('<I',d[4+28:4+32])[0],*struct.unpack('<2I',d[4+36:4+44]); fm[hex(ifmt)]+=1
        print(p, len(L), "KTX1:",ktx, "форматы:", fm.most_common(8), "пример:", L[0].filename)
with Z.open("packs/br_radarmap.astc.bpc") as f:
    z=zipfile.ZipFile(f); print("радар файлы:", [i.filename for i in z.infolist()][:12], len(z.infolist()))
