
import numpy as np
import zipfile, tempfile, os, sys, argparse, platform, struct
from openEMS.physical_constants import C0
from openEMS import openEMS
from CSXCAD import ContinuousStructure

STL_TOL = .001  # mm
STL_UNIT = 1e-3

DEFAULT_PITCH = 1e-3
DEFAULT_POINTS = 1000  # even to ensure group delay calculation
DEFAULT_REFERENCE = 50
DEFAULT_PRIORITY = 0
DEFAULT_DPHI = 2
DEFAULT_DTHETA = 2

MATERIALS = {  # s/m
    'silver':   { "kappa": 62.1e6 },  
    'copper':   { "kappa": 58.7e6 },
    'gold':     { "kappa": 44.2e6 },
    'aluminum': { "kappa": 36.9e6 },
    'brass':    { "kappa": 15.9e6 },
    'steel':    { "kappa": 10.1e6 },
}

COLORS = {
    "pec":      "#dbc7b8",
    "silver":   "#c0c0c0",
    "copper":   "#e6be8a",
    "gold":     "#ffd700",
    "aluminum": "#d0d5d9",
    "brass":    "#ac9f3c",
    "steel":    "#888b8d",
}


def parse_args():
    formatter_class = argparse.ArgumentDefaultsHelpFormatter
    parser = argparse.ArgumentParser(formatter_class=formatter_class)
    parser.add_argument('input_filename', nargs=1,
        help='input zip file of STL models')
    parser.add_argument('output_filename', nargs='?',
        help='s-parameter and farfield .npz output file')

    parser.add_argument('--pitch', type=float, default=DEFAULT_PITCH,
        help='length of a uniform yee cell side (m)')
    parser.add_argument('--frequency', type=float, metavar='FREQ',
        help='center simulation frequency (Hz)')
    parser.add_argument('--span', type=float, 
        help='simulation span, -20dB passband ends (Hz)')
    parser.add_argument('--points', type=int, default=DEFAULT_POINTS,
        help='measurement frequency points, set to 1 for center frequency')
    parser.add_argument('--start', type=int,
        help='first port to excite, starting from 1')
    parser.add_argument('--stop', type=int,
        help='last port to excite, starting from 1')
    parser.add_argument('--line', type=float, default=DEFAULT_REFERENCE,
        help='default characteristic impedance of ports')

    pat_group = parser.add_argument_group("farfield options")
    pat_group.add_argument('--farfield', action='store_true', 
        help='generate free-space farfield radiation patterns')
    pat_group.add_argument('--dphi', type=float, default=DEFAULT_DPHI,
        help='azimuth increment (degree)')
    pat_group.add_argument('--dtheta', type=float, default=DEFAULT_DTHETA,
        help='elevation increment (degree)')
    pat_group.add_argument('--nominimum', action='store_true', 
        help='do not find frequency of least VWSR')

    sim_group = parser.add_argument_group("openems options")
    sim_group.add_argument('--criteria', type=float,
        help='end criteria, eg -60 (dB)')
    sim_group.add_argument('--average', action='store_true', 
        help='use cell material averaging')
    sim_group.add_argument('--verbose', type=int, default=0,
        help='openems verbose setting')
    sim_group.add_argument('--threads', type=int, default=0,
        help='number of threads to use, 0 for all')

    debug_group = parser.add_argument_group("debugging options")
    debug_group.add_argument('--show-model', action='store_true', 
        help='run AppCSXCAD on input model, no simulation')
    debug_group.add_argument('--dump-pec', action='store_true', 
        help='generate PEC dump file and run ParaView on it')

    return parser.parse_args()


def value_error(message):
    print(f'ERROR: {message}.')
    sys.exit(1)


def parse_stl(filename):
    data = []
    with open(filename, 'rb') as fp:
        header = fp.read(5)
        if header == b'solid':
            facet = [] 
            for ln in fp:
                d = ln.split()
                if d[0] == b'endfacet' and facet:
                    data.append(np.array(facet))
                    facet = []
                if d[0] == b'vertex' and len(d) == 4:
                    facet.append([ float(x) for x in d[1:] ])
        else:
            raise ValueError('binary stl files unsupported: not enough precision')
    return data


def model_bbox(data):
    start = None
    stop = None
    for facet in data:
        for v in facet:
            start = v if start is None else np.minimum(v, start) 
            stop = v if stop is None else np.maximum(v, stop)
    return start, stop                 


def unzip_models(filename, dirname):
    root, ext = os.path.splitext(filename)
    if ext != '.zip':
        filename = f'{root}.zip'
    zf = zipfile.ZipFile(filename)
    data = {}
    for info in zf.infolist():
        if not info.is_dir():
            root, ext = os.path.splitext(info.filename)
            if ext == '.stl':
                name = os.path.basename(root)
                path = zf.extract(info, dirname)
                data[name] = path
            else:
                print(f'WARNING: ignoring {info.filename}, only .stl files allowed')
    return data


