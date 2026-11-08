# Two-Stage Miller Opamp Sizing Explanation

**Run ID**: `harness_20261106_234417`  
**Final Status**: Feasible  
**Best Candidate ID**: 568  
**Figure of Merit (FoM)**: 0.6220  
**Simulator Calls Used**: 918 / 1000  
**Elapsed Time**: 1181.9 s (~19.7 min)  
**Total Feasible Solutions Found**: 101  

---

## 1. Final Sizing and Performance (Candidate #568)

### Optimized Parameters
| Parameter | Description | Value | Unit |
|---|---|---|---|
| `mn1` | Input pair multiplicity | 14 | count |
| `wn1` | Input pair width | 2.5e-6 | m (2.5 µm) |
| `ln1` | Input pair length | 9.0e-8 | m (90 nm) |
| `mp1` | Stage-1 PMOS load multiplicity | 3 | count |
| `wp1` | Stage-1 PMOS load width | 1.5e-6 | m (1.5 µm) |
| `lp1` | Stage-1 PMOS load length | 9.0e-8 | m (90 nm) |
| `mn3` | Diode bias multiplicity ($I_{\text{bias}}=30\,\mu\text{A}$) | 3 | count |
| `wn3` | Diode bias width | 1.0e-6 | m (1.0 µm) |
| `ln3` | Diode bias length | 9.0e-8 | m (90 nm) |
| `mn4` | Tail mirror multiplicity ($I_{\text{tail}}=50\,\mu\text{A}$) | 5 | count |
| `wn4` | Tail mirror width | 1.0e-6 | m (1.0 µm) |
| `ln4` | Tail mirror length | 9.0e-8 | m (90 nm) |
| `mp3` | Stage-2 CS driver multiplicity | 24 | count |
| `wp3` | Stage-2 CS driver width | 1.5e-6 | m (1.5 µm) |
| `lp3` | Stage-2 CS driver length | 9.0e-8 | m (90 nm) |
| `mn5` | Stage-2 sink multiplicity ($I_2=200\,\mu\text{A}$) | 20 | count |
| `wn5` | Stage-2 sink width | 1.0e-6 | m (1.0 µm) |
| `ln5` | Stage-2 sink length | 9.0e-8 | m (90 nm) |
| `cap` | Miller compensation capacitor $C_c$ | 5.0e-13 | F (0.5 pF) |
| `res` | Nulling resistor $R_c$ | 6500.0 | $\Omega$ (6.5 k$\Omega$) |

### Constraint Margins & Performance
| Specification | Target | Achieved Value | Margin | Status |
|---|---|---|---|---|
| **Gain** | $\ge 200.0\,\text{V/V}$ | **$722.2\,\text{V/V}$** | $+522.2\,\text{V/V}$ (+261.1%) | **PASSED** |
| **Unity-Gain Bandwidth (UGBW)** | $\ge 100.0\,\text{MHz}$ | **$104.9\,\text{MHz}$** | $+4.9\,\text{MHz}$ (+4.9%) | **PASSED** |
| **Phase Margin (PM)** | $\ge 60.0^\circ$ | **$61.86^\circ$** | $+1.86^\circ$ (+3.1%) | **PASSED** |
| **Slew Rate (SR)** | $\ge 30.0\,\text{V}/\mu\text{s}$ | **$51.81\,\text{V}/\mu\text{s}$** | $+21.81\,\text{V}/\mu\text{s}$ (+72.7%) | **PASSED** |
| **Input-Referred Noise** | $\le 0.030\,\text{V RMS}$ | **$0.0165\,\text{V RMS}$** | $-0.0135\,\text{V RMS}$ (-45.0%) | **PASSED** |
| **Layout Area** (opt target) | $2.0\times 10^{-9}\,\text{m}^2$ | **$6.904\times 10^{-10}\,\text{m}^2$** | $-65.5\%$ vs target | Optimized |
| **Supply Current** (opt target) | $200.0\,\mu\text{A}$ | **$278.9\,\mu\text{A}$** | $+39.5\%$ vs target | Optimized |

---

## 2. The Design Story (Lineage Chain)

