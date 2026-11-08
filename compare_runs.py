"""
Compare runs (e.g. our TD3 vs. the TAs' baseline) on the same simulation budget.

    python compare_runs.py --runs <run_id>:TD3 <baseline_run_id>:Baseline --max_sims 5000 [--out_dir comparison]

For each run it reads
    output_figs/<run_id>/history.csv   (written by td3_runner.py: FoM per step + n_simulations)
or, if that file is missing (e.g. a baseline that does not use our runner),
    output_figs/<run_id>/reward_history.npy / .csv  (one FoM per step; x-axis = step)
and the feasible designs in solutions/<run_id>.csv (or its filed copy under solutions/milestone*/).

Writes output_figs/<out_dir>/ (default output_figs/comparison/)
    max_fom_vs_sims.png   running max FoM vs. number of simulations, all runs
    pareto_overlay.png    current-area Pareto fronts, all runs
    comparison.csv        table: best FoM, first feasible, #feasible, #Pareto, per run
"""
import argparse
import csv
import glob
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from utils.plotting import is_pareto_efficient


def load_history(run_id):
    path = os.path.join('output_figs', run_id, 'history.csv')
    if os.path.isfile(path):
        with open(path) as f:
            rows = list(csv.DictReader(f))
        x = np.array([int(r['n_simulations']) for r in rows])
        y = np.array([float(r['reward']) for r in rows])
        feas = np.array([int(r['feasible']) for r in rows])
        return x, y, feas, '# simulations (reset included)'
    for ext in ('npy', 'csv'):
        path = os.path.join('output_figs', run_id, f'reward_history.{ext}')
        if os.path.isfile(path):
            y = np.load(path) if ext == 'npy' else np.loadtxt(path, delimiter=',')
            return np.arange(1, len(y) + 1), y, None, '# simulation step'
    raise FileNotFoundError(f'no history found for run {run_id}')


def solutions_csv(run_id):
    """Path of solutions/<run_id>.csv: new runs write it at the top level, finished runs are filed
    under solutions/milestone3_final/<method>/, milestone3_sweep/ or milestone4_harness/."""
    top = os.path.join('solutions', f'{run_id}.csv')
    if os.path.isfile(top):
        return top
    hits = glob.glob(os.path.join('solutions', '**', f'{run_id}.csv'), recursive=True)
    return hits[0] if hits else top


def load_solutions(run_id):
    path = solutions_csv(run_id)
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            if row.get('Specs'):
                specs = eval(row['Specs'], {'__builtins__': {}, 'np': np})
                out.append((int(row['Simulation step']), specs, float(row['Reward'])))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--runs', nargs='+', required=True, help='run_id:label pairs')
    p.add_argument('--max_sims', type=int, default=5000)
    p.add_argument('--out_dir', default='comparison', help='subfolder of output_figs/ to write into')
    args = p.parse_args()

    out_dir = os.path.join('output_figs', args.out_dir)
    os.makedirs(out_dir, exist_ok=True)
    plt.rcParams.update({'font.size': 14})
    fig1, ax1 = plt.subplots(figsize=(8, 5))
    fig2, ax2 = plt.subplots(figsize=(8, 6))
    table = []

    for spec in args.runs:
        run_id, label = spec.split(':', 1) if ':' in spec else (spec, spec)
        x, y, feas, xlabel = load_history(run_id)
        keep = x <= args.max_sims
        x, y = x[keep], y[keep]
        ax1.plot(x, np.maximum.accumulate(y), label=label, linewidth=2)

        n_steps = int(keep.sum())
        sols = [s for s in load_solutions(run_id) if s[0] < n_steps]
        first = None
        if feas is not None and feas[keep].any():
            first = int(x[np.argmax(feas[keep] == 1)])
        elif sols:
            first = sols[0][0]
        n_pareto = 0
        if sols:
            pts = np.array([[s[1]['area'] * 1e12, s[1]['current'] * 1e6] for s in sols])
            front = pts[is_pareto_efficient(pts)]
            front = front[np.argsort(front[:, 0])]
            n_pareto = len(front)
            line, = ax2.plot(front[:, 0], front[:, 1], 'o--', label=f'{label} Pareto', markersize=7)
            ax2.scatter(pts[:, 0], pts[:, 1], s=10, alpha=0.25, color=line.get_color())
        table.append([label, run_id, f'{y.max():.4f}', first, len(sols), n_pareto, int(x.max())])

    ax1.set_xlabel(xlabel)
    ax1.set_ylabel('Maximum FoM reached')
    ax1.grid(True)
    ax1.legend()
    fig1.tight_layout()
    fig1.savefig(os.path.join(out_dir, 'max_fom_vs_sims.png'), dpi=200)

    ax2.set_xlabel('Active Area (μm²)')
    ax2.set_ylabel('Total Current (μA)')
    ax2.grid(True, linestyle='--', alpha=0.7)
    ax2.legend()
    fig2.tight_layout()
    fig2.savefig(os.path.join(out_dir, 'pareto_overlay.png'), dpi=200)

    header = ['label', 'run_id', 'best_FoM', 'first_feasible_at', 'n_feasible', 'n_pareto', 'sims_used']
    with open(os.path.join(out_dir, 'comparison.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(table)
    for row in [header] + table:
        print(' | '.join(str(c) for c in row))


if __name__ == '__main__':
    main()
