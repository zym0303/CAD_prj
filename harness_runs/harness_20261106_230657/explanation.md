# Opamp Sizing Review and Design Explanation

## Run Overview
- **Run ID**: `harness_20261106_230657`
- **Mode**: `full`
- **Total Simulator Calls**: 923 / 1000 budget
- **LLM Decisions (Hand Sims / Sweeps)**: 33
- **RL Exploration & Training Calls**: 890 (Warmup: 230, Training: 660)
- **Feasible Candidates Found**: 29
- **Elapsed Time**: 972.3 s (~16.2 min)
- **Final Best Candidate**: **Candidate 832**
- **Feasible**: **Yes**
- **Figure of Merit (FoM)**: **0.6724** (Feasible threshold > 0.3)

---

## Final Best Design (Candidate 832)

### 1. Final Parameters
| Device / Element | Parameters | Description |
|---|---|---|
| **mn1, mn2** | `mn1=20`, `wn1=1.0 um`, `ln1=90 nm` | NMOS input differential pair (W_total = 20 um) |
| **mp1, mp2** | `mp1=3`, `wp1=1.25 um`, `lp1=90 nm` | PMOS active current-mirror load of stage 1 |
| **mn3** | `mn3=1`, `wn3=1.0 um`, `ln3=90 nm` | Diode-connected NMOS bias reference (Ibias = 30 uA) |
| **mn4** | `mn4=2`, `wn4=1.0 um`, `ln4=90 nm` | Tail current source mirror (I_tail ~ 60 uA) |
| **mp3** | `mp3=15`, `wp3=1.25 um`, `lp3=90 nm` | PMOS common-source 2nd stage driver |
| **mn5** | `mn5=4`, `wn5=1.5 um`, `ln5=90 nm` | 2nd stage NMOS current sink mirror (I_2 ~ 150 uA) |
| **Cc** | `cap=0.4 pF` (`4.0e-13 F`) | Miller compensation capacitor |
| **Rc** | `res=7700 ohm` | Nulling series resistor for zero cancellation / LHP placement |

### 2. Final Specifications and Margins
| Specification | Target | Achieved Value | Margin | Normalized Score ($z$) | Status |
|---|---|---|---|---|---|
| **Gain** | $\ge 200$ V/V | **334.7 V/V** | +134.7 V/V | +0.252 | **Satisfied** |
| **Phase Margin (PM)** | $\ge 60^\circ$ | **63.97 deg** | $+3.97^\circ$ | +0.0321 | **Satisfied** |
| **Slew Rate (SR)** | $\ge 30$ V/$\mu$s | **57.10 V/$\mu$s** | +27.1 V/$\mu$s | +0.311 | **Satisfied** |
| **UGBW** | $\ge 100$ MHz | **100.70 MHz** | +0.70 MHz | +0.00355 | **Satisfied** |
| **Input Noise** | $\le 0.03$ V RMS | **0.01023 V RMS** | -0.01977 V RMS | -0.491 | **Satisfied** |
| **Area** | minimize ($2\times 10^{-9}\,\text{m}^2$) | **$7.148\times 10^{-10}\,\text{m}^2$** | -64.3% vs target | -0.473 | **Optimized** |
| **Current** | minimize ($200\,\mu\text{A}$) | **$244.9\,\mu\text{A}$** | $+44.9\,\mu\text{A}$ | +0.101 | **Optimized** |

FoM formulation:
$$\text{FoM} = 0.3 - z_{\text{area}} - z_{\text{current}} = 0.3 - (-0.473) - 0.101 = 0.6724$$

---

## Design Story & Lineage

The evolution from initial topology hand calculations to final optimized solution followed a structured chain of explainable steps:

