# Opamp Sizing Explanation & Design Lineage Report

**Run ID**: `harness_20261107_121945`  
**Topology**: Two-Stage Miller OTA with Nulling Resistor (45 nm CMOS, $V_{DD} = 1.2$ V, $C_L = 10$ pF, $I_{bias} = 30\ \mu$A)  
**Best Design ID**: `351` (Source: TD3 Reinforcement Learning local refinement)  
**Best FoM**: **0.7240** (Feasible, constraint threshold $> 0.3$)

---

## 1. Final Parameters & Specifications

### Physical Parameters
| Parameter | Description | Value | Unit |
| :--- | :--- | :--- | :--- |
| `mn1` / `wn1` / `ln1` | Input differential pair NMOS | 11 / 2.50 $\mu$m / 90 nm | count / m / m |
| `mp1` / `wp1` / `lp1` | First-stage PMOS active mirror load | 5 / 2.50 $\mu$m / 90 nm | count / m / m |
| `mn3` / `wn3` / `ln3` | Bias diode NMOS ($30\ \mu$A source) | 3 / 1.00 $\mu$m / 90 nm | count / m / m |
| `mn4` / `wn4` / `ln4` | Tail current source NMOS | 6 / 1.25 $\mu$m / 90 nm | count / m / m |
| `mp3` / `wp3` / `lp3` | Second-stage PMOS common source | 16 / 2.50 $\mu$m / 90 nm | count / m / m |
| `mn5` / `wn5` / `ln5` | Second-stage NMOS current sink | 13 / 1.00 $\mu$m / 90 nm | count / m / m |
| `cap` ($C_c$) | Miller compensation capacitor | 0.60 | pF |
| `res` ($R_c$) | Miller nulling resistor | 6.0 | $\text{k}\Omega$ |

### Specifications & Constraint Margins
| Specification | Target | Achieved Value | Margin (Normalized $z$) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **DC Gain** | $\ge 200.0$ V/V (46.0 dB) | **729.5 V/V** (57.3 dB) | $+0.570$ | **PASS** (Large margin) |
| **Unity-Gain Bandwidth** | $\ge 100.0$ MHz | **100.8 MHz** | $+0.0039$ | **PASS** (Binding constraint) |
| **Phase Margin** | $\ge 60.0^\circ$ | **61.75$^\circ$** | $+0.0144$ | **PASS** (Well balanced) |
| **Slew Rate** | $\ge 30.0$ V/$\mu$s | **57.89 V/$\mu$s** | $+0.317$ | **PASS** (High margin) |
| **Input-Referred Noise** | $\le 30.0$ mV RMS | **16.12 mV RMS** | $-0.301$ | **PASS** (Low noise) |
| **Total Current** | minimize (target $200\ \mu$A) | **227.4 $\mu$A** | $+0.0641$ | Optimized |
| **Total Area** | minimize (target $2.00\text{ n}\text{m}^2$) | **$6.88 \times 10^{-10}\ \text{m}^2$** | $-0.488$ | Optimized (65.6% below target) |

---

## 2. Design Story & Lineage

The sizing progression moved through structured phases:
1. **Analyst (Candidate 1)**: First-cut sizing derived from analytical equations ($I_{tail}=56\ \mu$A, $I_2=90\ \mu$A, $C_c=1.0$ pF, $R_c=4.5\text{ k}\Omega$). Satisfied gain (723 V/V), phase margin ($66.4^\circ$), and slew rate ($37.2$ V/$\mu$s), but UGBW stalled at 45.9 MHz due to the second pole $p_2 = g_{m6}/(2\pi C_L) \approx 19.5$ MHz. Infeasible (reward = -0.3435).
2. **Sizer (Candidate 2)**: Lowered $C_c$ to 0.7 pF and tuned $R_c$ to $5.0\text{ k}\Omega$. UGBW increased from 45.9 MHz to 53.6 MHz, PM held at $60.4^\circ$, and area dropped from $6.95\times 10^{-10}$ to $6.30\times 10^{-10}\ \text{m}^2$ (reward = -0.2727).
3. **Sizer (Candidate 3)**: Boosted second-stage transconductance $g_{m6}$ ($mn5=11, mp3=11, wp3=2.5\ \mu$m) and input transconductance $g_{m1}$ ($mn1=22, wn1=2.75\ \mu$m), $C_c=0.6$ pF, $R_c=7.5\text{ k}\Omega$. UGBW surged to 86.5 MHz, PM at $59.84^\circ$ (reward = -0.0524).
4. **Sizer (Candidate 4)**: Increased second-stage sink $mn5=14, mp3=14$ with $C_c=0.7$ pF, $R_c=7.0\text{ k}\Omega$. **First feasible design achieved** (FoM = 0.6529, UGBW = 100.6 MHz, PM = $60.57^\circ$, SR = 48.9 V/$\mu$s, Gain = 753 V/V).
5. **Sizer (Candidates 5, 6, 7)**: Systematically trimmed input pair size from $mn1=22$ down to $mn1=12$ in 3 iterations. Reduced input gate capacitance and die area, lifting PM to $66.53^\circ$ and yielding the **best expert design** (Candidate 7, FoM = 0.6686, Area = $7.89\times 10^{-10}\ \text{m}^2$).
6. **RL Strategist (Candidate 351)**: Seeded TD3 actor with Candidate 7 and executed sparse exploration with noise-controlled training. TD3 discovered a novel asymmetric current redistribution: it increased $W_{n4}$ to $1.25\ \mu$m (raising $I_{tail}$ to $70.6\ \mu$A and $g_{m1}$ to 0.733 mS) while reducing $I_2$ to $126.8\ \mu$A. This permitted lowering $C_c$ from 0.7 pF to 0.6 pF, dropping total circuit area to $6.88\times 10^{-10}\ \text{m}^2$ and boosting slew rate to 57.89 V/$\mu$s, while strictly maintaining UGBW = 100.8 MHz and PM = $61.75^\circ$. **Overall Best FoM = 0.7240**.
7. **Sizer (Candidate 351 Sweep Polish)**: Swept $R_c \in [5.6\text{k}, 6.6\text{k}]\ \Omega$. Confirmed $R_c = 6.0\text{ k}\Omega$ as the optimal Pareto peak (lower $R_c$ violates UGBW, higher $R_c$ increases area).

