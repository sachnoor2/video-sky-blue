#!/usr/bin/env python3
"""Build the one world file for "Aasman Neela Kyun Hai?" - every shot renders from it.

    blender -b -P scenes/make_world.py -- --shotlist shotlist.json --out scenes/world.blend

One file holds three sets, one light rig, one palette and the whole camera grammar:

    set-sky    at the origin        ground, sky dome, sun disc, air molecules, a person
    set-beam   at x = +200          a light shaft, one molecule, four scattering fans, two bars
    set-orbit  at x = -200          the Earth, its thin blue shell, stars, an astronaut

The shot list supplies absolute frame ranges; this script keys every camera, every colour change
and every moving object on those exact frames, so the film's motion and its cut points agree.
Nothing here uses random numbers, so two builds of this file are identical.
"""
import argparse
import json
import math
import os
import sys

import bpy

D = math.pi / 180.0

BEAM = 200.0
ORBIT = -200.0

# The camera grammar: one name, many uses. id -> (camera, lens, loc0, rot0, loc1, rot1)
# rot is degrees (x, y, z). rx 90 looks level along +Y; rx < 90 looks down, rx > 90 looks up.
# rz > 0 swings the view toward -X, rz < 0 toward +X.
CAMS = {
    # --- set-sky: person at (0, -9.5, 0), sun high at (0, 70, 62)
    "01-hook":           ("cam-action", 30, (0.0, -13.0, 1.55), (92, 0, 0),   (0.0, -12.4, 1.62), (118, 0, 0)),
    "07-all-directions": ("cam-pov",    24, (0.0, -13.0, 1.70), (106, 0, -7), (0.0, -13.0, 1.70), (109, 0, 7)),
    "08-sunset-path":    ("cam-wide",   32, (0.0, -34.0, 7.0),  (88, 0, 0),   (0.0, -26.0, 5.5),  (90, 0, 0)),
    "09-sunset-red":     ("cam-macro",  40, (0.0, -22.0, 2.0),  (89, 0, 0),   (0.0, -19.0, 1.9),  (89, 0, 0)),
    "13-recap":          ("cam-action", 30, (0.0, -12.6, 1.50), (96, 0, 0),   (0.0, -12.2, 1.56), (116, 0, 0)),
    # --- set-beam: shaft and molecule at (200, -4, z), bars at (199.3 / 200.7, -1)
    "02-white-light":    ("cam-macro",  35, (200.2, -13.0, 3.2), (84, 0, 0),  (200.0, -11.5, 3.0), (85, 0, 0)),
    "03-molecules":      ("cam-macro",  40, (200.3, -11.0, 2.6), (85, 0, 0),  (200.1, -9.8, 2.7),  (84, 0, 0)),
    "04-scatter":        ("cam-action", 30, (200.4, -14.0, 4.0), (84, 0, 0),  (200.2, -12.2, 3.8), (85, 0, 0)),
    "05-number":         ("cam-macro",  32, (200.0, -9.5, 1.20), (87, 0, 0),  (200.2, -8.6, 1.15), (87, 0, 0)),
    "06-violet":         ("cam-macro",  35, (200.4, -11.0, 3.4), (85, 0, 0),  (200.2, -9.8, 3.2),  (86, 0, 0)),
    # --- set-orbit: Earth centre (-200, 12, -12) r 6, astronaut at (-202, -2, 3)
    "10-space":          ("cam-wide",   28, (-200.0, -14.0, 12.0), (46, 0, 0),  (-200.0, -10.0, 10.5), (47, 0, 0)),
    "11-thin-layer":     ("cam-action", 35, (-201.0, -6.0, 6.0),   (60, 0, -6), (-201.0, -4.0, 5.4),   (62, 0, -5)),
    "12-no-air":         ("cam-macro",  50, (-196.0, 0.0, -2.0),   (52, 0, 18), (-195.0, -2.0, -1.4),  (53, 0, 17)),
}


# ----------------------------------------------------------------------------- materials
def set_input(node, names, value):
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return True
    return False


