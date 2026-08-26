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
g.write("G90")
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
        y=plate_height-wall_depth)
for z in range(0,wall_height):

    g.rapid(z=Z+1)
g.teardown();
