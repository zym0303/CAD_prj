# Opamp Sizing Explanation (Run: harness_20261106_111015)

## 1. Final Sizing Parameters & Performance Specifications

### Best Feasible Design: Candidate 909
- **Figure of Merit (FoM / Reward)**: `0.6938` (Feasible, threshold > 0.3)
- **Feasible**: `True` (0 violated hard constraints)

### Physical Parameters
| Parameter | Description | Value | Unit |
|---|---|---|---|
| `mn1`, `wn1`, `ln1` | NMOS input differential pair | `17`, `2.50 µm`, `90 nm` | count, m, m |
| `mp1`, `wp1`, `lp1` | PMOS active load mirror (stage 1) | `3`, `2.00 µm`, `90 nm` | count, m, m |
| `mn3`, `wn3`, `ln3` | Diode-connected bias reference ($I_{\text{bias}}=30\,\mu\text{A}$) | `3`, `1.00 µm`, `90 nm` | count, m, m |
| `mn4`, `wn4`, `ln4` | NMOS tail current source | `8`, `1.00 µm`, `90 nm` | count, m, m |
| `mp3`, `wp3`, `lp3` | PMOS common-source driver (stage 2) | `9`, `2.00 µm`, `90 nm` | count, m, m |
| `mn5`, `wn5`, `ln5` | NMOS 2nd-stage current sink | `15`, `1.00 µm`, `90 nm` | count, m, m |
| `cap` | Miller compensation capacitor $C_c$ | `500` | fF |
| `res` | Nulling resistor $R_c$ | `6700` | $\Omega$ |

### Performance Specifications vs Hard Constraints
| Specification | Target | Value | Margin / Status | Normalized $z$ |
|---|---|---|---|---|
| **Gain** | $\ge 200.0\,\text{V/V}$ | **$326.7\,\text{V/V}$** | $+63.4\%$ (Passed) | $+0.241$ |
| **Phase Margin (PM)** | $\ge 60.0^\circ$ | **$61.47^\circ$** | $+1.47^\circ$ (Passed) | $+0.012$ |
| **UGBW** | $\ge 100.0\,\text{MHz}$ | **$100.0\,\text{MHz}$** | $+0.0\,\text{MHz}$ (Passed) | $+0.0002$ |
| **Slew Rate (SR)** | $\ge 30.0\,\text{V}/\mu\text{s}$ | **$59.49\,\text{V}/\mu\text{s}$** | $+98.3\%$ (Passed) | $+0.330$ |
| **Noise** | $\le 0.030\,\text{V}_{\text{RMS}}$ | **$0.00724\,\text{V}_{\text{RMS}}$** | $-75.9\%$ (Passed) | $-0.611$ |
| **Current** (Minimize) | $200.0\,\mu\text{A}$ | **$237.5\,\mu\text{A}$** | Soft target | $+0.086$ |
| **Area** (Minimize) | $2.00\times 10^{-9}\,\text{m}^2$ | **$7.037\times 10^{-10}\,\text{m}^2$** | Soft target | $-0.479$ |

---

## 2. The Design Story (Lineage Chain)

