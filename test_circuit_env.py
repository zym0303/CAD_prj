"""
Unit tests for the circuit environment (circuit_env.py), Milestone 2.

Put this file directly in the CAD/ folder and run, from CAD/ with the .venv active:
    python -m unittest test_circuit_env -v
or press the run button on this file in VS Code.

What is tested, and against what reference:
    1. action_refine       TA reference designs (action_* -> param_*), grid edges, clipping
    2. normalize_specs     TA reference designs (spec_* -> norm_*), hand calculations, broken specs
    3. reward_computation  TA reference designs (norm_* -> reward), hand calculations A-E
    4. simulate            netlist content, failure handling (ngspice not needed: mocked)
    5. reset / step        episode logic with a fake simulator (fast, no ngspice)
    6. end-to-end          real ngspice on the 5 TA reference designs (skipped if ngspice is missing)

The TA reference file Reference_Designs/references.csv has one row per attribute and one
column per design: param_*, action_*, spec_*, norm_*, reward. It uses the targets of
TwoStage.yaml (slew rate >= 30 V/us, UGBW >= 100 MHz).
"""
import csv
import math
import os
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

# CircuitEnv and NgspiceWrapper build every path from os.getcwd(), so always run from CAD/
CAD_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(CAD_DIR)

from circuit_env import CircuitEnv                               # noqa: E402
from ngspice_interface.ngspice_wrapper import NGSPICE_BIN        # noqa: E402

REFERENCE_CSV = os.path.join(CAD_DIR, "Reference_Designs", "references.csv")
SPECS = ["area", "current", "gain", "noise", "phm", "slewRate", "ugbw"]
NGSPICE_AVAILABLE = os.path.exists(NGSPICE_BIN) or shutil.which(NGSPICE_BIN) is not None
THIRD = 1.0 / 3.0


def load_references():
    """references.csv -> list of 5 dicts {'param': {...}, 'action': {...}, 'spec': {...}, 'norm': {...}, 'reward': x}"""
    with open(REFERENCE_CSV) as f:
        rows = [r for r in csv.reader(f) if r]
    n_designs = len(rows[0]) - 2                     # columns: Attribute, Unit, Design 1..n
    designs = [{"param": {}, "action": {}, "spec": {}, "norm": {}} for _ in range(n_designs)]
    for row in rows[1:]:
        key, values = row[0], row[2:]
        for d, value in enumerate(values):
            if key == "reward":
                designs[d]["reward"] = float(value)
            else:
                kind, name = key.split("_", 1)       # e.g. 'param', 'mp1'
                designs[d][kind][name] = float(value)
    return designs


REFERENCES = load_references()


def make_env():
    return CircuitEnv(run_id="unittest")


def on_target(env, **changes):
    """Spec dict with every spec exactly on its target, except the ones given."""
    specs = dict(env.dict_targets)
    specs.update(changes)
    return specs


# =============================================================================
# 1. action_refine
# =============================================================================
class TestActionRefine(unittest.TestCase):

    def setUp(self):
        self.env = make_env()
        self.grids = {name: np.arange(r["min"], r["max"], r["step"])
                      for name, r in self.env.param_ranges.items()}

    def test_1a_reference_actions_give_reference_sizes(self):
        """TA reference designs: action_* must be refined into exactly param_*."""
        for d, ref in enumerate(REFERENCES, start=1):
            action = [ref["action"][name] for name in self.env.param_ranges]
            params = self.env.action_refine(action)
            for name, value in params.items():
                with self.subTest(design=d, param=name):
                    self.assertAlmostEqual(value, ref["param"][name],
                                           delta=1e-9 * abs(ref["param"][name]) + 1e-15)

    def test_1b_minus_one_gives_minimum(self):
        params = self.env.action_refine([-1.0] * self.env.n_actions)
        for name, value in params.items():
            with self.subTest(param=name):
                self.assertAlmostEqual(value, self.env.param_ranges[name]["min"], delta=1e-15)

    def test_1c_plus_one_gives_last_grid_value(self):
        """+1 gives the last value of np.arange(min, max, step) (max itself is excluded, as in the TA code)."""
        params = self.env.action_refine([1.0] * self.env.n_actions)
        for name, value in params.items():
            with self.subTest(param=name):
                self.assertAlmostEqual(value, self.grids[name][-1], delta=1e-9 * abs(self.grids[name][-1]))

    def test_1d_zero_gives_middle_values(self):
        params = self.env.action_refine([0.0] * self.env.n_actions)
        self.assertEqual(params["mp1"], 12)              # grid 1..24 (24 values) -> index floor(0.5*23) = 11
        self.assertAlmostEqual(params["wp1"], 1.5e-6)    # grid 0.25..2.75 um (11 values) -> index 5
        self.assertAlmostEqual(params["lp1"], 90e-9)     # grid 45..180 nm (4 values) -> index floor(1.5) = 1
        self.assertAlmostEqual(params["cap"], 5.0e-12)   # grid 0.1..9.9 pF (99 values) -> index 49
        self.assertAlmostEqual(params["res"], 4900.0)    # grid 0..9800 ohm (99 values) -> index 49

    def test_1e_out_of_range_actions_are_clipped(self):
        n = self.env.n_actions
        self.assertEqual(self.env.action_refine([5.0] * n), self.env.action_refine([1.0] * n))
        self.assertEqual(self.env.action_refine([-5.0] * n), self.env.action_refine([-1.0] * n))
        self.assertEqual(self.env.action_refine([np.nan] * n), self.env.action_refine([0.0] * n))

    def test_1f_random_actions_stay_on_the_grid(self):
        rng = np.random.default_rng(2026)
        for _ in range(500):
            params = self.env.action_refine(rng.uniform(-1, 1, self.env.n_actions))
            for name, value in params.items():
                grid = self.grids[name]
                self.assertTrue(np.any(np.isclose(grid, value, rtol=1e-9, atol=0)), f"{name}={value} not on grid")
                if name.startswith("m"):
                    self.assertIsInstance(value, int)

    def test_1g_parameter_order_is_the_yaml_order(self):
        params = self.env.action_refine([0.0] * self.env.n_actions)
        self.assertEqual(list(params), list(self.env.param_ranges))

    def test_1h_wrong_action_length_raises(self):
        with self.assertRaises(ValueError):
            self.env.action_refine([0.0] * (self.env.n_actions - 1))


