"""Two groups of LLM-harness runs on one figure: (a) best FoM vs. simulator calls of every run,
(b) feasible designs of each group with the group's pooled current-area Pareto front.

    python plot_group_compare.py --a "task 1" id1 id2 ... --b "task 1+2" id3 id4 ... [--out NAME]

Reads harness_runs/<id>/log.csv. Writes output_figs/comparison/<out>.png and .csv (pooled fronts).
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from plot_harness_runs import INK, MUTED, pareto_front
from compare_runs import harness_dir

COLORS = ["#2a78d6", "#eb6834"]      # categorical slots 1-2 of the dataviz reference palette
MARKERS = ["o", "s"]


def load(run_id, max_sims):
    df = pd.read_csv(os.path.join(harness_dir(run_id), "log.csv"))
    df = df[df["sim_call"] <= max_sims].copy()
    specs = df["specs"].map(json.loads)
    df["current_uA"] = specs.map(lambda s: s["current"] * 1e6)
    df["area_um2"] = specs.map(lambda s: s["area"] * 1e12)
    df["best"] = df["reward"].cummax()
    return df


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--a", nargs="+", required=True, metavar=("LABEL", "RUN"))
    p.add_argument("--b", nargs="+", required=True, metavar=("LABEL", "RUN"))
    p.add_argument("--max-sims", type=int, default=1000)
    p.add_argument("--title", default="LLM harness, Gemini 3.8 Flash (High)")
    p.add_argument("--out", default="harness_group_compare")
    a = p.parse_args()
    groups = [(a.a[0], a.a[1:]), (a.b[0], a.b[1:])]

    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    rows = []
    for (label, runs), c, m in zip(groups, COLORS, MARKERS):
        feas, bests = [], []
        for k, run in enumerate(runs):
            df = load(run, a.max_sims)
            bests.append(df["best"].iloc[-1])
            ax1.step(df["sim_call"], df["best"], where="post", color=c, lw=1.6, alpha=0.85,
                     label=f"{label} ({len(runs)} runs)" if k == 0 else None)
            f = df[df["feasible"] == 1]
            if len(f):
                ax1.plot(f["sim_call"].iloc[0], f["best"].iloc[0], m, ms=7, mfc=c, mec="white", mew=1.2, zorder=4)
                feas.append(f)
        f = pd.concat(feas)
        cur, ar = f["current_uA"].to_numpy(), f["area_um2"].to_numpy()
        ax2.scatter(cur, ar, s=10, color=c, alpha=0.2, lw=0)
        fr = pareto_front(cur, ar)
        ax2.step(cur[fr], ar[fr], where="post", color=c, lw=2, zorder=3)
        ax2.plot(cur[fr], ar[fr], m, ms=8, mfc=c, mec="white", mew=1.5, zorder=4,
                 label=f"{label}: {len(f)} feasible, pooled front {len(fr)} pts, "
                       f"best FoM {np.mean(bests):.3f} ± {np.std(bests, ddof=1):.3f}")
        for i in fr:
            rows.append({"group": label, "current_uA": round(cur[i], 1), "area_um2": round(ar[i], 1),
                         "reward": round(float(f["reward"].iloc[i]), 4), "run": f["sim_call"].index[i]})

    ax1.axhline(0.3, color=MUTED, ls=":", lw=1)
    ax1.text(a.max_sims, 0.3, "feasible (FoM > 0.3)", ha="right", va="bottom", fontsize=8, color=MUTED)
    ax1.set_xlim(0, a.max_sims)
    ax1.set_ylim(bottom=max(-1.5, ax1.get_ylim()[0]))
    ax1.set_xlabel("simulator calls")
    ax1.set_ylabel("best FoM so far")
    ax1.set_title(f"(a) best FoM within {a.max_sims} simulations  (marker = first feasible design)",
                  loc="left", fontsize=10, color=INK)
    ax1.legend(fontsize=9, frameon=False, loc="lower right", bbox_to_anchor=(1, 0.08))
    ax2.set_xlabel("current [µA]")
    ax2.set_ylabel("area [µm²]")
    ax2.set_title("(b) feasible designs and pooled Pareto front per group (lower-left is better)",
                  loc="left", fontsize=10, color=INK)
    ax2.legend(fontsize=8, frameon=False, loc="upper right")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.25, lw=0.6)
    fig.suptitle(a.title, x=0.01, ha="left", fontsize=12, color=INK)
    fig.tight_layout()

    out_dir = os.path.join("output_figs", "comparison")
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, a.out + ".png")
    fig.savefig(png, dpi=160)
    pd.DataFrame(rows).drop(columns="run").to_csv(os.path.join(out_dir, a.out + ".csv"), index=False)
    print("saved", png)


if __name__ == "__main__":
    main()
