# harness_runs/ — traces of the LLM-harness runs

Every harness run (one `agy` conversation using the `opamp-harness` skill and the `cad` MCP server)
writes `harness_runs/<run_id>/`:

| file | content |
|---|---|
| `log.csv` | one row per simulator call: sim_call, elapsed_s, candidate_id, source (llm / rl_warmup / rl_train), agent, parent_id, changed parameters, **rationale**, reward, best_reward, feasible, violated, specs, parameters |
| `memory.jsonl` | the notes the agents exchange through `write_memory` (plan / decision / result / lesson) |
| `summary.json` | counters (simulator calls, RL steps, elapsed time) and the best design |
| `explanation.md` | the reviewer's explanation of the final design (lineage, attribution, trade-offs) |
| `op_data.jsonl`, `quick_analyses.jsonl` | optional task 2 only: transistor operating points and cheap analyses |

A new run lands at the top level; the finished runs are filed by the report section they belong to.
The analysis scripts (`compare_runtime.py`, `plot_run_trace.py`, `plot_group_compare.py`, `compare_harness.py`,
`plot_harness_runs.py`) find a run in either place (`compare_runs.harness_dir`).

| folder | report | runs | code version |
|---|---|---|---|
| `milestone4/` | §4 (Table 4.3, best run **harness_20261106_232516**, FoM 0.730) | 222948, 224902, 230657, 232516, 234417 (Nov 6, Gemini 3.8 Flash High) | skills v1.0, 10 MCP tools, nominal corner |
| `milestone4_optional2/` | §5.2 cheap analyses | 110719, 114002, 115759, 121945 (Nov 7) | + quick_analysis, operating_point, compare_operating_points, corner_check |
| `optional1_pvt/` | §5.1 PVT-robust harness | harness_20261107_142524-agy-optional1 | pvt_robust mode (12 corners) |
| `development/` | not in the report: earlier skill versions (Nov 5–6), the Flash-Medium runs (202431, 205408, 212351), smoke / unit-test runs | 14 runs + smoke + test_pvt_* | skills v0.1 – "run 4" |

Per-run token usage (LLM calls, input / cached / output tokens) is in `output_figs/comparison/agy_token_usage.csv`.
The raw agy transcripts are archived outside the repository (available on request).
