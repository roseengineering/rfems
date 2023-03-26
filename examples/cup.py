
import sys
from solid2 import *
from scadtool import openzip

def main(): 
    fo = 1296e6
    wavelen = 3e8 / fo * 1000

    diam = 2
    dipole_length = 0.9 * wavelen / 2
    cup_height =   0.5 * wavelen  # 0.5 to 0.6
    cup_diameter = 1.1 * wavelen  # 1.1 to 1.4
    cup_thickness = 8
    cup_bottom = -wavelen / 4
    sim_side = 4.2e11 / fo + cup_diameter

    with openzip(sys.argv[0]) as zf:
        # air
        size = [sim_side] * 3
        solid = cube(size, center=True)
        zf.save('sim_box-air', solid)

        # dipole
        size = [ dipole_length, diam, diam ]
        solid = cube(size, center=True)
        zf.save('dipole-copper', solid)

        # cup rim
        inner = cylinder(cup_diameter/2, h=cup_height) \
            .translateZ(cup_bottom)
        outer = cylinder(cup_diameter/2 + cup_thickness, h=cup_height) \
            .translateZ(cup_bottom)
        zf.save('cup rim-aluminum', outer - inner)

        # cup bottom
        solid = cylinder(cup_diameter/2 + cup_thickness, h=cup_thickness) \
            .translateZ(cup_bottom - cup_thickness)
        zf.save('cup bottom-aluminum', solid)
        
        # port
        size = [ diam ] * 3
        solid = cube(size, center=True)
        zf.save(f'port x 1', solid)


if __name__ == "__main__":
    main()





























