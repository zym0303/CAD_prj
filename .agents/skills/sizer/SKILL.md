---
name: sizer
description: Applies a targeted, predicted parameter change to the opamp and checks the prediction with one simulation. Use after the diagnoser has chosen a lever.
---

# Sizer

1. `read_memory(agent="diagnoser", last_n=1)` and the last 3 sizer entries.
2. Change 1-3 parameters, all serving the chosen lever. Send only the changed parameters
   to `simulate` (the others come from the best design, or from `base_id`). Values must be
   on the grid; if rejected, use the nearest allowed value the error gives.
3. Rationale format: "<change>: <mechanism>; expect <spec> <old> -> <new estimate>".
4. Compare the result with the prediction:
   - right direction: keep it; next step may move the same lever further.
   - wrong direction or another spec broke: note why (the model was wrong), revert by
     using base_id of the previous best next time.
5. `write_memory(agent="sizer", kind="result", ...)`: id, prediction vs. outcome, and a
   `lesson` entry when a prediction failed (e.g. "mp3 x2 lowered PM: Cgs of mp3 loads stage 1").
6. At most 3 simulations per diagnoser decision, then return to the diagnoser.
