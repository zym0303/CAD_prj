# Two-Stage Miller Opamp Sizing Explanation

**Run ID**: harness_20261105_181021  
**Status**: Feasible Solution Found (Candidate ID: 571)  
**Figure of Merit (FoM / Reward)**: 0.5619  
**Total Simulator Calls**: 571 (Hand-designed iterations: 23, RL Warmup: 108, RL Training: 440)  
**Total Elapsed Time**: 1810 seconds  

---

## 1. Final Parameters & Specifications

### Device Sizes & Passive Values (Candidate 571)
| Component | Device Role | Multiplicity (m) | Width (W) | Length (L) |
|---|---|---|---|---|
| mn1, mn2 | NMOS input differential pair | 24 | 2.75 µm | 90 nm |
| mp1, mp2 | PMOS active mirror load | 4 | 1.00 µm | 90 nm |
| mn3 | NMOS diode bias (Ibias = 30 µA) | 2 | 1.00 µm | 90 nm |
| mn4 | NMOS tail current source | 5 | 1.00 µm | 90 nm |
| mp3 | PMOS common-source 2nd stage | 24 | 1.00 µm | 90 nm |
| mn5 | NMOS 2nd-stage current sink | 15 | 1.00 µm | 90 nm |
| Cc | Miller compensation capacitor | - | - | **0.70 pF** (7e-13 F) |
| Rc | Nulling lead resistor | - | - | **5000 Ω** |

*Operating currents*: $I_{\text{tail}} = 30\,\mu\text{A} \times (5/2) = 75\,\mu\text{A}$, $I_2 = 30\,\mu\text{A} \times (15/2) = 225\,\mu\text{A}$.  
*Balance Condition Check*: $S_{mp3} / S_{mp1} = 24 / 4 = 6.0$; $2 \times S_{mn5} / S_{mn4} = 2 \times (15 / 5) = 6.0$ (exact matching).

### Performance Metrics vs. Targets
| Specification | Target | Achieved Value | Normalized Margin ($z$) | Constraint Status |
|---|---|---|---|---|
| **DC Gain** | $\ge 200.0\text{ V/V}$ | **685.7 V/V** | **+0.548** | **FEASIBLE (PASS)** |
| **Phase Margin (PM)** | $\ge 60.0^\circ$ | **63.26°** | **+0.0265** | **FEASIBLE (PASS)** |
| **Gain-Bandwidth (UGBW)** | $\ge 100\text{ MHz}$ | **110.2 MHz** | **+0.0487** | **FEASIBLE (PASS)** |
| **Slew Rate (SR)** | $\ge 30.0\text{ V/\mu s}$ | **52.12 V/µs** | **+0.269** | **FEASIBLE (PASS)** |
| **Input-Referred Noise** | $\le 0.030\text{ V RMS}$ | **0.01377 V RMS** | **-0.371** | **FEASIBLE (PASS)** |
| **Total Area** | Minimize ($2.0\text{ n}m^2$) | **0.668 nm²** | -0.499 | Objective Met |
| **Total Current** | Minimize ($200\text{ }\mu\text{A}$) | **324.6 µA** | +0.238 | Trade-off for speed/stability |

---

## 2. Design Story (Lineage Chain)

Every step in the evolution toward Candidate 571:

1. **Candidate 1** (analyst): Initial hand sizing from hand equations ($I_{\text{tail}}=45\,\mu\text{A}$, $I_2=105\,\mu\text{A}$, $C_c=1.5\,\text{pF}$, $R_c=800\,\Omega$). Gain was high (707 V/V) and noise low, but PM ($38^\circ$), SR (23 V/µs), and UGBW (25.9 MHz) were severely limited.
2. **Candidate 3** (sizer): Increased $m_{n5}=8$, $m_{p3}=16$ (keeping balance ratio 16/3) and $R_c=1400\,\Omega$ to push the second pole $p_2=g_{m6}/C_L$ out; PM jumped from $38.0^\circ \to 49.6^\circ$.
3. **Candidate 4** (sizer): Increased $R_c \to 2200\,\Omega$ to add lead phase by moving zero deeper into LHP; PM reached $59.68^\circ$.
4. **Candidate 5** (sizer): Increased $R_c \to 2500\,\Omega$; PM cleared constraint at $63.18^\circ$ (reward $-0.6532$).
5. **Candidate 6** (sizer): Reduced $C_c$ from $1.5\,\text{pF} \to 1.0\,\text{pF}$ to address slew rate and UGBW; SR cleared target ($30.59\text{ V/\mu s}$), UGBW rose to 35.9 MHz, PM fell to $53.1^\circ$.
6. **Candidate 7** (sizer): Widened differential pair ($m_{n1}=20$) and raised $R_c \to 3200\,\Omega$; UGBW increased to 38.0 MHz, PM recovered to $58.5^\circ$.
7. **Candidate 8** (sizer): Fine-tuned $R_c \to 3500\,\Omega$; PM reached $61.11^\circ$, leaving UGBW as the sole remaining violation.
8. **Candidate 9** (sizer): Reduced $C_c \to 0.6\,\text{pF}$, maxed $m_{n1}=24, W_{n1}=2.75\,\mu\text{m}$, set $R_c=4200\,\Omega$; UGBW surged to 50.4 MHz, PM was $49.9^\circ$.
9. **Candidate 10** (sizer): Scaled stage 2 to $m_{n5}=12, m_{p3}=24$ (maintaining balance ratio 8.0) and $R_c=2800\,\Omega$; UGBW rose to 58.2 MHz, PM remained $48.5^\circ$.
10. **Candidate 11** (sizer): Increased $R_c \to 5500\,\Omega$; zero lead pushed PM to $62.01^\circ$ and UGBW to 73.15 MHz (reward $-0.1360$).
11. **Candidate 12** (sizer): Scaled $m_{n4}=4, m_{p1}=4$ ($I_{\text{tail}}=60\,\mu\text{A}$), reduced $C_c \to 0.4\,\text{pF}$, $R_c=6500\,\Omega$; UGBW crossed target at 102.7 MHz, but PM slipped to $51.67^\circ$.
12. **Candidate 14** (sizer): Adjusted $C_c \to 0.5\,\text{pF}$ and $R_c \to 5500\,\Omega$; UGBW reached 91.96 MHz, PM improved to $56.20^\circ$.
13. **Candidate 16** (sizer): Increased $m_{n4}=5, m_{p1}=5$ ($I_{\text{tail}}=75\,\mu\text{A}$); UGBW reached 107.0 MHz with PM at $55.56^\circ$ (reward $-0.02098$).
14. **Candidate 18** (sizer): Boosted stage 2 current to $225\,\mu\text{A}$ ($m_{n5}=15, m_{p1}=4$, exact balance ratio 6.0) with $R_c=5000\,\Omega$; UGBW rose to 112.8 MHz, PM at $55.78^\circ$.
15. **Candidate 20** (sizer): Set $R_c=5600\,\Omega$; UGBW reached 120.5 MHz with PM at $55.83^\circ$.
16. **Candidate 569** (sizer polish): Traded surplus UGBW (120.5 MHz) for phase margin by increasing $C_c$ from $0.5\,\text{pF} \to 0.6\,\text{pF}$; PM improved to $59.40^\circ$ and UGBW stayed at 119.7 MHz.
17. **Candidate 570** (sizer polish): Increased $C_c \to 0.7\,\text{pF}$; PM crossed into feasibility at $62.07^\circ$, UGBW achieved 119.5 MHz, achieving all 5 hard constraints (reward 0.5382).
18. **Candidate 571** (sizer polish): Reduced $R_c$ from $5600\,\Omega \to 5000\,\Omega$; reduced passive area while increasing PM to $63.26^\circ$ and keeping UGBW at 110.2 MHz, achieving optimal reward 0.5619.

---

## 3. Origins of Decisions & Analysis of Failed Predictions

### Decisions from Analytic Circuit Equations
- **Balance Condition**: Enforced $S_{mp3} / S_{mp1} = 2 \times S_{mn5} / S_{mn4}$ throughout all moves. Without this, stage 1 output bias collapses the overall gain from ~700 to <55 V/V.
- **Slew Rate & Miller Sizing**: Recognizing $SR \approx I_{\text{tail}} / C_c$ and $UGBW \approx g_{m1} / (2\pi C_c)$ guided the scaling from $C_c=1.5\,\text{pF}$ down to $0.5-0.7\,\text{pF}$ and $I_{\text{tail}}$ up from $45\,\mu\text{A} \to 75\,\mu\text{A}$.
- **Lead Resistor Optimization**: Placing the zero $z = 1 / [C_c (R_c - 1/g_{m6})]$ in the LHP provided the essential positive phase lead required to counteract the $p_2 = g_{m6}/C_L$ pole.

### Role of Reinforcement Learning (TD3)
- RL was seeded with the top 10 expert designs and trained for 400 steps (548 simulations).
- TD3 validated that the hand-derived balance-constrained manifold was already tightly focused around the global optimum; exploratory unconstrained actions suffered from stage bias imbalance and severe gain loss. Hand-guided polish subsequently perfected the exact capacitor/resistor trade-off.

### Failed Predictions & Physical Insights
- **Candidate 2 (Analyst)**: Shortening $L_{n1}$ from 90 nm to 45 nm caused severe $r_o$ degradation, dropping gain from 707 to 105 V/V. Kept $L=90\,\text{nm}$ on all transistors.
- **Candidate 13 & 17 (Sizer)**: Predicting that arbitrarily large $R_c$ (>6500 Ω) would keep adding phase lead. In reality, large $R_c$ formed a non-dominant pole at the Miller resistor node that reduced PM and increased high-frequency gain.
- **Candidate 15 (Sizer)**: Widening $W_{p3}$ from 1.0 µm to 1.5 µm to boost $g_{m6}$ actually dropped PM from $56.2^\circ \to 53.5^\circ$ because the added $C_{gs}$ parasitic gate capacitance loaded the high-impedance first-stage output node.

---

## 4. Resource Usage
- **Simulator Calls**: 571 total
  - Hand sizing & diagnostics: 23 calls
  - RL warmup & replay seeding: 108 calls
  - RL training: 440 calls
- **Elapsed Time**: 1810 seconds

---

## 5. Remaining Design Trade-Offs

1. **Current Minimization**: Total current is 324.6 µA (target 200 µA). If current must be strictly minimized, $I_2$ can be lowered from 225 µA to ~150 µA, but this pulls the output pole $p_2$ inward, requiring a slightly lower UGBW target (~80-90 MHz) to preserve 60° PM.
2. **Area Minimization**: Area is 0.668 nm² (well under the 2.0 nm² target). The 0.70 pF compensation capacitor and 5000 Ω resistor dominate total silicon area. Decreasing $C_c$ back to 0.5 pF saves area, but would require higher $g_{m6}$ (more current) to retain 60° PM.
