import bpy,pathlib,math
from mathutils import Vector
ROOT=pathlib.Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'assets/source/foundation.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=False;scene.render.resolution_x=720;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world.color=(.3,.3,.3);scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
def area(name,loc,power,size):
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-3,-4,4),450,4);area('Fill',(3,-2,2),250,3);area('Rim',(1,2,3),450,2)
cam=bpy.data.cameras.new('ReviewCamera');o=bpy.data.objects.new('ReviewCamera',cam);scene.collection.objects.link(o);scene.camera=o;cam.type='ORTHO'
for name,loc,target,scale in [('front',(0,-4,1.1),(0,0,.88),1.95),('three-quarter',(2,-4,1.5),(0,0,.9),1.95),('face',(0,-3,1.46),(0,-.02,1.46),.42)]:
 o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();cam.ortho_scale=scale;scene.render.filepath=str(ROOT/'docs/screenshots'/('asset-'+name+'.png'));bpy.ops.render.render(write_still=True)
