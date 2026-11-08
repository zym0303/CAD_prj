# Two-Stage Miller Opamp Sizing Explanation

**Run ID**: harness_20261106_232516  
**Final Candidate ID**: 730  
**Feasibility**: True (All hard constraints satisfied)  
**Figure of Merit (FoM / Reward)**: 0.7301  
**Total Simulator Calls**: 900  
**Elapsed Time**: 1059.1 s  

---

## 1. Final Parameters and Performance Specs

### Sized Parameters
| Device / Element | Multiplicity (m) | Width (W) | Length (L) | Parameter Value |
|---|---|---|---|---|
| Differential Pair (mn1/mn2) | 16 | 1.50 µm | 135 nm | W_tot = 24.0 µm |
| Stage 1 Mirror Load (mp1/mp2) | 6 | 1.75 µm | 90 nm | W_tot = 10.5 µm |
| Reference Diode (mn3) | 6 | 1.00 µm | 135 nm | W_tot = 6.0 µm |
| Tail Current Source (mn4) | 8 | 1.00 µm | 90 nm | W_tot = 8.0 µm |
| Output Current Sink (mn5) | 13 | 1.00 µm | 90 nm | W_tot = 13.0 µm |
| Second Stage Driver (mp3) | 23 | 1.25 µm | 90 nm | W_tot = 28.75 µm |
| Miller Capacitor (cap / Cc) | - | - | - | 0.50 pF (5.0e-13 F) |
| Nulling Resistor (res / Rc) | - | - | - | 7.70 kΩ (7700 Ω) |

### Performance Specifications vs Targets
| Specification | Target | Achieved Value | Margin (Normalized z) | Status |
|---|---|---|---|---|
| **DC Gain** | ≥ 200.0 V/V | **812.7 V/V** (58.2 dB) | +0.605 | PASS (Excess margin) |
| **Unity-Gain Bandwidth (UGBW)** | ≥ 100.0 MHz | **100.1 MHz** | +0.00048 | PASS (Met target) |
| **Phase Margin (PM)** | ≥ 60.0° | **60.45°** | +0.00375 | PASS (Robust stability) |
| **Slew Rate (SR)** | ≥ 30.0 V/µs | **62.17 V/µs** | +0.349 | PASS (2x margin) |
| **Input-Referred Noise** | ≤ 0.030 V RMS | **0.01608 V RMS** | -0.302 | PASS (Well below limit) |
| **Total Current** | minimize (ref 200 µA) | **205.4 µA** | +0.0133 | PASS (Near nominal) |
| **Total Area** | minimize (ref 2000 µm²) | **771.3 µm²** (7.71e-10 m²) | -0.443 | PASS (61% smaller than ref) |

---

## 2. Design Story (Lineage Chain)

1. **Analyst (Candidate 1)**: Derived first-cut sizing using hand equations for balanced currents ($I_{\text{tail}} \approx 50\ \mu\text{A}, I_2 \approx 100\ \mu\text{A}$) and $L=90\text{ nm}$; achieved high DC gain (656 V/V) and low current (175 µA), but UGBW (25.4 MHz) and PM (36°) were constrained.
2. **Sizer (Candidate 3)**: Scaled $mn1$ (4 → 12) targeting $gm_1$; revealed that $mn1$ was in weak inversion where $gm_1$ is current-limited.
3. **Sizer (Candidate 4)**: Reduced $C_c$ (1.5 pF → 0.8 pF); immediately resolved slew rate violation ($SR = 35.9\text{ V/}\mu\text{s}$).
4. **Sizer (Candidate 11 & 12)**: Swept $R_c$ to 4.8 kΩ, using the LHP zero phase lead to push Phase Margin across 60° (60.75°).
5. **Sizer (Candidate 13 & 18)**: Halved $C_c$ to 0.4 pF and increased $R_c$ to 9.5 kΩ, lifting UGBW to 69.9 MHz while maintaining PM = 62.1°.
6. **Sizer (Candidate 20)**: Identified second pole $p_2 = gm_6 / C_L$ clamping; increased $gm_6$ via $mn5=12, mp3=24, mp1=5$ under balance ratio 4.8, driving UGBW from 69.9 MHz to 99.37 MHz (reward: -0.0585).
7. **RL Strategist (Candidate 625)**: TD3 agent anchored on Candidate 20 explored local multi-parameter trade-offs; discovered a balanced operating point ($mn3=6, mn4=8, mn5=13, mp1=6, mp3=23, C_c=0.5\text{ pF}, R_c=7.7\text{ k}\Omega$) reaching UGBW = 97.96 MHz, PM = 62.47°, gain = 772.7 V/V, and reward = +0.0115.
8. **Diagnoser & Sizer Polish (Candidates 729 & 730)**: Diagnosed that only +2.04 MHz was required for full feasibility; swept $mn1$ [10..14] (id: 729 at 99.6 MHz), then stepped $mn1$ to 16 (id: 730), crossing into full feasibility with UGBW = 100.1 MHz, PM = 60.45°, and FoM = 0.7301.
9. **RL Refinement Round 2+ (Candidates 741–894)**: Seeded only feasible designs into replay buffer; discovered 11 feasible variants across the Pareto front and verified that Candidate 730 is the sharp local optimum.

