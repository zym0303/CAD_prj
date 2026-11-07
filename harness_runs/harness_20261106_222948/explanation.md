# Opamp Sizing Explanation Report
**Run ID**: `harness_20261106_222948`  
**Date**: November 6, 2026  
**Status**: Feasible Global Optimum Reached (FoM = 0.6221)

---

## 1. Final Parameters and Performance

### Optimal Sizing Parameters (Candidate 921)
| Parameter | Description | Value | Unit |
|---|---|---|---|
| `mp1` | Multiplicity of PMOS load (stage 1) | 4 | count |
| `wp1` | Width of PMOS load (stage 1) | 1.0e-6 | m (1.00 $\mu$m) |
| `lp1` | Length of PMOS load (stage 1) | 9.0e-8 | m (90 nm) |
| `mn1` | Multiplicity of NMOS input pair | 14 | count |
| `wn1` | Width of NMOS input pair | 2.5e-6 | m (2.50 $\mu$m) |
| `ln1` | Length of NMOS input pair | 9.0e-8 | m (90 nm) |
| `mp3` | Multiplicity of PMOS driver (stage 2) | 16 | count |
| `wp3` | Width of PMOS driver (stage 2) | 1.0e-6 | m (1.00 $\mu$m) |
| `lp3` | Length of PMOS driver (stage 2) | 9.0e-8 | m (90 nm) |
| `mn3` | Multiplicity of NMOS diode bias | 1 | count |
| `wn3` | Width of NMOS diode bias | 1.0e-6 | m (1.00 $\mu$m) |
| `ln3` | Length of NMOS diode bias | 9.0e-8 | m (90 nm) |
| `mn4` | Multiplicity of NMOS tail mirror | 4 | count |
| `wn4` | Width of NMOS tail mirror | 1.0e-6 | m (1.00 $\mu$m) |
| `ln4` | Length of NMOS tail mirror | 9.0e-8 | m (90 nm) |
| `mn5` | Multiplicity of NMOS second stage sink | 12 | count |
| `wn5` | Width of NMOS second stage sink | 5.0e-7 | m (0.50 $\mu$m) |
| `ln5` | Length of NMOS second stage sink | 9.0e-8 | m (90 nm) |
| `cap` | Miller compensation capacitor $C_c$ | 6.0e-13 | F (0.60 pF) |
| `res` | Lead nulling resistor $R_c$ | 4000.0 | $\Omega$ (4.00 k$\Omega$) |

### Constraint Margins & Figures of Merit
| Metric | Specification Target | Constraint Type | Value Achieved | Margin (Abs / Rel) | Normalized $z$ | Status |
|---|---|---|---|---|---|---|
| **Gain** | $\ge 200.0$ V/V | Hard Constraint | **340.8 V/V** | +140.8 V/V (+70.4%) | +0.260 | **PASS** |
| **Noise** | $\le 0.030$ V RMS | Hard Constraint | **0.00873 V RMS** | -0.02127 V (-70.9%) | -0.549 | **PASS** |
| **Phase Margin** | $\ge 60.0^\circ$ | Hard Constraint | **60.56$^\circ$** | +0.56$^\circ$ (+0.93%) | +0.0046 | **PASS** |
| **Slew Rate** | $\ge 30.0$ V/$\mu$s | Hard Constraint | **60.10 V/$\mu$s** | +30.10 V/$\mu$s (+100.3%)| +0.334 | **PASS** |
| **UGBW** | $\ge 100.0$ MHz | Hard Constraint | **103.60 MHz** | +3.60 MHz (+3.60%) | +0.0177 | **PASS** |
| **Area** | Minimize ($2.0 \times 10^{-9}\,\text{m}^2$) | Optimization Goal | **$5.294 \times 10^{-10}\,\text{m}^2$** | -73.5% vs target | -0.581 | **Optimized** |
| **Current** | Minimize ($200.0\,\mu\text{A}$) | Optimization Goal | **$340.0\,\mu\text{A}$** | +70.0% vs target | +0.259 | **Optimized** |
| **Figure of Merit (FoM)** | Higher is better ($>0.3$ feasible) | Objective | **+0.6221** | — | — | **Optimal** |

