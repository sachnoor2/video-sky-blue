#!/usr/bin/env python3
"""Rigify + automatic weights, headless.

    blender -b character.blend -P scenes/rig.py

Automatic weights are a starting point: fix armpits, crotch, elbow insides and the jaw seam by hand,
or the character tears open on the first arm raise.
"""
import bpy

bpy.ops.preferences.addon_enable(module="rigify")
bpy.ops.object.armature_human_metarig_add()
bpy.ops.object.mode_set(mode="POSE")
bpy.ops.pose.rigify_generate()

arm = bpy.data.objects["rig"]
mesh = bpy.data.objects["Character"]
bpy.ops.object.select_all(action="DESELECT")
mesh.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type="ARMATURE_AUTO")

bpy.ops.export_scene.gltf(filepath="out/character.glb", export_format="GLB",
                          export_skins=True, export_animations=True, export_yup=True)
print("rigged and exported out/character.glb")
