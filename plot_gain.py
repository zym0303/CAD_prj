"""
Gain vs. frequency (Bode magnitude) of the TA reference designs.

Run from the CAD/ folder:
    python plot_gain.py

For each design in Reference_Designs/references.csv it runs the normal pipeline
(TwoStage.cir as it is: 27 degC) and plots |H(f)| = |v(net6)| over the whole AC sweep,
together with the TAs' reference values:
  - reference DC gain   -> diamond at 1 Hz (where find_dc_gain reads the gain)
  - reference UGBW      -> diamond at |H| = 1
The same designs at 25 degC are drawn dashed, for comparison.

Outputs
  Reference_Designs/gain_vs_frequency.png   one panel per design
  Reference_Designs/gain_vs_frequency.csv   the data: frequency and |H| per design and temperature
"""
import os
import sys

import numpy as np
import pandas as pd

CAD_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(CAD_DIR)
sys.path.insert(0, CAD_DIR)
from ngspice_interface import DUT          # noqa: E402

YAML_PATH = os.path.join(CAD_DIR, "ngspice_interface", "files", "yaml_files", "TwoStage.yaml")
REFERENCE_CSV = os.path.join(CAD_DIR, "Reference_Designs", "references.csv")
OUT_PNG = os.path.join(CAD_DIR, "Reference_Designs", "gain_vs_frequency.png")
OUT_CSV = os.path.join(CAD_DIR, "Reference_Designs", "gain_vs_frequency.csv")

# label -> temperature for create_new_netlist (None = TwoStage.cir's own value, 27 degC).
# The first entry is the one compared with the reference in the text box.
TEMPS = {"27 °C (TwoStage.cir)": None, "25 °C (for comparison)": 25}


def read_references(path):
    ref = pd.read_csv(path, index_col=0).drop(columns="Unit")
    designs = {}
    for design in ref.columns:
        col = ref[design]
        params = {k[len("param_"):]: float(v) for k, v in col.items() if k.startswith("param_")}
        for k in params:
            if k.startswith("m"):
                params[k] = int(round(params[k]))
        designs[design] = (params, float(col["spec_gain"]), float(col["spec_ugbw"]))
    return designs


def ac_response(dut, params, temp):
    netlist = dut.create_new_netlist(params, "TT", temp_pvt=temp)
    if dut.simulate(netlist) != 0:
        raise RuntimeError(f"ngspice failed on {netlist}")
    specs = dut.measure_metrics()
    return dut.freq.copy(), np.abs(dut.vout_complex), specs


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    dut = DUT(YAML_PATH)
    designs = read_references(REFERENCE_CSV)

    data = {}          # (design, temp label) -> (freq, gain, specs)
    for design, (params, _, _) in designs.items():
        for label, temp in TEMPS.items():
            data[(design, label)] = ac_response(dut, params, temp)
        print(f"  simulated {design}")

    # ---- CSV: one row per frequency, one column per design and temperature
    freq = next(iter(data.values()))[0]
    table = pd.DataFrame({"frequency_Hz": freq})
    for (design, label), (f, g, _) in data.items():
        temp_txt = label.split(" ")[0]
        table[f"{design} |H| {temp_txt}C (V/V)"] = g
    table.to_csv(OUT_CSV, index=False, float_format="%.6g")

    # ---- plot
    ink, muted, grid, surface = "#1f1f1e", "#6b6a63", "#e4e3dc", "#fcfcfb"
    colors = dict(zip(TEMPS, ["#2a78d6", "#eb6834"]))           # validated pair: CVD dE 24.7
    styles = dict(zip(TEMPS, ["-", (0, (4, 2))]))

    fig, axes = plt.subplots(2, 3, figsize=(13, 7.2), facecolor=surface)
    for ax, (design, (params, ref_gain, ref_ugbw)) in zip(axes.flat, designs.items()):
        ax.set_facecolor(surface)
        for label in TEMPS:
            f, g, _ = data[(design, label)]
            ax.loglog(f, g, color=colors[label], lw=2, ls=styles[label], zorder=3)
        ax.axhline(1.0, color=muted, lw=0.8, zorder=1)                     # unity gain
        # reference values
        ax.plot([1.0], [ref_gain], "D", ms=8, color=ink, mec=surface, mew=1.5, zorder=5)
        ax.plot([ref_ugbw], [1.0], "D", ms=8, color=ink, mec=surface, mew=1.5, zorder=5)

        g25 = data[(design, list(TEMPS)[0])][2]["gain"]
        u25 = data[(design, list(TEMPS)[0])][2]["ugbw"]
        dg = 100 * (g25 - ref_gain) / ref_gain
        g_alt = data[(design, list(TEMPS)[1])][2]["gain"]
        dg_alt = 100 * (g_alt - ref_gain) / ref_gain
        du = 100 * (u25 - ref_ugbw) / ref_ugbw
        ax.set_title(design, fontsize=11, color=ink, loc="left")
        ax.text(0.03, 0.05,
                f"gain  ref {ref_gain:<7.4g} 27°C {dg:+.2f}%  25°C {dg_alt:+.2f}%\n"
                f"UGBW  ref {ref_ugbw:<7.3g} 27°C {du:+.2f}%",
                transform=ax.transAxes, fontsize=7.5, color=ink, family="monospace",
                va="bottom", bbox=dict(boxstyle="round,pad=0.4", fc=surface, ec=grid))
        ax.set_xlim(1, 1e12)
        ax.set_ylim(1e-4, max(ref_gain, g25) * 4)
        ax.grid(which="major", color=grid, lw=0.6, zorder=0)
        ax.tick_params(labelsize=8, colors=muted, length=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(grid)
        ax.set_xlabel("frequency (Hz)", fontsize=8, color=muted)
        ax.set_ylabel("|H(f)| (V/V)", fontsize=8, color=muted)

    legend_ax = axes.flat[-1]
    legend_ax.axis("off")
    handles = [Line2D([], [], color=colors[l], lw=2, ls=styles[l]) for l in TEMPS]
    handles.append(Line2D([], [], marker="D", ls="", ms=8, color=ink, mec=surface))
    handles.append(Line2D([], [], color=muted, lw=0.8))
    legend_ax.legend(handles, [f"Our simulation, {l}" for l in TEMPS]
                     + ["TA reference: DC gain (at 1 Hz) and UGBW (at |H| = 1)", "Unity gain"],
                     loc="center left", frameon=False, fontsize=9, labelcolor=ink)
    fig.suptitle("Open-loop gain vs. frequency of the TA reference designs", x=0.01, ha="left",
                 fontsize=13, color=ink)
    fig.text(0.01, 0.925, "|v(net6)| from the AC analysis (input ac=1), log–log. "
             "The DC gain is read at the first point, 1 Hz.", fontsize=9, color=muted)
    fig.tight_layout(rect=(0, 0, 1, 0.91))
    fig.savefig(OUT_PNG, dpi=160, facecolor=surface)
    plt.close(fig)
    print(f"Saved {OUT_PNG}\n      {OUT_CSV}")


if __name__ == "__main__":
    main()
