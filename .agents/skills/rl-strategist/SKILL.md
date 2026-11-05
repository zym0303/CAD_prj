---
name: rl-strategist
description: Runs the TD3 reinforcement-learning sizer through the cad MCP tools as a local refiner anchored on the best expert design. Use for phase 3 of the opamp harness or when hand sizing has stalled.
---

# RL strategist

Started from random designs, TD3 needs ~780 simulations to find anything feasible (milestone 3),
and in a 550-simulation harness run it found nothing. So here it is used as a LOCAL
refiner: its actor is first pulled onto the best expert design, then it explores around it.

1. `read_memory(last_n=6)`, `get_status(k=3)`. Say in one sentence why RL is used now and
   which design it is anchored on.
2. `seed_rl(k=10, repeat=3, anchor_steps=300)`: expert designs into the replay buffer and
   the actor pretrained to propose the best one (0 simulations).
3. `warmup(n_steps=100, around_best=True, radius=0.15)`: neighbours of the best design;
   fills the buffer to >= 128 and gives the critic local data.
4. `train(n_steps=200, noise_sigma=0.1)` per batch. After each batch check `improved_best`:
   - improved: continue; after 2 improving batches use noise_sigma=0.05 (finer search);
   - 2 batches in a row without improvement, or 800 simulations in this phase, or the total budget (opamp-harness) is reached: stop.
   Size the last batch so it does not exceed the remaining budget.
5. `write_memory(agent="rl", kind="result", ...)`: simulations used, best id and FoM
   before/after, how many feasible designs exist now, and which parameters of the RL
   best differ from the expert design (this is what the sizer polishes next).
