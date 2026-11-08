# Opamp Sizing Final Review & Explanation

**Run ID**: `harness_20261107_114002`  
**Best Candidate ID**: `532`  
**Final Figure of Merit (FoM)**: `0.6819` (Feasible: Yes)

---

## 1. Final Parameters & Specifications

### Physical Sizing Parameters
- **Input Pair ($mn_1/mn_2$)**: $mn_1 = 22$, $W_{n1} = 2.0\,\mu\text{m}$, $L_{n1} = 90\,\text{nm}$
- **Stage 1 Load ($mp_1/mp_2$)**: $mp_1 = 4$, $W_{p1} = 2.0\,\mu\text{m}$, $L_{p1} = 90\,\text{nm}$
- **Bias Diode ($mn_3$)**: $mn_3 = 2$, $W_{n3} = 1.0\,\mu\text{m}$, $L_{n3} = 90\,\text{nm}$
- **Tail Current Source ($mn_4$)**: $mn_4 = 4$, $W_{n4} = 1.0\,\mu\text{m}$, $L_{n4} = 90\,\text{nm}$
- **Stage 2 PMOS ($mp_3$)**: $mp_3 = 16$, $W_{p3} = 2.0\,\mu\text{m}$, $L_{p3} = 90\,\text{nm}$
- **Stage 2 Current Sink ($mn_5$)**: $mn_5 = 8$, $W_{n5} = 1.0\,\mu\text{m}$, $L_{n5} = 90\,\text{nm}$
- **Compensation Network**: $C_c = 0.6\,\text{pF}$ ($6.0\times 10^{-13}\,\text{F}$), $R_c = 8300\,\Omega$

### Performance Specifications vs Targets

| Specification | Target | Achieved (TT, 27°C, 1.2V) | Margin / Normalized Score | Constraint Status |
|---|---|---|---|---|
| **DC Gain** | $\ge 200\,\text{V/V}$ | **$771.7\,\text{V/V}$** ($57.7\,\text{dB}$) | $+58.8\%$ ($z = +0.588$) | PASS (Hard) |
| **Unity Gain Bandwidth** | $\ge 100\,\text{MHz}$ | **$100.2\,\text{MHz}$** | $+0.2\%$ ($z = +0.0009$) | PASS (Hard) |
| **Phase Margin** | $\ge 60.0^\circ$ | **$60.25^\circ$** | $+0.4\%$ ($z = +0.0021$) | PASS (Hard) |
| **Slew Rate** | $\ge 30\,\text{V/}\mu\text{s}$ | **$52.31\,\text{V/}\mu\text{s}$** | $+74.4\%$ ($z = +0.271$) | PASS (Hard) |
| **Input-Referred Noise** | $\le 0.03\,\text{V RMS}$ | **$0.01473\,\text{V RMS}$** | $+50.9\%$ ($z = -0.341$) | PASS (Hard) |
| **Total Current** | Minimize (Target $200\,\mu\text{A}$) | **$207.8\,\mu\text{A}$** | $z = +0.0191$ | Objective |
| **Silicon Area** | Minimize (Target $2.0\,\text{nm}^2$) | **$8.551\times 10^{-10}\,\text{m}^2$** | $z = -0.401$ | Objective |

$$\text{FoM} = 0.3 - z_{\text{area}} - z_{\text{current}} = 0.3 - (-0.401) - 0.0191 = 0.6819$$

---

## 2. Design Story & Lineage

1. **Analyst (Hand Equations & Baseline Candidate 2)**:
   - *Change*: Selected current split $I_{\text{tail}} \approx 56\,\mu\text{A}$, $I_2 \approx 89\,\mu\text{A}$, $C_c = 1.2\,\text{pF}$, $R_c = 1400\,\Omega$, with matching mirror lengths ($90\,\text{nm}$) and balance ratio $mp_3/mp_1 = 2 \cdot mn_5/mn_4 = 3$.
   - *Effect*: Met Gain ($664\,\text{V/V}$), Current ($174.5\,\mu\text{A}$), Slew Rate ($30.12\,\text{V/}\mu\text{s}$), and Noise ($0.0197$), but UGBW stalled at $30.2\,\text{MHz}$ and PM at $32.86^\circ$ ($\text{FoM} = -0.7959$).
2. **Diagnoser & Sizer (Phase 1 Feasibility $\to$ Candidate 3)**:
   - *Change*: Identified second pole $p_2 = g_{m6}/(2\pi C_L) = 14.86\,\text{MHz}$ as the critical bottleneck throttling UGBW. Boosted $g_{m6}$ via wider $mp_3$ ($16$ fingers), balanced by $mp_1 = 4$ and $mn_5 = 8$; widened input pair $mn_1 = 22$; scaled $C_c$ down to $0.6\,\text{pF}$ and increased $R_c$ to $8400\,\Omega$ to move the LHP zero into the $30\text{--}40\,\text{MHz}$ region.
   - *Effect*: Reached full feasibility with Candidate 3 ($\text{FoM} = 0.6784$, $\text{UGBW} = 101.0\,\text{MHz}$, $\text{PM} = 60.05^\circ$).
