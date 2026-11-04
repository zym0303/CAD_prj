# Milestone 1 — Simulator Interface: what was done and why

This document explains every decision made in milestone 1, so it can be studied and reused for the report.

Files touched in this milestone:

| File | What changed |
|---|---|
| `ngspice_interface/files/input_netlists/TwoStage.cir` | Filled the `???` lines: four `wrdata` lines and the `noise` command |
| `ngspice_interface/dut_testbench.py` | Wrote `find_dc_gain`, `find_ugbw`, `find_phm`, `find_slew_rate` (+ two small helpers) |
| `ngspice_interface/ngspice_wrapper.py` | Setup only: use the local ngspice when the ESAT server path does not exist |
| `test_dut.py` | Unit tests, step by step through the pipeline |

---

## 1. The big picture: what milestone 1 is for

The whole project is an automatic opamp sizer. An optimiser (RL agent in milestone 3, LLM harness in milestone 4) proposes transistor sizes thousands of times. For each proposal, the code must answer: *how good is this opamp?* Milestone 1 builds that answer — the chain from "sizes in" to "specs out":

```
sizes {mp1, wp1, lp1, ..., cap, res}
   │  create_new_netlist()   copy of TwoStage.cir with the new .param values
   ▼
netlist in no_backup/output_netlists/
   │  simulate()             ngspice -b <netlist>
   ▼
ngspice runs: tran, ac, noise, op
   │  wrdata lines           ← written in this milestone
   ▼
4 CSV files in no_backup/output_files/
   │  parse_outputs()        given
   ▼
numpy arrays: time, vout_tran, freq, vout_complex, current, noise
   │  find_* functions       ← written in this milestone
   ▼
{area, current, gain, noise, phm, slewRate, ugbw}   → used by circuit_env.py (milestone 2)
```

Why it matters: if a measurement is wrong here, the RL agent will optimise the wrong thing in milestone 3 and nothing later can fix it. That is why the instructions ask for a unit test as *proof* of correctness.

---

## 2. The circuit (TwoStage.cir)

A two-stage Miller-compensated opamp in a 45 nm technology (`p045_TT.sp`, also SS and FF corners).

| Block | Devices | Role |
|---|---|---|
| Bias | `ibias` = 30 µA into diode-connected **mn3** | Creates the gate voltage `net7` that mirrors current into mn4 and mn5 |
| Tail current | **mn4** | Sets the current of the input pair |
| Stage 1 (input) | NMOS diff pair **mn1/mn2**, PMOS mirror load **mp1/mp2** | Differential → single-ended gain; output at `net5` |
| Stage 2 (output) | PMOS common-source **mp3**, NMOS current-source load **mn5** | Second gain stage; output at `net6` |
| Compensation | **Cc** (`cap`) in series with **Rc** (`res`) from `net5` to `net6` | Miller cap splits the poles (stability); the series resistor moves the right-half-plane zero (better phase margin) |
| Load | **CL** = 10 pF on `net6` | What the opamp has to drive |

**Input stimulus.** One source `Vinput` (node `aid`) drives two voltage-controlled sources `ein1`/`ein2` with gains +0.5 / −0.5 on top of `VCM` = 0.6 V. So the opamp sees a fully differential input of exactly `v(aid)` around the common-mode level. `Vinput` has:
- `ac=1.0` → in AC and noise analysis, `v(net6)` *is* the transfer function H(f) (input amplitude 1).
- `PULSE(-VHIGH/2 → +VHIGH/2)` → in transient, a ±0.6 V differential step: large enough to slew the output.

**Sign of the gain.** `aid` → +0.5 → `net1` → gate of mn2 → drain `net5` (inverting) → gate of mp3 → `net6` (inverting). Two inversions → **non-inverting**, DC phase ≈ 0°. This is used in the phase-margin calculation.

**Open loop.** There is no feedback in the testbench. All specs are open-loop specs. A side effect: with a large step input, the output swings almost rail-to-rail, which is exactly what the slew-rate measurement needs.

**Multipliers in the YAML** (`mn1: 2`, `mp1: 2`): the parameter `mn1` sizes *two* transistors (mn1 and mn2), likewise `mp1` (mp1 and mp2). The area estimator uses this.

---

## 3. The netlist: saving the simulation results

### 3.1 What was missing

