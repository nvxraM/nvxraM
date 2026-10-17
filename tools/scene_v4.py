#!/usr/bin/env python3
"""Aperture: an impossible satin-titanium artifact, physically lit in Cycles.

Original procedural geometry and materials. A closed trefoil ribbon carries a
deep teal enamel underside around one porcelain seed. The roughly 25 cm object
levitates above a circular obsidian pedestal. Real ray-traced cast shadows,
reflections and an 85 mm lens provide the photographic depth.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

S=.1
TAU=math.tau


def point(value):
    return Vector(value)*S


def material(name,color,metallic=0,roughness=.4,coat=0):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metallic
    bs.inputs['Roughness'].default_value=roughness
    bs.inputs['Coat Weight'].default_value=coat
    bs.inputs['Coat Roughness'].default_value=.14
    return mat


def microfinish(mat,scale=170,distance=.000012,strength=.08):
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bs=nodes.get('Principled BSDF')
    texture=nodes.new('ShaderNodeTexNoise')
    texture.inputs['Scale'].default_value=scale
    texture.inputs['Detail'].default_value=2
    bump=nodes.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value=distance
    bump.inputs['Strength'].default_value=strength
    links.new(texture.outputs['Fac'],bump.inputs['Height'])
    links.new(bump.outputs['Normal'],bs.inputs['Normal'])


def curve_position(t):
    return Vector(((2+math.cos(3*t))*math.cos(2*t),
                   (2+math.cos(3*t))*math.sin(2*t),math.sin(3*t)))*.385


def ribbon(metal,enamel,parent):
    vertices,faces,indices=[],[],[]
    nu=320
    # A rounded rectangular cross-section gives a wide satin face, finite
    # physical thickness and narrow polished edges, rather than a wire knot.
    section=[]
    for corner,(cx,cy,start) in enumerate([(1,1,0),(-1,1,math.pi/2),
                                          (-1,-1,math.pi),(1,-1,3*math.pi/2)]):
        for j in range(8):
            angle=start+j/7*math.pi/2
            section.append((cx,cy,math.cos(angle),math.sin(angle)))
    nv=len(section)
    for i in range(nu):
        t=TAU*i/nu
        center=curve_position(t)
        delta=.0005
        tangent=(curve_position(t+delta)-curve_position(t-delta)).normalized()
        curvature=(curve_position(t+delta)-2*center+curve_position(t-delta))
        normal=(curvature-tangent*curvature.dot(tangent)).normalized()
        binormal=tangent.cross(normal).normalized()
        twist=.35*math.sin(3*t)+.23*math.cos(2*t)
        wide=normal*math.cos(twist)+binormal*math.sin(twist)
        thin=tangent.cross(wide).normalized()
        a=.185+.018*math.sin(3*t+.5)
        b=.047
        radius=.021
        for cx,cy,c,s in section:
            x=cx*(a-radius)+radius*c
            y=cy*(b-radius)+radius*s
            vertices.append(point(center+wide*x+thin*y))
    for i in range(nu):
        for j in range(nv):
            # Cross-section then longitudinal direction produces exterior
            # normals for this closed, consistently oriented solid ribbon.
            faces.append((i*nv+j,i*nv+(j+1)%nv,
                          ((i+1)%nu)*nv+(j+1)%nv,((i+1)%nu)*nv+j))
            mid=(section[j][1]+section[(j+1)%nv][1])/2
            indices.append(1 if mid < -.4 else 0)
    data=bpy.data.meshes.new('Continuous solid trefoil ribbon')
    data.from_pydata(vertices,[],faces)
    data.update()
    obj=bpy.data.objects.new('Aperture / titanium and enamel trefoil',data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(metal)
    data.materials.append(enamel)
    for polygon,index in zip(data.polygons,indices):
        polygon.use_smooth=True
        polygon.material_index=index
    obj.parent=parent
    obj.rotation_euler=(math.radians(68),math.radians(-9),math.radians(-14))
    return obj


def sphere(name,location,radius,mat,scale=(1,1,1),parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,
                                       radius=radius*S,location=point(location))
    obj=bpy.context.object
    obj.name=name
    obj.scale=scale
    obj.parent=parent
    obj.data.materials.append(mat)
    for p in obj.data.polygons: p.use_smooth=True
    return obj


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def light(name,location,color,power,size,target=(0,0,1.3)):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=power*S*S
    data.color=color
    data.shape='DISK'
    data.size=size*S
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location=point(location)
    aim(obj,point(target))


def build(args):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.render.resolution_x=1600
    scene.render.resolution_y=800
    scene.render.resolution_percentage=args.percent
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.threads_mode='FIXED'
    scene.render.threads=args.threads
    scene.render.use_persistent_data=True
    scene.render.fps=20
    scene.cycles.device='CPU'
    scene.cycles.samples=args.samples
    scene.cycles.use_denoising=False
    scene.cycles.use_adaptive_sampling=True
    scene.cycles.adaptive_min_samples=min(4,args.samples)
    scene.cycles.adaptive_threshold=.08
    scene.cycles.max_bounces=6
    scene.cycles.diffuse_bounces=2
    scene.cycles.glossy_bounces=4
    scene.cycles.seed=281
    scene.cycles.use_animated_seed=False
    scene.cycles.sample_clamp_indirect=3
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=.2
    scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value=(.055,.069,.08,1)
    bg.inputs['Strength'].default_value=.22

    titanium=material('Satin champagne titanium',(.63,.58,.49),.94,.23,.12)
    titanium.node_tree.nodes.get('Principled BSDF').inputs['Anisotropic'].default_value=.18
    microfinish(titanium)
    enamel=material('Deep teal vitreous enamel',(.012,.075,.069),.12,.24,.65)
    pearl=material('Warm ivory porcelain',(.72,.69,.61),.08,.19,.55)
    pearl.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Weight'].default_value=.045
    pearl.node_tree.nodes.get('Principled BSDF').inputs['Subsurface Radius'].default_value=(.002,.0015,.001)
    microfinish(pearl,90,.000007,.035)
    darkpearl=material('Black polished titanium',(.028,.035,.039),.92,.16,.2)
    obsidian=material('Obsidian circular plinth',(.008,.011,.014),.3,.19,.25)
    microfinish(obsidian,160,.000008,.04)
    floor=material('Ink studio floor / restrained reflections',(.008,.012,.015),.12,.36,.09)
    floor.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.25

    root=bpy.data.objects.new('Levitating Aperture',None)
    bpy.context.collection.objects.link(root)
    root.location=point((0,0,1.51))
    sculpture=ribbon(titanium,enamel,root)
    seed=sphere('Porcelain seed in the aperture',(0,0,0),.142,pearl,
                (1,.93,1.12),root)
    seed.rotation_euler=(.2,-.1,.14)

    bpy.ops.mesh.primitive_cylinder_add(vertices=128,radius=1.86*S,
                                       depth=.15*S,location=point((0,0,.075)))
    pedestal=bpy.context.object
    pedestal.name='Circular obsidian pedestal / actual shadow receiver'
    pedestal.data.materials.append(obsidian)
    bevel=pedestal.modifiers.new('Physical ground and polished bevel','BEVEL')
    bevel.width=.0024
    bevel.segments=4
    for polygon in pedestal.data.polygons:
        polygon.use_smooth=len(polygon.vertices)==4
    bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,-.0001))
    bpy.context.object.name='Dark glossy photographic studio floor'
    bpy.context.object.data.materials.append(floor)
    light('Large warm studio key',(-3.8,-3,7.8),(1,.9,.77),2400,3.6)
    light('Restrained cool edge',(3.4,2.8,4.4),(.67,.78,1),380,3.2)
    light('Broad neutral fill',(1,-5,4.5),(.86,.91,1),180,4.7)

    bpy.ops.object.camera_add(location=point((7.2,-15,7.2)))
    camera=bpy.context.object
    camera.name='Static 85 mm physical studio camera'
    camera.data.type='PERSP'
    camera.data.lens=85
    camera.data.sensor_width=36
    aim(camera,point((0,0,1.04)))
    camera.data.dof.use_dof=True
    camera.data.dof.aperture_fstop=8
    camera.data.dof.aperture_blades=9
    focus=bpy.data.objects.new('Static optical focus at the porcelain seed',None)
    bpy.context.collection.objects.link(focus)
    focus.location=point((0,0,1.51))
    camera.data.dof.focus_object=focus
    scene.camera=camera

    drops=[]
    for i,(location,radius,mat) in enumerate([
        ((-1.29,.23,2.12),.052,titanium),((1.27,.4,1.95),.042,pearl),
    ]):
        obj=sphere(f'Suspended distant mote {i+1}',location,radius,mat)
        drops.append((obj,obj.location.copy(),i+1.2,.022*S))
    quat=camera.rotation_euler.to_quaternion()
    right,up,toward=(quat@Vector(axis) for axis in [(1,0,0),(0,1,0),(0,0,1)])
    foreground=point((0,0,1.51))+right*(1.69*S)+up*(-.62*S)+toward*(6.1*S)
    obj=sphere('Foreground optical bokeh mote',foreground/S,.078,darkpearl)
    drops.append((obj,obj.location.copy(),.4,.018*S))
    return scene,root,sculpture,seed,drops


def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=Path('/tmp/nvxram-v4-hero-raw'))
    p.add_argument('--frame-count',type=int,default=80)
    p.add_argument('--frames',default='all')
    p.add_argument('--samples',type=int,default=32)
    p.add_argument('--percent',type=int,default=100)
    p.add_argument('--threads',type=int,default=3)
    args=p.parse_args(argv)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    scene,root,sculpture,seed,drops=build(args)
    frames=range(args.frame_count) if args.frames=='all' else [int(x) for x in args.frames.split(',')]
    for frame in frames:
        phase=TAU*frame/args.frame_count
        root.location.z=S*(1.51+.028*math.sin(phase))
        root.rotation_euler=(.018*math.sin(phase),.026*math.sin(phase),.024*math.cos(phase))
        for obj,origin,offset,amplitude in drops:
            obj.location=origin+Vector((amplitude*math.sin(phase+offset),
                                       amplitude*.4*math.cos(phase+offset),
                                       amplitude*.65*math.sin(phase+offset)))
        scene.render.filepath=str(args.output_dir/f'frame-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'V4_FRAME_DONE {frame}',flush=True)


if __name__=='__main__':
    main()
