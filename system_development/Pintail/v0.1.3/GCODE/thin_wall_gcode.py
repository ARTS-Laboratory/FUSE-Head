#!/usr/bin/env python3
"""Generate Klipper-compatible G-code for a thin wall on a rectangular base.

Edit only the values in the USER SETTINGS section, then run:
    python3 thin_wall_gcode.py

The generated G-code uses standard M190/M109 wait commands, so it works with
Klipper/Fluidd installations that support normal Marlin-style temperature
commands.  It deliberately uses no third-party Python libraries.
"""

# ============================== USER SETTINGS ==============================

# Dimensions are [X length, Y width, Z height] in millimetres.
BASE_SIZE_MM = [60, 20, 0.25]

# Wall dimensions are [length along its orientation, thickness, height].
# Wall height starts at the top of the base; it is not the total print height.
WALL_SIZE_MM = [50, 0.5, 100]

# "x" makes the wall run left-to-right.  "y" rotates it 90 degrees.
WALL_ORIENTATION = "x"

# Number of parallel deposited tracks across WALL_SIZE_MM[1].  This is the
# "layers thick" setting.  The tracks are spread across the requested wall
# thickness, so changing it does not change the outside wall dimensions.
WALL_LAYERS_THICK = 1

# "positive" means +X (left-to-right) for an X wall, or +Y for a Y wall.
# "negative" reverses that direction.  Every wall track extrudes only in this
# direction; all return and cross-wall moves are non-extruding travels.
WALL_PRINT_DIRECTION = "positive"

# Build plate dimensions and placement. An offset of [0, 0] centers the base
# on a 220 x 220 mm plate. Positive X/Y moves the entire print accordingly.
BUILD_PLATE_SIZE_MM = [90, 150]
PLACEMENT_OFFSET_X_MM = -15
PLACEMENT_OFFSET_Y_MM = 90

# Global scan boundaries. These are absolute machine coordinates, not offsets.
# They default to the non-negative 0..220 mm plate range. Values must remain
# inside BUILD_PLATE_SIZE_MM. The scan goes to the closer end first, then
# sweeps to the opposite end after every wall layer.
SCAN_X_LEFTMOST_MM = 0.0
SCAN_X_RIGHTMOST_MM = 90
SCAN_Y_FRONTMOST_MM = 0.0
SCAN_Y_BACKMOST_MM = 150

# Temperatures: M190 waits for the bed and M109 waits for the nozzle.
BED_TEMPERATURE_C = 60
EXTRUDER_TEMPERATURE_C = 222

# Print settings.  Match these to your printer, filament, and nozzle.
NOZZLE_DIAMETER_MM = 0.40
BASE_LINE_WIDTH_MM = 0.42
LAYER_HEIGHT_MM = 0.20
FILAMENT_DIAMETER_MM = 1.75
EXTRUSION_MULTIPLIER = 1.00
FIRST_LAYER_SPEED_MM_S = 20.0
PRINT_SPEED_MM_S = 35.0
TRAVEL_SPEED_MM_S = 150.0

# Lift before moving to the start of each wall layer.  This prevents the
# non-extruding approach move from rubbing across the previously printed wall.
WALL_APPROACH_CLEARANCE_MM = 0.5

# A non-extruding scan is made after every wall layer. It runs parallel to the
# wall at the current wall-top Z plus this lift. Set the lift for your
# scanner/nozzle geometry. The file does not include G28, so home the printer
# or otherwise establish its absolute coordinate system before starting it.
ENABLE_LAYER_SCAN = True
SCAN_SPEED_MM_S = 15.0
SCAN_Z_LIFT_MM = 2.0
SCAN_CROSS_AXIS_OFFSET_MM = 0.0  # 0 = scan directly over the wall centreline
SCAN_SETTLE_SECONDS = 0.0        # Optional dwell before and after each sweep

OUTPUT_FILE = "thin_wall.gcode"

# ============================ END USER SETTINGS ============================


EPSILON = 0.000001
PI = 3.141592653589793


