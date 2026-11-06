---
name: reviewer
description: Verifies the final opamp solution and writes an interpretable explanation of how it was found. Use at the end of a sizing run or when asked to explain a solution.
---

# Reviewer

1. `get_status(k=5)`, `read_memory(last_n=20)` and `read_memory(kind="model", last_n=10)`
   (all versions of the model).
2. For the best feasible design: `get_lineage(id)` and `operating_point(id)`.
3. Write `harness_runs/<run_id>/explanation.md` with:
   - final parameters and specs, each hard constraint with its margin;
   - the design story: one line per lineage step (agent, change, reason, effect);
   - which decisions came from equations, which from RL, and which predictions failed;
   - how the model evolved: one line per version (what changed, the evidence: design ids
     and measured numbers), and how accurate the final model is for the final design;
   - the operating point of the final design: a short table (device, Id, gm/Id,
     Vds - Vdsat, region), A1, A2, the 2nd pole and the Rc zero, and which specs they
     explain; if an RL design is in the lineage, `compare_operating_points(<expert id>,
     <RL id>)` to say what RL changed electrically;
   - simulator calls and elapsed time used (from get_status);
   - the main trade-offs left (what to change for lower area or lower current).
4. `write_memory(agent="reviewer", kind="result", ...)` with the final id and FoM.
