"""
Unit tests for the DUT class (ngspice_interface/dut_testbench.py).

Put this file directly in the CAD/ folder and run, from CAD/:
    python -m unittest test_dut -v
or press the run button on this file in VS Code.

DUT inherits from NgspiceWrapper, so it has create_new_netlist(), simulate()
and measure_metrics() (which uses parse_outputs() + your find_* functions).
"""
import os
import random
import re
import subprocess
import unittest

import numpy as np
import yaml

# NgspiceWrapper builds every path from os.getcwd(), so always run from CAD/
CAD_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(CAD_DIR)

from ngspice_interface import DUT  # noqa: E402  (import after chdir on purpose)
from ngspice_interface.ngspice_wrapper import NGSPICE_BIN  # noqa: E402

YAML_PATH = os.path.join(CAD_DIR, "ngspice_interface", "files", "yaml_files", "TwoStage.yaml")
REFERENCE_CSV = os.path.join(CAD_DIR, "reference_designs.csv")  # given later by the TAs
REL_TOL = 0.05  # allowed relative difference vs. the reference measurements (5 %)

# Example sizing (same as the __main__ block of ngspice_wrapper.py)
PARAMS = {
    "mp1": 10, "wp1": 5.0e-07, "lp1": 100.0e-09,
    "mn1": 10, "wn1": 5.0e-07, "ln1": 100.0e-09,
    "mp3": 10, "wp3": 5.0e-07, "lp3": 100.0e-09,
    "mn3": 10, "wn3": 5.0e-07, "ln3": 100.0e-09,
    "mn4": 10, "wn4": 5.0e-07, "ln4": 100.0e-09,
    "mn5": 10, "wn5": 5.0e-07, "ln5": 100.0e-09,
    "cap": 5.0e-12, "res": 5.0e+3,
}
SPECS = ["area", "current", "gain", "noise", "phm", "slewRate", "ugbw"]


class TestDUT(unittest.TestCase):

    def setUp(self):
        self.dut = DUT(YAML_PATH)

    def simulate(self, params=PARAMS, process="TT", temp=None, vdd=None):
        """Create a netlist with these sizes, run ngspice, return the netlist path."""
        netlist = self.dut.create_new_netlist(params, process, temp, vdd)
        info = self.dut.simulate(netlist)
        self.assertEqual(info, 0, f"ngspice failed on {netlist}")
        return netlist

    # --- 0. environment -------------------------------------------------------
    def test_0_path_has_no_spaces(self):
        self.assertNotIn(" ", CAD_DIR,
                         "ngspice can't handle spaces in paths - move/rename the CAD folder")

    # --- 1. netlist generation ----------------------------------------------
    def test_1_netlist_is_created_with_new_params(self):
        netlist = self.dut.create_new_netlist(PARAMS, "TT")
        self.assertTrue(os.path.isfile(netlist))
        text = open(netlist).read()
        self.assertIn("mp1=10", text)
        self.assertIn("cap=5e-12", text)

    # --- 2. simulation -------------------------------------------------------
    def test_2_simulation_runs(self):
        self.simulate()

    def test_3_output_files_exist(self):
        """Needs the wrdata lines in TwoStage.cir to be filled in."""
        self.simulate()
        for kind in ["tran", "ac", "dc", "noise"]:
            f = os.path.join(self.dut.output_files_folder, f"{kind}_{self.dut.random_name}.csv")
            self.assertTrue(os.path.isfile(f), f"missing {f} - check the wrdata line for '{kind}'")

    # --- 3. measurements -----------------------------------------------------
    def test_4_all_metrics_are_measured(self):
        """Fails until the find_* TODOs in dut_testbench.py return numbers."""
        self.simulate()
        specs = self.dut.measure_metrics()
        print("\n  measured:", {k: f"{v:.4g}" if v is not None else None for k, v in specs.items()})
        for name in SPECS:
            with self.subTest(spec=name):
                self.assertIsNotNone(specs.get(name), f"{name} is None (not implemented yet?)")

    # --- 4. compare with the reference designs --------------------------------
    @unittest.skipUnless(os.path.isfile(REFERENCE_CSV), "reference_designs.csv not in CAD/ yet")
    def test_5_matches_reference_designs(self):
        import pandas as pd
        ref = pd.read_csv(REFERENCE_CSV)
        param_cols = [c for c in ref.columns if c in self.dut.param_names]
        spec_cols = [c for c in ref.columns if c in SPECS]
        for i, row in ref.iterrows():
            params = {c: row[c] for c in param_cols}
            for c in params:                      # multipliers m* must be integers in the netlist
                if c.startswith("m"):
                    params[c] = int(params[c])
            self.simulate(params)
            specs = self.dut.measure_metrics()
            for name in spec_cols:
                with self.subTest(design=i, spec=name):
                    expected, got = float(row[name]), specs[name]
                    self.assertIsNotNone(got)
                    tol = REL_TOL * abs(expected) if expected != 0 else 1e-12
                    self.assertAlmostEqual(got, expected, delta=tol,
                                           msg=f"design {i}: {name} = {got:.4g}, reference {expected:.4g}")


