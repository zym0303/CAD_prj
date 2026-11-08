# Opamp Sizing Explanation - Run `harness_20261106_190920`

## Final Design Summary (Candidate ID 836)

- **Status**: Feasible (Zero constraint violations)
- **Figure of Merit (FoM)**: **+0.7163** (Target: > 0.3 for feasibility)
- **Total Simulator Calls**: 968 (within 1000 budget)
- **Elapsed Time**: 1220.8 s (~20.3 min)
- **Total Feasible Designs Discovered**: 28

### Final Parameters
| Parameter | Description | Value | Unit |
|---|---|---|---|
| `mp1` | Multiplicity of PMOS mirror load stage 1 | 11 | count |
| `wp1` | Channel width of PMOS mirror load stage 1 | 1.00e-6 | m |
| `lp1` | Channel length of PMOS mirror load stage 1 | 9.00e-8 | m |
| `mn1` | Multiplicity of NMOS input differential pair | 12 | count |
| `wn1` | Channel width of NMOS input differential pair | 2.25e-6 | m |
| `ln1` | Channel length of NMOS input differential pair | 9.00e-8 | m |
| `mp3` | Multiplicity of PMOS stage-2 driver | 16 | count |
| `wp3` | Channel width of PMOS stage-2 driver | 1.75e-6 | m |
| `lp3` | Channel length of PMOS stage-2 driver | 9.00e-8 | m |
| `mn3` | Multiplicity of diode-connected bias NMOS | 2 | count |
| `wn3` | Channel width of diode-connected bias NMOS | 1.25e-6 | m |
| `ln3` | Channel length of diode-connected bias NMOS | 9.00e-8 | m |
| `mn4` | Multiplicity of tail current source NMOS | 7 | count |
| `wn4` | Channel width of tail current source NMOS | 1.00e-6 | m |
| `ln4` | Channel length of tail current source NMOS | 9.00e-8 | m |
| `mn5` | Multiplicity of stage-2 current sink NMOS | 7 | count |
| `wn5` | Channel width of stage-2 current sink NMOS | 1.50e-6 | m |
| `ln5` | Channel length of stage-2 current sink NMOS | 9.00e-8 | m |
| `cap` | Miller compensation capacitance ($C_c$) | 5.00e-13 (0.5 pF) | F |
| `res` | Nulling series resistance ($R_c$) | 6900.0 | $\Omega$ |

### Specifications and Margins
| Specification | Target / Constraint | Measured Value | Margin | Status |
|---|---|---|---|---|
| **Gain** | $\ge 200.0$ V/V | 622.5 V/V | **+422.5 V/V** (+211%) | PASS |
| **UGBW** | $\ge 100.0$ MHz | 107.3 MHz | **+7.3 MHz** (+7.3%) | PASS |
| **Phase Margin** | $\ge 60.0^\circ$ | 60.59° | **+0.59°** | PASS |
| **Slew Rate** | $\ge 30.0$ V/$\mu$s | 64.28 V/$\mu$s | **+34.28 V/$\mu$s** (+114%) | PASS |
| **Input Noise** | $\le 0.03$ V RMS | 0.01437 V RMS | **-0.0156 V RMS** (52% margin) | PASS |
| **Die Area** | minimize (ref 2.0e-9 $\text{m}^2$) | 7.111e-10 $\text{m}^2$ | Normalized: -0.475 | OPTIMIZED |
| **Supply Current**| minimize (ref 200.0 $\mu$A) | 225.1 $\mu$A | Normalized: +0.0592 | OPTIMIZED |

---

## The Design Story (Lineage Progression)

