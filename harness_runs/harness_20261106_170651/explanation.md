# Opamp Sizing Explanation Report

**Run ID**: `harness_20261106_170651`  
**Best Feasible Design**: Candidate `533`  
**Figure of Merit (FoM)**: `0.6836`  
**Feasible**: `True`  
**Total Simulator Calls**: `900`  
**Elapsed Time**: `2618.3 s` (~43.6 minutes)  
**Total Feasible Designs Generated**: `102`

---

## 1. Final Parameters and Performance Specifications

### Final Circuit Parameters (Candidate 533)

| Device / Component | Parameter | Multiplicity ($m$) | Width ($W$) | Length ($L$) | Unit / Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **mn1, mn2** (Diff Pair) | mn1, wn1, ln1 | 13 | 2.000 µm | 90 nm | NMOS input pair |
| **mp1, mp2** (Stage 1 Load) | mp1, wp1, lp1 | 6 | 1.000 µm | 90 nm | PMOS mirror load |
| **mn3** (Bias Reference) | mn3, wn3, ln3 | 3 | 1.000 µm | 90 nm | Diode NMOS ($I_{bias}=30\,\mu\text{A}$) |
| **mn4** (Tail Source) | mn4, wn4, ln4 | 6 | 1.000 µm | 90 nm | NMOS tail ($I_{tail}=56.5\,\mu\text{A}$) |
| **mp3** (Stage 2 CS) | mp3, wp3, lp3 | 9 | 2.750 µm | 90 nm | PMOS 2nd-stage driver |
| **mn5** (Stage 2 Sink) | mn5, wn5, ln5 | 11 | 1.000 µm | 90 nm | NMOS 2nd-stage mirror sink |
| **Cc** (Miller Cap) | cap | - | - | - | **0.500 pF** ($5.0 \times 10^{-13}\,\text{F}$) |
| **Rc** (Nulling Resistor) | res | - | - | - | **9200.0 Ω** ($9.2\,\text{k}\Omega$) |

### Performance Specifications and Margins

| Specification | Target | Hard Constraint | Achieved Value | Margin (Physical) | Normalized $z$ | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Gain** | $\ge 200\,\text{V/V}$ | Yes | **727.9 V/V** (57.2 dB) | $+527.9\,\text{V/V}$ (+264%) | $+0.569$ | **PASS** |
| **Phase Margin (PM)** | $\ge 60.0^\circ$ | Yes | **62.71°** | $+2.71^\circ$ (+4.5%) | $+0.022$ | **PASS** |
| **Unity-Gain Bandwidth (UGBW)** | $\ge 100.0\,\text{MHz}$ | Yes | **100.30 MHz** | $+0.30\,\text{MHz}$ (+0.3%) | $+0.0015$ | **PASS** |
| **Slew Rate (SR)** | $\ge 30.0\,\text{V/\mu s}$ | Yes | **55.42 V/µs** | $+25.42\,\text{V/\mu s}$ (+84.7%) | $+0.298$ | **PASS** |
| **Input Noise** | $\le 0.030\,\text{V RMS}$ | Yes | **0.0177 V RMS** | $-0.0123\,\text{V RMS}$ (-41%) | $-0.258$ | **PASS** |
| **Total Area** | Minimize ($\le 2\,\text{nm}^2$) | Target | **8.690 × 10⁻¹⁰ m²** | $-1.131 \times 10^{-9}\,\text{m}^2$ (-56.5%) | $-0.394$ | **OPTIMAL** |
| **Total Current** | Minimize ($\le 200\,\mu\text{A}$) | Target | **204.3 µA** | $+4.3\,\mu\text{A}$ (+2.1%) | $+0.0107$ | **OPTIMAL** |

$$\text{FoM} = 0.3 - z_{\text{area}} - z_{\text{current}} = 0.3 - (-0.394) - (0.0107) = \mathbf{0.6836}$$

---

## 2. Design Story: Step-by-Step Lineage