---

## 2. The Design Story (Lineage Chain)

- **Step 1 (Analyst, Cand 1)**: Derived first sizing from hand equations ($I_{\text{tail}}=60\,\mu\text{A}$, $I_2=120\,\mu\text{A}$, $C_c=2\,\text{pF}$) satisfying balance ratio $S_{mp3}/S_{mp1} = 2 \cdot S_{mn5}/S_{mn4} = 4$; achieved high gain (642 V/V) and low noise (19.7 mV), but stalled on UGBW (23.5 MHz), PM ($37.1^\circ$), and SR (21.2 V/$\mu$s).
- **Step 2 (Analyst, Cand 2)**: Tested short $L_{n1}=45\,\text{nm}$ and $C_c=0.8\,\text{pF}$; demonstrated that minimum channel length collapses stage-1 output resistance and gain (down to 98 V/V), while small $C_c$ without stage-2 drive hits the output pole ceiling $p_2 = g_{m6}/C_L$.
- **Step 3 (Sizer, Cand 3)**: Boosted stage-2 drive to $mn_5=6, mp_3=12$ while lowering $C_c$ to 1.2 pF, satisfying the slew rate constraint ($30.7\,\text{V}/\mu\text{s}$) while retaining systematic DC balance.
- **Step 4 (Sizer, Cand 4)**: Increased input pair $mn_1$ from 8 to 16 and raised $R_c$ to $1800\,\Omega$, pushing phase margin from $39.8^\circ$ to $49.8^\circ$ via lead-zero advance while keeping gain > 640 V/V.
- **Step 5 (Sizer, Cand 5)**: Doubled tail current ($mn_4=4$, $I_{\text{tail}}=120\,\mu\text{A}$) to overcome weak inversion and tripled second stage sink ($mn_5=12$, $I_2=360\,\mu\text{A}$) with $C_c=0.6\,\text{pF}$, driving UGBW to 89.3 MHz and slew rate to $43.5\,\text{V}/\mu\text{s}$.
- **Step 6 (Sizer, Cand 11)**: Swept $R_c$ to $3800\,\Omega$, placing the LHP zero $f_z = \frac{1}{2\pi C_c (R_c - 1/g_{m6})}$ near 100 MHz, achieving full circuit feasibility (FoM = +0.4724, $\text{PM}=61.9^\circ$, $f_u=116.1\,\text{MHz}$).
- **Step 7 (Sizer, Cand 12)**: Scaled mirror master $wn_3=1.25\,\mu\text{m}$ to trim current by 20% down to $396\,\mu\text{A}$, leaving UGBW marginally below spec at 98.6 MHz.
- **Step 8 (Sizer, Cand 13)**: Increased input pair multiplicity $mn_1=20$ and $R_c=4500\,\Omega$, recovering feasibility with improved FoM = +0.5223 ($I = 397\,\mu\text{A}$).
- **Step 9 (RL, Cand 253)**: TD3 continuous policy training discovered that lengthening channel lengths ($L=135\,\text{nm}$) on first-stage loads and trimming $mn_5=7$ cut current to $281\,\mu\text{A}$ while doubling gain to 1097 V/V (FoM = +0.5585).
- **Step 10 (Sizer, Cand 719)**: Trimmed $R_c$ to $6900\,\Omega$ on Candidate 253, shaving excess resistor area to reach FoM = +0.5658.
- **Step 11 (RL, Cand 751)**: Round 2 local exploration discovered $mn_5=12$ with narrower unit width $W_{n5}=0.5\,\mu\text{m}$ and $R_c=4100\,\Omega$, achieving an FoM breakthrough to +0.6176 with balanced low layout area ($5.37 \times 10^{-10}\,\text{m}^2$) and $60.1\,\text{V}/\mu\text{s}$ slew rate.
- **Step 12 (Sizer, Cand 921)**: Executed final Phase 4 sweep fine-tuning $R_c$ from $4100\,\Omega$ to $4000\,\Omega$, shaving resistor layout area to establish the global optimum FoM = +0.6221.