def fmt(value, decimals=3):
    """Format a G-code number without unnecessary trailing zeroes."""
    if abs(value) < EPSILON:
        value = 0.0
    if decimals == 0:
        return format(value, ".0f")
    text = format(value, ".{}f".format(decimals)).rstrip("0").rstrip(".")
    return text if text else "0"


def require_positive(name, value):
    if value <= 0:
        raise ValueError("{} must be greater than zero.".format(name))


def make_layers(total_height, target_layer_height):
    """Return (top_z, actual_layer_height) pairs with an exact final height."""
    require_positive("height", total_height)
    require_positive("LAYER_HEIGHT_MM", target_layer_height)

    layers = []
    z = 0.0
    while z + target_layer_height < total_height - EPSILON:
        z += target_layer_height
        layers.append((z, target_layer_height))

    final_height = total_height - z
    if final_height > EPSILON:
        layers.append((total_height, final_height))
    return layers


def line_positions(start, end, spacing):
    """Return evenly spaced line centres, including both requested edges."""
    require_positive("line spacing", spacing)
    if end < start:
        raise ValueError("Line end cannot be before its start.")

    positions = [start]
    position = start + spacing
    while position < end - EPSILON:
        positions.append(position)
        position += spacing
    if end - positions[-1] > EPSILON:
        positions.append(end)
    return positions


def extrusion_amount(distance, line_width, layer_height):
    """Return relative filament length for a rectangular deposited bead."""
    filament_area = PI * (FILAMENT_DIAMETER_MM / 2.0) ** 2
    deposited_volume = distance * line_width * layer_height
    return deposited_volume / filament_area * EXTRUSION_MULTIPLIER


class GCode:
    def __init__(self):
        self.lines = []

    def add(self, line):
        self.lines.append(line)

    def comment(self, text):
        self.add("; {}".format(text))

    def travel(self, x=None, y=None, z=None, speed_mm_s=None):
        parts = ["G0"]
        if x is not None:
            parts.append("X{}".format(fmt(x)))
        if y is not None:
            parts.append("Y{}".format(fmt(y)))
        if z is not None:
            parts.append("Z{}".format(fmt(z)))
        if speed_mm_s is not None:
            parts.append("F{}".format(fmt(speed_mm_s * 60.0, 0)))
        self.add(" ".join(parts))

    def extrude_to(self, x, y, distance, line_width, layer_height, speed_mm_s):
        amount = extrusion_amount(distance, line_width, layer_height)
        self.add(
            "G1 X{} Y{} E{} F{}".format(
                fmt(x),
                fmt(y),
                fmt(amount, 5),
                fmt(speed_mm_s * 60.0, 0),
            )
        )

    def dwell(self, seconds):
        if seconds > 0:
            self.add("G4 P{}".format(int(seconds * 1000.0)))