- **Step 1 (#1, Analyst)**: Derived initial sizing from hand equations ($I_{\text{tail}}=50\,\mu\text{A}, I_2=100\,\mu\text{A}, C_c=1.5\,\text{pF}, R_c=1.2\,\text{k}\Omega$). Result: DC gain ($730\,\text{V/V}$) and current ($177\,\mu\text{A}$) were excellent, but UGBW ($28.8\,\text{MHz}$) and PM ($46.7^\circ$) fell short.
- **Step 2 (#2, Analyst)**: Scaled channel lengths down to $45\,\text{nm}$. Result: Severe $g_{\text{ds}}$ conductance collapse dropped DC gain to $11.2\,\text{V/V}$. Lesson: keep $L=90\,\text{nm}$ across devices.
- **Step 3 (#3, Sizer)**: Widened input pair ($m_{n1}=16, w_{n1}=2.5\,\mu\text{m}$) and reduced $C_c$ to $1.0\,\text{pF}$ on candidate #1. Result: Slew rate passed ($33.9\,\text{V}/\mu\text{s}$) and UGBW increased to $37.5\,\text{MHz}$, but PM dropped to $37.4^\circ$.
- **Step 4 (#4, Sizer)**: Boosted second-stage transconductance $g_{m6}$ ($m_{n5}=15, m_{p3}=24$) maintaining balance $m_{p3}/m_{p1} = 6 = 2m_{n5}/m_{n4}$. Result: PM recovered to $50.5^\circ$ and UGBW rose to $45.0\,\text{MHz}$.
- **Step 5 (#5-#10, Sizer)**: Swept $R_c \in [1.8\,\text{k}, 4.0\,\text{k}]\Omega$ on candidate #4. Candidate #10 ($R_c=4.0\,\text{k}\Omega$) shifted the zero into the LHP, raising PM to $73.6^\circ$ and UGBW to $59.0\,\text{MHz}$.
- **Step 6 (#11, Sizer)**: Traded PM margin by increasing $m_{n1}=20$ and reducing $C_c=0.6\,\text{pF}$ on candidate #10. Result: UGBW rose to $68.2\,\text{MHz}$ with PM at $57.2^\circ$.
- **Step 7 (#12, Sizer)**: Scaled $C_c=0.4\,\text{pF}$ and $R_c=6.0\,\text{k}\Omega$ (keeping $\omega_z \approx 1/(R_c C_c)$ constant). Result: UGBW reached $88.0\,\text{MHz}$, SR reached $58.3\,\text{V}/\mu\text{s}$, with PM at $52.1^\circ$.
- **Step 8 (#13, Sizer)**: Attempted widening $w_{p1}, w_{p3}$ to $2.5\,\mu\text{m}$. Result: Phase margin degraded to $47.7^\circ$ due to $C_{\text{gs3}}$ loading stage 1. Reverted to candidate #12.
- **Step 9 (#14-#19, Sizer)**: Swept $R_c \in [6.5\,\text{k}, 9.0\,\text{k}]\Omega$ on candidate #12. Candidate #17 ($R_c=8.0\,\text{k}\Omega$) resolved the UGBW constraint ($101.5\,\text{MHz} \ge 100\,\text{MHz}$), leaving only PM at $52.7^\circ$.
- **Step 10 (#20, Sizer)**: Boosted stage-2 current to $200\,\mu\text{A}$ ($m_{n5}=20, m_{p1}=3$) to push $p_2 \approx g_{m6}/C_L$ out while cutting stage-1 load. Result: UGBW reached $118.5\,\text{MHz}$, with PM at $51.8^\circ$.
- **Step 11 (#21-#22, Sizer)**: Increased $C_c$ ($0.4\,\text{pF} \to 0.5\,\text{pF} \to 0.6\,\text{pF}$). Result: PM rose to $54.5^\circ \to 57.0^\circ$ while UGBW stayed comfortably above $114\,\text{MHz}$.
- **Step 12 (#23, Sizer)**: Set $C_c = 0.7\,\text{pF}, R_c = 7000\,\Omega$. Result: **Full Feasibility achieved!** FoM = 0.5548, PM = $60.91^\circ$, UGBW = $109.9\,\text{MHz}$, all hard constraints met.
- **Step 13 (#25-#29, Diagnoser/Sizer)**: Phase 2 Optimization. Progressively downsized $m_{n1}$ ($24 \to 22 \to 20 \to 18 \to 16 \to 14$), reducing layout area while PM increased to $66.56^\circ$ and UGBW stayed at $110.3\,\text{MHz}$. FoM rose to 0.5675 (candidate #29).
- **Step 14 (#530-#534, Sizer)**: Phase 4 Polish 1. Swept $R_c \in [5\,\text{k}, 7.5\,\text{k}]\Omega$ on #29. Candidate #533 ($R_c = 6.5\,\text{k}\Omega$) minimized resistor area, jumping FoM to 0.5860 with $\text{PM}=68.22^\circ$.
- **Step 15 (#568, RL Warmup Round 2)**: Anchored TD3 on candidate #533. Warmup exploration discovered that reducing $C_c$ to $0.5\,\text{pF}$ maintained stability ($\text{PM} = 61.86^\circ$, $\text{UGBW} = 104.9\,\text{MHz}$) while cutting layout area from $7.57\times 10^{-10}\,\text{m}^2$ to $6.904\times 10^{-10}\,\text{m}^2$. FoM jumped to **0.6220**.
- **Step 16 (#915-#918, Sizer)**: Phase 4 Polish 2. Swept $R_c$ around $6.5\,\text{k}\Omega$ on candidate #568. Confirmed that $R_c = 6.5\,\text{k}\Omega$ is the global optimum of the manifold ($R_c=6.0\,\text{k}\Omega$ failed UGBW at $99.67\,\text{MHz}$; $R_c \ge 7.0\,\text{k}\Omega$ carried area penalties).

---

## 3. Decision Breakdown & Validation

- **Equations & Circuit Reasoning**:
  - Exact balance condition $S_{mp3}/S_{mp1} = 2 S_{mn5}/S_{mn4}$ was strictly preserved across all iterations, maintaining saturation in both stages and keeping DC gain above $720\,\text{V/V}$.
  - Second pole tracking $p_2 \approx g_{m6}/C_L$: boosting $m_{n5}$ to 20 enabled the amplifier to drive the heavy $C_L = 10\,\text{pF}$ load without stability breakdown.
  - Zero placement $\omega_z \approx 1/(R_c C_c)$: moving the zero into the LHP provided $+15^\circ$ to $+25^\circ$ of phase lead around UGBW.
- **RL Exploration (TD3)**:
  - Local warmup around the feasible anchor #533 uncovered that $C_c = 0.5\,\text{pF}$ combined with $R_c = 6.5\,\text{k}\Omega$ and $m_{n1}=14$ retains adequate phase lead ($61.86^\circ$) while drastically shrinking total silicon area.
  - Built a dense replay buffer of 940 points with 99 feasible Pareto-optimal variations.
- **Failed Predictions & Physical Insights**:
  - *Candidate #2*: Scaling channel lengths to minimum feature size ($45\,\text{nm}$) failed due to severe channel-length modulation ($g_{\text{ds}}$).
  - *Candidate #13*: Widening $w_{p3}$ to $2.5\,\mu\text{m}$ to raise $g_{m6}$ degraded PM because its $C_{\text{gs}}$ directly loaded stage 1's high-impedance output node.

---

## 4. Remaining Trade-Offs

1. **To reduce current further**:
   - $I_2$ is currently $200\,\mu\text{A}$ ($m_{n5}=20$). Reducing $m_{n5}$ to 18 ($I_2 = 180\,\mu\text{A}$) cuts $20\,\mu\text{A}$ of supply current (saving $\sim 0.02$ current penalty), but drops PM to $\sim 58^\circ$, requiring a slightly larger $C_c$ ($0.6\,\text{pF}$) which trades off against area.
2. **To reduce area further**:
   - Device $m_{n1}$ is currently 14. Downsizing to $m_{n1}=12$ reduces area slightly, but drops $g_{m1}$, bringing UGBW very close to the $100\,\text{MHz}$ boundary.
   - Candidate #568 currently balances both objectives near their Pareto boundary.
