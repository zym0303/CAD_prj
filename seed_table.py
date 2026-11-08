"""
Aggregate RL runs over seeds: one row per configuration, mean +- std of the best FoM,
first-feasible simulation count, number of feasible designs.

    python seed_table.py sweep        # the 12-config hyperparameter sweep, seeds 123456 / 7 / 42, 2000 sims
    python seed_table.py final        # final TD3 config (5 seeds) vs TAs' SAC baseline (3 seeds), 5000 sims

Reads output_figs/<run_id>/summary.json, output_figs/<run_id>/history.csv and solutions/<run_id>.csv,
writes output_figs/comparison/<name>_seeds.csv and, for `final`, output_figs/comparison/final_seeds.png
(mean running-max FoM per method with the min-max band over seeds, plus all per-seed Pareto fronts).
"""
import csv
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from compare_runs import load_history, load_solutions
from utils.plotting import is_pareto_efficient
from compare_runs import run_dir

SWEEP_SEEDS = ['', '_s7', '_s42']          # '' = seed 123456 (run_sweep.sh), others run_rl_overnight.sh
SWEEP = [  # (group, label, run_id without seed suffix)
    ('default', 'sigma 0.1, batch 128, w 300, lr 3e-4/1e-3, gamma 0.99', 'sw_base'),
    ('noise', 'sigma 0.05', 'sw_noise0.05'), ('noise', 'sigma 0.2', 'sw_noise0.2'), ('noise', 'sigma 0.3', 'sw_noise0.3'),
    ('gamma', 'gamma 0.5', 'sw_gamma0.5'), ('gamma', 'gamma 0.0', 'sw_gamma0.0'),
    ('batch', 'batch 64', 'sw_batch64'), ('batch', 'batch 256', 'sw_batch256'),
    ('warm-up', 'w 128', 'sw_w128'), ('warm-up', 'w 1000', 'sw_w1000'),
    ('lr', 'lr 1e-4/3e-4', 'sw_lr_slow'), ('lr', 'lr 1e-3/1e-3', 'sw_lr_fast'),
]
FINAL = [  # (label, [run_ids])
    ('TD3 final (w 128, gamma 0.99)', ['final_g099', 'final_g099_s7', 'final_g099_s42', 'final_g099_s1', 'final_g099_s2']),
    ('TD3 final (w 128, gamma 0)', ['final_g0', 'final_g0_s7', 'final_g0_s42', 'final_g0_s1', 'final_g0_s2']),
    ('SAC baseline (TAs)', ['sac_baseline', 'sac_baseline_s7', 'sac_baseline_s42']),
]


def run_stats(run_id):
    with open(os.path.join(run_dir(run_id), 'summary.json')) as f:
        s = json.load(f)
    ff = s.get('first_feasible_step_and_sims')
    return {'run_id': run_id, 'seed': s['args']['seed'], 'best': s['best_fom'],
            'first_feasible_sims': ff[1] if ff else None, 'n_feasible': len(load_solutions(run_id)),
            'failed': s.get('n_failed_sims'), 'runtime_s': s.get('runtime_s')}


def aggregate(label, run_ids, group=''):
    st = [run_stats(r) for r in run_ids if os.path.isfile(os.path.join(run_dir(r), 'summary.json'))]
    best = np.array([x['best'] for x in st])
    ff = [x['first_feasible_sims'] for x in st]
    ff_ok = [v for v in ff if v is not None]
    return {'group': group, 'config': label, 'n_seeds': len(st),
            'best_mean': best.mean(), 'best_std': best.std(ddof=1) if len(best) > 1 else 0.0,
            'best_min': best.min(), 'best_max': best.max(),
            'per_seed': ' / '.join(f'{x["best"]:.3f}' for x in st),
            'first_feasible_median': int(np.median(ff_ok)) if ff_ok else None,
            'never_feasible': sum(v is None for v in ff),
            'n_feasible_mean': np.mean([x['n_feasible'] for x in st]),
            'failed_sims_mean': np.mean([x['failed'] for x in st]),
            'runs': st}


