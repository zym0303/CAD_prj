"""Unit tests of the transistor operating-point data (optional task 2).

TwoStage.cir writes Id, gm, gds, Vgs, Vth, Vds, Vdsat of every transistor and the DC node
voltages during the same simulation that measures the specs (ngspice_interface/op_data.py).
These tests show that:
    1. the data is written and parsed for all 8 transistors and 5 nodes;
    2. the extra output line changes no measured spec (same values as before the change);
    3. the data obeys the circuit's current laws (KCL, current mirrors);
    4. the derived small-signal gain A1*A2 matches the simulated gain;
    5. broken bias is detected (device in triode, output at a rail, which side to fix);
    6. a failed or incomplete simulation gives None instead of a crash;
    7. compare() reports what changed between two designs.

    python -m pytest test_op_data.py -v
"""
import math
import os
import tempfile
import unittest
from types import SimpleNamespace

from ngspice_interface import DUT
from ngspice_interface.op_data import DEVICES, NODES, QUANTITIES, compare, derive, read_op_data

CAD_DIR = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(CAD_DIR, "ngspice_interface", "files", "yaml_files", "TwoStage.yaml")

# Design 681: best design of harness run harness_20261106_000906 (all devices saturated).
GOOD = {"mp1": 4, "wp1": 1.5e-06, "lp1": 9e-08, "mn1": 13, "wn1": 1.75e-06, "ln1": 9e-08,
        "mp3": 11, "wp3": 2.5e-06, "lp3": 9e-08, "mn3": 2, "wn3": 1.25e-06, "ln3": 9e-08,
        "mn4": 6, "wn4": 1e-06, "ln4": 9e-08, "mn5": 12, "wn5": 1e-06, "ln5": 9e-08,
        "cap": 6e-13, "res": 5900.0}
# Its specs as logged in that run, i.e. measured BEFORE the op_TwoStage.csv line was added.
GOOD_SPECS = {"area": 6.652685714285713e-10, "current": 0.00025102503, "gain": 716.5278900090458,
              "noise": 0.018397338, "phm": 66.17861620226859, "slewRate": 54.68647688709368,
              "ugbw": 100219522.44718425}
# Default sizes written in TwoStage.cir: mn5 sinks far more than mp3 can source.
BROKEN = {"mp1": 10, "wp1": 0.5e-6, "lp1": 90e-9, "mn1": 38, "wn1": 0.5e-6, "ln1": 90e-9,
          "mn3": 9, "wn3": 0.5e-6, "ln3": 90e-9, "mp3": 4, "wp3": 0.5e-6, "lp3": 90e-9,
          "mn4": 20, "wn4": 0.5e-6, "ln4": 90e-9, "mn5": 60, "wn5": 0.5e-6, "ln5": 90e-9,
          "cap": 3e-12, "res": 1e3}
IBIAS = 30e-6


def simulate(params):
    """Run one full simulation; return (measured specs, raw operating point)."""
    dut = DUT(YAML_PATH)
    info = dut.simulate(dut.create_new_netlist(params, "TT", 27, 1.2))
    assert info == 0, "ngspice failed"
    return dut.measure_metrics(), read_op_data(dut)


class TestOperatingPoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.specs, cls.op = simulate(GOOD)
        cls.d = derive(cls.op, GOOD, cls.specs["ugbw"])
        cls.bad_specs, cls.bad_op = simulate(BROKEN)
        cls.bad = derive(cls.bad_op, BROKEN, cls.bad_specs["ugbw"])

    # --- 1. data is written and parsed ---------------------------------------
    def test_1_all_devices_and_nodes_are_read(self):
        self.assertIsNotNone(self.op, "op_<netlist>.csv missing: check the wrdata op line in TwoStage.cir")
        for d in DEVICES:
            for q in QUANTITIES:
                with self.subTest(device=d, quantity=q):
                    self.assertTrue(math.isfinite(self.op["devices"][d][q]))
        for n in NODES:
            self.assertTrue(0.0 <= self.op["nodes"][n] <= 1.2, f"V({n}) outside the supply")

    # --- 2. the extra output changes no spec ----------------------------------
    def test_2_specs_are_unchanged(self):
        for name, ref in GOOD_SPECS.items():
            with self.subTest(spec=name):
                self.assertAlmostEqual(self.specs[name], ref, delta=1e-6 * abs(ref))

    # --- 3. current laws -----------------------------------------------------
    def test_3a_kcl_total_current(self):
        """i(vdd) = Ibias + I_tail (mn4) + I_2 (mn5)."""
        dev = self.op["devices"]
        self.assertAlmostEqual(self.specs["current"], IBIAS + dev["mn4"]["id"] + dev["mn5"]["id"],
                               delta=1e-3 * self.specs["current"])

    def test_3b_tail_current_splits_over_the_input_pair(self):
        dev = self.op["devices"]
        self.assertAlmostEqual(dev["mn4"]["id"], dev["mn1"]["id"] + dev["mn2"]["id"],
                               delta=1e-3 * dev["mn4"]["id"])

    def test_3c_series_devices_carry_the_same_current(self):
        dev = self.op["devices"]
        for top, bottom in [("mp1", "mn1"), ("mp2", "mn2"), ("mp3", "mn5")]:
            with self.subTest(pair=(top, bottom)):
                self.assertAlmostEqual(dev[top]["id"], dev[bottom]["id"], delta=1e-3 * dev[bottom]["id"])

    def test_3d_bias_diode_carries_ibias(self):
        self.assertAlmostEqual(self.op["devices"]["mn3"]["id"], IBIAS, delta=1e-3 * IBIAS)

    # --- 4. derived quantities -------------------------------------------------
    def test_4a_gain_estimate_matches_simulation(self):
        est = self.d["circuit"]["gain_estimate"]
        self.assertAlmostEqual(est, self.specs["gain"], delta=0.05 * self.specs["gain"])

    def test_4b_good_design_has_no_warnings(self):
        self.assertEqual(self.d["warnings"], [])
        for d in DEVICES:
            self.assertEqual(self.d["devices"][d]["region"], "saturation", d)

    def test_4c_pole_and_zero_notes(self):
        """Design 681: p2 = gm6/(2 pi CL) ~ 32 MHz < UGBW, PM comes from the LHP zero (Rc > 1/gm6)."""
        c = self.d["circuit"]
        self.assertLess(c["p2_gm6_over_2piCL_MHz"], self.specs["ugbw"] / 1e6)
        self.assertTrue(c["zero_type"].startswith("LHP"))
        self.assertTrue(any("limited by gm6" in n for n in self.d["notes"]))

    # --- 5. broken bias is detected -------------------------------------------
    def test_5a_device_in_triode_is_reported(self):
        self.assertEqual(self.bad["devices"]["mn5"]["region"], "triode")
        self.assertTrue(any(w.startswith("mn5") and "triode" in w for w in self.bad["warnings"]))

    def test_5b_output_at_ground_points_to_the_right_side(self):
        self.assertLess(self.bad["circuit"]["balance_ratio_sizes"], 1.0)
        w = [w for w in self.bad["warnings"] if w.startswith("output DC level at ground")]
        self.assertEqual(len(w), 1, self.bad["warnings"])
        self.assertIn("larger S_mp3 or smaller S_mn5", w[0])

    # --- 6. failures give None ---------------------------------------------------
    def test_6a_missing_file_gives_none(self):
        engine = SimpleNamespace(output_files_folder=tempfile.gettempdir(), random_name="does_not_exist")
        self.assertIsNone(read_op_data(engine))

    def test_6b_incomplete_file_gives_none(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "op_x.csv"), "w") as f:
                f.write(" net4 @mn1[id] net4 @mn1[gm]\n 0 1e-5 0 2e-4\n")
            self.assertIsNone(read_op_data(SimpleNamespace(output_files_folder=folder, random_name="x")))

    # --- 7. compare ----------------------------------------------------------------
    def test_7a_compare_identical_is_empty(self):
        diff = compare(self.d, self.d)
        self.assertEqual(diff["devices"], {})
        self.assertEqual(diff["circuit"], {})

    def test_7b_compare_reports_region_and_warning_changes(self):
        diff = compare(self.d, self.bad)
        self.assertEqual(diff["devices"]["mn5"]["region"], ["saturation", "triode"])
        self.assertTrue(any(w.startswith("mn5") for w in diff["warnings_only_in_b"]))
        self.assertEqual(diff["warnings_only_in_a"], [])


if __name__ == "__main__":
    unittest.main()