def validate_settings():
    if len(BASE_SIZE_MM) != 3 or len(WALL_SIZE_MM) != 3:
        raise ValueError("BASE_SIZE_MM and WALL_SIZE_MM must each have three values.")
    if len(BUILD_PLATE_SIZE_MM) != 2:
        raise ValueError("BUILD_PLATE_SIZE_MM must have two values.")

    for name, value in (
        ("base X", BASE_SIZE_MM[0]),
        ("base Y", BASE_SIZE_MM[1]),
        ("base Z", BASE_SIZE_MM[2]),
        ("wall length", WALL_SIZE_MM[0]),
        ("wall thickness", WALL_SIZE_MM[1]),
        ("wall height", WALL_SIZE_MM[2]),
        ("build plate X", BUILD_PLATE_SIZE_MM[0]),
        ("build plate Y", BUILD_PLATE_SIZE_MM[1]),
        ("NOZZLE_DIAMETER_MM", NOZZLE_DIAMETER_MM),
        ("BASE_LINE_WIDTH_MM", BASE_LINE_WIDTH_MM),
        ("FILAMENT_DIAMETER_MM", FILAMENT_DIAMETER_MM),
        ("WALL_LAYERS_THICK", WALL_LAYERS_THICK),
        ("SCAN_SPEED_MM_S", SCAN_SPEED_MM_S),
    ):
        require_positive(name, value)

    if int(WALL_LAYERS_THICK) != WALL_LAYERS_THICK:
        raise ValueError("WALL_LAYERS_THICK must be a whole number.")
    if WALL_ORIENTATION.lower() not in ("x", "y"):
        raise ValueError('WALL_ORIENTATION must be "x" or "y".')
    if WALL_PRINT_DIRECTION.lower() not in ("positive", "negative"):
        raise ValueError('WALL_PRINT_DIRECTION must be "positive" or "negative".')
    if WALL_APPROACH_CLEARANCE_MM < 0 or SCAN_Z_LIFT_MM < 0 or SCAN_SETTLE_SECONDS < 0:
        raise ValueError("Wall-approach clearance, scan lift, and settle time cannot be negative.")

    for name, value in (
        ("SCAN_X_LEFTMOST_MM", SCAN_X_LEFTMOST_MM),
        ("SCAN_X_RIGHTMOST_MM", SCAN_X_RIGHTMOST_MM),
        ("SCAN_Y_FRONTMOST_MM", SCAN_Y_FRONTMOST_MM),
        ("SCAN_Y_BACKMOST_MM", SCAN_Y_BACKMOST_MM),
    ):
        if value < 0:
            raise ValueError("{} cannot be negative.".format(name))
    if not 0 <= SCAN_X_LEFTMOST_MM < SCAN_X_RIGHTMOST_MM <= BUILD_PLATE_SIZE_MM[0]:
        raise ValueError("X scan boundaries must be ordered and inside BUILD_PLATE_SIZE_MM.")
    if not 0 <= SCAN_Y_FRONTMOST_MM < SCAN_Y_BACKMOST_MM <= BUILD_PLATE_SIZE_MM[1]:
        raise ValueError("Y scan boundaries must be ordered and inside BUILD_PLATE_SIZE_MM.")

    wall_track_width = WALL_SIZE_MM[1] / WALL_LAYERS_THICK
    if wall_track_width < NOZZLE_DIAMETER_MM * 0.65:
        raise ValueError(
            "Wall tracks are too narrow for this nozzle. Reduce WALL_LAYERS_THICK "
            "or increase WALL_SIZE_MM[1]."
        )
    if wall_track_width > NOZZLE_DIAMETER_MM * 1.8:
        raise ValueError(
            "Wall tracks are too wide for this nozzle. Increase WALL_LAYERS_THICK "
            "or reduce WALL_SIZE_MM[1]."
        )


def geometry():
    """Calculate base and wall bounds, centered on the build plate plus offset."""
    center_x = BUILD_PLATE_SIZE_MM[0] / 2.0 + PLACEMENT_OFFSET_X_MM
    center_y = BUILD_PLATE_SIZE_MM[1] / 2.0 + PLACEMENT_OFFSET_Y_MM

    base_x0 = center_x - BASE_SIZE_MM[0] / 2.0
    base_x1 = center_x + BASE_SIZE_MM[0] / 2.0
    base_y0 = center_y - BASE_SIZE_MM[1] / 2.0
    base_y1 = center_y + BASE_SIZE_MM[1] / 2.0

    orientation = WALL_ORIENTATION.lower()
    if orientation == "x":
        wall_x0 = center_x - WALL_SIZE_MM[0] / 2.0
        wall_x1 = center_x + WALL_SIZE_MM[0] / 2.0
        wall_y0 = center_y - WALL_SIZE_MM[1] / 2.0
        wall_y1 = center_y + WALL_SIZE_MM[1] / 2.0
    else:
        wall_x0 = center_x - WALL_SIZE_MM[1] / 2.0
        wall_x1 = center_x + WALL_SIZE_MM[1] / 2.0
        wall_y0 = center_y - WALL_SIZE_MM[0] / 2.0
        wall_y1 = center_y + WALL_SIZE_MM[0] / 2.0

    return {
        "center_x": center_x,
        "center_y": center_y,
        "base_x0": base_x0,
        "base_x1": base_x1,
        "base_y0": base_y0,
        "base_y1": base_y1,
        "wall_x0": wall_x0,
        "wall_x1": wall_x1,
        "wall_y0": wall_y0,
        "wall_y1": wall_y1,
    }


