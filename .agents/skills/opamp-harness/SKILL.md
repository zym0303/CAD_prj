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
| analyst | circuit-analyst | Explain topology, derive a first design from equations | design_space, simulate (1-2), write_memory |
| diagnoser | diagnoser | Find the binding spec of the current best and pick the lever | get_status, read_memory, write_memory |
| sizer | sizer | One targeted change per simulation, predicted then checked | simulate, read_memory, write_memory |
| rl | rl-strategist | Run TD3 anchored on the best expert design (local refinement) | seed_rl, warmup, train, get_status |
| reviewer | reviewer | Verify and explain the final solution | get_status, get_lineage, read_memory |

## Modes (pick from the user's words; default = full)

| Mode | Triggered by | Workflow |
|---|---|---|
| full | "full", "with RL", or no mode given | phases 1-5 below |
| no-rl | "without RL", "no RL", "hand only" | phases 1, 2, 5 (phase 2 up to 25 sims) |
| test | "test", "quick" | analyst + one diagnoser/sizer round, <= 5 sims, no RL, get_status(k=3), stop |

Budgets (the user may override them, e.g. "budget 1500 sims, 30 hand sims"):
- total simulator calls: 1000 (default);
- hand simulations (analyst + sizer): 40. These cost LLM tokens; RL simulations barely do.
Start by stating the mode and both budgets in one line. This skill is the full
instruction; the user does not repeat the steps.

## Phases (full mode)

1. Feasibility (analyst, then diagnoser -> sizer rounds), <= 25 simulations:
   until a design is feasible (FoM > 0.3).
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

## Stopping rule (budget only, no FoM target)

There is no target FoM: always keep improving until a budget is used.
- Moving between phases is decided by stalls (the phase rules above), never by the FoM value.
- After phase 4, if both budgets have room left: repeat phase 3 (RL anchored on the new
  best, at most the remaining total budget) and phase 4, while hand simulations remain.
- Stop and go to phase 5 when the total budget is used, or the hand budget is used and the
  last RL round gave < 0.005 improvement (nothing left that is cheap in tokens).
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
  result/lesson), at most a few sentences, with candidate ids and numbers.
- Every `simulate` call needs a rationale with a prediction (which spec moves, which way).
- Simulations are expensive. Never simulate to "see what happens".
- Narrate each decision for the user in 1-3 sentences: what, why, expected effect.
