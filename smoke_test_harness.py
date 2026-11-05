"""Smoke test of the harness backend with real ngspice, no LLM (~20 simulations).

    python smoke_test_harness.py
"""
import mcp_server  # noqa: F401  (checks the MCP server module imports)
from sizing_tools import SizingExperiment

exp = SizingExperiment(batch_size=8, run_id="smoke")
ds = exp.design_space()
print("params:", len(ds["parameters"]), "| constraints:", ds["hard_constraints"])

mid = exp.evaluation_env.action_refine([0.0] * len(exp.param_names))   # mid-grid design
r1 = exp.simulate(mid, rationale="mid-grid starting point", agent="test")
print("sim 1:", r1["id"], r1["reward"], r1["feasible"], r1["violated"])

r2 = exp.simulate({"cap": 2e-12}, rationale="Cc -> 2p: expect higher UGBW", agent="test")
print("sim 2 (partial):", r2["id"], r2["reward"], "changes:", r2["changes"])

r3 = exp.simulate({"cap": 2e-12}, rationale="duplicate", agent="test")
assert "note" in r3, "duplicate should not be re-simulated"
try:
    exp.simulate({"wn1": 3.3e-7}, rationale="off-grid", agent="test")
    raise AssertionError("off-grid value accepted")
except ValueError as e:
    print("off-grid rejected:", e)

assert abs(exp.param_to_action(mid) - 0).max() < 0.2
back = exp.evaluation_env.action_refine(exp.param_to_action(exp.best["parameters"]))
assert back == exp.best["parameters"], "param_to_action is not the inverse of action_refine"

print("seed+anchor:", exp.seed_rl(k=2, repeat=2, anchor_steps=20))
w = exp.warmup(10)
print("warmup: steps", w["steps_completed"], "sims", w["simulator_calls_used"], w.get("error"))
lw = exp.warmup(5, around_best=True, n_params=2)
print("local warmup: steps", lw["steps_completed"], lw.get("error"))
sw = exp.sweep("res", [1000.0, 2000.0, 3000.0], rationale="Rc sweep test", agent="test")
print("sweep:", [(r["value"], r["reward"]) for r in sw["results"]])
t = exp.train(5, noise_sigma=0.05)
print("train: steps", t["steps_completed"], "updates", t["updates_performed"], t.get("error"))

exp.write_memory("test", "lesson", "smoke test ran")
print("memory:", exp.read_memory(last_n=1)["entries"])
print("lineage:", exp.get_lineage(r2["id"]))
s = exp.get_status(3)
print("status: sims", s["simulator_calls"], "| best", s["best"][0]["reward"], "| replay", s["replay_size"])
print("\nOK - log in harness_runs/smoke/log.csv")