def validate_geometry(box):
    def inside_build_plate(name, x0, x1, y0, y1):
        if x0 < -EPSILON or y0 < -EPSILON:
            raise ValueError("{} extends below the build plate origin.".format(name))
        if x1 > BUILD_PLATE_SIZE_MM[0] + EPSILON or y1 > BUILD_PLATE_SIZE_MM[1] + EPSILON:
            raise ValueError("{} extends beyond BUILD_PLATE_SIZE_MM.".format(name))

    inside_build_plate("Base", box["base_x0"], box["base_x1"], box["base_y0"], box["base_y1"])
    inside_build_plate("Wall", box["wall_x0"], box["wall_x1"], box["wall_y0"], box["wall_y1"])

    if (
        box["wall_x0"] < box["base_x0"] - EPSILON
        or box["wall_x1"] > box["base_x1"] + EPSILON
        or box["wall_y0"] < box["base_y0"] - EPSILON
        or box["wall_y1"] > box["base_y1"] + EPSILON
    ):
        raise ValueError(
            "The wall does not fit on the base. For a Y-oriented 18 mm wall, "
            "increase BASE_SIZE_MM[1] to at least 18 mm."
        )

    if ENABLE_LAYER_SCAN:
        if WALL_ORIENTATION.lower() == "x":
            scan_cross_position = box["center_y"] + SCAN_CROSS_AXIS_OFFSET_MM
            if not box["base_y0"] - EPSILON <= scan_cross_position <= box["base_y1"] + EPSILON:
                raise ValueError("The X-wall scan line must remain within the base Y range.")
        else:
            scan_cross_position = box["center_x"] + SCAN_CROSS_AXIS_OFFSET_MM
            if not box["base_x0"] - EPSILON <= scan_cross_position <= box["base_x1"] + EPSILON:
                raise ValueError("The Y-wall scan line must remain within the base X range.")


def print_base_layer(gcode, box, z, layer_height, horizontal, speed):
    """Print a solid raster base; alternating layers swap raster direction."""
    half_width = BASE_LINE_WIDTH_MM / 2.0
    x0 = box["base_x0"] + half_width
    x1 = box["base_x1"] - half_width
    y0 = box["base_y0"] + half_width
    y1 = box["base_y1"] - half_width

    gcode.travel(z=z, speed_mm_s=TRAVEL_SPEED_MM_S)
    if horizontal:
        rows = line_positions(y0, y1, BASE_LINE_WIDTH_MM)
        for index, y in enumerate(rows):
            if index % 2 == 0:
                start_x, end_x = x0, x1
            else:
                start_x, end_x = x1, x0
            gcode.travel(x=start_x, y=y, speed_mm_s=TRAVEL_SPEED_MM_S)
            gcode.extrude_to(end_x, y, abs(end_x - start_x), BASE_LINE_WIDTH_MM, layer_height, speed)
    else:
        columns = line_positions(x0, x1, BASE_LINE_WIDTH_MM)
        for index, x in enumerate(columns):
            if index % 2 == 0:
                start_y, end_y = y0, y1
            else:
                start_y, end_y = y1, y0
            gcode.travel(x=x, y=start_y, speed_mm_s=TRAVEL_SPEED_MM_S)
            gcode.extrude_to(x, end_y, abs(end_y - start_y), BASE_LINE_WIDTH_MM, layer_height, speed)