# =============================================================================
# 5. Correctness: Python measurements vs. an independent ngspice reference
# =============================================================================
N_RANDOM_DESIGNS = 8          # random sizings from the YAML grid (+ the PARAMS design above)
RANDOM_SEED = 2026            # fixed, so the test is reproducible
REPORT_CSV = os.path.join(CAD_DIR, "no_backup", "correctness_report.csv")

# Allowed difference between Python (normal netlist) and the reference (fine ngspice run).
# Relative tolerances, except phm (absolute, in degrees).
TOLERANCES = {
    "gain": 0.001,      # 0.1 %  same data point, only parsing can differ
    "current": 0.001,   # 0.1 %  same operating point
    "noise": 0.01,      # 1 %    reference integrates over a 2x finer frequency grid
    "ugbw": 0.005,      # 0.5 %  reference: 1000 points/decade instead of 10
    "phm": 0.5,         # 0.5 deg
    "slewRate": 0.01,   # 1 %    same 50 ns data, ngspice meas instead of Python
}

# The reference .control block. It replaces the netlist's own .control block and uses
# ngspice's built-in 'meas' commands, so it shares no code with dut_testbench.py:
#   - AC with 1000 points/decade (100x finer) -> gain at 1 Hz, UGBW, phase at UGBW
#   - transient with the same 50 ns step      -> 10-90 % slew rate of both edges
#     (+ a 1 ns run, reported but not tested: it shows the error caused by the 50 ns
#      step of the course netlist itself, which is not a bug in our Python code)
#   - noise with 20 points/decade             -> total output noise
#   - operating point                          -> supply current
REFERENCE_CONTROL = """
.control
set units=degrees
option numdgt=7

* --- slew rate, same 50 ns step as TwoStage.cir: checks our Python method ---
tran 50n 30u
let vmx = maximum(v(net6))
let vmn = minimum(v(net6))
let vlo = vmn + 0.1*(vmx - vmn)
let vhi = vmn + 0.9*(vmx - vmn)
meas tran t_rise trig v(net6) val=vlo rise=1 targ v(net6) val=vhi rise=1
meas tran t_fall trig v(net6) val=vhi fall=1 targ v(net6) val=vlo fall=1
let sr_rise = (vhi - vlo) / t_rise / 1e6
let sr_fall = (vhi - vlo) / t_fall / 1e6
print sr_rise sr_fall

* --- slew rate with a 1 ns step: shows the effect of the 50 ns step (info only) ---
tran 1n 30u
let vmx = maximum(v(net6))
let vmn = minimum(v(net6))
let vlo = vmn + 0.1*(vmx - vmn)
let vhi = vmn + 0.9*(vmx - vmn)
meas tran tf_rise trig v(net6) val=vlo rise=1 targ v(net6) val=vhi rise=1
meas tran tf_fall trig v(net6) val=vhi fall=1 targ v(net6) val=vlo fall=1
let srf_rise = (vhi - vlo) / tf_rise / 1e6
let srf_fall = (vhi - vlo) / tf_fall / 1e6
print srf_rise srf_fall

* --- AC with 1000 points/decade (100x finer than TwoStage.cir) ---
ac dec 1000 1 1T
meas ac ref_gain find vm(net6) at=1
meas ac ref_ugbw when vm(net6)=1 fall=1
meas ac ref_phase find vp(net6) at=ref_ugbw

* --- noise with 20 points/decade (2x finer; ngspice itself returns NaN for some
*     designs at 50+ points/decade, so the reference stays at 20) ---
noise v(net6) vinput dec 20 1 1T
print onoise_total

* --- operating point ---
op
let ref_current = -i(vdd)
print ref_current
.endc
.end
"""


def random_design(yaml_path, rng):
    """Pick a random value on the YAML grid (min, max, step) for every parameter."""
    with open(yaml_path) as f:
        grid = yaml.load(f, Loader=yaml.Loader)["params"]
    design = {}
    for name, (lo, hi, step) in grid.items():
        value = lo + step * rng.randint(0, int(round((hi - lo) / step)))
        design[name] = int(round(value)) if name.startswith("m") else float(f"{value:.4g}")
    return design


