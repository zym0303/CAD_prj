---
name: reviewer
description: Verifies the final opamp solution and writes an interpretable explanation of how it was found. Use at the end of a sizing run or when asked to explain a solution.
---

# Reviewer

1. `get_status(k=5)` and `read_memory(last_n=20)`.
2. For the best feasible design: `get_lineage(id)`, `operating_point(id)` and ONE
   `corner_check(candidate_id=id)` (12 PVT corners of the robust mode, ~1 s, 0 simulator
   calls). The design is sized at TT only, so the corner check is a report, not a goal.
3. Write `harness_runs/<run_id>/explanation.md` with:
   - final parameters and specs, each hard constraint with its margin;
   - the design story: one line per lineage step (agent, change, reason, effect);
   - which decisions came from equations, which from RL, and which predictions failed;
   - the operating point of the final design: a short table (device, Id, gm/Id,
     Vds - Vdsat, region), A1, A2, the 2nd pole and the Rc zero, and which specs they
     explain; if an RL design is in the lineage, `compare_operating_points(<expert id>,
     <RL id>)` to say what RL changed electrically;
   - the PVT check: worst-case value and corner of every spec, the failing corners and
     the worst-case FoM (from corner_check);
   - how the cheap analyses were used: quick_calls, quick_runs, operating-point lookups,
     and which simulations they replaced or which decisions they changed;
   - simulator calls and elapsed time used (from get_status);
   - the main trade-offs left (what to change for lower area or lower current).
4. `write_memory(agent="reviewer", kind="result", ...)` with the final id and FoM.