def wall_track_positions(box, track_width):
    """Return cross-axis centres for the wall's parallel deposited tracks."""
    if WALL_ORIENTATION.lower() == "x":
        start = box["wall_y0"] + track_width / 2.0
        end = box["wall_y1"] - track_width / 2.0
    else:
        start = box["wall_x0"] + track_width / 2.0
        end = box["wall_x1"] - track_width / 2.0
    return line_positions(start, end, track_width)


def print_wall_layer(gcode, box, z, layer_height, track_width):
    """Print each wall track in exactly one wall-parallel extrusion direction."""
    orientation = WALL_ORIENTATION.lower()
    positive = WALL_PRINT_DIRECTION.lower() == "positive"
    track_positions = wall_track_positions(box, track_width)

    if orientation == "x":
        low, high = box["wall_x0"] + track_width / 2.0, box["wall_x1"] - track_width / 2.0
        start_x, end_x = (low, high) if positive else (high, low)
        gcode.travel(z=z + WALL_APPROACH_CLEARANCE_MM, speed_mm_s=TRAVEL_SPEED_MM_S)
        gcode.travel(x=start_x, y=track_positions[0], speed_mm_s=TRAVEL_SPEED_MM_S)
        gcode.travel(z=z, speed_mm_s=TRAVEL_SPEED_MM_S)
        for y in track_positions:
            gcode.travel(x=start_x, y=y, speed_mm_s=TRAVEL_SPEED_MM_S)
            gcode.extrude_to(end_x, y, abs(end_x - start_x), track_width, layer_height, PRINT_SPEED_MM_S)
    else:
        low, high = box["wall_y0"] + track_width / 2.0, box["wall_y1"] - track_width / 2.0
        start_y, end_y = (low, high) if positive else (high, low)
        gcode.travel(z=z + WALL_APPROACH_CLEARANCE_MM, speed_mm_s=TRAVEL_SPEED_MM_S)
        gcode.travel(x=track_positions[0], y=start_y, speed_mm_s=TRAVEL_SPEED_MM_S)
        gcode.travel(z=z, speed_mm_s=TRAVEL_SPEED_MM_S)
        for x in track_positions:
            gcode.travel(x=x, y=start_y, speed_mm_s=TRAVEL_SPEED_MM_S)
            gcode.extrude_to(x, end_y, abs(end_y - start_y), track_width, layer_height, PRINT_SPEED_MM_S)


def scan_after_wall_layer(gcode, box, wall_top_z):
    """Move to the nearest scan end, then sweep to the opposite end with no E."""
    if not ENABLE_LAYER_SCAN:
        return

    orientation = WALL_ORIENTATION.lower()
    positive = WALL_PRINT_DIRECTION.lower() == "positive"
    scan_z = wall_top_z + SCAN_Z_LIFT_MM
    gcode.comment("TYPE:SCAN (non-extruding: current position -> near end -> far end)")
    gcode.travel(z=scan_z, speed_mm_s=TRAVEL_SPEED_MM_S)

    if orientation == "x":
        # +X wall printing ends near the right scan boundary; -X ends near left.
        near_x, far_x = (
            (SCAN_X_RIGHTMOST_MM, SCAN_X_LEFTMOST_MM)
            if positive
            else (SCAN_X_LEFTMOST_MM, SCAN_X_RIGHTMOST_MM)
        )
        scan_y = box["center_y"] + SCAN_CROSS_AXIS_OFFSET_MM
        gcode.travel(x=near_x, y=scan_y, speed_mm_s=SCAN_SPEED_MM_S)
        gcode.dwell(SCAN_SETTLE_SECONDS)
        gcode.travel(x=far_x, y=scan_y, speed_mm_s=SCAN_SPEED_MM_S)
    else:
        # +Y wall printing ends near the back scan boundary; -Y ends near front.
        near_y, far_y = (
            (SCAN_Y_BACKMOST_MM, SCAN_Y_FRONTMOST_MM)
            if positive
            else (SCAN_Y_FRONTMOST_MM, SCAN_Y_BACKMOST_MM)
        )
        scan_x = box["center_x"] + SCAN_CROSS_AXIS_OFFSET_MM
        gcode.travel(x=scan_x, y=near_y, speed_mm_s=SCAN_SPEED_MM_S)
        gcode.dwell(SCAN_SETTLE_SECONDS)
        gcode.travel(x=scan_x, y=far_y, speed_mm_s=SCAN_SPEED_MM_S)
    gcode.dwell(SCAN_SETTLE_SECONDS)


