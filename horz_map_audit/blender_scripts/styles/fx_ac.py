import bpy, numpy as np
S=256; FXD="/srv/blender/assets/horz_facades"
def save(name,a):
    im=bpy.data.images.get(name) or bpy.data.images.new(name,S,S)
    if tuple(im.size)!=(S,S): im.scale(S,S)
    im.pixels.foreach_set(np.concatenate([np.clip(a[::-1],0,1),np.ones((S,S,1))],-1).astype(np.float32).ravel())
    im.filepath_raw=f"{FXD}/{name}.png"; im.file_format='PNG'; im.save(); im.filepath=im.filepath_raw
r=np.random.default_rng(1)
a=np.ones((S,S,3))*0.86; a*=1+(r.random((S,S,1))-.5)*0.05
yy,xx=np.mgrid[0:S,0:S]; m=(xx-150)**2+(yy-128)**2<80**2; a[m]=0.32
for k in range(70,230,10): a[(np.abs(xx-150)<80)&(np.abs(yy-k)<2)&m]=0.75
a[20:236,20:24]=0.6; a[:, :]*=np.linspace(1.0,0.9,S)[:,None,None]; save("fx_ac",a)
a=np.ones((S,S,3))*0.2; m=(xx-128)**2+(yy-128)**2<120**2; a[m]=0.80; a[(xx-128)**2+(yy-128)**2<20**2]=0.35
a*=1+(r.random((S,S,1))-.5)*0.06; save("fx_dish",a)
print("ok")
