#!/usr/bin/env python3
"""PELAGIC: an original procedural deep-sea organism, photographed in Cycles.

A thin scalloped gelatinous bell, radial luminous tissue, folded oral arms and
delicate trailing tentacles occupy real 3D space. The camera's optical aperture
separates the organism from distant life and suspended particles. No world
volume, downloaded textures, hard stage, metal or typographic elements.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

S=.1
TAU=math.tau


def p(value): return Vector(value)*S


def mat(name,color,rough=.3,emission=0,transmission=0,coat=0):
    material=bpy.data.materials.new(name)
    material.use_nodes=True
    bs=material.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Roughness'].default_value=rough
    bs.inputs['IOR'].default_value=1.18
    bs.inputs['Transmission Weight'].default_value=transmission
    bs.inputs['Coat Weight'].default_value=coat
    bs.inputs['Coat Roughness'].default_value=.15
    bs.inputs['Emission Color'].default_value=(*color,1)
    bs.inputs['Emission Strength'].default_value=emission
    return material


def gel_material(name,color,strength=1):
    material=mat(name,color,.19,.075*strength,.35,.42)
    nodes,links=material.node_tree.nodes,material.node_tree.links
    bs=nodes.get('Principled BSDF')
    transparent=nodes.new('ShaderNodeBsdfTransparent')
    blend=nodes.new('ShaderNodeMixShader')
    blend.inputs[0].default_value=.57
    links.new(transparent.outputs[0],blend.inputs[1])
    links.new(bs.outputs[0],blend.inputs[2])
    links.new(blend.outputs[0],nodes.get('Material Output').inputs['Surface'])
    return material


def mesh(name,vertices,faces,material,parent=None):
    data=bpy.data.meshes.new(name)
    data.from_pydata([p(v) for v in vertices],[],faces)
    data.update()
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.parent=parent
    data.materials.append(material)
    for poly in data.polygons: poly.use_smooth=True
    return obj


def curve(name,points,radius,material,parent=None):
    data=bpy.data.curves.new(name,'CURVE')
    data.dimensions='3D'
    data.resolution_u=1
    data.bevel_depth=radius*S
    data.bevel_resolution=2
    spline=data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for vertex,co in zip(spline.points,points): vertex.co=(*p(co),1)
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.parent=parent
    data.materials.append(material)
    return obj


def bell_point(theta,alpha):
    scallop=1+.047*math.cos(12*theta)*math.sin(alpha)**7
    radius=1.03*math.sin(alpha)*scallop
    z=.64*math.cos(alpha)+.025*math.cos(12*theta)*math.sin(alpha)**8
    return Vector((radius*math.cos(theta),radius*math.sin(theta),z))


def organism(name,location,scale,phase_offset=0,secondary=False):
    root=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(root)
    root.location=p(location)
    root.scale=(scale,scale,scale)
    root.rotation_euler=(.06,-.09,-.10)
    lightlevel=.22 if secondary else 1
    gel=gel_material(name+' / delicate gelatin',(.12,.32,.35),lightlevel)
    cyan=mat(name+' / radial bioluminescent tissue',(.055,.68,.68),.28,1.5*lightlevel)
    strand=mat(name+' / fine translucent tentacles',(.13,.45,.49),.3,.42*lightlevel,.22,.15)
    peach=gel_material(name+' / peach oral tissue',(.8,.36,.24),lightlevel)
    violet=gel_material(name+' / violet inner folds',(.24,.16,.42),lightlevel)
    vertices,faces=[],[]
    nu,nv=30,128
    for i in range(nu):
        alpha=.008+(math.pi/2+.095-.008)*i/(nu-1)
        for j in range(nv): vertices.append(bell_point(TAU*j/nv,alpha))
    for i in range(nu-1):
        for j in range(nv):
            a=i*nv+j
            faces.append((a,i*nv+(j+1)%nv,(i+1)*nv+(j+1)%nv,a+nv))
    bell=mesh(name+' / scalloped thin bell',vertices,faces,gel,root)
    shell=bell.modifiers.new('Thin biological membrane','SOLIDIFY')
    shell.thickness=.00045
    shell.offset=-1
    for j in range(16):
        angle=TAU*j/16
        points=[bell_point(angle+.018*math.sin(5*a+j),a)*1.005
                for a in [(.06+(math.pi/2+.07-.06)*k/88) for k in range(89)]]
        curve(name+f' / radial canal {j:02}',points,.0023 if j%2 else .0031,cyan,root)
    # Folds have real surface area and curl through depth, rather than being
    # flat painted lines. Their warm translucent edges contrast with the bell.
    arms=[]
    for arm in range(4):
        vertices,faces=[],[]
        angle=arm*TAU/4+.35
        for i in range(70):
            t=i/69
            length=1.50+.13*math.sin(arm+1)
            radius=.16+.15*t+.12*math.sin(2.3*math.pi*t+arm)
            center=Vector((radius*math.cos(angle+.8*t),radius*math.sin(angle+.8*t),-.05-length*t))
            side=Vector((math.cos(angle+1.6*t),math.sin(angle+1.6*t),0))
            width=(.14+.055*math.sin(11*math.pi*t+arm))*(1-.65*t)
            for j in range(7):
                v=-1+2*j/6
                fold=Vector((0,.055*math.sin(8*math.pi*t+v*2+arm),.035*math.cos(v*math.pi)))
                vertices.append(center+side*(width*v)+fold)
        for i in range(69):
            for j in range(6):
                a=i*7+j
                faces.append((a,a+1,a+8,a+7))
        arms.append(mesh(name+f' / folded oral arm {arm}',vertices,faces,peach if arm%2 else violet,root))
    tentacles=[]
    for j in range(18):
        angle=TAU*j/18+.09
        length=1.55+.54*(.5+.5*math.sin(j*1.73))
        points=[]
        for k in range(100):
            t=k/99
            radius=.96*(1-.45*t)
            x=radius*math.cos(angle)+.15*t*math.sin(2.5*math.pi*t+j)
            y=radius*math.sin(angle)+.12*t*math.sin(2.0*math.pi*t+j*.8)
            points.append(Vector((x,y,-.055-length*t)))
        obj=curve(name+f' / trailing tentacle {j:02}',points,.0017 if j%3 else .0026,
                  strand if j%4 else cyan,root)
        tentacles.append((obj,[Vector(v) for v in points],angle,j))
    return root,bell,arms,tentacles,phase_offset,scale


def aim(obj,target): obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def light(name,location,color,energy,size,target=(.8,0,1.9)):
    data=bpy.data.lights.new(name,'AREA')
    data.energy=energy*S*S
    data.color=color
    data.shape='DISK'
    data.size=size*S
    obj=bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location=p(location)
    aim(obj,p(target))


def backdrop(camera):
    # An unlit gradient at depth suggests the abyss without an expensive world
    # volume. All life and particles remain physical 3D objects in front of it.
    mat_bg=bpy.data.materials.new('Pelagic indigo light falloff')
    mat_bg.use_nodes=True
    nodes,links=mat_bg.node_tree.nodes,mat_bg.node_tree.links
    nodes.clear()
    tex=nodes.new('ShaderNodeTexCoord')
    subtract=nodes.new('ShaderNodeVectorMath'); subtract.operation='SUBTRACT'
    subtract.inputs[1].default_value=(.62,.65,0)
    distance=nodes.new('ShaderNodeVectorMath'); distance.operation='LENGTH'
    ramp=nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position=.02
    ramp.color_ramp.elements[0].color=(.006,.021,.047,1)
    ramp.color_ramp.elements[1].position=.8
    ramp.color_ramp.elements[1].color=(.0003,.0012,.007,1)
    emission=nodes.new('ShaderNodeEmission')
    output=nodes.new('ShaderNodeOutputMaterial')
    links.new(tex.outputs['Generated'],subtract.inputs[0])
    links.new(subtract.outputs[0],distance.inputs[0])
    links.new(distance.outputs[0],ramp.inputs[0])
    links.new(ramp.outputs[0],emission.inputs[0])
    links.new(emission.outputs[0],output.inputs[0])
    bpy.ops.mesh.primitive_plane_add(size=3,location=(0,1.9,.11))
    obj=bpy.context.object
    obj.name='Distant underwater light gradient'
    obj.rotation_euler=camera.rotation_euler
    obj.data.materials.append(mat_bg)


def build(args):
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.render.resolution_x=1600; scene.render.resolution_y=800
    scene.render.resolution_percentage=args.percent
    scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGB'
    scene.render.threads_mode='FIXED'; scene.render.threads=args.threads
    scene.render.use_persistent_data=True; scene.render.fps=20
    scene.cycles.device='CPU'; scene.cycles.samples=args.samples
    scene.cycles.use_denoising=False; scene.cycles.use_adaptive_sampling=True
    scene.cycles.adaptive_min_samples=min(4,args.samples); scene.cycles.adaptive_threshold=.08
    scene.cycles.max_bounces=6; scene.cycles.diffuse_bounces=2
    scene.cycles.glossy_bounces=3; scene.cycles.transmission_bounces=3
    scene.cycles.transparent_max_bounces=6
    scene.cycles.seed=527; scene.cycles.use_animated_seed=False
    scene.cycles.sample_clamp_indirect=2
    scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=0
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.003,.009,.028,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.2
    main=organism('Pelagic / primary medusa',(.78,0,1.71),1)
    distant=organism('Pelagic / distant medusa',(-1.9,5.3,1.28),.48,1.4,True)
    light('Cool diffuse water light',(-3,-4.8,6.6),(.38,.76,1),800,5)
    light('Soft violet rear tissue separation',(3.5,3.2,3.6),(.49,.32,1),240,4)
    light('Restrained warm internal bounce',(.8,-1.8,2.9),(1,.63,.45),35,1.8)
    bpy.ops.object.camera_add(location=p((1.4,-16.5,3.8)))
    camera=bpy.context.object; camera.name='Static 85 mm underwater observation camera'
    camera.data.type='PERSP'; camera.data.lens=85; camera.data.sensor_width=36
    aim(camera,p((0,0,1.03)))
    camera.data.dof.use_dof=True; camera.data.dof.aperture_fstop=5.6; camera.data.dof.aperture_blades=9
    focus=bpy.data.objects.new('Static optical focus / main bell interior',None)
    bpy.context.collection.objects.link(focus); focus.location=p((.78,0,1.97))
    camera.data.dof.focus_object=focus; scene.camera=camera
    backdrop(camera)
    dust=mat('Sparse suspended plankton',(.22,.47,.57),.5,.35)
    rng=random.Random(527)
    particles=[]
    for i in range(45):
        location=(rng.uniform(-3.6,3.5),rng.uniform(-5.5,5),rng.uniform(-.45,3.35))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=rng.uniform(.004,.013)*S,location=p(location))
        obj=bpy.context.object; obj.name=f'Suspended fine particle {i:02}'
        obj.data.materials.append(dust)
        particles.append((obj,obj.location.copy(),rng.random()*TAU))
    return scene,[main,distant],particles


def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=Path('/tmp/nvxram-v5-hero-raw'))
    parser.add_argument('--frame-count',type=int,default=60); parser.add_argument('--frames',default='all')
    parser.add_argument('--samples',type=int,default=32); parser.add_argument('--percent',type=int,default=100)
    parser.add_argument('--threads',type=int,default=3)
    args=parser.parse_args(argv); args.output_dir.mkdir(parents=True,exist_ok=True)
    scene,organisms,particles=build(args)
    frames=range(args.frame_count) if args.frames=='all' else [int(v) for v in args.frames.split(',')]
    for frame in frames:
        phase=TAU*frame/args.frame_count
        for root,bell,arms,tentacles,offset,scale in organisms:
            q=phase+offset
            pulse=.055*math.sin(q)
            root.scale=(scale*(1+pulse),scale*(1+pulse),scale*(1-.35*pulse))
            root.rotation_euler=(.06+.014*math.sin(q),-.09+.02*math.sin(q),-.10+.025*math.cos(q))
            for obj,original,angle,index in tentacles:
                for k,(vertex,base) in enumerate(zip(obj.data.splines[0].points,original)):
                    t=k/(len(original)-1)
                    sway=Vector((.11*t*t*math.sin(q+2*t+index*.4),
                                 .07*t*t*math.sin(q+2.5*t+index*.6),.025*t*math.sin(q+index)))
                    vertex.co=(*p(base+sway),1)
        for obj,origin,offset in particles:
            obj.location=origin+p((.025*math.sin(phase+offset),.01*math.cos(phase+offset),.015*math.sin(phase+offset)))
        scene.render.filepath=str(args.output_dir/f'frame-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'V5_FRAME_DONE {frame}',flush=True)


if __name__=='__main__': main()
