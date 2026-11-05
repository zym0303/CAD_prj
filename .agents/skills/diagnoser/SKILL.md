---
name: diagnoser
description: Diagnoses the current best opamp design, identifies the binding or violated specification and chooses which circuit lever to move next. Use between sizing iterations.
---

# Diagnoser

1. `read_memory(last_n=8)` and `get_status(k=3)`.
2. Classify the best design:
   - infeasible: list violated constraints, ordered by normalized violation (most negative
     first for gain/phm/slewRate/ugbw, most positive for noise).
   - feasible: the margin of each hard constraint (normalized value). Large margins are
     wasted current or area: name the one to trade away.
3. Choose ONE lever and explain the mechanism, using the equations of circuit-analyst.
   Prefer levers that fix the worst spec without breaking a spec with a small margin.
   Known couplings: Cc trades PM against UGBW/SR/area; I_2 trades PM/SR against current;
   longer L trades gain against UGBW/PM.
4. Stall check: if the last 3 sizer results in memory did not improve the best reward,
   or the design is feasible with all margins small, decide "hand over to rl".
5. `write_memory(agent="diagnoser", kind="decision", ...)`: best id, binding spec, chosen
   lever, expected trade-off, or the handover decision with the reason.
