---
name: opamp-harness
description: Orchestrates explainable sizing of the two-stage Miller opamp with the cad MCP tools. Use when asked to size, optimize or improve the opamp, or to run the sizing harness.
---

# Opamp sizing harness (orchestrator)

You coordinate six specialist agents. Each one has its own skill; read that skill
before acting in its role, and act ONLY in that role until it hands over.
If subagents are available, start each role as a subagent with its skill and pass it
only the memory it needs. Otherwise play the roles one after another in this session.

| Role (agent name) | Skill | Job | Tools |
|---|---|---|---|
| analyst | circuit-analyst | Explain topology, derive a first design from equations | design_space, simulate (1-2), write_memory |
| modeler | modeler | Turn the textbook equations into this run's model, check it on measured data, correct it during the run (0 simulations) | operating_point, compare_operating_points, get_status, read_memory, write_memory (kind model) |
| diagnoser | diagnoser | Find the binding spec of the current best and pick the lever | get_status, operating_point, read_memory, write_memory |
| sizer | sizer | One targeted change per simulation, predicted then checked | simulate, quick_analysis (op), compare_operating_points, read_memory, write_memory |
| rl | rl-strategist | Run TD3 anchored on the best expert design (local refinement) | seed_rl, warmup, train, get_status |
| reviewer | reviewer | Verify and explain the final solution | get_status, get_lineage, operating_point, compare_operating_points, quick_analysis (corners), read_memory |

## Modes (pick from the user's words; default = full)

| Mode | Triggered by | Workflow |
|---|---|---|
| full | "full", "with RL", or no mode given | phases 1-5 below |
| no-rl | "without RL", "no RL", "hand only" | phases 1, 2, 5 (phase 2 up to 25 sims) |
| test | "test", "quick" | analyst + modeler v1 + one diagnoser/sizer round, <= 5 sims, no RL, get_status(k=3), stop |

Budgets (the user may override them, e.g. "budget 1500 sims, 30 hand sims"):
- total simulator calls: 1000 (default);
- hand decisions: 40. Each simulate OR sweep call counts as one (a sweep of 6 values is
  one decision). Decisions cost LLM tokens; RL and sweep simulations barely do.
- operating-point lookups (operating_point, compare_operating_points): at most 20. They
  use 0 simulations and do not count as hand decisions.
- model versions (modeler): at most 6. They use 0 simulations and do not count as hand
  decisions; the modeler's operating-point lookups count in the 20 above.
- quick analyses (`quick_analysis`, cheap op/ac/noise/short-tran runs, also at other PVT
  corners): at most 30 calls of <= 10 variants each. They are not simulator calls and not
  hand decisions, but they are ngspice runs and are reported separately (quick_runs).
Start by stating the mode and both budgets in one line. This skill is the full
instruction; the user does not repeat the steps.

## Phases (full mode)

1. Feasibility (analyst, then modeler v1, then diagnoser -> sizer rounds), <= 25
   simulations: until a design is feasible (FoM > 0.3).
2. Optimization (diagnoser in feasible mode -> sizer), <= 15 simulations:
   trade the excess margins for less current and area. Ends after 4 sizer simulations in
   a row that improve the best FoM by less than 0.005.
3. RL refinement (rl), <= 800 simulations or the remaining total budget: TD3 anchored on the best expert design,
   exploring its neighbourhood. Also produces the feasible designs for the Pareto front.
4. Polish (diagnoser -> sizer), <= 6 simulations, on the RL best.
5. Review (reviewer) and final summary: get_status(k=3), then 5 lines: best id, FoM,
   feasible, simulator calls, elapsed time.

If phase 1 is not feasible after 25 simulations, go to phase 3 anyway (anchored on the
best infeasible design), then back to phase 2.

Hand over to the modeler (in any phase, within its 6 versions) when:
- the sizer reports a lever that moved its spec by less than half of the prediction twice;
- the diagnoser finds an operating point that contradicts the model (a warning, or a
  different limiting factor than the model assumes);
- an RL round ends with a new best design the model would not have predicted.
Then continue where you were. The model is built in this run only, from textbook
equations and this run's measurements.

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

## Rules for every role

- Do NOT read project files, reference designs or configs, and do not explore the
  folder. The skills and `design_space` contain everything; runtime counts in the
  comparison with the RL sizer, and the design must come from reasoning, not copying.

- Context: start each role by calling `read_memory` (last 5-10 entries). Do not re-read
  the netlist or old tool outputs; the memory is the shared context.
- Memory: end each role with one `write_memory` entry (kind plan/observation/decision/
  result/lesson; the modeler writes kind model), at most a few sentences, with candidate
  ids and numbers.
- Every `simulate` call needs a rationale with a prediction (which spec moves, which way).
- A `quick_analysis` result is never a design result: only `simulate` creates candidates.
  Never report, seed or compare a design that was only quick-analysed.
- Simulations are expensive. Never simulate to "see what happens".
- Narrate each decision for the user in 1-3 sentences: what, why, expected effect.
