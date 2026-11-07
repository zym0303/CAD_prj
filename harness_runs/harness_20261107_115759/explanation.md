# Design Explanation & Review: Two-Stage Miller Opamp Sizing

**Harness Run ID**: `harness_20261107_115759`  
**Execution Mode**: Full (Analytical -> Diagnoser/Sizer -> TD3 RL Refinement -> Polish -> Review)  
**Final Candidate ID**: **729**  
**Final FoM (Reward)**: **0.6849** (Feasible, > 0.3)  
**Feasibility**: **PASS** (All 5 hard constraints satisfied)

---

## 1. Final Sizing & Performance Summary

### Device Parameters (Candidate 729)
| Parameter | Value | Unit | Description |
|---|---|---|---|
| `mn1` / `mn2` | 23 | fingers | NMOS differential input pair |
| `wn1` / `wn2` | 2.25e-6 | m | NMOS input finger width |
| `ln1` / `ln2` | 9.0e-8 | m | NMOS input channel length |
| `mp1` / `mp2` | 6 | fingers | PMOS stage 1 active mirror load |
| `wp1` / `wp2` | 2.25e-6 | m | PMOS stage 1 load finger width |
| `lp1` / `lp2` | 9.0e-8 | m | PMOS stage 1 load channel length |
| `mn3` | 4 | fingers | NMOS bias reference diode (Ibias = 30 µA) |
| `wn3` | 1.0e-6 | m | NMOS bias diode finger width |
| `ln3` | 9.0e-8 | m | NMOS bias diode channel length |
| `mn4` | 8 | fingers | NMOS stage 1 tail current mirror |
| `wn4` | 1.25e-6 | m | NMOS tail current finger width |
| `ln4` | 9.0e-8 | m | NMOS tail current channel length |
| `mp3` | 18 | fingers | PMOS stage 2 common-source driver |
| `wp3` | 2.50e-6 | m | PMOS stage 2 CS finger width |
| `lp3` | 9.0e-8 | m | PMOS stage 2 CS channel length |
| `mn5` | 18 | fingers | NMOS stage 2 current sink mirror |
| `wn5` | 1.25e-6 | m | NMOS stage 2 sink finger width |
| `ln5` | 9.0e-8 | m | NMOS stage 2 sink channel length |
| `cap` ($C_c$) | 7.0e-13 | F | Miller compensation capacitor (0.7 pF) |
| `res` ($R_c$) | 5000.0 | $\Omega$ | Nulling resistor (5.0 k$\Omega$) |

### Performance Metrics vs. Targets (TT, 1.2 V, 27 °C)
| Metric | Value | Constraint / Target | Normalized Margin $z$ | Status |
|---|---|---|---|---|
| **Gain** | **303.0 V/V** | $\ge$ 200.0 V/V | +0.205 (+103.0 V/V) | **PASS** |
| **UGBW** | **100.5 MHz** | $\ge$ 100.0 MHz | +0.0024 (+0.50 MHz) | **PASS** |
| **Phase Margin** | **62.24°** | $\ge$ 60.0° | +0.0183 (+2.24°) | **PASS** |
| **Slew Rate** | **55.07 V/µs** | $\ge$ 30.0 V/µs | +0.295 (+25.07 V/µs) | **PASS** |
| **Noise** | **0.00556 V RMS** | $\le$ 0.030 V RMS | -0.687 (-0.0244 V RMS) | **PASS** |
| **Total Current** | **248.7 µA** | Minimize (Target 200 µA) | +0.109 (+48.7 µA) | Optimized |
| **Total Area** | **6.784e-10 m²** | Minimize (Target 2.0e-9 m²) | -0.493 (-1.32e-9 m²) | Optimized |
| **FoM (Reward)**| **0.6849** | Maximize (> 0.3 feasible) | — | **FEASIBLE BEST** |

---

## 2. Design Story & Lineage

