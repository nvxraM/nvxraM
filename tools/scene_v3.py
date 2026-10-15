#!/usr/bin/env python3
"""A procedural, physically photographed impossible specimen for profile v3.

Three eroded basalt petals peel into machined titanium around an ivory seed.
The sculpture floats over a real textured plinth. All dimensions use meters;
the specimen is about 25 cm tall and is photographed through an 85 mm lens.
Cycles traces the actual soft shadows, metallic reflections and optical DOF.
No imported art, emissive decoration, neon, or external textures are used.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector, noise

S = .1
TAU = math.tau


def position(values):
    return Vector(values) * S


def material(name, color, metallic=0, roughness=.4):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = roughness
    return mat


def surface_noise(mat, scale, distance, strength, roughness=None):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    texture = nodes.new('ShaderNodeTexNoise')
    texture.inputs['Scale'].default_value = scale
    texture.inputs['Detail'].default_value = 3
    texture.inputs['Roughness'].default_value = .7
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = strength
    bump.inputs['Distance'].default_value = distance
    links.new(texture.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    if roughness:
        ramp = nodes.new('ShaderNodeMapRange')
        ramp.inputs['From Min'].default_value = 0
        ramp.inputs['From Max'].default_value = 1
        ramp.inputs['To Min'].default_value = roughness[0]
        ramp.inputs['To Max'].default_value = roughness[1]
        links.new(texture.outputs['Fac'], ramp.inputs['Value'])
        links.new(ramp.outputs['Result'], bs.inputs['Roughness'])


def stone_material():
    mat = material('Eroded charcoal basalt', (.037, .04, .043), 0, .6)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    texture = nodes.new('ShaderNodeTexNoise')
    texture.inputs['Scale'].default_value = 5
    texture.inputs['Detail'].default_value = 5
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (.019, .021, .023, 1)
    ramp.color_ramp.elements[1].color = (.074, .079, .084, 1)
    links.new(texture.outputs['Fac'], ramp.inputs[0])
    links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
    surface_noise(mat, 115, .00027, .32, (.48, .72))
    return mat


def mesh(name, vertices, faces, materials, indices=None, parent=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata([position(p) for p in vertices], [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    for mat in materials:
        data.materials.append(mat)
    for i, polygon in enumerate(data.polygons):
        polygon.use_smooth = True
        if indices: polygon.material_index = indices[i]
    obj.parent = parent
    return obj


def sphere(name, location, radius, mat, parent=None, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24,
                                       radius=radius*S, location=position(location))
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    obj.parent = parent
    obj.data.materials.append(mat)
    for p in obj.data.polygons: p.use_smooth = True
    return obj


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def light(name, location, color, power, size, target=(0, 0, 1.3)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power*S*S
    data.color = color
    data.shape = 'DISK'
    data.size = size*S
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position(location)
    aim(obj, position(target))
    return obj


def petal(name, angle, stone, metal, cut, parent):
    """A thick spherical shell patch, twisted into one open organic lamella."""
    vertices, faces, indices = [], [], []
    nu, nv = 105, 33
    for layer in range(2):
        for i in range(nu):
            t = i/(nu-1)
            latitude = -1.04+2.12*t
            width = .09+.56*math.sin(math.pi*t)**.62
            center_angle = angle+.91*(t-.5)+.1*math.sin(TAU*t)
            for j in range(nv):
                v = -1+2*j/(nv-1)
                phi = center_angle+v*width
                theta = latitude+.075*math.sin(3*phi+1.3)*math.sin(math.pi*t)
                radius = 1.18 if layer == 0 else 1.035
                unit = Vector((math.cos(theta)*math.cos(phi),
                               math.cos(theta)*math.sin(phi), math.sin(theta)))
                if layer == 0:
                    # Millimeter-scale irregularity in the silhouette, not a
                    # noisy displacement that overwhelms the physical form.
                    radius += .027*noise.noise_vector(unit*5.5)[0]
                    radius += .009*noise.noise_vector(unit*17)[1]
                vertices.append(tuple(unit*radius))
    layer_size=nu*nv
    for layer in range(2):
        for i in range(nu-1):
            for j in range(nv-1):
                a=layer*layer_size+i*nv+j
                f=(a,a+nv,a+nv+1,a+1)
                faces.append(tuple(reversed(f)) if layer == 0 else f)
                indices.append(layer)
    # Polished cut faces make the shell's real thickness legible in the light.
    for i in range(nu-1):
        for j in (0, nv-1):
            a=i*nv+j
            face=(a,a+nv,a+nv+layer_size,a+layer_size)
            faces.append(face if j == 0 else tuple(reversed(face)))
            indices.append(2)
    for i in (0,nu-1):
        for j in range(nv-1):
            a=i*nv+j
            face=(a,a+1,a+1+layer_size,a+layer_size)
            faces.append(face if i == nu-1 else tuple(reversed(face)))
            indices.append(2)
    obj=mesh(name,vertices,faces,[stone,metal,cut],indices,parent)
    bevel=obj.modifiers.new('Softened real cut edges','BEVEL')
    bevel.width=.0012
    bevel.segments=2
    return obj


def titanium_curl(mat,parent):
    """One continuous flat helicoid emerges from the shell's hidden interior."""
    vertices,faces=[],[]
    nu=220
    for i in range(nu):
        t=i/(nu-1)
        angle=-.85*math.pi+2.45*math.pi*t
        radius=.61+.075*math.sin(TAU*t)
        z=-.62+1.30*t
        width=.11+.055*math.sin(math.pi*t)
        # A solid, gently twisted titanium strip, with visibly finite edges.
        for radial,height in [(-width/2,-.022),(width/2,-.022),
                              (width/2,.022),(-width/2,.022)]:
            rr=radius+radial*math.cos(.5*angle)
            zz=z+radial*math.sin(.5*angle)+height
            vertices.append((rr*math.cos(angle),rr*math.sin(angle),zz))
    for i in range(nu-1):
        for j in range(4):
            a=i*4+j
            faces.append((a,i*4+(j+1)%4,(i+1)*4+(j+1)%4,a+4))
    faces.extend([(3,2,1,0),tuple((nu-1)*4+j for j in range(4))])
    obj=mesh('Unfolded titanium helicoid',vertices,faces,[mat],parent=parent)
    bevel=obj.modifiers.new('Rounded machined strip edges','BEVEL')
    bevel.width=.0009
    bevel.segments=3
    return obj