1. **ID 1 (Analyst)**: Initial sizing from first-principles hand equations ($I_{\text{tail}}=60\,\mu\text{A}, I_2=90\,\mu\text{A}, C_c=1.5\,\text{pF}, R_c=1\,\text{k}\Omega$); reward = -1.392.
2. **ID 2 (Analyst)**: Re-allocated current budget towards stage 2 ($I_2=120\,\mu\text{A}, I_{\text{tail}}=30\,\mu\text{A}$), reduced $C_c=0.8\,\text{pF}$, wider input pair; reward improved to -0.958.
3. **ID 3 (Sizer)**: Reduced $C_c \to 0.4\,\text{pF}$ and increased $R_c \to 1600\,\Omega$ on base 2 to boost $g_{m1}/C_c$; UGBW increased 28.2 $\to$ 40.25 MHz, SR increased 22.2 $\to$ 29.16 V/$\mu$s; reward = -0.734.
4. **ID 6 (Sizer sweep)**: Swept $C_c \in [0.1..0.6]\,\text{pF}$; $C_c = 0.1\,\text{pF}$ pushed slew rate to 39.71 V/$\mu$s (PASS) and UGBW to 68.96 MHz; reward = -0.513.
5. **ID 16 (Sizer sweep)**: Swept $R_c \in [1.5..6.5]\,\text{k}\Omega$ on base 6; phase lead from LHP zero monotonically boosted phase margin 43.9° $\to$ 49.86°; reward = -0.472.
6. **ID 18 (Sizer)**: Increased $R_c \to 9500\,\Omega$ on base 16, maximizing phase lead without adding capacitive load; PM reached 52.97°; reward = -0.448.
7. **ID 19 (Sizer)**: Lengthened mirror devices $ln3, ln4, ln5 \to 135\,\text{nm}$; increased stage 2 output resistance without loading interstage node 1; gain surged 127.8 $\to$ 174.4 V/V; reward = -0.296.
8. **ID 21 (Sizer)**: Re-balanced stage currents with $mn4=2$ ($I_{\text{tail}}=60\,\mu\text{A}$) and $mp3=8$ ($S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4} = 4$), halving stage 2 input gate capacitance; PM surged to 65.24° (PASS), SR to 31.02 V/$\mu$s (PASS), noise 7.2 mV (PASS); reward = -0.2935.
9. **ID 338 (RL Training Round 1)**: TD3 anchored on Candidate 21 explored local parameter space, finding a 20-dimensional balanced coordinate ($mp1=11, mp3=16, mn3=2, mn4=7, mn5=7, C_c=0.8\,\text{pF}, R_c=7.1\,\text{k}\Omega$) reaching full feasibility with FoM = +0.6594 (0 violations).
10. **ID 805 (Sizer Polish Sweep)**: Swept $C_c \in [0.5..0.9]\,\text{pF}$ on feasible base 338; $C_c=0.5\,\text{pF}$ traded excess PM margin (+8.8°) for a 12% die area reduction, boosting FoM to +0.7115.
11. **ID 836 (RL Warmup Round 2)**: Re-anchored TD3 on Candidate 805; sparse 2-parameter perturbation identified $mn1=12, R_c=6900\,\Omega$, achieving the global optimum FoM = **+0.7163**.

---

## Attribution of Design Decisions

- **From Analytical Equations**:
  - Systematic offset balance condition $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4}$.
  - Initial current partitioning ($I_{\text{tail}}$ vs $I_2$).
  - Identification of $I_2 / (C_c + C_L)$ as the binding falling slew rate limit.
  - Phase lead compensation via $R_c > 1/g_{m6}$ to generate a stabilizing LHP zero.
  - Mirror length lengthening ($ln3=ln4=ln5=135\,\text{nm}$) for stage-2 gain without loading the interstage node.
- **From RL (TD3 Exploration)**:
  - Discovery of the global multi-parameter coordinate shifts that resolved the simultaneous gain (>600 V/V) and bandwidth (>100 MHz) trade-off.
  - Precise fractional aspect ratios between $mn3=2, mn4=7, mn5=7$ with $mn1=12, mp1=11, mp3=16$.
  - Generating the 28-design feasible Pareto front.
- **Failed Predictions & Model Adjustments**:
  - *Prediction*: Lowering $C_c$ alone would fix slew rate. *Reality*: Slew rate was held back by second-stage sink current $I_2 / (C_c + C_L)$, requiring higher $mn5$ drive.
  - *Prediction*: Lengthening $lp1$ to 135 nm while keeping $lp3$ at 90 nm with adjusted multiplicity would boost gain without hurting stage 2. *Reality*: Threshold voltage and $V_{ov}$ mismatch severely degraded systematic balance and collapsed gain (Candidate 23, gain dropped to 40 V/V). Equal lengths on matching pairs must be strictly preserved.

---

## Remaining Trade-offs & Next Steps

1. **For Lower Power / Supply Current**:
   - $I_2$ and $I_{\text{tail}}$ currently provide generous slew rate (64.3 V/$\mu$s vs 30 V/$\mu$s) and gain (622 vs 200).
   - Scaling down $mn4$ and $mn5$ simultaneously by ~10-15% (e.g. via slightly wider $mn3$ or reduced multiplicities) would trim current from 225 $\mu$A to <200 $\mu$A.
2. **For Smaller Die Area**:
   - Device $mp3$ ($16 \times 1.75\,\mu\text{m}$) and $mp1$ ($11 \times 1.0\,\mu\text{m}$) contribute significantly to active silicon area. With gain at 622 V/V, slight reduction in $mp1$ and $mp3$ width would yield smaller active area while keeping gain well above 200 V/V.
