"""Cheaper simulations and analyses (optional task 2).

A full simulation of TwoStage.cir runs four analyses: a 30 us transient (~98 % of the
time, only for the slew rate), AC (gain, UGBW, PM), noise and the DC operating point
(current, transistor data). QuickDUT runs any SUBSET of them on a design, optionally at
another PVT corner, with a SHORT transient:

    analysis  time      gives
    op        ~0.01 s   current, transistor operating point (Id, gm, gds, Vgs, Vth, Vds, Vdsat)
    ac        ~0.01 s   gain, UGBW, phase margin
    noise     ~0.01 s   output noise
    tran      ~0.1 s    slew rate, from a 5 us transient (first rising edge only)
    area      0 s       always, from the sizes (no simulation)

The quick netlist is generated from TwoStage.cir on every run (make_quick_netlist): the
circuit part is copied unchanged, only the .control block keeps the selected analyses and
their wrdata lines. So the quick and the full simulation always describe the same circuit,
and the specs are measured with the same DUT functions (find_dc_gain, find_ugbw, ...).
"""
import os
import re
import time

import numpy as np

from .area_estimation import BPTM45nmAreaEstimator
from .dut_testbench import DUT
from .op_data import read_op_data

ANALYSES = ("op", "ac", "noise", "tran")          # canonical order
SPECS_BY_ANALYSIS = {"op": ("current",), "ac": ("gain", "phm", "ugbw"),
                     "noise": ("noise",), "tran": ("slewRate",)}
# The input pulse rises at 0.5..1.0 us and falls at 5.5 us; the slew rate is measured on
# the first rising edge, so 5 us contains everything find_slew_rate needs.
SHORT_TRAN_STOP = "5u"


def make_quick_netlist(text, analyses, tran_stop=SHORT_TRAN_STOP):
    """Netlist text that runs only `analyses` (subset of ANALYSES).

    Everything outside .control ... .endc is copied unchanged. Inside, each analysis line
    keeps the wrdata lines that follow it; analyses not selected are dropped with their
    wrdata lines; the transient stop time becomes tran_stop.
    """
    unknown = set(analyses) - set(ANALYSES)
    if unknown or not analyses:
        raise ValueError(f"analyses must be a non-empty subset of {ANALYSES}, got {list(analyses)}")
    head, sep, rest = text.partition(".control")
    body, sep2, tail = rest.partition(".endc")
    if not sep or not sep2:
        raise ValueError("netlist has no .control ... .endc block")
    lines, owner, found = [], None, set()
    for line in body.splitlines():
        words = line.split()
        word = words[0].lower() if words else ""
        if word in ANALYSES:
            owner = word
            found.add(word)
            if word in analyses:
                if word == "tran":           # tran <step> <stop> [...]
                    words[2] = tran_stop
                    line = " ".join(words)
                lines.append(line)
        elif word == "wrdata":
            if owner in analyses:
                lines.append(line)
        elif word == "run" or word.startswith("*"):
            continue                         # no analyses outside .control; comments
        else:
            lines.append(line)               # set / option lines
    missing = set(analyses) - found
    if missing:
        raise ValueError(f"netlist has no {sorted(missing)} analysis")
    return head + ".control\n" + "\n".join(l for l in lines if l.strip()) + "\n.endc" + tail


class QuickDUT(DUT):
    """DUT that runs a subset of the analyses of the circuit's netlist (see module doc)."""

    def __init__(self, yaml_path, template_dir):
        super().__init__(yaml_path)
        self.full_netlist_path = self.netlist_path
        self.template_dir = template_dir

    def run(self, params, analyses, process="TT", temp=27, vdd=1.2, tran_stop=SHORT_TRAN_STOP):
        """Simulate `params` with only `analyses` at one PVT corner.

        Returns (specs, op, ngspice_seconds): specs has 'area' plus the specs the selected
        analyses measure (SPECS_BY_ANALYSIS); op is read_op_data output (None without 'op').
        Raises RuntimeError if ngspice fails or an output file is missing.
        """
        analyses = tuple(a for a in ANALYSES if a in analyses)
        # Regenerated every time: clean.sh may empty no_backup/ during a run.
        os.makedirs(self.template_dir, exist_ok=True)
        template = os.path.join(self.template_dir, f"{self.circuit_name}_quick_{'_'.join(analyses)}.cir")
        with open(self.full_netlist_path) as f:
            text = f.read()
        with open(template, "w") as f:
            f.write(make_quick_netlist(text, analyses, tran_stop))
        self.netlist_path = template
        try:
            path = self.create_new_netlist(params, process=process, temp_pvt=temp, vdd=vdd)
        finally:
            self.netlist_path = self.full_netlist_path
        t0 = time.time()
        if self.simulate(path) != 0:
            raise RuntimeError("ngspice failed or timed out")
        seconds = time.time() - t0

        def data(prefix):
            fname = os.path.join(self.output_files_folder, f"{prefix}_{self.random_name}.csv")
            if not os.path.isfile(fname):
                raise RuntimeError(f"ngspice wrote no {prefix} output")
            return np.genfromtxt(fname, skip_header=1)

        # same parsing and measurement code as DUT.parse_outputs / DUT.measure_metrics
        specs = {"area": float(BPTM45nmAreaEstimator(params, self.circuit_multipliers).find_area())}
        if "op" in analyses:
            specs["current"] = float(-data("dc")[1])
        if "ac" in analyses:
            raw = data("ac")
            freq, vout = raw[:, 0], raw[:, 1] + 1j * raw[:, 2]
            specs["gain"] = self.find_dc_gain(vout)
            specs["phm"] = self.find_phm(freq, vout)
            specs["ugbw"] = self.find_ugbw(freq, vout)
        if "noise" in analyses:
            specs["noise"] = float(data("noise")[0])
        if "tran" in analyses:
            raw = data("tran")
            specs["slewRate"] = self.find_slew_rate(raw[:, 0], raw[:, 1], threshold_low=0.1,
                                                    threshold_high=0.9, time_unit="us")
        op = read_op_data(self) if "op" in analyses else None
        return {k: float(v) for k, v in specs.items()}, op, seconds


def model_processes(model_dir):
    """Process corners that have a model file, e.g. ('FF', 'SS', 'TT') for p045_<corner>.sp."""
    names = [re.match(r"\w+?_(\w+)\.sp$", f) for f in sorted(os.listdir(model_dir))]
    return tuple(m.group(1) for m in names if m)
