#!/usr/bin/env python3
"""Build a synthetic WORLD file so the pipeline can be proven before any art exists.

    blender -b -P scenes/make_test_scene.py -- --out scenes/world.blend --frames 90

One geometry set, one light rig, three cameras (wide / action / macro) - the same shape every real
video uses. Renders in seconds at low samples.
"""
import argparse, math, sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="scenes/world.blend")
ap.add_argument("--frames", type=int, default=90)
a = ap.parse_args(argv)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# --- geometry (built once, shared by every shot)
bpy.ops.mesh.primitive_cube_add(size=1.4, location=(0, 0, 0))
cube = bpy.context.object
cube.name = "Subject"
cube.rotation_mode = "XYZ"
cube.keyframe_insert("rotation_euler", frame=1)
cube.rotation_euler = (0.4, 0.6, 2.2)
cube.keyframe_insert("rotation_euler", frame=a.frames)

bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, -1.2))

# --- one key light, one direction, one temperature
bpy.ops.object.light_add(type="AREA", location=(2.5, -3, 4))
light = bpy.context.object
light.data.energy = 700
light.data.keyframe_insert("energy", frame=1)
light.data.energy = 950
light.data.keyframe_insert("energy", frame=max(2, a.frames // 2))
light.data.energy = 700
light.data.keyframe_insert("energy", frame=a.frames)

# --- the camera set: a grammar, not a random draw
CAMS = {
    "cam-wide":   ((0.0, -7.5, 2.2), (math.radians(78), 0, 0)),
    "cam-action": ((0.0, -4.2, 1.2), (math.radians(84), 0, 0)),
    "cam-macro":  ((0.9, -1.9, 0.55), (math.radians(88), 0, math.radians(22))),
}
for name, (loc, rot) in CAMS.items():
    bpy.ops.object.camera_add(location=loc, rotation=rot)
    cam = bpy.context.object
    cam.name = name
    cam.data.lens = 50

scene.camera = bpy.data.objects["cam-action"]

# --- the push-in lives in the world, so every shot inherits it
act = bpy.data.objects["cam-action"]
act.keyframe_insert("location", frame=1)
act.location = (0.0, -3.2, 1.0)
act.keyframe_insert("location", frame=a.frames)

scene.frame_start = 1
scene.frame_end = a.frames
scene.render.resolution_x = 720
scene.render.resolution_y = 1280
scene.render.fps = 30
scene.render.engine = "CYCLES"

bpy.ops.wm.save_as_mainfile(filepath=a.out)
print(f"wrote {a.out} ({a.frames} frames, cameras: {', '.join(CAMS)})")
