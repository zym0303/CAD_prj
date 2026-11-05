# Milestone 3 — The TD3 agent, explained

This document walks through Milestone 3: what TD3 does in this project, the two methods in `td3/agent.py`, the episodic loop in `td3_runner.py`, the hyperparameters, and how to produce the plots and the baseline comparison.

**Status**

| Item | Status |
|---|---|
| `select_action` | ✅ implemented, tested |
| `update_parameters` (+ `_soft_update` helper) | ✅ implemented, tested (TD target checked by hand) |
| `td3_runner.py` fixes (defaults, keyword bug, 5k-simulation budget, logging, final plots, Pareto export) | ✅ done, tested end to end with ngspice mocked |
| `test_td3_agent.py` | ✅ 9/9 pass |
| `run_sweep.sh` (tuning), `compare_runs.py` (baseline comparison) | ✅ written, smoke-tested |
| Real ngspice runs: sweep + final 5k run | ⏳ on the Mac |
| Baseline comparison | ⏳ `baseline_runner.py` still empty: ask the TAs for the baseline agent |

---

## 0. The big picture

```
            obs s (7 normalized specs)
CircuitEnv ─────────────────────────────► Actor μ(s) ──► a ∈ [-1,1]^20 ──► + noise ──► env.step(a)
     ▲                                                                              │
     └──────────────── (s, a, r, s', done) stored in ReplayBuffer ◄─────────────────┘
                                      │
                         random mini-batch every step
                                      ▼
                    Critic Q1, Q2 learn "how good is design a?"
                    Actor learns "propose the a the critic likes most"
```

| Network | Role | Updated how |
|---|---|---|
| `actor` μ(s) | proposes a design | gradient ascent on Q1(s, μ(s)), every 2nd step |
| `critic` (Q1, Q2) | predicts the return of (s, a) | MSE to the TD target, every step |
| `actor_target`, `critic_target` | slow copies used to build the target | Polyak averaging, τ = 0.005 |

**A property of this environment worth putting in the report.** The action is an *absolute* design, so the next state s' depends only on a, not on s. The problem is really black-box optimization written as an MDP: the critic learns a surrogate model of FoM(design), and the actor does gradient ascent on that surrogate. That is why TD3 can work with only ~5k simulations, and it is also why γ has little meaning here (§4).

---

## 1. `select_action(state, explore=True)`

a = clip( μ(s) + ε, −1, 1 ),  ε ~ N(0, (max_action · σ)²) per component

1. numpy array → `torch.FloatTensor(state.reshape(1, -1))`. The network needs a batch dimension `(1, 7)`. Tensors are also accepted.
2. `self.actor(state)` under `torch.no_grad()` → `(1, 20)`, already in [−1, 1] thanks to `max_action * tanh`, then `.cpu().numpy().flatten()` → `(20,)`.
3. Noise: `np.random.normal(0, max_action * expl_noise, action_dim)`. `np.random` is seeded by the runner, so runs are reproducible.
4. Clip to [−max_action, max_action], so the buffer stores the action that was actually applied.

`explore=False` returns μ(s) without noise. It isn't needed for training, but it's handy for evaluating the learned policy and for the tests.

**Why noise?** The actor is deterministic. Without noise it would keep proposing the same design, and the critic would never learn what neighbouring designs look like.

**Interaction with the parameter grid** (good for justifying σ): `action_refine` cuts the action interval of width 2 into n bins. Lengths have 5 values (bin width 0.5) and multipliers have 25 (bin width 0.083). With σ = 0.1, exploration almost never changes a length but often changes a multiplier, capacitor or resistor.

---

## 2. `update_parameters(memory_batch, update=None)`

**Unpacking.** `ReplayBuffer.sample` returns **(state, action, next_state, reward, not_done)**, and the agent unpacks in that order. `reward` and `not_done` are `(B, 1)`.