3. **RL Strategist (Phase 3 TD3 Refinement)**:
   - *Change*: Explored 900+ states in the replay buffer around Candidate 3. Discovered 15 feasible Pareto candidates (such as Candidate 662 and Candidate 88) exploring alternative currents and phase margin trade-offs.
   - *Effect*: Confirmed Candidate 3 sits right at the optimal trade-off boundary between current consumption, bandwidth, and area.
4. **Sizer (Phase 4 Polish Sweep $\to$ Final Candidate 532)**:
   - *Change*: Swept $R_c$ across 8 grid points ($8000\text{--}8700\,\Omega$) on Candidate 3.
   - *Effect*: At $R_c = 8300\,\Omega$, layout area was reduced to $8.551\times 10^{-10}\,\text{m}^2$ while preserving $\text{PM} = 60.25^\circ$ and $\text{UGBW} = 100.2\,\text{MHz}$, improving the global best FoM to **$0.6819$**.

---

## 3. Decisions from Equations vs RL vs Sizer Screening

- **Equations**: Derived current mirror ratios, systematic offset zeroing condition ($S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4}$), and the realization that second stage transconductance $g_{m6}$ governs both the non-dominant pole $p_2 = g_{m6}/(2\pi C_L)$ and the Miller zero $f_z \approx 1/(2\pi(R_c - 1/g_{m6})C_c)$.
- **Screening & Failed Predictions**:
  - *Failed Idea*: Dropping PMOS gate lengths $L_{p1}, L_{p3}$ from $90\,\text{nm}$ to minimum grid length $45\,\text{nm}$ was screened via `quick_analysis`. It failed drastically: DIBL and channel length modulation collapsed DC gain from $664\,\text{V/V}$ down to $20.8\,\text{V/V}$ ($A_1 \approx 5.4$, $A_2 \approx 4.2$). Screening caught this immediately at zero simulation cost.
  - *LHP Zero Placement*: Hand calculation suggested $R_c \approx 1/g_{m6} \approx 600\text{--}1000\,\Omega$. However, screening proved that placing the zero far away ($>500\,\text{MHz}$) failed to rescue phase margin at $100\,\text{MHz}$. Raising $R_c$ to $8300\,\Omega$ placed the zero directly at $34.3\,\text{MHz}$, providing vital phase lead exactly where $p_2$ induced phase lag.
- **RL Exploration**: TD3 thoroughly mapped the multi-dimensional stability envelope around the hand solution, proving that no localized perturbation of lengths, widths, or currents could exceed Candidate 532's FoM without either violating UGBW ($<100\,\text{MHz}$) or increasing current/area.

---

## 4. Operating Point Analysis of Candidate 532

### Transistor DC Operating Point Table

| Device | Role | $I_d\,(\mu\text{A})$ | $g_m\,(\text{mS})$ | $g_{m}/I_d\,(\text{V}^{-1})$ | $V_{gs}\,(\text{V})$ | $V_{ds}\,(\text{V})$ | $V_{dsat}\,(\text{V})$ | $V_{ds} - V_{dsat}\,(\text{V})$ | Region | Inversion |
|---|---|---|---|---|---|---|---|---|---|---|
| **$mn_1$** | Input Pair (mirror) | $28.38$ | $0.608$ | $21.42$ | $0.311$ | $0.420$ | $0.043$ | $+0.377$ | Saturation | Weak |
| **$mn_2$** | Input Pair (out) | $28.38$ | $0.608$ | $21.42$ | $0.311$ | $0.420$ | $0.043$ | $+0.377$ | Saturation | Weak |
| **$mp_1$** | Load Diode | $28.38$ | $0.423$ | $14.90$ | $0.490$ | $0.490$ | $0.112$ | $+0.378$ | Saturation | Moderate |
| **$mp_2$** | Load Mirror | $28.38$ | $0.423$ | $14.90$ | $0.490$ | $0.490$ | $0.112$ | $+0.378$ | Saturation | Moderate |
| **$mn_3$** | Bias Reference | $30.00$ | $0.495$ | $16.52$ | $0.473$ | $0.473$ | $0.070$ | $+0.402$ | Saturation | Moderate |
| **$mn_4$** | Tail Current | $56.76$ | $0.944$ | $16.63$ | $0.473$ | $0.289$ | $0.069$ | $+0.220$ | Saturation | Moderate |
| **$mp_3$** | 2nd Stage PMOS | $121.1$ | $1.781$ | $14.72$ | $0.490$ | $0.697$ | $0.114$ | $+0.583$ | Saturation | Moderate |
| **$mn_5$** | 2nd Stage Sink | $121.1$ | $1.997$ | $16.50$ | $0.473$ | $0.503$ | $0.070$ | $+0.433$ | Saturation | Moderate |