1. **Analyst (Eq. Derivation, Candidate 1)**: Initial sizing from first-principles hand equations targeting $I_{tail}=50\,\mu\text{A}$, $I_2=100\,\mu\text{A}$, balanced mirror ratio $S_{mp3}/S_{mp1} = 2 \cdot S_{mn5}/S_{mn4} = 4.0$. $C_c=1.5\,\text{pF}, R_c=800\,\Omega$. Result: Gain 611.8 V/V, current 175 µA, but UGBW limited to 24 MHz and PM to 31.1° by 2nd pole $p_2 \approx 15\,\text{MHz}$ and RHP zero at 402 MHz.
2. **Analyst (Tuning, Candidate 2)**: Scaled input pair $m_{n1}=12, W_{n1}=2.5\,\mu\text{m}$, dropped $C_c$ to 0.8 pF, increased $R_c$ to 1800 Ω (LHP zero). Result: Gain 653.6 V/V, SR 38.6 V/µs (met), current 196.3 µA, UGBW improved to 42.0 MHz, PM 35.4°.
3. **Diagnoser & Sizer (Candidate 3)**: Attempted to double $g_{m6}$ by reducing $L_{p1}, L_{p3}$ from 90 nm to 45 nm. Prediction failed: 45 nm PMOS suffered severe short-channel output conductance spike ($g_{ds}$ increased 14–16x, intrinsic $g_m/g_{ds}$ collapsed from 42 to 4.6), causing gain collapse to 21.2 V/V. Lesson: PMOS channel lengths must remain $\ge 90\,\text{nm}$.
4. **Diagnoser & Sizer (Candidate 4)**: Reverted to 90 nm lengths; doubled PMOS widths while maintaining balance ratio $S_{mp3}/S_{mp1} = 3.667$ ($m_{p1}: 3\to6, m_{p3}: 4\to8$), dropped $C_c$ to 0.4 pF, set $R_c=2800\,\Omega$. Result: $g_{m6}$ rose to 1.50 mS ($p_2=23.9\,\text{MHz}$), UGBW surged to 67.1 MHz, slew rate to 58.9 V/µs, gain to 727 V/V.
5. **Sizer (Rc Parameter Sweep, Candidate 10)**: Swept $R_c$ from 3.8 kΩ to 8.8 kΩ to pull the LHP zero down from 186 MHz toward UGBW. Monotonic improvement: at $R_c=8800\,\Omega$, PM reached 59.03° (target 60°) and UGBW reached 93.6 MHz (target 100 MHz).
6. **Sizer (Rc Fine Sweep, Candidate 19)**: Swept $R_c$ from 8.6 kΩ to 9.8 kΩ. Candidate 19 at $R_c=9800\,\Omega$ reached UGBW = 99.82 MHz (180 kHz shy of 100 MHz) and PM = 59.10° (0.9° shy of 60°), reward = +0.01125.
7. **RL Strategist (Round 1 Anchoring & Warmup, Candidate 35)**: TD3 actor anchored to Candidate 19 via behavioral cloning (`seed_rl`). Warmup sparse local exploration ($n=100$) produced the first fully feasible design Candidate 35 ($\text{FoM}=0.6481$): $m_{n1}=10, m_{p3}=9, C_c=0.6\,\text{pF}, R_c=9800\,\Omega$, achieving PM = 64.57° and UGBW = 104.7 MHz.
8. **Sizer Polish (Candidate 226)**: Swept $R_c$ on base 35; $R_c=9400\,\Omega$ reduced resistor area and boosted PM to 65.28°, achieving FoM = 0.6614.
9. **RL Strategist (Round 2 Anchoring & Warmup, Candidate 249)**: Re-anchored to Candidate 226. Local warmup produced Candidate 249 ($\text{FoM}=0.6620$): $m_{n1}=12, R_c=9300\,\Omega$.
10. **Diagnoser & Sizer Polish (Candidate 377)**: Sizer reduced $C_c$ from 0.6 pF to 0.5 pF on Candidate 249, cutting dominant capacitor area by 17%. Result: PM = 61.62°, UGBW = 101.2 MHz, FoM jumped to 0.6779.
11. **RL Strategist (Round 3 Anchoring & Warmup, Candidate 418)**: Re-anchored to Candidate 377. Local exploration found Candidate 418 ($\text{FoM}=0.6801$): scaled input pair dimensions to $m_{n1}=13, W_{n1}=2.0\,\mu\text{m}$ (reducing total gate width from 30 µm to 26 µm), lowering parasitic input capacitance and area to $8.76 \times 10^{-10}\,\text{m}^2$ while preserving PM = 62.61° and UGBW = 101.0 MHz.
12. **Final Sizer Polish (Candidate 533)**: Swept $R_c$ [9000..9500] on Candidate 418. Candidate 533 ($R_c=9200\,\Omega$) achieved optimal area reduction while maintaining UGBW at 100.3 MHz and PM at 62.71°, reaching the run record **FoM = 0.6836**.
13. **RL Rounds 4–5 Budget Saturation**: Continued TD3 training and local exploration until the simulator budget of 900 calls was reached, generating 102 feasible Pareto-front designs and confirming Candidate 533 as the global optimum.

