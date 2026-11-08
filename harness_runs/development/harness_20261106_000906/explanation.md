# Opamp Sizing Explanation (Run: harness_20261106_000906)

## 1. Final Sizing Parameters and Specs

### Final Device Sizing (Candidate ID: 681)
- **First Stage Input Pair (`mn1`/`mn2`)**: $m = 13$, $W = 1.75\,\mu\text{m}$, $L = 90\,\text{nm}$
- **First Stage Active Load (`mp1`/`mp2`)**: $m = 4$, $W = 1.50\,\mu\text{m}$, $L = 90\,\text{nm}$
- **Bias Diode (`mn3`)**: $m = 2$, $W = 1.25\,\mu\text{m}$, $L = 90\,\text{nm}$ ($I_{\text{bias}} = 30\,\mu\text{A}$)
- **Tail Current Source (`mn4`)**: $m = 6$, $W = 1.00\,\mu\text{m}$, $L = 90\,\text{nm}$ ($I_{\text{tail}} \approx 72\,\mu\text{A}$)
- **Second Stage Driver (`mp3`)**: $m = 11$, $W = 2.50\,\mu\text{m}$, $L = 90\,\text{nm}$
- **Second Stage Sink (`mn5`)**: $m = 12$, $W = 1.00\,\mu\text{m}$, $L = 90\,\text{nm}$ ($I_2 \approx 144\,\mu\text{A}$)
- **Compensation**: $C_c = 0.60\,\text{pF}$ (`cap` = $6.0\times 10^{-13}\,\text{F}$), $R_c = 5900\,\Omega$ (`res` = $5900.0\,\Omega$)

### Performance Specifications and Margins
| Specification | Target | Value (Candidate 681) | Status | Margin (Normalized / Physical) |
|---|---|---|---|---|
| **Figure of Merit (FoM)** | $> 0.30$ | **0.6877** | **Feasible** | $+0.3877$ above feasibility threshold |
| **UGBW** | $\ge 100.0\,\text{MHz}$ | $100.20\,\text{MHz}$ | Pass | $+0.20\,\text{MHz}$ ($z = +0.0011$, binding constraint) |
| **Phase Margin (PM)** | $\ge 60.0^\circ$ | $66.18^\circ$ | Pass | $+6.18^\circ$ ($z = +0.0490$) |
| **DC Gain** | $\ge 200.0\,\text{V/V}$ | $716.5\,\text{V/V}$ | Pass | $+516.5\,\text{V/V}$ ($z = +0.564$) |
| **Slew Rate** | $\ge 30.0\,\text{V/\mu s}$ | $54.69\,\text{V/\mu s}$ | Pass | $+24.69\,\text{V/\mu s}$ ($z = +0.292$) |
| **Input-Referred Noise** | $\le 0.030\,\text{V RMS}$ | $0.0184\,\text{V RMS}$ | Pass | $-0.0116\,\text{V RMS}$ ($z = -0.240$) |
| **Total Current** | minimize ($200\,\mu\text{A}$) | $251.0\,\mu\text{A}$ | - | $z_{\text{current}} = +0.113$ |
| **Total Area** | minimize ($2.0\,\text{nm}^2$) | $6.653\times 10^{-10}\,\text{m}^2$ | - | $z_{\text{area}} = -0.501$ (well below target) |

---

## 2. Design Story (Lineage Chain)

