# from moonraker_client import MoonrakerClient
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
def print_rect_in_center(g, d):
    center = (PLATE_DIMENSIONS[0] / 2, PLATE_DIMENSIONS[1] / 2)
    for z in range(0, d[2]):
        for y in range(0, d[1]):
            g.rapid(
                x=center[0] - d[0] / 2,
                y=center[1] - d[1] / 2 + y,
            )
            g.move(x=g.position[0] + d[0])
        g.rapid(z=g.position[2] + 1)

def extrude_hook(origin, target, params, state):
    dt = target - origin
    length = math.hypot(dt.x, dt.y, dt.z)
    params.update(E=0.1 * length)
    return params

g = GCodeBuilder(output="test.gcode")
g.add_hook(extrude_hook)
print_rect_in_center(g, BASE_DIMENSIONS)
print_rect_in_center(g, WALL_DIMENSIONS)
g.teardown()
# with MoonrakerClient("http://localhost:7125") as client:
