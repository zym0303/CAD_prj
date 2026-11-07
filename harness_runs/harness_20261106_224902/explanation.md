# Opamp Sizing Explanation Report

- **Run ID**: `harness_20261106_224902`
- **Best Candidate ID**: 767
- **FoM (Reward)**: 0.7096
- **Feasible**: True (All hard constraints satisfied)
- **Total Simulator Calls**: 951
- **Elapsed Time**: ~975 s

---

## 1. Final Parameters & Specifications

### Device Sizing & Component Values
| Device / Component | Parameter | Multiplicity (m) | Width (W) | Length (L) | Unit / Value |
|---|---|---|---|---|---|
| Input Diff Pair (mn1, mn2) | mn1, wn1, ln1 | 16 | 1.50 µm | 90 nm | W_eff = 24.0 µm |
| Active Load (mp1, mp2) | mp1, wp1, lp1 | 3 | 2.25 µm | 90 nm | W_eff = 6.75 µm |
| Bias Diode (mn3) | mn3, wn3, ln3 | 1 | 1.00 µm | 90 nm | W_eff = 1.00 µm |
| Tail Current Source (mn4) | mn4, wn4, ln4 | 3 | 0.75 µm | 90 nm | W_eff = 2.25 µm |
| Second Stage CS (mp3) | mp3, wp3, lp3 | 15 | 2.00 µm | 90 nm | W_eff = 30.0 µm |
| Second Stage Sink (mn5) | mn5, wn5, ln5 | 5 | 1.25 µm | 90 nm | W_eff = 6.25 µm |
| Miller Capacitor (Cc) | cap | - | - | - | 500 fF (0.50 pF) |
| Nulling Resistor (Rc) | res | - | - | - | 5600 Ω (5.60 kΩ) |

### Performance Specifications vs Constraints
| Specification | Target | Unit | Final Value | Constraint Type | Normalized Margin | Absolute Margin | Status |
|---|---|---|---|---|---|---|---|
| **Gain** | ≥ 200.0 | V/V | 307.0 | Hard (≥) | +0.211 | +107.0 V/V | **Pass** |
| **Noise** | ≤ 0.03 | V RMS | 0.00815 | Hard (≤) | -0.573 | -0.0219 V RMS | **Pass** |
| **Phase Margin** | ≥ 60.0 | deg | 63.43 | Hard (≥) | +0.0278 | +3.43° | **Pass** |
| **Slew Rate** | ≥ 30.0 | V/µs | 57.48 | Hard (≥) | +0.314 | +27.48 V/µs | **Pass** |
| **Unity-Gain BW** | ≥ 100.0 | MHz | 100.5 | Hard (≥) | +0.00265 | +0.50 MHz | **Pass** |
| **Current** | min (200) | µA | 256.5 | Optimization | +0.124 | +56.5 µA | **Optimized** |
| **Area** | min (2.0) | 10⁻⁹ m² | 0.6086 | Optimization | -0.533 | -1.391 × 10⁻⁹ m² | **Optimized** |

---

## 2. Design Story (Lineage Chain)

1. **Candidate 1 (Analyst, Hand Init)**: Sized initial baseline from first-order equations (I_tail ≈ 60 µA, I_2 ≈ 120 µA, Cc = 1.2 pF, Rc = 800 Ω). *Effect: Gain (623 V/V) passed, but UGBW (30.4 MHz) and PM (28.7°) were severely violated.*
2. **Candidate 2 (Analyst, Hand Sizing)**: Doubled input pair width (wn1=2 µm) and stage 2 PMOS width (wp3=2 µm), dropped Cc to 0.8 pF and raised Rc to 1500 Ω. *Effect: Slew rate met (40.4 V/µs); UGBW improved to 45.4 MHz, PM to 36.6°.*
3. **Candidate 4 (Sizer, Hand Lever)**: Reverted failed ln1 reduction (Candidate 3) and applied second-pole push via increased stage 2 transconductance (mn5: 4→6, mp3: 8→12, res=800 Ω). *Effect: Lifted UGBW to 53.6 MHz and reward to -0.5227.*
4. **Candidate 9 (Sizer, Resistor Sweep)**: Swept Rc from 800 Ω to 4500 Ω to push the zero into the LHP, providing positive phase lead. *Effect: PM achieved feasibility (72.15°) and UGBW rose to 73.73 MHz; reward jumped to -0.1318.*
5. **Candidate 10 (Sizer, Hand Lever)**: Reduced Cc (0.8 pF → 0.6 pF) and widened input pair mn1 (12→16) to spend excess PM margin for higher gm1/Cc. *Effect: UGBW rose to 79.33 MHz, PM remained feasible at 63.21°.*
6. **Candidate 13 (Sizer, Cap Sweep)**: Swept Cc from 700 fF down to 300 fF, finding optimal balance at Cc = 500 fF. *Effect: UGBW reached 82.98 MHz, PM at 58.14°.*
7. **Candidate 15 (Sizer, Second Pole & Resistor Push)**: Increased stage 2 gm6 (mn5: 6→8, mp3: 12→16) maintaining balance ratio = 8, with Rc = 5500 Ω. *Effect: **FEASIBILITY ACHIEVED** (FoM = 0.5994; UGBW = 113.9 MHz, PM = 62.64°, SR = 55.12 V/µs).*
8. **Candidate 16 (Sizer, Phase 2 Optimization)**: Reduced stage 2 current (mn5: 8→7, mp3: 16→14) and raised Rc to 6000 Ω to preserve PM. *Effect: Shaved 29.5 µA current to 293.2 µA, raising FoM to 0.6257.*
9. **Candidate 19 (Sizer, Resistor Sweep Optimization)**: Swept Rc to minimize resistor area, settling at Rc = 5400 Ω. *Effect: Area reduced to 5.98 × 10⁻¹⁰ m², best hand design achieved with FoM = 0.6507.*
10. **Candidate 389 (RL Strategist, TD3 Local Refinement)**: TD3 local refinement anchored on Candidate 19 explored multi-dimensional current rebalancing (mn4=3/wn4=0.75 µm, mn5=5/wn5=1.25 µm, mp1=3/wp1=2.25 µm, mp3=15/wp3=2.0 µm, res=5700 Ω). *Effect: Reduced current from 293.2 µA to 257.3 µA while maintaining UGBW = 102.4 MHz and PM = 62.04°, boosting FoM to 0.7001.*
11. **Candidate 725 (Sizer, Phase 4 Polish)**: Swept Rc around Candidate 389, finding Rc = 5600 Ω reduced area further to 6.152 × 10⁻¹⁰ m² with FoM = 0.7042.
12. **Candidate 767 (RL Strategist, Round 2 Refinement)**: RL round 2 anchored on Candidate 725 trimmed input pair width wn1 from 2.0 µm to 1.5 µm. *Effect: Trimmed area to 6.086 × 10⁻¹⁰ m² and current to 256.5 µA with UGBW = 100.5 MHz and PM = 63.43°, achieving final best FoM = 0.7096.*

