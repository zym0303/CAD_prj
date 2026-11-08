# Sizing a two-stage Miller opamp with RL and an LLM-based agentic harness

KU Leuven, Computer-Aided IC Design 2026–2027 — Afonso de Mello (r1071179), Yumeng Zhang (r1074480).
The report (`Computer_Aided_IC_Design_Report.pdf`) explains the milestones; this file explains how to
run the code and where every result of the report comes from.

## 1. Requirements and setup

- Linux or macOS, **ngspice** on the `PATH` (we used ngspice-36; the wrapper also accepts the course
  server binary), **Python 3.12** for everything except the TAs' SAC baseline.
- Python packages: numpy scipy matplotlib pyyaml pandas gymnasium torch `mcp[cli]` pydantic pytest.

```bash
# Linux (uv) — the same packages setup_mac.sh installs on macOS
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python numpy scipy matplotlib pyyaml pandas gymnasium torch "mcp[cli]" pydantic python-dotenv pytest
source .venv/bin/activate
# macOS: bash setup_mac.sh   (installs ngspice + uv with Homebrew, creates .venv, checks ngspice runs the netlist)
```

The TAs' SAC baseline (`Reference_Designs/milestone3_baseline/*.cpython-39-x86_64-linux-gnu.so`) is a
compiled module for **Python 3.9 on Linux x86-64**; it needs its own environment:

```bash
uv venv --python 3.9 .venv39
uv pip install --python .venv39/bin/python numpy scipy matplotlib pyyaml pandas gymnasium torch
```

`no_backup/` holds the netlists and ngspice output of every simulation; `bash clean.sh` empties it.

## 2. Unit tests (run before everything else)

```bash
pytest -q                      # all 6 files, ~2.5 min (86 tests, 400+ subtests)
pytest -q test_dut.py          # milestone 1: simulator interface vs. the TA reference designs
pytest -q test_circuit_env.py  # milestone 2: action_refine, normalisation, reward, reset/step, end to end
pytest -q test_td3_agent.py    # milestone 3: TD3 update rules, replay buffer, a short learning run
pytest -q test_quick_analysis.py test_op_data.py   # optional task 2: cheap analyses and transistor data
pytest -q test_pvt_robust_harness.py               # optional task 1: PVT-robust mode of env and harness
python smoke_test_harness.py   # milestone 4 backend without an LLM: MCP tools on real ngspice (~20 sims)
```

The outputs of the last complete test run are in `test_results/` (one file per test file + `README.md`).

## 3. Milestone 3 — the RL sizer

```bash
# final configuration (w 128, γ 0), 5000 simulations, seed 123456  -> output_figs/final_g0/, solutions/final_g0/
python td3_runner.py --max_sims 5000 --seed 123456 --w 128 --gamma 0.0 --run_id final_g0
# the γ 0.99 variant
python td3_runner.py --max_sims 5000 --seed 123456 --w 128 --gamma 0.99 --run_id final_g099
# TAs' SAC baseline on the same environment and budget (Python 3.9 venv)
.venv39/bin/python baseline_runner.py --max_sims 5000 --seed 123456 --run_id sac_baseline
```

`td3_runner.py` options: `--seed --noise_sigma --batch_size --w --pi_lr --q_lr --gamma --tau
--actor_update_interval --hidden_size --max_sims --run_id [--pvt_robust]`. A run writes
`output_figs/<run_id>/` (`history.csv` per step, `summary.json`, learning-curve and Pareto plots) and
`solutions/<run_id>.csv` (every feasible design); at the end it exports the current–area Pareto designs
of the run to `solutions/<run_id>/` (netlists `pareto_NN_stepSSSS.cir` + `pareto_solutions.csv` with
parameters, specs and FoM).

**The RL deliverable** (Pareto netlists after 5000 simulations) is
`solutions/milestone3_final/td3_gamma0/final_g0/` — see `solutions/README.md`.

Reproducing the experiments of the report:

| report | command | output |
|---|---|---|
| §3.3 sweep, seed 123456 | `bash run_sweep.sh` (12 configs × 2000 sims) | `output_figs/sw_*` |
| §3.3 sweep, seeds 7 and 42 + §3.4 seeds | `bash run_rl_overnight.sh` (28 runs, 8 in parallel) | `output_figs/sw_*_s7, _s42, final_*_s*, sac_baseline_s*` |
| §3.4 extra seeds of one configuration | `GAMMA=0.0 SEEDS="7 42 1 2" SAC_SEEDS="" bash run_rl_seeds.sh` | `output_figs/final_g0_s*` |
| Fig. 3, Fig. 4, Appendix A | `python plot_sweep_groups.py sweep` and `python plot_sweep_groups.py grid` | `output_figs/sweep_3seeds/` |
| Fig. 5, Table 3 | `python plot_sweep_groups.py final`; `python seed_table.py final` | `output_figs/baseline_cmp_seeds/`, `output_figs/comparison/final_seeds.*` |

## 4. Milestone 4 — the LLM-based agentic harness

