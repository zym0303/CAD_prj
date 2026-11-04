import argparse
import csv
import json
import os
import shutil
import time
import torch
import numpy as np
from td3 import TD3, ReplayBuffer
from circuit_env import CircuitEnv
from datetime import datetime
from utils.plotting import plot_running_maximum, solutions2pareto, is_pareto_efficient


def readParser(argv=None):
    parser = argparse.ArgumentParser(description='TD3-based RL for Circuit Sizing')

    parser.add_argument('--seed', type=int, default=123456, metavar='N',
                        help='random seed (default: 123456)')

    # ---- tuned hyperparameters (see Milestone_3_explained.md, section 4) ----
    parser.add_argument('--noise_sigma', type=float, default=0.1,
                        help='fixed std of the Gaussian exploration noise added to mu(s) (default: 0.1)')

    parser.add_argument('--batch_size', type=int, default=128, metavar='N',
                        help='mini-batch size sampled from the replay buffer (default: 128)')

    parser.add_argument('--w', type=int, default=300, metavar='N',
                        help='number of warmup steps with random actions (default: 300)')

    parser.add_argument('--pi_lr', type=float, default=3e-4, metavar='G',
                        help='actor learning rate (default: 3e-4)')

    parser.add_argument('--q_lr', type=float, default=1e-3, metavar='G',
                        help='critic learning rate (default: 1e-3)')
    # -------------------------------------------------------------------------

    parser.add_argument('--gamma', type=float, default=0.99, metavar='G',
                        help='discount factor for reward (default: 0.99)')

    parser.add_argument('--tau', type=float, default=0.005, metavar='G',
                        help='target smoothing coefficient(τ) (default: 0.005)')

    parser.add_argument('--target_update_interval', type=int, default=1, metavar='N',
                        help='not used: TD3 updates the targets together with the delayed actor update')

    parser.add_argument('--actor_update_interval', type=int, default=2, metavar='N',
                        help='actor (and target) update every N critic updates (default: 2)')

    parser.add_argument('--hidden_size', type=int, default=256, metavar='N',
                        help='not used: the networks in td3/agent.py are fixed at 256 units')

    parser.add_argument('--T', type=int, default=10_000, metavar='N',
                        help='upper bound on environment steps (default: 10_000)')

    parser.add_argument('--max_sims', type=int, default=5000, metavar='N',
                        help='simulation budget: stop when this many ngspice runs (reset included) '
                             'have been done (default: 5000)')

    parser.add_argument('--replay_size', type=int, default=1000000, metavar='N',
                        help='size of replay buffer (default: 1000000)')

    parser.add_argument('--cuda', default=False, action="store_true",
                        help='not used: the device is chosen automatically in td3/agent.py')

    parser.add_argument('--run_id', type=str, default=datetime.now().strftime('%Y-%m-%d--%H-%M-%S'), metavar='N',
                        help='run identifier (default: current time)')

    return parser.parse_args(argv)


# ----------------------------------------------------------------------------
# Logging: one row per environment step, so that FoM can be plotted against
# the number of simulations (reset simulations included) for the baseline comparison
# ----------------------------------------------------------------------------
class StepLogger:
    def __init__(self, run_id):
        self.dir = os.path.join('output_figs', str(run_id))
        os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, 'history.csv')
        self.best = -np.inf
        self.first_feasible = None      # (step, n_simulations) of the first design meeting all constraints
        self.t0 = time.time()
        with open(self.path, 'w', newline='') as f:
            csv.writer(f).writerow(['step', 'n_simulations', 'phase', 'reward', 'max_reward',
                                    'feasible', 'critic_loss', 'actor_loss', 'wall_time_s'])

    def log(self, step, env, phase, reward, info, losses=None):
        self.best = max(self.best, reward)
        if info.get('goal_reached', False) and self.first_feasible is None:
            self.first_feasible = (step, env.n_simulations)
        losses = losses or {}
        with open(self.path, 'a', newline='') as f:
            csv.writer(f).writerow([step, env.n_simulations, phase, reward, self.best,
                                    int(info.get('goal_reached', False)),
                                    losses.get('critic_loss', ''), losses.get('actor_loss', ''),
                                    round(time.time() - self.t0, 2)])
        if step % 50 == 0:
            print(f"[{phase}] step {step:5d} | sims {env.n_simulations:5d} | "
                  f"FoM {reward:+.4f} | best {self.best:+.4f} | failed sims {env.n_failed_sims}")


def budget_left(args, env, total_steps):
    return total_steps < args.T and env.n_simulations < args.max_sims


def clean_up():
    # empty the no_backup folder (netlists / output files of past simulations)
    os.system('bash ./clean.sh')


def train(args, env, agent, env_pool, logger):
    total_steps = warmup_exploration(args, env, env_pool, logger)
    while budget_left(args, env, total_steps):
        obs = env.reset()
        done = False
        while not done and budget_left(args, env, total_steps):
            action = agent.select_action(obs)
            next_state, reward, done, info = env.step(action)
            env_pool.push(obs, action, reward, next_state, done)
            obs = next_state
            losses = train_policy(args, env_pool, agent, total_steps)
            logger.log(total_steps, env, 'td3', reward, info, losses)
            total_steps += 1
            # clean up the no_backup folder every 100 steps
            if total_steps % 100 == 0:
                clean_up()
    return total_steps