The `.control` block is a script ngspice runs top to bottom. The analyses (`tran`, `ac`, `op`) were already there, but nothing *saved* their results. ngspice kept them in memory and threw them away when it exited. That is why test_2 (simulation runs) passed but test_3 (output files exist) failed.

### 3.2 The lines added

```spice
tran 50n 30u
wrdata tran_TwoStage.csv v(net6)

ac dec 10 1 1T
wrdata ac_TwoStage.csv v(net6)

noise v(net6) vinput dec 10 1 1T
wrdata noise_TwoStage.csv onoise_total

op
wrdata dc_TwoStage.csv i(vdd)
```

### 3.3 Why each choice

- **`v(net6)`** — `net6` is the output node (drain of mp3/mn5, where CL is).
- **`wrdata`** writes vectors as plain text columns. The x-axis (time, frequency) is always written first. A complex vector (AC) gives two columns: real and imaginary. `set wr_vecnames` (already in the netlist) adds a header line — that is why `parse_outputs()` uses `skip_header=1`.
- **`noise v(net6) vinput dec 10 1 1T`** — syntax is `noise v(output) <input source> <sweep>`.
  - `vinput` is the source with `ac=1`; noise analysis needs it to refer noise to the input.
  - Same sweep as AC (1 Hz – 1 THz, 10 points/decade) so both cover the same band.
  - Produces two result sets: `noise1` (spectral density, V/√Hz per frequency) and `noise2` (integrated). **`onoise_total`** in `noise2` is the total RMS output noise in V — one number, which is the spec.
- **`i(vdd)`** — current through the supply source named `vdd`. ngspice counts current flowing *into* the + terminal as positive; a supply delivers current *out* of it, so `i(vdd)` is negative (≈ −75 µA). That is why the given parser does `self.current = - dc_raw_outputs[1]`.

### 3.4 Rules the lines must follow (from the wrapper code)

1. **`wrdata` at the start of the line.** `create_new_netlist()` only rewrites lines where `line.startswith("wrdata")`.
2. **File name `<kind>_TwoStage.csv`, no folder.** The wrapper finds it with the regex `wrdata (\w+)\.csv`, keeps the part before the first `_` and rewrites it to `no_backup/output_files/<kind>_<random_name>.csv` — a unique name per simulation, so parallel runs never overwrite each other.
3. **One vector per file**, because `parse_outputs()` reads fixed columns:

| File | Columns written | Parser reads | Why |
|---|---|---|---|
| tran | `time  v(net6)` | `[:,0]`, `[:,1]` | |
| ac | `frequency  Re  Im` | `[:,0]`, `[:,1]`, `[:,2]` | complex → 2 columns |
| dc | `net4  i(vdd)` | `[1]` | `op` has no x-axis; ngspice uses the first node (`net4`, shown as `[default scale]` by `display`) as column 0 |
| noise | `onoise_total  onoise_total` | `[0]` | no x-axis either; the value is written twice |

### 3.5 How it was checked

- Running ngspice by hand (`env -u DISPLAY ngspice ...cir`, then `display`, `setplot`, `setplot noise2`, `print onoise_total`) showed all result sets (`tran1`, `ac1`, `noise1`, `noise2`, `op`) and `onoise_total = 4.4794519e-05` for the template sizes.
- The four CSVs had the column layout above.
- test_3 passes.

Side note: `env -u DISPLAY` is needed only for *interactive* ngspice on the Mac, because the Homebrew ngspice tries to open an X11 (XQuartz) window. Batch mode (`-b`), which the Python code uses, is not affected.

---

## 4. The measurements (dut_testbench.py)

Input data for every function:

| Name | What | Size |
|---|---|---|
| `freq` | AC frequencies 1 Hz → 1 THz, 10 per decade | 121 |
| `vout` | complex `v(net6)` = H(f), since the input is `ac=1` | 121 |
| `time`, `signal` | transient time and `v(net6)` | ~650–680 |

Area, current and noise needed no new function (area: `area_estimation.py`; current and noise: read straight from the CSVs).

### 4.1 DC gain — `find_dc_gain`

```python
return float(np.abs(vout)[0])
```
- **What:** magnitude of H at the first AC point (1 Hz).
- **Why 1 Hz is "DC":** the dominant pole of this opamp is at kHz or higher, so at 1 Hz the gain curve is flat.
- **Why V/V and not dB:** the YAML target is `gain: 200`. 200 dB is impossible for a 2-stage opamp; 200 V/V (≈ 46 dB) is realistic. So the spec is in V/V.

