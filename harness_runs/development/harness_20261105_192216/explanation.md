# Opamp Sizing Explanation & Design Lineage Report

**Run ID**: harness_20261105_192216  
**Best Design Candidate ID**: 577  
**Feasible**: Yes (FoM = 0.6857)  
**Total Simulator Calls**: 577  
**Elapsed Time**: 1056.2 s  

---

## 1. Final Design: Sizing Parameters & Specifications

### Sizing Parameters (Physical Grid Values)
- **Differential Input Pair ($M_{n1,2}$)**: $m_{n1} = 23$, $W_{n1} = 2.0\,\mu\text{m}$, $L_{n1} = 90\,\text{nm}$ (Total $W_1 = 46.0\,\mu\text{m}$)
- **First-Stage Active Load ($M_{p1,2}$)**: $m_{p1} = 6$, $W_{p1} = 1.25\,\mu\text{m}$, $L_{p1} = 90\,\text{nm}$
- **Bias Reference Branch ($M_{n3}$)**: $m_{n3} = 3$, $W_{n3} = 1.0\,\mu\text{m}$, $L_{n3} = 90\,\text{nm}$ ($I_{\text{bias}} = 30.0\,\mu\text{A}$)
- **Tail Current Source ($M_{n4}$)**: $m_{n4} = 8$, $W_{n4} = 1.0\,\mu\text{m}$, $L_{n4} = 90\,\text{nm}$ ($I_{\text{tail}} \approx 80\,\mu\text{A}$)
- **Second-Stage Driver ($M_{p3}$)**: $m_{p3} = 18$, $W_{p3} = 1.25\,\mu\text{m}$, $L_{p3} = 90\,\text{nm}$
- **Second-Stage Current Sink ($M_{n5}$)**: $m_{n5} = 16$, $W_{n5} = 0.75\,\mu\text{m}$, $L_{n5} = 90\,\text{nm}$ ($I_2 \approx 120\,\mu\text{A}$)
- **Miller Compensation**: $C_c = 0.6\,\text{pF}$ ($6.0 \times 10^{-13}\,\text{F}$), $R_c = 7.0\,\text{k}\Omega$ ($7000\,\Omega$)

### Performance Specifications & Margins
| Specification | Target | Achieved Value | Margin | Normalized $z$ | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gain** | $\ge 200.0\,\text{V/V}$ | **723.5 V/V** | **+523.5 V/V** | +0.567 | **PASS** |
| **Phase Margin (PM)** | $\ge 60.0^\circ$ | **62.12°** | **+2.12°** | +0.017 | **PASS** |
| **Unity-Gain Bandwidth (UGBW)** | $\ge 100.0\,\text{MHz}$ | **101.8 MHz** | **+1.8 MHz** | +0.009 | **PASS** |
| **Slew Rate (SR)** | $\ge 30.0\,\text{V}/\mu\text{s}$ | **57.93 V/$\mu$s** | **+27.93 V/$\mu$s** | +0.318 | **PASS** |
| **Input-Referred Noise** | $\le 0.030\,\text{V RMS}$ | **0.0140 V RMS** | **-0.0160 V RMS** | -0.363 | **PASS** |
| **Total Current** | minimize ($200\,\mu\text{A}$) | **226.3 $\mu$A** | $+26.3\,\mu\text{A}$ | +0.062 | Optimized |
| **Total Area** | minimize ($2\times 10^{-9}\,\text{m}^2$) | **$7.635\times 10^{-10}\,\text{m}^2$** | $-1.236\times 10^{-9}\,\text{m}^2$ | -0.447 | Optimized |
| **Figure of Merit (FoM)** | $> 0.30$ (feasible) | **0.6857** | **+0.3857** | — | **FEASIBLE** |

---

## 2. Design Story & Lineage

The final solution represents a synthesis of analytical domain knowledge, deep reinforcement learning exploration, and local sensitivity polish:

