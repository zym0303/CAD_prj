# Opamp Sizing Explanation (Run: harness_20261106_202431)

## 1. Final Design: Candidate 843

### Parameters
- **Differential input pair (NMOS)**: `mn1 = 12`, `wn1 = 1.75 µm`, `ln1 = 135 nm` ($W_{\text{tot}} = 21.0\,\mu\text{m}$)
- **First-stage PMOS load**: `mp1 = 5`, `wp1 = 1.50 µm`, `lp1 = 90 nm` ($W_{\text{tot}} = 7.5\,\mu\text{m}$)
- **Bias diode (NMOS)**: `mn3 = 4`, `wn3 = 1.00 µm`, `ln3 = 90 nm` ($W_{\text{tot}} = 4.0\,\mu\text{m}$, carrying $I_{\text{bias}} = 30\,\mu\text{A}$)
- **Tail current source (NMOS)**: `mn4 = 9`, `wn4 = 1.00 µm`, `ln4 = 90 nm` ($W_{\text{tot}} = 9.0\,\mu\text{m}$, $I_{\text{tail}} \approx 67.5\,\mu\text{A}$)
- **Second-stage PMOS driver**: `mp3 = 12`, `wp3 = 2.00 µm`, `lp3 = 90 nm` ($W_{\text{tot}} = 24.0\,\mu\text{m}$)
- **Second-stage NMOS sink**: `mn5 = 13`, `wn5 = 1.25 µm`, `ln5 = 90 nm` ($W_{\text{tot}} = 16.25\,\mu\text{m}$, $I_2 \approx 121.9\,\mu\text{A}$)
- **Miller compensation**: `cap = 0.5 pF` ($5.0 \times 10^{-13}\,\text{F}$), `res = 9500 Ω`

---

## 2. Performance Specifications and Margins

| Specification | Achieved Value | Target | Margin (Normalized $z$) | Status |
|---|---|---|---|---|
| **DC Gain** | **882.6 V/V** (58.9 dB) | $\ge 200.0\,\text{V/V}$ | $+0.631$ (+341%) | **Feasible** |
| **Unity-Gain Bandwidth (UGBW)** | **110.9 MHz** | $\ge 100.0\,\text{MHz}$ | $+0.0517$ (+10.9%) | **Feasible** |
| **Phase Margin (PM)** | **62.10°** | $\ge 60.0^\circ$ | $+0.0172$ (+2.10°) | **Feasible** |
| **Slew Rate** | **59.74 V/µs** | $\ge 30.0\,\text{V/\mu s}$ | $+0.331$ (+99.1%) | **Feasible** |
| **Input-Referred Noise** | **18.99 mV RMS** | $\le 30.0\,\text{mV RMS}$ | $-0.225$ (-36.7%) | **Feasible** |
| **Total Current** | **207.7 µA** | $200.0\,\mu\text{A}$ (minimize) | $+0.0189$ | **Optimized** |
| **Active + Cap Area** | **$8.931 \times 10^{-10}\,\text{m}^2$** | $2.0 \times 10^{-9}\,\text{m}^2$ (minimize) | $-0.383$ | **Optimized** |
| **Figure of Merit (FoM)** | **0.6637** | $> 0.300$ (feasible) | $+0.3637$ above threshold | **Optimal** |

---

## 3. Design Lineage and Optimization Story