def get_material(name):
    return name.split('-')[-1].strip().lower()


def get_portdir(name):
    name = get_material(name)
    data = name.split()
    for d in data:
        if d == 'x': return 0
        if d == 'y': return 1
        if d == 'z': return 2
    value_error('No port direction provided in port name')
    

def get_zo(name):
    data = get_material(name).split()
    for d in data:
        key, _, value = d.partition('=')
        if key == 'zo': return int(value)
    return args.line


def get_priority(name):
    data = get_material(name).split()
    for d in data:
        key, _, value = d.partition('=')
        if key == 'priority': return int(value)
    return DEFAULT_PRIORITY


def get_custom_material(name):
    data = get_material(name).split()
    options = {}
    for d in data:
        key, _, value = d.partition('=')
        if key == 'epsilon': options['epsilon'] = float(value)
        if key == 'kappa': options['kappa'] = float(value)
    return options


def toint(s):
    try:
        return int(s)
    except ValueError:
        pass


def is_port(name):
    data = get_material(name).split()
    return data and data[0] == 'port'


def get_portnum(name):
    data = get_material(name).split()
    for d in data:
        n = toint(d)
        if n is None:
            continue
        if n <= 0: 
            value_error('Port number must be 1 or greater')
        return n
    value_error('No port number provided')


def get_simports(models):
    port_models = [ k for k in models.keys() if is_port(k) ]
    portnum = sorted([ get_portnum(k) for k in port_models ])
    nport = len(port_models)
    if nport == 0:
        print('WARNING: No ports provided')
    if portnum != list(range(1, nport + 1)):
        value_error('Ports must be numbered consecutive')
    port_start = max(0, args.start-1) if args.start else 0
    port_stop = port_start + 1 if args.stop is None else args.stop
    port_stop = nport if port_stop == 0 else min(port_stop, nport) 
    port_stop = max(port_stop, port_start + 1)
    return port_start, port_stop, nport


def frequency_sweep():
    frequency = args.frequency
    span = args.span
    if frequency:
        span = span or frequency
    elif span:
        frequency = frequency or span
    elif args.show_model or args.dump_pec:
        frequency = span = 1
    else:
        value_error('Either frequency span or center frequency must be set')
    return frequency, span


def setup_simulation(CSX):
    average = args.average
    fo, span = frequency_sweep()
    kw = {}
    if args.criteria:
        kw['EndCriteria'] = 10 ** (args.criteria / 10)
    if args.dump_pec:
        kw['NrTS'] = 0
    FDTD = openEMS(CellConstantMaterial=not average, **kw) 
    FDTD.SetGaussExcite(fo, span / 2)
    boundary = [ 'MUR' if args.farfield else 'PEC' ] * 6
    FDTD.SetBoundaryCond(boundary)
    FDTD.SetCSX(CSX)
    return FDTD


def get_frequencies():
    points = args.points
    fo, span = frequency_sweep()
    if points == 1:
        f = np.array([ fo ])
    else:
        f = np.linspace(fo - span / 2, fo + span / 2, points)
    return f


def run_appcsxcad(CSX, sim_path):
    os.mkdir(sim_path)
    CSX_file = os.path.join(sim_path, 'model.xml')
    CSX.Write2XML(CSX_file)
    os.system('AppCSXCAD "{}"'.format(CSX_file))
    sys.exit(0)


def run_paraview():
    os.system('paraview "PEC_dump.vtp"')
    sys.exit(0)


def run_simulation(FDTD, sim_path):
    threads = max(0, args.threads)
    verbose = args.verbose
    dump_pec = args.dump_pec
    FDTD.Run(sim_path, verbose=verbose, numThreads=threads, debug_pec=dump_pec)


def calc_sparameters(ports, s, n):
    for m in range(len(ports)):
        s[:,m,n] = ports[m].uf_ref / ports[n].uf_inc


def calc_radiation(sim_path, s, n, nf2ff):
    dphi = args.dphi
    dtheta = args.dtheta
    theta = np.arange(-180.0, 180.0, dtheta)
    phi = np.arange(0, 180, dphi)
    frequency = get_frequencies()
    if not args.nominimum:
        ix = np.argmin(np.abs(s[:,n,n]))
        frequency = frequency[ix] or frequency_sweep()[0]
    res = nf2ff.CalcNF2FF(sim_path, frequency, theta, phi)
    res = dict(res.__dict__)
    return res


def save_results(filename, f, s, z, ff):
    root, ext = os.path.splitext(filename)
    if ext != '.npz':
        filename = f'{root}.npz'
    np.savez(filename, f=f, s=s, z=z, **ff)