1. **Candidate 1 (Analyst)**: Hand equations derived $I_{\text{tail}}=50\,\mu\text{A}$, $I_2=100\,\mu\text{A}$, balance ratio $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4} = 4.0$, $C_c=1.5\,\text{pF}, R_c=1.0\,\text{k}\Omega$. Achieved high gain ($703.2\,\text{V/V}$) with $L=90\,\text{nm}$, establishing the fundamental topology template, but suffered low UGBW ($27.6\,\text{MHz}$) and PM ($40.1^\circ$).
2. **Candidate 4 (Sizer)**: Reduced $C_c$ from $1.5\,\text{pF} \to 0.6\,\text{pF}$ and raised $R_c \to 2.5\,\text{k}\Omega$. Slew rate jumped to $43.2\,\text{V}/\mu\text{s}$ (feasible) and UGBW rose to $46.2\,\text{MHz}$.
3. **Candidate 5 (Sizer)**: Applied pole-zero cancellation theory $R_c \approx \frac{1}{g_{m6}}(1 + C_L/C_c) \approx 8.0\,\text{k}\Omega$. Zero cancelled the heavy $C_L=10\,\text{pF}$ pole; PM surged from $39.7^\circ \to 69.27^\circ$ and UGBW reached $64.1\,\text{MHz}$.
4. **Candidate 6 (Sizer)**: Boosted $g_{m1}$ ($m_{n1}=16$) and scaled $C_c \to 0.4\,\text{pF}$, moving UGBW to $73.85\,\text{MHz}$ and PM to $59.56^\circ$.
5. **Candidate 10 (Sizer)**: Recognized weak-inversion operation of the input pair ($g_m \propto I_D$); scaled $m_{n4}=6, m_{n5}=12$, moving UGBW to $85.8\,\text{MHz}$ and PM to $59.35^\circ$.
6. **Candidate 11 (Sizer)**: Scaled $m_{n4}=7, m_{n5}=14, m_{n1}=18$, reaching $98.95\,\text{MHz}$ UGBW and $58.71^\circ$ PM.
7. **Candidate 17 (Sizer)**: Switched to $C_c = 0.5\,\text{pF}$ for stronger pole-splitting separation with $m_{n4}=8, m_{n5}=16, m_{n1}=22$. **Achieved full feasibility ($\text{FoM} = 0.6100$)**.
8. **Candidate 19 (Sizer)**: Optimized current by scaling $m_{n4}=7, m_{n5}=15, m_{p3}=17$. Current reduced to $245.3\,\mu\text{A}$, lifting FoM to **0.6477**.
9. **Candidate 138 (RL Strategist / TD3)**: TD3 local refinement discovered an alternative low-current operating point with $W_{n5}=0.75\,\mu\text{m}$, $W_{p1}=1.25\,\mu\text{m}, m_{p1}=6$, and $W_{p3}=1.25\,\mu\text{m}, m_{p3}=18$. Dropped total current to **$226.3\,\mu\text{A}$** with high margins ($PM=65.3^\circ, UGBW=107.7\,\text{MHz}, \text{Gain}=723.5\,\text{V/V}$), though with $C_c=0.8\,\text{pF}$ ($\text{FoM} = 0.6305$).
10. **Candidate 572 (Sizer Polish)**: Reduced $C_c$ on Candidate 138 from $0.8\,\text{pF} \to 0.6\,\text{pF}$, trimming capacitor area and lifting FoM to **0.6636**.
11. **Candidate 574 (Sizer Polish)**: Trimmed $R_c$ to $7.4\,\text{k}\Omega$, lifting FoM to **0.6709**.
12. **Candidate 575 (Sizer Polish)**: Trimmed $R_c$ to $7.1\,\text{k}\Omega$, lifting FoM to **0.6820**.
13. **Candidate 577 (Sizer Polish)**: Tuned $R_c$ to $7.0\,\text{k}\Omega$, pinning UGBW right above target at $101.8\,\text{MHz}$ and minimizing area. **Final global champion with $\text{FoM} = 0.6857$**.

---

## 3. Methodological Attribution: Equations vs. RL vs. Lessons

- **Decisions from Hand Equations**:
  - Mirror balance condition $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4}$ preserved the high internal gain ($>650\,\text{V/V}$) throughout all hand and polish steps.
  - Pole-zero cancellation formula $R_c \approx \frac{1}{g_{m6}}(1 + C_L/C_c)$ was the pivotal analytical breakthrough that elevated phase margin from $39^\circ \to 69^\circ$ with $C_L = 10\,\text{pF}$.
  - Current-splitting trade-offs between $I_{\text{tail}}$ (slew rate, bandwidth) and $I_2$ (second-pole stability, gain).

- **Decisions from Reinforcement Learning (TD3)**:
  - TD3 discovered the asymmetric device sizing ($W_{n5}=0.75\,\mu\text{m}$ combined with $W_{p1}=W_{p3}=1.25\,\mu\text{m}$), which unlocked a reduction of total current from $245.3\,\mu\text{A} \to 226.3\,\mu\text{A}$ while simultaneously boosting DC gain from $670 \to 723.5\,\text{V/V}$ and lowering noise to $0.0140\,\text{V RMS}$.
  - Generated a dense population of 20 feasible Pareto candidates.

- **Failed Predictions & Circuit Lessons**:
  - *Candidate 2 ($L=45\,\text{nm}$)*: Predicted higher $g_m$ from minimum channel length; failed because DIBL and channel-length modulation collapsed $r_o$ and dropped DC gain to $3.8\,\text{V/V}$.
  - *Candidate 8 ($W_{p3}=2\,\mu\text{m}$)*: Predicted higher $g_{m6}$ would raise PM; failed because the doubled gate area added parasitic $C_{gs3}$ that heavily loaded the first-stage output node, degrading PM from $59.6^\circ \to 52.6^\circ$.
  - *Candidate 9 ($W_{n1}$ widening)*: Predicted diff-pair widening alone would scale UGBW; observed negligible gain because at $I_D=25\,\mu\text{A}$ the input NMOS operates in weak inversion where $g_m/I_D \approx \text{const}$. Increasing $I_{\text{tail}}$ was required.
  - *Candidate 576 ($R_c=6.8\,\text{k}\Omega$)*: Over-trimming $R_c$ caused UGBW to dip slightly below target ($99.86\,\text{MHz}$), defining the lower bound for compensation resistance.

---

## 4. Remaining Trade-offs & Sensitivity

1. **Trading Current for Bandwidth**: With UGBW at $101.8\,\text{MHz}$ ($+1.8\,\text{MHz}$ margin), current cannot be further reduced without increasing input pair width $W_{n1}$ or accepting a slight drop below $100\,\text{MHz}$.
2. **Trading Area for Phase Margin**: Candidate 577 uses $C_c = 0.6\,\text{pF}$ and $R_c = 7.0\,\text{k}\Omega$ to yield $PM = 62.12^\circ$. Reducing $C_c$ to $0.5\,\text{pF}$ drops area by $\sim 4\%$, but dips PM to $58.7^\circ$. Thus, Candidate 577 lies directly on the constrained Pareto frontier.