def build(args):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'
    scene.render.resolution_x=1600
    scene.render.resolution_y=900
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
    scene.cycles.adaptive_threshold=.08
    scene.cycles.adaptive_min_samples=min(4,args.samples)
    scene.cycles.max_bounces=7
    scene.cycles.diffuse_bounces=3
    scene.cycles.glossy_bounces=4
    scene.cycles.transmission_bounces=4
    scene.cycles.seed=127
    scene.cycles.use_animated_seed=False
    scene.cycles.sample_clamp_indirect=3
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=.15
    scene.world.use_nodes=True
    bg=scene.world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value=(.07,.075,.085,1)
    bg.inputs['Strength'].default_value=.22

    stone=stone_material()
    metal=material('Warm satin titanium',(.61,.59,.53),.92,.23)
    metal.node_tree.nodes.get('Principled BSDF').inputs['Anisotropic'].default_value=.2
    surface_noise(metal,180,.000012,.1,(.20,.27))
    cut=material('Machined pale bronze cut',(.46,.40,.29),.86,.29)
    surface_noise(cut,150,.00002,.08)
    pearl=material('Ivory porcelain seed',(.8,.77,.68),.12,.2)
    pearl_bs=pearl.node_tree.nodes.get('Principled BSDF')
    pearl_bs.inputs['Coat Weight'].default_value=.65
    pearl_bs.inputs['Coat Roughness'].default_value=.09
    pearl_bs.inputs['Subsurface Weight'].default_value=.06
    pearl_bs.inputs['Subsurface Radius'].default_value=(.003,.002,.001)
    pearl_bs.inputs['Thin Film Thickness'].default_value=280
    pearl_bs.inputs['Thin Film IOR'].default_value=1.37
    surface_noise(pearl,90,.000008,.05)

    root=bpy.data.objects.new('Levitating opened specimen',None)
    bpy.context.collection.objects.link(root)
    root.location=position((0,0,1.63))
    root.rotation_euler=(.05,.08,-.12)
    petals=[]
    # The open side faces the lens; staggered angles reveal polished interiors.
    for i,(angle,offset,rotation) in enumerate([
        (math.radians(25),(.20,.10,.03),(.12,-.10,.12)),
        (math.radians(150),(-.13,.17,.13),(-.08,.14,-.08)),
        (math.radians(247),(-.23,-.19,-.10),(.07,-.09,-.05)),
    ]):
        obj=petal(f'Basalt chrysalis / lamella {i+1}',angle,stone,metal,cut,root)
        obj.location=position(offset)
        obj.rotation_euler=rotation
        petals.append((obj,obj.location.copy(),Vector(rotation),i*TAU/3))
    seed=sphere('Suspended porcelain seed',(0,0,0),.32,pearl,root,(1,.86,1.18))
    seed.rotation_euler=(.12,-.2,.08)
    titanium_curl(metal,root)
    chrome=material('Liquid polished titanium',(.65,.66,.64),1,.12)
    drops=[]
    for i,(point,radius) in enumerate([
        ((-1.36,-.18,1.45),.095),((1.35,.1,1.94),.12),
        ((.56,.75,2.73),.073),((-.45,-.27,.43),.055),
    ]):
        obj=sphere(f'Suspended titanium bead {i+1}',point,radius,chrome,
                   scale=(1,1,1.16 if i%2 else .96))
        drops.append((obj,obj.location.copy(),i*.9,.035*S))

    # A real beveled, subtly porous stage supplies contact and cast shadows.
    plinth=material('Dark honed concrete',(.035,.039,.042),.03,.58)
    surface_noise(plinth,125,.00012,.18,(.53,.67))
    bpy.ops.mesh.primitive_cube_add(size=1,location=position((0,0,.12)))
    block=bpy.context.object
    block.name='Honed concrete plinth / real cast shadows'
    block.dimensions=position((3.65,2.7,.24))
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel=block.modifiers.new('Small physical bevel','BEVEL')
    bevel.width=.004
    bevel.segments=4
    block.data.materials.append(plinth)
    # A physical satin-metal inlay sits on the front face of the stage. It
    # receives the same light, perspective and lens focus as the specimen.
    label_data=bpy.data.curves.new('nvxraM / plinth inlay','FONT')
    label_data.body='nvxraM'
    label_data.align_x='CENTER'
    label_data.align_y='CENTER'
    label_data.size=.012
    label_data.space_character=1.16
    label_data.extrude=.000015
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if font.exists(): label_data.font=bpy.data.fonts.load(str(font))
    label=bpy.data.objects.new('Physical nvxraM inlay',label_data)
    bpy.context.collection.objects.link(label)
    label.location=position((0,-1.353,.108))
    label.rotation_euler=(math.pi/2,0,0)
    label.data.materials.append(material('Satin silver inlay',(.42,.43,.41),.75,.3))
    ground=material('Matte charcoal studio floor',(.024,.027,.031),0,.78)
    surface_noise(ground,350,.000035,.08)
    bpy.ops.mesh.primitive_plane_add(size=30,location=(0,0,-.001))
    bpy.context.object.name='Physical studio floor'
    bpy.context.object.data.materials.append(ground)
    light('Coherent warm large softbox',(-3.8,-4.8,7),(1,.88,.73),1800,3.7)
    light('Weak cool rear separation',(3.5,3,4.8),(.69,.79,1),420,3.4)
    light('Broad neutral photographic fill',(2,-4,5.3),(.87,.91,1),260,5)

    bpy.ops.object.camera_add(location=position((8,-15,7)))
    camera=bpy.context.object
    camera.name='Static 85 mm product-photography camera'
    camera.data.type='PERSP'
    camera.data.lens=85
    camera.data.sensor_width=36
    aim(camera,position((0,0,1.23)))
    camera.data.dof.use_dof=True
    focus=bpy.data.objects.new('Static optical focus / central seed',None)
    bpy.context.collection.objects.link(focus)
    focus.location=position((0,0,1.63))
    camera.data.dof.focus_object=focus
    camera.data.dof.aperture_fstop=8
    camera.data.dof.aperture_blades=9
    camera.data.dof.aperture_rotation=.15
    scene.camera=camera

    # Two much closer physical droplets demonstrate optical depth of field.
    quat=camera.rotation_euler.to_quaternion()
    toward=quat@Vector((0,0,1))
    right=quat@Vector((1,0,0))
    up=quat@Vector((0,1,0))
    center=position((0,0,1.63))
    for i,(horizontal,vertical,near,radius) in enumerate([
        (1.55,-.83,7.4,.095),(-1.18,.10,9.4,.075),
    ]):
        point=center+right*(horizontal*S)+up*(vertical*S)+toward*(near*S)
        obj=sphere(f'Foreground defocused droplet {i+1}',point/S,radius,chrome,
                   scale=(1,.9,1.15))
        drops.append((obj,obj.location.copy(),i+1.2,.025*S))
    return scene,root,petals,seed,drops


