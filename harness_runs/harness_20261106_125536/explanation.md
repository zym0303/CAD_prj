# Opamp Sizing Explanation Report
**Run ID:** `harness_20261106_125536`  
**Best Feasible Candidate ID:** `741`  
**FoM:** `0.6801` (Feasible: > 0.3)

---

## 1. Final Parameters, Specs, and Constraint Margins

### Final Sizing Parameters (Candidate 741)
| Parameter | Description | Value | Unit |
|---|---|---|---|
| `mp1` | PMOS load multiplier (Stage 1) | 10 | count |
| `wp1` | PMOS load width | 1.0e-6 | m |
| `lp1` | PMOS load length | 9.0e-8 | m |
| `mn1` | NMOS input pair multiplier | 10 | count |
| `wn1` | NMOS input pair width | 2.0e-6 | m |
| `ln1` | NMOS input pair length | 9.0e-8 | m |
| `mp3` | PMOS driver multiplier (Stage 2) | 22 | count |
| `wp3` | PMOS driver width | 2.0e-6 | m |
| `lp3` | PMOS driver length | 9.0e-8 | m |
| `mn3` | NMOS diode bias multiplier | 4 | count |
| `wn3` | NMOS diode bias width | 1.0e-6 | m |
| `ln3` | NMOS diode bias length | 9.0e-8 | m |
| `mn4` | NMOS tail current multiplier | 7 | count |
| `wn4` | NMOS tail current width | 1.0e-6 | m |
| `ln4` | NMOS tail current length | 9.0e-8 | m |
| `mn5` | NMOS 2nd-stage sink multiplier | 14 | count |
| `wn5` | NMOS 2nd-stage sink width | 1.25e-6 | m |
| `ln5` | NMOS 2nd-stage sink length | 9.0e-8 | m |
| `cap` | Miller compensation capacitance ($C_c$) | 6.0e-13 (0.6 pF) | F |
| `res` | Nulling resistor ($R_c$) | 8600.0 (8.6 kΩ) | Ω |

### Specifications and Constraint Margins
| Specification | Target | Achieved Value | Margin | Normalized Score ($z$) | Status |
|---|---|---|---|---|---|
| **Gain ($A_v$)** | $\ge 200.0$ V/V | **700.7** V/V | +500.7 V/V (+250%) | +0.556 | FEASIBLE |
| **Noise** | $\le 0.030$ V RMS | **0.01772** V RMS | -0.01228 V RMS (-41%) | -0.257 | FEASIBLE |
| **Phase Margin (PM)** | $\ge 60.0$ deg | **62.72** deg | +2.72 deg (+4.5%) | +0.0221 | FEASIBLE |
| **Slew Rate (SR)** | $\ge 30.0$ V/μs | **48.89** V/μs | +18.89 V/μs (+63%) | +0.239 | FEASIBLE |
| **Unity Gain BW (UGBW)** | $\ge 100.0$ MHz | **100.10** MHz | +0.10 MHz (+0.1%) | +0.00028 | FEASIBLE (Binding) |
| **Area** | minimize (2.0 n$m^2$) | **0.8694** n$m^2$ | -1.1306 n$m^2$ (-56.5%) | -0.394 | Optimized |
| **Current** | minimize (200 μA) | **205.7** μA | +5.7 μA (+2.8%) | +0.014 | Optimized |

---

## 2. The Design Story (Lineage Chain)

