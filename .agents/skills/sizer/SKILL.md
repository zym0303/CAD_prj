---
name: sizer
description: Applies a targeted, predicted parameter change to the opamp and checks the prediction with one simulation. Use after the diagnoser has chosen a lever.
---

# Sizer

1. `read_memory(agent="diagnoser", last_n=1)` and the last 3 sizer entries.
2. Change 1-3 parameters, all serving the chosen lever. Send only the changed parameters
   to `simulate` (the others come from the best design, or from `base_id`). Values must be
   on the grid; if rejected, use the nearest allowed value the error gives.
   Screen first when the outcome is uncertain: ONE `quick_analysis` with 3-8 variants
   of the lever (e.g. three mn5/mp3 pairs, each with two Cc values), measuring the specs
   at risk ("op" + "ac" for current, gain, UGBW and PM; add "tran" if the SR margin is
   < 20 %, "noise" if the noise margin is < 20 %). Drop variants with `op_warnings` or
   violations; `simulate` only the best one (highest `fom_if_feasible`, or reward). If the
   best lower-current variant misses UGBW or PM by < 3 %, screen Cc/Rc around it once more
   before giving the lever up.
3. Rationale format: "<change>: <mechanism>; expect <spec> <old> -> <new estimate>"
   (with a screened variant: "screened: <spec> <value>").
4. Compare the result with the prediction:
   - right direction: keep it; next step may move the same lever further.
   - wrong direction or another spec broke: find why with
     `compare_operating_points(<base id>, <new id>)` (which device quantity moved
     unexpectedly), revert by using base_id of the previous best next time.
5. `write_memory(agent="sizer", kind="result", ...)`: id, prediction vs. outcome, and a
   `lesson` entry when a prediction failed (e.g. "mp3 x2 lowered PM: Cgs of mp3 loads stage 1").
6. At most 3 simulations per diagnoser decision, then return to the diagnoser.
7. If a lever moved its spec by less than half of the prediction twice, the model behind
   it is wrong: say so in a lesson and ask the diagnoser for a different lever.
8. Fine tuning of ONE parameter (Rc, Cc, a multiplicity): screen 5-8 grid values with
   `quick_analysis` (only the analyses of the specs it moves) and `simulate` the best one,
   instead of repeated simulate calls. Use `sweep` (real simulations, all become
   candidates) only in phase 4 polish, when the feasible neighbours are wanted for the
   Pareto front. A sweep counts as one decision.
9. Check the balance condition (circuit-analyst) before touching mn4, mn5, mp1 or mp3.
