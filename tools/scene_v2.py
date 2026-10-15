#!/usr/bin/env python3
"""Render the original v2 'living machine' sculpture with Blender 4.3+.

All geometry, materials and motion are procedural. No downloaded art, scene
templates, render services or personal information are used.
Run through render_v2_hero.py, or blender --background --python this_file -- --help.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TAU = math.tau


def material(name, color, metallic=0.0, roughness=.3, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Metallic'].default_value = metallic
    bs.inputs['Roughness'].default_value = roughness
    bs.inputs['Coat Weight'].default_value = .35
    bs.inputs['Coat Roughness'].default_value = .12
    bs.inputs['Emission Color'].default_value = (*color, 1)
    bs.inputs['Emission Strength'].default_value = emission
    return mat


def pearl_material():
    mat = material('Pearlescent titanium / folded membrane', (.46, .58, .68), .83, .2)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Thin Film Thickness'].default_value = 425
    bs.inputs['Thin Film IOR'].default_value = 1.38
    bs.inputs['Coat Weight'].default_value = .65
    layer = nodes.new('ShaderNodeLayerWeight')
    layer.inputs['Blend'].default_value = .35
    ramp = nodes.new('ShaderNodeValToRGB')
    stops = ramp.color_ramp
    stops.elements.remove(stops.elements[1])
    stops.elements[0].position = 0
    stops.elements[0].color = (.09, .27, .32, 1)
    for position, color in [(.22, (.42, .66, .7, 1)),
                            (.5, (.56, .38, .64, 1)),
                            (.77, (.79, .72, .67, 1)),
                            (1, (.6, .7, .76, 1))]:
        stops.elements.new(position).color = color
    links.new(layer.outputs['Facing'], ramp.inputs[0])
    links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
    return mat


def mesh(name, vertices, faces, mat, parent=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for polygon in data.polygons:
        polygon.use_smooth = True
    obj.parent = parent
    return obj


def polycurve(name, points, bevel, mat, parent=None):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 2
    data.bevel_depth = bevel
    data.bevel_resolution = 3
    spline = data.splines.new('POLY')
    spline.points.add(len(points)-1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj.parent = parent
    return obj


def sphere(name, point, radius, mat, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=radius,
                                       location=point)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.data.materials.append(mat)
    for p in obj.data.polygons:
        p.use_smooth = True
    return obj


def aim(obj, point):
    obj.rotation_euler = (Vector(point)-obj.location).to_track_quat('-Z', 'Y').to_euler()


def light(name, location, color, energy, size, target=(0, 0, .3), shape='DISK', size_y=None):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.color = color
    data.shape = shape
    data.size = size
    data.use_shadow_jitter = False
    if size_y is not None:
        data.size_y = size_y
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def build(args):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = args.engine
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = args.percent
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.film_transparent = False
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = args.threads
    scene.render.use_persistent_data = True
    scene.render.fps = 20
    if args.engine == 'CYCLES':
        scene.cycles.device = 'CPU'
        scene.cycles.samples = args.samples
        # Some distribution builds omit OpenImageDenoise; preserve a working
        # CPU fallback without relying on a non-existent denoising kernel.
        scene.cycles.use_denoising = False
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = .075
        scene.cycles.max_bounces = 5
        scene.cycles.glossy_bounces = 3
        scene.cycles.diffuse_bounces = 2
    else:
        scene.eevee.taa_render_samples = args.samples
        scene.eevee.use_raytracing = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.world.color = (.008, .012, .02)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.025, .035, .055, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .3

    # Two circularly twisted cross-sections form one continuous, solid membrane.
    pearl = pearl_material()
    titanium = material('Pale platinum', (.6, .72, .74), .92, .14)
    ice = material('Bioluminescent ice', (.1, .82, 1), .3, .16, 2.0)
    lilac = material('Bioluminescent lilac', (.63, .28, 1), .3, .18, 1.5)
    warm = material('Warm molecular bead', (1, .42, .19), .65, .19, .4)
    root = bpy.data.objects.new('Living machine / periodic motion', None)
    bpy.context.collection.objects.link(root)
    root.scale = (.74, .74, .74)
    sculpture = bpy.data.objects.new('Membrane orientation', None)
    bpy.context.collection.objects.link(sculpture)
    sculpture.parent = root
    sculpture.rotation_euler = (math.radians(66), math.radians(-13), math.radians(-18))
    vertices, faces = [], []
    nu, nv = 192, 48
    for i in range(nu):
        u = TAU*i/nu
        major = 1.6 + .09*math.cos(3*u)
        twist = 2*u + .3*math.sin(3*u)
        a, b = .66+.1*math.cos(3*u), .18+.035*math.sin(3*u)
        for j in range(nv):
            v = TAU*j/nv
            radial = a*math.cos(v)*math.cos(twist)-b*math.sin(v)*math.sin(twist)
            height = a*math.cos(v)*math.sin(twist)+b*math.sin(v)*math.cos(twist)
            vertices.append(((major+radial)*math.cos(u),
                             (major+radial)*math.sin(u),
                             height+.17*math.sin(3*u)))
    for i in range(nu):
        for j in range(nv):
            faces.append((i*nv+j, ((i+1)%nu)*nv+j,
                          ((i+1)%nu)*nv+(j+1)%nv, i*nv+(j+1)%nv))
    membrane = mesh('Twisted toroidal membrane', vertices, faces, pearl, sculpture)
    modifier = membrane.modifiers.new('Continuous polished surface', 'SUBSURF')
    modifier.levels = 1
    modifier.render_levels = 1

    # DNA is translated into an abstract luminous spine; no research labels.
    molecule = bpy.data.objects.new('Molecular spine', None)
    bpy.context.collection.objects.link(molecule)
    molecule.parent = root
    molecule.rotation_euler = (math.radians(5), math.radians(-22), math.radians(3))
    for side, mat in [(0, ice), (1, lilac)]:
        points=[]
        for j in range(241):
            t = j/240
            angle=TAU*2.3*t+side*math.pi
            points.append((-2.1+4.2*t, .3*math.cos(angle), .3*math.sin(angle)))
        polycurve('Luminous helix '+str(side+1), points, .029, mat, molecule)
    for j in range(27):
        t = j/26
        angle=TAU*2.3*t
        x=-2.1+4.2*t
        a=(x, .3*math.cos(angle), .3*math.sin(angle))
        b=(x, -.3*math.cos(angle), -.3*math.sin(angle))
        polycurve('Molecular rung '+str(j), [a,b], .014, titanium, molecule)
        sphere('Ice atom '+str(j), a, .045 if j%5 else .067, ice, molecule)
        sphere('Lilac atom '+str(j), b, .045 if j%5 else .067, lilac if j%7 else warm, molecule)

    # A fine halo is a reflective physical tube, rather than a flat graphic ring.
    points=[(2.62*math.cos(TAU*i/280), 2.62*math.sin(TAU*i/280), 0)
            for i in range(281)]
    halo=polycurve('Orbital platinum halo', points, .008, titanium, root)
    halo.rotation_euler=(math.radians(68),math.radians(12),math.radians(28))
    rng=random.Random(127)
    particles=[]
    for i in range(21):
        angle=rng.random()*TAU
        radius=rng.uniform(2.4, 3.25)
        point=(radius*math.cos(angle),rng.uniform(-1.0, 1.0),radius*.62*math.sin(angle))
        obj=sphere('Drifting microstructure '+str(i),point,rng.uniform(.012,.035),
                   ice if i%3==0 else titanium)
        particles.append((obj,Vector(point),rng.random()*TAU,rng.uniform(.035,.11)))

    light('Softbox / cool pearl',(-4,-6,8),(.68,.87,1),1800,5)
    light('Violet strip / rim',(4,1,4),(.45,.25,1),1800,4,shape='RECTANGLE',size_y=1)
    light('Cyan strip / rim',(-4,3,1),(.08,.8,1),1900,4,shape='RECTANGLE',size_y=.6)
    light('Warm studio / edge',(4,-2,-.1),(1,.55,.32),550,3,shape='RECTANGLE',size_y=.4)
    light('White top / broad',(0,0,8),(.9,.94,1),1200,3)

    bpy.ops.object.camera_add(location=(5,-11,6))
    camera=bpy.context.object
    camera.name='Orthographic gallery camera'
    target=Vector((0,0,-.35))
    aim(camera,target)
    camera.data.type='ORTHO'
    camera.data.ortho_scale=9.4
    camera.data.lens=60
    scene.camera=camera
    quat=camera.rotation_euler.to_quaternion()
    right,up=quat@Vector((1,0,0)),quat@Vector((0,1,0))
    toward=quat@Vector((0,0,1))
    text= bpy.data.curves.new('nvxraM wordmark','FONT')
    text.body='nvxraM'
    text.align_x='CENTER'
    text.align_y='CENTER'
    text.size=.37
    text.space_character=1.13
    font=Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if font.exists(): text.font=bpy.data.fonts.load(str(font))
    label=bpy.data.objects.new('nvxraM',text)
    bpy.context.collection.objects.link(label)
    label.location=target+up*(-1.92)+toward*2
    label.rotation_euler=camera.rotation_euler
    label.data.materials.append(material('Quiet white wordmark',(.7,.77,.85),0,.6,.7))

    scene.use_nodes = True
    nodes=scene.node_tree.nodes
    nodes.clear()
    render=nodes.new('CompositorNodeRLayers')
    glare=nodes.new('CompositorNodeGlare')
    glare.glare_type='FOG_GLOW'
    glare.quality='HIGH'
    glare.threshold=1.6
    glare.size=7
    glare.mix=-.91
    output=nodes.new('CompositorNodeComposite')
    scene.node_tree.links.new(render.outputs['Image'],glare.inputs['Image'])
    scene.node_tree.links.new(glare.outputs['Image'],output.inputs['Image'])
    return scene,root,molecule,particles


def main():
    argsv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output-dir',type=Path,default=Path('/tmp/nvxram-v2-frames'))
    p.add_argument('--frames',default='all',help='Comma-separated zero-based indices, or all')
    p.add_argument('--frame-count',type=int,default=80)
    p.add_argument('--samples',type=int,default=8)
    p.add_argument('--percent',type=int,default=100)
    p.add_argument('--threads',type=int,default=4)
    p.add_argument('--engine',choices=['CYCLES','BLENDER_EEVEE_NEXT'],default='BLENDER_EEVEE_NEXT')
    args=p.parse_args(argsv)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    scene,root,molecule,particles=build(args)
    frames=range(args.frame_count) if args.frames=='all' else [int(x) for x in args.frames.split(',')]
    for frame in frames:
        phase=TAU*frame/args.frame_count
        root.rotation_euler=(.045*math.sin(phase),.09*math.sin(phase+.4),.10*math.cos(phase))
        root.location.z=.06*math.sin(phase)
        molecule.rotation_euler.x=.11*math.sin(phase)+math.radians(5)
        for obj,origin,offset,amplitude in particles:
            obj.location=origin+Vector((amplitude*math.sin(phase+offset),
                                      amplitude*math.cos(phase+offset),
                                      amplitude*.6*math.sin(phase+offset)))
        scene.render.filepath=str(args.output_dir/f'frame-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'V2_FRAME_DONE {frame}',flush=True)


if __name__=='__main__':
    main()