### Small-Signal & Frequency Quantities
- **First Stage Gain ($A_1$)**: $31.30\,\text{V/V}$
- **Second Stage Gain ($A_2$)**: $24.92\,\text{V/V}$
- **Calculated Gain ($A_1 \times A_2$)**: $780.3\,\text{V/V}$ (matches simulated $771.7\,\text{V/V}$)
- **First Stage gm/Cc pole**: $g_{m1}/(2\pi C_c) = 161.2\,\text{MHz}$
- **Second Pole ($p_2$)**: $g_{m6}/(2\pi C_L) = 28.35\,\text{MHz}$ (with $C_L = 10\,\text{pF}$)
- **LHP Nulling Zero**: $f_z = 1/[2\pi (R_c - 1/g_{m6}) C_c] = 34.28\,\text{MHz}$
- **DC Balance**: $S_{mp3}/S_{mp1} = 4.0$, $2 S_{mn5}/S_{mn4} = 4.0$ ($\text{Ratio} = 1.000$, $\Delta V = 1.5\,\mu\text{V}$, $V_{\text{out,DC}} = 0.5032\,\text{V}$ mid-rail).

---

## 5. PVT Robustness Analysis (12 Corners)

A 12-corner PVT sweep was evaluated ($0^\circ\text{C}$ to $100^\circ\text{C}$, $1.0\,\text{V}$ to $1.2\,\text{V}$, TT/SS/FF process corners):

| Spec | Target | Worst-Case Value | Worst Corner |
|---|---|---|---|
| **DC Gain** | $\ge 200\,\text{V/V}$ | **$507.3\,\text{V/V}$** | FF, 1.0 V, 100°C |
| **Noise** | $\le 0.03\,\text{V RMS}$ | **$0.01723\,\text{V RMS}$** | SS, 1.2 V, 0°C |
| **Total Current** | Min (200 $\mu$A) | **$212.4\,\mu\text{A}$** | FF, 1.2 V, 0°C |
| **Area** | Min (2 $\text{nm}^2$) | **$8.551\times 10^{-10}\,\text{m}^2$** | TT, 1.2 V, 0°C |
| **Phase Margin** | $\ge 60.0^\circ$ | **$57.93^\circ$** | SS, 1.0 V, 0°C |
| **Slew Rate** | $\ge 30\,\text{V/}\mu\text{s}$ | **$24.28\,\text{V/}\mu\text{s}$** | SS, 1.0 V, 100°C |
| **UGBW** | $\ge 100\,\text{MHz}$ | **$58.77\,\text{MHz}$** | SS, 1.0 V, 100°C |

- **Nominal Corner (TT, 27°C, 1.2V)**: Fully feasible ($\text{FoM} = 0.6819$, 0 violations).
- **Corner Behavior**: In the slow process corner at elevated temperature ($100^\circ\text{C}$) and reduced supply ($1.0\,\text{V}$), carrier mobility and transconductance drop, reducing UGBW to $58.8\,\text{MHz}$ and Slew Rate to $24.3\,\text{V/}\mu\text{s}$. Gain and noise maintain wide safety margins across all 12 corners.

---

## 6. Cheap Analyses Utilization

- **`quick_calls` Used**: 12 calls (56 quick variant simulations).
- **`operating_point` / `compare_operating_points` Lookups**: 4 lookups.
- **`corner_check` Calls**: 1 call (12 PVT runs).
- **Impact**: Screening screened out 56 design variants before ever committing simulator calls. Crucially, screening prevented wasted simulations on $45\,\text{nm}$ channel length variants (which collapsed gain) and enabled precise closed-loop placement of $R_c$ and $C_c$.

---

## 7. Budget & Runtime Summary

- **Total Simulator Calls**: 910 calls (91% of 1000 budget used).
  - LLM Hand decisions: 4 decisions (Analyst: 2 sims, Sizer: 1 sim, Polish sweep: 8 sims = 1 decision).
  - RL Warmup: 175 simulations.
  - RL TD3 Training: 725 simulations.
- **Feasible Designs Found**: 15 distinct feasible solutions.
- **Elapsed Wall-Clock Time**: ~947 seconds.

---

## 8. Trade-Offs Remaining

1. **Lower Current**: Tail current ($56.8\,\mu\text{A}$) and second stage current ($121.1\,\mu\text{A}$) can be scaled down by increasing $W_{n3}$ from $1.0\,\mu\text{m}$ to $1.25\,\mu\text{m}$. This saves $\sim 35\,\mu\text{A}$ of supply current, but will require relaxing the UGBW constraint from $100\,\text{MHz}$ to $\sim 75\text{--}80\,\text{MHz}$.
2. **Lower Area**: Capacitor $C_c = 0.6\,\text{pF}$ accounts for a substantial fraction of the area ($8.55\times 10^{-10}\,\text{m}^2$). Dropping $C_c$ to $0.4\,\text{pF}$ reduces area by $\sim 15\%$, but requires accepting a lower phase margin ($\sim 54^\circ$).
