<<<<<<< HEAD
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
=======
from gscrib import GCodeBuilder
#Geometry (mm)
plate_width=220
plate_height=180
base_length=80
base_depth=10
base_thickness=1
wall_thickness=1
wall_length=80
wall_height=10
g = GCodeBuilder(output="output.gcode");
g.set_length_units("millimeters")
g.set_distance_mode("absolute")
g.write("M104 S220")
g.write("M190 S60")
g.write("M109 S220")
g.set_axis(x=0, y=0, z=0)
X=g.position[0]
Y=g.position[1]
Z=g.position[2]
def update_position():
    global X, Y, Z
    X = g.position[0]
    Y = g.position[1]
    Z = g.position[2]
def extrusion_hook():
    g.write("E1.0")
    
g.move_hook(extrusion_hook)
g.rapid(z=4)
g.rapid(x=plate_width-base_length,
        y=plate_height-base_depth,
        z=0)
update_position()
for z in range(0,base_thickness):
    for y in range(0,base_depth):
        for x in range(0, base_length):
            g.move(x=X+1)
            update_position()
        g.rapid(y=Y+1)
        g.rapid(x=plate_width-base_length)
        update_position()
    g.rapid(z=Z+1)
    update_position()
g.rapid(x=plate_width-wall_length,
        y=plate_height-wall_thickness)
for z in range(0,wall_height):

    g.rapid(z=Z+1)
g.set_axis(x=g.position[0],
           y=g.position[1],
           z=g.position[2])
g.teardown()
>>>>>>> ee0983fdc91662727b9a529c5addd61b22fda2f0
