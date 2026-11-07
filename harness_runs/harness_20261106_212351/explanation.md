# Opamp Sizing Review & Explanation

**Run ID**: harness_20261106_212351  
**Total Simulator Calls**: 900  
**Elapsed Time**: 998.3 s  
**Best Candidate ID**: 895  
**Final Figure of Merit (FoM)**: 0.6967  
**Feasible**: True (All 5 hard constraints satisfied)

---

## 1. Final Parameters & Specifications

### Device Parameters
| Parameter | Value | Units | Description |
|---|---|---|---|
| `mn1` / `wn1` / `ln1` | 6 / 2.50 µm / 135 nm | count / m / m | NMOS differential input pair |
| `mp1` / `wp1` / `lp1` | 6 / 1.75 µm / 90 nm | count / m / m | PMOS active mirror load |
| `mn3` / `wn3` / `ln3` | 2 / 1.50 µm / 90 nm | count / m / m | Diode-connected reference bias (Ibias = 30 µA) |
| `mn4` / `wn4` / `ln4` | 10 / 1.00 µm / 90 nm | count / m / m | Stage 1 tail current mirror sink |
| `mp3` / `wp3` / `lp3` | 9 / 1.75 µm / 90 nm | count / m / m | Stage 2 PMOS common-source driver |
| `mn5` / `wn5` / `ln5` | 13 / 0.75 µm / 90 nm | count / m / m | Stage 2 NMOS current sink mirror |
| `cap` ($C_c$) | 0.50 pF (5.0e-13 F) | F | Miller compensation capacitor |
| `res` ($R_c$) | 9000.0 Ω (9.0 kΩ) | Ω | Lead-compensation nulling resistor |

### Performance Specifications & Margins
| Specification | Measured Value | Required Target | Constraint Type | Margin (Normalized) | Status |
|---|---|---|---|---|---|
| **DC Gain** | 252.5 V/V | ≥ 200.0 V/V | Hard Constraint | +0.116 (+52.5 V/V) | **Pass** |
| **Phase Margin (PM)** | 65.98° | ≥ 60.0° | Hard Constraint | +0.048 (+5.98°) | **Pass** |
| **Unity Gain Bandwidth (UGBW)** | 100.1 MHz | ≥ 100.0 MHz | Hard Constraint | +0.0004 (+0.1 MHz) | **Pass** |
| **Slew Rate (SR)** | 64.68 V/µs | ≥ 30.0 V/µs | Hard Constraint | +0.366 (+34.68 V/µs) | **Pass** |
| **Input-Referred Noise** | 0.00659 V RMS | ≤ 0.0300 V RMS | Hard Constraint | -0.640 (-0.0234 V RMS) | **Pass** |
| **Total Current** | 203.1 µA | 200.0 µA (target) | Soft Optimization Target | +0.0078 (+3.1 µA) | **Optimized** |
| **Layout Area** | 0.848 nm² | 2.00 nm² (target) | Soft Optimization Target | -0.404 (-1.152 nm²) | **Optimized** |

$\text{FoM} = 0.3 - z_{\text{area}} - z_{\text{current}} = 0.3 - (-0.404) - (0.0078) = 0.6967$.

---

## 2. The Design Story (Lineage Chain)

