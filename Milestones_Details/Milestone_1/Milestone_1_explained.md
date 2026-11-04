# Milestone 1 — Simulator Interface: what was done and why

This document explains every decision made in milestone 1, so it can be studied and reused for the report. It describes the **final state** of the code; section 6 tells the story of how the reference comparison led to the final settings.

**Final settings at a glance**

| Setting | Value | Where | Why |
|---|---|---|---|
| Temperature | **27 °C** | `TwoStage.cir`: `.param temp_pvt=27` | Only temperature at which the TA reference designs are reproduced (section 6) |
| Transient step | **1 ns** | `TwoStage.cir`: `tran 1n 30u` | 50 ns underestimates fast slew rates by up to 73 % (section 5.2) |
| Slew rate | **rising edge, 10 % → 90 %** | `dut_testbench.py`: `find_slew_rate` | Definition used by the TA reference designs (section 4.4) |
| Targets | slew rate **30 V/µs**, UGBW **100 MHz** (others unchanged) | `TwoStage.yaml` | Same targets as the TAs' normalised specs (section 6.5) |

Files of this milestone:

| File | What it contains |
|---|---|
| `ngspice_interface/files/input_netlists/TwoStage.cir` | `wrdata` lines + `noise` command (filled in); 27 °C; 1 ns transient |
| `ngspice_interface/dut_testbench.py` | `find_dc_gain`, `find_ugbw`, `find_phm`, `find_slew_rate` (+ two helpers) |
| `ngspice_interface/ngspice_wrapper.py` | Setup only: use the local ngspice when the ESAT server path does not exist |
| `test_dut.py` | Unit tests 0–7 (section 5) |
| `compare_references.py` | Our specs vs. the TA reference designs at 27 °C and 25 °C → `Reference_Designs/comparison.csv/.png` |
| `plot_gain.py` | Gain vs. frequency of the reference designs at 27 °C and 25 °C → `Reference_Designs/gain_vs_frequency.csv/.png` |
| `Reference_Designs/references.csv` | The 5 TA reference designs (sizes, specs, actions, normalised specs, reward) |

---

## 1. The big picture: what milestone 1 is for

The project is an automatic opamp sizer. An optimiser (RL agent in milestone 3, LLM harness in milestone 4) proposes transistor sizes thousands of times. For each proposal, the code must answer: *how good is this opamp?* Milestone 1 builds that answer — the chain from "sizes in" to "specs out":

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

If a measurement is wrong here, the RL agent optimises the wrong thing and nothing later can fix it. That is why the instructions ask for a unit test as *proof* of correctness.

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

**Input stimulus.** One source `Vinput` (node `aid`) drives two voltage-controlled sources `ein1`/`ein2` with gains +0.5 / −0.5 on top of `VCM` = 0.6 V, so the opamp sees a differential input of exactly `v(aid)`. `Vinput` has:
- `ac=1.0` → in AC and noise analysis, `v(net6)` *is* the transfer function H(f).
- `PULSE(−VHIGH/2 → +VHIGH/2)` → in transient, a ±0.6 V differential step: large enough to slew the output.

**Sign of the gain.** `aid` → +0.5 → `net1` → gate of mn2 → drain `net5` (inverting) → gate of mp3 → `net6` (inverting). Two inversions → **non-inverting**, DC phase ≈ 0°. Used in the phase-margin calculation.

**Open loop.** There is no feedback in the testbench; all specs are open-loop. With a large step input the output swings almost rail-to-rail, which is what the slew-rate measurement needs.

**Multipliers in the YAML** (`mn1: 2`, `mp1: 2`): the parameter `mn1` sizes *two* transistors (mn1 and mn2), likewise `mp1`. The area estimator uses this.

---

## 3. The netlist: saving the simulation results

### 3.1 What was missing

The `.control` block is a script ngspice runs top to bottom. The analyses (`tran`, `ac`, `op`) were already there, but nothing *saved* their results; ngspice threw them away on exit. That is why test_2 (simulation runs) passed but test_3 (output files exist) failed.

### 3.2 The final `.control` block

