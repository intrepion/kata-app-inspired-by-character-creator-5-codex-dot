"""Actual GLB export rendered in Blender Cycles; no added SSS or material fixes."""
import bpy,pathlib,math
from mathutils import Vector
ROOT=pathlib.Path(__file__).resolve().parents[1]
for mode in ['baseline','neutral']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'artifacts'/('hair-cards-'+mode+'.glb')))
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
    scene.render.resolution_x=500;scene.render.resolution_y=625;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('Neutral studio');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.18,.18,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
    def sun(name,loc,energy):
        d=bpy.data.lights.new(name,'SUN');d.energy=energy;d.angle=.12;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.46))-o.location).to_track_quat('-Z','Y').to_euler();return o
    key=sun('Key',(-2.8,-4.2,4.8),2.5);fill=sun('Fill',(3,-3,2),.9)
    data=bpy.data.cameras.new('Review camera');cam=bpy.data.objects.new('Review camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.lens=68
    for label,angle,backlight in [('front',0,False),('three-quarter',.65,False),('back',math.pi,False)]:
        target=Vector((0,-.045,1.461));cam.location=target+Vector((math.sin(angle)*.90,-math.cos(angle)*.90,.04));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
        key.location=(2,3,2) if backlight else (-2.8,-4.2,4.8);key.rotation_euler=(target-key.location).to_track_quat('-Z','Y').to_euler();key.data.energy=3.5 if backlight else 2.5
        fill.data.energy=.65 if backlight else .9
        scene.render.filepath=str(ROOT/'artifacts'/('blender-hair-cards-'+mode+'-'+label+'.png'));bpy.ops.render.render(write_still=True)