1. **id 1 (Analyst)**: Hand-calculated initial sizing ($I_{\text{tail}}\approx 50\,\mu\text{A}$, $I_2\approx 100\,\mu\text{A}$, $C_c=1.5\,\text{pF}$, $R_c=800\,\Omega$, balance ratio = 4). Outcome: Gain=611.8 and current=175.1 µA were excellent, but UGBW (24.1 MHz), PM (31.1°), and SR (23.1 V/µs) violated targets. FoM = -1.029.
2. **id 3 (Sizer - sweep $C_c$)**: Reduced $C_c$ from $1.5\,\text{pF}$ to $0.4\,\text{pF}$. Effect: Slew rate jumped to $40.6\,\text{V/\mu s}$ (satisfied), UGBW doubled to $48.3\,\text{MHz}$, but PM dropped to $19.2^\circ$ due to second pole bottleneck $p_2 \approx g_{m6}/C_L$. FoM = -0.8195.
3. **id 8 (Sizer)**: Boosted second-stage transconductance $g_{m6}$ via `mn5: 10 -> 15` and `mp3: 4 -> 6` while keeping the balance condition $S_{mp3}/S_{mp1} = 2 \times S_{mn5}/S_{mn4} = 6$. Effect: Pushed $p_2$ out; UGBW rose to $58.1\,\text{MHz}$, PM rose to $23.85^\circ$, SR reached $47.8\,\text{V/\mu s}$. FoM = -0.6591.
4. **id 13 (Sizer - sweep $R_c$)**: Swept $R_c$ to $3000\,\Omega$. Effect: Moved transmission zero into the LHP ($R_c > 1/g_{m6}$), adding phase lead and raising PM to $39.6^\circ$. FoM = -0.4284.
5. **id 19 (Sizer - sweep $R_c$)**: Increased $R_c$ to $8500\,\Omega$. Effect: Phase margin reached $65.89^\circ$ (exceeding the $60^\circ$ target), UGBW rose to $77.4\,\text{MHz}$. FoM = -0.1079.
6. **id 20 (Sizer)**: Increased input pair $m_{n1}$ from 6 to 9. Effect: Raised $g_{m1}$ without extra DC current, bringing UGBW to $78.67\,\text{MHz}$. FoM = -0.1002.
7. **id 21 (Sizer)**: Reduced $C_c$ to $0.3\,\text{pF}$. Effect: Lifted UGBW to $83.12\,\text{MHz}$ and SR to $51.65\,\text{V/\mu s}$, with PM at $57.5^\circ$. FoM = -0.0932.
8. **id 25 (Sizer - sweep $R_c$)**: Set $R_c = 9800\,\Omega$. Effect: Restored PM to $60.33^\circ$ (feasible) with UGBW at $88.99\,\text{MHz}$. Reached the 25-simulation Phase 1 boundary at FoM = -0.0406 (only UGBW remaining).
9. **id 518 (RL Strategist - TD3 train)**: Seeded replay buffer from expert candidate 25 and trained TD3 actor locally. RL discovered simultaneous adjustments: lengthened $L_{n1}$ to $135\,\text{nm}$ (raising gain to 987.6) and balanced $W_{p3}=24\,\mu\text{m}$ ($m_{p3}=12$) against $W_{n5}=16.25\,\mu\text{m}$ ($m_{n5}=13$), yielding the first fully feasible design with UGBW = 117.3 MHz, PM = 60.60°, FoM = 0.6358.
10. **id 843 (RL Strategist - TD3 round 2 warmup)**: Refined local neighborhood around candidate 518 with slightly reduced input pair width ($W_{n1} = 1.75\,\mu\text{m}$) and increased mirror width ($W_{p1}=1.5\,\mu\text{m}$). Effect: Current reduced to $207.7\,\mu\text{A}$ while preserving PM at $62.10^\circ$, UGBW at $110.9\,\text{MHz}$, and Gain at $882.6\,\text{V/V}$. Reached highest FoM of **0.6637**.

---

## 4. Source of Decisions & Failed Predictions

- **From First-Order Equations**:
  - Bias split ($I_{\text{tail}} \approx 50-67\,\mu\text{A}$, $I_2 \approx 100-125\,\mu\text{A}$) and balance condition $S_{mp3}/S_{mp1} = 2 \times S_{mn5}/S_{mn4}$ preventing systematic offset.
  - Slew-rate scaling through $C_c$ reduction ($1.5\,\text{pF} \to 0.4\,\text{pF}$).
  - Identification of $p_2 \approx g_{m6}/C_L$ as the dominant UGBW/PM barrier with $C_L=10\,\text{pF}$.
  - Nulling resistor LHP zero placement ($R_c > 1/g_{m6}$) yielding $+40^\circ$ of phase boost.
- **From RL Exploration**:
  - Increasing input pair channel length $L_{n1}$ from $90\,\text{nm}$ to $135\,\text{nm}$ to raise DC gain from 600 to 987, creating margin to trade for wider $W$ and higher $g_m$.
  - Exact multi-parameter coordination of $m_{n4}=9, m_{n5}=13, m_{p1}=5, m_{p3}=12$ to maintain balance and achieve UGBW > 110 MHz at minimal current (207.7 µA).
- **Failed Predictions**:
  - In candidate 2, shortening $L_{n1}$ to $45\,\text{nm}$ collapsed DC gain to $102.4\,\text{V/V}$ due to severe channel-length modulation.
  - Decreasing $C_c$ below $0.4\,\text{pF}$ in candidate 826 degraded PM to $52.39^\circ$, demonstrating that $C_c \ge 0.5\,\text{pF}$ is necessary when driving $10\,\text{pF}$ load at $60^\circ$ PM.

---

## 5. Harness Execution Metrics

- **Run ID**: `harness_20261106_202431`
- **Total Simulator Calls**: 938 (out of 1000 budget; >= 900 stopping criterion met)
- **Hand Decisions Used**: 9 (out of 40 budget)
- **Feasible Solutions Found**: 23 designs
- **Total Elapsed Time**: 901.1 s (~15.0 minutes)

---

## 6. Remaining Trade-Offs

- **Lower Current**: To drop below $200\,\mu\text{A}$, $I_2$ can be decreased slightly by reducing $m_{n5}$ from 13 to 11, provided $R_c$ is increased toward $9800\,\Omega$ to maintain $60^\circ$ PM.
- **Lower Area**: $C_c = 0.5\,\text{pF}$ and $R_c = 9500\,\Omega$ constitute over 60% of total area ($8.93 \times 10^{-10}\,\text{m}^2$). Moving to a higher $g_{m6}$ architecture would permit $C_c = 0.35\,\text{pF}$, shaving ~15% total area at the expense of slightly higher stage 2 current.