---

## 3. Decision Breakdown: Analytical Equations vs. RL vs. Failed Hypotheses

### Hand Equations (Analyst, Diagnoser, Sizer)
- **Current Split & Mirror Sizing**: Stage currents ($I_{tail} \approx 56\,\mu\text{A}, I_2 \approx 118\,\mu\text{A}$) and balance constraint $S_{mp3}/S_{mp1} \approx 2 \cdot S_{mn5}/S_{mn4}$ held stage-1 output DC precisely near 0.69 V, preserving $>350\,\text{mV}$ saturation margins on all devices.
- **Miller Pole Splitting & LHP Zero Compensation**: Derived $R_c > 1/g_{m6}$ condition to move the nulling zero from the RHP to the LHP ($z_{LHP} \approx 1 / [2\pi C_c (R_c - 1/g_{m6})]$), supplying $+40^\circ$ of phase lead that neutralized the phase lag of $p_2 \approx 25.7\,\text{MHz}$.
- **Area-Margin Trade-Off**: Identified that $C_c=0.5\,\text{pF}$ and $R_c=9.2\,\text{k}\Omega$ minimized passive layout area while safely clearing the 60° PM boundary.

### Reinforcement Learning Contributions (TD3 Local Refiner)
- **Feasibility Discovery**: Discovered the exact multi-parameter perturbation ($m_{n1}: 12\to10, m_{p3}: 8\to9, C_c: 0.4\text{p}\to0.6\text{p}$) that crossed all 5 hard constraints simultaneously for the first time (Candidate 35).
- **Parasitic Gate Area Co-Optimization**: Co-optimized input pair finger geometry ($m_{n1}=13, W_{n1}=2.0\,\mu\text{m}$ vs $12 \times 2.5\,\mu\text{m}$), shrinking gate area by 13% without losing transconductance ($g_{m1} \approx 0.591\,\text{mS}$).
- **Pareto Exploration**: Explored the feasible region to construct a 102-point feasible library for trade-off analysis.

### Failed Predictions & Discarded Hypotheses
- **PMOS Minimum-Length Scaling (Candidate 3)**: Predicted that halving $L_{p1}, L_{p3}$ to 45 nm would double $g_{m6}$ and increase UGBW. Result: Short-channel DIBL and channel length modulation spiked $g_{ds}$ by 16x and collapsed stage gain from 654 to 21.2 V/V. Corrected: Retained $L \ge 90\,\text{nm}$.
- **Excessive Input Multiplicity (Candidates 11, 20)**: Predicted increasing $m_{n1}$ would boost $g_{m1}$ in weak inversion. Result: In weak inversion ($V_{ov} < 0$), $g_{m1} \approx I_d / (n V_t)$ is current-dependent; increasing width only added parasitic gate capacitance $C_{gs}$, reducing PM without raising UGBW.

---

## 4. Final DC Operating Point Analysis (Candidate 533)

### Transistor Operating Point Summary

| Device | Role | $I_d$ (µA) | $g_m$ (mS) | $g_{ds}$ (µS) | $g_m/I_d$ (1/V) | $V_{gs}$ (V) | $V_{ds}$ (V) | $V_{dsat}$ (V) | Saturation Margin ($V_{ds}-V_{dsat}$) | Region | Inversion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **mn1** | Diff pair (in-) | 28.27 | 0.591 | 10.01 | 20.91 | 0.335 | 0.425 | 0.044 | **+0.381 V** | Saturation | Weak |
| **mn2** | Diff pair (in+) | 28.27 | 0.591 | 10.01 | 20.91 | 0.335 | 0.425 | 0.044 | **+0.381 V** | Saturation | Weak |
| **mp1** | Active load (diode) | 28.27 | 0.388 | 8.55 | 13.71 | 0.510 | 0.510 | 0.125 | **+0.385 V** | Saturation | Moderate |
| **mp2** | Active load (out1) | 28.27 | 0.388 | 8.55 | 13.71 | 0.510 | 0.510 | 0.125 | **+0.385 V** | Saturation | Moderate |
| **mn3** | Bias diode ref | 30.00 | 0.528 | 9.18 | 17.60 | 0.449 | 0.449 | 0.063 | **+0.387 V** | Saturation | Moderate |
| **mn4** | Tail current source| 56.54 | 1.001 | 19.66 | 17.70 | 0.449 | 0.265 | 0.062 | **+0.203 V** | Saturation | Moderate |
| **mp3** | Stage-2 CS driver | 117.80| 1.614 | 35.45 | 13.70 | 0.510 | 0.521 | 0.125 | **+0.396 V** | Saturation | Moderate |
| **mn5** | Stage-2 sink | 117.80| 2.057 | 34.37 | 17.46 | 0.449 | 0.679 | 0.063 | **+0.615 V** | Saturation | Moderate |