def write_table(rows, path):
    cols = ['group', 'config', 'n_seeds', 'best_mean', 'best_std', 'best_min', 'best_max', 'per_seed',
            'first_feasible_median', 'never_feasible', 'n_feasible_mean', 'failed_sims_mean']
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([f'{r[c]:.4f}' if isinstance(r[c], float) else r[c] for c in cols])
    print(f'{"group":9s} {"config":48s} n  mean   std    min    max    per seed (123456 / 7 / 42 ...)   1st feas  #feas')
    for r in rows:
        print(f'{r["group"]:9s} {r["config"]:48s} {r["n_seeds"]}  {r["best_mean"]:.3f}  {r["best_std"]:.3f}  '
              f'{r["best_min"]:.3f}  {r["best_max"]:.3f}  {r["per_seed"]:28s}  {str(r["first_feasible_median"]):6s}'
              f'{"(" + str(r["never_feasible"]) + " never)" if r["never_feasible"] else "":10s} {r["n_feasible_mean"]:.0f}')
    print('written', path)


def final_figure(rows, max_sims, out_png):
    plt.rcParams.update({'font.size': 12})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    colors = ['#2a78d6', '#eb6834', '#3aa655']
    grid = np.arange(2, max_sims + 1)      # the first FoM exists after the reset + first step (2 sims)
    for color, r in zip(colors, rows):
        curves = []
        for st in r['runs']:
            x, y, _, _ = load_history(st['run_id'])
            keep = x <= max_sims
            run_max = np.maximum.accumulate(y[keep])
            curves.append(np.interp(grid, x[keep], run_max, left=np.nan))
            sols = load_solutions(st['run_id'])
            if sols:
                pts = np.array([[s[1]['area'] * 1e12, s[1]['current'] * 1e6] for s in sols])
                front = pts[is_pareto_efficient(pts)]
                front = front[np.argsort(front[:, 0])]
                ax2.plot(front[:, 0], front[:, 1], 'o-', color=color, markersize=4, alpha=0.6, linewidth=1)
        c = np.array(curves)
        ax1.plot(grid, np.nanmean(c, 0), color=color, linewidth=2, label=f'{r["config"]} ({r["n_seeds"]} seeds)')
        ax1.fill_between(grid, np.nanmin(c, 0), np.nanmax(c, 0), color=color, alpha=0.18, linewidth=0)
        ax2.plot([], [], 'o-', color=color, label=f'{r["config"]}: Pareto front of each seed')
    ax1.axhline(0.3, color='grey', linestyle=':', linewidth=1)
    ax1.text(max_sims, 0.31, 'FoM 0.3: feasible, targets exactly met', ha='right', va='bottom', color='grey', fontsize=10)
    ax1.set_xlabel('# simulations (reset included)')
    ax1.set_ylabel('Maximum FoM reached (mean, min-max band over seeds)')
    ax1.set_ylim(-1.0, 0.8)
    ax1.grid(True, alpha=0.4)
    ax1.legend(loc='lower right')
    ax2.set_xlabel('Active area (um^2)')
    ax2.set_ylabel('Total current (uA)')
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png, dpi=200)
    print('written', out_png)


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else 'sweep'
    os.makedirs('output_figs/comparison', exist_ok=True)
    if what == 'sweep':
        rows = [aggregate(label, [rid + s for s in SWEEP_SEEDS], group) for group, label, rid in SWEEP]
        write_table(rows, 'output_figs/comparison/sweep_seeds.csv')
    elif what == 'final':
        rows = [aggregate(label, ids) for label, ids in FINAL]
        write_table(rows, 'output_figs/comparison/final_seeds.csv')
        for r in rows:
            for st in r['runs']:
                print(f'    {st["run_id"]:18s} seed {st["seed"]:7d}  best {st["best"]:.4f}  first feasible at '
                      f'{st["first_feasible_sims"]} sims  {st["n_feasible"]} feasible  {st["failed"]} failed  {st["runtime_s"]:.0f} s')
        final_figure(rows, 5000, 'output_figs/comparison/final_seeds.png')
    else:
        sys.exit('usage: python seed_table.py sweep|final')


if __name__ == '__main__':
    main()
