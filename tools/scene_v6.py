#!/usr/bin/env python3
"""PELAGIC / THE RELIC: one original, physically lit underwater environment.

A thin scalloped gelatinous bell, radial luminous tissue, folded oral arms and
delicate trailing tentacles occupy real 3D space. The camera's optical aperture
separates the organism from distant life and suspended particles. No world
volume or downloaded textures. A weathered stone bas-relief carries the handle
as real geometry, sharing the same grazing cyan light and shadow receivers.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector, noise

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


def gel_material(name,color,strength=1,opacity=.49):
    material=mat(name,color,.24,.065*strength,.35,.32)
    nodes,links=material.node_tree.nodes,material.node_tree.links
    bs=nodes.get('Principled BSDF')
    transparent=nodes.new('ShaderNodeBsdfTransparent')
    blend=nodes.new('ShaderNodeMixShader')
    blend.inputs[0].default_value=opacity
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
    scallop=1+.059*math.cos(12*theta)*math.sin(alpha)**7
    radius=1.03*math.sin(alpha)*scallop
    z=(.64*math.cos(alpha)+.031*math.cos(12*theta)*math.sin(alpha)**8
       +.008*math.sin(5*theta)*math.sin(alpha)**3)
    return Vector((radius*math.cos(theta),radius*math.sin(theta),z))


def organism(name,location,scale,phase_offset=0,secondary=False):
    root=bpy.data.objects.new(name,None)
    bpy.context.collection.objects.link(root)
    root.location=p(location)
    root.scale=(scale,scale,scale)
    root.rotation_euler=(.06,-.09,-.10)
    lightlevel=.22 if secondary else 1
    gel=gel_material(name+' / delicate gelatin',(.12,.32,.35),lightlevel,.37 if not secondary else .49)
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
            if not secondary and j%5==0:
                x-=.14*t*t
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


def stone_material():
    material=mat('Wet weathered submerged stone',(.027,.045,.055),.62,0,0,.12)
    nodes,links=material.node_tree.nodes,material.node_tree.links
    bs=nodes.get('Principled BSDF')
    geometry=nodes.new('ShaderNodeNewGeometry')
    coarse=nodes.new('ShaderNodeTexNoise'); coarse.inputs['Scale'].default_value=78
    coarse.inputs['Detail'].default_value=4
    fine=nodes.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value=800
    fine.inputs['Detail'].default_value=3
    ramp=nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color=(.011,.023,.031,1)
    ramp.color_ramp.elements[1].color=(.052,.075,.080,1)
    bump=nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.34; bump.inputs['Distance'].default_value=.00035
    links.new(geometry.outputs['Position'],coarse.inputs['Vector'])
    links.new(geometry.outputs['Position'],fine.inputs['Vector'])
    links.new(coarse.outputs['Fac'],ramp.inputs[0])
    links.new(ramp.outputs[0],bs.inputs['Base Color'])
    links.new(fine.outputs['Fac'],bump.inputs['Height'])
    links.new(bump.outputs[0],bs.inputs['Normal'])
    return material


def submerged_relic(stone,font):
    root=bpy.data.objects.new('Partly buried weathered relic',None)
    bpy.context.collection.objects.link(root)
    root.location=p((-1.70,-.72,-.065)); root.rotation_euler=(.025,0,-.055)
    outline=[(-1.30,-.50),(-1.21,-.10),(-1.05,.34),(-.68,.45),
             (-.48,.57),(.58,.47),(.84,.30),(1.25,.27),
             (1.31,.06),(1.08,-.09),(1.23,-.24),(.96,-.54),
             (.55,-.60),(-.90,-.55)]
    vertices=[(x,depth,z) for depth in (-.24,.24) for x,z in outline]
    n=len(outline)
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    obj=mesh('Irregular marine stone fragment',vertices,faces,stone,root)
    bevel=obj.modifiers.new('Eroded rounded stone edges','BEVEL')
    bevel.width=.0035; bevel.segments=3
    # Raised chiseled bas-relief is embedded in the stone face. Its world-space
    # grain, bevels and actual contact shadows integrate it with the relic.
    text=bpy.data.curves.new('nvxraM / physical chiseled bas-relief','FONT')
    text.body='nvxraM'; text.font=font
    text.align_x='CENTER'; text.align_y='CENTER'; text.size=.064
    text.extrude=.0015; text.bevel_depth=.00080; text.bevel_resolution=2
    label=bpy.data.objects.new('nvxraM carved stone lettering',text)
    bpy.context.collection.objects.link(label)
    label.parent=root; label.location=p((0,-.242,.035)); label.rotation_euler=(math.pi/2,0,0)
    label.data.materials.append(stone)
    return root,label


def seafloor(stone):
    floor=stone.copy(); floor.name='Physical seafloor with distant indigo attenuation'
    nodes,links=floor.node_tree.nodes,floor.node_tree.links
    geometry=nodes.get('Geometry')
    separate=nodes.new('ShaderNodeSeparateXYZ')
    fade=nodes.new('ShaderNodeMapRange'); fade.interpolation_type='SMOOTHSTEP'
    fade.inputs['From Min'].default_value=.50
    fade.inputs['From Max'].default_value=1.40
    emission=nodes.new('ShaderNodeEmission')
    emission.inputs[0].default_value=(.002,.0075,.020,1)
    blend=nodes.new('ShaderNodeMixShader')
    links.new(geometry.outputs['Position'],separate.inputs[0])
    links.new(separate.outputs['Y'],fade.inputs['Value'])
    links.new(fade.outputs['Result'],blend.inputs[0])
    links.new(nodes.get('Principled BSDF').outputs[0],blend.inputs[1])
    links.new(emission.outputs[0],blend.inputs[2])
    links.new(blend.outputs[0],nodes.get('Material Output').inputs['Surface'])
    vertices,faces=[],[]
    nx,ny=43,61
    for j in range(ny):
        y=-3.7+90*j/(ny-1)
        for i in range(nx):
            x=-8+16*i/(nx-1)
            z=-.59+.012*y+.026*math.sin(x*.9)*math.sin(y*.7)
            z+=.018*noise.noise_vector(Vector((x*.7,y*.7,2)))[0]
            vertices.append((x,y,z))
    for j in range(ny-1):
        for i in range(nx-1):
            a=j*nx+i; faces.append((a,a+1,a+nx+1,a+nx))
    return mesh('Gently sloped physical seafloor / shadow receiver',vertices,faces,floor)


def hidden_organ(root):
    dark=mat('Dark wet annular tissue',(.009,.017,.026),.35,.012,.1,.23)
    warm=mat('Restrained peach inner tissue edge',(.42,.16,.085),.37,.19,.12,.1)
    vertices,faces=[],[]
    nu,nv=96,12
    for i in range(nu):
        angle=TAU*i/nu
        radius=.245*(1+.10*math.sin(5*angle)+.035*math.cos(9*angle))
        tube=.045+.009*math.sin(3*angle)
        for j in range(nv):
            v=TAU*j/nv
            vertices.append(((radius+tube*math.cos(v))*math.cos(angle),
                             (radius+tube*math.cos(v))*math.sin(angle),
                             tube*math.sin(v)+.018*math.sin(4*angle)))
    for i in range(nu):
        for j in range(nv):
            faces.append((i*nv+j,((i+1)%nu)*nv+j,
                          ((i+1)%nu)*nv+(j+1)%nv,i*nv+(j+1)%nv))
    obj=mesh('Uncanny folded annular internal organ',vertices,faces,dark,root)
    obj.data.materials.append(warm)
    for i,face in enumerate(obj.data.polygons):
        face.material_index=1 if i%nv in (7,8) else 0
    obj.location=p((0,-.10,.275)); obj.rotation_euler=(1.04,.18,-.2)


def living_edges(relic):
    body=gel_material('Foreground living marine tissue',(.08,.25,.29),.7)
    tip=mat('Restrained cyan cilia tips',(.045,.5,.55),.35,.55)
    groups=[]
    # Corners frame the name, leaving the letter counters and strokes clear.
    anchors=[(-1.26,-.18,-.46),(-1.08,.05,.30),(1.16,-.10,-.43),
             (1.27,.08,.16),(-1.40,.32,-.48)]
    for index,anchor in enumerate(anchors):
        for j in range(6):
            angle=-.9+j*.32+index
            length=.24+.14*(.5+.5*math.sin(j*1.8+index))
            points=[]
            for k in range(25):
                t=k/24
                points.append(Vector(anchor)+Vector((.13*t*math.cos(angle),
                              -.08*t*math.sin(angle),length*t+.02*math.sin(3*t+j))))
            obj=curve(f'Living relic cilium {index}/{j}',points,.0042,body,relic)
            groups.append((obj,[Vector(v) for v in points],index+j))
            curve(f'Bioluminescent cilium tip {index}/{j}',points[-5:],.0047,tip,relic)
    # A sparse near-camera fan establishes optical depth in the same scene.
    for j in range(7):
        points=[]
        for k in range(35):
            t=k/34
            points.append(Vector((-.68+.12*math.sin(j*.7)*t,-2.0+.12*t,
                                  -.61+(.40+.12*math.sin(j))*t)))
        obj=curve(f'Near-camera marine frond {j}',points,.005,body)
        groups.append((obj,[Vector(v) for v in points],j+.7))
    return groups


def build(args):
    if not args.font.is_file():
        raise FileNotFoundError(f'Required physical lettering font is missing: {args.font}. Pass an existing TrueType font with --font.')
    font=bpy.data.fonts.load(str(args.font.resolve()))
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.render.resolution_x=1600; scene.render.resolution_y=900
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
    main=organism('Pelagic / primary medusa',(.78,0,1.90),1)
    distant=organism('Pelagic / distant medusa',(-1.9,5.3,1.28),.48,1.4,True)
    hidden_organ(main[0])
    stone=stone_material()
    seafloor(stone)
    relic,_=submerged_relic(stone,font)
    living_edges(relic)
    # A compact directional source gives the living tissue, carved bevels and
    # seabed coherent shadows. The broad fill is deliberately much weaker.
    light('Directional cyan water light',(3.2,-4.4,6.1),(.24,.85,1),1150,1.5,(-.4,0,.3))
    light('Jelly-side cyan grazing light',(.8,-1.3,1.6),(.10,.65,.75),110,1.2,(-1.7,-.72,0))
    light('Weak broad blue water fill',(-3,-4,4.5),(.4,.62,.85),130,5)
    light('Low cyan letter-bevel rake',(-1.8,-3,.8),(.15,.70,.78),55,.75,(-1.7,-.72,0))
    light('Restrained violet rear separation',(3.5,3.2,3.6),(.49,.32,1),120,3)
    light('Restrained warm internal bounce',(.8,-1.8,2.9),(1,.63,.45),35,1.8)
    bpy.ops.object.camera_add(location=p((1.4,-16.5,4.4)))
    camera=bpy.context.object; camera.name='Static 85 mm underwater observation camera'
    camera.data.type='PERSP'; camera.data.lens=85; camera.data.sensor_width=36
    aim(camera,p((0,0,1.03)))
    camera.data.dof.use_dof=True; camera.data.dof.aperture_fstop=8; camera.data.dof.aperture_blades=9
    focus=bpy.data.objects.new('Static optical focus / main bell interior',None)
    bpy.context.collection.objects.link(focus); focus.location=p((.78,0,2.16))
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
    parser.add_argument('--output-dir',type=Path,default=Path('/tmp/nvxram-v6-raw'))
    parser.add_argument('--frame-count',type=int,default=60); parser.add_argument('--frames',default='all')
    parser.add_argument('--samples',type=int,default=48); parser.add_argument('--percent',type=int,default=100)
    parser.add_argument('--threads',type=int,default=4)
    parser.add_argument('--font',type=Path,default=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
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
        print(f'V6_FRAME_DONE {frame}',flush=True)


if __name__=='__main__': main()
