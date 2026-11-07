"""Tests of the harness PVT-robust mode (optional task 1 in the LLM harness), real ngspice.

    python -m pytest test_pvt_robust_harness.py -v        (~1-2 min: every design = 12 corners)

Checks: nominal is the default and unchanged; the mode can only be switched on before the
first simulation; robust candidates carry the worst case over the 12 corners and the same
FoM as CircuitEnv.robust_reward_computation (what td3_runner --pvt_robust optimizes); the RL
tools, operating_point and corner_check work in robust mode.
"""
import json
import math

import numpy as np
import pytest

from circuit_env import CircuitEnv
from sizing_tools import SizingExperiment, robust_fom

# a design of a nominal harness run (feasible at TT 27 C, fails UGBW/PM at 100 C)
NOMINAL_BEST = {'mp1': 5, 'wp1': 2.5e-06, 'lp1': 9e-08, 'mn1': 11, 'wn1': 2.5e-06, 'ln1': 9e-08,
                'mp3': 16, 'wp3': 2.5e-06, 'lp3': 9e-08, 'mn3': 3, 'wn3': 1e-06, 'ln3': 9e-08,
                'mn4': 6, 'wn4': 1.25e-06, 'ln4': 9e-08, 'mn5': 13, 'wn5': 1e-06, 'ln5': 9e-08,
                'cap': 6e-13, 'res': 6000.0}


@pytest.fixture(scope="module")
def robust():
    exp = SizingExperiment(batch_size=8, run_id="test_pvt_robust")
    assert exp.mode == "nominal"                     # default: nothing changes for a normal run
    out = exp.enable_pvt_robust_mode("test")
    assert out["mode"] == "pvt_robust" and len(out["corners"]) == 12
    return exp


def test_nominal_is_default_and_switch_refused_after_a_simulation():
    exp = SizingExperiment(batch_size=8, run_id="test_pvt_nominal")
    assert exp.mode == "nominal" and exp.design_space()["mode"] == "nominal"
    r = exp.simulate(NOMINAL_BEST, rationale="nominal reference", agent="test")
    assert "failing_corners" not in r                # nominal output format unchanged
    assert r["feasible"]                             # the nominal design passes at TT 27 C
    with pytest.raises(ValueError, match="before the first simulation"):
        exp.enable_pvt_robust_mode("too late")
    assert exp.mode == "nominal"


def test_robust_simulate_is_worst_case_over_12_corners(robust):
    r = robust.simulate(NOMINAL_BEST, rationale="robust check of the nominal best", agent="test")
    env = robust.evaluation_env
    assert env.pvt_robust and len(env.corner_specs) == 12
    for k in env.dict_targets:                       # worst case of every spec
        values = [s[k] for s in env.corner_specs]
        expected = max(values) if k in env.LOWER_IS_BETTER else min(values)
        assert math.isclose(r["specs"][k], expected, rel_tol=1e-3)
    # this design is feasible at TT 27 C but not in all corners
    assert not r["feasible"] and r["reward"] < 0.3
    assert "ugbw" in r["violated"]
    assert any("100C" in c for c in r["failing_corners"])
    assert "100C" in r["worst_corner"]["ugbw"]
    cand = robust.by_id[r["id"]]
    assert cand["robust"]["op_corner"] in r["failing_corners"]


def test_robust_fom_matches_the_environment(robust):
    cand = robust.best
    env = robust.evaluation_env
    env.simulate(cand["parameters"])                 # fresh corner_specs of this design
    env.cur_norm_specs = env.normalize_specs(env._worst_case(env.corner_specs))
    expected = env.robust_reward_computation()
    got = robust_fom(env, env._worst_case(env.corner_specs), env.corner_specs)
    assert math.isclose(got[0], expected[0], abs_tol=1e-12) and got[1] == expected[1]
    assert math.isclose(cand["reward"], expected[0], abs_tol=1e-9)


def test_operating_point_and_corner_check_in_robust_mode(robust):
    op = robust.operating_point()
    assert op["corner"].endswith("(worst corner of this design)")
    assert op["devices"] and op["circuit"]["I_total_uA"] > 0
    cc = robust.corner_check(rationale="consistency", agent="test")
    assert "candidate" in cc and not cc["feasible_in_all_corners"]
    # quick runs use a 5 us transient instead of 30 us: same failing corners, FoM close
    assert set(cc["failing_corners"]) == set(robust.best["robust"]["failing_corners"])
    assert abs(cc["worst_case_fom"] - robust.best["reward"]) < 0.02


def test_rl_tools_in_robust_mode(robust):
    calls0 = robust.simulator_calls
    s = robust.seed_rl(k=2, repeat=8, anchor_steps=20)      # only 1 expert design so far
    assert s["replay_size"] >= 8
    w = robust.warmup(2, around_best=True, n_params=2)
    assert w["steps_completed"] == 2 and "error" not in w
    t = robust.train(2, noise_sigma=0.05)
    assert t["steps_completed"] == 2 and "error" not in t and t["updates_performed"] == 2
    assert robust.simulator_calls == calls0 + 4      # one call per design, not per corner
    status = robust.get_status(3)
    assert status["mode"] == "pvt_robust"
    assert status["corner_ngspice_runs"] >= 12 * robust.simulator_calls
    for c in status["best"]:
        assert "failing_corners" in c
    summary = json.load(open(robust.out_dir / "summary.json"))
    assert summary["mode"] == "pvt_robust" and "failing_corners" in summary["best"]


def test_mcp_server_exposes_the_switch():
    import asyncio
    import mcp_server
    server = mcp_server.create_server(SizingExperiment(batch_size=8, run_id="test_pvt_mcp"))
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert "enable_pvt_robust_mode" in names and "corner_check" in names