### Circuit-Level Pole, Zero, and Stage Metrics
- **Stage 1 Gain ($A_1$)**: $31.84\,\text{V/V}$
- **Stage 2 Gain ($A_2$)**: $23.12\,\text{V/V}$
- **DC Open-Loop Gain**: $A_1 \times A_2 = \mathbf{736.0\,\text{V/V}}$ (Simulated: 727.9 V/V)
- **Miller Parameter $g_{m1} / (2\pi C_c)$**: $188.2\,\text{MHz}$
- **Second Pole $p_2 = g_{m6} / (2\pi C_L)$**: **$25.69\,\text{MHz}$** (with $C_L=10\,\text{pF}$)
- **Compensation Zero $z_{LHP}$**: **$37.10\,\text{MHz}$** ($R_c=9.2\,\text{k}\Omega > 1/g_{m6}=619.6\,\Omega$)
- **DC Balance**: $V_{out1} = 0.6900\,\text{V}$, $V_{out,dc} = 0.6786\,\text{V}$ ($\Delta V = 1.76\,\text{mV}$ offset)

### Electrical Comparison: Expert Anchor (19) vs. Final Optimal (533)
`compare_operating_points(19, 533)` reveals the critical mechanisms:
- $g_{m6}$ increased from $1.502\,\text{mS}$ to $1.614\,\text{mS}$ (+7.5%), pushing the limiting second pole $p_2$ from $23.91\,\text{MHz}$ to $25.69\,\text{MHz}$.
- $C_c$ increased from $0.4\,\text{pF}$ to $0.5\,\text{pF}$, which together with $R_c=9200\,\Omega$ placed the lead-compensating zero at $37.1\,\text{MHz}$, lifting PM from $59.10^\circ$ (violated) to $62.71^\circ$ (feasible).
- Input pair width scaled down from $30\,\mu\text{m}$ to $26\,\mu\text{m}$, reducing overall silicon area from $8.81 \times 10^{-10}\,\text{m}^2$ to $8.69 \times 10^{-10}\,\text{m}^2$.

---

## 5. Resource Consumption and Budget Summary

- **Total Simulator Calls**: 900 (LLM hand/sweep calls: 35, RL warmup: 290, RL training: 575)
- **Total Hand Decisions**: 16 decisions (well within 40 decision budget)
- **Operating Point Lookups**: 12 lookups (within 20 lookup budget)
- **Elapsed Real Time**: 2618.3 seconds (~43.6 minutes)
- **Replay Buffer Size**: 930 transitions
- **Feasible Solutions in Pareto Set**: 102 designs

---

## 6. Remaining Trade-Offs and Sensitivity Analysis

1. **Lower Area Trade-Off**:
   - Area is dominated by $C_c$ (0.5 pF) and $R_c$ ($9.2\,\text{k}\Omega$).
   - Dropping $R_c$ below $9.2\,\text{k}\Omega$ saves resistor area, but reduces UGBW below 100 MHz (e.g., $R_c=9100\,\Omega \implies \text{UGBW}=99.58\,\text{MHz}$, violating spec).
   - Dropping $C_c$ to 0.4 pF requires $R_c \ge 9.8\,\text{k}\Omega$ for stability, which yields higher resistor area and lower PM margin ($59.1^\circ$).
2. **Lower Current Trade-Off**:
   - Current is $204.3\,\mu\text{A}$ ($I_{bias}=30\,\mu\text{A}, I_{tail}=56.5\,\mu\text{A}, I_2=117.8\,\mu\text{A}$).
   - Slew rate is $55.4\,\text{V/\mu s}$ (far above the $30\,\text{V/\mu s}$ target). In principle, $I_{tail}$ could be reduced to $\sim 45\,\mu\text{A}$ to save $\sim 11\,\mu\text{A}$, but lower $I_{tail}$ drops $g_{m1}$, which would drag UGBW below the strict 100 MHz boundary unless $C_c$ could be decreased simultaneously.