### 4.2 Unity-gain bandwidth — `find_ugbw`

**Definition:** the first frequency where |H(f)| = 1 (0 dB). Target: 1 MHz.

**Problem:** with 10 points per decade, neighbouring points are 26 % apart in frequency; the crossing almost never lands on a sample. We must estimate it *between* samples.

**Method:**
1. `_first_unity_crossing`: the first index `i` with |H| < 1. The crossing lies between `i-1` (above 1) and `i` (below 1).
2. Take a small window of points around it (`_local_window`, 3 on each side).
3. Fit a cubic spline to **log10|H| vs log10 f** and solve log10|H| = 0 with a root finder. This is the helper `_get_best_crossing` that was already in the file (scipy `InterpolatedUnivariateSpline` + `brentq`).
4. If the spline fails, fall back to a straight line between the two bracketing points.

**Why log-log:** on a Bode plot, near the crossing, log|H| vs log f is close to a straight line (−20 dB/decade for a dominant-pole opamp). In linear axes it is strongly curved, so any interpolation is worse.

**Why a spline instead of a straight line (tested, not assumed):** 40 random sizings, 27 with a unity crossing, compared to a reference ngspice run with 1000 points/decade:

| Method on the normal 10 points/decade | median error | worst error |
|---|---|---|
| straight line in log-log | 0.08 % | 0.81 % |
| cubic spline in log-log (chosen) | 0.000 % | 0.002 % |
| ngspice `meas ... when vm(net6)=1` on the same coarse sweep | ~0.3 % | — |

The curve bends slightly near the crossing; a straight line over a 26 % frequency step cuts the corner, the spline follows it.

**Why only a local window:** a spline over all 121 points + a root search over the whole range could lock onto a *later* crossing on designs with gain peaking. The first crossing is the one that defines UGBW.

**Guards (bad designs must give a bad number, not a crash):**
- gain never above 1 → `0` (no bandwidth at all)
- gain never below 1 within the sweep → last frequency (1 THz)

