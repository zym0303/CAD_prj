# Milestone 2 — The Circuit Environment, explained

This document walks through every TODO in `circuit_env.py`: what it has to do, why, the best way to write it, and the traps to avoid. Methods that are already implemented in `circuit_env.py` include the actual code and the checks it passed; the others give the reasoning, formulas and structure.

**Status**

| Method | Status |
|---|---|
| `action_refine` | ✅ implemented, matches the TA reference designs exactly |
| `normalize_specs` | ✅ implemented and verified |
| `reward_computation` | ✅ implemented and verified |
| `simulate` | ✅ implemented and verified (failure path + real ngspice run on the Mac) |
| `reset` (+ `_get_obs` helper) | ✅ implemented and verified (mocked simulator) |
| `step` | ✅ implemented and verified (mocked simulator) |
| full run `python circuit_env.py` | ✅ verified on the Mac (real ngspice) |
| unit test file `test_circuit_env.py` | ✅ 28 tests, all pass on the Mac (incl. end-to-end with real ngspice) |

**Targets used in this project** (from `TwoStage.yaml`, deliberately stricter than the slides): gain ≥ 200, noise ≤ 30 mVrms, phase margin ≥ 60°, **slew rate ≥ 30 V/µs**, **UGBW ≥ 100 MHz**; area target 2e-9 m², current target 200 µA. The code reads everything from the YAML, so changing a target never requires changing Python.

---

## 0. The big picture: what the environment is

In RL there are two players: the **agent** (TD3, Milestone 3) and the **environment** (this file). The agent never sees transistors or ngspice. It only sees numbers:

```
           action a ∈ [-1,1]^20                       observation s ∈ R^7, reward r
 TD3  ───────────────────────────►  CircuitEnv  ─────────────────────────────────►  TD3
                                       │
                                       │ action_refine → real sizes (W, L, m, Cc, Rc)
                                       │ simulate      → netlist → ngspice → specs
                                       │ normalize     → s = [z_area, z_current, z_gain, ...]
                                       │ reward        → FoM
```

So the environment is a **translator** in both directions:

| Direction | Method | From | To |
|---|---|---|---|
| Agent → circuit | `action_refine` | 20 numbers in [-1, 1] | 20 real parameter values on the YAML grid |
| Circuit → simulator | `simulate` | parameter dict | measured specs dict (M1 code) |
| Simulator → agent | `normalize_specs` | specs with very different units | 7 numbers of similar magnitude |
| Simulator → agent | `reward_computation` | normalized specs | one scalar FoM |
| Episode control | `reset`, `step` | — | gym-style API used by `td3_runner.py` |

`evaluate(action)` (already written) simply chains the first three:

```python
self.param_values   = self.action_refine(action)
self.real_specs     = self.simulate(self.param_values)
self.cur_norm_specs = self.normalize_specs(self.real_specs)
```

Keep in mind the **API contract** that `td3_runner.py` expects (it is *not* the modern gymnasium API):

```python
obs = env.reset()                              # returns ONLY the observation
next_state, reward, done, info = env.step(a)   # returns a 4-tuple
```

---

## 1. `action_refine(action)` — from [-1, 1] to real sizes

### What it must do
The TD3 actor ends with a `tanh`, so it outputs 20 numbers in [-1, 1]. The netlist needs real values such as `wp1 = 1.5e-6`, `mn3 = 7`, `cap = 2.3e-12`. `action_refine` builds that mapping.

### Why normalize actions at all?
The parameters span wildly different scales (L ≈ 1e-7 m, C ≈ 1e-12 F, R ≈ 1e3 Ω, m ≈ 10). A neural network trains well only if all outputs live on the same scale, so the agent works in a unit hypercube and the environment does the unit conversion. Same idea as normalizing inputs in any ML problem.

### The parameter grid
Every parameter in `TwoStage.yaml` has `(min, max, step)`. The allowed values are built exactly like in the TA code, with `np.arange(min, max, step)`. **`np.arange` excludes `max`**, so the grids are:

| Parameter type | YAML (min, max, step) | grid = `np.arange(...)` | N (# values) |
|---|---|---|---|
| multipliers `m*` | 1, 25, 1 | 1, 2, …, 24 | 24 |
| widths `w*` | 0.25 µm, 3.0 µm, 0.25 µm | 0.25 … 2.75 µm | 11 |
| lengths `l*` | 45 nm, 225 nm, 45 nm | 45, 90, 135, 180 nm | 4 |
| `cap` (Cc) | 0.1 pF, 10 pF, 0.1 pF | 0.1 … 9.9 pF | 99 |
| `res` (Rc) | 0 Ω, 9.9 kΩ, 100 Ω | 0 … 9.8 kΩ | 99 |

The step is not decoration: it represents what is actually manufacturable/meaningful (lengths in multiples of the 45 nm node, integer multipliers). So the refined value must be **on the grid**, not just in the range.

### Why this exact convention? The TA reference designs
`Reference_Designs/references.csv` gives, for 5 designs, both the **action** vector (`action_*`) and the resulting **sizes** (`param_*`). So it defines what `action_refine` must return. A first version of our function used a different (also reasonable) convention: grid including `max` and rounding to the nearest value. It reproduced only 1 parameter out of 20. For example, action 0.7 for `wp1` gave 2.5 µm, while the reference is 2.25 µm. Fitting the reference data shows the TA convention is:

- grid = `np.arange(min, max, step)` (N values, max excluded),
- index = `floor((a + 1)/2 · (N − 1))`, i.e. round **down**.

Every reference action is exactly the centre of a bin (e.g. (a+1)/2·(N−1) = 5.5 → index 5), which is how you can tell the TAs round down: rounding to nearest would give 6. With this convention all **100** reference parameters (5 designs × 20) are reproduced exactly.

Matching the TA convention matters for two reasons: the unit test can use the reference designs as an independent oracle, and in Milestone 3 our agent is compared to the TA baseline agent, which must search the same design space.

### The mapping (step by step)
For each parameter i:

1. **Clip** `a_i` to [-1, 1]. The actor output is in range, but TD3 adds Gaussian exploration noise *after* the `tanh`, so a + noise can be e.g. 1.17. Also replace NaN with 0 for safety.
2. **Build the grid**: `grid = np.arange(min, max, step)`, N = `len(grid)`.
3. **Bin index**: `k = floor((a + 1)/2 · (N − 1))`, clamped to `0 … N−1`.
4. **Real value**: `v = grid[k]`.

Geometrically, [-1, 1] is cut into N − 1 equal bins; bin k gives grid value k. The last grid value is reached only at a = +1 exactly. That's less exotic than it sounds: every action pushed beyond +1 by the exploration noise is clipped to exactly +1.

Examples (verified):

| action | mp1 | wp1 | lp1 | cap | res |
|---|---|---|---|---|---|
| −1 | 1 | 0.25 µm | 45 nm | 0.1 pF | 0 Ω |
| 0 | 12 | 1.5 µm | 90 nm | 5.0 pF | 4.9 kΩ |
| +1 | 24 | 2.75 µm | 180 nm | 9.9 pF | 9.8 kΩ |
| +2 (clipped) | 24 | 2.75 µm | 180 nm | 9.9 pF | 9.8 kΩ |
| TA design 1 (action 0.7 for wp1) | 6 | 2.25 µm | 135 nm | 0.8 pF | 9.5 kΩ |

### Why use `np.arange` itself instead of a formula?
`np.arange` with float steps decides the number of values from a floating-point division, which can be off by one near the end. Using the same function as the TA code guarantees the same grid, so the same N, so the same mapping. A hand-written formula for N could silently disagree for one parameter.

### Two small but important details
- **Integers stay integers.** The multipliers are written into the netlist as `m=...`; writing `m=7.0` may work in ngspice, but `7` is cleaner and the area estimator multiplies by it. The code detects integer ranges by checking that `min`, `max` and `step` are Python `int`s in the YAML (more robust than relying on the name starting with `m`).
- **Float clean-up.** Grid values like `3 * 2.5e-7` are `7.500000000000001e-07` in floating point. That string ends up in the netlist and in the solutions CSV. Formatting to 7 significant digits (`float(f"{v:.6e}")`) gives `7.5e-07`.

### Order matters
`zip(action, self.param_ranges.items())` relies on the dictionary keeping the YAML order (guaranteed since Python 3.7). Action index 0 is therefore always `mp1`, index 1 `wp1`, and so on. This is also the column order of `action_*` in the reference file. If this order ever changed between runs, the agent's learned policy would be meaningless.

### Implementation

```python
def action_refine(self, action):
    action = np.asarray(action, dtype=np.float64).flatten()
    if action.shape[0] != self.n_actions:
        raise ValueError(f"Expected action of length {self.n_actions}, got {action.shape[0]}")

    # NaN -> 0 (centre of the range), then clip to the valid action interval
    # (the actor's tanh output + exploration noise can leave [-1, 1])
    action = np.clip(np.nan_to_num(action, nan=0.0), -1.0, 1.0)

    params = {}
    # self.param_ranges keeps the YAML order, so action[i] always maps to the same parameter
    for a, (name, rng) in zip(action, self.param_ranges.items()):
        p_min, p_max, p_step = rng['min'], rng['max'], rng['step']

        grid = np.arange(p_min, p_max, p_step)                  # allowed values (max excluded)
        k = int(np.floor((a + 1.0) / 2.0 * (len(grid) - 1)))    # bin index
        k = min(max(k, 0), len(grid) - 1)                       # safety clamp
        value = grid[k]

        if all(isinstance(x, int) for x in (p_min, p_max, p_step)):
            params[name] = int(value)                           # multipliers mp1, mn1, ...
        else:
            params[name] = float(f"{value:.6e}")                # 7.500000000000001e-07 -> 7.5e-07

    return params
```

### What to say in the report
"The actor outputs a ∈ [-1,1]^20. Each component is clipped and mapped onto the grid of allowed values of its parameter, `np.arange(min, max, step)` (N values): [-1, 1] is divided into N − 1 equal bins and bin k selects grid value k, i.e. k = ⌊(a+1)/2 · (N−1)⌋. Multipliers are kept integer. This convention reproduces all 5 TA reference designs exactly." Add the example table above.

---

## 2. `simulate(params)` — run the circuit

### What it must do
Take the parameter dict, produce a netlist, run ngspice, and return the spec dict `{'area', 'current', 'gain', 'noise', 'phm', 'slewRate', 'ugbw'}`. All the hard work was done in Milestone 1; here you only **orchestrate** it.

### Structure
`self.simulation_engine` is a `DUT` object (subclass of `NgspiceWrapper`, created once in `__init__`). Three calls:

1. `netlist_path = self.simulation_engine.create_new_netlist(params, process=self.pvt_corner['process'], temp_pvt=self.pvt_corner['temp'], vdd=self.pvt_corner['voltage'])`
   - this copies `TwoStage.cir`, overwrites the `.param` values, sets the model file (`p045_TT.sp`) and gives the output files a unique random name.
2. `info = self.simulation_engine.simulate(netlist_path)` → `0` = ok, `1` = ngspice failed.
3. `specs = self.simulation_engine.measure_metrics()` → parses the `.csv` files and computes the specs.

Passing the PVT corner from `self.pvt_corner` (instead of hard-coding `'TT'`) costs nothing now and makes the optional PVT-robust task much easier later.

### The important part: failures
With random sizes, some simulations *will* fail. If `simulate` crashes, a 10 000-step training run dies at step 3 700. So a failure must become a **bad reward** ("don't go there"), never an exception.

### What can actually fail, given our Milestone 1 code
Our `dut_testbench.py` is already defensive: for a design with no unity-gain crossing it returns UGBW = 0 and PM = 0, and for an output that never rises it returns slew rate = 0, instead of crashing. Those designs are therefore *not* failures: they get real (bad) numbers, which normalize to −1. What remains:

| Failure | How it shows up |
|---|---|
| ngspice crashes / does not converge | output `.csv` files missing → `np.genfromtxt` raises `FileNotFoundError` |
| ngspice writes an empty or truncated file | `IndexError` when slicing `[:, 0]` |
| ngspice killed by a signal | `engine.simulate` returns `info = 1` |
| anything unexpected in our measurement code | any other exception |

One subtle point: `NgspiceWrapper.simulate` checks `exit_code % 256`. `os.system` returns the exit code shifted left by 8 bits (exit code 1 → 256), so `% 256` is 0 for a normal non-zero exit; it only detects a process killed by a signal. A "normal" ngspice error is therefore *not* reported through `info`; it shows up one step later as missing output files. That's why catching exceptions around `measure_metrics` is essential, and checking `info` alone would not be enough.

### Design decisions in the implementation

**1. One `try/except` around all three steps.** Any exception, from any of the three calls, means "this design could not be evaluated". Catching `Exception` (not a bare `except:`) still lets you stop a run with Ctrl+C.

**2. A failed design gets NaN, not made-up numbers.** Instead of inventing values like "gain = 0, noise = 1e3", every measured spec is set to `NaN` ("not measured"). `normalize_specs` already maps NaN to the worst value of each spec (§3), so that logic lives in one place. Area is still computed with `BPTM45nmAreaEstimator`, because it only needs the sizes, not ngspice.

**3. The resulting reward.** Every hard constraint at its worst gives r_H = −5 (five constraints × −1), so a failed design gets FoM ≈ −5 (checked: −5.05 for the mid-range design). That is lower than any design that actually simulates, which is exactly the signal we want.

**4. Count and report failures.** `self.n_failed_sims` (initialized to 0 in `__init__`) is incremented on every failure, and a one-line warning is printed. At the end of training you can report e.g. "12 of 5000 simulations failed".

**5. Plain floats, fixed order.** `float(specs[name])` converts numpy scalars, so the solutions CSV contains `0.0123` instead of `np.float64(0.0123)`. Looping over `self.dict_targets` returns the keys in the same fixed order as everywhere else.

**6. The PVT corner comes from `self.pvt_corner`.** Process (model file `p045_TT.sp`), temperature (`.param temp_pvt`) and supply (`.param VDD`) are passed through, so the optional PVT-robust task only needs to change `self.pvt_corner`.

### Implementation

```python
# at the top of circuit_env.py
from ngspice_interface.area_estimation import BPTM45nmAreaEstimator

# in __init__
self.n_failed_sims = 0     # number of simulations that crashed (see simulate)

def simulate(self, params):
    engine = self.simulation_engine
    try:
        netlist_path = engine.create_new_netlist(
            params,
            process=self.pvt_corner['process'],
            temp_pvt=self.pvt_corner['temp'],
            vdd=self.pvt_corner['voltage'],
        )
        info = engine.simulate(netlist_path)
        if info != 0:
            raise RuntimeError("ngspice exited with an error")
        specs = engine.measure_metrics()
    except Exception as err:
        self.n_failed_sims += 1
        print(f"[simulate] simulation failed ({type(err).__name__}: {err}) "
              f"-> worst-case specs (failed so far: {self.n_failed_sims})")
        return self._failed_specs(params)

    # plain Python floats (numpy scalars print badly in the solutions CSV)
    return {name: float(specs[name]) for name in self.dict_targets}

def _failed_specs(self, params):
    """Spec dict for a design whose simulation failed: real area, NaN for everything measured."""
    specs = {name: float('nan') for name in self.dict_targets}
    try:
        specs['area'] = float(
            BPTM45nmAreaEstimator(params, self.simulation_engine.circuit_multipliers).find_area())
    except Exception:
        pass   # stays NaN -> normalize_specs gives it the worst value
    return specs
```

**7. Count every simulation.** `self.n_simulations += 1` at the start of `simulate` counts *every* ngspice run, including the one done by `reset` (see §4 for why that matters).

### Verified
- **Failure path** (tested on a machine without ngspice): the missing output file raised `FileNotFoundError`, which was caught. Result: area = 2.14e-9 (real), all other specs NaN → normalized to the worst values → reward **−5.05**, `hard_satisfied = False`, `n_failed_sims = 1`. No crash. ✅
- **Normal path** (Mac, Homebrew ngspice), on the design that the *first* version of `action_refine` produced for all actions = 0 (m = 13, W = 1.75 µm, L = 135 nm, …). The sizes are different with the final convention, but this check is about specs → reward, which doesn't depend on the mapping: ✅

| Spec | Measured | Target | z | Contribution to r_H |
|---|---|---|---|---|
| gain | 38.6 | ≥ 200 | −0.677 | −0.677 |
| noise | 0.67 mVrms | ≤ 30 mVrms | −0.957 | 0 (met) |
| phm | 86.6° | ≥ 60° | +0.181 | 0 (met) |
| slewRate | 5.81 V/µs | ≥ 30 | −0.676 | −0.676 |
| ugbw | 3.45 MHz | ≥ 100 MHz | −0.933 | −0.933 |
| area | 2.14e-9 m² | 2e-9 | o = +0.034 | r_T: −0.034 |
| current | 76.2 µA | 200 µA | o = −0.448 | r_T: +0.448 |

r_H = −2.285, r_T = +0.414 → FoM = −2.285 + 0.05 × 0.414 = **−2.265**, exactly what the code printed. `n_failed_sims = 0`. This single run confirms the whole chain refine → netlist → ngspice → measure → normalize → reward on a real simulation.

### Pitfalls
- Run everything from the `CAD/` folder; paths are built from `os.getcwd()`.
- `ngspice_wrapper.py` uses the KU Leuven server binary if it exists, otherwise the `ngspice` on your PATH (Homebrew on the Mac).
- Don't delete output files inside `simulate`; `clean.sh` is called by the runner every 100 steps.

---

## 3. `normalize_specs(spec_dict)` — put all specs on the same scale

### What it must do
For every spec `y` with target `y*` (from `self.dict_targets`):

```
z = (y − y*) / (y + y*)
```

Return a dict with the same keys.

### Why this formula?
The raw specs differ by 15 orders of magnitude (area ≈ 1e-9 m², UGBW ≈ 1e6 Hz). This formula is a **relative, bounded distance to the target**:

| y relative to y* | z |
|---|---|
| y = y* | 0 |
| y = 2 y* | +1/3 |
| y = y*/2 | −1/3 |
| y → ∞ | → +1 |
| y → 0 | → −1 |

- It is **unit-free** — every spec becomes a number in (−1, 1) for positive values.
- It is **symmetric in ratios**: being 2× too high and 2× too low give the same magnitude (1/3).
- It **saturates**: being 1000× off is not 1000× worse than being 10× off, which keeps the reward and the critic's targets bounded and training stable.
- The **sign** tells you the direction: z > 0 means "above target", z < 0 "below target". Whether that is good depends on the spec (see reward).

These z values are both the **observation** (state) given to the agent and the input to the reward.

### Design decisions in the implementation

**1. Loop over `self.dict_targets`, not over `spec_dict`.**
The observation vector must always have the same 7 entries in the same order (`area, current, gain, noise, phm, slewRate, ugbw`, the YAML order), because input neuron 0 of the actor/critic must always mean "area". If we looped over `spec_dict`, a measurement function that returned keys in another order, or forgot one, would silently scramble the observation.

**2. A direction for every spec: `LOWER_IS_BETTER`.**
A class constant at the top of `CircuitEnv`:

```python
LOWER_IS_BETTER = ('noise', 'area', 'current')
```

Every other spec (gain, phm, slewRate, ugbw) is "higher is better". This single definition is used in two places: here (to decide what the *worst* value is) and in `reward_computation` (to decide the penalty sign). Defining it once means the two can never disagree.

**3. Robustness for broken designs.**
With random sizes, some designs are pathological. The formula then breaks:

| Case | Raw formula | What we do |
|---|---|---|
| spec missing / `None` / NaN / ±inf (e.g. gain never crosses 0 dB → no UGBW) | crash or NaN | worst value |
| `y + y* = 0` (e.g. phm = −60°) | division by zero | worst value |
| `y + y* < 0` (e.g. phm = −90°) | sign flips → z = +5 (looks *great*!) | worst value |
| `−y* < y < 0` (e.g. phm = −30°) | z = −3 (outside [-1, 1]) | clip to −1 |
| `y ≥ 0` (every normal design) | z ∈ (−1, 1) | unchanged |

"Worst value" is −1 for higher-is-better specs and +1 for lower-is-better specs, the limit the formula approaches as the spec gets infinitely bad. The third row is the dangerous one: without the guard, a badly unstable amplifier would *look* like it has an excellent phase margin, and the agent would learn to make unstable designs.

A NaN in the observation would propagate through the neural networks and destroy training (every weight becomes NaN after one gradient step), so it is never allowed through.

For all normal designs (positive specs), none of these rules change anything: the guards and the clip only act on broken simulations. Mention it in the report as a design decision.

### Implementation

```python
def normalize_specs(self, spec_dict):
    norm_specs = {}
    # loop over the targets (not over spec_dict) -> fixed set and order of keys
    for name, goal in self.dict_targets.items():
        worst = 1.0 if name in self.LOWER_IS_BETTER else -1.0

        try:
            value = float(spec_dict[name])
        except (KeyError, TypeError, ValueError):
            value = np.nan

        denominator = value + goal
        if not np.isfinite(value) or denominator <= 0:
            norm_specs[name] = worst
            continue

        z = (value - goal) / denominator
        norm_specs[name] = float(np.clip(z, -1.0, 1.0))

    return norm_specs
```

Line by line:
- `float(spec_dict[name])` turns numpy scalars into plain floats, and turns `None` or a missing key into an exception that we catch → NaN.
- `np.isfinite` rejects NaN and ±inf in one test.
- `denominator <= 0` covers both the exact-zero and the sign-flip case.
- `float(np.clip(...))` keeps values plain Python floats, which print and save cleanly in the CSV.

### Verified results (use these in the unit test)
- gain = 100, target 200 → z = −100/300 = **−0.3333** ✅
- noise = 0.06, target 0.03 → z = 0.03/0.09 = **+0.3333** ✅
- area = 4e-9, target 2e-9 → z = **+0.3333** ✅
- current = 1e-4, target 2e-4 → z = **−0.3333** ✅
- output keys are in the same order as `dict_targets` ✅
- phm = −60°, ugbw = None, slewRate = NaN, gain = −50 → all **−1.0** ✅
- noise missing from the dict → **+1.0** ✅

---

## 4. `reset(seed=None, options=None)` — start a new episode

### What it must do (from the docstring)
1. `self.episode_steps = 0`
2. pick a **random action** in [-1, 1]^20
3. `self.evaluate(action)` → sets `param_values`, `real_specs`, `cur_norm_specs`
4. `self.score = 0`
5. return the observation: `np.array([self.cur_norm_specs[k] for k in self.dict_targets], dtype=np.float32)`

### Why a random starting design?
An episode is a short trajectory (10 steps) of design modifications. Starting each episode at a different random point spreads the experience across the design space, so the replay buffer contains diverse transitions and the critic generalizes better. It is a form of exploration.

### Design decisions in the implementation

**1. The `_get_obs()` helper.** `reset` and `step` must build the observation in exactly the same way. One small helper does it:

```python
def _get_obs(self):
    return np.array([self.cur_norm_specs[name] for name in self.dict_targets], dtype=np.float32)
```

The order is always the YAML `targets` order (`area, current, gain, noise, phm, slewRate, ugbw`), and the dtype is `float32` because that's what PyTorch and the replay buffer use.

**2. Randomness and seeds.** Two cases:
- **No seed** (how `td3_runner.py` calls it): use numpy's global generator `np.random`. The runner calls `np.random.seed(args.seed)` at the start, so a whole run is reproducible from `--seed`.
- **A seed is passed** (`env.reset(seed=1)`, e.g. in a test): call `super().reset(seed=seed)`, which seeds gymnasium's own generator `self.np_random`, and use that from then on (flag `self._use_env_rng`). This is the standard gymnasium convention.

We don't call `np.random.seed()` inside the environment: changing the global generator would also change the agent's exploration noise behind its back.

**3. Return only `obs`**, not gymnasium's `(obs, info)` tuple: `td3_runner.py` does `obs = env.reset()`.

**4. Reset costs a simulation.** The random start design must be simulated to produce the first observation. That matters for the "5k simulations" comparison with the baseline: with 10-step episodes, 10 000 steps cost 11 000 ngspice runs. Decision: `reward_history` (and therefore the max-FoM plot) has one entry per **step**, as the `step` docstring asks, and `self.n_simulations` counts **every** ngspice run, reset included. Report both numbers; say explicitly which one is on the x-axis.

**5. The episode score** is set to 0 in `__init__` too (`self.score = 0.0`), so `step` can never hit an undefined attribute.

### Implementation

```python
def reset(self, *, seed=None, options=None):
    if seed is not None:
        super().reset(seed=seed)          # seeds self.np_random
        self._use_env_rng = True
    rng = self.np_random if self._use_env_rng else np.random

    self.episode_steps = 0
    action = rng.uniform(-1.0, 1.0, self.n_actions)
    self.evaluate(action)
    self.score = 0.0

    return self._get_obs()
```

New attributes in `__init__`:

```python
self.n_simulations = 0     # every ngspice run, including the one in reset (see simulate)
self.n_failed_sims = 0     # number of simulations that crashed (see simulate)
self.best_reward = -np.inf # best FoM so far (for the max-FoM plot)
self.score = 0.0           # sum of rewards in the current episode
self._use_env_rng = False  # becomes True once reset() gets a seed
```

### Verified (simulator replaced by a fake returning known specs)
- observation: shape (7,), dtype float32, values = the normalized specs ✅
- `episode_steps` is 0 after reset ✅
- `reset(seed=1)` twice → identical start designs ✅

---

## 5. `reward_computation(norm_specs)` — the Figure of Merit

### The formula (slide 48)
Hard constraints Y (gain, noise, phm, slewRate, ugbw):

```
r_y = min(z_y, 0)     for lower-bound specs  y ∈ Y_L  (gain, phm, slewRate, ugbw: "must be ≥ target")
r_y = −max(z_y, 0)    for upper-bound specs  y ∈ Y_U  (noise: "must be ≤ target")
r_H = Σ w_y · r_y
```

Optimization targets T (area, current, both "lower is better"):

```
r_t = −o_t            (o_t is the normalized value, same formula as z)
r_T = Σ w_t · r_t
```

Figure of merit:

```
FoM = r_H + 0.05 · r_T      if r_H < 0   (some constraint violated)
FoM = 0.3 + r_T             if r_H ≥ 0   (all constraints met → bonus)
```

The weights `w` come from `self.spec_weights` (all 1.0 now, but use them — it makes the code general).

### Understanding each piece
- **`min(z, 0)` for lower bounds**: if gain is above target, z > 0 → contribution 0. There is no reward for "over-satisfying" a constraint — once it's met, it's met. If it's below target, the penalty grows with how far below.
- **`−max(z, 0)` for noise**: mirror image. Noise below target → 0; above → negative.
- Therefore **r_H ≤ 0 always**, and **r_H = 0 ⇔ every constraint is satisfied**. That's why "r_H ≥ success_threshold (0)" is the feasibility test.
- **Infeasible region** (r_H < 0): the agent's priority is to fix the constraints, so the optimization targets get only a small weight (0.05). They're still there so that, between two equally infeasible designs, the cheaper one is slightly preferred.
- **Feasible region**: a **+0.3 bonus** creates a clear "cliff" between infeasible and feasible designs: any feasible design scores more than any infeasible one (as long as r_T > −0.3). Then the reward is fully about minimizing area and current: r_T > 0 means smaller than target.

### Which spec has which direction?
This uses the same `LOWER_IS_BETTER = ('noise', 'area', 'current')` constant as `normalize_specs` (see §3). Within the hard constraints only `noise` is in it, so noise is the only upper-bound constraint; gain, phm, slewRate and ugbw are lower bounds. The YAML lists **5** hard constraints (slew rate included), while the slides say 4. The code reads the YAML, so 5 it is.

### Implementation

```python
def reward_computation(self, norm_specs):
    reward = 0.0
    hard_satisfied = False

    # 1. hard constraints: only violations are penalized, over-satisfying gives nothing
    hard_reward = 0.0
    for spec in self.hard_constraints:
        z = norm_specs[spec]
        weight = self.spec_weights.get(spec, 1.0)
        if spec in self.LOWER_IS_BETTER:          # upper bound, e.g. noise <= 30 mVrms
            hard_reward += weight * (-max(z, 0.0))
        else:                                     # lower bound, e.g. gain >= 200
            hard_reward += weight * min(z, 0.0)

    # 2. optimization targets: smaller than target -> positive contribution
    opt_reward = 0.0
    for target in self.optimization_targets:
        weight = self.spec_weights.get(target, 1.0)
        opt_reward += weight * (-norm_specs[target])

    # 3. feasible -> bonus + full optimization reward; infeasible -> fix constraints first
    if hard_reward >= self.success_threshold:
        hard_satisfied = True
        reward = 0.3 + opt_reward
    else:
        reward = hard_reward + 0.05 * opt_reward

    return float(reward), hard_satisfied
```

How it maps onto the docstring's 4 steps:
1. `reward = 0.0`, `hard_satisfied = False`.
2. The first loop builds r_H (`hard_reward`). It's kept in its own variable instead of adding straight into `reward`, so the feasibility test in step 3 looks *only* at the constraints.
3. `hard_reward >= self.success_threshold` is the docstring's "all hard constraints satisfied *or* the total passes the threshold of 0". Because every r_y ≤ 0, r_H ≥ 0 can only happen when every r_y = 0, so the two conditions are the same thing. Using `self.success_threshold` (instead of a literal 0) keeps the constructor argument meaningful. Note `>=` and not `>`: a design exactly on every target is feasible.
4. `float(reward)` makes sure the replay buffer gets a plain number, not a numpy scalar.

Small choices:
- `self.spec_weights.get(spec, 1.0)` uses the YAML weights, and falls back to 1.0 if a spec has no weight, instead of crashing.
- The optimization part is computed once and used in both branches (×1 when feasible, ×0.05 when not).

### Return value
`(reward, hard_satisfied)`: a Python `float` and a `bool`. `step` will use `hard_satisfied` to decide when to save a solution and update the max-FoM plot.

### Hand-calculated examples (all verified ✅, use them in the unit test)
**A. One constraint fails**: gain = 100 (z = −0.3333), all other constraints met, area = 4e-9 (o = +0.3333), current = 1e-4 (o = −0.3333):
- r_H = −0.3333; r_T = −0.3333 + 0.3333 = 0
- FoM = −0.3333 + 0.05·0 = **−0.3333**, hard_satisfied = **False**

**B. All met**: area = 1e-9 (o = −0.3333), current = 2e-4 (o = 0):
- r_H = 0; r_T = +0.3333
- FoM = 0.3 + 0.3333 = **0.6333**, hard_satisfied = **True**

**C. Everything exactly on target**: all z = 0 → FoM = **0.3**, hard_satisfied = **True** (boundary case — tests `≥` vs `>`).

**D. Noise fails**: noise = 0.06 (z = +0.3333), others met, area & current on target → r_H = −0.3333 → FoM = **−0.3333** (tests the sign flip for upper-bound specs).

**E. Over-satisfying**: gain = 10 000 and UGBW = 1 GHz, everything else on target → still FoM = **0.3**, True (proves there is no extra reward for exceeding a constraint).

---

## 6. `step(action)` — one interaction

### What it must do (docstring, with explanations)
1. **Evaluate** the action: `self.evaluate(action)`.
2. **Reward**: `reward, hard_satisfied = self.reward_computation(self.cur_norm_specs)`.
3. **Observation**: `ob = self._get_obs()` (same helper as in `reset`).
4. **Bookkeeping**: `self.reward_history.append(reward)`, `self.score += reward`.
5. **Directories**: `os.makedirs(f'./output_figs/{self.run_id}', exist_ok=True)` and `os.makedirs('./solutions', exist_ok=True)` — the plotting and saving helpers assume they exist.
6. **If the goal is reached** (`hard_satisfied`):
   - `plot_running_maximum(self.reward_history, self.run_id)` → this is the **"Maximum FoM per simulation step"** plot required in the final report.
   - Also save the design: `save_solutions_csv(self.run_id, self.env_steps, self.param_values, self.real_specs, reward)` (from `utils/saving.py`). That CSV is what `solutions2pareto` reads to make the **Current-Area Pareto plot**, and it's the content of the `Solutions` folder you must submit. Not explicitly in the docstring, but you need it.
7. **Counters**: `self.env_steps += 1`, `self.episode_steps += 1`.
8. **Done flag**: `done = self.episode_steps >= self.max_steps_per_episode` (10).
9. **Every 10 steps**: `self.score_history.append(self.score)`, `plotLearning(self.score_history, self.run_id)`, `self.score = 0`. With 10-step episodes this is simply "once per episode": the score is the sum of rewards over the episode.
10. **Return** `ob, reward, done, info` with e.g. `info = {'goal_reached': hard_satisfied, 'specs': self.real_specs, 'params': self.param_values}`.

### Why episodes of 10 steps if there is no "game over"?
Circuit sizing has no natural terminal state. The episode length is an artificial horizon: every 10 steps the environment jumps to a new random design (reset), which forces exploration and prevents the agent from getting stuck refining one bad region. It's also a hyperparameter you can discuss.

### Note on what "state → action → next state" means here
The action is an **absolute** design (all 20 parameters), not a delta. The observation tells the agent how the *last* design performed; the agent then proposes the next design. The `done` flag is stored in the replay buffer; with `done=True` the TD3 target uses no bootstrap term (Milestone 3).

### Design decisions in the implementation

**1. `env_steps` is used *before* it is incremented** when saving a solution, so the first step has index 0 in the CSV. The counters are only incremented afterwards (docstring step 7).

**2. Saving every feasible design.** `save_solutions_csv` appends one row per feasible design to `./solutions/<run_id>.csv`. All of them are kept, not only the Pareto-optimal ones: `solutions2pareto` filters the Pareto front afterwards, and the full list lets you plot the non-Pareto points too.

**3. Throttled max-FoM plot.** The docstring says to plot whenever the goal is reached. Late in training almost every step is feasible, and a matplotlib plot + PNG write takes about as long as a simulation, so plotting every time would nearly double the run time. The curve only changes *shape* when a new maximum is found, so the plot is redrawn when `reward > self.best_reward`, plus every 100 steps to extend the x-axis. Nothing is lost: `reward_history` keeps every value, and the final plot can always be redrawn at the end.

**4. Learning curve every 10 steps.** `env_steps % 10 == 0` → append the episode score (sum of the 10 rewards) to `score_history`, redraw `average_score.png`, reset the score. With 10-step episodes this lines up exactly with the episode boundaries.

**5. Types.** `reward` is already a `float` (from `reward_computation`), the observation is `float32`, and `done` is cast with `bool(...)`. The replay buffer stores numpy arrays, so a stray numpy bool or float64 would be silently converted, but keeping the types clean avoids surprises.

**6. A richer `info` dict.** Not used by the runner, but handy for debugging and for Milestone 4 (the LLM harness can read specs and counters from it):

```python
info = {'goal_reached': hard_satisfied, 'specs': self.real_specs, 'params': self.param_values,
        'env_steps': self.env_steps, 'n_simulations': self.n_simulations,
        'n_failed_sims': self.n_failed_sims}
```

### Implementation

```python
# at the top of circuit_env.py
from utils.saving import save_solutions_csv

def step(self, action):
    # 1-3. evaluate, reward, observation
    self.evaluate(action)
    reward, hard_satisfied = self.reward_computation(self.cur_norm_specs)
    ob = self._get_obs()

    # 4. bookkeeping
    self.reward_history.append(reward)
    self.score += reward

    # 5. output folders (the plotting / saving helpers assume they exist)
    os.makedirs(os.path.join('output_figs', str(self.run_id)), exist_ok=True)
    os.makedirs('solutions', exist_ok=True)

    # 6. goal reached: keep the solution and update the max-FoM plot
    if hard_satisfied:
        save_solutions_csv(self.run_id, self.env_steps, self.param_values, self.real_specs, reward)
        new_best = reward > self.best_reward
        if new_best or self.env_steps % 100 == 0:
            plot_running_maximum(self.reward_history, self.run_id)
    self.best_reward = max(self.best_reward, reward)

    # 7. counters
    self.env_steps += 1
    self.episode_steps += 1

    # 8. episode end
    done = self.episode_steps >= self.max_steps_per_episode

    # 9. learning curve (sum of rewards per 10 steps = per episode)
    if self.env_steps % 10 == 0:
        self.score_history.append(self.score)
        plotLearning(self.score_history, self.run_id)
        self.score = 0.0

    # 10. return
    info = {...}   # see above
    return ob, reward, bool(done), info
```

### Verified (simulator replaced by a fake returning known specs)
Two episodes of 10 steps. Episode 1: 9 infeasible designs (gain = 100 → FoM −0.3333) and 1 feasible (area 1e-9 → FoM 0.6333). Episode 2: 10 feasible designs.

| Check | Expected | Got |
|---|---|---|
| return value | 4-tuple, `done` a `bool`, obs `float32` | ✅ |
| `done` | True exactly at steps 10 and 20 | ✅ |
| episode 1 score | 9 × (−0.3333) + 0.6333 = −2.3667 | ✅ −2.3667 |
| episode 2 score | 10 × 0.6333 = 6.3333 | ✅ 6.3333 |
| saved solutions | 1 + 10 = 11 rows | ✅ 11 |
| plots | `average_score.png`, `max_reward.png` | ✅ both written |

### End-to-end check: `python circuit_env.py` on the Mac (real ngspice) ✅
One reset (random design) + one step (random design). The step's design:

| Spec | Value | Target | Status | Contribution |
|---|---|---|---|---|
| gain | 14.5 | ≥ 200 | fails, z = −0.865 | r_H: −0.865 |
| noise | 0.31 mVrms | ≤ 30 mVrms | met | 0 |
| phm | 87.5° | ≥ 60° | met | 0 |
| slewRate | 40.9 V/µs | ≥ 30 | met | 0 |
| ugbw | 116.5 MHz | ≥ 100 MHz | met | 0 |
| area | 2.97e-9 m² | 2e-9 | o = +0.196 | r_T: −0.196 |
| current | 469 µA | 200 µA | o = +0.402 | r_T: −0.402 |

FoM = −0.865 + 0.05 × (−0.598) = **−0.8948**, exactly what the code printed. The printed observation `[0.196, 0.402, −0.865, −0.980, 0.187, 0.153, 0.076]` is exactly these z values in YAML order (area, current, gain, noise, phm, slewRate, ugbw). This confirms reset → step → refine → netlist → ngspice → measure → normalize → reward → observation on real simulations.

Observation for later (Milestone 3/4): in both random designs, the specs that fail by far are **gain** (11.6 and 14.5 vs 200), while slew rate and UGBW can already be met by chance. Gain needs long channels and/or low bias current in the gain stages, which pushes UGBW and slew rate down: that trade-off is what the agent has to learn.

### Pitfalls
- Run from `CAD/`: `output_figs/` and `solutions/` are relative paths.
- The solutions CSV is **appended to**: reusing a `run_id` mixes two runs. The default run id is a timestamp, so this only happens if you pass the same `--run_id` twice.

---

## 7. The unit test (`test_circuit_env.py`)

### Goal
"Prove" that the environment is correct by comparing its outputs against values that were **not** produced by our code: the TA reference designs, and values calculated by hand.

### How to run it
From `CAD/`, with the `.venv` active:

```bash
python -m unittest test_circuit_env -v
```

or the run button in VS Code. It uses Python's built-in `unittest` (same as `test_dut.py` from Milestone 1, and `pytest` isn't installed in the `.venv`).

