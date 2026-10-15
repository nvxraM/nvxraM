#!/usr/bin/env python3
"""A physically lit, procedural macro still life for the profile footer.

Run with Blender 4.3+: blender -b --python tools/scene_field_v3.py -- --help.
Cycles writes ordinary AgX RGB PNGs. Denoising and delivery encoding are external.
No external models, imagery, fonts, text or personal information are used.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


TAU = math.tau
SCALE = .1  # Physical macro scale: the largest grounded pearl is 36 mm across.


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def principled(name, color, metallic, roughness):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    return material, shader


def stone_material():
    material, shader = principled('Fine-grained neutral basalt', (.014, .015, .016), 0, .79)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    coordinates = nodes.new('ShaderNodeTexCoord')
    grain = nodes.new('ShaderNodeTexNoise')
    grain.inputs['Scale'].default_value = 1450
    grain.inputs['Detail'].default_value = 3
    grain.inputs['Roughness'].default_value = .72
    links.new(coordinates.outputs['Object'], grain.inputs['Vector'])
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = .1
    ramp.color_ramp.elements[0].color = (.006, .0065, .007, 1)
    ramp.color_ramp.elements[1].position = .9
    ramp.color_ramp.elements[1].color = (.024, .025, .026, 1)
    links.new(grain.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], shader.inputs['Base Color'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .24
    bump.inputs['Distance'].default_value = .00012
    links.new(grain.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return material


def pearl_material():
    material, shader = principled('Warm natural pearl with subtle nacre', (.67, .65, .6), .22, .22)
    shader.inputs['Coat Weight'].default_value = .75
    shader.inputs['Coat Roughness'].default_value = .14
    shader.inputs['IOR'].default_value = 1.52
    shader.inputs['Thin Film Thickness'].default_value = 260
    shader.inputs['Thin Film IOR'].default_value = 1.34
    nodes, links = material.node_tree.nodes, material.node_tree.links
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 175
    noise.inputs['Detail'].default_value = 2
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .08
    bump.inputs['Distance'].default_value = .000025
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], shader.inputs['Normal'])
    return material


def groove_height(x, y):
    """Actual shallow carved channels, rather than a painted line or fake shadow."""
    axis = .16 * math.sin(1.55 * x) + .035 * x
    h = 0
    for offset, depth, width in ((-.19, .018, .025), (.16, .012, .021)):
        h -= depth * math.exp(-((y - axis - offset) / width) ** 2)
    return h


def make_floor(material):
    # Mesh resolution is concentrated around the visible field. The resulting
    # surface normals and ray-traced channel shadows remain geometrically real.
    vertices, faces = [], []
    nx, ny = 320, 150
    for iy in range(ny + 1):
        y = -1.6 + 3.2 * iy / ny
        for ix in range(nx + 1):
            x = -5 + 10 * ix / nx
            vertices.append((x * SCALE, y * SCALE, groove_height(x, y) * SCALE))
    for iy in range(ny):
        for ix in range(nx):
            corner = iy * (nx + 1) + ix
            faces.append((corner, corner + 1, corner + nx + 2, corner + nx + 1))
    data = bpy.data.meshes.new('Carved stone surface geometry')
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new('Dark stone / contact and cast shadow receiver', data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    for face in data.polygons:
        face.use_smooth = True
    return obj


def bead(name, x, y, radius, material, hovering=False):
    # Grounded spheres sit on uncarved shoulders, never on top of a depression.
    # The sole hovering pearl is deliberately separated from its cast shadow.
    z = radius if not hovering else .31
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32,
                                       radius=radius * SCALE,
                                       location=(x * SCALE, y * SCALE, z * SCALE))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    return obj


def softbox(name, location, color, energy, size, target, size_y):
    data = bpy.data.lights.new(name, 'AREA')
    data.shape = 'RECTANGLE'
    data.energy = energy
    data.color = color
    data.size, data.size_y = size, size_y
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
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
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .08
    scene.cycles.adaptive_min_samples = min(4, args.samples)
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 3
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 3
    scene.cycles.use_animated_seed = False
    scene.cycles.seed = 173
    scene.render.resolution_x, scene.render.resolution_y = 1600, 260
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
    world = scene.world.node_tree.nodes.get('Background')
    world.inputs['Color'].default_value = (.19, .21, .23, 1)
    world.inputs['Strength'].default_value = .16
    scene.use_nodes = False

    make_floor(stone_material())
    pearl = pearl_material()
    mercury, shader = principled('Polished mercury / neutral reflection', (.78, .79, .8), 1, .105)
    shader.inputs['Coat Weight'].default_value = .35
    shader.inputs['Coat Roughness'].default_value = .1
    # Three primary, focused grounded beads rest between the carved channels.
    bead('Sharp pearl / left', -.45, -.015, .14, pearl)
    bead('Sharp mercury / centre', .05, .045, .18, mercury)
    bead('Sharp pearl / right', .58, .065, .12, pearl)
    floating = bead('Hovering pearl / single surreal departure', -.1, .23, .082, pearl, True)
    # Front and rear droplets are genuinely defocused by the macro lens.
    for name, x, y, radius, material in [
            ('Near mercury / left bokeh', -1.72, -.45, .115, mercury),
            ('Near pearl / right bokeh', 1.45, -.43, .135, pearl),
            ('Near microdroplet', .92, -.51, .052, mercury),
            ('Far pearl / left', -1.35, .59, .066, pearl),
            ('Far mercury / right', 1.07, .65, .085, mercury),
            ('Far microdroplet', 1.83, .52, .042, mercury),
            ('Middle pearl', -1.02, .22, .058, pearl)]:
        bead(name, x, y, radius, material)

    softbox('Dominant warm studio softbox', (-.34, -.26, .55),
            (1, .94, .85), 8, .33, (0, 0, 0), .24)
    softbox('Weak cool reflection fill', (.3, .2, .32),
            (.77, .86, 1), .45, .3, (0, 0, .015), .22)

    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(.005, .0045, .018))
    focus = bpy.context.object
    focus.name = 'Optical focus at middle grounded bead'
    bpy.ops.object.camera_add(location=(0, -1.05, .58))
    camera = bpy.context.object
    camera.name = '85 mm macro lens / physical depth of field'
    camera.data.type = 'PERSP'
    camera.data.lens = 85
    camera.data.sensor_width = 36
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = focus
    camera.data.dof.aperture_fstop = 1.2
    camera.data.dof.aperture_blades = 9
    camera.data.dof.aperture_ratio = 1
    camera.data.clip_start = .01
    camera.data.clip_end = 25
    aim(camera, (0, .008, .016))
    scene.camera = camera
    return scene, floating, focus


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('/tmp/nvxram-v3-field-frames'))
    parser.add_argument('--frame-count', type=int, default=60)
    parser.add_argument('--frames', default='all', help='Comma-separated zero-based indices, or all')
    parser.add_argument('--samples', type=int, default=32)
    parser.add_argument('--percent', type=int, default=100)
    parser.add_argument('--threads', type=int, default=3)
    args = parser.parse_args(argv)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scene, floating, focus = build(args)
    frames = range(args.frame_count) if args.frames == 'all' else [int(value) for value in args.frames.split(',')]
    for frame in frames:
        phase = TAU * (frame % args.frame_count) / args.frame_count
        floating.location = (-.01 + .0008 * math.sin(phase),
                             .023 + .0005 * math.sin(phase),
                             .031 + .0022 * math.sin(phase))
        focus.location.z = .018 + .0006 * math.sin(phase)
        scene.render.filepath = str(args.output_dir / f'frame-{frame:04d}.png')
        bpy.ops.render.render(write_still=True)
        print(f'V3_FIELD_FRAME_DONE {frame}', flush=True)


if __name__ == '__main__':
    main()
