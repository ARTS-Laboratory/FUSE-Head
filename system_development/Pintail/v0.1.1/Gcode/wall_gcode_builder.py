# from moonraker_client import MoonrakerClient
import gscrib
from gscrib import GCodeBuilder
import math

PLATE_DIMENSIONS = [150, 170]
BASE_DIMENSIONS = (
    int(PLATE_DIMENSIONS[0] / 4),
    int(PLATE_DIMENSIONS[1] / 8),
    1,
)
WALL_DIMENSIONS = (
    int(BASE_DIMENSIONS[0] * 3/4),
    1,
    10,
)
print(f'PLATE DIMENSIONS (mm): {PLATE_DIMENSIONS}')
print(f'BASE DIMENSIONS (mm): {BASE_DIMENSIONS}')
print(f'WALL DIMENSIONS (mm): {WALL_DIMENSIONS}')
def print_rect_in_center(g, d, sensor_data_collection=False):
    center = (PLATE_DIMENSIONS[0] / 2, PLATE_DIMENSIONS[1] / 2)
    for z in range(0, d[2]):
        for y in range(0, d[1]):
            g.rapid(
                x=center[0] - d[0] / 2,
                y=center[1] - d[1] / 2 + y,
            )
            g.wait()
            if (sensor_data_collection):
                g.rapid(
                    x=g.position[0] - 10
                )
            g.move(x=g.position[0] + d[0])
            g.wait()
            if (sensor_data_collection):
                g.rapid(
                    x=g.position[0] + 10
                )
        g.rapid(z=g.position[2] + 1)

def extrude_hook(origin, target, params, state):
    dt = target - origin
    length = math.hypot(dt.x, dt.y, dt.z)
    params.update(E=0.1 * length)
    return params

g = GCodeBuilder(output="wall.gcode")
g.write("SET_KINEMATIC_POSITION X=0 Y=0 Z=0")
g.set_fan_speed(255)
g.set_bed_temperature(60)
g.halt(gscrib.enums.HaltMode.WAIT_FOR_BED)
g.set_hotend_temperature(220)
g.halt(gscrib.enums.HaltMode.WAIT_FOR_HOTEND)
g.add_hook(extrude_hook)
print_rect_in_center(g, BASE_DIMENSIONS)
print_rect_in_center(g, WALL_DIMENSIONS, True)
g.teardown()