1. **Analyst (`id=1`, reward: -0.8444)**: Hand-calculated sizing based on current splitting ($I_{tail}=50\mu\text{A}, I_2=100\mu\text{A}$, balance condition satisfied) yielded gain=670.6 V/V, noise=20.5 mV, SR=28.18 V/μs, PM=31.89 deg, UGBW=29.8 MHz. Operating point diagnosed that UGBW was severely bottlenecked by the 2nd pole $p_2 = g_{m6}/(2\pi C_L) = 17.9$ MHz and an RHP zero at 1.5 GHz ($R_c < 1/g_{m6}$).
2. **Sizer (`id=3`, reward: -0.6512)**: Doubled $mp3$ width (6->12) and $mp1$ (3->6) to preserve balance, raised $R_c$ to 1200 Ω ($> 1/g_{m6}$); pushed $p_2$ to 25 MHz and moved zero into LHP; PM jumped 31.9 -> 42.4 deg, UGBW rose to 33.0 MHz.
3. **Sizer (`id=4`, reward: -0.6387)**: Reduced $C_c$ from 1.2 pF to 0.8 pF to raise $I_{tail}/C_c$ and $g_{m1}/C_c$; SR became feasible at 37.93 V/μs and UGBW reached 41.15 MHz.
4. **Sizer (`id=10`, sweep, reward: -0.3358)**: Swept $R_c$ from 1500 to 4000 Ω; optimal LHP zero at 60 MHz boosted PM to 60.76 deg (feasible!) with UGBW at 46.42 MHz.
5. **Sizer (`id=11`, reward: -0.2942)**: Widened $mp3$ (12->20), $mp1$ (6->10), and $mn1$ (8->14); raised $g_{m6}$ and $g_{m1}$, driving UGBW from 46.4 to 51.11 MHz while preserving PM at 61.25 deg.
6. **Sizer (`id=12`, reward: -0.3241)**: Dropped $C_c$ from 0.8 pF to 0.5 pF; UGBW rose to 60.19 MHz and SR reached 51.27 V/μs, but PM dipped to 48.3 deg due to zero frequency shift.
7. **Sizer (`id=18`, sweep, reward: -0.1315)**: Swept $R_c$ from 4500 to 7000 Ω; restored LHP zero time constant with smaller $C_c$, driving UGBW to 73.77 MHz and PM to 59.21 deg.
8. **Sizer (`id=23`, sweep, reward: -0.04686)**: Swept $R_c$ 7500..9500 Ω; pushed UGBW to 88.47 MHz and PM to 59.13 deg.
9. **Sizer (`id=25`, reward: -0.01592)**: Increased $mn5$ (10->12, $I_2 \approx 122\mu\text{A}$) and $mp3$ (20->24), satisfying balance ratio $2S_5/S_4 = 4.8 = S_{mp3}/S_{mp1}$; boosted $g_{m6}$ by 20% and pushed $p_2$ to 32 MHz; UGBW surpassed 100 MHz (101.1 MHz!).
10. **Sizer (`id=26-28`, reward: 0.6312)**: Adjusted $C_c$ across 0.6, 0.7, to 0.8 pF for Miller pole splitting; candidate 28 achieved FULL FEASIBILITY (PM=60.73 deg, UGBW=102.7 MHz, FoM=0.6312).
11. **Sizer (`id=29-31`, reward: 0.6379)**: Phase 2 hand optimization reduced $mn1$ from 14 to 8, saving gate area while maintaining UGBW=101.4 MHz and PM=63.97 deg; candidate 31 became the peak expert hand design.
12. **RL Strategist (`id=445`, reward: 0.6528)**: TD3 seeded on expert design 31 explored multi-parameter coupling. Discovered that adjusting bias mirrors ($mn3:4, mn4:7, mn5:14, wn5:1.25\mu\text{m}, mp3:22$) enabled dropping $C_c$ from 0.8 pF to 0.6 pF (saving 25% capacitor area) while keeping $p_2 \approx 31.8$ MHz and UGBW=106 MHz.
13. **Sizer (`id=733`, sweep, reward: 0.6731)**: Polish phase swept $R_c$ on candidate 445 down to 8800 Ω; reduced resistor area while increasing PM to 62.24 deg and maintaining UGBW at 101.6 MHz.
14. **Sizer (`id=741`, sweep, reward: 0.6801)**: Swept $R_c$ to 8600 Ω, reaching the exact Pareto optimum where UGBW=100.10 MHz ($\ge 100$), PM=62.72 deg ($\ge 60$), and area is minimized to 0.8694 n$m^2$.

---

## 3. Decision Origins and Predictions

### Decisions from First-Principles Hand Equations
- **Current Budget Splitting**: Fixed $I_{bias}=30\mu\text{A}$, allotted $I_{tail}\approx 50\mu\text{A}$ and $I_2\approx 120\mu\text{A}$ to satisfy $I_{total} \le 200\mu\text{A}$ and slew rate constraints.
- **Stage Balance Condition**: Enforced $S_{mp3}/S_{mp1} = 2 \cdot S_{mn5}/S_{mn4}$ across all mirror size adjustments to prevent systematic DC offset and gain collapse at the stage 1 output.
- **Lead Compensation ($R_c$)**: Located the nulling resistor value such that $R_c > 1/g_{m6}$, converting the RHP zero into an LHP zero that provides positive phase boost around UGBW.

### Decisions from Reinforcement Learning (TD3)
- **Simultaneous Mirror & Cap Optimization**: While single-parameter hand adjustments stalled at $C_c=0.8$ pF, TD3 successfully discovered a coupled multi-transistor shift ($mn3, mn4, mn5, wn5, mp3$) that re-distributed currents to permit reducing $C_c$ to 0.6 pF without violating $p_2$ or UGBW constraints.
- **Pareto Front Exploration**: RL populated the replay buffer with 93 distinct feasible candidate designs spanning various trade-offs (e.g. candidate 767 with DC gain of 945 V/V).

### Failed Predictions & Physical Root Causes
- **Candidate 2 ($l_{n1}$ reduced from 90 nm to 45 nm)**: Predicted higher $g_{m1}$ would raise UGBW; failed because short-channel effect lowered output resistance $r_{o1}$, collapsing overall DC gain from 670 V/V down to 114 V/V (violating the 200 V/V gain constraint).
- **Candidate 24 ($C_c$ reduced to 0.4 pF on design 20)**: Predicted $g_{m1}/C_c$ would directly lift UGBW past 100 MHz; failed because the 2nd pole $p_2 = g_{m6}/(2\pi C_L)$ was lower than UGBW, capping the bandwidth and dropping PM to 54.9 deg.
- **Candidate 32 ($R_c$ reduced to 9000 Ω on design 31)**: Predicted saving resistor area with excess PM margin; failed because lowering $R_c$ pushed the LHP zero higher in frequency, eroding the high-frequency phase and magnitude boost and dropping UGBW to 97.7 MHz.

