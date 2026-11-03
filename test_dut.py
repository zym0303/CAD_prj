"""
Unit tests for the DUT class (ngspice_interface/dut_testbench.py).

Put this file directly in the CAD/ folder and run, from CAD/:
    python -m unittest test_dut -v
or press the run button on this file in VS Code.

DUT inherits from NgspiceWrapper, so it has create_new_netlist(), simulate()
and measure_metrics() (which uses parse_outputs() + your find_* functions).
"""
import os
import unittest

# NgspiceWrapper builds every path from os.getcwd(), so always run from CAD/
CAD_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(CAD_DIR)

from ngspice_interface import DUT  # noqa: E402  (import after chdir on purpose)

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
