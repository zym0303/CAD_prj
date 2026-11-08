"""Milestone 3 figures with several seeds per configuration: 3.3 sweep groups and 3.4 baseline comparison.

    python plot_sweep_groups.py sweep      # output_figs/sweep_3seeds/{noise,gamma,batch,warmup,lr}.png + .csv
    python plot_sweep_groups.py final      # output_figs/baseline_cmp_seeds/td3_vs_sac.png + .csv
    python plot_sweep_groups.py grid       # output_figs/sweep_3seeds/sweep_grid.png (5 groups, max FoM) + gamma_score.png
    python plot_sweep_groups.py            # all three

Each figure has three panels:
  (a) maximum FoM reached vs. simulations: mean over the seeds (line) and min-max band;
  (b) per-step score (FoM of the design proposed at each step, 50-step moving average), mean over seeds;
  (c) current-area Pareto front of the feasible designs pooled over the seeds of each configuration
      (faint dots: all feasible designs).
Sweep: the default configuration (sw_base: sigma 0.1, batch 128, w 300, lr 3e-4/1e-3, gamma 0.99) is
dark grey in every figure, variants use the categorical palette; seeds 123456 (run_sweep.sh), 7 and 42
(run_rl_overnight.sh), 2000 simulations. Final: TD3 w 128 with gamma 0.99 and gamma 0 (5 seeds each)
vs. the TAs' SAC baseline (3 seeds), 5000 simulations (run_rl_seeds.sh, run_rl_overnight.sh,
baseline_runner.py). Data: output_figs/<run>/history.csv, summary.json and solutions/<run>.csv.
"""
import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from compare_runs import load_history, load_solutions
from utils.plotting import is_pareto_efficient

SWEEP_SEEDS = ["", "_s7", "_s42"]                    # seed 123456 (no suffix), 7, 42
DEFAULT = ("default (σ 0.1, batch 128, w 300, lr 3e-4/1e-3, γ 0.99)", "sw_base")
GROUPS = {   # group -> (title, [(label, run_id_without_seed), ...]); the default is added first
    "noise": ("Exploration noise σ", [("σ 0.05", "sw_noise0.05"), ("σ 0.2", "sw_noise0.2"), ("σ 0.3", "sw_noise0.3")]),
    "gamma": ("Discount factor γ", [("γ 0.5", "sw_gamma0.5"), ("γ 0", "sw_gamma0.0")]),
    "batch": ("Batch size", [("batch 64", "sw_batch64"), ("batch 256", "sw_batch256")]),
    "warmup": ("Warm-up steps w (random actions before training)", [("w 128", "sw_w128"), ("w 1000", "sw_w1000")]),
    "lr": ("Learning rates (actor / critic)", [("lr 1e-4 / 3e-4", "sw_lr_slow"), ("lr 1e-3 / 1e-3", "sw_lr_fast")]),
}
FINAL = [   # (label, [run_ids], color)
    ("TD3, w 128, γ 0.99", ["final_g099", "final_g099_s7", "final_g099_s42", "final_g099_s1", "final_g099_s2"], "#2a78d6"),
    ("TD3, w 128, γ 0", ["final_g0", "final_g0_s7", "final_g0_s42", "final_g0_s1", "final_g0_s2"], "#eb6834"),
    ("SAC baseline (TAs)", ["sac_baseline", "sac_baseline_s7", "sac_baseline_s42"], "#3aa655"),
]
DEFAULT_COLOR = "#4a4a4a"
COLORS = ["#2a78d6", "#eb6834", "#3aa655"]
WINDOW = 50
INK, MUTED = "#222222", "#8a8a8a"