# =============================================================================
# 2. normalize_specs
# =============================================================================
class TestNormalizeSpecs(unittest.TestCase):

    def setUp(self):
        self.env = make_env()

    def test_2a_reference_specs_give_reference_norms(self):
        for d, ref in enumerate(REFERENCES, start=1):
            norm = self.env.normalize_specs(ref["spec"])
            for name in SPECS:
                with self.subTest(design=d, spec=name):
                    self.assertAlmostEqual(norm[name], ref["norm"][name], delta=1e-9)

    def test_2b_hand_calculations(self):
        norm = self.env.normalize_specs(on_target(self.env, gain=100, noise=0.06, area=4e-9, current=1e-4))
        self.assertAlmostEqual(norm["gain"], -THIRD)     # (100-200)/(100+200)
        self.assertAlmostEqual(norm["noise"], THIRD)     # (0.06-0.03)/(0.06+0.03)
        self.assertAlmostEqual(norm["area"], THIRD)
        self.assertAlmostEqual(norm["current"], -THIRD)
        for name in ("phm", "slewRate", "ugbw"):
            self.assertAlmostEqual(norm[name], 0.0)      # exactly on target

    def test_2c_output_order_is_the_yaml_order(self):
        norm = self.env.normalize_specs(dict(reversed(list(on_target(self.env).items()))))
        self.assertEqual(list(norm), list(self.env.dict_targets))

    def test_2d_broken_specs_get_the_worst_value(self):
        norm = self.env.normalize_specs(on_target(self.env, phm=-60.0, ugbw=None, slewRate=float("nan"), gain=-50.0))
        for name in ("phm", "ugbw", "slewRate", "gain"):     # higher is better -> worst = -1
            self.assertEqual(norm[name], -1.0, name)
        specs = on_target(self.env, phm=-90.0)                # y + y* < 0: must NOT look good
        self.assertEqual(self.env.normalize_specs(specs)["phm"], -1.0)
        specs = on_target(self.env)
        del specs["noise"]                                    # lower is better -> worst = +1
        self.assertEqual(self.env.normalize_specs(specs)["noise"], 1.0)

    def test_2e_values_stay_in_minus_one_one(self):
        rng = np.random.default_rng(1)
        for _ in range(200):
            specs = {name: rng.uniform(-2, 2) * goal for name, goal in self.env.dict_targets.items()}
            for value in self.env.normalize_specs(specs).values():
                self.assertTrue(-1.0 <= value <= 1.0 and math.isfinite(value))