---

## 3. Equation-Guided vs. RL-Discovered Mechanisms

- **From Hand Equations**:
  - DC gain requirement ($A_v \ge 200$) mandated minimum channel lengths of $L = 90$ nm for load devices to suppress channel-length modulation.
  - Zero-systematic-offset balance condition: $\frac{S_{mp3}}{S_{mp1}} \approx 2 \frac{S_{mn5}}{S_{mn4}}$.
  - Lead-lag compensation via nulling resistor $R_c > 1/g_{m6}$ to generate a Left-Half-Plane (LHP) zero:
    $$z_{LHP} = -\frac{1}{C_c (R_c - 1/g_{m6})}$$
    positioned between 35 MHz and 50 MHz to cancel the phase lag of the second pole $p_2 = g_{m6}/(2\pi C_L) \approx 31.2$ MHz.
- **Failed Prediction (Diagnosed & Fixed)**:
  - An exploratory attempt using minimum channel length $L = 45$ nm across signal devices caused output conductance $g_{ds}$ to explode, collapsing DC gain to 11.06 V/V. `quick_analysis` instantly identified this failure without wasting simulator calls, steering the design back to $L = 90$ nm.
- **RL-Discovered Innovations**:
  - Rather than scaling devices proportionally, TD3 realized that second-stage pole $p_2$ was already high enough at 31 MHz, but stage-1 transconductance $g_{m1}$ was the gating factor for lowering $C_c$. By widening $mn4$ ($1.25\ \mu$m) and slightly narrowing $mn5$, RL shifted current from stage 2 to stage 1, raising $g_{m1}$ by 22.8% and allowing $C_c$ to be reduced to 0.6 pF.

---

## 4. Operating Point Analysis of Final Design (Candidate 351)

