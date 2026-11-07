---
name: opamp-harness
description: Orchestrates explainable sizing of the two-stage Miller opamp with the cad MCP tools. Use when asked to size, optimize or improve the opamp, or to run the sizing harness.
---

# Opamp sizing harness (orchestrator)

You coordinate five specialist agents. Each one has its own skill; read that skill
before acting in its role, and act ONLY in that role until it hands over.
If subagents are available, start each role as a subagent with its skill and pass it
only the memory it needs. Otherwise play the roles one after another in this session.

| Role (agent name) | Skill | Job | Tools |
|---|---|---|---|
| analyst | circuit-analyst | Explain topology, derive a first design from equations | design_space, quick_analysis, simulate (1-2), write_memory |
| diagnoser | diagnoser | Find the binding spec of the current best and pick the lever | get_status, operating_point, read_memory, write_memory |
| sizer | sizer | One targeted change per simulation, predicted then checked | quick_analysis, simulate, compare_operating_points, read_memory, write_memory |
| rl | rl-strategist | Run TD3 anchored on the best expert design (local refinement) | seed_rl, warmup, train, get_status |
| reviewer | reviewer | Verify and explain the final solution | get_status, get_lineage, operating_point, corner_check, read_memory |

## Modes (pick from the user's words; default = full)

| Mode | Triggered by | Workflow |
|---|---|---|
| full | "full", "with RL", or no mode given | phases 1-5 below |
| no-rl | "without RL", "no RL", "hand only" | phases 1, 2, 5 (phase 2 up to 25 sims) |
| test | "test", "quick" | analyst + one diagnoser/sizer round, <= 5 sims, no RL, get_status(k=3), stop |
| robust | "PVT-robust", "robust", "12 corners", "optional task 1" | `enable_pvt_robust_mode` FIRST, then phases 1-5 with the robust rules below (can be combined with no-rl or test) |

`enable_pvt_robust_mode` is called ONLY in robust mode, and only as the very first tool call
(it is refused after the first simulation). In every other mode never call it: those runs
are sized at the nominal corner (TT, 1.2 V, 27 C) exactly as before.

Budgets (the user may override them, e.g. "budget 1500 sims, 30 hand sims"):
- total simulator calls: 1000 (default);
- hand decisions: 40. Each simulate OR sweep call counts as one (a sweep of 6 values is
  one decision). Decisions cost LLM tokens; RL and sweep simulations barely do.
- cheap analyses: at most 30 `quick_analysis` calls (<= 10 variants each), 20
  operating-point lookups (`operating_point`, `compare_operating_points`) and 3
  `corner_check` calls. They are NOT simulator calls and NOT hand decisions; their ngspice
  runs are reported separately (quick_runs).
Start by stating the mode and both budgets in one line (robust mode: its own budgets, below). This skill is the full
instruction; the user does not repeat the steps.

## Phases (full mode)

1. Feasibility (analyst, then diagnoser -> sizer rounds), <= 25 simulations:
   until a design is feasible (FoM > 0.3).
2. Optimization (diagnoser in feasible mode -> sizer), <= 15 simulations:
   trade the excess margins for less current and area. Ends after 4 sizer simulations in
   a row that improve the best FoM by less than 0.005. It does NOT end while the current
   is above 1.5x its target and a current-lowering lever has not been screened yet.
3. RL refinement (rl), <= 800 simulations or the remaining total budget: TD3 anchored on the best expert design,
   exploring its neighbourhood. Also produces the feasible designs for the Pareto front.
4. Polish (diagnoser -> sizer), <= 6 simulations, on the RL best.
5. Review (reviewer) and final summary: get_status(k=3), then 5 lines: best id, FoM,
   feasible, simulator calls, elapsed time.

If phase 1 is not feasible after 25 simulations, go to phase 3 anyway (anchored on the
best infeasible design), then back to phase 2.

## Stopping rule (budget only, no FoM target)

