# solutions/ — feasible designs and Pareto netlists of every run

Every run writes `solutions/<run_id>.csv` while it trains (one row per feasible design: simulation
step, specs, parameters, FoM), and `td3_runner.py` / `baseline_runner.py` finish by exporting the
current–area Pareto-optimal designs of that run to `solutions/<run_id>/`:

    solutions/<run_id>/pareto_solutions.csv     Solution, Simulation step, Reward (FoM), Specs, Circuit Params, Netlist
    solutions/<run_id>/pareto_NN_stepSSSS.cir   the regenerated ngspice netlist of each Pareto design

New runs land at the top level of `solutions/`; the finished runs of the report are filed as below.
The analysis scripts (`compare_runs.py`, `seed_table.py`, `plot_sweep_groups.py`, `compare_runtime.py`)
find a run's csv in either place.

## The RL deliverable (milestone 3): `milestone3_final/`

5000-simulation runs of the final TD3 configuration and of the TAs' SAC baseline.

| folder | agent | configuration | seeds (run ids) |
|---|---|---|---|
| `td3_gamma0/` | **our TD3, final configuration** | w 128, γ 0, σ 0.1, batch 128, lr 3e-4 / 1e-3, τ 0.005 | `final_g0` (123456), `final_g0_s1`, `_s2`, `_s7`, `_s42` |
| `td3_gamma099/` | our TD3, γ 0.99 variant | as above with γ 0.99 | `final_g099` (123456), `_s1`, `_s2`, `_s7`, `_s42` |
| `sac_baseline/` | TAs' SAC baseline (`baseline_runner.py`) | TA defaults (batch 100, w 100, lr 3e-4) | `sac_baseline` (123456), `_s7`, `_s42` |

**Best RL solution reported:** `milestone3_final/td3_gamma0/final_g0/` — 7 Pareto netlists and
`pareto_solutions.csv` (best FoM 0.658 after 5000 simulations, seed 123456; the five seeds of this
configuration give 0.646 ± 0.032). Per-seed figures and tables: `output_figs/baseline_cmp_seeds/`.

## Hyperparameter sweep (milestone 3.3): `milestone3_sweep/`

2000-simulation runs, one parameter changed at a time from the default (σ 0.1, batch 128, w 300,
lr 3e-4 / 1e-3, γ 0.99), three seeds each: `sw_<config>` (seed 123456), `sw_<config>_s7`, `sw_<config>_s42`.
Configs: `base`, `noise0.05/0.2/0.3`, `gamma0.5/0.0`, `batch64/256`, `w128/1000`, `lr_slow/lr_fast`.
Tables and figures: `output_figs/sweep_3seeds/`.

## LLM harness: `milestone4/`, `milestone4_optional2/`, `development/`

`harness_<date>_<time>.csv`: the feasible designs each harness run simulated (LLM steps, RL warm-up
and RL training alike), filed like `harness_runs/`:
`milestone4/` = the five runs of report §4 (best: candidate 730 of `harness_20261106_232516`, FoM 0.730),
`milestone4_optional2/` = the four cheap-analysis runs of §5.2, `development/` = earlier runs not in the report.
The full trace of a run — every simulated design with its agent, parent, changed parameters, rationale
and result, the agents' memory notes and the reviewer's explanation — is in `harness_runs/<group>/<run_id>/`
(`log.csv`, `memory.jsonl`, `summary.json`, `explanation.md`).