def run_reference(netlist_path):
    """Run the fine ngspice reference on a copy of the netlist; return {name: value}."""
    with open(netlist_path) as f:
        circuit = f.read().split(".control")[0]          # keep the circuit, drop its .control
    ref_path = netlist_path.replace(".cir", "_reference.cir")
    with open(ref_path, "w") as f:
        f.write(circuit + REFERENCE_CONTROL)
    out = subprocess.run([NGSPICE_BIN, "-b", ref_path], cwd=CAD_DIR,
                         capture_output=True, text=True).stdout
    values = {}
    for name, number in re.findall(r"^(\w+)\s*=\s*(\S+)", out, re.M):
        try:
            values[name] = float(number)
        except ValueError:          # ngspice prints e.g. "-" or "failed" if a meas fails
            pass
    ref = {
        "gain": values.get("ref_gain"),
        "current": values.get("ref_current"),
        "noise": values.get("onoise_total"),
        "ugbw": values.get("ref_ugbw"),
        "phm": 180.0 + values["ref_phase"] if "ref_phase" in values else None,
        "slewRate": (min(values["sr_rise"], values["sr_fall"])
                     if "sr_rise" in values and "sr_fall" in values else None),
        "slewRate_1ns": (min(values["srf_rise"], values["srf_fall"])
                         if "srf_rise" in values and "srf_fall" in values else None),
    }
    return ref


def phase_difference(a, b):
    """Difference between two angles in degrees, ignoring whole turns of 360 deg.
    Needed because ngspice's vp() wraps the phase into (-180, 180] while Python unwraps it:
    an unstable design is PM = -62 deg in Python and 298 deg in ngspice - the same angle."""
    return (a - b + 180.0) % 360.0 - 180.0


class TestCorrectness(unittest.TestCase):
    """Proof of correctness across several sizings (milestone 1 requirement)."""

    def test_6_measurements_match_ngspice_reference(self):
        rng = random.Random(RANDOM_SEED)
        designs = [("PARAMS", PARAMS)] + [(f"random_{k}", random_design(YAML_PATH, rng))
                                          for k in range(N_RANDOM_DESIGNS)]
        dut = DUT(YAML_PATH)
        rows = []
        for label, design in designs:
            netlist = dut.create_new_netlist(design, "TT")
            self.assertEqual(dut.simulate(netlist), 0, f"{label}: ngspice failed")
            py = dut.measure_metrics()
            ref = run_reference(netlist)

            for spec, tol in TOLERANCES.items():
                got, expected = py[spec], ref[spec]
                if expected is None or np.isnan(expected):
                    # ngspice found no result (gain < 1 everywhere -> no UGBW/PM; output never
                    # completes an edge -> no slew rate). Python must then return its
                    # "no result" value 0 (worst case) instead of crashing or a wrong number.
                    with self.subTest(design=label, spec=spec):
                        self.assertIsNotNone(got)
                        if spec in ("ugbw", "phm", "slewRate"):
                            self.assertEqual(got, 0.0, f"{label} {spec}: expected 0, got {got}")
                    rows.append((label, spec, got, None, None, "ok (no reference, python = 0)"
                                 if got == 0.0 else "no reference"))
                    continue
                if spec == "phm":
                    err = abs(phase_difference(got, expected))
                    ok = err <= tol
                else:
                    err = abs(got - expected) / abs(expected)
                    ok = err <= tol
                rows.append((label, spec, got, expected, err, "ok" if ok else "FAIL"))
                with self.subTest(design=label, spec=spec):
                    self.assertTrue(ok, f"{label} {spec}: python {got:.6g}, reference {expected:.6g}")

            # Info only: slew rate of the 50 ns course netlist vs. a 1 ns simulation
            fine = ref["slewRate_1ns"]
            if fine is not None and py["slewRate"]:
                rows.append((label, "SR@1ns", py["slewRate"], fine,
                             abs(py["slewRate"] - fine) / abs(fine), "info"))

        # Print a table and save it as CSV (useful for the report).
        os.makedirs(os.path.dirname(REPORT_CSV), exist_ok=True)
        with open(REPORT_CSV, "w") as f:
            f.write("design,spec,python,reference,error,status\n")
            print(f"\n  {'design':10s} {'spec':9s} {'python':>12s} {'reference':>12s} {'error':>10s}")
            for label, spec, got, expected, err, status in rows:
                f.write(f"{label},{spec},{got},{expected},{err},{status}\n")
                err_txt = "-" if err is None else (f"{err:.3f} deg" if spec == "phm" else f"{100*err:.3f} %")
                exp_txt = "-" if expected is None else f"{expected:.5g}"
                print(f"  {label:10s} {spec:9s} {got:12.5g} {exp_txt:>12s} {err_txt:>10s}  {status}")
        print(f"  saved to {REPORT_CSV}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