### Strategy
- **Two independent references.**
  1. `Reference_Designs/references.csv`: for 5 designs the TAs give the action, the sizes, the specs, the normalized specs and the reward. Each step of the chain can therefore be checked separately: `action_* → param_*`, `spec_* → norm_*`, `norm_* → reward`.
  2. Hand calculations (examples A–E of §5, and the z values of §3).
- **Pure logic without ngspice.** `action_refine`, `normalize_specs` and `reward_computation` need no simulator.
- **Mocking for the rest.** For `simulate`'s failure handling and for `reset`/`step`, the simulator is replaced with `unittest.mock.patch.object`, so the tests are fast, deterministic, and also run on a machine without ngspice.
- **One real end-to-end test** with ngspice on the 5 reference designs; skipped automatically if ngspice isn't installed.
- **No mess in `CAD/`.** The episode tests `chdir` into a temporary folder, so `output_figs/` and `solutions/` from the tests are deleted afterwards.

### The tests

| # | Test | Reference | What it proves |
|---|---|---|---|
| 1a | reference actions → sizes | TA `action_*` → `param_*` | all 100 parameters exactly reproduced |
| 1b | all −1 → minimum | YAML `min` | lower edge |
| 1c | all +1 → last grid value | `np.arange(...)[-1]` | upper edge (max excluded) |
| 1d | all 0 → middle values | hand: mp1 = 12, wp1 = 1.5 µm, lp1 = 90 nm, Cc = 5 pF, Rc = 4.9 kΩ | the floor-bin formula |
| 1e | ±5 and NaN | same as ±1 and 0 | clipping and NaN safety |
| 1f | 500 random actions | grid | always on the grid, multipliers `int` |
| 1g | key order | YAML | fixed parameter order |
| 1h | wrong action length | — | raises `ValueError` |
| 2a | reference specs → norms | TA `spec_*` → `norm_*` | normalization formula, all 7 specs × 5 designs |
| 2b | hand values | ±1/3 | formula and sign |
| 2c | key order | YAML | fixed observation order |
| 2d | broken specs | worst values −1 / +1 | phm = −60° and −90°, None, NaN, missing key |
| 2e | 200 random specs | [-1, 1] | always finite and bounded |
| 3a | reference norms → reward | TA `reward` | FoM formula on 5 real designs |
| 3b–3f | examples A–E | hand (§5) | each branch: one failure, feasible + bonus, boundary `>=`, noise sign, no reward for over-satisfying |
| 3g | return types | — | `float`, `bool` |
| 4a | netlist content | refined params | every `.param` written correctly, TT model file |
| 4b | crash while measuring | — | worst-case specs, area still real, reward < −4.9, failure counted |
| 4c | ngspice error code | — | same handling for `info = 1` |
| 4d | simulation counter | — | `n_simulations` counts, keys in YAML order |
| 5a | `reset` | normalized fake specs | returns only the obs: shape (7,), float32, correct values; episode counter 0 |
| 5b | `reset(seed=…)` | — | same seed → same design, other seed → other design |
| 5c | two full episodes | hand | 4-tuple and types; `done` at steps 10 and 20; every reward; episode scores −2.367 and 6.333; the 11 feasible designs saved at steps 3, 10–19; both plots written |
| 6a | end-to-end, real ngspice | TA specs, norms, rewards | action → refine → netlist → ngspice → specs (±5 %) → norms (±0.02) → reward (±0.05), no failed simulation |

