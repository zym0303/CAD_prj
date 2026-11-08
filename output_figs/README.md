# output_figs/ — training outputs and the figures of the report

Every RL run (`td3_runner.py`, `baseline_runner.py`) writes `output_figs/<run_id>/`: `history.csv`
(one row per step: simulations, FoM, best FoM, losses, wall time), `summary.json`, `max_reward.png`,
`average_score.png`, `pareto.png`; the network weights `td3_*` stay on disk but are not tracked.
`output_figs/<run_id>.log` is the console log of the run. Every harness run writes its two plots to
`output_figs/<run_id>/`. New runs land at the top level; the finished runs are filed as below, and the
analysis scripts find them in either place (`compare_runs.run_dir`).

| folder | content | report |
|---|---|---|
| `milestone3_final/td3_gamma0/` | TD3 w 128, γ 0: `final_g0` (seed 123456), `_s1`, `_s2`, `_s7`, `_s42`, 5000 sims | §3.4, §4.5 |
| `milestone3_final/td3_gamma099/` | TD3 w 128, γ 0.99: `final_g099` + 4 seeds | §3.4 |
| `milestone3_final/sac_baseline/` | TAs' SAC baseline: `sac_baseline` + seeds 7, 42 | §3.4 |
| `milestone3_sweep/` | hyperparameter sweep, 12 configs × seeds 123456 / 7 / 42, 2000 sims (`sw_*`) | §3.3 |
| `sweep_3seeds/` | **Fig. 3** `sweep_grid.png`, **Fig. 4** `gamma_score.png`, Appendix A `noise/gamma/batch/warmup/lr.png`, tables `*.csv` (`plot_sweep_groups.py sweep`, `grid`) | §3.3, App. A |
| `baseline_cmp_seeds/` | **Fig. 5** `td3_vs_sac.png`, `td3_vs_sac.csv`, `td3_vs_sac_per_seed.csv` (`plot_sweep_groups.py final`) | §3.4 |
| `comparison/` | **Fig. 6** `run_20261106_232516_trace.png` (`plot_run_trace.py`), **Fig. 7** + Table 6 `harness_vs_td3g0_runtime.{png,csv}` (`compare_runtime.py`), Table 7 `agy_token_usage.csv`, `final_seeds.*` / `sweep_seeds.csv` (`seed_table.py`), `harness_task1_vs_task12.*` (§5.2) | §4, §5.2 |
| `milestone4/` | plots of the five harness runs of §4 | §4 |
| `milestone4_optional2/` | plots of the four cheap-analysis harness runs | §5.2 |
| `optional1_pvt/` | PVT-robust TD3 runs `pvt_robust_v1..v3`, the robust harness run, **Fig. 8** in `comparison_pvt/` | §5.1 |
| `development/` | not in the report: single-seed comparisons superseded by the 3-seed ones (`comparison_{noise,gamma,other,baseline}`, `comparison_old/`), plots of the early harness runs, smoke runs | — |
