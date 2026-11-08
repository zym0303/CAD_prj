"""Several LLM-harness runs in one figure: (a) best FoM vs. simulator calls, (b) current-area
Pareto front of the feasible designs.

    python plot_harness_runs.py harness_20261106_222948 harness_20261106_224902 ...
    python plot_harness_runs.py --root ~/CAD_prj_archive --max-sims 1000 --title "Flash High" <ids>

Reads <root>/harness_runs/<id>/log.csv. Writes <root>/output_figs/comparison/<out>.png and a
.csv with the numbers behind the figure (best FoM, sims to first feasible, front size).
"""
import argparse
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from compare_runs import _find_dir

# categorical slots 1-5 of the dataviz reference palette, fixed order (run i -> slot i)
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
MARKERS = ["o", "s", "^", "D", "v", "P"]
INK, MUTED = "#2b2b29", "#76756d"


def pareto_front(cur, area):
    """Non-dominated points (minimise current and area), sorted by current."""
    order = np.lexsort((area, cur))
    front, best = [], np.inf
    for i in order:
        if area[i] < best:
            front.append(i)
            best = area[i]
    return np.array(front, dtype=int)


def load(root, run_id, max_sims):
    df = pd.read_csv(os.path.join(_find_dir(os.path.join(root, "harness_runs"), run_id), "log.csv"))
    df = df[df["sim_call"] <= max_sims].copy()
    specs = df["specs"].map(json.loads)
    df["current_uA"] = specs.map(lambda s: s["current"] * 1e6)
    df["area_um2"] = specs.map(lambda s: s["area"] * 1e12)
    df["best"] = df["reward"].cummax()
    return df


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("runs", nargs="+")
    p.add_argument("--root", default=".", help="folder holding harness_runs/ (e.g. ~/CAD_prj_archive)")
    p.add_argument("--max-sims", type=int, default=1000)
    p.add_argument("--title", default="LLM harness")
    p.add_argument("--out", default="harness_runs_fom_pareto")
    a = p.parse_args()
    root = os.path.expanduser(a.root)

    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    rows = []
    for i, run in enumerate(a.runs):
        df = load(root, run, a.max_sims)
        c, m = COLORS[i % len(COLORS)], MARKERS[i % len(MARKERS)]
        label = f"run {i + 1} ({run.removeprefix('harness_')})"
        feas = df[df["feasible"] == 1]
        first = int(feas["sim_call"].iloc[0]) if len(feas) else None

        # (a) best FoM so far vs. simulations
        ax1.step(df["sim_call"], df["best"], where="post", color=c, lw=2,
                 label=f"{label}: best {df['best'].iloc[-1]:.3f}, feasible @ sim {first}")
        if first:
            ax1.plot(first, df.loc[df["sim_call"] == first, "best"].iloc[0], m, ms=8,
                     mfc=c, mec="white", mew=1.5, zorder=4)

        # (b) feasible designs and their Pareto front
        n_front = 0
        if len(feas):
            cur, ar = feas["current_uA"].to_numpy(), feas["area_um2"].to_numpy()
            ax2.scatter(cur, ar, s=10, color=c, alpha=0.18, lw=0)
            f = pareto_front(cur, ar)
            n_front = len(f)
            ax2.step(cur[f], ar[f], where="post", color=c, lw=2, zorder=3)
            ax2.plot(cur[f], ar[f], m, ms=8, mfc=c, mec="white", mew=1.5, zorder=4,
                     label=f"{label}: {len(feas)} feasible, {n_front} on front")
        rows.append({"run": run, "sims": int(df["sim_call"].iloc[-1]), "elapsed_s": float(df["elapsed_s"].iloc[-1]),
                     "best_fom": round(float(df["best"].iloc[-1]), 4), "first_feasible_sim": first,
                     "n_feasible": len(feas), "n_front": n_front,
                     "llm_sims": int((df["source"] == "llm").sum())})

    ax1.axhline(0.3, color=MUTED, ls=":", lw=1)
    ax1.text(a.max_sims, 0.3, "feasible (FoM > 0.3)", ha="right", va="bottom", fontsize=8, color=MUTED)
    ax1.set_xlim(0, a.max_sims)
    ax1.set_ylim(bottom=max(-1.5, ax1.get_ylim()[0]))
    ax1.set_xlabel("simulator calls")
    ax1.set_ylabel("best FoM so far")
    ax1.set_title(f"(a) best FoM within {a.max_sims} simulations  (marker = first feasible)",
                  loc="left", fontsize=10, color=INK)
    ax1.legend(fontsize=8, frameon=False, loc="lower right", bbox_to_anchor=(1, 0.08))

    ax2.set_xlabel("current [µA]")
    ax2.set_ylabel("area [µm²]")
    ax2.set_title("(b) Pareto front of feasible designs (lower-left is better)",
                  loc="left", fontsize=10, color=INK)
    ax2.legend(fontsize=8, frameon=False, loc="upper right")
    for ax in (ax1, ax2):
        ax.grid(alpha=0.25, lw=0.6)
    fig.suptitle(a.title, x=0.01, ha="left", fontsize=12, color=INK)
    fig.tight_layout()

    out_dir = os.path.join(root, "output_figs", "comparison")
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, a.out + ".png")
    fig.savefig(png, dpi=160)
    table = pd.DataFrame(rows)
    table.to_csv(os.path.join(out_dir, a.out + ".csv"), index=False)
    print(table.to_string(index=False))
    print("saved", png)


if __name__ == "__main__":
    main()
