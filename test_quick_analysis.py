"""Unit tests of the cheap analyses (optional task 2, ngspice_interface/quick_analysis.py).

These tests show that:
    1. the quick netlist keeps the circuit unchanged and runs only the selected analyses;
    2. every quick analysis measures exactly the spec of the full simulation (same circuit,
       same measurement code), and the short 5 us transient gives the same slew rate;
    3. op-only gives the same transistor data as the full simulation and detects broken bias;
    4. PVT corners change the results in the physically expected direction;
    5. the quick_analysis tool never creates a candidate, a simulator call or RL data, caches
       repeated runs, logs every run and rejects bad input.

    python -m pytest test_quick_analysis.py -v
"""
import json
import os
import shutil
import unittest

from ngspice_interface.quick_analysis import ANALYSES, QuickDUT, make_quick_netlist
from test_op_data import BROKEN, GOOD, GOOD_SPECS, YAML_PATH, simulate

CAD_DIR = os.path.dirname(os.path.abspath(__file__))
NETLIST = os.path.join(CAD_DIR, "ngspice_interface", "files", "input_netlists", "TwoStage.cir")
TEMPLATES = os.path.join(CAD_DIR, "no_backup", "quick_netlists")


def control_block(text):
    return text.partition(".control")[2].partition(".endc")[0]