| Step | Candidate ID | Agent | Action & Circuit Change | Engineering Reason | Performance Effect |
|---|---|---|---|---|---|
| 0 | **1** | Analyst | Hand equation first-cut sizing: $I_{\text{tail}}=38\,\mu\text{A}$, $I_2=109\,\mu\text{A}$, balanced ratio 5.5, $C_c=1.2\,\text{pF}$, $R_c=800\,\Omega$. | Establish balanced baseline operating point. | FoM = -0.9148. Gain (654) and noise pass, but UGBW (26.9 MHz) and PM (34.6°) fail due to low $g_{m6}$ (1.15 mS) and 2nd pole at 18.2 MHz. |
| 1 | **2** | Sizer | Implement exact 5.0 balance ratio ($mn_4=6, mn_5=15, mp_1=4, mp_3=20$), $C_c=0.8\,\text{pF}$, $R_c=6\,\text{k}\Omega$. | Cancel 2nd pole $p_2 = 37.9\,\text{MHz}$ using LHP zero $f_z = 35.7\,\text{MHz}$ via $R_c = \frac{1}{g_{m6}}(1 + \frac{C_L}{C_c})$. | **FoM = 0.6451 (FEASIBLE)**. UGBW jumps to 100.3 MHz, PM = 61.63°, Gain = 769, SR = 45.8 V/µs. |
| 2 | — | Diagnoser | Screen global current reduction via $S_{mn3}$ ($w_{n3}=1.25\,\mu\text{m}, mn_3=4$). | Try trading excess margins to lower current to $\le 200\,\mu\text{A}$. | Current drops to 190–199 µA, but $g_m$ reduction drops UGBW to 75–85 MHz. Handed over to RL at Pareto boundary. |
| 3 | **324** | RL (TD3) | Local exploration around candidate 2 ($C_c \to 0.7\,\text{pF}, R_c = 5.9\,\text{k}\Omega, mn_4=8, mn_5=18, mp_1=6, mp_3=18$). | Trade excess gain and stage-2 bias to reduce capacitor area and boost speed. | FoM improves to 0.6499. Area drops to $7.43\times 10^{-10}\,\text{m}^2$, UGBW = 112.2 MHz, PM = 60.42°. |
| 4 | **723** | Sizer | 1-D sweep of $R_c$ ($res$) from 6200 $\Omega$ down to 5600 $\Omega$ on candidate 324. | Reduce resistor area and increase phase margin. | FoM rises to 0.6614 ($res=5600\,\Omega$). Feasible. |
| 5 | **729** | Sizer | Extend 1-D sweep of $R_c$ down to [5000..5500] $\Omega$. | Push area minimization down to the exact UGBW constraint boundary. | **FoM = 0.6849 ($res=5000\,\Omega$)**. Area drops to $6.78\times 10^{-10}\,\text{m}^2$, UGBW hits 100.5 MHz boundary with PM = 62.24°. |

---

## 3. Decision Origins: Equations vs. Reinforcement Learning

### Derived from Analytical Equations
1. **DC Balance Condition**: Maintaining $\frac{S_{mp3}}{S_{mp1}} = 2 \frac{S_{mn5}}{S_{mn4}}$ prevented stage 1 output offset from driving stage 2 into the supply rails.
2. **Pole-Zero Doublet Cancellation**: Recognizing that $UGBW$ was clamped by the 2nd pole $p_2 = \frac{g_{m6}}{2\pi C_L} \approx 36\,\text{MHz}$ with $-40\,\text{dB/dec}$ roll-off led directly to the exact design formula:
   $$R_c = \frac{1}{g_{m6}} \left(1 + \frac{C_L}{C_c}\right)$$
   Setting $f_z \approx p_2$ flattened the roll-off back to $-20\,\text{dB/dec}$, boosting UGBW from 27 MHz to over 100 MHz in a single targeted step (Candidate 2).
3. **Current Mirror Length Matching**: Enforcing identical channel length ($L = 90\,\text{nm}$) across bias mirrors avoided severe threshold voltage mismatch and DIBL distortion.

### Discovered by Reinforcement Learning (TD3)
1. **Multi-Parameter Redistribution**: TD3 discovered that raising stage 1 tail current ($I_{\text{tail}} = 71.6\,\mu\text{A}$ vs. $57.3\,\mu\text{A}$) with $mn_4=8, w_{n4}=1.25\,\mu\text{m}$ permitted a lower compensation capacitance ($C_c = 0.7\,\text{pF}$ instead of $0.8\,\text{pF}$).
2. **Area-Current Rebalancing**: TD3 traded modest excess current ($+8.3\,\mu\text{A}$) for a large reduction in capacitor and device area ($-13.5\%$), which significantly increased the net figure of merit.