def is_applesilicon():
    return platform.system() == 'Darwin' and platform.processor() == 'arm'


#####################

def add_parts(CSX, models): 
    pitch = args.pitch
    mesh = CSX.GetGrid()
    mesh.SetDeltaUnit(STL_UNIT)
    bbox = [ None, None ]
    for name in sorted([ k for k in models.keys() if not is_port(k) ]):
        material = get_material(name)
        priority = get_priority(name)
        start, stop = model_bbox(parse_stl(models[name]))

        # handle <3d surfaces
        ix = np.logical_or(stop - start < STL_TOL, np.isclose(stop - start, STL_TOL))
        start[ix] = stop[ix] = ((start + stop) / 2)[ix]

        bbox[0] = start if bbox[0] is None else np.minimum(bbox[0], start)
        bbox[1] = stop if bbox[1] is None else np.maximum(bbox[1], stop)
        tag = material.split()[0]
        if tag == 'air':
            continue
        if args.dump_pec:
            options = None
        elif tag in MATERIALS:
            options = MATERIALS[tag]
        else:
            options = get_custom_material(material)
        if options:
            mat = CSX.AddMaterial(name, **options)
        else:
            mat = CSX.AddMetal(name) # pec
        if tag in COLORS:
            mat.SetColor(COLORS[tag])
        for n in range(3):
            mesh.AddLine('xyz'[n], [ start[n], stop[n] ])

        if np.any(np.isclose(stop - start, 0)):
            prim = mat.AddBox(start, stop, priority=priority)
        else:
            prim = mat.AddPolyhedronReader(models[name], priority=priority)
            prim.ReadFile()

    bbox = np.array(bbox).T
    mesh.AddLine('x', bbox[0])
    mesh.AddLine('y', bbox[1])
    mesh.AddLine('z', bbox[2])
    return mesh


def add_ports(FDTD, mesh, models, n):
    port = []
    ports = [ name for name in models.keys() if is_port(name) ]
    for name in sorted(ports, key=get_portnum):
        priority = get_priority(name)
        zo = get_zo(name)
        port_nr = get_portnum(name)
        p_dir = get_portdir(name)
        excite = (port_nr == n + 1)
        edges2grid = [ 'yz', 'xz', 'xy' ][p_dir]
        start, stop = model_bbox(parse_stl(models[name]))

        # handle <3d surfaces
        ix = np.logical_or(stop - start < STL_TOL, np.isclose(stop - start, STL_TOL))
        start[ix] = stop[ix] = ((start + stop) / 2)[ix]

        p = FDTD.AddLumpedPort(port_nr=port_nr, R=zo, start=start, stop=stop,
            p_dir=p_dir, excite=excite, priority=priority, edges2grid=edges2grid)
        port.append(p)
        for n in range(3):
            mesh.AddLine('xyz'[n], [ start[n], stop[n] ])

    return port


def smooth_mesh(mesh):
    pitch = args.pitch
    mesh.SmoothMeshLines('all', pitch / STL_UNIT)


def main():
    input_filename = os.path.abspath(args.input_filename[0])
    output_filename = os.path.abspath(args.output_filename or input_filename)
    line = args.line

    with tempfile.TemporaryDirectory() as tempdir:
        tempdir = os.path.realpath(tempdir)
        mod_path = os.path.join(tempdir, 'mod')
        sim_path = os.path.join(tempdir, 'sim')
        models = unzip_models(input_filename, mod_path)
        port_start, port_stop, nport = get_simports(models)
        frequency = get_frequencies()
        s = np.zeros((len(frequency), nport, nport), dtype=np.complex128)
        ff = {}

        if args.farfield or is_applesilicon():
            if port_stop - port_start > 1:
                value_error('Only one port can be simulated with farfield or apple silicon')

        for n in range(port_start, port_stop):
            CSX = ContinuousStructure()
            FDTD = setup_simulation(CSX)
            mesh = add_parts(CSX, models)
            ports = add_ports(FDTD, mesh, models, n)
            smooth_mesh(mesh)

            if args.farfield:
                nf2ff = FDTD.CreateNF2FFBox()
            if args.show_model:
                run_appcsxcad(CSX, sim_path)
            run_simulation(FDTD, sim_path)
            if args.dump_pec:
                run_paraview()
            for p in ports:
                p.CalcPort(sim_path, frequency)
            calc_sparameters(ports, s, n)
            if args.farfield:
                ff = calc_radiation(sim_path, s, n, nf2ff)

    save_results(output_filename, f=frequency, s=s, z=line, ff=ff)
    if is_applesilicon():
        os.kill(os.getpid(), 9)


if __name__ == '__main__':
    args = parse_args()
    main()


