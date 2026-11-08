# Opamp Sizing Explanation Report

## 1. Final Design Parameters and Measured Specifications

**Candidate ID**: 777 (Source: `rl_train`, TD3 local refinement)
**Figure of Merit (FoM)**: 0.6357 (Feasible: Yes)

### Parameters
| Parameter | Value | Unit | Description |
| :--- | :--- | :--- | :--- |
| `mn1` | 23 | count | Input pair NMOS finger multiplicity |
| `wn1` | 2.50 µm | m | Input pair NMOS finger width |
| `ln1` | 90 nm | m | Input pair NMOS gate length |
| `mp1` | 3 | count | First-stage PMOS active load multiplicity |
| `wp1` | 2.50 µm | m | First-stage PMOS active load width |
| `lp1` | 90 nm | m | First-stage PMOS active load length |
| `mn3` | 3 | count | Reference bias diode NMOS multiplicity |
| `wn3` | 1.25 µm | m | Reference bias diode NMOS width |
| `ln3` | 90 nm | m | Reference bias diode NMOS length |
| `mn4` | 10 | count | First-stage tail current source multiplicity |
| `wn4` | 1.00 µm | m | First-stage tail current source width |
| `ln4` | 90 nm | m | First-stage tail current source length |
| `mp3` | 12 | count | Second-stage PMOS driver multiplicity |
| `wp3` | 2.25 µm | m | Second-stage PMOS driver width |
| `lp3` | 90 nm | m | Second-stage PMOS driver length |
| `mn5` | 17 | count | Second-stage NMOS current sink multiplicity |
| `wn5` | 1.25 µm | m | Second-stage NMOS current sink width |
| `ln5` | 90 nm | m | Second-stage NMOS current sink length |
| `cap` (`Cc`) | 0.80 pF | F | Miller compensation capacitor |
| `res` (`Rc`) | 5.20 kΩ | Ω | Nulling resistor |

### Specifications and Margins
| Specification | Target | Measured Value | Normalized Margin ($z$) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Gain** | $\ge 200.0\text{ V/V}$ | 589.7 V/V | +0.493 (margin: +194.8%) | Pass |
| **Phase Margin** | $\ge 60.0^\circ$ | 65.96° | +0.047 (margin: +5.96°) | Pass |
| **UGBW** | $\ge 100.0\text{ MHz}$ | 101.3 MHz | +0.006 (margin: +1.3 MHz) | Pass |
| **Slew Rate** | $\ge 30.0\text{ V/\mu s}$ | 51.58 V/µs | +0.265 (margin: +71.9%) | Pass |
| **Noise** | $\le 0.03\text{ V RMS}$ | 0.0106 V RMS | -0.477 (margin: -64.7%) | Pass |
| **Current** (opt) | minimize ($200\text{ \mu A}$) | 263.0 µA | +0.136 | Optimized |
| **Area** (opt) | minimize ($2.0\text{ n}m^2$) | 0.718 nm² | -0.472 | Optimized |

---

## 2. Design Evolution and Key Milestones

1. **Analyst (First-cut sizing, IDs 2 & 3)**:
   - Initial sizing derived from textbook equations with balanced current mirrors ($I_{\text{tail}}=56\,\mu\text{A}$, $I_2=175\,\mu\text{A}$, $C_c=1.5\,\text{pF}$, $R_c=1.5\,\text{k}\Omega$).
   - Measured ID 2: Gain 600 V/V, PM 52.3°, SR 26.9 V/µs, UGBW 33.2 MHz (FoM = -0.6058).
   - ID 3 tested $L_1=45\,\text{nm}$, revealing that short-channel $g_{ds}$ collapsed gain to 91.6 V/V. Sizing established that $L \ge 90\,\text{nm}$ is required for all signal transistors.
2. **Modeler (Model v1)**:
   - DC operating point analysis revealed that measured UGBW was bounded not by $g_{m1}/(2\pi C_c)$ ($60.4\,\text{MHz}$), but by the second pole $p_2 = g_{m6}/(2\pi C_L) = 24.5\,\text{MHz}$ causing early phase roll-off.
