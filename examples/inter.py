
# See Fisher cavity filter in the ARRL handbook
# Also see Dishal's paper from 1965 on interdigital filters
# for calculating coupling distances, and included as a PDF.

import sys, argparse
import numpy as np
from solid2 import *
from scadtool import openzip

def parse_args():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=formatter_class)
    parser.add_argument('--a', type=int, default=0, help='rod to resonate')
    parser.add_argument('--b', type=int, default=0, help='second rod to resonate')
    parser.add_argument('--rod', type=float, nargs='*', help='rod length (mm)')
    parser.add_argument('--sep', type=float, nargs='*', help='rod separation (mm)')
    parser.add_argument('--tap', type=float, nargs='*', help='tap position (mm)')
    parser.add_argument('--short', type=int, help='short resonantors')
    parser.add_argument('--kij', type=float, nargs='*', help='denormalized kij')
    parser.add_argument('--qe1', type=float, nargs='*', help='denormalized qe1')
    parser.add_argument('--frequency', type=float, default=1296e6, help='center frequency (Hz)')
    parser.add_argument('--notap', action='store_true', help='do not tap resonantors')
    parser.add_argument('--deembed', action='store_true', help='deembed filter')
    return parser.parse_args()


######################################


def sign(value):
    return 2 * bool(value) - 1


def main(): 
    output = sys.argv[0]
    frequency = args.frequency
    rod = np.array(args.rod) * 1000 # mm
    sep = np.array(args.sep) * 1000 # mm
    tap = np.array(args.tap) * 1000 # mm

    eps = 1e-3 # infinitely thin
    mm = 25.4 
    thick = 2  # thickness of aluminum enclosure
    screw = .112 * mm   # (inches) 4-40 screw
    diam = .25 * mm
    boxh = .75 * mm  # short edge
    boxl = 3e8 / frequency / 4 * 1000 # mm
    endsep = boxh if args.deembed else .7 * boxh # for <2% effect (see dishal)
    zo = 138 * np.log10(1.25 * boxh / diam)  # rod impedance
    
    minspace = 1 if frequency > 800e6 else 2
    base_rod = boxl * (.9 if frequency > 800e6 else .95)

    base_tap = 0
    if args.qe1:
        qe1 = np.array(args.qe1)
        base_tap = 2 * boxl / np.pi * np.arcsin(np.sqrt(50 * np.pi / (4 * qe1 * zo)))

    base_sep = 0
    if args.kij:
        kij = np.array(args.kij)
        base_sep = (.91 * diam / boxh - np.log10(kij) - 0.048) * boxh / 1.37

    rod = rod + base_rod
    sep = sep + base_sep
    tap = tap + base_tap

    ###################

    rodpos = np.cumsum(np.hstack((0, sep))) - np.sum(sep) / 2
    boxw = np.sum(sep) + 2 * endsep

    thick = np.array(thick)
    cavity = np.array([ boxw, boxh, boxl ])

    with openzip(sys.argv[0]) as zf:

        #########################
        # enclosure
        #########################

        # tops
        solid = (cube(cavity + 2 * thick, center=True) - 
                 cube(cavity + [ 2, 2, 0 ] * thick, center=True))
        zf.save('box tops-aluminum priority=10', solid)

        # edges
        solid = (cube(cavity + 2 * thick, center=True) - 
                 cube(cavity + [ 0, 2, 2 ] * thick, center=True))
        zf.save('box edges-aluminum priority=10', solid)

        # lids
        solid = (cube(cavity + 2 * thick, center=True) - 
                 cube(cavity + [ 2, 0, 2 ] * thick, center=True))
        zf.save('box lids-aluminum priority=10', solid)

        #########################
        # rods
        #########################

        portnum = 1
        w = cavity[0] / 2
        z = cavity[2] / 2
        rw = 1   # wire diameter

        for i in range(len(rod)):
            screw_length = 2 * z - rod[i] - minspace

            solid = (cylinder(diam / 2, rod[i], center=True) 
                .translateX(rodpos[i]) 
                .translateZ(sign(i % 2) * (z - rod[i] / 2)))
            zf.save(f'rods{i+1}-aluminum priority=10', solid)

            if i == args.a - 1 or i == args.b - 1:
                if not args.notap and (i == 0 or i == len(rod) - 1):
                    h = sign(i % 2) * (z - tap[1 if i else 0])

                    # tap wire
                    wire_length = w - sign(i) * rodpos[i]
                    size = [ wire_length, rw, rw ]
                    solid = (cube(size, center=True) 
                        .translateX(sign(i) * (w - wire_length / 2))
                        .translateZ(h))
                    zf.save(f'tap{portnum}-copper priority=5', solid)

                    # tap port
                    size = [ rw, rw, rw ]
                    solid = (cube(size, center=True) 
                        .translateX(sign(i) * (w - rw / 2))
                        .translateZ(h))
                    zf.save(f'port x {portnum}', solid)
                else:
                    # probe port
                    size = [ screw, eps, minspace ]
                    solid = (cube(size, center=True) 
                        .translateX(rodpos[i]) 
                        .translateZ(sign(i % 2) * (z - rod[i] - minspace / 2)))
                    zf.save(f'port z {portnum}', solid)

                portnum += 1

            elif args.short is not None and i >= args.short:
                screw_length = 2 * z - rod[i]

            solid = (cylinder(screw/2, screw_length, center=True)
                .translateX(rodpos[i])
                .translateZ(sign(i % 2) * (screw_length / 2 - z)))
            zf.save(f'screw{i+1}-aluminum priority=10', solid)

        
if __name__ == "__main__":
    args = parse_args()
    main()
  
 
