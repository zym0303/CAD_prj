---
name: diagnoser
description: Diagnoses the current best opamp design, identifies the binding or violated specification and chooses which circuit lever to move next. Use between sizing iterations.
---

# Diagnoser

1. `read_memory(last_n=8)`, `get_status(k=3)` and `operating_point()`: the best design's
   transistor data (0 simulator calls).
2. Classify the best design:
   - infeasible: list violated constraints, ordered by normalized violation (most negative
     first for gain/phm/slewRate/ugbw, most positive for noise).
   - feasible: the margin of each hard constraint (normalized value). Large margins are
     wasted current or area: name the one to trade away.
   Feasible mode (phase 2/4): FoM = 0.3 - z_area - z_current, so only current and area
   count (current = 30 uA + I_tail + I_2; compare z_area and z_current to see which term
   costs more). Spend the largest
   margins: SR and UGBW margins allow less I_tail / I_2; a large gain margin allows
   wider (lower-Vov) devices at lower current. Global lever: a larger S_mn3 lowers BOTH
   mirrored currents at once (I = 30 uA * S/S_mn3) and keeps the balance condition.
   Area: Cc dominates; drop Cc where PM margin allows, then reduce large m*W*L devices.
3. Choose ONE lever and explain the mechanism, using the equations of circuit-analyst
   checked against the operating point: fix its warnings first (a device in or near
   triode, output at a rail); its notes say what really limits UGBW and PM (2nd pole
   gm6/(2 pi CL) vs UGBW, the Rc zero). Feasible mode: the devices with the largest
   Vds - Vdsat and the highest gm/Id show where current can be removed. Quote at least
   one operating-point number in the decision.
   Prefer levers that fix the worst spec without breaking a spec with a small margin.
   Known couplings: Cc trades PM against UGBW/SR/area; I_2 trades PM/SR against current;
   longer L trades gain against UGBW/PM.
   Robust mode (get_status mode "pvt_robust"): the specs are worst cases; use
   `failing_corners` and `worst_corner` to say WHICH corner limits each spec, and name the
   corner in the decision. Hot corners (100 C) lower mobility, so gm, UGBW and slew rate
   drop there; cold corners (0 C) raise UGBW and squeeze the phase margin. A lever that
   fixes a hot-corner spec must be checked against the cold-corner phase margin (and the
   reverse); the operating point is that of the design's worst corner.
4. Stall check: if the last 3 sizer results in memory did not improve the best reward,
   or the design is feasible with all margins small, decide "hand over to rl".
   Exception: while the current is above 1.5x its target, small margins are not a stall.
   Choose a current-lowering lever (larger S_mn3, or smaller mn5 with the mp3 partner)
   combined with a Cc/Rc retune, and ask the sizer to screen it first.
5. `write_memory(agent="diagnoser", kind="decision", ...)`: best id, binding spec, chosen
   lever, expected trade-off, or the handover decision with the reason.