### Results
- Sandbox (no ngspice): **28 tests, all pass in 0.8 s, 1 skipped** (6a, needs ngspice). ✅
- Mac with ngspice: **28 tests, all pass in 4.1 s, 0 skipped** ✅, including 6a: the 5 TA reference designs go from action to reward through real ngspice and match the TA specs (±5 %), normalized specs and rewards, with no failed simulation.
- The two `[simulate] simulation failed ...` lines in the output are expected: they are printed by tests 4b and 4c, which deliberately make a simulation fail.

### Why the reference file is the strongest evidence
Each hand calculation only checks that the code does what *we* think it should. The reference file was produced by the TAs' own implementation, so agreeing with it on actions, normalized specs and rewards shows our environment matches the expected one, including details we could have interpreted differently (as happened with the action grid, §1).

### What to say in the report
Explain the strategy (two independent references, mocking, one end-to-end test), show the chain `action → param → spec → norm → reward` for one reference design, show one hand calculation (example A or B), and state that all tests pass.

---

## 8. Order of work (done)

1. `action_refine` ✅ (TA convention, all reference designs reproduced)
2. `normalize_specs` ✅
3. `reward_computation` ✅
4. `simulate` ✅ (failure handling + real ngspice run)
5. `_get_obs`, `reset`, `step` ✅
6. `python circuit_env.py` smoke test on the Mac ✅
7. `test_circuit_env.py` ✅ 28/28 pass on the Mac

**Milestone 2 is complete.**