class TestQuickNetlist(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(NETLIST) as f:
            cls.text = f.read()

    def test_1a_circuit_part_unchanged(self):
        for analyses in (["op"], ["ac", "noise"], list(ANALYSES)):
            quick = make_quick_netlist(self.text, analyses)
            self.assertEqual(quick.partition(".control")[0], self.text.partition(".control")[0])

    def test_1b_only_selected_analyses(self):
        for analyses in (["op"], ["ac"], ["noise"], ["tran"], ["op", "ac"]):
            words = [l.split()[0] for l in control_block(make_quick_netlist(self.text, analyses)).splitlines()
                     if l.split()]
            with self.subTest(analyses=analyses):
                self.assertEqual(sorted(w for w in words if w in ANALYSES), sorted(analyses))
                self.assertNotIn("run", words)

    def test_1c_wrdata_follows_its_analysis(self):
        block = control_block(make_quick_netlist(self.text, ["op"]))
        self.assertIn("wrdata dc_TwoStage.csv", block)
        self.assertIn("wrdata op_TwoStage.csv", block)
        self.assertNotIn("tran_TwoStage", block)
        self.assertNotIn("ac_TwoStage", block)

    def test_1d_short_transient(self):
        block = control_block(make_quick_netlist(self.text, ["tran"]))
        self.assertIn("tran 1n 5u", block)

    def test_1e_bad_input(self):
        with self.assertRaises(ValueError):
            make_quick_netlist(self.text, ["dc"])
        with self.assertRaises(ValueError):
            make_quick_netlist(self.text, [])


class TestQuickResults(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.q = QuickDUT(YAML_PATH, TEMPLATES)
        cls.full_specs, cls.full_op = simulate(GOOD)

    def test_2a_each_analysis_gives_the_full_simulation_spec(self):
        for analysis, names in (("op", ["current"]), ("ac", ["gain", "phm", "ugbw"]),
                                ("noise", ["noise"]), ("tran", ["slewRate"])):
            specs, _, _ = self.q.run(GOOD, [analysis])
            self.assertEqual(sorted(specs), sorted(names + ["area"]))
            for name in names + ["area"]:
                with self.subTest(analysis=analysis, spec=name):
                    self.assertAlmostEqual(specs[name], GOOD_SPECS[name], delta=1e-6 * abs(GOOD_SPECS[name]))

    def test_2b_all_quick_analyses_equal_full_simulation(self):
        specs, _, _ = self.q.run(GOOD, list(ANALYSES))
        for name, ref in self.full_specs.items():
            with self.subTest(spec=name):
                self.assertAlmostEqual(specs[name], ref, delta=1e-6 * abs(ref))

    def test_3a_op_only_equals_full_operating_point(self):
        _, op, _ = self.q.run(GOOD, ["op"])
        for d, values in self.full_op["devices"].items():
            for k, v in values.items():
                self.assertAlmostEqual(op["devices"][d][k], v, delta=1e-9 * abs(v) + 1e-15)
        for n, v in self.full_op["nodes"].items():
            self.assertAlmostEqual(op["nodes"][n], v, delta=1e-9)
        self.assertIsNone(self.q.run(GOOD, ["ac"])[1], "no op data without the op analysis")

    def test_3b_op_only_detects_broken_bias(self):
        from ngspice_interface.op_data import derive
        _, op, _ = self.q.run(BROKEN, ["op"])
        warnings = derive(op, BROKEN)["warnings"]
        self.assertTrue(any(w.startswith("output DC level at ground") for w in warnings), warnings)

    def test_4_corners(self):
        tt, _, _ = self.q.run(GOOD, ["ac"])
        ss, _, _ = self.q.run(GOOD, ["ac"], process="SS")
        ff, _, _ = self.q.run(GOOD, ["ac"], process="FF")
        self.assertLess(ss["ugbw"], tt["ugbw"])       # slow devices: less gm
        self.assertGreater(ff["ugbw"], tt["ugbw"])
        cold, _, _ = self.q.run(GOOD, ["op"], temp=-40)
        hot, _, _ = self.q.run(GOOD, ["op"], temp=125)
        self.assertNotAlmostEqual(cold["current"], hot["current"], delta=1e-9)
        low, _, _ = self.q.run(GOOD, ["op"], vdd=1.0)
        self.assertNotAlmostEqual(low["current"], self.q.run(GOOD, ["op"])[0]["current"], delta=1e-9)


class TestQuickTool(unittest.TestCase):
    RUN_ID = "test_quick_analysis"

    @classmethod
    def setUpClass(cls):
        from sizing_tools import SizingExperiment
        cls.x = SizingExperiment(run_id=cls.RUN_ID)
        cls.x.simulate(GOOD, rationale="reference design", agent="test")

    @classmethod
    def tearDownClass(cls):
        for path in (os.path.join("harness_runs", cls.RUN_ID), os.path.join("output_figs", cls.RUN_ID),
                     os.path.join("output_figs", cls.RUN_ID + "_evaluate")):
            shutil.rmtree(path, ignore_errors=True)
        for name in (cls.RUN_ID, cls.RUN_ID + "_evaluate"):
            if os.path.exists(os.path.join("solutions", name + ".csv")):
                os.remove(os.path.join("solutions", name + ".csv"))

    def test_5a_no_candidate_no_simulator_call(self):
        x = self.x
        before = (x.simulator_calls, len(x.by_id), len(x.candidates), int(x.replay.size), x.best["id"])
        out = x.quick_analysis([{"mn5": 10}, {"mn5": 14}], ["op"], rationale="test", agent="test")
        self.assertEqual(before, (x.simulator_calls, len(x.by_id), len(x.candidates), int(x.replay.size),
                                  x.best["id"]))
        self.assertEqual(len(out["results"]), 2)
        for row in out["results"]:
            self.assertIn("fom_if_feasible", row)
            self.assertIn("circuit", row)
            self.assertIn("phm", row["not_measured"])

    def test_5b_full_set_scores_like_simulate(self):
        out = self.x.quick_analysis([{}], list(ANALYSES), rationale="test", agent="test")
        row = out["results"][0]
        self.assertEqual(row["not_measured"], [])
        self.assertTrue(row["feasible"])
        self.assertAlmostEqual(row["reward"], self.x.best["reward"], delta=1e-3)

    def test_5c_cache_and_log(self):
        x = self.x
        x.quick_analysis([{"res": 6000.0}], ["ac"], rationale="test", agent="test")
        runs = x.quick_runs
        out = x.quick_analysis([{"res": 6000.0}], ["ac"], rationale="test", agent="test")
        self.assertEqual(x.quick_runs, runs)
        self.assertTrue(out["results"][0]["cached"])
        with open(x.quick_path) as f:
            entries = [json.loads(l) for l in f]
        self.assertEqual(len(entries), x.quick_runs)
        self.assertEqual(json.load(open(x.out_dir / "summary.json"))["quick_runs"], x.quick_runs)

    def test_5d_corner_and_warnings(self):
        out = self.x.quick_analysis([{}], ["op", "ac"], rationale="test", agent="test",
                                    corner={"process": "SS", "temp": 80})
        self.assertEqual(out["corner"], {"process": "SS", "voltage": 1.2, "temp": 80.0})
        # mn5 doubled (on the grid): it sinks far more than mp3 sources -> output at ground
        broken = self.x.quick_analysis([{"mn5": 24}], ["op"], rationale="test", agent="test")
        warnings = broken["results"][0].get("op_warnings", [])
        self.assertTrue(any(w.startswith("output DC level at ground") for w in warnings), warnings)

    def test_5e_bad_input(self):
        x, ok = self.x, dict(rationale="test", agent="test")
        for kwargs in (dict(variants=[{}] * 11), dict(variants=[]), dict(variants=[{}], analyses=["dc"]),
                       dict(variants=[{}], corner={"process": "XX"}), dict(variants=[{}], corner={"temp": 300}),
                       dict(variants=[{}], corner={"vdd": 1.0}), dict(variants=[{"mn5": 10.5}])):
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                with self.assertRaises(ValueError):
                    x.quick_analysis(**{**ok, **kwargs})
        with self.assertRaises(ValueError):
            x.quick_analysis([{}], rationale=" ", agent="test")

    def test_6a_corner_check_twelve_corners(self):
        from circuit_env import CircuitEnv
        x = self.x
        before = (x.simulator_calls, len(x.by_id), x.best["id"])
        runs, checks = x.quick_runs, x.corner_checks
        out = x.corner_check(rationale="test", agent="test")
        self.assertEqual(before, (x.simulator_calls, len(x.by_id), x.best["id"]), "not a simulation")
        self.assertEqual(len(out["corners"]), len(CircuitEnv.PVT_CORNERS))
        self.assertEqual(x.quick_runs - runs, len(CircuitEnv.PVT_CORNERS))
        self.assertEqual(x.corner_checks, checks + 1)
        self.assertEqual(out["not_measured"], [])
        # the worst case is the min (or max) over the corners, as in CircuitEnv._worst_case
        for name, worst in out["worst_case"].items():
            values = [row["specs"][name] for row in out["corners"]]
            expected = max(values) if name in CircuitEnv.LOWER_IS_BETTER else min(values)
            self.assertAlmostEqual(worst["value"], expected, delta=1e-9 * abs(expected) + 1e-15, msg=name)
        failing = [row["corner"] for row in out["corners"] if row["violated"]]
        self.assertEqual(out["failing_corners"], failing)
        self.assertEqual(out["feasible_in_all_corners"], not failing)
        # the TT 1.2 V corners bracket the nominal 27 C simulation
        tt = [row["specs"]["current"] for row in out["corners"] if row["corner"].startswith("TT 1.2V")]
        self.assertTrue(min(tt) <= x.best["specs"]["current"] * 1.05)
        # cached: a second check runs nothing
        x.corner_check(rationale="again", agent="test")
        self.assertEqual(x.quick_runs - runs, len(CircuitEnv.PVT_CORNERS))

    def test_6b_corner_check_variant_and_bad_input(self):
        x = self.x
        out = x.corner_check(rationale="test", agent="test", variant={"cap": 3e-12}, analyses=["ac"])
        self.assertEqual(out["variant"], {"cap": 3e-12})
        self.assertIsNone(out["nominal"])
        self.assertIn("current", out["not_measured"])
        for kwargs in (dict(rationale=" "), dict(analyses=["dc"]), dict(variant={"cap": 3.05e-12}),
                       dict(candidate_id=99999), dict(variant=[1])):
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                with self.assertRaises(ValueError):
                    x.corner_check(**{"rationale": "test", "agent": "test", **kwargs})


if __name__ == "__main__":
    unittest.main()