```spice
* transient analysis
tran 1n 30u
wrdata tran_TwoStage.csv v(net6)

* ac analysis
ac dec 10 1 1T
wrdata ac_TwoStage.csv v(net6)

* noise analysis
noise v(net6) vinput dec 10 1 1T
wrdata noise_TwoStage.csv onoise_total

* dc analysis
op
wrdata dc_TwoStage.csv i(vdd)
```

and in the parameters: `.param temp_pvt=27` (used by `.temp {temp_pvt}`).

### 3.3 Why each line

- **`v(net6)`** — `net6` is the output node (drain of mp3/mn5, where CL is).
- **`wrdata`** writes vectors as plain text columns; the x-axis (time, frequency) comes first; a complex vector (AC) gives two columns, real and imaginary. `set wr_vecnames` (already in the netlist) adds a header line → `parse_outputs()` uses `skip_header=1`.
- **`noise v(net6) vinput dec 10 1 1T`** — syntax `noise v(output) <input source> <sweep>`. `vinput` is the source with `ac=1`. Same sweep as AC. It produces `noise1` (spectral density) and `noise2` (integrated); **`onoise_total`** in `noise2` is the total RMS output noise in V — the spec.
- **`i(vdd)`** — current through the supply source `vdd`. ngspice counts current flowing *into* the + terminal as positive; a supply delivers current *out*, so `i(vdd)` is negative. Hence `self.current = - dc_raw_outputs[1]` in the given parser.
- **`tran 1n 30u`** (was `tran 50n 30u` in the template) — see section 5.2. `tran 50n 30u 0 1n` (50 ns output step, 1 ns maximum internal step) was also tried: ngspice writes every internal step, so it gives the same ~30 000 points and identical results, and was not faster (1.16 s vs 1.01 s per simulation). `tran 1n 30u` is simpler to read.
- **`temp_pvt=27`** (was 25 in the template) — see section 6.

Cost of the 1 ns step: a full simulation takes ~1.0–1.2 s instead of ~0.05 s → 5k simulations ≈ 1.5 h. Start the milestone 3 runs early.

### 3.4 Rules the lines must follow (from the wrapper code)

1. **`wrdata` at the start of the line.** `create_new_netlist()` only rewrites lines where `line.startswith("wrdata")`.
2. **File name `<kind>_TwoStage.csv`, no folder.** The wrapper finds it with the regex `wrdata (\w+)\.csv`, keeps the part before the first `_` and rewrites it to `no_backup/output_files/<kind>_<random_name>.csv` — a unique name per simulation.
3. **One vector per file**, because `parse_outputs()` reads fixed columns:

| File | Columns written | Parser reads | Why |
|---|---|---|---|
| tran | `time  v(net6)` | `[:,0]`, `[:,1]` | |
| ac | `frequency  Re  Im` | `[:,0]`, `[:,1]`, `[:,2]` | complex → 2 columns |
| dc | `net4  i(vdd)` | `[1]` | `op` has no x-axis; ngspice uses the first node (`net4`, shown as `[default scale]` by `display`) as column 0 |
| noise | `onoise_total  onoise_total` | `[0]` | no x-axis either; the value is written twice |

### 3.5 How it was checked by hand

`env -u DISPLAY ngspice ngspice_interface/files/input_netlists/TwoStage.cir` (from `CAD/`), then `display`, `setplot`, `setplot noise2`, `print onoise_total`: all result sets exist (`tran1`, `ac1`, `noise1`, `noise2`, `op`), and the four CSVs have the column layout above. `env -u DISPLAY` is only needed for *interactive* ngspice on the Mac (it otherwise tries to open an XQuartz window); batch mode (`-b`), used by Python, is not affected.

---

## 4. The measurements (dut_testbench.py)

Input data for every function:

| Name | What | Size |
|---|---|---|
| `freq` | AC frequencies 1 Hz → 1 THz, 10 per decade | 121 |
| `vout` | complex `v(net6)` = H(f), since the input is `ac=1` | 121 |
| `time`, `signal` | transient time and `v(net6)` | ~30 000 (1 ns step) |

Area, current and noise need no new function (area: `area_estimation.py`; current and noise: read straight from the CSVs).

