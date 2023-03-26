
import sys, os
from pylab import *

#* theta   : theta angles
#* phi     : phi angles
#* r       : radius
#* freq    : frequencies
#* Dmax    : directivity over frequency
#* Prad    : total radiated power over frequency
#* E_theta : theta component of electric field over frequency/theta/phi
#* E_phi   : phi   component of electric field over frequency/theta/phi
#* E_norm  : abs   component of electric field over frequency/theta/phi
#* E_cprh  : theta component of electric field over frequency/theta/phi
#* E_cplh  : theta component of electric field over frequency/theta/phi
#* P_rad   : radiated power (S) over frequency/theta/phi

class loadz(object):
    def __init__(self, filename):
        root, ext = os.path.splitext(filename)
        if ext != f'.npz':
            filename = f'{root}.npz'
        with np.load(filename) as my_dict:
            for key in my_dict:
                 setattr(self, key, my_dict[key])


def plot_sparameters(f, s):
    figure()
    nport = s.shape[1]
    for n in range(nport):
        if np.all(s[:,:,n] == 0): continue
        sdb = 20 * np.log10(abs(s[:,:,n]))
        plot(f/1e9, sdb[:,0], 'k-', linewidth=2, label=f'$S_{{1{n+1}}}$')
        if nport > 1: 
            plot(f/1e9, sdb[:,1], 'r--', linewidth=2, label=f'$S_{{2{n+1}}}$')
        grid()
        legend()
        ylabel('S-Parameter (dB)')
        xlabel('frequency (GHz)')


def plot_pattern(phi, theta, E, Dmax, name):
    phi = phi * 180 / np.pi
    theta = theta * 180 / np.pi
    xz = np.where(isclose(phi, 0))[0]
    yz = np.where(isclose(phi, 90))[0]
    E = 20.0 * np.log10(abs(E) / np.max(abs(E)) * Dmax)
    figure()
    plot(theta, np.squeeze(E[:,xz]), 'k-', linewidth=2, label='xz-plane')
    plot(theta, np.squeeze(E[:,yz]), 'r--', linewidth=2, label='yz-plane')
    grid()
    ylabel('Directivity (dBi)')
    xlabel('Theta (deg)')
    title(name)
    legend()


def main(filename):
    res = loadz(filename)

    f = res.f
    s = res.s
    z = res.z
    plot_sparameters(f, s)

    if hasattr(res, 'Dmax'):
        phi = res.phi
        theta = res.theta
        freq = res.freq[0]
        Dmax = res.Dmax[0]
        E_norm = res.E_norm[0]
        E_theta = res.E_theta[0]
        E_phi = res.E_phi[0]

        # Calculate co- and cross-pol, Modern Antenna Design, p.22
        E_co = E_theta * np.cos(phi) - E_phi * np.sin(phi)
        E_cx = E_theta * np.sin(phi) + E_phi * np.cos(phi)

        name = f'{freq/1e6:.3f} MHz'
        plot_pattern(phi=phi, theta=theta, E=E_norm, Dmax=Dmax, name=f'E norm at {name}')
        plot_pattern(phi=phi, theta=theta, E=E_cx, Dmax=Dmax, name=f'E cross-pol at {name}')

    show()


if __name__ == "__main__":    
    main(sys.argv[1])


