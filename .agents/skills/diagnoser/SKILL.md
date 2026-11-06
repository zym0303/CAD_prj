---
name: diagnoser
description: Diagnoses the current best opamp design, identifies the binding or violated specification and chooses which circuit lever to move next. Use between sizing iterations.
---

# Diagnoser

1. `read_memory(last_n=8)`, `get_status(k=3)` and `operating_point()`: the best design's
   transistor data (0 simulations).
2. Classify the best design:
   - infeasible: list violated constraints, ordered by normalized violation (most negative
     first for gain/phm/slewRate/ugbw, most positive for noise).
   - feasible: the margin of each hard constraint (normalized value). Large margins are
     wasted current or area: name the one to trade away.
   Feasible mode (phase 2/4): FoM = 0.3 - z_area - z_current, so only current and area
   count. Current = 30 uA + I_tail + I_2 is usually the bigger term. Spend the largest
   margins: SR and UGBW margins allow less I_tail / I_2; a large gain margin allows
   wider (lower-Vov) devices at lower current. Global lever: a larger S_mn3 lowers BOTH
   mirrored currents at once (I = 30 uA * S/S_mn3) and keeps the balance condition.
   Area: Cc dominates; drop Cc where PM margin allows, then reduce large m*W*L devices.
3. Choose ONE lever and explain the mechanism, using the equations of circuit-analyst.
   Prefer levers that fix the worst spec without breaking a spec with a small margin.
   Known couplings: Cc trades PM against UGBW/SR/area; I_2 trades PM/SR against current;
   longer L trades gain against UGBW/PM.
   Use the operating point: fix its warnings first (a device in triode or the output at a
   rail breaks the gain; the warning says which side to change). Its notes say what really
   limits UGBW and PM (2nd pole gm6/(2 pi CL) vs UGBW, the Rc zero), so choose the lever
   from the measured gm and gds, not only from the textbook equations. Quote at least one
   operating-point number in the decision.
4. Stall check: if the last 3 sizer results in memory did not improve the best reward,
   or the design is feasible with all margins small, decide "hand over to rl".
5. `write_memory(agent="diagnoser", kind="decision", ...)`: best id, binding spec, chosen
   lever, the operating-point number behind it, expected trade-off, or the handover
   decision with the reason.
