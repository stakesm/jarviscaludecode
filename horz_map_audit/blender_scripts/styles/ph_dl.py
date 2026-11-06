import urllib.request, json, os, concurrent.futures as cf
D="/srv/blender/assets/polyhaven_cc0"; os.makedirs(D, exist_ok=True)
IDS="""white_plaster_02 painted_plaster_wall yellow_plaster yellow_plaster_02 blue_plaster_weathered grey_plaster worn_plaster_wall red_plaster_weathered
plastered_wall_02 white_stucco red_brick_03 red_bricks_04 brick_wall_001 white_bricks whitewashed_brick yellow_bricks dark_brick_wall large_red_bricks
concrete_wall_008 precast_concrete_wall concrete_panels concrete_slab_wall concrete_wall_006 painted_concrete
weathered_plank_siding exterior_wall_cladding white_planks_clean wood_plank_wall raw_plank_wall blue_painted_planks distressed_painted_planks green_rough_planks
corrugated_iron_02 box_profile_metal_sheet grey_roof_tiles roof_tiles_14 clay_roof_tiles roof_slates_02 rusty_corrugated_iron grey_roof_01
asphalt_02 worn_asphalt clean_asphalt asphalt_track concrete_pavers square_concrete_pavers herringbone_pavement brick_pavement concrete_pavement
leafy_grass sparse_grass forrest_ground_01 grass_path_2 dirt park_dirt gravel_road painted_metal_shutter green_metal_rust blue_metal_plate rusty_metal_sheet wooden_gate""".split()
UA={"User-Agent":"horz-map-builder"}
def get(i):
    p=f"{D}/{i}.jpg"
    if os.path.exists(p): return i, "есть"
    try:
        F=json.loads(urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{i}",headers=UA),timeout=60).read())
        u=F["Diffuse"]["1k"]["jpg"]["url"]
        open(p,"wb").write(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=120).read()); return i,"ok"
    except Exception as e: return i, "ERR "+str(e)[:80]
with cf.ThreadPoolExecutor(8) as ex: R=list(ex.map(get, IDS))
print([r for r in R if r[1].startswith("ERR")], len([r for r in R if not r[1].startswith("ERR")]), "из", len(IDS))