### 4.1 DC gain — `find_dc_gain`

```python
return float(np.abs(vout)[0])
```
- Magnitude of H at the first AC point (1 Hz). The dominant pole is at kHz or higher, so the gain curve is flat at 1 Hz (visible in `gain_vs_frequency.png`).
- **V/V, not dB:** the target `gain: 200` only makes sense in V/V (≈ 46 dB).

### 4.2 Unity-gain bandwidth — `find_ugbw`

**Definition:** the first frequency where |H(f)| = 1 (0 dB).

**Problem:** with 10 points/decade, neighbouring points are 26 % apart; the crossing almost never lands on a sample.

**Method:**
1. `_first_unity_crossing`: first index `i` with |H| < 1; the crossing lies between `i-1` and `i`.
2. `_local_window`: 3 points on each side.
3. Cubic spline of **log10|H| vs log10 f**, solve log10|H| = 0 with a root finder — the helper `_get_best_crossing` that was already in the file (scipy spline + `brentq`).
4. If the spline fails: straight line between the two bracketing points.

**Why log-log:** near the crossing, log|H| vs log f is close to a straight line (−20 dB/decade); in linear axes it is strongly curved.

**Why a spline (tested, not assumed)** — 27 random designs vs. a 1000-points/decade ngspice reference:

| Method on the normal 10 points/decade | median error | worst error |
|---|---|---|
| straight line in log-log | 0.08 % | 0.81 % |
| **cubic spline in log-log (chosen)** | 0.000 % | 0.002 % |
| ngspice `meas ... when vm(net6)=1` on the same coarse sweep | ~0.3 % | — |

**Why only a local window:** a spline over all 121 points could lock onto a *later* crossing on designs with gain peaking.

**Guards:** gain never above 1 → `0`; never below 1 within the sweep → last frequency. Bad designs get a bad number, not a crash.

