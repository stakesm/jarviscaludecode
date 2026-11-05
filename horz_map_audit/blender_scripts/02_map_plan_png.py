import bpy, numpy as np
sc=bpy.data.scenes['HORZ • Карта (макет)']
# 2D-план карты
N=2400; X0,X1,Y0,Y1=-3100,3100,-3000,3600
img=np.ones((N,N,3),np.float32)*np.array([0.95,0.95,0.92],np.float32)
order=sorted(sc.collection.objects,key=lambda o:o.name)
for o in order:
    import colorsys
    hh=colorsys.rgb_to_hsv(*o.active_material.diffuse_color[:3])[0]
    c=np.array(colorsys.hsv_to_rgb(hh,0.9,0.6),np.float32)
    me=o.data; v=np.empty(len(me.vertices)*3,np.float32); me.vertices.foreach_get('co',v); v=v.reshape(-1,8,3)
    mn=v.min(1); mx=v.max(1)
    sx=(mx[:,0]-mn[:,0]); sy=(mx[:,1]-mn[:,1])
    keep=(sx<400)&(sy<400)&~((np.abs(sx-2)<1e-3)&(np.abs(sy-2)<1e-3))
    for a,b in zip(mn[keep],mx[keep]):
        i0=int((a[0]-X0)/(X1-X0)*N); i1=max(i0+3,int((b[0]-X0)/(X1-X0)*N))
        j0=int((Y1-b[1])/(Y1-Y0)*N); j1=max(j0+3,int((Y1-a[1])/(Y1-Y0)*N))
        if 0<=i0<N and 0<=j0<N: img[j0:j1,i0:i1]=c
# сетка 500 м
for x in range(-3000,3101,500):
    i=int((x-X0)/(X1-X0)*N); img[:,max(0,i):i+1]=img[:,max(0,i):i+1]*0.85
for y in range(-3000,3601,500):
    j=int((Y1-y)/(Y1-Y0)*N); img[max(0,j):j+1]=img[max(0,j):j+1]*0.85
im=bpy.data.images.get("map_plan") or bpy.data.images.new("map_plan",N,N)
im.pixels.foreach_set(np.concatenate([img[::-1],np.ones((N,N,1),np.float32)],-1).ravel())
im.filepath_raw="/srv/blender/mapkit/out/map_plan.png"; im.file_format='PNG'; im.save()