1. **Candidate 1 & 2 (Analyst)**: Sized initial topology with $I_{\text{tail}} \approx 60\,\mu\text{A}$, $I_2 \approx 120\,\mu\text{A}$ and balance ratio $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4} = 4$; achieved Gain $716\,\text{V/V}$, SR $36.3\,\text{V/\mu s}$, but PM ($29.5^\circ$) and UGBW ($41\,\text{MHz}$) were binding violations.
2. **Candidate 8 (Sizer, sweep $R_c$)**: Swept $R_c$ from $800\,\Omega$ to $2300\,\Omega$ to null the RHP zero; monotonically recovered PM from $29.5^\circ$ to $51.3^\circ$.
3. **Candidate 9 (Sizer, test $l_{n1}$)**: Scaled $l_{n1}$ down to $45\,\text{nm}$ to increase input transconductance; prediction failed as short-channel output conductance collapsed DC gain from $716$ to $117\,\text{V/V}$.
4. **Candidate 10 (Sizer, increase $R_c$)**: Advanced $R_c$ to $3200\,\Omega$ on base 8; pushed PM to $60.87^\circ$, satisfying the phase margin constraint and leaving UGBW as the sole violation.
5. **Candidate 11 & 12 (Sizer, $C_c$ & stage 2 gm)**: Lowered $C_c$ to $0.6\,\text{pF}$ and raised $g_{m6}$ ($mn5=10, wp3=2.5\mu\text{m}$, exact balance ratio $5.0$); lifted UGBW from $45.8\,\text{MHz}$ to $63.4\,\text{MHz}$.
6. **Candidate 17 (Sizer, sweep $R_c$)**: Swept $R_c$ over $3500-6300\,\Omega$ to match the lower $C_c$; at $R_c=6300\,\Omega$, PM reached $65.97^\circ$ and UGBW reached $87.62\,\text{MHz}$.
7. **Candidate 18 (Sizer, $C_c=0.5\,\text{pF}$)**: Scaled $C_c$ down to $0.5\,\text{pF}$ and adjusted $R_c=7200\,\Omega$; pushed UGBW to $97.14\,\text{MHz}$ ($97\%$ of target).
8. **Candidate 21 (Sizer, sweep $R_c$, FEASIBLE)**: Swept $R_c$ over $7500-8700\,\Omega$; at $R_c=7800\,\Omega$, UGBW crossed the threshold to $102.4\,\text{MHz}$ with PM $62.47^\circ$, achieving full feasibility ($\text{FoM} = 0.6590$).
9. **Candidate 26 & 27 (Sizer, trim $mn1$)**: Pruned input pair multiplicity $mn1$ from 18 to 14; lowered gate area and improved feasible FoM to $0.6635$.
10. **Candidate 136 (RL Strategist, TD3 Anchor Refinement)**: TD3 explored multi-dimensional interactions around candidate 27, discovering that re-centering the bias mirror ($w_{n3}=1.25\mu\text{m}, m_{n4}=6, m_{n5}=12, m_{p1}=4, m_{p3}=11$) allowed $R_c$ to drop to $6400\,\Omega$ with $C_c=0.6\,\text{pF}$, slashing total area to $7.01\times 10^{-10}\,\text{m}^2$ ($\text{FoM} = 0.6678$).
11. **Candidate 681 (Sizer, Polish Sweep)**: Fine-swept $R_c$ down to $5900\,\Omega$ on base 136; verified that $5900\,\Omega$ sits exactly at the UGBW feasibility boundary ($100.2\,\text{MHz}$) while reducing resistor area, yielding the global peak FoM of **0.6877**.

---

## 3. Decision Breakdown: Equations, RL, and Failed Predictions

- **Decisions from Hand Equations**:
  - Current split and device matching ratios maintaining the balance condition $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4}$.
  - Scaling $R_c$ inversely with $C_c$ to null the RHP zero and project phase lead into the UGBW transition region.
  - Sizing $mn5$ and $wp3$ to shift the second pole $p_2 = g_{m6}/C_L$ well beyond UGBW.
- **Decisions from TD3 Reinforcement Learning**:
  - Multi-parameter re-centering across 7 devices simultaneously ($wn3, mn4, mn5, mp1, mp3, mn1, wn1$), finding an optimal balance point that shaved current mirror sensitivity and allowed smaller compensation area.
  - Populating a rich Pareto front containing 76 feasible designs in the replay buffer.
- **Predictions that Failed**:
  - *Sizer Candidate 9*: Shortening $ln1$ to $45\,\text{nm}$ was expected to double $g_{m1}$ without breaking constraints; instead, severe DIBL and channel-length modulation collapsed stage 1 output resistance, causing DC gain to drop from $716\,\text{V/V}$ to $117\,\text{V/V}$. (Lesson: $ln1 \ge 90\,\text{nm}$ is strictly required).
  - *Sizer Candidate 19*: Increasing $mn1$ from 18 to 20 was expected to lift UGBW by $+5\%$, but produced only $+0.05\,\text{MHz}$ ($< 0.1\%$) because bandwidth was bottlenecked by second-stage pole/zero dynamics rather than $g_{m1}$ alone.

---

## 4. Resource Usage
- **Simulator Calls**: 917 calls (out of 1000 total budget; meeting the stopping criteria $\ge 900$).
- **LLM Hand Decisions**: 16 decisions (out of 40 budget).
- **Feasible Solutions Discovered**: 76 distinct designs.
- **Elapsed Wall-Clock Time**: ~900 seconds.

---

## 5. Main Trade-Offs Left
- **For Lower Area**: Resistor $R_c$ occupies substantial silicon real estate. Reducing $R_c$ below $5900\,\Omega$ reduces area further, but causes UGBW to fall just shy of the $100\,\text{MHz}$ constraint ($5800\,\Omega \to 99.06\,\text{MHz}$). To enable even smaller $R_c$, one would slightly increase $I_2$ ($mn5$) to raise $g_{m6}$.
- **For Lower Current**: Total current ($251\,\mu\text{A}$) exceeds the $200\,\mu\text{A}$ target ($z = +0.113$). Current can be lowered by scaling $wn3$ upward, but this reduces $g_{m1}$ and $g_{m6}$, requiring a slightly higher $C_c$ or longer channels to maintain stability and gain.