1. **Candidate 1 (Analyst)**: Sized initial hand design from first-order equations ($I_{\text{tail}}=60\,\mu\text{A}, I_2=90\,\mu\text{A}, C_c=1.5\,\text{pF}, R_c=800\,\Omega$). Result: Gain=599.7, PM=23.2°, UGBW=24.5 MHz; suffered from low second pole $p_2 \approx g_{m6}/C_L$.
2. **Candidate 2 (Analyst)**: Boosted second-stage transconductance $g_{m6}$ ($W_{mp3}=20\,\mu\text{m}, I_2=100\,\mu\text{A}$) and input pair size while enforcing systematic balance $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4} = 5.0$. Result: Gain=732.3, PM improved to 42.5°, UGBW to 29.1 MHz.
3. **Candidate 4 (Sizer - Sweep)**: Decreased $C_c$ from $1.2\,\text{pF}$ to $0.5\,\text{pF}$ via parametric sweep to boost $g_{m1}/C_c$ and slew rate. Result: SR solved ($43.64\,\text{V}/\mu\text{s} > 30$), UGBW climbed to 46.3 MHz, area dropped to $0.296\,\text{nm}^2$.
4. **Candidates 15 & 20 (Sizer - Sweep)**: Swept nulling resistor $R_c$ from $1.2\,\text{k}\Omega$ to $9.6\,\text{k}\Omega$ to push the transmission zero into the left half-plane ($R_c > 1/g_{m6}$). Result: PM rose monotonically from 28.2° to 65.6° (fully feasible), leaving only UGBW binding.
5. **Candidate 22 (Sizer)**: Identified that $g_{m1}/C_c$ had collided with the second-pole ceiling $g_{m6}/C_L$. Increased $m_{n5}$ ($10 \to 12$) and $m_{p3}$ ($10 \to 12$) to push $p_2$ out by $44\%$, maintaining balance at 6.0. Result: UGBW broke through the ceiling to 78.84 MHz.
6. **Candidate 25 (Sizer)**: Reduced $m_{n3}$ ($3 \to 2$) as a global current lever to scale all currents by $1.5\times$ ($I_{\text{tail}} = 60\,\mu\text{A}, I_2 = 180\,\mu\text{A}$). Result: UGBW reached 132.1 MHz, PM reached 59.56° (within 0.44° of feasibility).
7. **Candidates 75 & 540 (RL Warmup)**: Local exploration around Candidate 25 discovered fully feasible solutions ($C_c=0.5\,\text{pF}, R_c=9.6\,\text{k}\Omega, \text{FoM}=0.5544 \to 0.6365$).
8. **Candidate 810 (RL TD3 Training)**: TD3 agent refined the transistor dimensions globally ($m_{n1}=6, l_{n1}=135\,\text{nm}, m_{p1}=6, m_{p3}=9, m_{n4}=10, m_{n5}=13$), reducing current from $256\,\mu\text{A}$ down to $203.1\,\mu\text{A}$ while preserving PM (66.05°) and UGBW (102.4 MHz), boosting FoM to 0.6862.
9. **Candidate 895 (Sizer - Polish Sweep)**: Fine-tuned $R_c$ downwards from $9300\,\Omega$ to $9000\,\Omega$, trimming excess layout area from $0.870\,\text{nm}^2$ to $0.848\,\text{nm}^2$ with PM remaining robust at 65.98° and UGBW at 100.1 MHz. Result: Final optimal $\text{FoM} = 0.6967$.

---

## 3. Decisions from Equations vs. RL vs. Failed Hypotheses

* **From Equations**:
  * Systematic offset balance condition $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4}$ preserved across all manual iterations.
  * LHP zero generation via $R_c > 1/g_{m6}$ to recover phase margin from 28° to 65.6°.
  * Second-pole ceiling diagnosis ($g_{m1}/C_c \approx g_{m6}/C_L$) resolving the UGBW bottleneck by scaling $I_2$ and $m_{p3}$.
  * Global current scaling via reference diode $m_{n3}$.
* **From RL (TD3 & Warmup)**:
  * Non-intuitive multi-variable rebalancing: reducing $m_{n1}$ count while increasing channel length $l_{n1}$ to $135\,\text{nm}$ to slash device current to $203.1\,\mu\text{A}$ while simultaneously meeting gain ($252.5\,\text{V}/\text{V}$) and noise ($0.0066\,\text{V}$).
  * Generating 48 distinct feasible candidate points for the design Pareto front.
* **Failed Predictions & Circuit Lessons**:
  * *Lesson 1 (Sim 3)*: Halving $l_{n1}$ from 90 nm to 45 nm caused severe channel length modulation, collapsing DC gain ($732 \to 121.6$) and degrading UGBW due to stage 1 rout drop. Minimum channel length for the input pair must remain $\ge 90\,\text{nm}$.
  * *Lesson 2 (Sim 24)*: Doubling input pair width $m_{n1}$ ($12 \to 24$) at low current failed to increase $g_{m1}$ because devices entered weak inversion where $g_m$ depends on current, not width, while gate capacitance doubled. Current scaling was required.

---

## 4. Remaining Trade-offs
* **For Lower Area**: $R_c$ ($9\,\text{k}\Omega$) and $C_c$ ($0.5\,\text{pF}$) contribute the vast majority of layout area. Shifting to an active nulling transistor or lowering $C_L$ would allow reducing $R_c$ and $C_c$, dropping area below $0.5\,\text{nm}^2$.
* **For Lower Current**: Slew rate ($64.7\,\text{V}/\mu\text{s}$) and phase margin ($66.0^\circ$) have ample headroom above their constraints ($30\,\text{V}/\mu\text{s}$ and $60^\circ$). $I_{\text{tail}}$ and $I_2$ can be throttled by an additional 15–20% if UGBW target is relaxed slightly.
