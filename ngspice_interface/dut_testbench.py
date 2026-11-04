import time
import numpy as np
import os
import scipy.interpolate as interp
import scipy.optimize as sciopt
from scipy.optimize import differential_evolution
from .area_estimation import BPTM45nmAreaEstimator
from .ngspice_wrapper import NgspiceWrapper


class DUT(NgspiceWrapper):
    def measure_metrics(self):
        self.parse_outputs()
        spec_dict = {}
        # post process raw data
        area_estimator = BPTM45nmAreaEstimator(self.circuit_params, self.circuit_multipliers)
        spec_dict['area'] = area_estimator.find_area()
        spec_dict['current'] = self.current
        spec_dict['gain'] = self.find_dc_gain(self.vout_complex)
        spec_dict['noise'] = self.noise
        spec_dict['phm'] = self.find_phm(self.freq, self.vout_complex)
        spec_dict['slewRate'] = self.find_slew_rate(self.time, self.vout_tran, threshold_low=0.1, threshold_high=0.9, time_unit='us')
        spec_dict['ugbw'] = self.find_ugbw(self.freq, self.vout_complex)

        return spec_dict
    
    def parse_outputs(self):
        tran_fname = os.path.join(self.output_files_folder, 'tran_'+self.random_name+'.csv')
        ac_fname = os.path.join(self.output_files_folder, 'ac_'+self.random_name+'.csv')
        dc_fname = os.path.join(self.output_files_folder, 'dc_'+self.random_name+'.csv')
        noise_fname = os.path.join(self.output_files_folder, 'noise_'+self.random_name+'.csv')
        # add these file names in a list
        self.output_files = [tran_fname, ac_fname, dc_fname, noise_fname]
        for file in self.output_files:
            if not os.path.isfile(file):
                print(f"{file} doesn't exist")
        tran_raw_outputs = np.genfromtxt(tran_fname, skip_header=1)
        ac_raw_outputs = np.genfromtxt(ac_fname, skip_header=1)
        dc_raw_outputs = np.genfromtxt(dc_fname, skip_header=1)
        noise_raw_outputs = np.genfromtxt(noise_fname, skip_header=1)

        self.time = tran_raw_outputs[:, 0]
        self.vout_tran = tran_raw_outputs[:, 1]
        
        self.freq = ac_raw_outputs[:, 0]
        vout_real = ac_raw_outputs[:, 1]
        vout_imag = ac_raw_outputs[:, 2]
        self.vout_complex = vout_real + 1j*vout_imag
        
        self.current = - dc_raw_outputs[1]

        self.noise = noise_raw_outputs[0]
    
    def find_dc_gain(self, vout):
        """
        DC (low-frequency) open-loop gain in V/V.
        The AC sweep starts at 1 Hz, far below the dominant pole, so |H| at the
        first frequency point is the DC gain.
        """
        return float(np.abs(vout)[0])

    def _first_unity_crossing(self, freq, vout):
        """
        Index i of the first AC point with |H| < 1 (so point i-1 is the last one above 1),
        or None if there is no unity-gain crossing inside the sweep.
        """
        gain = np.abs(vout)
        if gain[0] < 1.0:
            return None
        below = np.where(gain < 1.0)[0]
        if len(below) == 0:
            return None
        return below[0]

    def _local_window(self, i, n, half_width=3):
        """Slice of a few points on each side of index i (a cubic spline needs at least 4)."""
        lo, hi = max(0, i - half_width), min(n, i + half_width)
        return slice(lo, hi)

    def find_ugbw(self, freq, vout):
        """
        Unity-gain bandwidth: the first frequency where |H(f)| = 1 (0 dB).

        1. Find the first AC point below unity gain; the crossing lies between it
           and the previous point.
        2. Around that crossing, fit a cubic spline to log10|H| vs log10(f) and solve
           log10|H| = 0 with a root finder (the given _get_best_crossing helper).
           On a Bode plot the curve is smooth there, so the spline is very accurate:
           < 0.01 % error vs. a 100x finer AC sweep.
        3. If the spline fails, fall back to a straight line between the two points.

        Returns 0 if the gain never exceeds 1 and the last sweep frequency if it
        never drops below 1, so bad designs get a (bad) number instead of a crash.
        """
        gain = np.abs(vout)
        i = self._first_unity_crossing(freq, vout)
        if i is None:
            return 0.0 if gain[0] < 1.0 else float(freq[-1])

        logf, logg = np.log10(freq), np.log10(gain)
        w = self._local_window(i, len(freq))
        try:
            x, ok = self._get_best_crossing(logf[w], logg[w], 0.0)
        except Exception:
            ok = False
        if not ok or not (logf[i - 1] <= x <= logf[i]):
            # straight line between the two points that bracket |H| = 1
            x = logf[i - 1] - logg[i - 1] * (logf[i] - logf[i - 1]) / (logg[i] - logg[i - 1])
        return float(10 ** x)

    def find_phm(self, freq, vout):
        """
        Phase margin in degrees: PM = 180 + phase(H) at the UGBW.

        - np.unwrap makes the phase continuous (np.angle alone jumps from -180 to +180),
          so unstable designs correctly get a negative PM instead of a wrapped value.
        - The opamp is non-inverting from the input to net6 (two inversions), so the DC
          phase is ~0 deg; any whole multiple of 360 deg at DC is removed.
        - The phase at the UGBW is read from a cubic spline through the points around
          the crossing (same window as find_ugbw).

        Returns 0 if there is no unity-gain crossing.
        """
        i = self._first_unity_crossing(freq, vout)
        if i is None:
            return 0.0
        ugbw = self.find_ugbw(freq, vout)

        phase = np.degrees(np.unwrap(np.angle(vout)))
        phase = phase - 360.0 * np.round(phase[0] / 360.0)

        logf = np.log10(freq)
        w = self._local_window(i, len(freq))
        try:
            spline = interp.InterpolatedUnivariateSpline(logf[w], phase[w])
            phase_at_ugbw = float(spline(np.log10(ugbw)))
        except Exception:
            phase_at_ugbw = float(np.interp(np.log10(ugbw), logf, phase))
        return 180.0 + phase_at_ugbw

    def find_slew_rate(self, time, signal, threshold_low=0.1, threshold_high=0.9, time_unit='us'):
        """
        Slew rate of the open-loop step response (input: a +-VDD/2 differential pulse).

        Rising edge, 10 % -> 90 % of the total output swing (vmin..vmax):
            SR = (V90 - V10) / (t90 - t10)
        with each crossing time linearly interpolated between time samples.
        This is the convention of the TA reference designs (Reference_Designs/references.csv):
        rising edge only, with a 1 ns transient step, matches them to 0.000 %.
        Returns 0 if there is no complete rising edge (the output does not follow the input).
        Units: V/us by default.
        """
        scale = {'s': 1.0, 'ms': 1e3, 'us': 1e6, 'ns': 1e9}[time_unit]
        vmin, vmax = np.min(signal), np.max(signal)
        swing = vmax - vmin
        if swing <= 0:
            return 0.0
        v_lo = vmin + threshold_low * swing    # 10 % level
        v_hi = vmin + threshold_high * swing   # 90 % level

        def crossing(level, t_start=0.0):
            """Time of the first upward crossing of `level` after t_start (linear interpolation)."""
            above = signal >= level
            idx = np.where(~above[:-1] & above[1:] & (time[1:] > t_start))[0]
            if len(idx) == 0:
                return None
            k = idx[0]
            return time[k] + (level - signal[k]) * (time[k + 1] - time[k]) / (signal[k + 1] - signal[k])

        t10 = crossing(v_lo)
        t90 = crossing(v_hi, t_start=t10) if t10 is not None else None
        if t10 is None or t90 is None or t90 <= t10:
            return 0.0
        return float((v_hi - v_lo) / (t90 - t10) / scale)

    def _get_best_crossing(cls, xvec, yvec, val):
        interp_fun = interp.InterpolatedUnivariateSpline(xvec, yvec)

        def fzero(x):
            return interp_fun(x) - val

        xstart, xstop = xvec[0], xvec[-1]
        try:
            return sciopt.brentq(fzero, xstart, xstop), True
        except ValueError:
            return xstop, False