def generate_gcode():
    validate_settings()
    box = geometry()
    validate_geometry(box)

    base_layers = make_layers(BASE_SIZE_MM[2], LAYER_HEIGHT_MM)
    wall_layers = make_layers(WALL_SIZE_MM[2], LAYER_HEIGHT_MM)
    wall_track_width = WALL_SIZE_MM[1] / WALL_LAYERS_THICK

    gcode = GCode()
    gcode.comment("Thin wall on rectangular base; generated by thin_wall_gcode.py")
    gcode.comment("Base mm: {}".format(BASE_SIZE_MM))
    gcode.comment("Wall mm [length, thickness, height]: {}".format(WALL_SIZE_MM))
    gcode.comment("Wall orientation: {}; one-way extrusion: {}".format(WALL_ORIENTATION, WALL_PRINT_DIRECTION))
    gcode.comment("Wall tracks: {}; individual track width: {} mm".format(WALL_LAYERS_THICK, fmt(wall_track_width)))
    gcode.comment(
        "Scan boundaries mm: X [{}..{}], Y [{}..{}]".format(
            SCAN_X_LEFTMOST_MM,
            SCAN_X_RIGHTMOST_MM,
            SCAN_Y_FRONTMOST_MM,
            SCAN_Y_BACKMOST_MM,
        )
    )
    gcode.comment(
        "Placement offset mm: [{}, {}]".format(
            PLACEMENT_OFFSET_X_MM,
            PLACEMENT_OFFSET_Y_MM,
        )
    )
    gcode.add("G21 ; millimetres")
    gcode.add("G90 ; absolute X/Y/Z coordinates")
    gcode.add("M83 ; relative extrusion")
    gcode.comment("No G28: printer must already be homed and using these absolute coordinates")
    gcode.add("M140 S{} ; start heating bed".format(BED_TEMPERATURE_C))
    gcode.add("M104 S{} ; start heating nozzle".format(EXTRUDER_TEMPERATURE_C))
    gcode.add("M190 S{} ; wait for bed temperature".format(BED_TEMPERATURE_C))
    gcode.add("M109 S{} ; wait for nozzle temperature".format(EXTRUDER_TEMPERATURE_C))
    gcode.add("G92 E0")

    for index, (z, layer_height) in enumerate(base_layers):
        gcode.comment("LAYER:{} TYPE:BASE".format(index))
        speed = FIRST_LAYER_SPEED_MM_S if index == 0 else PRINT_SPEED_MM_S
        print_base_layer(gcode, box, z, layer_height, index % 2 == 0, speed)

    for index, (relative_z, layer_height) in enumerate(wall_layers):
        top_z = BASE_SIZE_MM[2] + relative_z
        gcode.comment("LAYER:{} TYPE:WALL".format(len(base_layers) + index))
        print_wall_layer(gcode, box, top_z, layer_height, wall_track_width)
        scan_after_wall_layer(gcode, box, top_z)

    gcode.comment("End of print")
    gcode.travel(z=BASE_SIZE_MM[2] + WALL_SIZE_MM[2] + 5.0, speed_mm_s=TRAVEL_SPEED_MM_S)
    gcode.add("M104 S0 ; turn off nozzle")
    gcode.add("M140 S0 ; turn off bed")
    gcode.add("M107 ; turn off fan")
    gcode.add("M84 ; disable motors")
    return "\n".join(gcode.lines) + "\n"


def main():
    gcode = generate_gcode()
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\n") as output:
        output.write(gcode)
    print("Wrote {}".format(OUTPUT_FILE))


if __name__ == "__main__":
    main()