def seed_curves(run_ids, max_sims):
    """Running max and moving-average score of each run on a common simulation grid, plus per-run stats."""
    grid = np.arange(2, max_sims + 1)
    run_max, score, stats = [], [], []
    for rid in run_ids:
        if not os.path.isfile(os.path.join("output_figs", rid, "history.csv")):
            continue
        x, y, feas, _ = load_history(rid)
        keep = x <= max_sims
        x, y, feas = x[keep], y[keep], feas[keep]
        with open(os.path.join("output_figs", rid, "history.csv")) as f:
            closs = [float(r["critic_loss"]) for r in csv.DictReader(f) if r["critic_loss"]]
        run_max.append(np.interp(grid, x, np.maximum.accumulate(y), left=np.nan))
        ma = np.convolve(y, np.ones(WINDOW) / WINDOW, mode="valid")
        score.append(np.interp(grid, x[WINDOW - 1:], ma, left=np.nan))
        with open(os.path.join("output_figs", rid, "summary.json")) as f:
            summary = json.load(f)
        first = int(x[np.argmax(feas == 1)]) if feas.any() else None
        stats.append({"run": rid, "seed": summary["args"]["seed"], "best": float(y.max()),
                      "first_feasible_sims": first, "n_feasible": int(feas.sum()),
                      "failed_sims": summary.get("n_failed_sims"), "runtime_s": summary.get("runtime_s"),
                      "critic_loss_mean": round(float(np.mean(closs)), 4) if closs else None})
    return grid, np.array(run_max), np.array(score), stats


def pooled_front(run_ids):
    pts = []
    for rid in run_ids:
        pts += [[sol[1]["area"] * 1e12, sol[1]["current"] * 1e6] for sol in load_solutions(rid)]
    if not pts:
        return np.empty((0, 2)), np.empty((0, 2))
    pts = np.array(pts)
    front = pts[is_pareto_efficient(pts)]
    return pts, front[np.argsort(front[:, 0])]


def plot_figure(name, suptitle, entries, out_dir, max_sims, group=""):
    """entries: [(label, [run_ids], color)]. Writes <out_dir>/<name>.png and .csv; returns the csv rows."""
    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(17, 5))
    rows = []
    for label, run_ids, color in entries:
        grid, run_max, score, stats = seed_curves(run_ids, max_sims)
        with np.errstate(all="ignore"):
            ax1.plot(grid, np.nanmean(run_max, 0), color=color, lw=2, label=f"{label}  ({len(stats)} seeds)")
            ax1.fill_between(grid, np.nanmin(run_max, 0), np.nanmax(run_max, 0), color=color, alpha=0.15, lw=0)
            ax2.plot(grid, np.nanmean(score, 0), color=color, lw=1.6, label=label)
        pts, front = pooled_front(run_ids)
        if len(pts):
            ax3.scatter(pts[:, 0], pts[:, 1], s=8, color=color, alpha=0.15, lw=0)
            ax3.step(front[:, 0], front[:, 1], where="post", color=color, lw=1.8, zorder=3)
            ax3.plot(front[:, 0], front[:, 1], "o", ms=6, mfc=color, mec="white", mew=1.2, zorder=4,
                     label=f"{label}: {len(pts)} feasible, front {len(front)} pts")
        bests = np.array([s["best"] for s in stats])
        firsts = [s["first_feasible_sims"] for s in stats if s["first_feasible_sims"] is not None]
        runtimes = [s["runtime_s"] for s in stats if s["runtime_s"]]
        rows.append({"group": group, "config": label, "run_ids": " ".join(s["run"] for s in stats),
                     "n_seeds": len(stats), "best_mean": round(bests.mean(), 4),
                     "best_std": round(bests.std(ddof=1), 4) if len(bests) > 1 else 0,
                     "best_min": round(bests.min(), 4), "best_max": round(bests.max(), 4),
                     "per_seed_best": " / ".join(f"{b:.3f}" for b in bests),
                     "first_feasible_median_sims": int(np.median(firsts)) if firsts else None,
                     "first_feasible_per_seed": " / ".join(str(s["first_feasible_sims"]) for s in stats),
                     "seeds_never_feasible": len(stats) - len(firsts),
                     "feasible_per_seed_mean": round(np.mean([s["n_feasible"] for s in stats]), 1),
                     "feasible_pooled": len(pts), "pareto_pts_pooled": len(front),
                     "front_min_area_um2": round(front[:, 0].min(), 1) if len(front) else None,
                     "front_min_current_uA": round(front[:, 1].min(), 1) if len(front) else None,
                     "failed_sims_per_seed": " / ".join(str(s["failed_sims"]) for s in stats),
                     "critic_loss_mean": round(float(np.mean([s["critic_loss_mean"] for s in stats
                                                              if s["critic_loss_mean"] is not None])), 4),
                     "runtime_s_per_seed": " / ".join(f"{t:.0f}" for t in runtimes)})

    for ax in (ax1, ax2):
        ax.axhline(0.3, color=MUTED, ls=":", lw=1)
        ax.set_xlim(0, max_sims)
        ax.set_xlabel("# simulations (reset included)")
        ax.grid(alpha=0.25, lw=0.6)
    ax1.text(max_sims, 0.3, "FoM 0.3: feasible, area & current at target", ha="right", va="bottom",
             fontsize=8, color=MUTED)
    ax1.set_ylim(-1.0, 0.8)
    ax1.set_ylabel("maximum FoM reached")
    ax1.set_title("(a) best FoM so far: mean over seeds, band = min-max", loc="left", fontsize=10, color=INK)
    ax1.legend(fontsize=8, frameon=False, loc="lower right")
    ax2.set_ylim(-3.0, 0.6)
    ax2.set_ylabel(f"FoM of the proposed design ({WINDOW}-step moving average)")
    ax2.set_title("(b) per-step score: what the policy proposes, mean over seeds", loc="left", fontsize=10, color=INK)
    ax2.legend(fontsize=8, frameon=False, loc="lower right")
    ax3.set_xlabel("active area [µm²]")
    ax3.set_ylabel("total current [µA]")
    ax3.set_xlim(left=0)
    ax3.set_ylim(0, 1000)
    ax3.grid(alpha=0.25, lw=0.6, ls="--")
    ax3.set_title("(c) current-area Pareto front, feasible designs pooled over the seeds",
                  loc="left", fontsize=10, color=INK)
    ax3.legend(fontsize=7.5, frameon=False, loc="upper right")
    fig.suptitle(suptitle, x=0.01, ha="left", fontsize=12, color=INK)
    fig.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    fig.savefig(os.path.join(out_dir, f"{name}.png"), dpi=160)
    plt.close(fig)
    write_csv(os.path.join(out_dir, f"{name}.csv"), rows)
    print(f"{name:10s} " + " | ".join(f"{r['config'].split(' (')[0]}: {r['best_mean']:.3f}±{r['best_std']:.3f}, "
                                       f"1st feas {r['first_feasible_median_sims']}, front {r['pareto_pts_pooled']}"
                                       for r in rows))
    return rows


