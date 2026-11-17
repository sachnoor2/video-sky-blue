#!/usr/bin/env python3
"""Blender driver: render an absolute frame range from ONE world file, through one camera.

    blender -b scenes/world.blend -P scenes/render.py -- --camera cam-macro --start 0 --end 95

The world file holds the geometry, the lights, the materials and every camera, so two shots cannot
disagree about the light, the palette or the scale. Cycles CPU, PNG, absolute zero-padded numbering.
"""
import argparse, os, sys

import bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--camera", required=True)
ap.add_argument("--start", type=int, required=True)
ap.add_argument("--end", type=int, required=True)
ap.add_argument("--out", default="public/out")
ap.add_argument("--samples", type=int, default=32)
a = ap.parse_args(argv)

scene = bpy.context.scene

cam = bpy.data.objects.get(a.camera)
if cam is None:
    sys.exit(f"camera {a.camera!r} not found in this world - add it to the world file, do not invent a new angle")
scene.camera = cam

scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = a.samples
scene.cycles.use_denoising = True
scene.render.motion_blur_shutter = 0.5
scene.render.fps = 30
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = os.path.join(a.out, "frame_######")
scene.frame_start = a.start
scene.frame_end = a.end

bpy.ops.render.render(animation=True)
print(f"rendered {a.start}-{a.end} via {a.camera} into {a.out}")
