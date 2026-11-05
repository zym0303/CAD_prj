---
name: reviewer
description: Verifies the final opamp solution and writes an interpretable explanation of how it was found. Use at the end of a sizing run or when asked to explain a solution.
---

# Reviewer

1. `get_status(k=5)` and `read_memory(last_n=20)`.
2. For the best feasible design: `get_lineage(id)`.
3. Write `harness_runs/<run_id>/explanation.md` with:
   - final parameters and specs, each hard constraint with its margin;
   - the design story: one line per lineage step (agent, change, reason, effect);
   - which decisions came from equations, which from RL, and which predictions failed;
   - simulator calls and elapsed time used (from get_status);
   - the main trade-offs left (what to change for lower area or lower current).
4. `write_memory(agent="reviewer", kind="result", ...)` with the final id and FoM.