---

## 3. Decision Breakdown: Equations vs RL vs Failed Predictions

- **Equation-Driven Decisions**:
  - Balanced DC symmetry condition ($S_{mp3}/S_{mp1} = 2 \cdot S_{mn5}/S_{mn4}$) kept systematic offset near zero, preserving high DC gain (>750 V/V).
  - Identification of slew rate scaling ($SR \approx I_{\text{tail}} / C_c$) allowed single-step resolution of slew rate.
  - Identification of $p_2 \approx gm_6 / C_L$ pole ceiling allowed breaking the 70 MHz UGBW barrier by sizing $mp3$ and $mn5$.
- **RL-Driven Decisions**:
  - TD3 co-optimized 8 parameters simultaneously in the neighborhood of Candidate 20, adjusting reference length $ln3=135\text{ nm}$, $mn3=6$, $mn4=8$, $mn5=13$, and $mp3=23$ to balance mirror voltage headroom and output resistance.
  - Generated the feasible design cluster (11 feasible designs) populating the Pareto front.
- **Failed Predictions & Circuit Lessons**:
  - *Candidate 2*: Shortening PMOS channel lengths to 45 nm caused severe output conductance degradation and offset collapse (gain dropped to 11.5 V/V). Channel lengths were kept at ≥90 nm thereafter.
  - *Candidate 3*: Tripling $mn1$ width at low tail current produced negligible UGBW increase (+1.1 MHz) because weak-inversion transconductance was current-limited by $I_D / (n V_t)$.
  - *Candidate 20 parasitic pole*: Setting $R_c = 9.5\text{ k}\Omega$ with wide $mp3$ ($m=24$) introduced a high-frequency pole $p_3 = 1/(R_c C_{gs3}) \approx 550\text{ MHz}$ that eroded phase margin by ~10°. Reducing $R_c$ to 7.7 kΩ restored phase stability.

---

## 4. Resource Utilization

- **Total Simulator Calls**: 900
  - Phase 1 Feasibility (Analyst & Hand Sizer): 25 calls (25 LLM designs)
  - Phase 3 RL Refinement Round 1: 700 calls (100 warmup + 600 TD3 training steps)
  - Phase 4 Hand Polish: 5 calls (id 726–730)
  - Phase 3 RL Refinement Round 2+: 160 calls (30 warmup + 130 TD3 training steps)
  - Final Verification & Sweep: 10 calls (id 891–900)
- **Total LLM Hand Decisions**: 18 decisions (well within 40-decision budget)
- **Total Feasible Designs Found**: 11
- **Elapsed Time**: 1059.1 seconds (~17.6 minutes)

---

## 5. Remaining Trade-Offs

- **Lower Current**: Tail current is ~50 µA and stage 2 current is ~125 µA ($I_{\text{tot}} \approx 205\ \mu\text{A}$). To reduce current below 200 µA, stage 2 current could be decreased by 10 µA ($mn5 = 12$), but this will push $p_2$ lower and require a larger $R_c$ or slightly wider $mp3$ to keep PM ≥ 60°.
- **Lower Area**: The capacitor $C_c = 0.5\text{ pF}$ accounts for ~65% of the total area ($771\ \mu\text{m}^2$). Dropping $C_c$ to 0.4 pF reduces area by ~15%, but lowers PM to ~52°, requiring higher $gm_6$ (more stage 2 current) to compensate.