def warmup_exploration(args, env, env_pool, logger):
    """Fill the replay buffer with uniformly random designs before learning starts."""
    step_counter = 0
    while step_counter < args.w and env.n_simulations < args.max_sims:
        obs = env.reset()
        done = False
        while not done and env.n_simulations < args.max_sims:
            action = env.action_space.sample()
            next_state, reward, done, info = env.step(action)
            env_pool.push(obs, action, reward, next_state, done)
            obs = next_state
            logger.log(step_counter, env, 'warmup', reward, info)
            step_counter += 1
            if step_counter % 100 == 0:
                clean_up()
    return step_counter


def train_policy(args, env_pool, agent, total_steps):
    # ReplayBuffer.sample returns (state, action, next_state, reward, not_done)
    batch = env_pool.sample(args.batch_size)
    return agent.update_parameters(memory_batch=batch, update=total_steps)


# ----------------------------------------------------------------------------
# After training: final plots and the Solutions folder
# ----------------------------------------------------------------------------
def _parse_dict(text):
    # the CSV stores str(dict); numpy scalars may appear as np.float64(...)
    return eval(text, {'__builtins__': {}, 'np': np})


def export_pareto_solutions(env, run_id, out_root='Solutions'):
    """
    Read every feasible design from ./solutions/<run_id>.csv, keep the current-area
    Pareto-optimal ones, regenerate their netlists (clean.sh deletes the originals) and
    write them with a CSV of params, specs and FoM to Solutions/<run_id>/.
    """
    csv_path = os.path.join('solutions', f'{run_id}.csv')
    if not os.path.isfile(csv_path):
        print("No feasible design found -> no Pareto solutions to export.")
        return None

    rows = []
    with open(csv_path, newline='') as f:
        for row in csv.DictReader(f):
            if not row.get('Specs'):
                continue                                  # empty separator rows
            rows.append({'step': int(row['Simulation step']),
                         'specs': _parse_dict(row['Specs']),
                         'params': _parse_dict(row['Circuit Params']),
                         'reward': float(row['Reward'])})

    costs = np.array([[r['specs']['area'], r['specs']['current']] for r in rows])
    pareto = [r for r, keep in zip(rows, is_pareto_efficient(costs)) if keep]
    pareto.sort(key=lambda r: r['specs']['area'])

    out_dir = os.path.join(out_root, str(run_id))
    os.makedirs(out_dir, exist_ok=True)
    engine = env.simulation_engine
    with open(os.path.join(out_dir, 'pareto_solutions.csv'), 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Solution', 'Simulation step', 'Reward', 'Specs', 'Circuit Params', 'Netlist'])
        for i, r in enumerate(pareto):
            netlist = engine.create_new_netlist(r['params'], process=env.pvt_corner['process'],
                                                temp_pvt=env.pvt_corner['temp'],
                                                vdd=env.pvt_corner['voltage'])
            name = f'pareto_{i:02d}_step{r["step"]}.cir'
            shutil.copy(netlist, os.path.join(out_dir, name))
            writer.writerow([i, r['step'], r['reward'], str(r['specs']), str(r['params']), name])

    print(f"{len(rows)} feasible designs, {len(pareto)} on the Pareto front -> {out_dir}/")
    return csv_path


def finalize(args, env, agent, total_steps, start_time, logger):
    run_dir = os.path.join('output_figs', str(args.run_id))
    os.makedirs(run_dir, exist_ok=True)

    # final versions of the two required plots (the env only redraws them now and then)
    plot_running_maximum(env.reward_history, args.run_id)
    csv_path = export_pareto_solutions(env, args.run_id)
    if csv_path is not None:
        solutions2pareto(csv_path, args.run_id, show_all=True)

    agent.save(os.path.join(run_dir, 'td3'))

    summary = {
        'args': vars(args),
        'env_steps': total_steps,
        'n_simulations': env.n_simulations,
        'n_failed_sims': env.n_failed_sims,
        'best_fom': float(np.max(env.reward_history)) if env.reward_history else None,
        'first_feasible_step_and_sims': logger.first_feasible,
        'runtime_s': round(time.time() - start_time, 1),
    }
    with open(os.path.join(run_dir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


def main(args=None):
    if args is None:
        args = readParser()
    if args.w < args.batch_size:
        raise ValueError(f"warmup steps w={args.w} must be >= batch_size={args.batch_size}")

    start_time = time.time()
    # Set random seed
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    # Initial environment
    env = CircuitEnv(run_id=args.run_id)
    env.action_space.seed(args.seed)          # makes the warmup designs reproducible too
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    # Intial agent
    agent = TD3(state_dim, env.action_space, args)
    # Initial pool for env
    env_pool = ReplayBuffer(state_dim, action_dim, max_size=args.replay_size)
    # Training
    logger = StepLogger(args.run_id)
    total_steps = train(args, env, agent, env_pool, logger)
    finalize(args, env, agent, total_steps, start_time, logger)


if __name__ == "__main__":
    main()
