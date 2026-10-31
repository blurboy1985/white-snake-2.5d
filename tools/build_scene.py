"""Build every set, prop, actor and camera from build/timeline.json, then save or render.

Usage:
  blender --background --enable-autoexec --python tools/build_scene.py -- ROOT save
  blender --background --enable-autoexec --python tools/build_scene.py -- ROOT stills F1,F2,... [PERCENT]
  blender --background --enable-autoexec --python tools/build_scene.py -- ROOT anim [START END]
"""
import json
import math
import pathlib
import random
import sys

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:]
ROOT = pathlib.Path(ARGS[0])
MODE = ARGS[1]
TIMELINE = json.loads((ROOT / "build" / "timeline.json").read_text(encoding="utf-8"))
CHARS = ROOT / "build" / "chars"
ORIGINS = {
    "pagoda": (0, 0, 0), "under": (0, 0, -60), "lake": (600, 0, 0), "shop": (1200, 0, 0),
    "kunlun": (1800, 0, 0), "temple": (2400, 0, 0), "study": (3000, 0, 0),
}
random.seed(7)


def at(o, x, y, z):
    return (o[0] + x, o[1] + y, o[2] + z)


# ---------- materials ----------

def mat_surface(name, color, rough=0.7, metal=0.0, emit=None, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    if emit:
        p.inputs["Emission Color"].default_value = (*emit, 1)
        p.inputs["Emission Strength"].default_value = strength
    return m


def mat_unlit(name, color, strength=1.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    if alpha < 1:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = alpha
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        m.surface_render_method = "BLENDED"
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


def mat_sky(name, horizon, zenith):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    em = nt.nodes.new("ShaderNodeEmission")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*horizon, 1)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (*zenith, 1)
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m


IMAGE_MATS = {}


def mat_image(variant, silhouette=False):
    key = (variant, silhouette)
    if key in IMAGE_MATS:
        return IMAGE_MATS[key]
    img = bpy.data.images.load(str(CHARS / f"{variant}.png"), check_existing=True)
    m = bpy.data.materials.new(f"img_{variant}{'_sil' if silhouette else ''}")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Cubic"
    em = nt.nodes.new("ShaderNodeEmission")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    if silhouette:
        em.inputs["Color"].default_value = (0.02, 0.015, 0.02, 1)
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = 0.9
        nt.links.new(tex.outputs["Alpha"], mul.inputs[0])
        nt.links.new(mul.outputs[0], mix.inputs["Fac"])
    else:
        nt.links.new(tex.outputs["Color"], em.inputs["Color"])
        nt.links.new(tex.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "BLENDED"
    IMAGE_MATS[key] = m
    return m


def mat_contact_shadow():
    m = bpy.data.materials.new("contact_shadow")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = "LENGTH"
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.2
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = 0.5
    mr.inputs["To Max"].default_value = 0.0
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0, 0, 0, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.surface_render_method = "BLENDED"
    return m


# ---------- geometry helpers ----------

def link(obj, coll):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def prim(kind, coll, loc, scale=(1, 1, 1), rot=(0, 0, 0), mat=None, name=None, **kw):
    ops = {
        "cube": bpy.ops.mesh.primitive_cube_add, "cyl": bpy.ops.mesh.primitive_cylinder_add,
        "cone": bpy.ops.mesh.primitive_cone_add, "sphere": bpy.ops.mesh.primitive_uv_sphere_add,
        "plane": bpy.ops.mesh.primitive_plane_add, "torus": bpy.ops.mesh.primitive_torus_add,
        "circle": bpy.ops.mesh.primitive_circle_add,
    }
    ops[kind](location=loc, rotation=[math.radians(r) for r in rot], **kw)
    obj = bpy.context.object
    obj.scale = scale
    if name:
        obj.name = name
    if mat:
        obj.data.materials.append(mat)
    if kind in ("sphere", "cyl", "cone", "torus"):
        bpy.ops.object.shade_smooth()
    return link(obj, coll)


def empty(coll, loc, name):
    obj = bpy.data.objects.new(name, None)
    obj.location = loc
    coll.objects.link(obj)
    return obj


def parent(child, par):
    child.parent = par
    child.matrix_parent_inverse = par.matrix_world.inverted()


def sun(coll, rot, color, strength, name):
    data = bpy.data.lights.new(name, "SUN")
    data.energy = strength
    data.color = color
    data.angle = math.radians(8)
    obj = bpy.data.objects.new(name, data)
    obj.rotation_euler = [math.radians(r) for r in rot]
    coll.objects.link(obj)
    obj.light_linking.receiver_collection = coll
    obj.light_linking.blocker_collection = coll
    return obj


def point(coll, loc, color, power, name, radius=0.1, kind="POINT"):
    data = bpy.data.lights.new(name, kind)
    data.energy = power
    data.color = color
    data.shadow_soft_size = radius
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    coll.objects.link(obj)
    return obj


def dome(coll, o, horizon, zenith, radius=220):
    d = prim("sphere", coll, o, (radius, radius, radius), mat=mat_sky(f"sky_{coll.name}", horizon, zenith),
             name=f"dome_{coll.name}", segments=48, ring_count=24)
    d.visible_shadow = False
    return d


def new_set(name):
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll


# ---------- keyframes ----------

def key(obj, path, frame, value, interp="BEZIER", index=-1):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    target = obj
    attr = path
    if "." in path:
        head, attr = path.rsplit(".", 1)
        target = obj.path_resolve(head)
    if index >= 0:
        getattr(target, attr)[index] = value
    else:
        setattr(target, attr, value)
    target.keyframe_insert(attr, index=index, frame=frame)


def hold_then_restore(obj, path, start, settle, end, rest, moved):
    key(obj, path, 0, rest, "CONSTANT")
    key(obj, path, start, rest, "BEZIER")
    key(obj, path, settle, moved, "CONSTANT")
    key(obj, path, end + 1, rest, "CONSTANT")


# ---------- sets ----------

FX = {}


def build_pagoda(coll, o):
    dome(coll, o, (0.98, 0.6, 0.36), (0.26, 0.2, 0.46))
    prim("plane", coll, at(o, 0, -60, -0.3), (220, 70, 1), mat=mat_surface("dusk_water", (0.07, 0.12, 0.2), rough=0.08))
    prim("cube", coll, at(o, 0, 70, -1), (160, 62, 1), mat=mat_surface("dusk_grass", (0.17, 0.2, 0.12)))
    hill = mat_surface("dusk_hill", (0.24, 0.22, 0.36), rough=0.95)
    for x, y, sx, sz in ((-70, 140, 60, 26), (10, 160, 70, 34), (85, 135, 55, 22), (-20, 120, 30, 12)):
        prim("sphere", coll, at(o, x, y, -4), (sx, 30, sz), mat=hill, segments=32, ring_count=16)
    tree = mat_surface("dusk_tree", (0.08, 0.14, 0.08))
    for _ in range(26):
        x = random.choice((-1, 1)) * random.uniform(9, 45)
        y = random.uniform(12, 50)
        h = random.uniform(4, 8)
        prim("cone", coll, at(o, x, y, h / 2), (1, 1, 1), mat=tree, vertices=10, radius1=h * 0.35, radius2=0, depth=h)

    brick = mat_surface("brick", (0.5, 0.27, 0.15), rough=0.9)
    tile = mat_surface("roof_tile", (0.1, 0.1, 0.11), rough=0.6)
    stone = mat_surface("stone", (0.45, 0.43, 0.4), rough=0.9)
    gold = mat_surface("gold", (0.9, 0.65, 0.2), rough=0.3, metal=1.0)
    window = mat_unlit("pagoda_window", (1.0, 0.62, 0.28), 2.5)
    base = at(o, 0, 30, 0)
    prim("cyl", coll, (base[0], base[1], 0.6), (1, 1, 1), mat=stone, vertices=8, radius=6.2, depth=1.2)
    tiers, z = [], 1.2
    for i in range(5):
        r, h = 4.2 - 0.55 * i, 3.4 - 0.3 * i
        piv = empty(coll, (base[0], base[1], z), f"tier{i}")
        body = prim("cyl", coll, (base[0], base[1], z + h / 2), mat=brick, vertices=8, radius=r, depth=h)
        roof = prim("cone", coll, (base[0], base[1], z + h + 0.45), mat=tile, vertices=8, radius1=r + 1.9, radius2=r * 0.6, depth=0.9)
        win = prim("plane", coll, (base[0], base[1] - r * 0.93, z + h * 0.5), (0.45, 0.7, 1), rot=(90, 0, 0), mat=window)
        for part in (body, roof, win):
            parent(part, piv)
        tiers.append(piv)
        z += h + 0.9
    fin = prim("cone", coll, (base[0], base[1], z + 1.4), mat=gold, vertices=8, radius1=0.5, radius2=0.05, depth=2.8)
    parent(fin, tiers[-1])
    dust_mat = mat_unlit("dust", (0.55, 0.45, 0.36), 1.0, alpha=0.55)
    dust = [prim("sphere", coll, at(o, random.uniform(-6, 6), 30 + random.uniform(-4, 3), random.uniform(1, 8)), (0.01,) * 3,
                 mat=dust_mat, segments=16, ring_count=8) for _ in range(12)]
    bowl = prim("sphere", coll, (base[0], base[1], z + 26), (0.01,) * 3, mat=mat_surface("bowl", (1.0, 0.75, 0.25), 0.25, 1.0, (1.0, 0.7, 0.2), 3.0),
                segments=32, ring_count=16)
    bowl_light = point(coll, (base[0], base[1], z + 3), (1.0, 0.75, 0.35), 0, "bowl_light", radius=2)
    sun(coll, (62, 0, -55), (1.0, 0.68, 0.45), 3.2, "pagoda_sun")
    FX["pagoda"] = {"tiers": tiers, "dust": dust, "bowl": bowl, "bowl_light": bowl_light, "top": z}


def build_under(coll, o):
    wall = mat_surface("vault", (0.22, 0.2, 0.19), rough=0.95)
    prim("cube", coll, at(o, 0, 4, -0.1), (6, 6, 0.1), mat=wall)
    prim("cube", coll, at(o, 0, 8.1, 3), (6, 0.1, 3.2), mat=wall)
    for x in (-5.5, 5.5):
        prim("cube", coll, at(o, x, 4, 3), (0.2, 6, 3.2), mat=wall)
    prim("cube", coll, at(o, -3.5, 4, 6.1), (2.6, 6, 0.1), mat=wall)
    prim("cube", coll, at(o, 3.5, 4, 6.1), (2.6, 6, 0.1), mat=wall)
    for x in range(-5, 6, 2):
        prim("cube", coll, at(o, x, 7.95, 3), (0.06, 0.06, 3.2), mat=mat_surface(f"seam{x}", (0.14, 0.12, 0.12)))
    shaft = prim("cone", coll, at(o, 0, 4, 3), mat=mat_unlit("shaft", (1.0, 0.8, 0.4), 1.0, alpha=0.06), vertices=24, radius1=1.6, radius2=0.7, depth=6)
    shaft.visible_shadow = False
    spot = point(coll, at(o, 0, 4, 5.9), (1.0, 0.78, 0.4), 1800, "vault_spot", radius=0.4, kind="SPOT")
    spot.data.spot_size = math.radians(55)
    point(coll, at(o, 2, -2, 2.5), (0.45, 0.5, 0.9), 120, "vault_fill", radius=1)
    wash = point(coll, at(o, -1.5, 2.5, 1.0), (1.0, 0.7, 0.4), 900, "wall_wash", radius=0.3, kind="SPOT")
    wash.rotation_euler = (math.radians(80), 0, math.radians(-20))
    wash.data.spot_size = math.radians(70)


def build_lake(coll, o):
    dome(coll, o, (0.64, 0.7, 0.74), (0.34, 0.4, 0.5))
    prim("plane", coll, at(o, 0, 40, 0), (200, 120, 1), mat=mat_surface("lake_water", (0.17, 0.26, 0.29), rough=0.06))
    wood = mat_surface("pier_wood", (0.33, 0.2, 0.11))
    prim("cube", coll, at(o, 0, -0.8, 0.15), (3.4, 2.2, 0.15), mat=wood)
    for x in (-3, -1, 1, 3):
        prim("cyl", coll, at(o, x, 1.3, 0.2), mat=wood, vertices=10, radius=0.12, depth=1.2)
    stone = mat_surface("bridge_stone", (0.6, 0.6, 0.58))
    prim("torus", coll, at(o, 9, 26, 0), rot=(90, 0, 0), mat=stone, major_radius=5, minor_radius=1.0)
    prim("cube", coll, at(o, 9, 26, 5.4), (9, 1.2, 0.45), mat=stone)
    for x in (2.5, 15.5):
        prim("cube", coll, at(o, x, 26, 2.4), (2.2, 1.2, 2.6), mat=stone)
    bark = mat_surface("bark", (0.22, 0.15, 0.1))
    leaf = mat_surface("willow", (0.28, 0.46, 0.22))
    prim("cyl", coll, at(o, -5.5, 6, 2.5), mat=bark, vertices=10, radius=0.3, depth=5)
    for _ in range(14):
        prim("sphere", coll, at(o, -5.5 + random.uniform(-2.5, 2.5), 6 + random.uniform(-1, 1), random.uniform(2.5, 5.5)),
             (0.5, 0.5, random.uniform(1.4, 2.2)), mat=leaf, segments=12, ring_count=8)
    hull = mat_surface("boat", (0.24, 0.14, 0.08))
    prim("cube", coll, at(o, 5, 9, 0.2), (2.4, 0.7, 0.3), mat=hull)
    prim("cyl", coll, at(o, 5, 9, 0.6), (1, 1, 1), rot=(0, 90, 0), mat=mat_surface("canopy", (0.12, 0.1, 0.09)), vertices=16, radius=0.7, depth=1.6)
    prim("sphere", coll, at(o, 3.2, 9, 1.1), (0.18, 0.18, 0.24), mat=mat_unlit("boat_lantern", (1.0, 0.45, 0.15), 3.0))
    point(coll, at(o, 3.2, 8.6, 1.1), (1.0, 0.55, 0.25), 60, "boat_light")
    hill = mat_surface("lake_hill", (0.42, 0.48, 0.52), rough=0.95)
    for x, y, sx, sz in ((-60, 110, 55, 22), (30, 130, 70, 30), (95, 105, 40, 16)):
        prim("sphere", coll, at(o, x, y, -3), (sx, 25, sz), mat=hill, segments=32, ring_count=16)

    verts, faces = [], []
    for _ in range(1400):
        x, y, z = random.uniform(-14, 14), random.uniform(-6, 26), random.uniform(0, 12)
        for zz in (z, z + 12):
            i = len(verts)
            verts += [(x, y, zz), (x + 0.012, y, zz), (x + 0.012, y, zz + 0.45), (x, y, zz + 0.45)]
            faces.append((i, i + 1, i + 2, i + 3))
    me = bpy.data.meshes.new("rain")
    me.from_pydata(verts, [], faces)
    rain = bpy.data.objects.new("rain", me)
    rain.location = o
    rain.data.materials.append(mat_unlit("rain", (0.85, 0.9, 0.95), 1.0, alpha=0.4))
    rain.visible_shadow = False
    coll.objects.link(rain)
    drv = rain.driver_add("location", 2).driver
    drv.type = "SCRIPTED"
    drv.expression = "-((frame * 0.7) % 12)"
    sun(coll, (55, 0, 20), (0.8, 0.86, 1.0), 2.2, "lake_sun")


def build_shop(coll, o):
    floor = mat_surface("shop_floor", (0.3, 0.17, 0.09))
    plaster = mat_surface("plaster", (0.78, 0.68, 0.52), rough=0.95)
    prim("cube", coll, at(o, 0, 0, -0.05), (5, 6, 0.05), mat=floor)
    prim("cube", coll, at(o, 0, 4.3, 1.9), (5, 0.1, 1.9), mat=plaster)
    for x in (-4.6, 4.6):
        prim("cube", coll, at(o, x, 0, 1.9), (0.1, 6, 1.9), mat=plaster)
    prim("cube", coll, at(o, 0, 0, 3.85), (5, 6, 0.1), mat=mat_surface("ceiling", (0.25, 0.15, 0.09)))
    drawer = mat_surface("drawer", (0.46, 0.24, 0.11))
    brass = mat_surface("brass", (0.85, 0.62, 0.25), rough=0.3, metal=1.0)
    prim("cube", coll, at(o, 0, 4.05, 1.55), (3.3, 0.2, 1.4), mat=mat_surface("cabinet", (0.28, 0.14, 0.07)))
    for row in range(7):
        for col in range(9):
            x, z = -2.9 + col * 0.725, 0.4 + row * 0.38
            prim("cube", coll, at(o, x, 3.83, z), (0.33, 0.04, 0.16), mat=drawer)
            prim("sphere", coll, at(o, x, 3.77, z), (0.03,) * 3, mat=brass, segments=8, ring_count=6)
    prim("cube", coll, at(o, 0, 4.0, 3.25), (1.6, 0.1, 0.32), mat=mat_surface("sign", (0.12, 0.08, 0.06)))
    prim("cube", coll, at(o, 0, 3.94, 3.25), (1.35, 0.02, 0.22), mat=mat_unlit("sign_gold", (0.85, 0.6, 0.2), 1.2))
    prim("cube", coll, at(o, 0, 1.5, 0.5), (2.3, 0.35, 0.5), mat=mat_surface("counter", (0.36, 0.19, 0.09)))
    prim("cube", coll, at(o, 0, 1.5, 1.02), (2.4, 0.42, 0.03), mat=mat_surface("counter_top", (0.2, 0.1, 0.05), rough=0.35))
    prim("sphere", coll, at(o, 1.4, 1.45, 1.22), (0.17, 0.17, 0.2), mat=mat_surface("jar", (0.42, 0.28, 0.16), rough=0.3))
    prim("cube", coll, at(o, -4.48, 1.0, 1.8), (0.02, 0.8, 0.7), mat=mat_unlit("shop_window", (1.0, 0.85, 0.6), 1.6))
    red = mat_unlit("lantern_red", (0.95, 0.2, 0.08), 2.2)
    for x in (-2.6, 2.6):
        prim("cyl", coll, at(o, x, 1.0, 3.35), mat=mat_surface("cord", (0.05, 0.05, 0.05)), vertices=6, radius=0.01, depth=0.9)
        prim("sphere", coll, at(o, x, 1.0, 2.7), (0.32, 0.32, 0.38), mat=red, segments=24, ring_count=12)
        point(coll, at(o, x, 0.6, 2.6), (1.0, 0.45, 0.2), 160, f"lantern_light{x}", radius=0.3)
    bunting = mat_surface("bunting", (0.2, 0.55, 0.3))
    for i in range(9):
        prim("cone", coll, at(o, -3.2 + i * 0.8, 2.6, 3.55), (1, 1, 1), rot=(180, 0, 0), mat=bunting, vertices=3, radius1=0.2, depth=0.35)
    point(coll, at(o, 0, -2.5, 3.3), (1.0, 0.82, 0.62), 380, "shop_key", radius=1.5, kind="AREA").data.size = 3


def build_kunlun(coll, o):
    dome(coll, o, (0.82, 0.88, 0.96), (0.24, 0.42, 0.78))
    snow = mat_surface("snow", (0.92, 0.95, 1.0), rough=0.8)
    blue = mat_surface("far_rock", (0.46, 0.53, 0.66), rough=0.9)
    rock_tex = bpy.data.textures.new("rock", "CLOUDS")
    rock_tex.noise_scale = 5
    for x, y, r, h, m in ((-50, 90, 32, 58, snow), (15, 110, 40, 70, snow), (60, 85, 28, 46, snow),
                          (-25, 50, 18, 26, blue), (30, 55, 20, 30, blue), (-6, 70, 14, 34, snow)):
        c = prim("cone", coll, at(o, x, y, h / 2 - 2), mat=m, vertices=32, radius1=r, radius2=0, depth=h)
        sub = c.modifiers.new("sub", "SUBSURF")
        sub.subdivision_type = "SIMPLE"
        sub.levels = sub.render_levels = 4
        disp = c.modifiers.new("disp", "DISPLACE")
        disp.texture = rock_tex
        disp.strength = r * 0.12
    ledge = prim("cube", coll, at(o, 0, 3.5, 0.25), (4.5, 3.5, 0.25), mat=mat_surface("ledge", (0.22, 0.24, 0.3)))
    bev = ledge.modifiers.new("bev", "BEVEL")
    bev.width = 0.2
    bev.segments = 3
    prim("cyl", coll, at(o, 1.5, 3.2, 0.62), mat=mat_surface("stem", (0.55, 0.38, 0.22)), vertices=12, radius=0.04, depth=0.25)
    prim("sphere", coll, at(o, 1.5, 3.2, 0.76), (0.24, 0.24, 0.07),
         mat=mat_surface("lingzhi", (0.6, 0.18, 0.08), 0.35, emit=(1.0, 0.6, 0.15), strength=0.6))
    herb_light = point(coll, at(o, 1.5, 2.8, 1.1), (1.0, 0.75, 0.3), 40, "herb_light", radius=0.2)
    mist = mat_unlit("mist", (0.95, 0.97, 1.0), 1.0, alpha=0.22)
    for y, z in ((25, 4), (40, 9), (60, 14)):
        m = prim("plane", coll, at(o, 0, y, z), (90, 8, 1), rot=(90, 0, 0), mat=mist)
        m.visible_shadow = False
    sun(coll, (50, 0, 30), (1.0, 0.95, 0.88), 2.2, "kunlun_sun")
    FX["kunlun"] = {"herb_light": herb_light}


def build_temple(coll, o):
    dome(coll, o, (0.34, 0.33, 0.46), (0.07, 0.07, 0.17))
    prim("cube", coll, at(o, 0, 22, 0), (24, 20, 2), mat=mat_surface("temple_hill", (0.18, 0.2, 0.16)))
    stone = mat_surface("steps", (0.5, 0.48, 0.45))
    for i in range(5):
        prim("cube", coll, at(o, 0, 1.8 - i * 0.4, 0.2 + i * 0.4), (3.2, 0.2, 0.2), mat=stone)
    prim("cube", coll, at(o, 0, 11, 2.4), (6.5, 3.4, 0.4), mat=stone)
    red = mat_surface("pillar_red", (0.6, 0.1, 0.07))
    for x in (-5, -2.5, 2.5, 5):
        prim("cyl", coll, at(o, x, 7.9, 4.55), mat=red, vertices=16, radius=0.28, depth=3.5)
    prim("cube", coll, at(o, 0, 10.5, 4.55), (5.4, 2.4, 1.75), mat=mat_surface("hall", (0.42, 0.09, 0.07)))
    roof = prim("cone", coll, at(o, 0, 10.4, 7.6), (1.0, 0.55, 1), rot=(0, 0, 45), mat=mat_surface("temple_roof", (0.14, 0.2, 0.17)),
                vertices=4, radius1=9.5, radius2=1.2, depth=3.2)
    roof.scale = (1.35, 0.62, 1)
    gold = mat_surface("temple_gold", (0.9, 0.65, 0.2), 0.3, 1.0)
    for x in (-1.5, 1.5):
        prim("cube", coll, at(o, x, 6.2, 3.6), (0.15, 0.15, 1.6), mat=red)
    prim("cube", coll, at(o, 0, 6.2, 5.25), (1.8, 0.2, 0.15), mat=red)
    gate = empty(coll, at(o, 0, 6.2, 5.0), "gate")
    for i in range(7):
        bar = prim("cyl", coll, at(o, -1.2 + i * 0.4, 6.2, 3.6), mat=gold, vertices=8, radius=0.05, depth=3.0)
        parent(bar, gate)
    lantern = mat_unlit("temple_lantern", (1.0, 0.7, 0.3), 3)
    for x in (-3.8, 3.8):
        prim("sphere", coll, at(o, x, 7.6, 5.4), (0.25, 0.25, 0.32), mat=lantern)
        point(coll, at(o, x, 7.0, 5.2), (1.0, 0.6, 0.3), 180, f"temple_lamp{x}", radius=0.3)
    water = prim("plane", coll, at(o, 0, 10, -1.5), (40, 40, 1), mat=mat_surface("flood", (0.12, 0.26, 0.34), rough=0.05))
    sub = water.modifiers.new("sub", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 6
    wave = water.modifiers.new("wave", "WAVE")
    wave.height, wave.width, wave.speed, wave.narrowness = 0.25, 2.2, 0.18, 1.2
    sun(coll, (60, 0, -30), (0.62, 0.68, 1.0), 1.6, "temple_sun")
    FX["temple"] = {"gate": gate, "water": water}


def build_study(coll, o):
    prim("cube", coll, at(o, 0, 0, -0.05), (3, 4, 0.05), mat=mat_surface("study_floor", (0.26, 0.17, 0.11)))
    wall = mat_surface("study_wall", (0.68, 0.64, 0.56), rough=0.95)
    prim("cube", coll, at(o, 0, 3.1, 1.6), (3, 0.1, 1.6), mat=wall)
    for x in (-3, 3):
        prim("cube", coll, at(o, x, 0, 1.6), (0.1, 4, 1.6), mat=wall)
    prim("cube", coll, at(o, 1.2, 3.0, 1.75), (0.55, 0.02, 0.65), mat=mat_unlit("study_window", (0.78, 0.86, 1.0), 1.3))
    prim("cube", coll, at(o, 1.2, 2.98, 1.75), (0.6, 0.03, 0.03), mat=mat_surface("mullion", (0.2, 0.12, 0.08)))
    shelf = mat_surface("shelf", (0.3, 0.18, 0.1))
    prim("cube", coll, at(o, -1.7, 2.85, 1.1), (0.8, 0.2, 1.1), mat=shelf)
    colors = [(0.55, 0.15, 0.12), (0.18, 0.3, 0.45), (0.75, 0.65, 0.4), (0.25, 0.35, 0.2)]
    for row in range(4):
        x = -2.4
        while x < -1.0:
            w = random.uniform(0.04, 0.08)
            prim("cube", coll, at(o, x + w, 2.7, 0.35 + row * 0.5), (w * 0.9, 0.12, random.uniform(0.15, 0.2)),
                 mat=mat_surface(f"book{row}{x:.2f}", random.choice(colors)))
            x += w * 2 + 0.01
    prim("cube", coll, at(o, 0, 1.0, 0.39), (1.3, 0.45, 0.39), mat=mat_surface("desk", (0.3, 0.18, 0.1), rough=0.4))
    paper = mat_surface("paper", (0.95, 0.93, 0.86))
    for dx, rz in ((-0.6, 8), (-0.45, -5)):
        prim("cube", coll, at(o, dx, 0.9, 0.785), (0.15, 0.2, 0.002), rot=(0, 0, rz), mat=paper)
    prim("cyl", coll, at(o, -1.0, 1.15, 0.95), mat=mat_surface("lamp_post", (0.15, 0.15, 0.15)), vertices=8, radius=0.015, depth=0.35)
    prim("cone", coll, at(o, -1.0, 1.15, 1.15), mat=mat_unlit("lamp_shade", (1.0, 0.85, 0.55), 1.5), vertices=16, radius1=0.16, radius2=0.06, depth=0.14)
    point(coll, at(o, -1.0, 1.0, 1.05), (1.0, 0.75, 0.45), 35, "desk_lamp", radius=0.08)
    point(coll, at(o, 0.3, -1.5, 2.2), (1.0, 0.9, 0.8), 140, "study_key", radius=1.2, kind="AREA").data.size = 2
    point(coll, at(o, 1.2, 2.5, 1.8), (0.7, 0.8, 1.0), 60, "window_fill", radius=0.6)

    prim("cyl", coll, at(o, 0.3, 0.9, 0.787), mat=mat_surface("plate", (0.85, 0.9, 0.95), rough=0.2), vertices=32, radius=0.19, depth=0.012)
    shell = mat_surface("crab_shell", (0.86, 0.3, 0.11), rough=0.35)
    inside = mat_surface("crab_inside", (0.95, 0.85, 0.6), rough=0.6)
    prim("sphere", coll, at(o, 0.3, 0.9, 0.812), (0.11, 0.08, 0.026), mat=inside, segments=32, ring_count=16)
    hinge = empty(coll, at(o, 0.3, 0.985, 0.818), "crab_hinge")
    lid = prim("sphere", coll, at(o, 0.3, 0.9, 0.818), (0.122, 0.09, 0.032), mat=shell, segments=32, ring_count=16)
    parent(lid, hinge)
    for side in (-1, 1):
        for i in range(4):
            prim("cyl", coll, at(o, 0.3 + side * 0.15, 0.93 + i * 0.03, 0.8), (1, 1, 1), rot=(0, 90 + side * 25, side * (15 - i * 12)),
                 mat=shell, vertices=8, radius=0.008, depth=0.13)
        prim("sphere", coll, at(o, 0.3 + side * 0.12, 0.78, 0.81), (0.04, 0.025, 0.02), mat=shell, segments=12, ring_count=8)
        prim("sphere", coll, at(o, 0.3 + side * 0.025, 0.815, 0.835), (0.007,) * 3, mat=mat_surface(f"crab_eye{side}", (0.02, 0.02, 0.02), 0.2),
             segments=8, ring_count=6)
    FX["study"] = {"hinge": hinge}


BUILDERS = {"pagoda": build_pagoda, "under": build_under, "lake": build_lake, "shop": build_shop,
            "kunlun": build_kunlun, "temple": build_temple, "study": build_study}


# ---------- fx ----------

def fx_collapse(shot, fx):
    f, end = fx["frame"], shot["end"]
    p = FX["pagoda"]
    for i, tier in enumerate(p["tiers"]):
        start = f + (4 - i) * 2
        settle = start + 16 + i
        rest_z = tier.location.z
        hold_then_restore(tier, "location", start, settle, end, (tier.location.x, tier.location.y, rest_z),
                          (tier.location.x + random.uniform(-2.5, 2.5), tier.location.y + random.uniform(-2, 1), 1.2 + i * 0.55))
        hold_then_restore(tier, "rotation_euler", start, settle, end, (0, 0, 0),
                          tuple(math.radians(random.uniform(-28, 28)) for _ in range(3)))
    for d in p["dust"]:
        size = random.uniform(3, 6.5)
        key(d, "scale", f + 6, (0.01,) * 3, "BEZIER")
        key(d, "scale", f + 30, (size,) * 3, "CONSTANT")
        key(d, "scale", end + 1, (0.01,) * 3, "CONSTANT")


def fx_bowl(shot, fx):
    p = FX["pagoda"]
    f, bowl, top = fx["frame"], p["bowl"], p["top"]
    key(bowl, "scale", 0, (0.01,) * 3, "CONSTANT")
    key(bowl, "scale", f, (3.5, 3.5, 1.6), "BEZIER")
    key(bowl, "location", f, (bowl.location.x, bowl.location.y, top + 26), "BEZIER")
    key(bowl, "location", f + 30, (bowl.location.x, bowl.location.y, top + 4.5), "CONSTANT")
    key(p["bowl_light"], "data.energy", 0, 0, "CONSTANT")
    key(p["bowl_light"], "data.energy", f + 20, 0, "BEZIER")
    key(p["bowl_light"], "data.energy", f + 32, 60000, "CONSTANT")


def fx_bowl_off(frame):
    p = FX["pagoda"]
    key(p["bowl"], "scale", frame, (0.01,) * 3, "CONSTANT")
    key(p["bowl_light"], "data.energy", frame, 0, "CONSTANT")


def fx_herb_glow(shot, fx):
    light = FX["kunlun"]["herb_light"]
    key(light, "data.energy", fx["frame"] - 4, 40, "BEZIER")
    key(light, "data.energy", fx["frame"] + 8, 900, "CONSTANT")


def fx_gate_close(shot, fx):
    gate = FX["temple"]["gate"]
    x, y, z = tuple(gate.location)
    key(gate, "location", 0, (x, y, z + 3.2), "CONSTANT")
    key(gate, "location", fx["frame"], (x, y, z + 3.2), "BEZIER")
    key(gate, "location", fx["frame"] + 6, (x, y, z), "CONSTANT")


def fx_flood(shot, fx):
    water = FX["temple"]["water"]
    x, y = water.location.x, water.location.y
    key(water, "location", 0, (x, y, -1.5), "CONSTANT")
    key(water, "location", fx["frame"], (x, y, -1.5), "BEZIER")
    key(water, "location", fx["frame"] + 36, (x, y, 2.3), "CONSTANT")


def fx_crab(shot, fx, angle, dur):
    hinge = FX["study"]["hinge"]
    key(hinge, "rotation_euler", fx["frame"], tuple(hinge.rotation_euler), "BEZIER")
    key(hinge, "rotation_euler", fx["frame"] + dur, (math.radians(angle), 0, 0), "CONSTANT")


FX_HANDLERS = {
    "collapse": fx_collapse, "bowl": fx_bowl, "herb_glow": fx_herb_glow, "gate_close": fx_gate_close,
    "flood": fx_flood, "crab_open": lambda s, f: fx_crab(s, f, -100, 10), "crab_close": lambda s, f: fx_crab(s, f, -12, 6),
    "bowl_hold": lambda s, f: None, "crab_hold_open": lambda s, f: None,
}


# ---------- actors and cameras ----------

SHADOW_MAT = None


def variant_plane(name, variant, scale, silhouette):
    img = bpy.data.images.load(str(CHARS / f"{variant}.png"), check_existing=True)
    w, h = img.size[0] / 1100 * scale, img.size[1] / 1100 * scale
    me = bpy.data.meshes.new(name)
    me.from_pydata([(-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, 0, h), (-w / 2, 0, h)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    corners = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for loop in me.loops:
        uv.data[loop.index].uv = corners[loop.vertex_index]
    obj = bpy.data.objects.new(name, me)
    obj.data.materials.append(mat_image(variant, silhouette))
    obj.visible_shadow = False
    return obj, w


def build_actor(shot, actor, coll):
    o = ORIGINS[shot["set"]]
    name = f"{shot['id']}_{actor['who']}"
    root = empty(coll, at(o, *actor["at"]), name)
    flip = -1 if actor.get("flip") else 1
    variants = sorted({k["variant"] for k in actor["keys"] if "variant" in k})
    planes = {}
    for v in variants:
        plane, width = variant_plane(f"{name}_{v}", v, actor["scale"], actor.get("silhouette", False))
        coll.objects.link(plane)
        plane.parent = root
        planes[v] = plane
    if actor.get("shadow", True):
        global SHADOW_MAT
        SHADOW_MAT = SHADOW_MAT or mat_contact_shadow()
        sh = prim("circle", coll, (0, 0, 0), mat=SHADOW_MAT, vertices=32, radius=1, fill_type="NGON")
        sh.parent = root
        sh.location = (0, 0, 0.01)
        sh.scale = (actor["scale"] * 0.32, actor["scale"] * 0.12, 1)
        sh.visible_shadow = False
        planes["_shadow"] = sh

    showing = []
    for k in actor["keys"]:
        if "variant" in k or k.get("hide"):
            showing.append((k["frame"], None if k.get("hide") else k["variant"]))
    for v, plane in planes.items():
        def show(frame, on):
            key(plane, "hide_render", frame, not on, "CONSTANT")
            key(plane, "hide_viewport", frame, not on, "CONSTANT")
        if shot["start"] > 0:
            show(0, False)
        for frame, current in showing:
            show(frame, current is not None and (v == "_shadow" or current == v))
        show(shot["end"] + 1, False)

    base_scale = (flip, 1, 1)
    key(root, "scale", shot["start"], base_scale, "BEZIER")
    key(root, "location", shot["start"], tuple(root.location), "BEZIER")
    key(root, "rotation_euler", shot["start"], (0, 0, 0), "BEZIER")
    loc = list(root.location)
    for k in actor["keys"]:
        f = k["frame"]
        if "move" in k:
            key(root, "location", f, tuple(loc), "BEZIER")
            loc = list(at(o, *k["move"]))
            key(root, "location", f + k.get("dur", 12), tuple(loc), "BEZIER")
        if "rot" in k:
            target = (0, math.radians(k["rot"]), 0)
            if k.get("dur", 9) > 1:
                key(root, "rotation_euler", f, tuple(root.rotation_euler), "BEZIER")
                key(root, "rotation_euler", f + k.get("dur", 9), target, "BEZIER")
            else:
                key(root, "rotation_euler", f, target, "BEZIER")
        if k.get("hop"):
            for df, (sx, sz) in ((0, (1, 1)), (3, (1.08, 0.9)), (7, (0.96, 1.07)), (11, (1, 1))):
                key(root, "scale", f + df, (flip * sx, 1, sz), "BEZIER")
        if k.get("pop"):
            for df, s in ((0, 0.05), (5, 1.12), (9, 1.0)):
                key(root, "scale", f + df, (flip * s, s, s), "BEZIER")


def build_camera(shot, coll):
    o = ORIGINS[shot["set"]]
    c = shot["cam"]
    shaker = empty(coll, (0, 0, 0), f"{shot['id']}_shaker")
    look = empty(coll, at(o, *c["look"]), f"{shot['id']}_look")
    data = bpy.data.cameras.new(shot["id"])
    data.lens = c["lens"]
    data.sensor_width = 36
    data.clip_end = 900
    data.dof.use_dof = True
    data.dof.focus_object = look
    data.dof.aperture_fstop = c.get("fstop", 5.6)
    cam = bpy.data.objects.new(f"cam_{shot['id']}", data)
    coll.objects.link(cam)
    cam.parent = shaker
    con = cam.constraints.new("TRACK_TO")
    con.target = look
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    key(cam, "location", shot["start"], at(o, *c["from"]), "BEZIER")
    key(cam, "location", shot["end"] + 1, at(o, *c["to"]), "BEZIER")
    if "shake" in c:
        f = c["shake"]
        amp = 0.25 if shot["set"] in ("pagoda", "temple") else 0.06
        key(shaker, "location", f - 1, (0, 0, 0), "BEZIER")
        for i in range(10):
            fall = amp * (1 - i / 10)
            key(shaker, "location", f + i * 2, (random.uniform(-fall, fall), 0, random.uniform(-fall, fall)), "BEZIER")
        key(shaker, "location", f + 22, (0, 0, 0), "BEZIER")
    marker = bpy.context.scene.timeline_markers.new(shot["id"], frame=shot["start"])
    marker.camera = cam
    return cam


# ---------- main ----------

def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
    scene.render.fps = TIMELINE["fps"]
    scene.frame_start, scene.frame_end = 0, TIMELINE["frame_end"]
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.eevee.taa_render_samples = 24
    scene.eevee.shadow_pool_size = "1024"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.compression = 15
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.03, 0.03, 0.04, 1)
    scene.world = world
    return scene


def main():
    scene = setup_scene()
    colls = {name: new_set(name) for name in ORIGINS}
    for name, build in BUILDERS.items():
        build(colls[name], ORIGINS[name])
    actors_coll = new_set("actors")
    cams_coll = new_set("cameras")
    for shot in TIMELINE["shots"]:
        build_camera(shot, cams_coll)
        for actor in shot.get("actors", []):
            build_actor(shot, actor, actors_coll)
        for fx in shot["fx"]:
            FX_HANDLERS[fx["type"]](shot, fx)
    fx_bowl_off(next(s for s in TIMELINE["shots"] if s["id"] == "s23")["start"])
    scene.camera = bpy.data.objects["cam_s01"]

    out = ROOT / "build"
    if MODE == "save":
        bpy.ops.wm.save_as_mainfile(filepath=str(out / "episode.blend"))
    elif MODE == "stills":
        scene.render.resolution_percentage = int(ARGS[3]) if len(ARGS) > 3 else 50
        (out / "stills").mkdir(exist_ok=True)
        for f in [int(x) for x in ARGS[2].split(",")]:
            scene.frame_set(f)
            scene.render.filepath = str(out / "stills" / f"{f:04d}.png")
            bpy.ops.render.render(write_still=True)
    elif MODE == "anim":
        if len(ARGS) > 3:
            scene.frame_start, scene.frame_end = int(ARGS[2]), int(ARGS[3])
        scene.render.filepath = str(out / "frames" / "####")
        bpy.ops.render.render(animation=True)


main()
