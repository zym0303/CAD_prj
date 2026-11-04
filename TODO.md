# CAD Project 2026 — To-Do

**Deadline: Sunday 8 November 2026, 23:59 (Brussels time)**

## Milestone 1 — Simulator interface
Files: `TwoStage.cir`, `dut_testbench.py`, `test_dut.py`
- [x] Fill the `???` lines in `TwoStage.cir`: `wrdata` for tran / ac / noise / dc, plus the `noise` command (makes test_3 pass)
- [x] Write `find_dc_gain`, `find_ugbw`, `find_phm`, `find_slew_rate` in `dut_testbench.py` (makes test_4 pass)
- [x] Correctness test: several sizings, compare Python results with ngspice `meas`
- [x] Get `reference_designs.csv` from the TAs, put it in `CAD/`, check test_5 passes
- [x] Add a plot for gain, for each of the frequencies to check it properly
- [x] Confirm with the TAs: reference designs reproduced only at 27 °C (25 °C: design 1 gain/noise −7.8 %), see Milestone_1_explained.md §6
- [ ] Report: circuit topology, how each spec is measured, unit test as proof

## Milestone 2 — Circuit environment
File: `circuit_env.py` (can be done in parallel with milestone 1)
- [x] Convert actions in [-1, 1] to real parameter values (line ~75); reproduces all 5 TA reference designs (`action_*` -> `param_*`)
- [x] Simulate and measure for a set of parameters (line ~120); failed simulations give worst-case specs instead of crashing
- [x] Normalise specs against the targets (line ~174); matches `norm_*` in `Reference_Designs/references.csv`
- [x] `reset()` (line ~227)
- [x] `step()` (line ~257)
- [x] Reward from normalised specs and hard constraints (line ~320); matches the rewards in `Reference_Designs/references.csv`
- [x] Unit test with hand-calculated normalised specs and rewards: `test_circuit_env.py`, 28/28 pass (incl. end-to-end with ngspice)
- [ ] Report: action refinement, normalisation, `step`/`reset`, the test (material in `Milestones_Details/Milestone_2/Milestone_2_explained.md`)

## Milestone 3 — TD3 agent
Files: `td3/agent.py`, `td3_runner.py`
- [ ] Action selection with exploration noise (`agent.py`, line ~89)
- [ ] TD3 learning step: twin critics, target policy smoothing, delayed actor update (`agent.py`, line ~112)
- [ ] Tune in `td3_runner.py`: noise sigma, batch size, warmup steps, actor and critic learning rates
- [ ] 5k-simulation run → plots: max FoM vs. simulation step, and current–area Pareto front
- [ ] Compare with the TAs' baseline agent (`baseline_runner.py`) within 5k simulations
- [ ] Report: agent implementation, episodic loop, hyperparameter choices

## Milestone 4 — LLM agentic harness
- [ ] Install and learn the Antigravity CLI (check Toledo / ask the TAs)
- [ ] Split sizing into sub-tasks; one LLM agent per sub-task (prompt, MCP tools, skills)
- [ ] MCP tools: run a simulation, run the RL sizer
- [ ] Context and memory passing between agents
- [ ] Runtime vs. max FoM comparison against the pure RL sizer (plot or table)
- [ ] Examples of explainability (traceable reasoning and decision steps)
- [ ] Report: agents, tools, context/memory, skills, best solutions with reasoning

## Submission
- [ ] Report PDF, at most 10 pages
- [ ] `Solutions/` folder: netlists of the Pareto designs (after 5k simulations) + a `.csv` with params, specs and reward (FoM)
- [ ] One archive: `[student number]_[last name]_G[group number].zip` with report, project directory and `Solutions/`

## Optional (only if everything else is finished)
- [ ] PVT-robust solutions over 12 corners: {TT, SS, FF} × {1.2 V, 1.0 V} × {0 °C, 100 °C}
- [ ] Cheaper analyses (DC/AC/selected corners, transistor data) exposed as MCP tools for the harness

## Rough plan
| Day | Work |
|---|---|
| Tue 3 Nov | Milestone 1 (one of us) · start milestone 2 (the other) |
| Wed 4 – Thu 5 Nov | Finish milestone 2 · milestone 3, start the 5k run early |
| Fri 6 – Sat 7 Nov | Milestone 4 · plots and solutions |
| Sun 8 Nov | Report, archive, submit before 23:59 |

## Git routine
- `git pull` before you start working
- Commit and `git push` as soon as something works
- Avoid editing the same file at the same time; claim items above with your name
