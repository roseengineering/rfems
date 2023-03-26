
from openEMS.physical_constants import *
import sys
from solid2 import *
from scadtool import openzip

def main():
    eps = 1e-3
    substrate_x = 60
    substrate_y = 60
    substrate_thickness = 1.524
    patch_x = 32
    patch_y = 40
    patch_z = .035
    feed_x = -6
    substrate_epsR = 3.38
    substrate_kappa = 1e-3 * 2 * np.pi * 2.45e9 * EPS0 * substrate_epsR

    with openzip(sys.argv[0]) as zf:
        # air
        size = [200, 200, 200]
        solid = cube(size, center=True)
        zf.save('sim_box-air', solid)

        # patch
        size = [ patch_x, patch_y, eps ]
        solid = cube(size, center=True).translateZ(substrate_thickness / 2)
        zf.save('patch-pec priority=10', solid)

        # ground
        size = [ substrate_x, substrate_y, eps ]
        solid = cube(size, center=True).translateZ(-substrate_thickness / 2)
        zf.save('ground-pec priority=10', solid)

        # substrate
        size = [ substrate_x, substrate_y, substrate_thickness ]
        solid = cube(size, center=True)
        zf.save(f'substrate-epsilon={substrate_epsR:g} kappa={substrate_kappa:g}', solid)

        # port
        size = [ eps, eps, substrate_thickness ]
        solid = cube(size, center=True).translateX(feed_x)
        zf.save(f'port z 1', solid)


if __name__ == "__main__":
    main()






