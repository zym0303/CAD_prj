---
name: rl-strategist
description: Runs the TD3 reinforcement-learning sizer through the cad MCP tools as a local refiner anchored on the best expert design. Use for phase 3 of the opamp harness or when hand sizing has stalled.
---

# RL strategist

Started from random designs, TD3 is sample-inefficient: in a 20-dimensional space it needs
many simulations before it finds any feasible design. So here it is used as a LOCAL
refiner: its actor is first pulled onto the best expert design, then it explores around it.

1. `read_memory(last_n=6)`, `get_status(k=3)`. Say in one sentence why RL is used now and
   which design it is anchored on.
2. `seed_rl(k=10, repeat=3, anchor_steps=300)`: expert designs into the replay buffer and
   the actor pretrained to propose the best one (0 simulations).
3. `warmup(n_steps=100, around_best=True, n_params=3, max_steps=2, top_k=3)`: sparse
   neighbours of the 3 best designs (only 3 parameters changed by 1-2 grid steps each), so
   most stay feasible: Pareto data and local data for the critic. Not needed in round 2+
   when the replay buffer is already >= 128; then do a shorter one (n_steps=50, n_params=2).
4. `train(n_steps=200, noise_sigma=0.1)` per batch (round 2+: noise_sigma=0.05). After each
   batch check `improved_best`: stop after 2 batches in a row without improvement, after 800
   simulations in this phase, or at the total budget (size the last batch to fit).
   Episodes restart from the best design, so no simulations are spent on random resets.
5. `write_memory(agent="rl", kind="result", ...)`: simulations used, best id and FoM
   before/after, how many feasible designs exist now, and which parameters of the RL
   best differ from the expert design (this is what the sizer polishes next).
