#!/usr/bin/env python3
"""Build the one world file for "Time Aapke Pairon Mein Dheere Chalta Hai".

    blender -b -P scenes/make_world.py -- --shotlist shotlist.json --out scenes/world.blend

One file holds three sets, one light rig, one palette and the whole camera grammar:

    set-tower  at the origin        a clock tower, two faces, a pendulum, two people
    set-lab    at x = +100          two atoms a millimetre apart, a laser, a scale marker
    set-orbit  at x = -100          the Earth, four GPS satellites, a dish, a drifting fix

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

LAB = 100.0
ORBIT = -100.0

# The camera grammar: one name, many uses. id -> (camera, lens, loc0, rot0, loc1, rot1)
# rot is degrees (x, y, z). rx 90 looks level along +Y; rx < 90 looks down, rx > 90 looks up.
# rz > 0 swings the view toward -X, rz < 0 toward +X.
CAMS = {
    # --- set-tower: tower at y = 12, faces at (0, 10.75, 3.2) and (0, 10.75, 6.4)
    # every end point below is the next shot's start point: the camera never resets.
    "01-hook":  ("cam-pov",    30, (0.0, -6.0, 1.55), (100, 0, 0), (0.0, -5.8, 1.62), (112, 0, 0)),
    "02-proof": ("cam-action", 30, (0.0, -5.8, 1.62), (112, 0, 0), (0.0, -5.2, 1.90), (104, 0, 0)),
    "03-base":  ("cam-action", 30, (0.0, -5.2, 1.90), (104, 0, 0), (0.0, -4.6, 2.60), (96, 0, 0)),
    "04-roof":  ("cam-rise",   30, (0.0, -4.6, 2.60), (96, 0, 0),  (0.0, -4.0, 3.80), (92, 0, 0)),
    "05-why":   ("cam-rise",   30, (0.0, -4.0, 3.80), (92, 0, 0),  (0.0, -3.4, 5.00), (90, 0, 0)),
    "06-rate":  ("cam-face",   40, (0.0, -3.4, 5.00), (90, 0, 0),  (0.0, -2.8, 5.60), (90, 0, 0)),
    "07-life":  ("cam-face",   40, (0.0, -2.8, 5.60), (90, 0, 0),  (0.0, -2.4, 6.20), (90, 0, 0)),
    # --- set-lab: atoms at (100, 3.0, 1.60) and (100, 3.0, 2.15)
    "08-mm":    ("cam-macro",  55, (100.15, 0.70, 1.90), (90, 0, 0), (100.10, 1.00, 1.90), (90, 0, 0)),
    "09-clock": ("cam-macro",  55, (100.10, 1.00, 1.90), (90, 0, 0), (100.05, 1.20, 1.90), (90, 0, 0)),
    # --- set-orbit: Earth centre (-100, 12, -14) r 6, dish at (-100, -1.5, -20)
    "10-gps":   ("cam-wide",   28, (-100.0, -20.0, 8.0), (78, 0, 0), (-100.0, -16.0, 7.0), (80, 0, 0)),
    "11-sat":   ("cam-wide",   28, (-100.0, -16.0, 7.0), (80, 0, 0), (-100.0, -13.0, 6.0), (82, 0, 0)),
    "12-farq":  ("cam-action", 35, (-100.0, -8.0, 3.0),  (84, 0, 0), (-100.0, -6.0, 3.2),  (84, 0, 0)),
    "13-drift": ("cam-action", 35, (-100.0, -6.0, 3.2),  (84, 0, 0), (-100.0, -4.0, 3.4),  (86, 0, 0)),
    "14-twist": ("cam-pov",    35, (-100.0, -3.0, 2.0),  (88, 0, 0), (-100.0, -2.5, 2.0),  (88, 0, 0)),
    "15-pahad": ("cam-wide",   28, (-100.0, -3.0, 2.2),  (82, 0, 0), (-100.0, -12.0, 6.0), (78, 0, 0)),
    # --- back to the tower, still moving
    "16-recap": ("cam-wide",   28, (0.0, -26.0, 6.0), (82, 0, 0), (0.0, -34.0, 9.0), (80, 0, 0)),
    "17-close": ("cam-action", 30, (0.0, -7.5, 1.6),  (88, 0, 0), (0.0, -6.8, 2.0),  (94, 0, 0)),
    "18-end":   ("cam-rise",   35, (0.0, -6.8, 2.0),  (94, 0, 0), (0.0, -5.0, 5.6),  (92, 0, 0)),
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
    return [
        cylinder(f"{prefix}-torso", (x, y, z + 0.92), 0.20, 0.72, suit, verts=16),
        sphere(f"{prefix}-head", (x, y, z + 1.44), 0.145, skin),
        cylinder(f"{prefix}-leg-l", (x - 0.10, y, z + 0.32), 0.075, 0.66, suit, verts=12),
        cylinder(f"{prefix}-leg-r", (x + 0.10, y, z + 0.32), 0.075, 0.66, suit, verts=12),
        cylinder(f"{prefix}-arm-l", (x - 0.27, y, z + 0.95), 0.055, 0.60, suit, verts=12),
        cylinder(f"{prefix}-arm-r", (x + 0.27, y, z + 0.95), 0.055, 0.60, suit, verts=12),
    ]


def pivot_at_top(ob, depth):
    from mathutils import Matrix
    ob.data.transform(Matrix.Translation((0.0, 0.0, -depth / 2.0)))


def hand(name, centre, length, mat, tilt=0.0):
    """A clock hand lying in the face plane, its origin at the pivot."""
    from mathutils import Matrix
    ob = cube(name, centre, 1.0, mat)
    ob.data.transform(Matrix.Translation((0.0, 0.0, 0.5)))
    ob.scale = (0.05, 0.03, length)
    ob.rotation_euler = (0.0, tilt, 0.0)
    return ob


def build_tower(shotlist):
    stone = surface_mat("tower-stone", (0.10, 0.10, 0.11), rough=0.85)
    dark = surface_mat("tower-dark", (0.03, 0.032, 0.038), rough=0.6)
    ground = surface_mat("tower-ground", (0.05, 0.052, 0.058), rough=0.9)
    plane("tower-ground", (0, 0, -0.02), 400, ground)

    cylinder("tower-shaft", (0, 12.0, 3.5), 1.2, 7.0, stone, verts=32)
    cylinder("tower-roof", (0, 12.0, 7.05), 1.5, 0.15, stone, verts=32)

    face_mat = emission_mat("tower-face", (0.92, 0.88, 0.76), 0.55)
    rim_mat = surface_mat("tower-rim", (0.02, 0.02, 0.03), rough=0.4, metal=0.6)
    hand_mat = emission_mat("tower-hand", (1.0, 0.55, 0.15), 0.9)

    faces = {}
    for name, z in (("low", 3.2), ("high", 6.4)):
        cylinder(f"tower-face-{name}", (0, 10.72, z), 1.35, 0.12, face_mat,
                 rot=(90 * D, 0, 0), verts=48)
        cylinder(f"tower-rim-{name}", (0, 10.66, z), 1.45, 0.06, rim_mat,
                 rot=(90 * D, 0, 0), verts=48)
        faces[name] = (hand(f"tower-hand-{name}", (0, 10.62, z), 0.95, hand_mat),
                       hand(f"tower-hand-{name}-h", (0, 10.60, z), 0.62, hand_mat, 1.9))

    rod_mat = surface_mat("pendulum-rod", (0.35, 0.28, 0.12), rough=0.35, metal=0.8)
    rod = cylinder("pendulum-rod", (0, 10.35, 3.9), 0.035, 1.5, rod_mat, verts=12)
    pivot_at_top(rod, 1.5)
    bob = sphere("pendulum-bob", (0, 10.35, 3.15), 0.22, rod_mat, seg=20, ring=12)

    person_mat = surface_mat("tower-person", (0.07, 0.08, 0.10), rough=0.8)
    skin_mat = surface_mat("tower-skin", (0.11, 0.09, 0.08), rough=0.7)
    make_figure("person-base", (0.9, 9.2, 0.0), person_mat, skin_mat)
    make_figure("person-roof", (0.7, 11.4, 7.15), person_mat, skin_mat)

    # --- the pendulum swings while the camera climbs the base
    for sid, amp in (("01-hook", 0.32), ("02-proof", 0.30), ("03-base", 0.26)):
        f0, f1 = shot_window(shotlist, sid)
        f = f0
        while f <= f1:
            t = (f - f0) / 30.0
            key_rot(rod, f, (0.0, amp * math.sin(t * 4.4), 0.0))
            key_rot(bob, f, (0.0, amp * math.sin(t * 4.4), 0.0))
            f += 4

    # --- the two faces tick, and the upper one ticks faster
    for sid, low_rate, high_rate in (("04-roof", 0.9, 1.15), ("05-why", 0.8, 1.2),
                                     ("06-rate", 0.7, 1.3), ("07-life", 0.6, 1.4),
                                     ("17-close", 0.9, 1.15), ("18-end", 0.6, 1.4)):
        f0, f1 = shot_window(shotlist, sid)
        for name, rate in (("low", low_rate), ("high", high_rate)):
            minute, hour = faces[name]
            key_rot(minute, f0, (0, 0.4, 0))
            key_rot(minute, f1, (0, 0.4 + rate * 2.2, 0))
            key_rot(hour, f0, (0, 1.9, 0))
            key_rot(hour, f1, (0, 1.9 + rate * 0.18, 0))
    return faces


def build_lab(shotlist):
    x = LAB
    bench = surface_mat("lab-bench", (0.03, 0.033, 0.04), rough=0.7)
    plane("lab-floor", (x, 4, -0.02), 24, bench)
    plane("lab-wall", (x, 9, 4), 24, bench)
    bpy.context.object.rotation_euler = (90 * D, 0, 0)

    atom_mat = emission_mat("lab-atom", (0.55, 0.78, 1.0), 1.1)
    atom_lo = sphere("lab-atom-low", (x, 3.0, 1.60), 0.30, atom_mat, seg=32, ring=16)
    atom_hi = sphere("lab-atom-high", (x, 3.0, 2.15), 0.30, atom_mat, seg=32, ring=16)

    gap_mat = emission_mat("lab-gap", (1.0, 0.35, 0.15), 1.2)
    cylinder("lab-gap", (x, 2.72, 1.875), 0.012, 0.55, gap_mat, verts=8)
    label_mat = emission_mat("lab-label", (1.0, 0.97, 0.92), 1.3)
    label("lab-label-mm", "1 mm", (x, 2.60, 1.875), 0.16, label_mat, rot=(90 * D, 0, 0))

    beam_mat = emission_mat("lab-laser", (1.0, 0.45, 0.25), 1.0)
    cylinder("lab-laser", (x, 1.0, 2.6), 0.025, 5.0, beam_mat, rot=(90 * D, 0, 0), verts=8)

    f0, f1 = shot_window(shotlist, "08-mm")
    key_scale(atom_lo, f0, (1, 1, 1))
    key_scale(atom_lo, f1, (1.18, 1.18, 1.18))
    key_strength(atom_mat, f0, 0.8)
    key_strength(atom_mat, f1, 1.4)

    f0, f1 = shot_window(shotlist, "09-clock")
    for i, ob in enumerate((atom_lo, atom_hi)):
        step = 6 if i == 0 else 4
        f = f0
        while f <= f1:
            key_strength(atom_mat, f, 1.5)
            f += step
    key_strength(atom_mat, f1, 1.0)
    return {"atoms": (atom_lo, atom_hi)}


def build_orbit(shotlist):
    x = ORBIT
    centre = (x, 12.0, -14.0)
    earth = sphere("orbit-earth", centre, 6.0, earth_mat("orbit-earth-mat"), seg=64, ring=32)
    shell = sphere("orbit-shell", centre, 6.10,
                   limb_mat("orbit-shell-mat", (0.32, 0.58, 1.0), 1.6), seg=64, ring=32)

    ground = surface_mat("orbit-ground", (0.04, 0.045, 0.05), rough=0.9)
    plane("orbit-ground", (x, -4, -20.2), 40, ground)
    dish_mat = surface_mat("orbit-dish", (0.55, 0.56, 0.6), rough=0.3, metal=0.7)
    cone("orbit-dish", (x, -1.5, -19.9), 0.7, 0.12, 0.45, dish_mat, rot=(180 * D, 0, 0), verts=32)

    sat_body = surface_mat("orbit-sat", (0.62, 0.64, 0.70), rough=0.35, metal=0.5)
    panel = surface_mat("orbit-panel", (0.06, 0.12, 0.32), rough=0.25, metal=0.4,
                        emit=(0.10, 0.18, 0.45), emit_strength=0.25)
    sats = []
    for i in range(4):
        a = i * (math.pi / 2.0) + 0.4
        r = 9.0
        loc = (x + r * math.cos(a), 12.0 + r * 0.55, -14.0 + r * math.sin(a))
        parts = [cube(f"sat-{i}", loc, 0.36, sat_body)]
        for side in (-1, 1):
            p = cube(f"sat-{i}-panel-{side}", (loc[0] + side * 0.55, loc[1], loc[2]), 1.0, panel)
            p.scale = (0.42, 0.03, 0.16)
            parts.append(p)
        sats.append((parts, loc, a))

    person_mat = surface_mat("orbit-person", (0.10, 0.10, 0.12), rough=0.8)
    skin_mat = surface_mat("orbit-skin", (0.12, 0.10, 0.09), rough=0.7)
    make_figure("person-ground", (x, -3.2, -20.0), person_mat, skin_mat)

    # the fix drifts: a marker sliding away from the person, 10 km exaggerated
    fix_mat = emission_mat("orbit-fix", (1.0, 0.25, 0.15), 1.4)
    marker = cube("orbit-fix", (x, -2.0, -19.9), 0.25, fix_mat)

    f0, f1 = shot_window(shotlist, "10-gps")
    for i, (parts, loc, a) in enumerate(sats):
        for p in parts:
            key_rot(p, f0, (0, 0, a))
            key_rot(p, f1, (0, 0, a + 0.6))
    key_rot(earth, f0, (0, 0, 0))
    key_rot(earth, f1, (0, 0, 0.10))

    f0, f1 = shot_window(shotlist, "11-sat")
    for parts, loc, a in sats:
        for p in parts:
            key_rot(p, f0, (0, 0, a + 0.6))
            key_rot(p, f1, (0, 0, a + 1.1))
    key_rot(earth, f0, (0, 0, 0.10))
    key_rot(earth, f1, (0, 0, 0.16))

    sig_mat = emission_mat("orbit-signal", (0.35, 0.75, 1.0), 1.0)
    f0, f1 = shot_window(shotlist, "12-farq")
    for i, (parts, loc, a) in enumerate(sats):
        ob = cylinder(f"orbit-signal-{i}", (x, (loc[1] - 19.9) / 2.0, (loc[2] - 19.9) / 2.0),
                      0.02, 1.0, sig_mat, verts=6)
        key_scale(ob, f0, (1, 1, 0.01))
        key_scale(ob, f0 + 10 + i * 4, (1, 1, 1))
        key_scale(ob, f1, (1, 1, 1))

    f0, f1 = shot_window(shotlist, "13-drift")
    key_loc(marker, f0, (x, -2.0, -19.9))
    key_loc(marker, f1, (x + 2.6, -1.2, -19.9))
    f0, f1 = shot_window(shotlist, "14-twist")
    key_loc(marker, f0, (x + 2.6, -1.2, -19.9))
    key_loc(marker, f1, (x + 2.8, -1.1, -19.9))
    key_rot(earth, f0, (0, 0, 0.16))
    key_rot(earth, f1, (0, 0, 0.20))

    f0, f1 = shot_window(shotlist, "15-pahad")
    key_rot(earth, f0, (0, 0, 0.20))
    key_rot(earth, f1, (0, 0, 0.24))
    return {"earth": earth, "marker": marker}


# ----------------------------------------------------------------------------- cameras
def build_cameras(shotlist):
    cams = {}
    for name in ("cam-wide", "cam-action", "cam-macro", "cam-pov", "cam-rise", "cam-face"):
        bpy.ops.object.camera_add(location=(0, 0, 0), rotation=(90 * D, 0, 0))
        cam = bpy.context.object
        cam.name = name
        cam.data.lens = 35
        cam.data.clip_start = 0.02
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
    bpy.ops.object.light_add(type="SUN", location=(0, -40, 30))
    sun = bpy.context.object
    sun.name = "light-sun"
    sun.data.energy = 2.4
    sun.data.angle = 3.0 * D
    sun.rotation_euler = (62 * D, 0, 18 * D)

    bpy.ops.object.light_add(type="AREA", location=(LAB - 2, 0.5, 4.5))
    fill = bpy.context.object
    fill.name = "light-lab"
    fill.data.energy = 260.0
    fill.data.size = 6.0
    fill.rotation_euler = (55 * D, 0, -20 * D)

    bpy.ops.object.light_add(type="SUN", location=(ORBIT - 40, 60, 40))
    key = bpy.context.object
    key.name = "light-orbit"
    key.data.energy = 3.2
    key.rotation_euler = (115 * D, 0, -55 * D)


def setup_world(shotlist):
    world = bpy.data.worlds.new("space")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.006, 0.008, 0.014, 1.0)
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

    build_tower(shotlist)
    build_lab(shotlist)
    build_orbit(shotlist)
    build_lights()
    cams = build_cameras(shotlist)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=a.out)
    print(f"wrote {a.out}: {len(bpy.data.objects)} objects, {len(cams)} cameras, "
          f"{shotlist['totalFrames']} frames, sets {', '.join(shotlist.get('sets', []))}")


if __name__ == "__main__":
    main()
