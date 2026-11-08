"""Milestone 4: LLM harness vs. RL alone, maximum FoM reached vs. runtime and vs. simulator calls.

    python compare_runtime.py \
        --harness "LLM harness (task 1)" harness_20261106_222948 harness_20261106_224902 harness_20261106_230657 \
                                         harness_20261106_232516 harness_20261106_234417 \
        --rl "TD3 alone, w 128, gamma 0" final_g0 --rl "TD3 alone, w 128, gamma 0.99" final_g099 \
        --rl "SAC baseline alone" sac_baseline

Harness runs: harness_runs/<id>/log.csv (elapsed_s, sim_call, reward; the clock starts at the first
tool call, so LLM latency is included). RL runs: output_figs/<id>/history.csv (wall_time_s,
n_simulations, reward; ngspice time only). Only RL runs that ran alone on the machine should be
given (parallel runs have inflated wall times).

Writes output_figs/comparison/<out>.png (a: FoM vs runtime, log x; b: FoM vs simulator calls, log x;
c: current-area Pareto fronts, harness runs pooled vs. each RL run) and harness_vs_rl_runtime.csv: per run, the runtime and simulator calls needed to reach
FoM 0.3 / 0.5 / 0.6 / 0.65, the best FoM at 1000 s and at 900 simulator calls, the final best FoM.
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import json

import numpy as np
import pandas as pd

from compare_runs import load_solutions
from utils.plotting import is_pareto_efficient
from compare_runs import harness_dir, run_dir

INK, MUTED = "#222222", "#8a8a8a"
HARNESS_COLOR = "#2a78d6"
RL_COLORS = ["#eb6834", "#3aa655", "#8e5bd8", "#d4418e"]
THRESHOLDS = [0.3, 0.5, 0.6, 0.65]


def load_harness(run_id):
    df = pd.read_csv(os.path.join(harness_dir(run_id), "log.csv"))
    return df["elapsed_s"].to_numpy(), df["sim_call"].to_numpy(), df["reward"].cummax().to_numpy()


def load_rl(run_id):
    df = pd.read_csv(os.path.join(run_dir(run_id), "history.csv"))
    return df["wall_time_s"].to_numpy(), df["n_simulations"].to_numpy(), df["reward"].cummax().to_numpy()


def harness_feasible(run_ids):
    pts = []
    for rid in run_ids:
        df = pd.read_csv(os.path.join(harness_dir(rid), "log.csv"))
        for spec in df.loc[df["feasible"] == 1, "specs"]:
            d = json.loads(spec)
            pts.append([d["current"] * 1e6, d["area"] * 1e12])
    return np.array(pts).reshape(-1, 2)


def rl_feasible(run_ids):
    pts = [[sol[1]["current"] * 1e6, sol[1]["area"] * 1e12] for rid in run_ids for sol in load_solutions(rid)]
    return np.array(pts).reshape(-1, 2)


def draw_front(ax, pts, color, marker, label):
    if not len(pts):
        return 0
    front = pts[is_pareto_efficient(pts)]
    front = front[np.argsort(front[:, 0])]
    ax.scatter(pts[:, 0], pts[:, 1], s=9, color=color, alpha=0.18, lw=0)
    ax.step(front[:, 0], front[:, 1], where="post", color=color, lw=1.8, zorder=3)
    ax.plot(front[:, 0], front[:, 1], marker, ms=6, mfc=color, mec="white", mew=1.2, zorder=4,
            label=f"{label}: {len(pts)} feasible, front {len(front)} pts")
    return len(front)


def first_reach(x, fom, threshold):
    hit = np.nonzero(fom >= threshold)[0]
    return float(x[hit[0]]) if len(hit) else None


def value_at(x, fom, limit):
    ok = x <= limit
    return float(fom[ok][-1]) if ok.any() else None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--harness", nargs="+", action="append", default=[], metavar=("LABEL", "RUN"))
    p.add_argument("--rl", nargs="+", action="append", default=[], metavar=("LABEL", "RUN"))
    p.add_argument("--out", default="harness_vs_rl_runtime")
    a = p.parse_args()

    plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                         "axes.spines.right": False})
    fig, (ax_t, ax_s, ax_p) = plt.subplots(1, 3, figsize=(18, 5))
    rows = []

    def add(label, run_id, t, s, fom, color, lw, alpha, legend):
        ax_t.step(np.clip(t, 1, None), fom, where="post", color=color, lw=lw, alpha=alpha, label=legend)
        ax_s.step(np.clip(s, 1, None), fom, where="post", color=color, lw=lw, alpha=alpha, label=legend)
        row = {"method": label, "run_id": run_id, "best_fom": round(float(fom[-1]), 4),
               "runtime_s": round(float(t[-1])), "simulator_calls": int(s[-1]),
               "fom_at_1000s": value_at(t, fom, 1000), "fom_at_900_sims": value_at(s, fom, 900)}
        for th in THRESHOLDS:
            tt, ss = first_reach(t, fom, th), first_reach(s, fom, th)
            row[f"time_to_{th}_s"] = None if tt is None else round(tt)
            row[f"sims_to_{th}"] = None if ss is None else int(ss)
        rows.append(row)

    for group in a.harness:
        label, runs = group[0], group[1:]
        for k, run in enumerate(runs):
            t, s, fom = load_harness(run)
            add(label, run, t, s, fom, HARNESS_COLOR, 1.5, 0.85, f"{label}, {len(runs)} runs" if k == 0 else None)
    for group, color in zip(a.rl, RL_COLORS):
        label, runs = group[0], group[1:]
        for k, run in enumerate(runs):
            t, s, fom = load_rl(run)
            add(label, run, t, s, fom, color, 2.0, 0.95, f"{label} ({run})" if k == 0 else None)

    for ax, xlabel, tag in ((ax_t, "runtime [s]  (harness: incl. LLM latency; RL: ngspice + updates)", "a"),
                            (ax_s, "simulator calls", "b")):
        ax.set_xscale("log")
        ax.axhline(0.3, color=MUTED, ls=":", lw=1)
        ax.set_ylim(-1.0, 0.8)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("maximum FoM reached")
        ax.grid(alpha=0.25, lw=0.6, which="both")
        ax.set_title(f"({tag}) maximum FoM vs. {'runtime' if tag == 'a' else 'simulator calls'}",
                     loc="left", fontsize=10, color=INK)
    ax_t.text(ax_t.get_xlim()[1], 0.3, "FoM 0.3: feasible, targets met", ha="right", va="bottom", fontsize=8, color=MUTED)
    ax_t.axvline(1000, color=HARNESS_COLOR, ls="--", lw=0.8, alpha=0.6)
    ax_t.text(1000, -0.95, " harness budget ≈ 1000 s", color=HARNESS_COLOR, fontsize=8)
    ax_s.axvline(900, color=HARNESS_COLOR, ls="--", lw=0.8, alpha=0.6)
    ax_s.text(900, -0.95, " harness budget 900-1000 sims", color=HARNESS_COLOR, fontsize=8)
    ax_t.legend(fontsize=8, frameon=False, loc="lower right", bbox_to_anchor=(1, 0.06))
    # (c) current-area Pareto fronts of the feasible designs, harness runs pooled vs. each RL method
    for group in a.harness:
        draw_front(ax_p, harness_feasible(group[1:]), HARNESS_COLOR, "o", f"{group[0]}, {len(group) - 1} runs pooled")
    for group, color in zip(a.rl, RL_COLORS):
        draw_front(ax_p, rl_feasible(group[1:]), color, "s", group[0])
    ax_p.set_xlabel("total current [µA]")
    ax_p.set_ylabel("active area [µm²]")
    ax_p.set_xlim(150, 700)
    ax_p.set_ylim(400, 1300)
    ax_p.grid(alpha=0.25, lw=0.6, ls="--")
    ax_p.set_title("(c) current-area Pareto front of the feasible designs", loc="left", fontsize=10, color=INK)
    ax_p.legend(fontsize=8, frameon=False, loc="upper right")
    fig.suptitle("LLM-based agentic harness vs. the RL sizer alone (single runs on the same machine)",
                 x=0.01, ha="left", fontsize=12, color=INK)
    fig.tight_layout()
    out_dir = os.path.join("output_figs", "comparison")
    os.makedirs(out_dir, exist_ok=True)
    fig.savefig(os.path.join(out_dir, a.out + ".png"), dpi=160)
    table = pd.DataFrame(rows)
    table.to_csv(os.path.join(out_dir, a.out + ".csv"), index=False)
    pd.set_option("display.width", 250)
    print(table.to_string(index=False))
    print("saved", os.path.join(out_dir, a.out + ".png"))


if __name__ == "__main__":
    main()
