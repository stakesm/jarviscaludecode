import urllib.request, json, os, concurrent.futures as cf
UA={"User-Agent":"horz-map-builder"}
MD="/srv/blender/assets/polyhaven_models"; TD="/srv/blender/assets/polyhaven_cc0"
MODELS="""ArmChair_01 Sofa_01 sofa_02 sofa_03 CoffeeTable_01 modern_coffee_table_01 Television_01 television_02 WoodenChair_01 WoodenTable_01 dining_table dining_chair_02
drawer_cabinet modern_wooden_cabinet Shelf_01 wooden_bookshelf_worn ClassicNightstand_01 old_bed_frame vintage_day_bed GreenChair_01 SchoolChair_01 SchoolDesk_01
metal_office_desk CashRegister_01 steel_frame_shelves_01 steel_frame_shelves_02 wooden_display_shelves_01 worn_metal_rack mounted_fluorescent_lights modern_ceiling_lamp_01
Chandelier_01 potted_plant_01 potted_plant_02 BarberShopChair_01 bar_chair_round_01 metal_stool_01 security_camera_01 tool_cart industrial_storage_cart vintage_microwave
electric_stove ceiling_fan hanging_picture_frame_01 wall_clock standing_chalkboard_01 plastic_monobloc_chair_01 exterior_aircon_unit power_box_01 ornate_mirror_01""".split()
TEX="""laminate_floor laminate_floor_02 wood_floor herringbone_parquet floor_tiles_06 floor_tiles_08 large_grey_tiles interior_tiles white_tiles square_tiles_03 long_white_tiles
dirty_tiles marble_tiles terrazzo_tiles beige_wall_001 beige_wall_002 painted_plaster_wall plastered_wall_04 white_plaster_rough_01 decrepit_wallpaper wooden_panels
dark_paneled_wood ceiling_interior worn_tile_floor checkered_pavement_tiles dirty_carpet carpet rubber_tiles concrete_floor_painted smooth_concrete_floor""".split()
def gm(i):
    try:
        F=json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{i}",headers=UA),timeout=60).read())
        g=F["gltf"]["1k"]["gltf"]; d=f"{MD}/{i}"; os.makedirs(d,exist_ok=True)
        if not os.path.exists(f"{d}/{i}.gltf"):
            open(f"{d}/{i}.gltf","wb").write(urllib.request.urlopen(urllib.request.Request(g["url"],headers=UA),timeout=120).read())
            for rel,info in g.get("include",{}).items():
                p=f"{d}/{rel}"; os.makedirs(os.path.dirname(p),exist_ok=True)
                open(p,"wb").write(urllib.request.urlopen(urllib.request.Request(info["url"],headers=UA),timeout=120).read())
        return i,"ok"
    except Exception as e: return i,"ERR "+str(e)[:60]
def gt(i):
    p=f"{TD}/{i}.jpg"
    if os.path.exists(p): return i,"ok"
    try:
        F=json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{i}",headers=UA),timeout=60).read())
        open(p,"wb").write(urllib.request.urlopen(urllib.request.Request(F["Diffuse"]["1k"]["jpg"]["url"],headers=UA),timeout=120).read()); return i,"ok"
    except Exception as e: return i,"ERR "+str(e)[:60]
with cf.ThreadPoolExecutor(10) as ex:
    R=list(ex.map(gm,MODELS)); Q=list(ex.map(gt,TEX))
print("модели:",sum(r[1]=="ok" for r in R),"/",len(MODELS),[r[0] for r in R if r[1]!="ok"])
print("текстуры:",sum(r[1]=="ok" for r in Q),"/",len(TEX),[r[0] for r in Q if r[1]!="ok"])
