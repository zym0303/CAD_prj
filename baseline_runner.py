"""
Run the TAs' SAC baseline (compiled, Reference_Designs/milestone3_baseline/) on OUR circuit
environment, with the same simulation budget and the same logging as td3_runner.py, so
compare_runs.py can put both on one plot.

    python baseline_runner.py --max_sims 5000 --seed 123456 --run_id sac_baseline
    python compare_runs.py --runs final_g099:TD3 sac_baseline:SAC --max_sims 5000

Any other argument (--batch_size, --w, --pi_lr, --q_lr, --alpha_lr, --init_temperature, ...)
is passed on to the TAs' sac_runner unchanged; leave them at their defaults for a fair baseline.

Needs Linux x86-64 + Python 3.9 (the .so files are compiled for that), e.g.
    /users/micas/mahmadza/public/bin/cad_env/bin/python baseline_runner.py ...
"""
import argparse
import json
import os
import sys
import time

import numpy as np

BASELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'Reference_Designs', 'milestone3_baseline')
sys.path.insert(0, BASELINE_DIR)

# sac_runner does `from td3 import SAC, ReplayBuffer`: make SAC available from our td3 package
import td3
import sac_baseline
td3.SAC = sac_baseline.SAC

import sac_runner
from circuit_env import CircuitEnv
from td3_runner import StepLogger, export_pareto_solutions
from utils.plotting import plot_running_maximum, solutions2pareto


class BudgetReached(Exception):
    pass


class LoggedCircuitEnv(CircuitEnv):
    """Our env + a hard simulation budget + one history.csv row per step (td3_runner format)."""
    max_sims = None
    warmup = 0
    instance = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        LoggedCircuitEnv.instance = self
        self.logger = StepLogger(self.run_id)
        self.steps = 0

    def _check_budget(self):
        if self.n_simulations >= self.max_sims:
            raise BudgetReached

    def reset(self, *args, **kwargs):
        self._check_budget()
        return super().reset(*args, **kwargs)

    def step(self, action):
        self._check_budget()
        ob, reward, done, info = super().step(action)
        phase = 'warmup' if self.steps < self.warmup else 'sac'
        self.logger.log(self.steps, self, phase, reward, info)
        self.steps += 1
        return ob, reward, done, info


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--max_sims', type=int, default=5000)
    ours, rest = p.parse_known_args()

    sys.argv = ['sac_runner'] + rest
    args = sac_runner.readParser()             # the TAs' own argument parser and defaults

    LoggedCircuitEnv.max_sims = ours.max_sims
    LoggedCircuitEnv.warmup = args.w
    sac_runner.CircuitEnv = LoggedCircuitEnv   # sac_runner builds its env through this name

    start = time.time()
    try:
        sac_runner.main(args)
        stop = 'T steps reached'
    except BudgetReached:
        stop = f'{ours.max_sims} simulations reached'

    env = LoggedCircuitEnv.instance
    run_dir = os.path.join('output_figs', str(env.run_id))
    plot_running_maximum(env.reward_history, env.run_id)
    csv_path = export_pareto_solutions(env, env.run_id)
    if csv_path is not None:
        solutions2pareto(csv_path, env.run_id, show_all=True)
    summary = {
        'agent': 'SAC baseline (TAs)',
        'stopped_because': stop,
        'args': vars(args),
        'max_sims': ours.max_sims,
        'env_steps': env.steps,
        'n_simulations': env.n_simulations,
        'n_failed_sims': env.n_failed_sims,
        'best_fom': float(np.max(env.reward_history)) if env.reward_history else None,
        'first_feasible_step_and_sims': env.logger.first_feasible,
        'runtime_s': round(time.time() - start, 1),
    }
    with open(os.path.join(run_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
