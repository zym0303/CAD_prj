"""Runtime and simulations vs. max FoM: LLM harness vs. pure RL sizer.

    python compare_harness.py --harness harness_20261106_101500 --rl final_g0

Reads harness_runs/<id>/log.csv and output_figs/<rl>/history.csv. Writes
output_figs/comparison/harness_vs_rl.png and harness_vs_rl.csv (time and simulations
needed to reach FoM thresholds, and the cheap quick_analysis runs of each harness run).
"""
import argparse
import ast
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def load_harness(run_id):
    df = pd.read_csv(os.path.join("harness_runs", run_id, "log.csv"))
    return pd.DataFrame({"time": df["elapsed_s"], "sims": df["sim_call"],
                         "fom": df["reward"].cummax(), "source": df["source"]})


def quick_runs(run_id):
    """Cheap quick_analysis ngspice runs of a harness run (0 for runs before that tool)."""
    try:
        with open(os.path.join("harness_runs", run_id, "summary.json")) as f:
            return int(json.load(f).get("quick_runs", 0))
    except (OSError, ValueError):
        return 0


def load_rl(run_id):
    df = pd.read_csv(os.path.join("output_figs", run_id, "history.csv"))
    return pd.DataFrame({"time": df["wall_time_s"], "sims": df["n_simulations"],
                         "fom": df["reward"].cummax()})


def first_reach(df, threshold):
    hit = df[df["fom"] >= threshold]
    return (None, None) if hit.empty else (float(hit["time"].iloc[0]), int(hit["sims"].iloc[0]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--harness", nargs="+", required=True, help="harness run ids")
    p.add_argument("--rl", default="final_g0", help="td3_runner run id")
    a = p.parse_args()

    curves = {f"LLM harness ({h})": load_harness(h) for h in a.harness}
    curves[f"TD3 only ({a.rl})"] = load_rl(a.rl)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for label, df in curves.items():
        axes[0].step(df["time"].clip(lower=1), df["fom"], where="post", label=label)
        axes[1].step(df["sims"], df["fom"], where="post", label=label)
    for ax, xl in zip(axes, ["runtime [s] (log)", "simulator calls (log)"]):
        ax.axhline(0.3, color="grey", ls=":", lw=1)  # FoM > 0.3 <=> feasible
        ax.set_xlabel(xl)
        ax.set_ylabel("max FoM reached")
        ax.set_ylim(bottom=-1)
        ax.grid(alpha=0.3)
    axes[0].set_xscale("log")
    axes[1].set_xscale("log")
    axes[0].legend()
    os.makedirs("output_figs/comparison", exist_ok=True)
    fig.tight_layout()
    fig.savefig("output_figs/comparison/harness_vs_rl.png", dpi=150)

    # Current-area Pareto front: feasible harness designs vs. the pure-RL feasible designs
    def front(points):
        out, best_area = [], float("inf")
        for c, a in sorted(points):
            if a < best_area:
                out.append((c, a)); best_area = a
        return out
    fig2, ax = plt.subplots(figsize=(6, 4.5))
    sets = {}
    for h in a.harness:
        log = pd.read_csv(os.path.join("harness_runs", h, "log.csv"))
        feas = log[log["feasible"] == 1]["specs"].map(json.loads)
        sets[f"LLM harness ({h})"] = [(s["current"] * 1e6, s["area"] * 1e12) for s in feas]
    try:
        from compare_runs import solutions_csv
        sol = pd.read_csv(solutions_csv(a.rl))
        specs = sol["Specs"].map(lambda t: ast.literal_eval(t) if isinstance(t, str) else t)
        sets[f"TD3 only ({a.rl})"] = [(float(s["current"]) * 1e6, float(s["area"]) * 1e12) for s in specs]
    except Exception as e:  # the RL file format is optional for this plot
        print("RL Pareto skipped:", e)
    for label, pts in sets.items():
        if not pts:
            continue
        c, ar = zip(*pts)
        sc = ax.scatter(c, ar, s=8, alpha=0.3)
        fc, fa = zip(*front(pts))
        ax.step(fc, fa, where="post", color=sc.get_facecolor()[0][:3], label=f"{label}: {len(pts)} feasible, {len(fc)} on front")
    ax.set_xlabel("current [uA]"); ax.set_ylabel("area [um^2]"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    fig2.tight_layout(); fig2.savefig("output_figs/comparison/pareto_harness_vs_rl.png", dpi=150)

    rl_best = curves[f"TD3 only ({a.rl})"]["fom"].iloc[-1]
    thresholds = [0.3, 0.5, 0.6, round(0.98 * rl_best, 3)]
    rows = []
    for label, df in curves.items():
        row = {"method": label, "best_fom": round(df["fom"].iloc[-1], 4),
               "total_time_s": round(df["time"].iloc[-1], 1), "total_sims": int(df["sims"].iloc[-1]),
               # cheap analyses are ngspice runs too: always reported next to the simulator calls
               "quick_runs": quick_runs(label[len("LLM harness ("):-1]) if label.startswith("LLM harness") else 0}
        for t in thresholds:
            tt, ss = first_reach(df, t)
            row[f"time_to_{t}"], row[f"sims_to_{t}"] = tt, ss
        rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv("output_figs/comparison/harness_vs_rl.csv", index=False)
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
