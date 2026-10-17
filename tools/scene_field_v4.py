#!/usr/bin/env python3
"""Procedural, physically lit titanium material study for the profile footer.

Blender 4.3+ renders AgX RGB PNG frames. Denoising and GIF encoding are external.
All geometry, shading, lighting and motion are original and local. No text,
downloaded assets, volumetrics, emission or transmission are used.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


TAU = math.tau


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def material(name, color, metallic=0, roughness=.3, coat=0):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Coat Weight'].default_value = coat
    shader.inputs['Coat Roughness'].default_value = .16
    return result, shader


def stage_material():
    result, shader = material('Fine honed obsidian', (.008, .012, .015), .12, .29, .16)
    nodes, links = result.node_tree.nodes, result.node_tree.links
    coordinates = nodes.new('ShaderNodeTexCoord')
    texture = nodes.new('ShaderNodeTexNoise')
    texture.inputs['Scale'].default_value = 2100
    texture.inputs['Detail'].default_value = 2
    texture.inputs['Roughness'].default_value = .62
    links.new(coordinates.outputs['Object'], texture.inputs['Vector'])
    roughness = nodes.new('ShaderNodeMapRange')
    roughness.inputs['From Min'].default_value = 0
    roughness.inputs['From Max'].default_value = 1
    roughness.inputs['To Min'].default_value = .25
    roughness.inputs['To Max'].default_value = .34
    links.new(texture.outputs['Fac'], roughness.inputs['Value'])
    links.new(roughness.outputs['Result'], shader.inputs['Roughness'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .09
    bump.inputs['Distance'].default_value = .000025
    links.new(texture.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return result


def satin_material():
    result, shader = material('Satin champagne titanium', (.63, .58, .49), .94, .23, .2)
    shader.inputs['Anisotropic'].default_value = .34
    nodes, links = result.node_tree.nodes, result.node_tree.links
    texture = nodes.new('ShaderNodeTexNoise')
    texture.inputs['Scale'].default_value = 2450
    texture.inputs['Detail'].default_value = 2
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .045
    bump.inputs['Distance'].default_value = .000007
    links.new(texture.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return result


def ribbon(name, foot, height, bend, yaw, front, backing):
    """A genuinely solid, curved and twisted strip, embedded into the floor."""
    vertices, faces, slots = [], [], []
    steps, across = 64, 8
    thickness = .0009
    for layer in (-1, 1):
        for index in range(steps + 1):
            t = index / steps
            centre = Vector((bend * (1 - math.cos(math.pi * t)),
                             .0034 * math.sin(math.pi * t),
                             height * math.sin(math.pi * .48 * t)))
            tangent = Vector((bend * math.pi * math.sin(math.pi * t),
                              .0034 * math.pi * math.cos(math.pi * t),
                              height * math.pi * .48 * math.cos(math.pi * .48 * t))).normalized()
            width_direction = Vector((tangent.z, 0, -tangent.x)).normalized()
            twist = -.3 + .95 * t
            width_direction = Matrix.Rotation(twist, 3, tangent) @ width_direction
            normal = tangent.cross(width_direction).normalized()
            width = .0092 * (.8 + .2 * math.sin(math.pi * t))
            for cross in range(across + 1):
                v = cross / across - .5
                # A slight real transverse camber produces broad, changing
                # reflections instead of a flat graphic coloured face.
                camber = normal * (v * v * .0014)
                point = centre + width_direction * (v * width) + camber
                point += normal * (layer * thickness / 2)
                vertices.append(tuple(point))
    rows = (steps + 1) * (across + 1)
    for layer_index in (0, 1):
        offset = layer_index * rows
        for index in range(steps):
            for cross in range(across):
                a = offset + index * (across + 1) + cross
                face = (a, a + 1, a + across + 2, a + across + 1)
                faces.append(tuple(reversed(face)) if layer_index == 1 else face)
                slots.append(layer_index)
    for index in range(steps):
        for cross in (0, across):
            a = index * (across + 1) + cross
            b = a + across + 1
            face = (a, b, rows + b, rows + a)
            faces.append(tuple(reversed(face)) if cross == across else face)
            slots.append(0)
    for index in (0, steps):
        for cross in range(across):
            a = index * (across + 1) + cross
            face = (a, a + 1, rows + a + 1, rows + a)
            faces.append(tuple(reversed(face)) if index == 0 else face)
            slots.append(0)
    mesh = bpy.data.meshes.new(name + ' / solid curved geometry')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(front)
    obj.data.materials.append(backing)
    for polygon, slot in zip(obj.data.polygons, slots):
        polygon.use_smooth = True
        polygon.material_index = slot
    obj.location = (foot[0], foot[1], -.0013)
    obj.rotation_euler.z = yaw
    bevel = obj.modifiers.new('Machined soft titanium edges', 'BEVEL')
    bevel.width = .00016
    bevel.segments = 3
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = .5
    return obj


def bead(name, x, y, radius, shading):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=radius,
                                       location=(x, y, radius))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(shading)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def softbox(name, position, color, energy, width, height, target):
    data = bpy.data.lights.new(name, 'AREA')
    data.shape = 'RECTANGLE'
    data.size, data.size_y = width, height
    data.energy, data.color = energy, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = position
    aim(obj, target)
    return obj


def build(args):
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 401
    scene.cycles.max_bounces = 5
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 0
    scene.render.resolution_x, scene.render.resolution_y = 1600, 240
    scene.render.resolution_percentage = args.percent
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'
    scene.render.image_settings.color_depth = '8'
    scene.render.film_transparent = False
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = args.threads
    scene.render.use_persistent_data = True
    scene.render.fps = 20
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (.18, .21, .24, 1)
    background.inputs['Strength'].default_value = .14
    scene.use_nodes = False

    bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, 0))
    floor = bpy.context.object
    floor.name = 'Honed obsidian / real cast shadows and reflections'
    floor.data.materials.append(stage_material())
    titanium = satin_material()
    teal, _ = material('Deep teal enamel underface', (.012, .075, .069), .12, .24, .65)
    amber, _ = material('Dark amber enamel underface', (.26, .092, .022), .24, .22, .7)
    porcelain, _ = material('Warm amber porcelain', (.64, .32, .105), .02, .22, .65)
    pearl, _ = material('Warm pearl microbeads', (.52, .49, .43), .22, .24, .45)
    ribbons = []
    for name, foot, height, bend, yaw, backing in [
            ('Left titanium curl', (-.063, .002), .027, .007, -.23, teal),
            ('Centre titanium curl', (-.008, .004), .035, -.008, .11, amber),
            ('Right titanium curl', (.053, .004), .025, .008, -.21, teal)]:
        obj = ribbon(name, foot, height, bend, yaw, titanium, backing)
        ribbons.append((obj, yaw))
    bead('Single warm amber porcelain bead', .024, -.001, .0074, porcelain)
    bead('Near pearl / optical bokeh', -.108, -.022, .0048, pearl)
    bead('Near amber / optical bokeh', .111, -.026, .0037, porcelain)
    bead('Far pearl / optical bokeh', -.095, .033, .0032, pearl)
    bead('Far pearl / small bokeh', .099, .039, .0027, pearl)

    softbox('Dominant warm broad softbox', (-.23, -.28, .38), (1, .9, .77),
            6, .28, .2, (0, 0, .012))
    softbox('Weak cool reflected fill', (.19, .13, .22), (.67, .78, 1),
            .75, .22, .17, (0, 0, .012))
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(-.006, .004, .016))
    focus = bpy.context.object
    focus.name = 'Optical focus / centre titanium slice'
    bpy.ops.object.camera_add(location=(0, -.71, .36))
    camera = bpy.context.object
    camera.name = 'Real 85 mm macro perspective / shallow optical DOF'
    camera.data.type = 'PERSP'
    camera.data.lens = 85
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = focus
    camera.data.dof.aperture_fstop = 1.8
    camera.data.dof.aperture_blades = 9
    camera.data.clip_start = .005
    camera.data.clip_end = 10
    aim(camera, (0, .003, .014))
    scene.camera = camera
    return scene, ribbons


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('/tmp/nvxram-v4-field-frames'))
    parser.add_argument('--frame-count', type=int, default=60)
    parser.add_argument('--frames', default='all', help='Comma-separated zero-based indices, or all')
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--percent', type=int, default=100)
    parser.add_argument('--threads', type=int, default=3)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scene, ribbons = build(args)
    frames = range(args.frame_count) if args.frames == 'all' else [int(value) for value in args.frames.split(',')]
    for frame in frames:
        phase = TAU * (frame % args.frame_count) / args.frame_count
        for index, (obj, yaw) in enumerate(ribbons):
            offset = index * .7
            obj.rotation_euler.x = .018 * math.sin(phase + offset)
            obj.rotation_euler.y = .026 * math.sin(phase + offset)
            obj.rotation_euler.z = yaw + .02 * math.cos(phase + offset)
        scene.render.filepath = str(args.output_dir / f'frame-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'V4_FIELD_FRAME_DONE {frame}', flush=True)


if __name__ == '__main__':
    main()