---

## 3. Decision Origins & Prediction Failures

- **Decisions from Hand Circuit Equations**:
  - Initial current split and mirror multiplicity derivation (Analyst).
  - Systematic offset zeroing balance condition: $S_{mp3}/S_{mp1} = 2 \cdot S_{mn5}/S_{mn4}$ maintained throughout hand iterations.
  - Identification of CL = 10 pF second-pole bottleneck ($p_2 \approx g_{m6}/C_L$), driving $g_{m6}$ scaling to unblock UGBW.
  - LHP zero positioning with $R_c > 1/g_{m6}$ to generate phase lead, successfully recovering PM without sacrificing bandwidth.
- **Decisions from Reinforcement Learning (TD3)**:
  - Complex multi-parameter re-allocation of stage 1 vs stage 2 currents by independently perturbing unit widths ($w_{n4}, w_{n5}, w_{p1}$) alongside multiplicities ($m_{n4}, m_{n5}, m_{p1}, m_{p3}$), which reduced total current by 36.7 µA beyond what simple grid multipliers could achieve.
  - Fine transistor width trimming ($w_{n1}: 2.0 \to 1.5\,\mu\text{m}$) to reduce input parasitic area while staying precisely atop the 100 MHz UGBW boundary.
- **Prediction Failures & Lessons Learned**:
  - *Candidate 3 failure*: Decreasing $l_{n1}$ to 45 nm was predicted to boost $g_{m1}$ and UGBW, but severely degraded output resistance $r_{o1}$ due to short-channel effects, collapsing low-frequency gain to 121 V/V and reducing UGBW. *Lesson*: $l_{n1} \ge 90\,\text{nm}$ is essential for DC gain.
  - *Candidate 17 failure*: Scaling global mirror width $w_{n3}$ to 1.25 µm reduced both currents by 20%, but simultaneously reduced $g_{m6}$, pulling UGBW below 100 MHz (82.6 MHz). *Lesson*: Multi-branch scaling must explicitly compensate second-stage pole frequency.

---

## 4. Resource Utilization

- **Total Simulator Calls**: 951 / 1000 budget
  - LLM Hand Sizing & Diagnostics: 31 calls
  - RL Exploration (Warmup & TD3 Updates): 920 calls
- **Total Hand Decisions**: 16 / 40 budget
- **Feasible Candidates Discovered**: 67
- **Elapsed Real Time**: 975.0 s (~16.2 min)

---

## 5. Remaining Circuit Trade-Offs

- **To reduce Area further**: The dominant contributors are Miller capacitor $C_c$ (500 fF) and nulling resistor $R_c$ (5600 Ω). Lowering $R_c$ to 5500 Ω dropped UGBW to 99.47 MHz (-0.5%); with a marginal boost in $I_2$ (or slightly larger $w_{p3}$), $R_c$ could be decreased below 5000 Ω, lowering total area.
- **To reduce Current further**: Current is 256.5 µA (target 200 µA). Slew rate is 57.48 V/µs (margin +27.48 V/µs) and noise is 0.00815 V RMS (margin -0.0219 V RMS). Tail current $I_{tail}$ could be scaled down, but would require compensating $g_{m1}$ with higher $m_{n1}$ or lower $C_c$.