**Rejected alternative — the −3 dB bandwidth** (e.g. `python-control`'s `bandwidth()`): that is where the gain drops to 0.707 × DC gain, i.e. the dominant pole, not UGBW. For a dominant-pole opamp UGBW ≈ A0 × f₋₃dB, so it would under-estimate the speed by the gain factor. It also needs an analytic model, while we only have samples.

### 4.3 Phase margin — `find_phm`

**Definition:** PM = 180° + ∠H(f) at f = UGBW. Below 0 → oscillates in unity feedback.

**Method:**
1. Phase in degrees, **unwrapped** (`np.unwrap`): `np.angle` only returns (−180°, 180°], so a phase past −180° would jump to +180°.
2. Shift by whole turns of 360° so the DC phase is near 0° (non-inverting circuit, section 2).
3. Phase at the UGBW from a cubic spline over the same local window as 4.2.
4. No unity crossing → 0.

**Why the unwrap is essential:** two random designs were unstable (phase −242° and −216° at the UGBW). Our code gives PM = −62° and −36° (correct). ngspice's `vp()` wraps the phase and gives 298° and 324° — "excellent" phase margin. Without unwrapping, the RL agent would be rewarded for unstable designs.

### 4.4 Slew rate — `find_slew_rate`

**Definition:** the rate of change of the output for a large input step, limited by how fast the bias currents charge Cc and CL.

**Method (final):**
1. Output swing: `vmin`, `vmax` of the transient output.
2. Levels: V10 = vmin + 0.1·swing, V90 = vmin + 0.9·swing.
3. **Rising edge:** first upward crossing of V10, then the first upward crossing of V90 after it.
4. Crossing times linearly interpolated between samples.
5. SR = (V90 − V10) / (t90 − t10), in V/µs.
6. No complete rising edge (output does not follow the input) → 0.

**Why 10 %–90 %:** the start and end of the edge are rounded (settling, not slewing); the middle 80 % is the linear slewing part.

**Why the rising edge only.** In a Miller opamp the two edges are limited by different currents (tail current through Cc vs. output stage into CL), so they differ — reference design 1: rising 73 V/µs, falling 20 V/µs. The first version returned the *slower* edge (worst case). The TA reference designs turned out to use the **rising edge only** (0.000 % difference on all 5 designs with rising edge + 1 ns step), and the reference defines the spec. Worth one sentence in the report: the falling edge can be much slower.

**Tested explicitly** (test_7, section 5): synthetic waveforms with known slopes — rising 10 V/µs with a slower falling edge → 10; rising 2.5 V/µs with a faster falling edge → 2.5; a 0.2 → 1.0 V edge → slope from the 10–90 % levels of the swing; no rising edge → 0.

---

## 5. The unit tests (test_dut.py)

Run from `CAD/`: `python -m unittest test_dut -v` (≈ 30–40 s; the 1 ns transient is the slow part). Each test checks one link of the chain in section 1.

| Test | Checks | Why it passes |
|---|---|---|
| test_0 | CAD path has no spaces | ngspice breaks on paths with spaces |
| test_1 | `create_new_netlist` writes the new sizes (`mp1=10`, `cap=5e-12`) | pure Python string editing (given code) |
| test_2 | ngspice exits without error | circuit and analyses were complete |
| test_3 | the 4 CSV files exist | the `wrdata` lines (section 3) |
| test_4 | all 7 specs are numbers | the `find_*` functions (section 4) |
| test_5 | specs match the 5 TA reference designs within 5 % (at 27 °C) | section 6 — worst difference 0.13 % |
| test_6 | specs match an independent ngspice `meas` reference on 9 designs | section 5.1 |
| test_7a–d | slew rate = rising edge, 10–90 %, 0 if no rising edge | section 4.4 |

Result for the test design (27 °C, 1 ns step):

```
area 2.041e-09   current 7.507e-05 A   gain 23.57 V/V   noise 0.00109 V
phm 80.70 deg    slewRate 5.441 V/us   ugbw 3.081e+06 Hz
```

Poor compared to the targets — they are just example sizes; finding good sizes is the RL agent's job.

### 5.1 test_6 — correctness across several sizings (`TestCorrectness`)

**Idea:** measure every spec twice with methods that share no code, and require them to agree.

1. **Designs:** the `PARAMS` design + 8 random sizings on the YAML grid, fixed seed (`RANDOM_SEED = 2026`). Random designs include *bad* ones (gain < 1, nearly unstable, too slow), which test the guards.
2. **Python side:** the normal pipeline.
3. **Reference side** (`run_reference`): the *same* generated netlist, with its `.control` block replaced by `REFERENCE_CONTROL` — ngspice's built-in `meas` commands and finer analyses. The transient line is copied from the netlist, so the reference always uses the same step as the code.

| Spec | Reference | Tolerance | Why |
|---|---|---|---|
| gain | `meas ac find vm(net6) at=1`, 1000 pts/decade | 0.1 % | same frequency point |
| current | `print -i(vdd)` after `op` | 0.1 % | same operating point |
| noise | `onoise_total`, 20 pts/decade | 1 % | integration grid 2× finer |
| ugbw | `meas ac when vm(net6)=1 fall=1`, 1000 pts/decade | 0.5 % | 100× finer sweep |
| phm | `180 + vp(net6)` at the reference UGBW | 0.5° | compared modulo 360° (`vp()` wraps, section 4.3) |
| slewRate | `meas tran trig/targ`, 10 %→90 %, rising edge, same transient | 1 % | same data, different code |

4. **No reference result** (gain < 1 everywhere, no complete edge) → Python must return exactly 0.
5. Table printed and saved to `no_backup/correctness_report.csv`.

**Result:** all 9 designs pass; gain, current, UGBW, PM, slew rate agree to 0.000 %/0.000°, noise to < 0.1 %.

**Found while building it:**
- ngspice's noise integration returns NaN for some designs at 50+ points/decade, while 10 and 20 agree to 0.08 % → the reference uses 20. The course netlist's 10 points/decade gave no NaN in 120 random designs.
- ngspice versions can differ on bad designs: `random_0` gives gain 6.8 with ngspice 42 but 4·10⁻¹⁰ with ngspice 47 (Mac) — the two settle into different DC operating points for this poorly sized circuit. The test still passes (both sides measure the same simulation).

### 5.2 The transient step: 50 ns → 1 ns

An earlier version of test_6 also ran the transient at 1 ns. Our *method* was exact, but the template's `tran 50n 30u` is too coarse: a 10–90 % edge at 15 V/µs takes ~65 ns, i.e. 1–2 samples, and interpolating between them underestimates the slope.

Survey over 120 random designs (small Cc, to get fast ones):

| True slew rate (1 ns step) | 50 ns step underestimates by (median) |
|---|---|
| 0–2 V/µs | 0 % |
| 2–5 V/µs | 2 % |
| 5–10 V/µs | 11 % |
| 10–20 V/µs | 32 % |
| > 20 V/µs | 67 % |

On the TA reference designs (rising edge), the slew rate error is −73 % (design 1, 72 V/µs) at 50 ns, −12 % at 5 ns, −1.7 % at 2 ns and **0.000 % at 1 ns** on all 5 designs → `tran 1n 30u`.

---

## 6. The temperature: why 27 °C

This is the part that took the longest, so it is described step by step. It is also a good "debugging story" for the report.

### 6.1 The symptom

First comparison with `Reference_Designs/references.csv`, using the template settings (25 °C):
- **Area: 0.000 %** on all 5 designs → the sizes are read and used correctly.
- **Everything else off by a small, consistent amount:** gain, UGBW, noise 1–2 % on designs 2–5; **design 1: gain −7.8 %, noise −7.7 %**, above the 5 % limit.

### 6.2 The key observation: every analysis shifts together

Each spec at 25 °C and 27 °C, compared with the reference (design 1, worst case):

| Spec | Comes from | 25 °C | 27 °C |
|---|---|---|---|
| current | operating point | +0.59 % | 0.000 % |
| gain | AC | −7.84 % | 0.000 % |
| UGBW | AC | +1.53 % | +0.015 % |
| phase margin | AC | −0.67 % | −0.014 % |
| noise | noise analysis | −7.74 % | +0.011 % |
| slew rate | transient | +1.26 % | 0.000 % |

Over all 5 designs and 7 specs (1 ns step, rising edge): **27 °C → 35/35 within 5 %, worst 0.13 %; 25 °C → 33/35, worst 7.8 %** (`comparison.png`).

Why this rules out a bug in our code:
- A bug in one `find_*` function would affect **one** spec. Here all four analyses (op, AC, noise, transient) shift together, which is what a different *simulation condition* does.
- The **supply current is not processed by our code at all** — it is the value ngspice writes for `i(vdd)`, only negated. It is still +0.59 % off at 25 °C and exact at 27 °C. No Python change can move it.
- test_6 shows that our measurements agree with ngspice's own `meas` commands to 0.000 % on 9 designs, and `gain_vs_frequency.png` shows the gain curve is flat at 1 Hz — the DC gain is read at the right place; at 25 °C the *whole plateau* sits lower.

Why design 1 is the most sensitive: it has the highest gain (817 V/V). The gain is a product of transconductances and output resistances, each of which changes slightly with temperature, so a 2 °C shift moves a high-gain design the most.

### 6.3 Hypotheses ruled out

| Hypothesis | Test | Result |
|---|---|---|
| A measurement bug | test_6 (ngspice `meas`), gain plot | measurements exact; all analyses shift together |
| Model nominal temperature (`TNOM`): ngspice prints "TEMP = 25, TNOM = 27" | `.options tnom=25` | no effect — the model files fix `tnom = 27` inside the transistor models |
| Transient step | 50 / 10 / 5 / 2 / 1 ns | only affects the slew rate, not gain/noise/current |
| Slew-rate definition | rising / falling / slower edge / maximum slope | only affects the slew rate |

### 6.4 Where 27 °C comes from

The course code itself uses 27 °C in two places, while only the netlist template said 25:
- `circuit_env.py`, line 63: `self.pvt_corner = {'process': 'TT', 'voltage': 1.2, 'temp': 27}`
- `ngspice_wrapper.py`, `__main__` example: `temp_pvt = 27`

27 °C is also ngspice's default nominal temperature. `references.csv` contains actions, normalised specs and rewards — what the RL environment produces — so the references were most likely generated through the environment, which passes `temp_pvt=self.pvt_corner['temp']` (27) to `create_new_netlist` and overrides the netlist's 25.

### 6.5 The targets in the reference file

The normalised specs in `references.csv` use `(spec − target) / (spec + target)`. Solving for the target gives **slew rate 30 V/µs** and **UGBW 1·10⁸ Hz** (e.g. design 1: norm_ugbw 0.4845 with UGBW 287.9 MHz → target 100.0 MHz), and gain 200, noise 0.03 as before. `TwoStage.yaml` was updated to these values. This is useful for milestone 2: the `norm_*` and `reward` rows are reference values for `circuit_env.py`.

### 6.6 Decision and open point

- **Decision:** `TwoStage.cir` uses **27 °C**. It is the only temperature at which our pipeline reproduces the TA reference designs, and it is the temperature of `circuit_env.py`'s `pvt_corner`, so milestones 1 and 2 are consistent.
- **Open point:** the TAs said the temperature should stay at 25 °C and that a difference above 5 % means a code issue. With the evidence above, no code issue could be found: the difference is in the simulation condition, including a value (the supply current) our code does not touch. Bring the comparison plot and table 6.2 to the TAs and ask whether the reference designs were generated with `pvt_corner['temp'] = 27`.
- If the answer is "use 25 °C anyway": change `.param temp_pvt` back to 25 and `TEMP` in `test_dut.py` to 25; test_5 will then fail on design 1 gain and noise (−7.8 %), which can be explained in the report with section 6.2.

### 6.7 The comparison tools

- **`python compare_references.py`** → `Reference_Designs/comparison.csv` (reference, value and % difference at 27 °C and 25 °C, within ±5 % yes/no) and `comparison.png` (% difference per spec and design, ±5 % band; blue 27 °C, orange 25 °C).
- **`python plot_gain.py`** → `Reference_Designs/gain_vs_frequency.png` (|H(f)| of each reference design at 27 °C solid and 25 °C dashed, reference DC gain and UGBW as diamonds) and `gain_vs_frequency.csv` (all 121 frequency points per design and temperature).

---

## 7. For the report (milestone 1 section)

Required by the instructions: *describe the topology, explain how each spec is measured, prove correctness with the unit test.*

1. **Topology** — section 2.
2. **Simulations** — transient ±0.6 V differential pulse, 1 ns step → slew rate; AC 1 Hz–1 THz → gain, UGBW, PM; noise over the same band → total output noise; operating point → supply current; area from the estimator. All at 27 °C.
3. **Each spec** — section 4: definition, method, why (log-log, spline, unwrap, rising edge).
4. **Proof** — unit test table (section 5); test_6 table (`no_backup/correctness_report.csv`); spline vs straight line table; unstable-design example; `comparison.png` (35/35 reference values within 0.13 %).
5. **Debugging story** — section 5.2 (time step) and section 6 (temperature): how the reference comparison exposed two simulation settings, how hypotheses were tested one at a time, and why the supply current proves it is not a measurement bug.

---

## 8. Quick reference: things that were confusing

- **"No graphics interface" / "Can't open display"** → interactive ngspice wants XQuartz. Use `env -u DISPLAY ngspice file.cir`. Batch mode (Python) is not affected.
- **"No job defined: run simulation not started"** → harmless; analyses are defined inside `.control`.
- **"toxe, toxp and dtox…"** → warning from the 45 nm model file, harmless.
- **"TEMP = 25.000000 and TNOM = 27.000000"** → simulation temperature vs. the models' nominal temperature (section 6.3).
- **Why `dc_raw_outputs[1]` and `noise_raw_outputs[0]`** → section 3.4. **Why the current is negated** → section 3.3.
- **ResourceWarning in test_1** → the test opens a file without closing it; harmless.
- **A file goes back to an old version after it was changed** → an open VS Code tab saved its old contents over it. Close the tab with **Don't Save** (or Cmd+Shift+P → "File: Revert File") before running, and keep Auto Save off while files are edited from outside.
- **Leftover `*_TwoStage.csv` in `CAD/`** → created by running ngspice by hand on the template; delete them (not covered by `.gitignore`).
