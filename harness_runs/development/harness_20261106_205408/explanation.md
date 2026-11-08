# Opamp Sizing Explanation Report

- **Run ID**: `harness_20261106_205408`
- **Best Candidate ID**: 873
- **FoM (Reward)**: 0.5822 (Feasible)
- **Total Simulator Calls**: 909
- **Elapsed Time**: 857.0 s

---

## 1. Final Parameters and Specifications

### Parameters (Candidate 873)
- Stage 1 Input Pair: `mn1` = 18, `wn1` = 2.00 µm, `ln1` = 90 nm
- Stage 1 Active Load: `mp1` = 3, `wp1` = 1.25 µm, `lp1` = 90 nm
- Bias Diode: `mn3` = 3, `wn3` = 1.00 µm, `ln3` = 90 nm
- Stage 1 Tail Source: `mn4` = 5, `wn4` = 1.50 µm, `ln4` = 90 nm
- Stage 2 Driver: `mp3` = 15, `wp3` = 1.50 µm, `lp3` = 90 nm
- Stage 2 Current Sink: `mn5` = 15, `wn5` = 1.25 µm, `ln5` = 90 nm
- Miller Compensation: `cap` (Cc) = 0.80 pF, `res` (Rc) = 5000.0 Ω

### Specifications & Margins
All hard constraints are fully satisfied:

| Specification | Target | Achieved Value | Margin (Normalized) | Status |
|---|---|---|---|---|
| **Gain** | $\ge 200.0\text{ V/V}$ | **643.8 V/V** | $+0.526$ ($+443.8\text{ V/V}$) | PASS |
| **Noise** | $\le 0.03\text{ V RMS}$ | **0.01524 V RMS** | $-0.326$ ($-0.0148\text{ V}$) | PASS |
| **Phase Margin** | $\ge 60.0^\circ$ | **71.03°** | $+0.0841$ ($+11.03^\circ$) | PASS |
| **Slew Rate** | $\ge 30.0\text{ V/µs}$ | **48.22 V/µs** | $+0.233$ ($+18.22\text{ V/µs}$) | PASS |
| **UGBW** | $\ge 100.0\text{ MHz}$ | **101.10 MHz** | $+0.00527$ ($+1.10\text{ MHz}$) | PASS |
| **Current** (Minimize) | $200.0\text{ µA}$ | **307.2 µA** | $+0.211$ | Target |
| **Area** (Minimize) | $2.0\text{ n}\text{m}^2$ | **0.678 n}\text{m}^2$ | $-0.493$ | Target |

---

## 2. Design Story: Step-by-Step Lineage

1. **id 1 (Analyst)**: Sized initial baseline from first-order equations ($I_{\text{tail}}=60\text{ µA}$, $I_2=180\text{ µA}$, ratio=6, $C_c=1.0\text{ pF}$, $R_c=1\text{ k}\Omega$). Gain was 599.7 and SR was 34.1, but UGBW (41.3 MHz) and PM (37.2°) were violated.
2. **id 8 (Sizer - Sweep)**: Swept $R_c$ [500 Ω to 3000 Ω]. At 3000 Ω, moving the transmission zero into the LHP boosted PM to 61.61° (meeting PM constraint), leaving only UGBW violated.
3. **id 9 (Sizer)**: Reduced $C_c$ to 0.5 pF and increased $mn_1$ to 14 with $R_c=4.5\text{ k}\Omega$. UGBW surged from 45.5 MHz to 68.25 MHz while maintaining PM at 54.75°.
4. **id 10 (Sizer)**: Reduced $C_c$ to 0.4 pF and increased $mn_1$ to 18 with $R_c=5.5\text{ k}\Omega$. UGBW reached 78.27 MHz and PM was 53.11°.
5. **id 11 (Sizer)**: Recognized that small $C_c$ caused UGBW to approach the 2nd pole $p_2 \approx g_{m6}/C_L$. Increased stage-2 driver sizing to $mp_3, mn_5 = 16 \times 1.5\text{ µm}$ to push $p_2$ out. UGBW jumped to 127.8 MHz and PM reached 59.11° (0.89° from feasible).
6. **id 16 (Sizer)**: Traded excess UGBW margin back into PM by increasing $C_c$ from 0.4 pF to 0.5 pF ($R_c=4.5\text{ k}\Omega$). Crossed feasibility threshold (**FoM = 0.4977**, UGBW = 110.5 MHz, PM = 63.61°).
7. **id 18 (Sizer)**: Reduced current by scaling stage-2 sizes to $mp_3, mn_5 = 14 \times 1.5\text{ µm}$, perfectly maintaining the balance condition $S_{mp3} = S_{mn5}$. Current dropped to 396.5 µA, boosting **FoM to 0.5456**.
8. **id 873 (RL - TD3)**: Pre-trained/anchored on design 18 and explored the local neighborhood. Discovered a superior multi-device balance: scaling $mn_3=3, mn_4=5, mn_5=15, mp_1=3, mp_3=15, C_c=0.8\text{ pF}, R_c=5000\text{ }\Omega$. Dropped total current down to 307.2 µA with a robust PM of 71.03° and UGBW of 101.1 MHz, achieving the run's best **FoM = 0.5822**.

---

## 3. Decisions: Equations vs. RL vs. Failed Predictions

- **Decisions from Equations**:
  - Current splitting and mirror ratio balance ($S_{mp3}/S_{mp1} = 2 \cdot S_{mn5}/S_{mn4}$) to avoid systematic DC offset and retain saturation.
  - Identification of $p_2 \approx g_{m6}/C_L$ bottleneck when scaling down $C_c$, and resolving it by increasing stage-2 transconductance.
  - LHP zero placement via nulling resistor $R_c \approx 1/g_{m6}$ for phase margin restoration.
- **Decisions from RL**:
  - Multi-dimensional co-optimization of device widths ($wp_1, wn_4, wp_3, wn_5$) and multiplicities ($mn_3=3, mn_4=5, mn_5=15$) that dropped overall current by nearly 90 µA while maintaining tight frequency specs.
- **Failed Predictions / Learned Lessons**:
  - *Candidate 2*: Dropping $ln_1$ to 45 nm collapsed stage-1 gain to 91.8 due to short-channel output conductance degradation. (Lesson: $L \ge 90\text{ nm}$ is mandatory for gain).
  - *Candidate 17*: Increasing $mn_3$ alone without compensating $mn_1/C_c$ dropped $I_{\text{tail}}$ too much, starving $g_{m1}$ and causing UGBW to fall below 100 MHz.

---

## 4. Resource Usage
- **Simulator Calls**: 909 / 1000 budget used (90.9%).
- **Hand Decisions**: 14 / 40 decisions used (35.0%).
- **Elapsed Wall-Clock Time**: 857.0 seconds.

---

## 5. Main Trade-Offs Left
- **For Lower Current**: Slew rate (48.2 V/µs) and gain (643.8) still have excess margin. Further decreasing $I_2$ (or increasing $mn_3$) could lower current toward 200 µA, provided $g_{m1}$ is boosted with wider $mn_1$ fingers or $C_c$ is slightly lowered with careful $R_c$ retuning to maintain UGBW $\ge 100\text{ MHz}$.
- **For Lower Area**: The Miller capacitor ($C_c = 0.8\text{ pF}$) and nulling resistor ($R_c = 5\text{ k}\Omega$) constitute the majority of passive area. Trimming $C_c$ to $0.5\text{ pF}$ and $R_c$ to $3.5\text{ k}\Omega$ would reduce passive area by ~30%, requiring a modest increase in stage-2 $g_{m6}$ to keep phase margin above 60°.
