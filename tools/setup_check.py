import sys
import time

import bpy

engine = sys.argv[sys.argv.index("--") + 1]
out = sys.argv[sys.argv.index("--") + 2]

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.resolution_percentage = 100
scene.render.filepath = out

bpy.ops.mesh.primitive_plane_add(size=10)
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 1))
bpy.ops.object.light_add(type="AREA", location=(3, -3, 5))
bpy.context.object.data.energy = 800
bpy.ops.object.camera_add(location=(0, -7, 3), rotation=(1.25, 0, 0))
scene.camera = bpy.context.object

device = "CPU"
if engine == "CYCLES":
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "HIP"
    prefs.get_devices()
    # The iGPU also reports as HIP and slows the discrete card down.
    gpus = [d for d in prefs.devices if d.type == "HIP" and "(TM) Graphics" not in d.name]
    for d in prefs.devices:
        d.use = d in gpus
    if gpus:
        scene.cycles.device = "GPU"
        device = "HIP: " + ", ".join(d.name for d in gpus)
    scene.cycles.samples = 64
else:
    scene.render.engine = "BLENDER_EEVEE"
    device = "EEVEE (OpenGL/Vulkan)"

start = time.time()
bpy.ops.render.render(write_still=True)
print(f"SETUP_CHECK engine={engine} device={device} seconds={time.time() - start:.2f}")