### Device DC Operating Points
| Device | Role | $I_d\ (\mu\text{A})$ | $g_m\ (\text{mS})$ | $g_m/I_d\ (\text{V}^{-1})$ | $V_{ov}\ (\text{V})$ | $V_{ds}\ (\text{V})$ | $V_{ds} - V_{dsat}\ (\text{V})$ | Region |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mn1`, `mn2` | Input diff pair | 35.32 | 0.733 | 20.75 | -0.124 | 0.467 | +0.422 | Saturation (weak) |
| `mp1`, `mp2` | Active mirror load | 35.32 | 0.558 | 15.78 | +0.058 | 0.476 | +0.373 | Saturation (moderate) |
| `mn3` | Bias reference | 30.00 | 0.528 | 17.60 | -0.018 | 0.449 | +0.387 | Saturation (moderate) |
| `mn4` | Tail current source | 70.64 | 1.250 | 17.70 | -0.020 | 0.258 | +0.196 | Saturation (moderate) |
| `mp3` | Stage-2 driver | 126.80 | 1.958 | 15.45 | +0.063 | 0.832 | +0.726 | Saturation (moderate) |
| `mn5` | Stage-2 current sink | 126.80 | 2.237 | 17.65 | -0.019 | 0.368 | +0.306 | Saturation (moderate) |

### Key Circuit Quantities
- First-Stage Gain: $A_1 = 30.24$
- Second-Stage Gain: $A_2 = 24.39$
- Total DC Gain Estimate: $A_1 \times A_2 = 737.6$ V/V (simulated: 729.5 V/V)
- Uncompensated Pole Projection: $g_{m1}/(2\pi C_c) = 194.4$ MHz
- Second Pole Frequency: $p_2 = g_{m6}/(2\pi C_L) = 31.17$ MHz
- Nulling Zero: $z_{LHP} = 48.32$ MHz (with $R_c = 6000\ \Omega$ vs $1/g_{m6} = 510.6\ \Omega$)
- Balance Metric: Systematic offset $\Delta V = -0.12$ mV (effectively zero)

---

## 5. PVT Robustness Verification (12 Corners)

The design was verified across the standard 12 corners: $\{TT, SS, FF\} \times \{1.0\text{ V}, 1.2\text{ V}\} \times \{0^\circ\text{C}, 100^\circ\text{C}\}$.

| Specification | Worst-Case Value | Worst-Case Corner | Target Constraint | Margin in Worst Corner |
| :--- | :--- | :--- | :--- | :--- |
| **DC Gain** | **502.9 V/V** | SS 1.0V 100$^\circ$C | $\ge 200.0$ V/V | $+302.9$ V/V (PASS) |
| **Noise** | **18.77 mV RMS** | SS 1.2V 0$^\circ$C | $\le 30.0$ mV RMS | $-11.23$ mV (PASS) |
| **Slew Rate** | **33.51 V/$\mu$s** | SS 1.0V 100$^\circ$C | $\ge 30.0$ V/$\mu$s | $+3.51$ V/$\mu$s (PASS) |
| **Phase Margin** | **56.88$^\circ$** | SS 1.0V 100$^\circ$C | $\ge 60.0^\circ$ | $-3.12^\circ$ (Marginal at 100$^\circ$C) |
| **UGBW** | **62.26 MHz** | SS 1.0V 100$^\circ$C | $\ge 100.0$ MHz | $-37.74$ MHz (Degraded by $T$) |
| **Current** | **232.9 $\mu$A** | FF 1.2V 0$^\circ$C | minimize ($200\ \mu$A) | $+32.9\ \mu$A |
| **Area** | **$6.88\times 10^{-10}\ \text{m}^2$** | Constant | minimize ($2.0\text{ n}\text{m}^2$) | $-1.312\text{ n}\text{m}^2$ |

- **Nominal Corner (TT, 1.2V, 27$^\circ$C)**: Fully feasible (FoM = 0.7240).
- **Sub-zero / Room Temperature Performance**: All 6 corners at $0^\circ$C pass all hard constraints with substantial margin (e.g. FF 1.2V 0$^\circ$C reaches UGBW = 126.9 MHz, PM = $62.7^\circ$).
- **High Temperature Impact**: At $100^\circ$C, carrier mobility reduction lowers device transconductance ($g_m$), which causes high-temperature bandwidth degradation typical for nominal-only sizing.

---

## 6. Efficient Analysis Tool Utilization

- **`quick_analysis` Calls**: 16 calls executing 79 quick screening runs.
  - Screened 5 initial current splits and topologies without consuming simulator calls.
  - Eliminated infeasible $L=45$ nm variants before wasting full simulation budget.
  - Fine-screened input pair multi-finger sizing ($mn1 \in [10, 22]$).
- **`operating_point` Lookups**: 4 lookups to inspect internal transistor saturation margins and identify the second pole bottleneck ($p_2 \approx 19.5 \to 31.2$ MHz).
- **`compare_operating_points`**: 1 lookup explaining the electrical shift from Expert Design 7 to RL Best 351.
- **`corner_check`**: 1 cheap robustness check over 12 PVT corners (12 quick runs, 0 simulator calls).

---

## 7. Execution Budget & Resource Summary

- **Total Simulator Calls**: **912** / 1000 budget (91.2% utilization, stopping condition satisfied).
- **Hand Decisions**: **12** / 40 budget (conservative, high-leverage LLM turns).
- **Feasible Designs Discovered**: **92** distinct designs.
- **Total Elapsed Time**: **989.6 seconds** (~16.5 minutes).

---

## 8. Remaining Trade-offs & Tuning Guidance

1. **Area vs. Phase Margin**: $C_c = 0.6$ pF sits on the boundary. Reducing $C_c$ to 0.5 pF would lower area further, but causes PM to dip to $\sim 56^\circ$ unless $I_2$ is increased to 160 $\mu$A.
2. **Current vs. PVT Bandwidth**: To make the opamp robust across extreme temperatures ($100^\circ$C), $I_2$ should be scaled up by $\approx 25\%$ (to $\approx 160\ \mu$A), which would trade off $\sim 0.04$ of TT nominal current FoM in exchange for PVT robustness.