**Rejected alternative: the −3 dB bandwidth** (e.g. `python-control`'s `bandwidth()`). That is the frequency where gain drops to 0.707 × DC gain — the dominant pole, not UGBW. For a dominant-pole opamp, UGBW ≈ A0 × f₋₃dB, so using it would under-estimate the speed by a factor equal to the gain (20–200×). It also works on an analytic model (it can evaluate H(jω) anywhere and bisect), while we only have samples. The *structure* is the same though: find the first point past the level, bracket, solve.

### 4.3 Phase margin — `find_phm`

**Definition:** PM = 180° + ∠H(f) at f = UGBW. How far the phase is from −180° when the loop gain reaches 1. Target: 60°. Below 0 → the opamp oscillates in unity feedback.

**Method:**
1. Phase in degrees: `np.degrees(np.angle(vout))`.
2. **`np.unwrap`** — `np.angle` only returns (−180°, 180°], so a phase that goes past −180° would jump to +180°. Unwrapping removes these jumps.
3. Shift by whole multiples of 360° so the DC phase is near 0° (the circuit is non-inverting, section 2).
4. Read the phase at the UGBW with a cubic spline over the same local window as in 4.2.
5. No unity crossing → return 0.

**Why the unwrap is essential (found during testing):** two of the 27 random designs are unstable — their phase is already −242° and −216° at the UGBW. Our code gives PM = −62° and −36° (correct: unstable). ngspice's `vp()` wraps the phase, giving 298° and 324° — which would look like *excellent* phase margin. Without unwrapping, the RL agent would be rewarded for unstable designs.

**Accuracy:** identical to the 1000-points/decade reference (0.000° median) for all stable designs.

### 4.4 Slew rate — `find_slew_rate`

**Definition:** the maximum rate of change of the output for a large input step, limited by how fast the bias currents can charge the capacitances (Cc, CL). Target: 15 V/µs.

**Method:**
1. Output swing: `vmin`, `vmax` of the transient output.
2. Levels: V10 = vmin + 0.1·swing, V90 = vmin + 0.9·swing.
3. Rising edge: first time the output crosses V10 upwards, then the first upward crossing of V90 after that. Falling edge: V90 downwards, then V10 downwards.
4. Each crossing time is linearly interpolated between the two samples around it (the time step is up to 50 ns, so this matters).
5. SR = (V90 − V10) / (t90 − t10) for each edge, converted to V/µs (`time_unit='us'` divides by 10⁶).
6. Return the **smaller** of the two edges.

**Why 10 %–90 %:** the first and last parts of the edge are rounded (small-signal settling, not slewing). The middle 80 % is the linear slewing part. These thresholds are given in the function signature.

**Why the minimum of both edges:** in a Miller opamp the two edges are limited by different currents (one by the tail current through Cc, the other by the output stage into CL), so they differ. For the test design: rising ≈ 5.2 V/µs, falling ≈ 2.0 V/µs. The worst case is what limits the opamp in practice. **Check with `reference_designs.csv`**: if the TAs use only the rising edge, return `rates[0]` instead.

**Missing edge → 0 (added after test_6, section 5.1).** Some bad designs rise once and never come back down within the 30 µs simulation — the output cannot follow the 10 µs input pulse at all. The first version returned the slope of the one edge it found; ngspice `meas` found no result. Now, if either edge is missing, the function returns 0: the missing edge has effectively no slew rate, and the worst-case rule says the slower edge counts.

**Accuracy:** reference run with a 1 ns time step: 2.012 V/µs. Our value on the normal 50 ns step: 2.002 (ngspice 47) / 1.994 (ngspice 42) — within 1 %. The small difference between versions is because ngspice chooses its internal time steps differently. **For faster designs the 50 ns step matters much more — see section 5.2.**

---

## 5. The unit tests (test_dut.py)

Each test checks one link of the chain in section 1, so the first failing test shows where it breaks.

| Test | Checks | Why it passes |
|---|---|---|
| test_0 | CAD path has no spaces | ngspice breaks on paths with spaces |
| test_1 | `create_new_netlist` writes a netlist with the new sizes (`mp1=10`, `cap=5e-12`) | pure Python string editing (given code) |
| test_2 | ngspice exits without error | the circuit and analyses were already complete |
| test_3 | the 4 CSV files exist | the `wrdata` lines (section 3) |
| test_4 | all 7 specs are numbers | the `find_*` functions (section 4) |
| test_5 | specs match the TAs' `reference_designs.csv` within 5 % | skipped until the file is provided |
| test_6 | specs match an independent ngspice `meas` reference on 9 designs | section 5.1 |

Result for the test design (all tests pass):

```
area 2.041e-09   current 7.508e-05 A   gain 23.7 V/V   noise 0.001093 V
phm 80.88 deg    slewRate 2.002 V/us   ugbw 3.106e+06 Hz
```

These numbers are poor compared to the targets (gain 200, SR 15). That is not a bug — they are just example sizes. Finding good sizes is the RL agent's job.

test_4 only proves the specs *exist*, not that they are *correct*, and only for one design. The instructions ask for verification "across different sets of sizes" — that is test_6.

### 5.1 test_6 — correctness across several sizings (`TestCorrectness`)

**Idea:** for every design, measure the specs twice with methods that share no code, and require them to agree.

1. **Designs:** the `PARAMS` design + 8 random sizings, each parameter picked on the YAML grid (min, max, step). Fixed random seed (`RANDOM_SEED = 2026`) so the test is reproducible. Random designs are good here because they include *bad* designs (gain < 1, unstable, too slow) that check the guards, not only nice cases.
2. **Python side:** the normal pipeline — `create_new_netlist` → `simulate` → `measure_metrics`.
3. **Reference side** (`run_reference`): take the *same* generated netlist, keep the circuit, replace its `.control` block with `REFERENCE_CONTROL`, run ngspice and read the printed results. It uses ngspice's built-in `meas` commands and finer analyses:

| Spec | Reference | Tolerance | Why this tolerance |
|---|---|---|---|
| gain | `meas ac find vm(net6) at=1`, 1000 pts/decade | 0.1 % | same frequency point |
| current | `print -i(vdd)` after `op` | 0.1 % | same operating point |
| noise | `onoise_total` with 20 pts/decade | 1 % | integration grid 2× finer |
| ugbw | `meas ac when vm(net6)=1 fall=1`, 1000 pts/decade | 0.5 % | 100× finer sweep |
| phm | `180 + vp(net6)` at the reference UGBW | 0.5° | compared modulo 360°, because `vp()` wraps (section 4.3) |
| slewRate | `meas tran trig/targ` 10 %→90 % on both edges, **same 50 ns step** | 1 % | same data, different code — checks our method |

4. **No reference result** (ngspice finds no crossing: gain < 1 everywhere, or no complete edge) → Python must return exactly 0 for ugbw / phm / slewRate.
5. Prints a table and saves it to `no_backup/correctness_report.csv` (useful for the report).

**Result (all 9 designs pass):** gain, current, UGBW, PM and slew rate agree to 0.000 %/0.000°; noise to < 0.1 %. Four random designs have gain < 1 (no UGBW → Python 0, correct), one is nearly unstable (PM 2.5°), two cannot follow the input pulse (slew → 0, correct).

**Two things found while building it:**
- **ngspice's noise integration returns NaN** for some designs at 50+ points/decade (e.g. `random_4`), while 10 and 20 points/decade agree to 0.08 %. That is an ngspice numerical problem in the reference, so the reference uses 20. The course netlist's 10 points/decade gave no NaN in 120 random designs.
- **The missing-edge rule** in `find_slew_rate` (section 4.4) — the first version disagreed with ngspice on `random_6`/`random_7`.

Runtime: about 10 s for the whole test.

### 5.2 Open issue for the group: the 50 ns transient step

test_6 also runs the transient at 1 ns and reports `SR@1ns` (info only, not pass/fail). Our *method* is exact, but the *data* from `tran 50n 30u` (the course netlist) is too coarse for fast edges: a 10 %–90 % edge of a design with SR = 15 V/µs takes ~65 ns, i.e. only 1–2 samples, and interpolating between them underestimates the slope.

Survey over 120 random designs (small Cc, to get fast ones):

| True slew rate (1 ns step) | 50 ns step underestimates by (median) |
|---|---|
| 0–2 V/µs | 0 % |
| 2–5 V/µs | 2 % |
| 5–10 V/µs | 11 % |
| **10–20 V/µs (around the 15 V/µs target)** | **32 %** |
| > 20 V/µs | 67 % |

Consequence: a design that truly meets 15 V/µs can be reported as ~10 V/µs and be rejected; the RL agent would push for ~22 V/µs true slew rate, costing current and area.

Options:
- `tran 5n 30u` in `TwoStage.cir`: accurate, but a full simulation takes ~0.22 s instead of ~0.05 s (5k simulations: ~18 min instead of ~4 min, both fine).
- Keep 50 ns: matches the course template and probably the TAs' `reference_designs.csv`.

**Ask the TAs** which step their reference designs used before changing it. Whatever is chosen, mention it in the report: it is a good example of the unit test finding a real limitation.

---

## 6. For the report (milestone 1 section)

Required by the instructions: *describe the topology, explain how each spec is measured, prove correctness with the unit test.*

1. **Topology** — section 2 (table + input stimulus + why the DC phase is 0°).
2. **Simulations** — one line per analysis: transient ±0.6 V differential pulse → slew rate; AC 1 Hz–1 THz → gain, UGBW, PM; noise over the same band → total output noise; operating point → supply current. Area from the estimator.
3. **Each spec** — sections 4.1–4.4: definition, method, why (log-log, spline, unwrap, worst edge).
4. **Proof** — the unit test table (section 5) + test_6's comparison table (`no_backup/correctness_report.csv`) + the spline vs straight line table and the unstable-design example + test_5 against the TAs' references once available.
5. **Limitation** — the 50 ns transient step (section 5.2) and what you decided.

---

## 7. Quick reference: things that were confusing

- **"No graphics interface" / "Can't open display"** → interactive ngspice wants XQuartz. Use `env -u DISPLAY ngspice file.cir`. Not an issue for the Python code (batch mode).
- **"No job defined: run simulation not started"** → harmless; all analyses are defined inside `.control`.
- **"toxe, toxp and dtox…"** → warning from the 45 nm model file, harmless.
- **Why `dc_raw_outputs[1]` and `noise_raw_outputs[0]`** → section 3.4.
- **Why the current is negated** → section 3.3.
- **ResourceWarning in test_1** → the test opens a file without closing it; harmless.