# =============================================================================
# 3. reward_computation
# =============================================================================
class TestRewardComputation(unittest.TestCase):

    def setUp(self):
        self.env = make_env()

    def reward_of(self, **changes):
        return self.env.reward_computation(self.env.normalize_specs(on_target(self.env, **changes)))

    def test_3a_reference_norms_give_reference_rewards(self):
        for d, ref in enumerate(REFERENCES, start=1):
            with self.subTest(design=d):
                reward, satisfied = self.env.reward_computation(ref["norm"])
                self.assertAlmostEqual(reward, ref["reward"], delta=1e-9)
                self.assertFalse(satisfied)          # none of the 5 reference designs meets all constraints

    def test_3b_example_A_one_constraint_fails(self):
        reward, satisfied = self.reward_of(gain=100, area=4e-9, current=1e-4)
        self.assertAlmostEqual(reward, -THIRD)       # r_H = -1/3, r_T = -1/3 + 1/3 = 0
        self.assertFalse(satisfied)

    def test_3c_example_B_all_constraints_met(self):
        reward, satisfied = self.reward_of(area=1e-9)
        self.assertAlmostEqual(reward, 0.3 + THIRD)  # bonus 0.3 + r_T = 1/3
        self.assertTrue(satisfied)

    def test_3d_example_C_exactly_on_target_is_feasible(self):
        reward, satisfied = self.reward_of()
        self.assertAlmostEqual(reward, 0.3)
        self.assertTrue(satisfied)

    def test_3e_example_D_noise_is_an_upper_bound(self):
        reward, satisfied = self.reward_of(noise=0.06)
        self.assertAlmostEqual(reward, -THIRD)
        self.assertFalse(satisfied)

    def test_3f_example_E_no_reward_for_over_satisfying(self):
        reward, satisfied = self.reward_of(gain=1e4, ugbw=1e10)
        self.assertAlmostEqual(reward, 0.3)
        self.assertTrue(satisfied)

    def test_3g_returns_plain_types(self):
        reward, satisfied = self.reward_of()
        self.assertIsInstance(reward, float)
        self.assertIsInstance(satisfied, bool)


# =============================================================================
# 4. simulate (ngspice mocked)
# =============================================================================
class TestSimulate(unittest.TestCase):

    def setUp(self):
        self.env = make_env()
        self.params = self.env.action_refine([REFERENCES[0]["action"][n] for n in self.env.param_ranges])

    def test_4a_netlist_contains_the_refined_parameters(self):
        """The netlist written for a design must contain exactly the refined values."""
        path = self.env.simulation_engine.create_new_netlist(self.params, process="TT", temp_pvt=27, vdd=1.2)
        with open(path) as f:
            text = f.read()
        written = dict(re.findall(r"(\w+)=([\w\.\+\-]+)", " ".join(
            line for line in text.splitlines() if line.startswith(".param"))))
        for name, value in self.params.items():
            with self.subTest(param=name):
                self.assertIn(name, written)
                self.assertAlmostEqual(float(written[name]), value, delta=1e-9 * abs(value) + 1e-15)
        self.assertIn("p045_TT.sp", text)

    def test_4b_crash_while_measuring_gives_worst_case_specs(self):
        engine = self.env.simulation_engine
        with patch.object(engine, "create_new_netlist", return_value="fake.cir"), \
             patch.object(engine, "simulate", return_value=0), \
             patch.object(engine, "measure_metrics", side_effect=FileNotFoundError("no output")):
            specs = self.env.simulate(self.params)
        self.assertEqual(self.env.n_failed_sims, 1)
        self.assertAlmostEqual(specs["area"], REFERENCES[0]["spec"]["area"], delta=1e-3 * specs["area"])
        for name in SPECS[1:]:
            self.assertTrue(math.isnan(specs[name]), name)
        reward, satisfied = self.env.reward_computation(self.env.normalize_specs(specs))
        self.assertLess(reward, -4.9)                # every hard constraint at its worst: r_H = -5
        self.assertFalse(satisfied)

    def test_4c_ngspice_error_code_gives_worst_case_specs(self):
        engine = self.env.simulation_engine
        with patch.object(engine, "create_new_netlist", return_value="fake.cir"), \
             patch.object(engine, "simulate", return_value=1):
            specs = self.env.simulate(self.params)
        self.assertEqual(self.env.n_failed_sims, 1)
        self.assertTrue(math.isnan(specs["gain"]))

    def test_4d_every_simulation_is_counted(self):
        engine = self.env.simulation_engine
        with patch.object(engine, "create_new_netlist", return_value="fake.cir"), \
             patch.object(engine, "simulate", return_value=0), \
             patch.object(engine, "measure_metrics", return_value=dict(REFERENCES[0]["spec"])):
            specs = self.env.simulate(self.params)
        self.assertEqual(self.env.n_simulations, 1)
        self.assertEqual(self.env.n_failed_sims, 0)
        self.assertEqual(list(specs), list(self.env.dict_targets))