---

## 4. Operating Point Analysis of the Final Design (Candidate 741)

### Transistor Operating Point Summary
| Device | Role | $I_d$ (μA) | $g_m$ (mS) | $g_{ds}$ (μS) | $g_m/I_d$ ($V^{-1}$) | $V_{ov}$ (V) | $V_{ds} - V_{dsat}$ (V) | Region | Inversion |
|---|---|---|---|---|---|---|---|---|---|
| **mn1** | Diff pair (mirror side) | 24.78 | 0.515 | 8.64 | 20.78 | -0.126 | +0.428 | Saturation | Weak |
| **mn2** | Diff pair (output side) | 24.78 | 0.515 | 8.64 | 20.78 | -0.126 | +0.428 | Saturation | Weak |
| **mp1** | Diode active load | 24.78 | 0.402 | 8.56 | 16.24 | +0.051 | +0.369 | Saturation | Moderate |
| **mp2** | Stage-1 mirror load | 24.78 | 0.402 | 8.56 | 16.24 | +0.051 | +0.369 | Saturation | Moderate |
| **mn3** | Bias diode ($I_{in}=30\mu\text{A}$) | 30.00 | 0.547 | 9.48 | 18.24 | -0.034 | +0.375 | Saturation | Weak |
| **mn4** | Tail current source | 49.56 | 0.908 | 17.67 | 18.32 | -0.036 | +0.202 | Saturation | Weak |
| **mp3** | Stage-2 CS driver | 126.10 | 1.997 | 41.67 | 15.84 | +0.057 | +0.793 | Saturation | Moderate |
| **mn5** | Stage-2 current sink | 126.10 | 2.308 | 42.69 | 18.30 | -0.035 | +0.247 | Saturation | Weak |

### Circuit Transfer & Frequency Metrics
- **Stage 1 Gain ($A_1$)**: 29.94 V/V
- **Stage 2 Gain ($A_2$)**: 23.67 V/V
- **Total Estimated Gain ($A_1 \cdot A_2$)**: 708.8 V/V (matches simulated $A_v = 700.7$ V/V).
- **First Pole ($g_{m1} / 2\pi C_c$)**: 136.6 MHz
- **Second Pole ($p_2 = g_{m6} / 2\pi C_L$)**: 31.79 MHz ($C_L = 10$ pF).
- **Nulling Resistor Zero ($z_{LHP}$)**: 32.75 MHz (LHP, since $R_c = 8600\,\Omega > 1/g_{m6} = 500.7\,\Omega$).
- **Pole-Zero Interaction**: The LHP zero at 32.75 MHz cancels the phase lag of the second pole at 31.79 MHz almost exactly ($\approx 1$ MHz difference), extending the phase margin to 62.72 deg at the 100.1 MHz unity-gain frequency.

### Electrical Shift Induced by RL (`compare_operating_points(31, 445)`)
- RL shifted $mn3, mn4, mn5$ to a 4:7:14 ratio with $w_{n5}=1.25\mu\text{m}$.
- Tail current $I_{tail}$ increased slightly from 46.90 to 49.56 μA; stage 2 current $I_2$ increased from 122.6 to 126.1 μA.
- $g_{m1}$ increased from 0.483 to 0.515 mS; $g_{m6}$ held steady at 2.00 mS.
- This allowed $C_c$ to drop from 0.8 pF to 0.6 pF, increasing $g_{m1}/(2\pi C_c)$ from 96.1 to 136.6 MHz while keeping $p_2 \approx 31.8$ MHz.
- Resistor area and capacitor area both decreased, driving FoM up by +0.0422.

---

## 5. Execution Summary and Resource Usage

- **Total Simulator Calls Used**: 931 / 1000
  - LLM Hand / Polish Calls: 41
  - RL Warmup Steps: 150
  - RL Training Steps: 740 (740 actor-critic updates)
- **Feasible Designs Discovered**: 93
- **DC Operating Point Lookups**: 7 / 20
- **Total Elapsed Runtime**: 1148 seconds (~19.1 minutes)

---

## 6. Remaining Trade-offs and Sensitivity

- **Area vs. UGBW**: Resistor $R_c = 8600\,\Omega$ is at the exact edge of feasibility for UGBW (100.1 MHz). Dropping $R_c$ below 8600 Ω reduces area further but moves the LHP zero higher, degrading magnitude boost at 100 MHz and violating the UGBW constraint.
- **Current vs. Phase Margin**: Total current is 205.7 μA (slightly above the 200 μA nominal target). To drop current below 200 μA, $I_2$ would need to be reduced; however, lowering $I_2$ drops $g_{m6}$, lowering $p_2 = g_{m6}/(2\pi C_L)$ and reducing phase margin below 60 deg.