There is no target FoM: always keep improving until a budget is used.
- Moving between phases is decided by stalls (the phase rules above), never by the FoM value.
- MANDATORY LOOP: after every phase 4, call get_status. If simulator_calls < total budget
  - 100 AND hand decisions remain, go back to phase 3 (rl round 2+ settings, anchored on the
  new best), then phase 4 again. Being "converged" or "optimal" is not a reason to skip
  this: unused budget is wasted. The reviewer may start only when simulator_calls >= total
  budget - 100, or hand decisions are used up.
- In phase 4, prefer one `sweep` (e.g. Rc or Cc over 5-8 grid values) to several simulate
  calls: same information, far fewer tokens.
- Before each phase, check get_status: never start a batch that would exceed the budget;
  shrink it instead (e.g. train(n_steps=remaining // 1.1)).
- Reaching feasibility is NOT a reason to stop: it starts phase 2.

Narrate every decision for the user in 1-3 sentences: role, what, why, expected effect.

## Cheap analyses (optional task 2): use them to save simulations

A simulation costs ~1 s of ngspice and one simulator call; `quick_analysis` runs only the
analyses you need (op/ac/noise ~0.01 s, a 5 us transient ~0.1 s) for up to 10 variants at
once, and `operating_point` reads transistor data that every simulation already saved.
- Screen, then simulate: whenever you would try several values or are unsure whether a
  change breaks a spec, screen the variants with ONE `quick_analysis` and `simulate`
  only the best one. Measure only the specs at risk (op = current, ac = gain/UGBW/PM,
  noise, tran = slew rate).
- Explain with data: before choosing a lever, and after a failed prediction, read the
  operating point (gm, gm/Id, Vds - Vdsat, I_tail, I_2, p2 vs UGBW) instead of guessing.
- A quick result is never a design result: only `simulate` creates candidates. Never
  report, seed or compare a design that was only quick-analysed.
- Do not screen what an equation already answers with confidence: cheap is not free
  (each call is an LLM turn).

## Robust mode (optional task 1)

After `enable_pvt_robust_mode`, every `simulate`, `sweep` and RL step evaluates the design
in the 12 corners {TT,SS,FF} x {1.2 V, 1.0 V} x {0 C, 100 C}; its specs are the WORST case
and it is feasible only if every corner passes. Each design also returns `failing_corners`
and `worst_corner` (the corner that sets each hard spec); `operating_point` shows the
design's worst corner. Same phases, same roles, with these changes:
- Default budgets: 600 simulator calls in total (each design is 12 ngspice runs, ~1-3 s),
  RL phase <= 400, hand decisions 40, corner_check <= 8. The user may override them.
- Screening: `quick_analysis` is single-corner. Screen at the corners that bind (read
  `worst_corner`: typically SS/1.0 V/100 C for UGBW and slew rate, the 0 C corners for phase
  margin), then `corner_check(variant=...)` on the best variant (12 quick runs, 0 simulator
  calls), and `simulate` only a variant whose corner check passes or comes closest.
- Feasible = "passes in all 12 corners". The current target (200 uA) is an optimization
  target, not a hard constraint: robustness may cost current; first reach all-corner
  feasibility, then trade margins for current and area as in phase 2.
- Report the corner trade-off in the narration: which corner sets which spec, and why.

## Rules for every role

- Do NOT read project files, reference designs or configs, and do not explore the
  folder. The skills and `design_space` contain everything; runtime counts in the
  comparison with the RL sizer, and the design must come from reasoning, not copying.
- Use NO information from earlier runs: do not read other harness_runs folders, solutions,
  logs or memory files of past runs. Only this run's memory (read_memory) and tools.

- Context: start each role by calling `read_memory` (last 5-10 entries). Do not re-read
  the netlist or old tool outputs; the memory is the shared context.
- Memory: end each role with one `write_memory` entry (kind plan/observation/decision/
  result/lesson), at most a few sentences, with candidate ids and numbers.
- Every `simulate` call needs a rationale with a prediction (which spec moves, which way).
- Simulations are expensive. Never simulate to "see what happens".
- Narrate each decision for the user in 1-3 sentences: what, why, expected effect.