def emission_mat(name, color, strength=2.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    m["emission_node"] = em.name
    return m


def emission_node(m):
    try:
        return m.node_tree.nodes[m["emission_node"]]
    except Exception:
        for n in m.node_tree.nodes:
            if n.type == "EMISSION":
                return n
    return None


def surface_mat(name, color, rough=0.6, metal=0.0, emit=None, emit_strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = m.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = m.node_tree.nodes.new("ShaderNodeOutputMaterial")
        m.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    set_input(bsdf, ["Base Color"], (color[0], color[1], color[2], 1.0))
    set_input(bsdf, ["Roughness"], rough)
    set_input(bsdf, ["Metallic"], metal)
    if emit:
        set_input(bsdf, ["Emission Color", "Emission"], (emit[0], emit[1], emit[2], 1.0))
        set_input(bsdf, ["Emission Strength"], emit_strength)
    return m


def sky_mat(name, top, horizon, strength=1.4, blend=1.0):
    """Gradient emission mixed over transparency.

    Generated Z runs 0 at the bottom of the dome to 1 at the top, so the ramp is the sky's own
    vertical gradient. The Mix Shader's Fac is the dome's opacity: two domes cross-fade between
    the daytime sky and the sunset, which is more robust than animating colour ramp elements.
    """
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.42
    ramp.color_ramp.elements[0].color = (horizon[0], horizon[1], horizon[2], 1.0)
    ramp.color_ramp.elements[1].position = 0.92
    ramp.color_ramp.elements[1].color = (top[0], top[1], top[2], 1.0)
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    tex = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(tex.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = blend
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    m["emission_node"] = em.name
    m["mix_node"] = mix.name
    return m


def mix_of(m):
    try:
        return m.node_tree.nodes[m["mix_node"]]
    except Exception:
        for n in m.node_tree.nodes:
            if n.type == "MIX_SHADER":
                return n
    return None


def limb_mat(name, color, strength=9.0):
    """Transparent face-on, glowing at grazing angles: the thin blue line of an atmosphere."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.62
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.96
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(lw.outputs["Fresnel"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs[0])
    nt.links.new(tr.outputs["BSDF"], mix.inputs[1])
    nt.links.new(em.outputs["Emission"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    m["emission_node"] = em.name
    return m


def earth_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    set_input(bsdf, ["Roughness"], 0.75)
    noise = m.node_tree.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.6
    noise.inputs["Detail"].default_value = 8.0
    ramp = m.node_tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.44
    ramp.color_ramp.elements[0].color = (0.015, 0.10, 0.30, 1)
    ramp.color_ramp.elements[1].position = 0.60
    ramp.color_ramp.elements[1].color = (0.06, 0.26, 0.10, 1)
    m.node_tree.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    m.node_tree.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return m


# ----------------------------------------------------------------------------- geometry
def finish(ob, name, mat, smooth=False):
    ob.name = name
    if mat:
        ob.data.materials.append(mat)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
    return ob


def sphere(name, loc, r, mat, seg=24, ring=12, smooth=True):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=ring)
    return finish(bpy.context.object, name, mat, smooth)


def plane(name, loc, size, mat):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc)
    return finish(bpy.context.object, name, mat)


def cube(name, loc, size, mat, origin_at_base=False):
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
    ob = finish(bpy.context.object, name, mat)
    if origin_at_base:
        from mathutils import Matrix
        ob.data.transform(Matrix.Translation((0, 0, size / 2.0)))
    return ob


def cylinder(name, loc, r, depth, mat, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth,
                                        location=loc, rotation=rot)
    return finish(bpy.context.object, name, mat, True)


def cone(name, loc, r1, r2, depth, mat, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth,
                                    location=loc, rotation=rot)
    return finish(bpy.context.object, name, mat, True)


def label(name, body, loc, size, mat, rot=(0, 0, 0)):
    try:
        bpy.ops.object.text_add(location=loc, rotation=rot)
        ob = bpy.context.object
        ob.name = name
        ob.data.body = body
        ob.data.size = size
        ob.data.align_x = "CENTER"
        ob.data.align_y = "CENTER"
        ob.data.extrude = 0.01
        if mat:
            ob.data.materials.append(mat)
        return ob
    except Exception as e:
        print(f"  label {name} skipped: {e}")
        return None


# ----------------------------------------------------------------------------- animation
def key_loc(ob, f, loc):
    ob.location = loc
    ob.keyframe_insert("location", frame=f)


def key_rot(ob, f, rot):
    ob.rotation_euler = rot
    ob.keyframe_insert("rotation_euler", frame=f)


def key_scale(ob, f, s):
    ob.scale = s
    ob.keyframe_insert("scale", frame=f)


def key_strength(m, f, value):
    node = emission_node(m)
    if node is None:
        return
    node.inputs["Strength"].default_value = value
    node.inputs["Strength"].keyframe_insert("default_value", frame=f)


def key_fac(m, f, value):
    """The dome's opacity: 0 hides it completely, 1 shows it fully."""
    node = mix_of(m)
    if node is None:
        return
    node.inputs[0].default_value = value
    node.inputs[0].keyframe_insert("default_value", frame=f)


def key_color(m, f, color):
    node = emission_node(m)
    if node is None:
        return
    node.inputs["Color"].default_value = (color[0], color[1], color[2], 1.0)
    node.inputs["Color"].keyframe_insert("default_value", frame=f)


def bob(ob, base, f0, f1, amp=0.35, phase=0.0, step=8):
    """Drift an object across one shot's window. Deterministic: phase comes from its index."""
    f = f0
    while f <= f1:
        t = (f - f0) * 0.09 + phase
        key_loc(ob, f, (base[0] + 0.45 * math.sin(t * 0.7),
                        base[1] + 0.30 * math.cos(t * 0.5),
                        base[2] + amp * math.sin(t)))
        f += step
    if (f1 - f0) % step:
        t = (f1 - f0) * 0.09 + phase
        key_loc(ob, f1, (base[0] + 0.45 * math.sin(t * 0.7),
                         base[1] + 0.30 * math.cos(t * 0.5),
                         base[2] + amp * math.sin(t)))


def shot_window(shotlist, sid):
    for s in shotlist["shots"]:
        if s["id"] == sid:
            return int(s["start"]), int(s["end"])
    sys.exit(f"shot {sid!r} missing from the shot list")


# ----------------------------------------------------------------------------- sets
def make_figure(prefix, base, suit, skin):
    """A stylised humanoid out of primitives: reads as a person at any distance, no rig needed."""
    x, y, z = base
    parts = [
        cylinder(f"{prefix}-torso", (x, y, z + 0.92), 0.20, 0.72, suit, verts=16),
        sphere(f"{prefix}-head", (x, y, z + 1.44), 0.145, skin),
        cylinder(f"{prefix}-leg-l", (x - 0.10, y, z + 0.32), 0.075, 0.66, suit, verts=12),
        cylinder(f"{prefix}-leg-r", (x + 0.10, y, z + 0.32), 0.075, 0.66, suit, verts=12),
        cylinder(f"{prefix}-arm-l", (x - 0.27, y, z + 0.95), 0.055, 0.60, suit, verts=12),
        cylinder(f"{prefix}-arm-r", (x + 0.27, y, z + 0.95), 0.055, 0.60, suit, verts=12),
    ]
    return parts


def build_sky(shotlist):
    ground_mat = surface_mat("sky-ground", (0.020, 0.026, 0.034), rough=0.95)
    plane("sky-ground", (0, 0, -0.02), 600, ground_mat)

    # two domes at almost the same radius: the daytime sky, and the sunset sky underneath it.
    # Only one is opaque at a time, cross-faded on the Mix Shader's Fac - a cut-safe colour change.
    day = sky_mat("sky-dome-day", top=(0.075, 0.235, 0.62), horizon=(0.72, 0.85, 0.96),
                  strength=0.85, blend=1.0)
    sphere("sky-dome-day", (0, 0, 0), 120.0, day, seg=64, ring=32)
    dusk = sky_mat("sky-dome-dusk", top=(0.26, 0.09, 0.24), horizon=(1.00, 0.50, 0.18),
                   strength=0.85, blend=0.0)
    sphere("sky-dome-dusk", (0, 0, 0), 119.2, dusk, seg=64, ring=32)

    sun_mat = emission_mat("sky-sun", (1.0, 0.95, 0.82), 2.4)
    sun = sphere("sky-sun", (0, 70, 62), 4.0, sun_mat, seg=24, ring=12)

    mol_mat = emission_mat("sky-molecule", (0.55, 0.78, 1.0), 0.95)
    molecules, bases = [], []
    n = 0
    for i in range(5):
        for j in range(4):
            for k in range(2):
                loc = (-18.0 + i * 9.0, -14.0 + j * 9.0, 5.0 + k * 11.0 + (i % 3) * 1.4)
                molecules.append(sphere(f"sky-mol-{n}", loc, 0.085, mol_mat, seg=10, ring=6))
                bases.append(loc)
                n += 1

    person_mat = surface_mat("sky-person", (0.05, 0.06, 0.08), rough=0.8)
    skin_mat = surface_mat("sky-skin", (0.09, 0.07, 0.06), rough=0.7)
    make_figure("sky-person", (0.0, -9.5, 0.0), person_mat, skin_mat)

    # --- motion, keyed inside each shot's own window
    f0, f1 = shot_window(shotlist, "01-hook")
    for i, m in enumerate(molecules):
        bob(m, bases[i], f0, f1, amp=0.5, phase=i * 0.37)

    f0, f1 = shot_window(shotlist, "07-all-directions")
    for i, m in enumerate(molecules):
        bob(m, bases[i], f0, f1, amp=0.5, phase=i * 0.37)
    key_strength(day, f0, 0.80)
    key_strength(day, f1, 1.15)          # the sky saturates as the scattered light arrives

    # sunset: the sun drops, the long path eats the blue, the dusk dome takes over
    f0, f1 = shot_window(shotlist, "08-sunset-path")
    key_loc(sun, f0, (0, 70, 62))
    key_loc(sun, f1, (0, 70, 3.0))
    key_fac(dusk, f0, 0.0)
    key_fac(dusk, f1, 1.0)
    key_color(sun_mat, f0, (1.0, 0.95, 0.82))
    key_color(sun_mat, f1, (1.0, 0.60, 0.26))
    for i, m in enumerate(molecules):
        bob(m, bases[i], f0, f1, amp=0.25, phase=i * 0.21)

    f0, f1 = shot_window(shotlist, "09-sunset-red")
    key_loc(sun, f0, (0, 70, 3.0))
    key_loc(sun, f1, (0, 70, 2.2))
    key_fac(dusk, f0, 1.0)
    key_fac(dusk, f1, 1.0)
    key_color(sun_mat, f0, (1.0, 0.60, 0.26))
    key_color(sun_mat, f1, (1.0, 0.26, 0.09))
    key_strength(sun_mat, f0, 2.2)
    key_strength(sun_mat, f1, 1.4)

    f0, f1 = shot_window(shotlist, "13-recap")
    key_fac(dusk, f0, 0.0)
    key_fac(dusk, f1, 0.0)
    key_strength(day, f0, 0.90)
    key_strength(day, f1, 1.00)
    for i, m in enumerate(molecules):
        bob(m, bases[i], f0, f1, amp=0.4, phase=i * 0.37)


def build_beam(shotlist):
    x = BEAM
    floor = surface_mat("beam-floor", (0.014, 0.016, 0.022), rough=0.9)
    plane("beam-floor", (x, 0, -0.02), 80, floor)

    beam_mat = emission_mat("beam-shaft", (1.0, 0.97, 0.92), 1.0)
    cylinder("beam-shaft", (x, -4.0, 15.0), 0.18, 30.0, beam_mat, verts=24)

    mol_mat = emission_mat("beam-molecule", (0.88, 0.94, 1.0), 1.2)
    sphere("beam-molecule", (x, -4.0, 5.0), 0.55, mol_mat, seg=24, ring=12)

    # four scattering fans: the wider the cone, the harder that colour is thrown
    spec = {
        "violet": ((0.52, 0.30, 0.95), 2.2, -0.95),
        "blue":   ((0.16, 0.42, 1.00), 1.8, -0.42),
        "green":  ((0.22, 0.82, 0.42), 1.0,  0.26),
        "red":    ((1.00, 0.20, 0.12), 0.35, 0.86),
    }
    fans = {}
    for name, (col, width, tilt) in spec.items():
        m = emission_mat(f"beam-fan-{name}", col, 0.9)
        d = (math.sin(tilt), 0.0, math.cos(tilt))
        depth = 5.0
        ob = cone(f"beam-fan-{name}",
                  (x + d[0] * depth * 0.5, -4.0, 5.0 + d[2] * depth * 0.5),
                  0.10, width, depth, m, rot=(0, tilt, 0))
        fans[name] = (ob, m, tilt, depth)

    # two bars for the number shot: blue 5.9 against red 1.0
    bar_blue_mat = emission_mat("beam-bar-blue", (0.16, 0.42, 1.00), 1.2)
    bar_red_mat = emission_mat("beam-bar-red", (1.00, 0.20, 0.12), 1.2)
    bar_b = cube("beam-bar-blue", (x - 0.7, -1.0, 0.0), 0.30, bar_blue_mat, origin_at_base=True)
    bar_r = cube("beam-bar-red", (x + 0.7, -1.0, 0.0), 0.30, bar_red_mat, origin_at_base=True)

    num_mat = emission_mat("beam-number", (1.0, 0.97, 0.9), 1.6)
    label("beam-number-59", "5.9x", (x - 0.7, -1.1, 2.15), 0.42, num_mat, rot=(90 * D, 0, 0))
    label("beam-number-1", "1x", (x + 0.7, -1.1, 0.62), 0.30, num_mat, rot=(90 * D, 0, 0))

    # 02: the white beam, no fans yet
    f0, f1 = shot_window(shotlist, "02-white-light")
    key_strength(beam_mat, f0, 0.8)
    key_strength(beam_mat, f1, 1.1)
    for name, (ob, m, tilt, depth) in fans.items():
        key_scale(ob, f0, (1, 1, 0.001))
        key_scale(ob, f1, (1, 1, 0.001))
        key_strength(m, f0, 0.0)
        key_strength(m, f1, 0.0)
    for b in (bar_b, bar_r):
        key_scale(b, f0, (1, 1, 0.001))
        key_scale(b, f1, (1, 1, 0.001))

    # 03: molecules appear in the beam path
    f0, f1 = shot_window(shotlist, "03-molecules")
    for i in range(9):
        loc = (x - 0.5 + (i % 3) * 0.5, -4.4 + (i // 3) * 0.35, 2.0 + i * 1.5)
        m = sphere(f"beam-mol-{i}", loc, 0.055, mol_mat, seg=10, ring=6)
        key_scale(m, f0, (0.001, 0.001, 0.001))
        key_scale(m, f0 + 12 + i * 2, (1, 1, 1))
        key_scale(m, f1, (1, 1, 1))
        bob(m, loc, f0, f1, amp=0.18, phase=i * 0.5)

    # 04: the fans open
    f0, f1 = shot_window(shotlist, "04-scatter")
    for name, (ob, m, tilt, depth) in fans.items():
        key_scale(ob, f0, (1, 1, 0.02))
        key_scale(ob, f0 + 10, (1, 1, 0.55))
        key_scale(ob, f1, (1, 1, 1.0))
        key_strength(m, f0, 0.0)
        key_strength(m, f0 + 6, 0.9)
        key_strength(m, f1, 1.0)

    # 05: the bars grow to 5.9 : 1
    f0, f1 = shot_window(shotlist, "05-number")
    key_scale(bar_b, f0, (1, 1, 0.001))
    key_scale(bar_b, f1, (1, 1, 5.9 * 0.30))
    key_scale(bar_r, f0, (1, 1, 0.001))
    key_scale(bar_r, f1, (1, 1, 1.0 * 0.30))
    key_strength(bar_blue_mat, f0, 0.3)
    key_strength(bar_blue_mat, f1, 1.3)
    key_strength(bar_red_mat, f0, 0.3)
    key_strength(bar_red_mat, f1, 1.3)

    # 06: violet is thrown hardest, then dimmed by the eye
    f0, f1 = shot_window(shotlist, "06-violet")
    ob, m, tilt, depth = fans["violet"]
    key_scale(ob, f0, (1, 1, 0.55))
    key_scale(ob, f1, (1, 1, 1.15))
    key_strength(m, f0, 1.2)
    key_strength(m, f1, 0.45)
    for name in ("blue", "green", "red"):
        ob2, m2, _t, _d = fans[name]
        key_strength(m2, f0, 0.9)
        key_strength(m2, f1, 0.35)


def build_orbit(shotlist):
    x = ORBIT
    centre = (x, 12.0, -12.0)

    earth = sphere("orbit-earth", centre, 6.0, earth_mat("orbit-earth-mat"), seg=64, ring=32)
    shell = sphere("orbit-shell", centre, 6.12,
                   limb_mat("orbit-shell-mat", (0.32, 0.58, 1.0), 1.6), seg=64, ring=32)

    sun_mat = emission_mat("orbit-sun", (1.0, 0.98, 0.92), 3.0)
    sphere("orbit-sun", (x - 40, 90, 40), 2.0, sun_mat, seg=16, ring=8)

    star_mat = emission_mat("orbit-star", (0.9, 0.95, 1.0), 1.5)
    for i in range(40):
        a = i * 2.399963
        r = 40.0 + (i % 7) * 4.0
        zz = -10.0 + (i * 37 % 40)
        sphere(f"orbit-star-{i}", (x + r * math.cos(a), 25.0 + r * 0.6 * math.sin(a), zz),
               0.14, star_mat, seg=8, ring=4)

    suit = surface_mat("orbit-suit", (0.80, 0.83, 0.88), rough=0.45,
                       emit=(0.9, 0.92, 0.95), emit_strength=0.18)
    visor = surface_mat("orbit-visor", (0.02, 0.03, 0.05), rough=0.1, metal=0.9)
    base = (x - 2.0, -2.0, 3.0)
    parts = make_figure("orbit-astro", base, suit, suit)
    parts.append(sphere("orbit-helmet", (base[0], base[1], base[2] + 1.44), 0.26, suit))
    parts.append(sphere("orbit-visor", (base[0], base[1] - 0.16, base[2] + 1.44), 0.17, visor))
    bases = [(p.location.x, p.location.y, p.location.z) for p in parts]
    shell_mat = shell.data.materials[0]

    f0, f1 = shot_window(shotlist, "10-space")
    key_rot(earth, f0, (0, 0, 0))
    key_rot(earth, f1, (0, 0, 0.12))
    for i, p in enumerate(parts):
        key_loc(p, f0, bases[i])
        key_loc(p, f1, (bases[i][0] + 0.9, bases[i][1] + 0.5, bases[i][2] - 0.3))
    key_strength(shell_mat, f0, 1.4)
    key_strength(shell_mat, f1, 1.9)

    f0, f1 = shot_window(shotlist, "11-thin-layer")
    key_rot(earth, f0, (0, 0, 0.12))
    key_rot(earth, f1, (0, 0, 0.20))
    for i, p in enumerate(parts):
        key_loc(p, f0, (bases[i][0] + 0.9, bases[i][1] + 0.5, bases[i][2] - 0.3))
        key_loc(p, f1, (bases[i][0] + 1.0, bases[i][1] - 0.6, bases[i][2] + 0.1))
    key_strength(shell_mat, f0, 1.9)
    key_strength(shell_mat, f1, 2.4)

    f0, f1 = shot_window(shotlist, "12-no-air")
    key_scale(shell, f0, (1, 1, 1))
    key_scale(shell, f0 + 12, (1.004, 1.004, 1.004))
    key_scale(shell, f1, (1.0, 1.0, 1.0))
    key_rot(earth, f0, (0, 0, 0.20))
    key_rot(earth, f1, (0, 0, 0.24))
    key_strength(shell_mat, f0, 2.4)
    key_strength(shell_mat, f1, 2.8)


# ----------------------------------------------------------------------------- cameras
def build_cameras(shotlist):
    cams = {}
    for name in ("cam-wide", "cam-action", "cam-macro", "cam-pov"):
        bpy.ops.object.camera_add(location=(0, 0, 0), rotation=(90 * D, 0, 0))
        cam = bpy.context.object
        cam.name = name
        cam.data.lens = 35
        cam.data.clip_start = 0.05
        cam.data.clip_end = 5000.0
        cams[name] = cam

    missing = [s["id"] for s in shotlist["shots"] if s["id"] not in CAMS]
    if missing:
        sys.exit(f"no camera move for: {', '.join(missing)}")

    for s in shotlist["shots"]:
        name, lens, l0, r0, l1, r1 = CAMS[s["id"]]
        if name != s["camera"]:
            sys.exit(f"{s['id']}: shot list says {s['camera']}, camera move says {name}")
        cam = cams[name]
        f0, f1 = int(s["start"]), int(s["end"])
        cam.data.lens = float(lens)
        cam.data.keyframe_insert("lens", frame=f0)
        key_loc(cam, f0, l0)
        key_rot(cam, f0, (r0[0] * D, r0[1] * D, r0[2] * D))
        cam.data.lens = float(lens)
        cam.data.keyframe_insert("lens", frame=f1)
        key_loc(cam, f1, l1)
        key_rot(cam, f1, (r1[0] * D, r1[1] * D, r1[2] * D))

    bpy.context.scene.camera = cams["cam-action"]
    return cams


def build_lights():
    bpy.ops.object.light_add(type="SUN", location=(0, -40, 70))
    sun = bpy.context.object
    sun.name = "light-sun"
    sun.data.energy = 3.0
    sun.data.angle = 2.0 * D
    sun.rotation_euler = (55 * D, 0, 20 * D)

    bpy.ops.object.light_add(type="AREA", location=(BEAM - 10, -14, 18))
    fill = bpy.context.object
    fill.name = "light-fill"
    fill.data.energy = 900.0
    fill.data.size = 14.0
    fill.rotation_euler = (40 * D, 0, -35 * D)

    bpy.ops.object.light_add(type="SUN", location=(ORBIT - 60, 120, 60))
    key = bpy.context.object
    key.name = "light-orbit"
    key.data.energy = 4.5
    key.rotation_euler = (110 * D, 0, -60 * D)


def setup_world(shotlist):
    world = bpy.data.worlds.new("space")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.008, 0.010, 0.020, 1.0)
    bg.inputs[1].default_value = 1.0

    sc = bpy.context.scene
    total = int(shotlist["totalFrames"])
    sc.render.resolution_x = int(shotlist.get("width", 720))
    sc.render.resolution_y = int(shotlist.get("height", 1280))
    sc.render.resolution_percentage = 100
    sc.render.fps = int(shotlist.get("fps", 30))
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 16
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.cycles.use_animated_seed = False
    sc.frame_start = 0
    sc.frame_end = max(total - 1, 0)
    try:
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
    except Exception:
        pass
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--shotlist", default="shotlist.json")
    ap.add_argument("--out", default="scenes/world.blend")
    a = ap.parse_args(argv)

    shotlist = json.load(open(a.shotlist, encoding="utf-8"))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_world(shotlist)

    build_sky(shotlist)
    build_beam(shotlist)
    build_orbit(shotlist)
    build_lights()
    cams = build_cameras(shotlist)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=a.out)
    print(f"wrote {a.out}: {len(bpy.data.objects)} objects, {len(cams)} cameras, "
          f"{shotlist['totalFrames']} frames, sets {', '.join(shotlist.get('sets', []))}")


if __name__ == "__main__":
    main()
