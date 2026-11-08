"""One LLM-harness run as a trace: FoM of every simulated design vs. simulator call, coloured by who
proposed it (LLM roles / RL warm-up neighbours / TD3 training steps), the running maximum, the phase
boundaries and the key candidates.

    python plot_run_trace.py harness_20261106_232516 [--mark 20 625 730] [--ymin -1.5]

Reads harness_runs/<run>/log.csv; writes output_figs/comparison/run_<id>_trace.png.
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from compare_runs import harness_dir

INK, MUTED = "#222222", "#8a8a8a"
SOURCE_STYLE = {   # source in log.csv -> (label, colour, marker, size)
    "llm": ("LLM roles (analyst / sizer / sweep)", "#2a78d6", "o", 28),
    "rl_warmup": ("RL warm-up: sparse neighbours of the best designs", "#3aa655", "^", 14),
    "rl_train": ("TD3 training steps", "#eb6834", ".", 10),
    "rl_reset": ("RL random reset", "#8e5bd8", "x", 14),
    "local": ("local search", "#d4418e", "s", 14),
}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run")
    p.add_argument("--mark", nargs="*", type=int, default=[], help="candidate ids to annotate")
    p.add_argument("--ymin", type=float, default=-1.5)
    a = p.parse_args()
    df = pd.read_csv(os.path.join(harness_dir(a.run), "log.csv"))
    x, y = df["sim_call"].to_numpy(), df["reward"].to_numpy()
    run_max = np.maximum.accumulate(y)

    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(13, 5.2))

    # phase bands: consecutive runs of LLM vs RL sources
    is_llm = (df["source"] == "llm").to_numpy()
    seg = np.r_[0, np.nonzero(np.diff(is_llm.astype(int)))[0] + 1, len(df)]
    for s, e in zip(seg[:-1], seg[1:]):
        if is_llm[s]:
            ax.axvspan(x[s] - 0.5, x[e - 1] + 0.5, color="#2a78d6", alpha=0.07, lw=0)
    ax.axhline(0.3, color=MUTED, ls=":", lw=1)
    ax.text(x[-1], 0.3, "FoM 0.3: feasible, area & current at target", ha="right", va="bottom", fontsize=8, color=MUTED)

    for src, (label, color, marker, size) in SOURCE_STYLE.items():
        m = (df["source"] == src).to_numpy()
        if m.any():
            ax.scatter(x[m], np.clip(y[m], a.ymin, None), s=size, color=color, marker=marker, alpha=0.75,
                       lw=0.6 if marker in "ox" else 0, edgecolors="white" if marker == "o" else None,
                       label=f"{label} ({m.sum()} sims)", zorder=3)
    ax.step(x, run_max, where="post", color=INK, lw=1.8, label="best FoM so far", zorder=4)

    for cid in a.mark:
        row = df[df["candidate_id"] == cid]
        if row.empty:
            continue
        xi, yi = int(row["sim_call"].iloc[0]), float(row["reward"].iloc[0])
        ax.annotate(f"id {cid}\nFoM {yi:+.3f}", (xi, yi), xytext=(0, 28), textcoords="offset points",
                    ha="center", fontsize=8, color=INK,
                    arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))

    below = int((y < a.ymin).sum())
    ax.set_ylim(a.ymin, 0.85)
    ax.set_xlim(0, x[-1] + 5)
    ax.set_xlabel(f"simulator call  (blue bands: LLM phases; {below} designs below {a.ymin} are drawn at the bottom edge)")
    ax.set_ylabel("FoM of the simulated design")
    ax.grid(alpha=0.25, lw=0.6)
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    best = df.loc[df["reward"].idxmax()]
    ax.set_title(f"{a.run}: {len(df)} simulator calls, best FoM {best['reward']:.3f} (id {int(best['candidate_id'])}, "
                 f"{best['source']}), first feasible at call {int(df[df['feasible'] == 1]['sim_call'].iloc[0]) if (df['feasible'] == 1).any() else '—'}",
                 loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    out = os.path.join("output_figs", "comparison", f"run_{a.run.replace('harness_', '')}_trace.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=160)
    print("saved", out)


if __name__ == "__main__":
    main()