def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=Path('/tmp/nvxram-v3-hero-raw'))
    p.add_argument('--frame-count',type=int,default=80)
    p.add_argument('--frames',default='all')
    p.add_argument('--samples',type=int,default=32)
    p.add_argument('--percent',type=int,default=100)
    p.add_argument('--threads',type=int,default=4)
    args=p.parse_args(argv)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    scene,root,petals,seed,drops=build(args)
    frames=range(args.frame_count) if args.frames=='all' else [int(i) for i in args.frames.split(',')]
    for frame in frames:
        phase=TAU*frame/args.frame_count
        root.location.z=S*(1.63+.035*math.sin(phase))
        root.rotation_euler=(.05+.018*math.sin(phase),.08+.025*math.sin(phase),
                             -.12+.025*math.cos(phase))
        for obj,origin,rotation,offset in petals:
            obj.location=origin+position((.015*math.sin(phase+offset),
                                         .014*math.cos(phase+offset),
                                         .018*math.sin(phase+offset)))
            obj.rotation_euler=rotation+Vector((.012*math.sin(phase+offset),
                                                .012*math.cos(phase+offset),0))
        for obj,origin,offset,amplitude in drops:
            obj.location=origin+Vector((amplitude*math.sin(phase+offset),
                                       amplitude*.5*math.cos(phase+offset),
                                       amplitude*.7*math.sin(phase+offset)))
        scene.render.filepath=str(args.output_dir/f'frame-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'V3_FRAME_DONE {frame}',flush=True)


if __name__=='__main__':
    main()