3. **Diagnoser & Sizer (Phase 1 Feasibility, IDs 4 -> 22)**:
   - ID 4: Doubled $m_{n1}$ (8 -> 16), lowered $C_c$ to $1.0\,\text{pF}$, $R_c=1.8\,\text{k}\Omega$. SR reached 34.4 V/µs (pass), UGBW climbed to 43.1 MHz.
   - ID 5: Doubled $W_{p3}$ and $W_{p1}$ to 2.0 µm maintaining balance ratio $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4} = 6.0$. Pushed $p_2$ out; UGBW rose to 50.2 MHz, PM to 54.0°.
   - ID 10: Swept $R_c$ to $3.5\,\text{k}\Omega$. LHP zero moved closer to UGBW, lifting PM to 72.0° and UGBW to 61.2 MHz.
   - IDs 11-13: Reduced $C_c$ to $0.5\,\text{pF}$ and increased $m_{n1}$ to 22. UGBW reached 102.6 MHz (pass), PM at 57.7°.
   - IDs 20-22: Balanced scaling of $m_{n4}=6$ ($I_{\text{tail}}=90\,\mu\text{A}$) and $m_{n5}=18$ ($I_2=270\,\mu\text{A}$) with $C_c=0.7\,\text{pF}$, $R_c=4.2\,\text{k}\Omega$. Reached full FEASIBILITY (ID 22, FoM = 0.5214, all constraints met).
4. **Phase 2 Optimization (IDs 23 -> 25)**:
   - Applied global mirror lever via $W_{n3}=1.25\,\mu\text{m}$ (scaled currents down by 20%) and maximized input pair fingers $m_{n1}=24$.
   - Reached expert boundary optimum: Candidate 25 with FoM = 0.6103, current reduced to 314.1 µA, UGBW exactly 100.04 MHz, PM 63.7°.
5. **Phase 3 & 4 RL Local Refinement and Polish (IDs 26 -> 777 -> 900)**:
   - TD3 anchored on Candidate 25 (`seed_rl`), followed by local perturbations (`warmup` and `train`).
   - Round 2 warmup produced Candidate 401 (FoM = 0.6131), polished with $R_c$ sweep to Candidate 622 (FoM = 0.6217, $C_c=0.6\,\text{pF}$, current = 319.5 µA).
   - Round 3 RL training discovered Candidate 777: FoM = 0.6357, achieving an additional 56.5 µA current reduction ($I_{\text{total}}=263.0\,\mu\text{A}$) by co-optimizing $m_{n3}=3$, $m_{n4}=10$, $m_{n5}=17$, and $C_c=0.8\,\text{pF}$.

---

## 3. Decision Lineage: Equations vs. RL vs. Failures

- **Decisions from Hand Equations**:
  - Mirror balancing relation $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4}$ preventing systematic offset (offset remained $< 2.5\,\text{mV}$ across all expert steps).
  - Identification of $p_2 = g_{m6}/(2\pi C_L)$ bottlenecking UGBW and PM, leading to widening of $M_{p3}$.
  - Nulling resistor LHP zero placement $f_z = 1/[2\pi C_c (R_c - 1/g_{m6})]$ to recover phase margin above 60°.
  - Global current scaling via bias transistor $S_{mn3}$ to lower total current while maintaining mirror balance.
- **Failed Predictions**:
  - $L_1=45\,\text{nm}$ in ID 3 collapsed stage gain by 85% due to channel length modulation ($g_{ds}$); equation required $L \ge 90\,\text{nm}$ constraint.
  - Large $R_c$ sweep ($>6.2\,\text{k}\Omega$) in ID 14-19 pushed UGBW out to 124 MHz, where high-frequency poles caused net phase loss, demonstrating an upper bound for $R_c$.
- **Decisions from TD3 Reinforcement Learning**:
  - Multi-parameter non-linear co-optimization between $m_{n3}=3$, $m_{n4}=10$, $m_{n5}=17$, and $m_{p1}=3$: RL adjusted the mirror sizing ratio to $S_{mp3}/S_{mp1} \approx 0.85 \times (2 S_{mn5}/S_{mn4})$ which lowered total current to 263 µA while internal DC node biasing safely kept all 8 devices in saturation with DC offset $V(\text{net5}) - V(\text{net4}) = -1.02\,\text{mV}$.
  - Trade-off between $C_c=0.8\,\text{pF}$ and $R_c=5.2\,\text{k}\Omega$ to provide low current while keeping UGBW at 101.3 MHz and PM at 65.96°.

---

## 4. Model Evolution

- **Version 1 (calibrated on IDs 2 and 3)**:
  - Validated stage gain equation $A_1 \cdot A_2 = 607$ vs. measured 600 V/V (+1.3% error).
  - Discovered that $p_2 = g_{m6}/(2\pi C_L) = 24.5\,\text{MHz}$ limited UGBW, correcting the simplified textbook model $UGBW = g_{m1}/(2\pi C_c)$.
  - Added short-channel validity condition: $L \ge 90\,\text{nm}$.