**Target policy smoothing (TD3 trick #2):**
```python
noise = (torch.randn_like(action) * policy_noise * max_action).clamp(-noise_clip*max_action, noise_clip*max_action)
next_action = (actor_target(next_state) + noise).clamp(-max_action, max_action)
```
This adds small clipped noise (std 0.2, clip ±0.5) to the target action, which encodes "similar actions have similar values". It stops the critic from forming narrow, spurious peaks that the actor would exploit. It is a different noise from the exploration noise in §1: that one acts on the environment, this one only exists inside the target.

**Clipped double-Q target (TD3 trick #1):**

y = r + γ · not_done · min( Q1'(s', ã'), Q2'(s', ã') )

Q-learning maximizes over a noisy estimate, so it systematically *overestimates*. Taking the more pessimistic of two critics cancels most of that bias. Steps 3–4 run under `torch.no_grad()`, because y is a fixed label. `not_done = 0` on the 10th step of an episode removes the bootstrap. Strictly speaking that's a time limit, not a real terminal state (one line in the report).

**Critic update:** `critic_loss = MSE(Q1, y) + MSE(Q2, y)`, then zero_grad → backward → step. Shape trap: everything must be `(B, 1)`, because `(B,)` + `(B,1)` would silently broadcast to `(B,B)`. The buffer stores `(N, 1)`, and the hand-computed test confirms it.

**Delayed policy update (TD3 trick #3)**, run when `total_it % policy_freq == 0` (every 2 critic updates):
- `actor_loss = -critic.Q1(state, actor(state)).mean()`. The minus is there because optimizers minimize. Gradients flow through the critic into the actor, but only `actor_optimizer.step()` is called.
- Soft target update for both pairs: θ' ← τθ + (1−τ)θ' (in-place helper `_soft_update`).
- Why delay? The actor chases the critic, so letting the critic settle first gives lower-variance policy gradients.

The method returns `{'critic_loss', 'actor_loss'}` for logging (the losses go into `history.csv`). `target_update_interval` in the runner is unused, because TD3 updates the targets in the delayed block.

---

## 3. The runner (`td3_runner.py`)

**Episodic loop**
1. **Warmup** (`--w` steps): uniformly random designs (`env.action_space.sample()`, seeded) fill the buffer; no learning. It completes whole episodes unless the budget runs out.
2. **Training**: each episode = `reset()` (random start design, which costs one simulation), then 10 × [`select_action` → `step` → `push` → one gradient update]. That's an update-to-data ratio of 1.
3. `clean.sh` runs every 100 steps.
4. **Stop** when `env.n_simulations >= --max_sims` (default **5000**, reset included) or after `--T` steps. 5000 simulations ≈ 4545 steps.
5. **Finalize**: final `max_reward.png`; the Pareto front of all feasible designs, with **netlists regenerated** into `solutions/<run_id>/` (since `clean.sh` deletes the originals) plus `pareto_solutions.csv`; `pareto.png` (all feasible designs in grey); agent weights; `summary.json`.

**Bugs fixed relative to the skeleton**

| Issue | Fix |
|---|---|
| `update_parameters(memory=...)` vs. parameter `memory_batch` → TypeError | call with `memory_batch=` |
| `default="???"` with `type=float/int` → argparse crashes at startup | real defaults |
| `T=10_000` is twice the budget, and reset costs a simulation | `--max_sims 5000` budget on `env.n_simulations` |
| Max-FoM plot throttled in `step` | redrawn at the end |
| Pareto netlists deleted by `clean.sh` | regenerated from the saved params |
| `./clean.sh` needs exec permission | `bash ./clean.sh` |
| batch larger than the warmup data | `ValueError` if `w < batch_size` |

**Outputs per run** (`output_figs/<run_id>/`): `history.csv` (one row per step: step, n_simulations, phase, FoM, running max, feasible, losses, wall time), `max_reward.png`, `average_score.png`, `pareto.png`, `summary.json`, `td3_*` weights. Plus `solutions/<run_id>.csv` (every feasible design) and `solutions/<run_id>/` (Pareto netlists + `pareto_solutions.csv`). For the submission, copy `solutions/final_g099/` into a folder named `Solutions/`.

---

## 4. Hyperparameters

The budget is tiny by RL standards (original TD3: 1M steps; here ~4.5k), and every choice should follow from that.

| Param | Default | Sweep | Reasoning |
|---|---|---|---|
| `noise_sigma` | 0.1 | 0.05 / 0.2 / 0.3 | Too small: stuck near the first decent design. Too large: close to random search, noisy critic data. Link it to the grid bin widths (§1). |
| `batch_size` | 128 | 64 / 256 | With only ~5k transitions, a large batch resamples the same points; smaller batches give noisier but more frequent signals. Must be ≤ w. |
| `w` | 300 | 128 / 1000 | The critic needs a minimally diverse dataset before the actor follows it, but warmup is random search taken from the budget. ~5–10% of the budget is defensible. |
| `pi_lr` | 3e-4 | 1e-4 / 1e-3 | The actor should learn slower than the critic (same logic as the delayed update). |
| `q_lr` | 1e-3 | 3e-4 / 1e-3 | The original TD3 paper used 1e-3; with few samples the critic should fit quickly. |
| `gamma` (extra) | 0.99 | 0.5 / 0.0 | Since s' depends only on a, bootstrapping mostly adds noise. |

**γ evidence (toy problem with the same structure, 3 seeds, 3300 steps).** Best reward found: γ = 0.99 → −0.016 / −0.009 / −0.013; γ = 0.5 → −0.003 / −0.003 / −0.003; γ = 0 → −0.004 / −0.003 / −0.003. That is about 4× better with low γ. Check it on the circuit (sweep group `gamma`) before using it for the final run, and if it holds it makes a strong report point.

**Tuning procedure.** One parameter at a time around the default, using short runs (`SIMS=2000`). Compare best FoM at the budget and the number of simulations until the first feasible design. Use 2 seeds if time allows (`SEED=1 bash run_sweep.sh ...`). Then do the full 5k run with the winner. RL is noisy across seeds, so say so in the report.

---

## 5. Tests (`test_td3_agent.py`, 9/9 pass)

| Test | Checks |
|---|---|
| `test_select_action_shape_and_range` | `(20,)`, within [−1, 1] even with σ = 2 |
| `test_select_action_accepts_tensor` | tensor input works |
| `test_select_action_deterministic_part_and_noise_std` | `explore=False` = actor output; the noise has mean 0 and std σ |
| `test_critic_loss_matches_hand_computed_td_target` | critic loss = hand-computed MSE to y = r + γ·not_done·min(Q1', Q2') |
| `test_done_means_no_bootstrap` | not_done = 0 → y = r |
| `test_delayed_actor_and_target_updates` | it. 1: critic only; it. 2: actor + both targets |
| `test_soft_update_formula` | θ' = τθ + (1−τ)θ' exactly |
| `test_td3_learns_toy_design_problem` (slow) | on a hidden-optimum problem with s' = f(a), the learned μ gets ≥ 5× closer to the optimum than random designs (achieved ≈ 10×) |
| `test_runner_end_to_end_mocked` | full `main()` with fake specs: budget respected (reset counted), warmup = w steps, history rows = steps, the 3 plots, `solutions/test/` with netlists |

---

## 6. How to run (from `CAD/`, on the Mac)

```bash
source .venv/bin/activate
python -m pytest test_td3_agent.py -v                 # 1. tests (~20 s)
python td3_runner.py --max_sims 200 --run_id smoke    # 2. real-ngspice smoke test
bash run_sweep.sh noise                               # 3. tuning, group by group (SIMS=2000 default)
python compare_runs.py --runs sw_base:0.1 sw_noise0.05:0.05 sw_noise0.2:0.2 sw_noise0.3:0.3 --max_sims 2000
python td3_runner.py --run_id final_td3 <best args>   # 4. final 5k run
python compare_runs.py --runs final_td3:TD3 <baseline_run_id>:Baseline --max_sims 5000   # 5. vs. baseline
```

Look at the smoke test's `summary.json` → `runtime_s` to estimate how long a 5k run takes before launching the sweep.

`compare_runs.py` writes `output_figs/comparison/max_fom_vs_sims.png`, `pareto_overlay.png` and `comparison.csv` (best FoM, first feasible, #feasible, #Pareto). For the baseline, it reads `history.csv` if the baseline runs through the same logging, otherwise a `reward_history.npy/.csv`, plus `solutions/<run_id>.csv`. Count simulations the same way for both (say in the report whether resets are included).

---

## 7. What to say in the report

1. **Agent**: the three TD3 tricks with their equations (§2), the exploration noise (§1), and why each one is there.
2. **Episodic loop**: warmup → 10-step episodes with random reset → one update per step; the budget counts every ngspice run (§3).
3. **Hyperparameters**: the table of §4 with the reasoning and the sweep results (best FoM and first feasible per setting).
4. **Results**: max FoM vs. simulations, current–area Pareto front, and the comparison table and overlays vs. the baseline at 5k simulations.
5. **Discussion**: s' depends only on a, so this is surrogate-based black-box optimization; the γ experiment; seed variance; failed simulations (`n_failed_sims`).
