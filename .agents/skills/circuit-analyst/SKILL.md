---
name: circuit-analyst
description: Explains the two-stage Miller opamp topology and derives a first-cut sizing from hand equations. Use at the start of an opamp sizing run or when asked how the circuit works.
---

# Circuit analyst

## Circuit (TwoStage.cir, 45 nm, VDD = 1.2 V, Ibias = 30 uA, CL = 10 pF)

| Device | Role | Parameters |
|---|---|---|
| mn1/mn2 | NMOS input differential pair | mn1, wn1, ln1 |
| mp1/mp2 | PMOS current-mirror load of stage 1 | mp1, wp1, lp1 |
| mn3 | diode-connected bias, carries Ibias = 30 uA | mn3, wn3, ln3 |
| mn4 | tail current source (mirror of mn3) | mn4, wn4, ln4 |
| mp3 | PMOS common-source 2nd stage | mp3, wp3, lp3 |
| mn5 | 2nd-stage current sink (mirror of mn3) | mn5, wn5, ln5 |
| Cc + Rc | Miller compensation with nulling resistor | cap, res |

Size of a device: S = m * W / L. Bias currents follow mirror ratios:
I_tail = 30 uA * S4/S3, I_2 = 30 uA * S5/S3 (same L for the mirror devices keeps this accurate).

## First-order design equations

- Total current ~ 30 uA + I_tail + I_2 (target 200 uA, minimized): plan I_tail + I_2 <= 170 uA.
- BALANCE CONDITION (zero systematic offset): S_mp3 / S_mp1 = 2 * S_mn5 / S_mn4. If it does
  not hold, the DC level at stage 1's output shifts, mp3 or mn5 leaves saturation and the
  gain collapses.
  Whenever you change mn4, mn5, mp1 or mp3, change the partner so the ratio stays equal.
- UGBW ~ gm1 / (2 pi Cc), gm1 = sqrt(2 k' S1 I_tail/2): larger S1, I_tail or smaller Cc.
- Slew rate ~ min(I_tail / Cc, I_2 / (Cc + CL)), in V/us with I in uA and C in pF.
- Gain ~ gm1 (ro2 || ro4) * gm6 (ro6 || ro7): longer L on mn1/mp1/mp3/mn5 raises ro and gain.
- Phase margin: p2 ~ gm6 / CL must be well above UGBW (p2 > 2.2 UGBW for 60 deg with the
  zero removed). Rc ~ 1/gm6 cancels the RHP zero; slightly larger moves it to the LHP and helps PM.
  Typical rule: Cc >= 0.22 CL for 60 deg => Cc around 2-3 pF.
- When Cc is small, gm1/Cc approaches the 2nd pole gm6/CL (CL = 10 pF) and UGBW stops
  following gm1/Cc: raising gm1 then helps little. Raise gm6 instead: more I_2 (mn5) with
  a wider mp3, keeping the balance condition.
- Noise (input-referred): larger gm1 and larger gate area of mn1/mp1 reduce it; long-L loads help.
- Area: sum of m*W*L of all devices plus the capacitor; Cc usually dominates, so keep Cc small.
- Mirror matching: use the same length for mn3, mn4, mn5.

## What to do

1. Call `design_space` once.
2. Pick the current split first (e.g. I_tail ~ 40-60 uA, I_2 ~ 80-120 uA) from the SR and
   UGBW targets, then Cc from PM, then S1 from UGBW, then mp3 from p2 > 2.2 UGBW, then L for gain.
3. Simulate at most 2 designs (full 20 parameters) with the equations in the rationale.
4. `write_memory(agent="analyst", kind="plan", ...)`: the design intent (current split, Cc,
   which device controls which spec) and the ids of the simulated designs.