### Failed Predictions & Model Lessons
- **Attempting $L_{p3} = 45\,\text{nm}$ (pmos minimum length)**: Hand reasoning predicted doubling $g_{m6}$ would push $p_2 > 50\,\text{MHz}$. However, 45nm PMOS experienced severe DIBL and threshold shift relative to 90nm $mp_1$, overdriving $mn_5$ and pulling $V_{\text{out}}$ to $1.135\,\text{V}$ (VDD rail) and collapsing gain to 24. `quick_analysis` caught this immediately with 0 simulator calls.
- **Attempting $L_{n1} = 45\,\text{nm}$ (input pair minimum length)**: Predicted to increase $g_{m1}$, but extreme short-channel output conductance collapsed $g_{m1}/g_{ds}$ from 59 to 5.8, dropping stage 1 gain to 5.3. Caught via `quick_analysis`.
- **Global Current Scaling below 200 µA**: Predicted to improve FoM by reducing $z_{\text{current}}$, but both $g_{m1}$ and $g_{m6}$ dropped proportionally, causing UGBW to fall to 75–85 MHz and violating the hard constraint.

---

## 4. Operating Point Analysis of the Final Design (Candidate 729)

### Transistor DC Operating Data
| Device | Role | $I_d$ (µA) | $g_m$ (mS) | $g_m/I_d$ (V⁻¹) | $V_{ds} - V_{dsat}$ (V) | Region | Inversion |
|---|---|---|---|---|---|---|---|
| `mn1` | Input pair (mirror side) | 35.80 | 0.765 | 21.35 | 0.399 | Saturation | Weak |
| `mn2` | Input pair (output side) | 35.80 | 0.765 | 21.35 | 0.399 | Saturation | Weak |
| `mp1` | Diode load | 35.80 | 0.573 | 16.02 | 0.371 | Saturation | Moderate |
| `mp2` | Stage 1 output load | 35.80 | 0.573 | 16.02 | 0.371 | Saturation | Moderate |
| `mn3` | Bias diode | 30.00 | 0.547 | 18.24 | 0.375 | Saturation | Weak |
| `mn4` | Tail current source | 71.61 | 1.311 | 18.31 | 0.229 | Saturation | Weak |
| `mp3` | Stage 2 common-source | 147.10 | 2.263 | 15.38 | 0.991 | Saturation | Moderate |
| `mn5` | Stage 2 current sink | 147.10 | 2.679 | 18.21 | 0.046 | Saturation | Weak |

### Small-Signal & Frequency Behavior
- **Stage 1 Gain**: $A_1 = 30.48\,\text{V/V}$
- **Stage 2 Gain**: $A_2 = 10.06\,\text{V/V}$
- **Overall DC Gain Estimate**: $A_1 A_2 = 306.5\,\text{V/V}$ (measured: 303.0 V/V)
- **Input Transconductance Pole**: $\frac{g_{m1}}{2\pi C_c} = 173.8\,\text{MHz}$
- **Second Pole**: $p_2 = \frac{g_{m6}}{2\pi C_L} = 36.01\,\text{MHz}$
- **LHP Zero**: $f_z = \frac{1}{2\pi C_c (R_c - 1/g_{m6})} = 49.88\,\text{MHz}$
- **Pole-Zero Action**: The zero at 49.88 MHz supplies $+62.24^\circ$ of phase lead at $100.5\,\text{MHz}$, canceling the phase lag from the 36 MHz pole and keeping PM above 60°.

### Electrical Evolution: Expert Baseline (Candidate 2) vs. Final Solution (Candidate 729)
Comparison via `compare_operating_points(2, 729)`:
- $I_{\text{tail}}$ increased from $57.29\,\mu\text{A}$ to $71.61\,\mu\text{A}$, boosting $g_{m1}$ from $0.621\,\text{mS}$ to $0.765\,\text{mS}$.
- Compensation capacitance $C_c$ decreased from $0.8\,\text{pF}$ to $0.7\,\text{pF}$, directly reducing active area from $7.84\times 10^{-10}\,\text{m}^2$ to $6.78\times 10^{-10}\,\text{m}^2$ ($-13.5\%$).
- Resistor $R_c$ tuned from $6000\,\Omega$ down to $5000\,\Omega$, tracking the smaller $C_c$ to preserve the optimal pole-canceling LHP zero.
- Total area dropped from $7.839\times 10^{-10}\,\text{m}^2$ to $6.784\times 10^{-10}\,\text{m}^2$, elevating FoM from 0.6451 to 0.6849.