- **Accuracy on Final Design (Candidate 777)**:
  - Predicted gain: $A_1 \cdot A_2 = 32.35 \times 18.44 = 596.5\text{ V/V}$ vs. measured 589.7 V/V (error: +1.15%).
  - Predicted current: $30 + 76.05 + 157.0 = 263.05\,\mu\text{A}$ vs. measured 263.00 µA (exact).
  - Model proved highly accurate and predictive.

---

## 5. Transistor Operating Point of Final Design (Candidate 777)

| Transistor | Role | $I_d$ (µA) | $g_m$ (mS) | $g_m/I_d$ (1/V) | $V_{ds} - V_{dsat}$ (mV) | Region | Inversion |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **mn1** | Input pair (mirror side) | 38.03 | 0.814 | 21.39 | +354.3 | Saturation | Weak |
| **mn2** | Input pair (output side) | 38.03 | 0.814 | 21.39 | +354.3 | Saturation | Weak |
| **mp1** | Active load (diode side) | 38.03 | 0.511 | 13.43 | +386.4 | Saturation | Moderate |
| **mp2** | Active load (stage 1 out) | 38.03 | 0.511 | 13.43 | +386.4 | Saturation | Moderate |
| **mn3** | Reference bias diode | 30.00 | 0.543 | 18.11 | +377.6 | Saturation | Weak |
| **mn4** | Tail current source | 76.05 | 1.383 | 18.18 | +229.1 | Saturation | Weak |
| **mp3** | Stage 2 common-source | 157.00 | 2.037 | 12.98 | +863.7 | Saturation | Moderate |
| **mn5** | Stage 2 current sink | 157.00 | 2.858 | 18.21 | +144.5 | Saturation | Weak |

### Circuit Properties
- First-stage gain $A_1$: 32.35 V/V (30.2 dB)
- Second-stage gain $A_2$: 18.44 V/V (25.3 dB)
- Overall gain estimate: 596.5 V/V (measured: 589.7 V/V)
- $p_2 = g_{m6} / (2\pi C_L)$: 32.42 MHz
- LHP zero $f_z = 1 / [2\pi C_c (R_c - 1/g_{m6})]$: 42.25 MHz (provides $+67^\circ$ phase lead at UGBW)
- Systematic offset: $V(\text{net5}) - V(\text{net4}) = -1.02\,\text{mV}$

### Electrical Changes Introduced by RL (Candidate 25 -> Candidate 777)
- $I_2$ (second stage current) decreased from 215.9 µA to 157.0 µA (-27.3%), reducing total current from 314.1 µA to 263.0 µA (-16.3%).
- $I_{\text{tail}}$ increased slightly from 68.3 µA to 76.1 µA, keeping $g_{m1}$ strong ($0.814\,\text{mS}$) so that $g_{m1}/(2\pi C_c)$ remained high at 161.8 MHz.
- Nulling resistor $R_c$ increased from $4.2\,\text{k}\Omega$ to $5.2\,\text{k}\Omega$ to lower $f_z$ from 59.6 MHz to 42.2 MHz, compensating for the lower second-stage $g_{m6}$ ($2.04\,\text{mS}$) and ensuring phase margin remained above 65°.

---

## 6. Budget and Execution Statistics

- **Total Simulator Calls Used**: 900 / 1000
- **Total Hand Decisions Used**: 24 / 40
- **Operating-Point Lookups Used**: 4 / 20
- **Model Versions Generated**: 1 / 6
- **Total Feasible Pareto Designs Generated**: 65
- **Elapsed Real Time**: 2963 s (~49.4 min)

---

## 7. Remaining Design Trade-Offs

1. **Trade-off for Lower Current**:
   - $I_2$ is currently 157 µA. It could be reduced further, but $p_2$ would drop below 30 MHz, requiring higher $C_c$ (which increases area) or risking PM violation.
2. **Trade-off for Lower Area**:
   - $C_c$ is currently 0.8 pF (accounting for ~50% of the active area). Dropping $C_c$ to 0.5-0.6 pF reduces area by ~15%, but pushes UGBW higher and tightens the phase margin constraint against 60°. Candidate 622 ($C_c=0.6\,\text{pF}$, area $5.78\text{ nm}^2$, PM = 60.00°) represents this exact Pareto boundary.