# =============================================================================
# 5. reset / step (fake simulator, outputs written to a temporary folder)
# =============================================================================
class TestEpisode(unittest.TestCase):

    def setUp(self):
        self.env = make_env()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)                           # output_figs/ and solutions/ go here, not into CAD/
        self.good = on_target(self.env, area=1e-9)   # feasible,   FoM 0.3 + 1/3
        self.bad = on_target(self.env, gain=100)     # infeasible, FoM -1/3

    def tearDown(self):
        os.chdir(CAD_DIR)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def fake_simulator(self, results):
        it = iter(results)
        return patch.object(self.env, "simulate", side_effect=lambda params: dict(next(it)))

    def test_5a_reset_returns_the_observation(self):
        with self.fake_simulator([self.bad]):
            ob = self.env.reset()
        self.assertIsInstance(ob, np.ndarray)        # only the observation, not (obs, info)
        self.assertEqual(ob.shape, (7,))
        self.assertEqual(ob.dtype, np.float32)
        expected = self.env.normalize_specs(self.bad)
        np.testing.assert_allclose(ob, [expected[n] for n in self.env.dict_targets], atol=1e-6)
        self.assertEqual(self.env.episode_steps, 0)

    def test_5b_reset_with_seed_is_reproducible(self):
        with self.fake_simulator([self.good, self.good, self.good]):
            self.env.reset(seed=1)
            first = dict(self.env.param_values)
            self.env.reset(seed=1)
            second = dict(self.env.param_values)
            self.env.reset(seed=2)
            third = dict(self.env.param_values)
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)

    def test_5c_two_episodes(self):
        """Episode 1: 3 bad, 1 good, 6 bad. Episode 2: 10 good."""
        episode1 = [self.bad] * 3 + [self.good] + [self.bad] * 6
        episode2 = [self.good] * 10
        sims = [self.bad] + episode1 + [self.bad] + episode2          # each reset also simulates
        rng = np.random.default_rng(0)
        dones = []
        with self.fake_simulator(sims):
            for episode in range(2):
                self.env.reset()
                for _ in range(10):
                    result = self.env.step(rng.uniform(-1, 1, self.env.n_actions))
                    self.assertEqual(len(result), 4)
                    ob, reward, done, info = result
                    self.assertEqual(ob.dtype, np.float32)
                    self.assertIsInstance(reward, float)
                    self.assertIsInstance(done, bool)
                    dones.append(done)

        self.assertEqual([i + 1 for i, d in enumerate(dones) if d], [10, 20])
        self.assertEqual(self.env.env_steps, 20)
        expected_rewards = [-THIRD] * 3 + [0.3 + THIRD] + [-THIRD] * 6 + [0.3 + THIRD] * 10
        np.testing.assert_allclose(self.env.reward_history, expected_rewards, atol=1e-9)
        np.testing.assert_allclose(self.env.score_history,
                                   [9 * -THIRD + 0.3 + THIRD, 10 * (0.3 + THIRD)], atol=1e-9)

        # every feasible design is saved (used for the Pareto plot), with its step index
        with open(os.path.join("solutions", "unittest.csv")) as f:
            rows = [r for r in csv.reader(f) if r][1:]
        self.assertEqual([int(r[0]) for r in rows], [3] + list(range(10, 20)))
        self.assertTrue(os.path.isfile(os.path.join("output_figs", "unittest", "max_reward.png")))
        self.assertTrue(os.path.isfile(os.path.join("output_figs", "unittest", "average_score.png")))


# =============================================================================
# 6. End-to-end with real ngspice on the TA reference designs
# =============================================================================
@unittest.skipUnless(NGSPICE_AVAILABLE, "ngspice not found")
class TestEndToEnd(unittest.TestCase):
    SPEC_REL_TOL = 0.05     # same tolerance as test_dut.py
    NORM_ABS_TOL = 0.02
    REWARD_ABS_TOL = 0.05

    def test_6a_reference_designs_from_action_to_reward(self):
        """action_* -> action_refine -> netlist -> ngspice -> specs -> norms -> reward, vs. the TA values."""
        env = make_env()
        for d, ref in enumerate(REFERENCES, start=1):
            action = [ref["action"][name] for name in env.param_ranges]
            env.evaluate(action)
            reward, _ = env.reward_computation(env.cur_norm_specs)
            for name in SPECS:
                with self.subTest(design=d, spec=name):
                    expected = ref["spec"][name]
                    self.assertAlmostEqual(env.real_specs[name], expected, delta=self.SPEC_REL_TOL * abs(expected),
                                           msg=f"design {d}: {name} = {env.real_specs[name]:.6g}, reference {expected:.6g}")
                    self.assertAlmostEqual(env.cur_norm_specs[name], ref["norm"][name], delta=self.NORM_ABS_TOL)
            with self.subTest(design=d, check="reward"):
                self.assertAlmostEqual(reward, ref["reward"], delta=self.REWARD_ABS_TOL)
        self.assertEqual(env.n_failed_sims, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