Components: the MCP server `mcp_server.py` wrapping the tools of `sizing_tools.py` (class
`SizingExperiment`: simulate, sweep, warmup, train, seed_rl, get_status, get_lineage, write/read_memory,
and the optional-task tools quick_analysis, operating_point, compare_operating_points, corner_check,
enable_pvt_robust_mode), and the instruction skills in `.agents/skills/` (hidden folder):
`opamp-harness` (orchestrator), `circuit-analyst`, `diagnoser`, `sizer`, `rl-strategist`, `reviewer`.

The LLM client is Google's **Antigravity CLI (`agy`)** with Gemini 3.8 Flash. Register the server once
(from the project folder, so the paths are absolute):

```bash
agy mcp add --type stdio --env PATH="$PATH" cad -- "$PWD/.venv/bin/python" "$PWD/mcp_server.py"
```

Run the harness — one fixed prompt, everything else comes from the skills:

```bash
agy -p "Use the opamp-harness skill to size the opamp (full mode)." --model gemini-3.8-flash-high
# quick check (analyst + one diagnoser/sizer round, <= 5 simulations, no RL):
agy -p "Use the opamp-harness skill, test mode." --model gemini-3.8-flash-high
# optional task 1: every design simulated in the 12 PVT corners
agy -p "Use the opamp-harness skill to size the opamp in PVT-robust mode." --model gemini-3.8-flash-high
```

Default budget: 1000 simulator calls and 40 hand decisions (the prompt may override them, e.g.
"budget 1500 sims"). A run writes `harness_runs/<run_id>/` (`log.csv` with every simulated design, its
agent, parent, changed parameters, rationale and result; `memory.jsonl`; `summary.json`; the reviewer's
`explanation.md`), `solutions/<run_id>.csv` and `output_figs/<run_id>/`. `bash run_harness_batch.sh`
runs N independent sessions in a row and moves each run's outputs out of the project so that the next
session cannot read them (`restore_past_runs.sh` brings them back); `python agy_token_usage.py <conversation.db>`
extracts the token counts.

Results of the report:

| report | command | output |
|---|---|---|
| Table 4.3 / §4.4 (best run `harness_20261106_232516`, FoM 0.730, 900 sims, 1055 s) | data in `harness_runs/milestone4/` | — |
| Fig. 6 trace of the best run | `python plot_run_trace.py harness_20261106_232516 --mark 20 625 730` | `output_figs/comparison/run_20261106_232516_trace.png` |
| Fig. 7, Table 6 harness vs. TD3 alone | `python compare_runtime.py --harness "LLM harness (task 1)" harness_20261106_222948 harness_20261106_224902 harness_20261106_230657 harness_20261106_232516 harness_20261106_234417 --rl "TD3 alone, w 128, γ 0" final_g0 --out harness_vs_td3g0_runtime` | `output_figs/comparison/harness_vs_td3g0_runtime.{png,csv}` |
| Table 7 token usage | `output_figs/comparison/agy_token_usage.csv` | — |
| §5.2 with vs. without cheap analyses | `python plot_group_compare.py --a "task 1" <5 ids> --b "task 1+2" harness_20261107_114002 harness_20261107_115759 harness_20261107_121945 --out harness_task1_vs_task12` | `output_figs/comparison/harness_task1_vs_task12.*` |

## 5. Where things are

| path | content |
|---|---|
| `ngspice_interface/` | milestone 1: netlist template (`files/input_netlists/TwoStage.cir`), YAML design space, `ngspice_wrapper.py`, `dut_testbench.py` (spec extraction), `area_estimation.py`, `quick_analysis.py` and `op_data.py` (optional task 2) |
| `circuit_env.py` | milestone 2: the Gym-style environment (`action_refine`, `normalize_specs`, `reward_computation`, `reset`, `step`; `pvt_robust=True` for optional task 1) |
| `td3/agent.py`, `td3/buffer.py`, `td3_runner.py` | milestone 3: TD3 agent, replay buffer, episodic training loop |
| `baseline_runner.py` | the TAs' SAC baseline on our environment with the same budget and logging |
| `sizing_tools.py`, `mcp_server.py`, `.agents/skills/` | milestone 4: tools, MCP server, instruction skills |
| `harness_runs/`, `output_figs/`, `solutions/` | run data, filed by report section — each has a `README.md` |
| `test_*.py`, `test_results/` | unit tests and their recorded output |
| `Reference_Designs/` | TA reference designs (`references.csv`) and the compiled SAC baseline |
| `Milestones_Details/` | our notes and diagrams per milestone |
| `AGY_RUNS.md`, `harness_versions/` | the development history of the harness (early runs and skill versions v1–v4) |
| `compare_runs.py`, `seed_table.py`, `plot_sweep_groups.py`, `compare_runtime.py`, `plot_run_trace.py`, `plot_group_compare.py`, `plot_harness_runs.py`, `compare_harness.py`, `compare_references.py`, `plot_gain.py` | analysis and plotting scripts behind the figures |