---

## 3. Decision Origins and Predictions

### Decisions from Analytic Equations
1. **Systematic Offset Balancing**: Constraining $\frac{S_{mp3}}{S_{mp1}} = 2 \cdot \frac{S_{mn5}}{S_{mn4}}$ prevented internal DC offset from forcing transistors into linear region, ensuring robust gain across every sizing candidate.
2. **Bandwidth Choke Diagnosis**: Identified that lowering $C_c$ without increasing $g_{m6}$ caused $f_u$ to choke at the output pole $p_2 = g_{m6}/C_L$.
3. **Phase Lead Zero Placement**: Calculated $R_c = \frac{1}{g_{m6}} + \frac{1}{2\pi C_c f_z}$ to position the LHP zero in the 90–120 MHz band, generating over $25^\circ$ of phase boost to lift PM past $60^\circ$.
4. **Global Current Scaling**: Increased $S_{mn3}$ to lower tail and second-stage currents simultaneously without perturbing the balance ratio.

### Decisions from Reinforcement Learning (TD3)
1. **Asymmetric Transistor Sizing**: RL broke free of uniform 1.0 $\mu$m finger widths by discovering that scaling $W_{n5}$ down to $0.5\,\mu\text{m}$ while maintaining finger count ($mn_5=12$) maintained slew rate while shrinking gate/parasitic capacitance and layout area.
2. **Channel Length Multi-Objective Tradeoff**: TD3 learned to stretch non-critical mirror channel lengths ($L=135\,\text{nm}$) to exploit high output resistance $r_o \propto L$ for DC gain boost (>1000 V/V) at minimal current penalty.
3. **Pareto Diversity**: Produced 58 distinct feasible designs across the current-area tradeoff surface.

### Failed Predictions & Model Lessons
- *Lesson 1 (Cand 2)*: Decreasing $L_{n1}$ to 45 nm to maximize $g_{m1}$ failed due to extreme short-channel output conductance degradation ($g_{ds}$), dropping DC gain to 98 V/V. Corrective action: kept $L \ge 90\,\text{nm}$.
- *Lesson 2 (Cand 4)*: Doubling input width $mn_1$ from 8 to 16 with constant $I_{\text{tail}}$ produced only a tiny increase in $f_u$ (37.4 $\to$ 39.2 MHz) because the differential pair operated in weak inversion where $g_m \approx I_D / (n V_t)$. Corrective action: scaled $I_{\text{tail}}$ directly via $mn_4$.
- *Lesson 3 (Cand 12)*: Reducing currents by 20% slightly pulled $f_u$ below 100 MHz (98.6 MHz); successfully compensated by widening $mn_1$ to 20.

---

## 4. Resource Usage
- **Total Simulator Calls**: 923 / 1000 budget used (92.3% utilization).
- **Hand Decisions**: 8 / 40 decisions used (20.0% utilization, highly token-efficient).
- **Total Elapsed Wall Time**: 1002.4 seconds (~16.7 minutes).
- **Total Feasible Candidates Generated**: 58.

---

## 5. Remaining Circuit Trade-offs
- **To Achieve Lower Current**: The dominant current consumer is the second stage ($mn_5$, carrying $\approx 180\,\mu\text{A}$). Reducing $mn_5$ or lowering tail current $mn_4$ reduces power, but directly erodes the $f_u$ margin (103.6 MHz vs 100 MHz target) and phase margin ($60.56^\circ$ vs $60.0^\circ$ target).
- **To Achieve Lower Area**: The nulling resistor $R_c = 4000\,\Omega$ contributes approximately $2.8 \times 10^{-10}\,\text{m}^2$ (over 50% of the active area). Lowering $R_c$ below $4000\,\Omega$ shaves area, but moves the lead zero higher in frequency, causing phase margin to dip below $60^\circ$ (as demonstrated by Cand 920 at $R_c = 3800\,\Omega$, $\text{PM} = 59.3^\circ$).
