"""
Compare our measurements with the TA reference designs.

Run from the CAD/ folder:
    python compare_references.py

Each of the 5 designs in Reference_Designs/references.csv is simulated with the normal
pipeline (TwoStage.cir as it is: 27 degC, 1 ns transient step; dut_testbench.py:
slew rate = rising edge, 10-90 %) and, for comparison, the same netlist at 25 degC.
Every spec is compared with the reference value.

Outputs
  Reference_Designs/comparison.csv   reference, value at each temperature, % difference, within +-5 %
  Reference_Designs/comparison.png   % difference per spec and design, with the +-5 % band
"""
import os
import sys

import numpy as np
import pandas as pd

CAD_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(CAD_DIR)                                   # NgspiceWrapper builds paths from os.getcwd()
sys.path.insert(0, CAD_DIR)
from ngspice_interface import DUT                   # noqa: E402

YAML_PATH = os.path.join(CAD_DIR, "ngspice_interface", "files", "yaml_files", "TwoStage.yaml")
REFERENCE_CSV = os.path.join(CAD_DIR, "Reference_Designs", "references.csv")
OUT_CSV = os.path.join(CAD_DIR, "Reference_Designs", "comparison.csv")
OUT_PNG = os.path.join(CAD_DIR, "Reference_Designs", "comparison.png")

LIMIT_PCT = 5.0
SPECS = ["area", "current", "gain", "noise", "phm", "slewRate", "ugbw"]
SPEC_LABELS = {"area": "Area", "current": "Current", "gain": "DC gain", "noise": "Noise",
               "phm": "Phase margin", "slewRate": "Slew rate", "ugbw": "UGBW"}

# name -> temperature passed to create_new_netlist (None = keep TwoStage.cir's own value, 27 degC).
# Everything else (1 ns transient step, measurements) is the normal pipeline.
SETTINGS = {
    "27C": None,
    "25C": 25,
}
CURRENT = "27C"


def read_references(path):
    """references.csv has one column per design; return {design: (params, specs)} and the units."""
    ref = pd.read_csv(path, index_col=0)
    units = ref["Unit"]
    ref = ref.drop(columns="Unit")
    designs = {}
    for design in ref.columns:
        col = ref[design]
        params = {k[len("param_"):]: float(v) for k, v in col.items() if k.startswith("param_")}
        for k in params:
            if k.startswith("m"):                    # multipliers must be integers in the netlist
                params[k] = int(round(params[k]))
        specs = {s: float(col["spec_" + s]) for s in SPECS}
        designs[design] = (params, specs)
    return designs, {s: units["spec_" + s] for s in SPECS}


def measure(dut, params, temp):
    netlist = dut.create_new_netlist(params, "TT", temp_pvt=temp)
    if dut.simulate(netlist) != 0:
        raise RuntimeError(f"ngspice failed on {netlist}")
    return dut.measure_metrics()


def build_table():
    dut = DUT(YAML_PATH)
    designs, units = read_references(REFERENCE_CSV)
    rows = []
    for design, (params, ref_specs) in designs.items():
        results = {name: measure(dut, params, temp) for name, temp in SETTINGS.items()}
        for spec in SPECS:
            ref = ref_specs[spec]
            row = {"design": design, "spec": spec, "unit": units[spec], "reference": ref}
            for name in SETTINGS:
                ours = results[name][spec]
                row[f"{name}_value"] = ours
                row[f"{name}_diff_pct"] = 100.0 * (ours - ref) / ref
                row[f"{name}_within_5pct"] = abs(row[f"{name}_diff_pct"]) <= LIMIT_PCT
            rows.append(row)
        print(f"  simulated {design}")
    return pd.DataFrame(rows)