- **Candidate 1** (`analyst`): Initial hand-equation sizing with balanced mirror ratios ($S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4} = 4$), $C_c=1.5\,\text{pF}$, $R_c=800\,\Omega$; yielded high gain ($703.6\,\text{V/V}$) but low UGBW ($27.6\,\text{MHz}$) and PM ($37.35^\circ$).
- **Candidate 3** (`sizer`): Lowered $C_c$ from $1.5\,\text{pF} \to 0.8\,\text{pF}$; boosted slew rate from $24.97 \to 36.99\,\text{V}/\mu\text{s}$ (becoming feasible) and UGBW to $39.2\,\text{MHz}$.
- **Candidate 4** (`sizer`): Increased $M_{n1}$ ($10 \to 18$); revealed that UGBW was clamped by the second pole $p_2 = g_{m6}/C_L$ rather than input $g_{m1}$.
- **Candidate 5** (`sizer`): Raised second-stage current and driver size ($M_{n5}: 10 \to 16$, $M_{p3}: 8 \to 13$) while preserving balance; pushed $p_2$ out, raising UGBW to $47.85\,\text{MHz}$ and PM to $37.62^\circ$.
- **Candidate 11** (`sizer`): Swept $R_c$ to $3500\,\Omega$; pushed the transmission zero into the left-half plane for lead compensation, lifting PM into feasibility at $65.58^\circ$.
- **Candidate 15** (`sizer`): Swept $C_c$ down to $600\,\text{fF}$; lifted UGBW to $62.24\,\text{MHz}$ with PM at $57.47^\circ$.
- **Candidate 17** (`sizer`): Increased $M_{n1}$ ($10 \to 16$) and $R_c$ ($3500 \to 4500\,\Omega$); lifted UGBW to $68.79\,\text{MHz}$ and PM to $62.26^\circ$.
- **Candidate 18** (`sizer`): Increased tail current $M_{n4}$ ($5 \to 7$) with balance adjustment $M_{p3} = 9$; lifted UGBW to $77.57\,\text{MHz}$ with PM at $61.14^\circ$.
- **Candidate 19** (`sizer`): Lowered $C_c$ ($600 \to 400\,\text{fF}$) and raised $R_c$ ($4500 \to 5500\,\Omega$); brought UGBW to $93.17\,\text{MHz}$ and PM to $55.23^\circ$.
- **Candidate 20** (`sizer`): Widened input pair $W_{n1}$ ($2.0 \to 2.5\,\mu\text{m}$) and increased $R_c$ ($5500 \to 6500\,\Omega$); pushed UGBW across $100\,\text{MHz}$ ($100.9\,\text{MHz}$) with PM at $56.68^\circ$.
- **Candidate 26** (`sizer`): Set $C_c = 500\,\text{fF}$ and $R_c = 7500\,\Omega$; achieved first full feasibility ($\text{FoM} = 0.6312$, $\text{UGBW} = 107.9\,\text{MHz}$, $\text{PM} = 62.27^\circ$).
- **Candidate 31** (`sizer`): Swept $R_c$ down to $7000\,\Omega$; reduced resistor area, raising FoM to $0.6502$.
- **Candidate 32** (`sizer`): Reduced second-stage current sink $M_{n5}$ ($16 \to 15$); saved $4.5\,\mu\text{A}$ of current while keeping UGBW at $101.2\,\text{MHz}$, reaching hand-sized peak $\text{FoM} = 0.6592$.
- **Candidate 536** (`sizer`): Polished $R_c$ to $6900\,\Omega$; brought FoM to $0.6631$ with tight margins ($\text{UGBW} = 100.2\,\text{MHz}$, $\text{PM} = 61.95^\circ$).
- **Candidate 596** (`rl`): TD3 reinforcement learning optimized across the high-dimensional parameter space ($M_{p1}: 2 \to 3$, $M_{n1}: 16 \to 17$, $M_{n4}: 7 \to 8$, $R_c: 7000\,\Omega$); reduced current from $249.8\,\mu\text{A}$ to $237.5\,\mu\text{A}$ and noise by $>50\%$ to $7.24\,\text{mV}$, improving FoM to $0.6822$.
- **Candidate 909** (`sizer`): Final polish sweep on candidate 596 fine-tuned $R_c$ to $6700\,\Omega$; reduced resistor area to $7.037\times 10^{-10}\,\text{m}^2$ while exactly meeting $\text{UGBW} = 100.0\,\text{MHz}$ and $\text{PM} = 61.47^\circ$, establishing the global best $\text{FoM} = 0.6938$.

---

## 3. Decision Origins & Prediction Verification

- **Decisions from Hand Equations**:
  - Mirror balancing relation $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4}$ was essential to keep systematic offset low and maintain high first-stage gain.
  - Pole splitting and zero cancellation: lowering $C_c$ to trade slew rate and UGBW, combined with increasing $R_c$ to push the zero into the left-half plane for phase lead.
  - Identifying the second-pole clamp ($p_2 = g_{m6}/C_L$): recognized that input pair width increases saturated without stage-2 $g_{m6}$ scaling.
- **Decisions from Reinforcement Learning**:
  - Re-optimizing stage 1 load mirror multiplicity $M_{p1}$ ($2 \to 3$) together with input pair $M_{n1}$ ($16 \to 17$) and tail $M_{n4}$ ($7 \to 8$). This simultaneous 4-parameter co-tuning trimmed total current by $>12\,\mu\text{A}$ and noise by $>50\%$ without degrading stability.
  - Generating 62 feasible designs to define the Pareto trade-off boundary.
- **Failed Predictions & Circuit Lessons**:
  - *Candidate 2*: Shortening $L_{n1}$ from $90\,\text{nm} \to 45\,\text{nm}$ collapsed gain from $703\,\text{V/V}$ down to $109\,\text{V/V}$ due to severe channel-length modulation.
  - *Candidate 4*: Increasing $M_{n1}$ by $+80\%$ yielded only $+1.4\%$ UGBW because the second pole $p_2 = g_{m6}/C_L$ at $C_L=10\,\text{pF}$ was governing the loop bandwidth.
  - *Candidate 27*: Increasing $M_{n3}$ ($3 \to 4$) reduced current to $200\,\mu\text{A}$ as predicted, but the resulting drop in branch transconductances pulled UGBW below $100\,\text{MHz}$.

---

## 4. Execution Statistics

- **Total Simulator Calls**: 911
- **Hand Decisions Used**: 20 (out of 40 budget)
- **RL Exploration Simulator Calls**: 870 (150 warmup + 720 TD3 training steps)
- **Feasible Designs Discovered**: 62
- **Elapsed Real Time**: 1467.8 seconds (~24.5 minutes)

---

## 5. Remaining Trade-offs

- **For Lower Area**: Resistor $R_c$ ($6.7\,\text{k}\Omega$) and capacitor $C_c$ ($500\,\text{fF}$) account for $>85\%$ of the total layout footprint ($7.037\times 10^{-10}\,\text{m}^2$). If the UGBW constraint could be relaxed below $100\,\text{MHz}$, $R_c$ and $C_c$ could both be reduced further.
- **For Lower Current**: Current is dominated by $I_2$ in the second stage ($M_{n5}=15$, $\sim 150\,\mu\text{A}$). Reducing $I_2$ pulls total current toward the $200\,\mu\text{A}$ target, but requires either a larger load compensation capacitor or higher input transconductance to prevent phase margin degradation.