---

## 5. PVT Robustness Verification (12 Corners)

A full 12-corner PVT sweep was executed on candidate 729 (Process: {TT, SS, FF}, Supply: {1.2 V, 1.0 V}, Temp: {0 °C, 100 °C}):

| Specification | Target | Nominal (TT 1.2V 27C) | Worst-Case Value | Worst-Case Corner | Status across PVT |
|---|---|---|---|---|---|
| **Phase Margin** | $\ge 60.0^\circ$ | **62.24°** | **61.55°** | TT 1.2V 0C | **Passes in ALL 12 corners** |
| **Slew Rate** | $\ge 30.0\,\text{V/\mu s}$ | **55.07 V/µs** | **30.12 V/µs** | SS 1.0V 100C | **Passes in ALL 12 corners** |
| **Noise** | $\le 0.030\,\text{V RMS}$ | **0.00556 V** | **0.00897 V** | FF 1.2V 0C | **Passes in ALL 12 corners** |
| **Gain** | $\ge 200.0\,\text{V/V}$ | **303.0 V/V** | 53.71 V/V | SS 1.0V 100C | Fails at 1.0V / 100C corners |
| **UGBW** | $\ge 100.0\,\text{MHz}$ | **100.5 MHz** | 56.67 MHz | SS 1.0V 100C | Fails at 100C corners |
| **Current** | Minimize | **248.7 µA** | 257.2 µA | FF 1.2V 0C | Robust |
| **Area** | Minimize | **6.784e-10 m²** | 6.784e-10 m² | (all corners) | Fixed physical size |

- **Nominal FoM**: 0.6849 (Feasible)
- **Worst-case FoM**: -0.8347
- **Failing Corners**: 8 corners, driven by high temperature (100 °C) where carrier mobility $\mu_n, \mu_p$ drops significantly, reducing $g_m$ and lowering UGBW and gain. Phase margin, slew rate, and noise remain fully compliant across all 12 PVT corners.

---

## 6. Cheap Analyses & Compute Efficiency

The cad MCP cheap analysis toolset was utilized systematically to protect the 1000 simulator call budget:
- `quick_analysis` calls: **17 calls** evaluating **115 circuit variants** in ~0.02s each with **0 simulator calls**.
- `operating_point` calls: **3 transistor-level lookups** extracting internal DC biases, $g_m/I_d$, and pole locations with **0 simulator calls**.
- `corner_check` calls: **1 check** running 12 PVT corners with **0 simulator calls**.
- **Simulator calls saved**: Estimated 120+ simulator calls saved by pre-screening invalid geometries (e.g. triode devices, collapsed gains, broken balances).

---

## 7. Budget & Execution Resource Totals

- **Total Simulator Calls Used**: **908** / 1000 budget (90.8% utilization, satisfying the mandatory stopping threshold $\ge 900$).
- **Total Hand Decisions**: **5** (out of 40 budget: 2 `simulate` calls and 3 `sweep` calls).
- **Replay Buffer Feasible Solutions**: **77 distinct feasible designs** generated across the Pareto front.
- **Total Elapsed Time**: **~1111 seconds** (~18.5 minutes).

---

## 8. Remaining Trade-offs & Future Levers

1. **Area vs. Phase Margin Boundary**:
   The compensation capacitor $C_c$ currently sits at $0.7\,\text{pF}$. Pushing $C_c$ down to $0.5\,\text{pF}$ would further decrease area, but requires $g_{m6} > 3.2\,\text{mS}$ to preserve $p_2 \ge 50\,\text{MHz}$ and PM $\ge 60^\circ$, which would necessitate higher stage 2 current.
2. **Current vs. Temperature Robustness**:
   Operating current is $248.7\,\mu\text{A}$. Reducing current towards $200\,\mu\text{A}$ tightens the nominal UGBW margin, making the amplifier more susceptible to mobility drop at high temperatures (100 °C). Increasing bias currents by 10-15% would achieve full PVT compliance at the expense of nominal FoM.