def plot(table):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    ink, muted, grid, surface = "#1f1f1e", "#6b6a63", "#e4e3dc", "#fcfcfb"
    colors = {"27C": "#2a78d6", "25C": "#eb6834"}            # validated pair: CVD dE 24.7
    labels = {"27C": "27 °C (TwoStage.cir)", "25C": "25 °C (for comparison)"}
    order = ["25C", "27C"]
    designs = list(dict.fromkeys(table["design"]))
    x = np.arange(len(designs))
    width = 0.36

    fig, axes = plt.subplots(2, 4, figsize=(13, 6.0), facecolor=surface)
    for ax, spec in zip(axes.flat, SPECS):
        sub = table[table["spec"] == spec].set_index("design").loc[designs]
        ax.set_facecolor(surface)
        ax.axhspan(-LIMIT_PCT, LIMIT_PCT, color="#2a78d6", alpha=0.06, lw=0, zorder=0)
        for lim in (-LIMIT_PCT, LIMIT_PCT):
            ax.axhline(lim, color=muted, lw=0.8, ls=(0, (3, 3)), zorder=1)
        ax.axhline(0, color=muted, lw=1, zorder=1)
        for i, name in enumerate(order):
            vals = sub[f"{name}_diff_pct"].to_numpy()
            xs = x + (i - 0.5) * (width + 0.02)
            ax.bar(xs, vals, width, color=colors[name], edgecolor=surface, linewidth=1, zorder=3)
            # a dot on every bar end, so values close to 0 % stay visible
            ax.plot(xs, vals, "o", ms=5.5, color=colors[name], mec=surface, mew=1.2, zorder=4)
        w27 = sub["27C_diff_pct"].abs().max()
        w25 = sub["25C_diff_pct"].abs().max()
        ax.set_title(f"{SPEC_LABELS[spec]}   (max: 27 °C {w27:.2f} %, 25 °C {w25:.2f} %)",
                     fontsize=9.5, color=ink, loc="left")
        ax.set_xticks(x, [d.replace("Design ", "D") for d in designs], fontsize=9, color=muted)
        cols = [f"{n}_diff_pct" for n in order]
        lo = min(-LIMIT_PCT * 1.6, sub[cols].min().min() * 1.15)
        hi = max(LIMIT_PCT * 1.6, sub[cols].max().max() * 1.15)
        ax.set_ylim(lo, hi)
        ax.tick_params(axis="y", labelsize=8, colors=muted, length=0)
        ax.tick_params(axis="x", length=0)
        ax.grid(axis="y", color=grid, lw=0.6, zorder=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(grid)
        ax.set_ylabel("difference vs reference (%)" if spec in ("area", "phm") else "",
                      fontsize=8, color=muted)

    legend_ax = axes.flat[-1]
    legend_ax.axis("off")
    handles = [Line2D([], [], marker="s", ls="", ms=10, color=colors[n]) for n in ["27C", "25C"]]
    handles.append(plt.Rectangle((0, 0), 1, 1, color="#2a78d6", alpha=0.12))
    legend_ax.legend(handles, [labels[n] for n in ["27C", "25C"]] + [f"±{LIMIT_PCT:.0f} % band"],
                     loc="center left", frameon=False, fontsize=9.5, labelcolor=ink)
    fig.suptitle("Our measurements vs. the TA reference designs", x=0.01, ha="left",
                 fontsize=13, color=ink)
    fig.text(0.01, 0.925, "(ours − reference) / reference, per design. 1 ns transient step, "
             "rising-edge slew rate. Each panel has its own y-scale; the shaded band is ±5 %.",
             fontsize=9, color=muted)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(OUT_PNG, dpi=160, facecolor=surface)
    plt.close(fig)


def main():
    print("Simulating the reference designs at 27 degC and 25 degC ...")
    table = build_table()
    table.to_csv(OUT_CSV, index=False, float_format="%.6g")
    plot(table)

    names = list(SETTINGS)
    print("\n% difference vs reference:")
    print(f"{'design':9s} {'spec':9s} {'reference':>11s} " + " ".join(f"{n:>10s}" for n in names))
    for _, r in table.iterrows():
        cells = " ".join(f"{r[f'{n}_diff_pct']:+9.3f}%" for n in names)
        flag = "" if r[f"{CURRENT}_within_5pct"] else "   <-- 27 degC outside 5 %"
        print(f"{r['design']:9s} {r['spec']:9s} {r['reference']:11.5g} {cells}{flag}")
    print()
    for n in names:
        ok = int(table[f"{n}_within_5pct"].sum())
        print(f"{n}: {ok}/{len(table)} values within ±{LIMIT_PCT:.0f} %   "
              f"(worst {table[f'{n}_diff_pct'].abs().max():.3f} %)")
    print(f"\nSaved {OUT_CSV}\n      {OUT_PNG}")


if __name__ == "__main__":
    main()
