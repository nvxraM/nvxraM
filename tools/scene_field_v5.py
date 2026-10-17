#!/usr/bin/env python3
"""Original pelagic macro: living radial filaments in an indigo abyss.

Blender 4.3+ writes AgX RGB PNGs for external denoising and delivery encoding.
The camera, optical defocus, shading, geometry and motion are procedural.
No external assets, floor, pedestal, metal, transmission or world volume.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


TAU = math.tau
STEMS, POINTS = 15, 52
FANS = [(-.102, .016, -.024, .042, .045),
        (-.035, -.002, -.026, .048, .049),
        (.037, .005, -.026, .044, .047),
        (.108, .023, -.024, .039, .044)]


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def material(name, color, glow=0, roughness=.32):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    shader = result.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Coat Weight'].default_value = .3
    shader.inputs['Coat Roughness'].default_value = .17
    shader.inputs['Emission Color'].default_value = (*color, 1)
    shader.inputs['Emission Strength'].default_value = glow
    # These tiny luminous surfaces are visible biological structures, not
    # hundreds of indirect area lights competing with the deliberate rim.
    if hasattr(result.cycles, 'emission_sampling'):
        result.cycles.emission_sampling = 'NONE'
    return result


def filament_material():
    result = material('Living cyan tissue / luminous distal filaments', (.04, .4, .4), 1.15)
    nodes, links = result.node_tree.nodes, result.node_tree.links
    shader = nodes.get('Principled BSDF')
    geometry = nodes.new('ShaderNodeNewGeometry')
    components = nodes.new('ShaderNodeSeparateXYZ')
    links.new(geometry.outputs['Position'], components.inputs[0])
    height = nodes.new('ShaderNodeMapRange')
    height.inputs['From Min'].default_value = -.027
    height.inputs['From Max'].default_value = .021
    height.clamp = True
    links.new(components.outputs['Z'], height.inputs['Value'])
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0
    ramp.color_ramp.elements[0].color = (.004, .018, .052, 1)
    ramp.color_ramp.elements[1].position = 1
    ramp.color_ramp.elements[1].color = (.23, .75, .63, 1)
    ramp.color_ramp.elements.new(.45).color = (.018, .11, .16, 1)
    ramp.color_ramp.elements.new(.77).color = (.065, .48, .47, 1)
    links.new(height.outputs['Result'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    links.new(ramp.outputs['Color'], shader.inputs['Emission Color'])
    return result


def filament_point(fan, stem, t, phase):
    x, y, z, length, spread = FANS[fan]
    seed = fan * 1.7 + stem * 2.399963229728653
    angle = -1.12 + 2.24 * stem / (STEMS - 1) + .065 * math.sin(seed)
    sway = math.sin(phase + seed)
    # A soft curved fan opens into the water. The distal half sways while the
    # thicker proximal tissue stays coherent and tapered, rather than rigid.
    xx = x + spread * math.sin(angle) * t ** 1.25
    xx += .007 * math.sin(seed + .7) * math.sin(t * math.pi) * t
    xx += .0026 * math.sin(phase + seed + t * 1.4) * t * t
    yy = y + .009 * math.sin(angle * 1.3) * t + .004 * t * t
    yy += .008 * math.sin(seed * .73) * t ** 1.5
    yy += .0015 * math.cos(phase + seed) * t * t
    variation = .92 + .1 * math.sin(seed * 1.3)
    zz = z + length * variation * (.35 + .65 * math.cos(angle)) * t
    zz += .0012 * sway * t * t
    return xx, yy, zz


def filament(fan, stem, shading):
    data = bpy.data.curves.new(f'Fan {fan + 1} / filament {stem + 1}', 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 1
    data.bevel_depth = .00039
    data.bevel_resolution = 2
    data.resolution_u = 1
    data.use_fill_caps = True
    spline = data.splines.new('POLY')
    spline.points.add(POINTS - 1)
    for index, point in enumerate(spline.points):
        t = index / (POINTS - 1)
        point.co = (*filament_point(fan, stem, t, 0), 1)
        point.radius = .4 + .65 * (1 - t) ** .7 + .06 * math.sin(t * 18 * math.pi + stem)
    obj = bpy.data.objects.new(data.name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(shading)
    return obj


def cell(name, location, radius, shading, aspect=(1, 1, 1)):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = aspect
    obj.data.materials.append(shading)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def softbox(name, location, color, energy, width, target):
    data = bpy.data.lights.new(name, 'AREA')
    data.shape = 'RECTANGLE'
    data.size, data.size_y = width, width * .4
    data.color, data.energy = color, energy
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    aim(obj, target)
    return obj


def backdrop():
    # A softly varying, distant emissive field supplies a photographic ink-blue
    # background without an expensive fog or a visible artificial horizon.
    shading = material('Distant indigo water', (.004, .009, .032), .65)
    nodes, links = shading.node_tree.nodes, shading.node_tree.links
    shader = nodes.get('Principled BSDF')
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3
    noise.inputs['Detail'].default_value = 1
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (.002, .005, .018, 1)
    ramp.color_ramp.elements[1].color = (.008, .022, .064, 1)
    links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    links.new(ramp.outputs['Color'], shader.inputs['Emission Color'])
    bpy.ops.mesh.primitive_plane_add(size=4, location=(0, .5, .1),
                                    rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.name = 'Distant water / no floor or horizon'
    obj.data.materials.append(shading)


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
    scene.cycles.seed = 503
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.transmission_bounces = 0
    scene.render.resolution_x, scene.render.resolution_y = 1600, 220
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
    background.inputs['Color'].default_value = (.008, .02, .065, 1)
    background.inputs['Strength'].default_value = .1
    scene.use_nodes = False
    backdrop()

    living = filament_material()
    cyan = material('Cyan photocyte / luminous tissue', (.17, .67, .59), 1.4)
    violet = material('Violet plankton', (.24, .13, .52), .7)
    peach = material('Peach plankton', (.72, .29, .15), .9)
    filaments, tips = [], []
    for fan in range(len(FANS)):
        for stem in range(STEMS):
            filaments.append((filament(fan, stem, living), fan, stem))
            tip = cell(f'Distal photocyte {fan}-{stem}', filament_point(fan, stem, 1, 0),
                       .0004, cyan if (fan + stem) % 9 else peach,
                       aspect=(.7, .7, 1.5))
            tips.append((tip, fan, stem))
    particles = []
    for index in range(17):
        seed = index * 2.399963229728653
        point = Vector((-.14 + .28 * index / 16,
                        -.045 + .095 * ((index * 7 % 17) / 16),
                        -.011 + .034 * ((index * 5 % 17) / 16)))
        radius = .0003 + (index % 4) * .00016
        obj = cell(f'Suspended plankton {index}', point, radius,
                   peach if index % 6 == 0 else violet if index % 4 == 0 else cyan)
        particles.append((obj, point, seed))

    softbox('Cool pelagic rim', (-.14, .12, .17), (.28, .72, 1), 2.5, .25, (0, 0, 0))
    softbox('Restrained warm reflected light', (.2, -.08, .14), (1, .53, .32), .24, .22, (0, 0, 0))
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(-.025, .003, -.001))
    focus = bpy.context.object
    focus.name = 'Macro focus inside the living fan'
    bpy.ops.object.camera_add(location=(0, -.73, .2))
    camera = bpy.context.object
    camera.name = '85 mm pelagic macro / optical bokeh'
    camera.data.type = 'PERSP'
    camera.data.lens = 85
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = focus
    camera.data.dof.aperture_fstop = 1.8
    camera.data.dof.aperture_blades = 9
    camera.data.clip_start = .005
    camera.data.clip_end = 10
    aim(camera, (0, .008, .011))
    scene.camera = camera
    return scene, filaments, tips, particles, living


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('/tmp/nvxram-v5-field-frames'))
    parser.add_argument('--frame-count', type=int, default=60)
    parser.add_argument('--frames', default='all', help='Comma-separated zero-based indices, or all')
    parser.add_argument('--samples', type=int, default=20)
    parser.add_argument('--percent', type=int, default=100)
    parser.add_argument('--threads', type=int, default=1)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scene, filaments, tips, particles, living = build(args)
    frames = range(args.frame_count) if args.frames == 'all' else [int(value) for value in args.frames.split(',')]
    for frame in frames:
        phase = TAU * (frame % args.frame_count) / args.frame_count
        for obj, fan, stem in filaments:
            for index, point in enumerate(obj.data.splines[0].points):
                point.co = (*filament_point(fan, stem, index / (POINTS - 1), phase), 1)
        for obj, fan, stem in tips:
            obj.location = filament_point(fan, stem, 1, phase)
        for obj, origin, seed in particles:
            obj.location = origin + Vector((.0012 * math.sin(phase + seed),
                                            .001 * math.cos(phase + seed),
                                            .0008 * math.sin(phase + seed)))
        living.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value = 1.15 * (1 + .045 * math.cos(phase))
        scene.render.filepath = str(args.output_dir / f'frame-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'V5_FIELD_FRAME_DONE {frame}', flush=True)


if __name__ == '__main__':
    main()