def _sweep_entries(configs, default_label="default"):
    entries = [(default_label, [DEFAULT[1] + s for s in SWEEP_SEEDS], DEFAULT_COLOR)]
    return entries + [(label, [rid + s for s in SWEEP_SEEDS], color) for (label, rid), color in zip(configs, COLORS)]


def _style():
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                         "axes.spines.right": False})


def grid():
    """Compact figure for the report: the maximum-FoM panel of the five sweep groups (3 + 2 layout),
    legend = best FoM mean +- std over the 3 seeds. Written to output_figs/sweep_3seeds/sweep_grid.png."""
    _style()
    fig = plt.figure(figsize=(15, 8))
    gs = fig.add_gridspec(2, 6)
    slots = [gs[0, 0:2], gs[0, 2:4], gs[0, 4:6], gs[1, 1:3], gs[1, 3:5]]
    for slot, (name, (title, configs)), letter in zip(slots, GROUPS.items(), "abcde"):
        ax = fig.add_subplot(slot)
        for label, run_ids, color in _sweep_entries(configs):
            g, run_max, _, stats = seed_curves(run_ids, 2000)
            bests = [s["best"] for s in stats]
            with np.errstate(all="ignore"):
                ax.plot(g, np.nanmean(run_max, 0), color=color, lw=1.8,
                        label=f"{label}: {np.mean(bests):.2f} ± {np.std(bests, ddof=1):.2f}")
                ax.fill_between(g, np.nanmin(run_max, 0), np.nanmax(run_max, 0), color=color, alpha=0.13, lw=0)
        ax.axhline(0.3, color=MUTED, ls=":", lw=1)
        ax.set_xlim(0, 2000)
        ax.set_ylim(-1.0, 0.8)
        ax.set_xlabel("# simulations")
        ax.set_ylabel("maximum FoM reached")
        ax.set_title(f"({letter}) {title}", loc="left", fontsize=9.5, color=INK)
        ax.grid(alpha=0.25, lw=0.6)
        ax.legend(fontsize=7.5, frameon=False, loc="lower right")
    fig.suptitle("TD3 hyperparameter sweep, 3 seeds × 2000 simulations per configuration: mean over seeds, "
                 "band = min-max; legend = best FoM mean ± std", x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout()
    out = os.path.join("output_figs", "sweep_3seeds", "sweep_grid.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print("written", out)


def gamma_score():
    """Stand-alone figure: per-step score (50-step moving average, mean over seeds) of the γ group.
    Written to output_figs/sweep_3seeds/gamma_score.png."""
    _style()
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    for label, run_ids, color in _sweep_entries(GROUPS["gamma"][1], "default (γ 0.99)"):
        g, _, score, _ = seed_curves(run_ids, 2000)
        with np.errstate(all="ignore"):
            ax.plot(g, np.nanmean(score, 0), color=color, lw=1.5, label=label)
    ax.axhline(0.3, color=MUTED, ls=":", lw=1)
    ax.text(2000, 0.3, "FoM 0.3: feasible, targets met", ha="right", va="bottom", fontsize=7.5, color=MUTED)
    ax.set_xlim(0, 2000)
    ax.set_ylim(-3.0, 0.6)
    ax.set_xlabel("# simulations")
    ax.set_ylabel(f"FoM of the proposed design ({WINDOW}-step moving average)")
    ax.set_title("Per-step score vs. discount factor γ (mean over 3 seeds)", loc="left", fontsize=9.5, color=INK)
    ax.grid(alpha=0.25, lw=0.6)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    fig.tight_layout()
    out = os.path.join("output_figs", "sweep_3seeds", "gamma_score.png")
    fig.savefig(out, dpi=160)
    plt.close(fig)
    print("written", out)


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def sweep():
    out_dir = os.path.join("output_figs", "sweep_3seeds")
    all_rows = []
    for name, (title, configs) in GROUPS.items():
        entries = [(DEFAULT[0], [DEFAULT[1] + s for s in SWEEP_SEEDS], DEFAULT_COLOR)]
        entries += [(label, [rid + s for s in SWEEP_SEEDS], color) for (label, rid), color in zip(configs, COLORS)]
        all_rows += plot_figure(name, f"TD3 hyperparameter sweep, {title}: 3 seeds × 2000 simulations per configuration",
                                entries, out_dir, max_sims=2000, group=name)
    write_csv(os.path.join(out_dir, "all_groups.csv"), all_rows)
    print("written", out_dir)


def final():
    out_dir = os.path.join("output_figs", "baseline_cmp_seeds")
    rows = plot_figure("td3_vs_sac", "Final TD3 configurations vs. the TAs' SAC baseline: 5000 simulations per run, "
                       "5 / 5 / 3 seeds", FINAL, out_dir, max_sims=5000, group="final")
    # per-seed table next to the aggregate
    per_seed = []
    for label, run_ids, _ in FINAL:
        _, _, _, stats = seed_curves(run_ids, 5000)
        for s in stats:
            per_seed.append({"config": label, **s})
    write_csv(os.path.join(out_dir, "td3_vs_sac_per_seed.csv"), per_seed)
    for r in per_seed:
        print(f"    {r['config']:20s} {r['run']:18s} seed {r['seed']:7d}  best {r['best']:.4f}  first feasible "
              f"{str(r['first_feasible_sims']):5s}  {r['n_feasible']:5d} feasible  {r['failed_sims']:3d} failed  {r['runtime_s']:6.0f} s")
    print("written", out_dir)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "both"
    if what in ("sweep", "both"):
        sweep()
    if what in ("final", "both"):
        final()
    if what in ("grid", "both"):
        grid()
        gamma_score()