1. **Candidate 1 (Analyst)**: Baseline hand calculation derived from first-order equations ($I_{\text{tail}}=60\,\mu\text{A}$, $I_2=90\,\mu\text{A}$, $C_c=1.5\,\text{pF}$, $R_c=800\,\Omega$, balance ratio $3:1$). Met DC gain (615) and noise, but phase margin ($24.6^\circ$) and UGBW ($23.4\,\text{MHz}$) were far below targets.
2. **Candidate 2 (Analyst)**: Sized $C_c$ down $1.5\,\text{pF}\to 0.5\,\text{pF}$, increased $m_{n1}$ $4\to 8$, and increased stage 2 drive ($m_{n5}=4, m_{p3}=8$, ratio $4:1$). UGBW rose to $49.0\,\text{MHz}$ and slew rate met spec ($39.4\,\text{V}/\mu\text{s}$).
3. **Candidate 8 (Sizer Sweep)**: Diagnosed binding spec as PM ($18.8^\circ$). Swept $R_c$ from $500\,\Omega$ to $3000\,\Omega$ to push the RHP zero into the LHP. PM monotonically increased from $17.9^\circ$ to $37.7^\circ$.
4. **Candidate 13 (Sizer Sweep)**: Extended $R_c$ sweep across $4000\,\Omega - 8000\,\Omega$. At $R_c=8000\,\Omega$, PM cleared the feasibility threshold to reach $65.8^\circ$, leaving UGBW ($62.2\,\text{MHz}$) as the only violated constraint.
5. **Candidate 19 (Sizer Sweep)**: Swept input pair $m_{n1}$ from 10 to 20 to increase $g_{m1}$. Discovered that UGBW saturated near $64.2\,\text{MHz}$ due to the non-dominant pole $p_2 \approx g_{m6}/C_L$ clamping loop crossover.
6. **Candidate 20 (Sizer Simulation)**: Attempted shortening channel length $l_{n1}$ $90\,\text{nm}\to 45\,\text{nm}$ to increase $g_{m1}$. **Failed prediction**: DIBL and severe output resistance reduction collapsed gain to 98 and dropped UGBW to $40.7\,\text{MHz}$. Established lesson that $l_{n1} \ge 90\,\text{nm}$ is essential.
7. **Candidate 23 (Sizer Sweep)**: Swept $C_c$ across $0.4\,\text{pF} - 0.2\,\text{pF}$ on Candidate 19. At $C_c=0.4\,\text{pF}$, UGBW reached $67.4\,\text{MHz}$ and PM was $57.4^\circ$.
8. **Candidate 24 (Sizer Simulation)**: Addressed non-dominant pole $p_2$ by scaling $m_{p3}$ $8\to 16$ and $m_{p1}$ $2\to 4$ (keeping balance ratio $4:1$). $g_{m6}$ doubled, pushing UGBW to $84.6\,\text{MHz}$ and PM to $59.59^\circ$ (within $0.4^\circ$ of target).
9. **Candidate 25 (Sizer Simulation)**: Final Phase 1 push with $C_c=0.3\,\text{pF}, R_c=9000\,\Omega$. Reached UGBW $93.4\,\text{MHz}$, PM $54.6^\circ$, reward $-0.0594$ (best expert anchor).
10. **Candidate 348 (RL Refinement)**: TD3 local exploration anchored on expert designs co-optimized device geometries ($m_{p1}=3, w_{p1}=1.25\,\mu\text{m}, m_{p3}=15, w_{p3}=1.25\,\mu\text{m}, w_{n5}=1.5\,\mu\text{m}, C_c=0.4\,\text{pF}, R_c=8000\,\Omega$). Crossed all hard constraints into full feasibility with FoM **0.6545** (UGBW $104\,\text{MHz}$, PM $61.7^\circ$).
11. **Candidate 577 (Sizer Polish Sweep)**: Polished $R_c$ across $7500\,\Omega - 8500\,\Omega$ on Candidate 348. $R_c=7700\,\Omega$ reduced passive area to $7.23\times 10^{-10}\,\text{m}^2$ while preserving PM $61.5^\circ$ and UGBW $101.6\,\text{MHz}$, elevating FoM to **0.6659**.
12. **Candidate 832 (Sizer Polish Sweep)**: Polished input width $w_{n1}$ across $1.0\,\mu\text{m} - 1.5\,\mu\text{m}$ on Candidate 577. $w_{n1}=1.0\,\mu\text{m}$ reduced input parasitic capacitance, boosting PM to $64.0^\circ$, reducing area to $7.148\times 10^{-10}\,\text{m}^2$ and current to $244.9\,\mu\text{A}$, reaching the final optimal FoM **0.6724**.

---

## Decisions: Equations vs RL vs Failed Predictions

- **Decisions from Hand Equations**:
  - Current partitioning ($I_{\text{tail}} \approx 60\,\mu\text{A}$, $I_2 \approx 120-150\,\mu\text{A}$).
  - Systematic DC offset balance: $S_{mp3}/S_{mp1} = 2 \cdot S_{mn5}/S_{mn4}$.
  - Nulling resistor zero movement: choosing $R_c > 1/g_{m6}$ to generate a left-half plane zero canceling excess phase lag from $p_2$.
  - Diagnosis of second-pole clamping: recognizing that increasing $g_{m1}$ cannot raise UGBW once $g_{m1}/C_c$ approaches $g_{m6}/C_L$.
- **Decisions from RL**:
  - Multi-dimensional joint tuning of stage 1 load aspect ratios ($w_{p1}=1.25\,\mu\text{m}, m_{p1}=3$) and stage 2 driver sizing ($w_{p3}=1.25\,\mu\text{m}, m_{p3}=15, w_{n5}=1.5\,\mu\text{m}$) that escaped the manual local search boundary and achieved concurrent feasibility across all 5 hard specs.
  - Generating a dense population of 29 feasible designs spanning the Pareto trade-off curve.
- **Failed Predictions & Lessons**:
  - *Shortening $l_{n1}$ to $45\,\text{nm}$*: Predicted to increase $g_{m1}$ and UGBW; failed due to strong channel-length modulation and DIBL collapsing stage 1 DC gain below spec.
  - *Scaling $m_{n1}$ alone past 16*: Predicted to push UGBW past $100\,\text{MHz}$; moved UGBW by $<2\,\text{MHz}$ due to non-dominant pole clamping.

---

## Remaining Circuit Trade-Offs

1. **Lower Current Trade-off**:
   - Total current is $244.9\,\mu\text{A}$ ($+44.9\,\mu\text{A}$ above nominal target).
   - $I_2$ can be lowered by reducing $w_{n5}$ ($1.5\,\mu\text{m}\to 1.0\,\mu\text{m}$), but this reduces $g_{m6}$ and lowers UGBW below $100\,\text{MHz}$. To do so, load capacitance $C_L$ would need to be lower, or $C_c$ reduced further with higher $R_c$.
2. **Lower Area Trade-off**:
   - The total active + passive area is $0.715\,\mu\text{m}^2$ (well below the $2.0\,\mu\text{m}^2$ target).
   - $R_c$ ($7.7\,\text{k}\Omega$) and $C_c$ ($0.4\,\text{pF}$) account for over 60% of total area. Dropping $R_c$ below $7.7\,\text{k}\Omega$ directly degrades phase margin below the $60^\circ$ specification.
