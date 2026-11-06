"""Transistor operating-point data of a full simulation (optional task 2).

TwoStage.cir writes, after its 'op' analysis, one extra output file op_<netlist>.csv with
Id, gm, gds, Vgs, Vth, Vds, Vdsat of every transistor and the DC node voltages. This is
the same simulation that measures the 7 specs: no extra analysis, no extra simulator call.

    read_op_data(engine)        raw values of the simulation the engine ran last
    derive(op, params, ugbw)    per-device and circuit-level quantities for reasoning
    compare(a, b)               what changed between two derived operating points

The circuit (net names of TwoStage.cir):

    mn1/mn2  input pair          drains net4 (mirror side) / net5 (stage-1 output), source net3
    mp1/mp2  current-mirror load gate net4 (mp1 diode-connected)
    mn4      tail current source drain net3, mirror of mn3
    mn3      bias diode          drain = gate = net7, carries Ibias = 30 uA
    mp3      2nd stage (CS)      gate net5, drain net6 (output)
    mn5      2nd-stage sink      drain net6, mirror of mn3
    Cc + Rc  Miller compensation between net5 and net6, CL = 10 pF on net6
"""
import math
import os

DEVICES = ("mn1", "mn2", "mp1", "mp2", "mn3", "mn4", "mp3", "mn5")
QUANTITIES = ("id", "gm", "gds", "vgs", "vth", "vds", "vdsat")
NODES = ("net3", "net4", "net5", "net6", "net7")
ROLES = {
    "mn1": "input pair (mirror side)", "mn2": "input pair (output side)",
    "mp1": "mirror load (diode)", "mp2": "mirror load (stage-1 output)",
    "mn3": "bias diode", "mn4": "tail current source",
    "mp3": "2nd stage common source", "mn5": "2nd stage current sink",
}
VDD = 1.2         # .param VDD
CLOAD = 10e-12    # .param cload
IBIAS = 30e-6     # .param ibias

# thresholds for warnings and labels
SAT_MARGIN_WARN = 0.05      # V: Vds - Vdsat below this = close to the triode region
BALANCE_WARN = 0.05         # V: |V(net5) - V(net4)| above this = stage 1 is unbalanced
RAIL_WARN = 0.15            # V: output DC level this close to a supply rail
GM_ID_WEAK = 18.0           # 1/V: gm/Id above this ~ weak inversion
GM_ID_STRONG = 8.0          # 1/V: gm/Id below this ~ strong inversion


def op_file(engine):
    """Path of the operating-point file of the last netlist the engine created."""
    return os.path.join(engine.output_files_folder, f"op_{engine.random_name}.csv")


def read_op_data(engine):
    """Read the operating point of the simulation the engine ran last.

    Args:
        engine: the ngspice DUT object (CircuitEnv.simulation_engine), right after a
            simulation; its output_files_folder and random_name locate the file.

    Returns:
        {"devices": {dev: {q: value}}, "nodes": {net: volts}} in SI units, magnitudes
        (PMOS values are positive), or None if the simulation failed or the file is
        missing or incomplete.
    """
    try:
        with open(op_file(engine)) as f:
            header = f.readline().split()
            values = f.readline().split()
        # wrdata writes "scale value" pairs: the names and values are every second column
        raw = dict(zip(header[1::2], (float(v) for v in values[1::2])))
    except (OSError, ValueError, AttributeError):
        return None
    try:
        out = {
            "devices": {d: {q: abs(raw[f"@{d}[{q}]"]) for q in QUANTITIES} for d in DEVICES},
            "nodes": {n: raw[f"v({n})"] for n in NODES},
        }
    except KeyError:
        return None
    flat = [v for d in out["devices"].values() for v in d.values()] + list(out["nodes"].values())
    if not all(math.isfinite(v) for v in flat):
        return None
    return out


def _sig(x, digits=4):
    x = float(x)
    if x == 0 or not math.isfinite(x):
        return x
    return float(f"{x:.{digits}g}")


def derive(op, params, ugbw=None):
    """Turn raw operating-point data into quantities an agent can reason with.

    Args:
        op: output of read_op_data.
        params: the design's parameters (needs 'cap' and 'res').
        ugbw: measured UGBW in Hz (optional), to compare with the 2nd pole.

    Returns:
        {"devices": per-device table, "circuit": stage gains, poles, zero, currents,
         balance, DC levels, "warnings": bias problems (triode, imbalance, rail),
         "notes": frequency-response facts (pole/zero positions)}
    """
    dev, nodes = op["devices"], op["nodes"]
    table, warnings, notes = {}, [], []
    for d in DEVICES:
        x = dev[d]
        margin = x["vds"] - x["vdsat"]
        gm_id = x["gm"] / x["id"] if x["id"] > 0 else float("inf")
        inversion = "weak" if gm_id >= GM_ID_WEAK else "strong" if gm_id < GM_ID_STRONG else "moderate"
        region = "triode" if margin < 0 else "saturation"
        table[d] = {
            "role": ROLES[d],
            "id_uA": _sig(x["id"] * 1e6), "gm_mS": _sig(x["gm"] * 1e3), "gds_uS": _sig(x["gds"] * 1e6),
            "vgs_V": _sig(x["vgs"]), "vth_V": _sig(x["vth"]), "vov_V": _sig(x["vgs"] - x["vth"]),
            "vds_V": _sig(x["vds"]), "vdsat_V": _sig(x["vdsat"]), "sat_margin_V": _sig(margin),
            "region": region, "inversion": inversion,
            "gm_id_per_V": _sig(gm_id), "gm_gds": _sig(x["gm"] / x["gds"]) if x["gds"] > 0 else None,
        }
        if margin < 0:
            warnings.append(f"{d} ({ROLES[d]}) in triode: Vds {x['vds']*1e3:.0f} mV < Vdsat {x['vdsat']*1e3:.0f} mV")
        elif margin < SAT_MARGIN_WARN:
            warnings.append(f"{d} ({ROLES[d]}) close to triode: Vds - Vdsat = {margin*1e3:.0f} mV")

    gm1, gm6 = dev["mn1"]["gm"], dev["mp3"]["gm"]
    a1 = gm1 / (dev["mn2"]["gds"] + dev["mp2"]["gds"])
    a2 = gm6 / (dev["mp3"]["gds"] + dev["mn5"]["gds"])
    cc, rc = float(params["cap"]), float(params["res"])
    gbw = gm1 / (2 * math.pi * cc)
    p2 = gm6 / (2 * math.pi * CLOAD)
    inv_gm6 = 1.0 / gm6
    if abs(rc - inv_gm6) < 1e-9 * inv_gm6:
        zero_hz, zero_type = None, "cancelled (Rc = 1/gm6)"
    else:
        zero_hz = 1.0 / (2 * math.pi * cc * abs(inv_gm6 - rc))
        zero_type = "LHP (adds phase)" if rc > inv_gm6 else "RHP (costs phase)"
    balance = nodes["net5"] - nodes["net4"]
    vout = nodes["net6"]
    # balance condition from the sizes, S = m*W/L: (S_mp3/S_mp1) / (2*S_mn5/S_mn4) should be 1.
    # > 1: mp3 sources more than mn5 sinks -> output pulled up; < 1: pulled down.
    size = lambda d: float(params[d]) * float(params["w" + d[1:]]) / float(params["l" + d[1:]])
    balance_ratio = (size("mp3") / size("mp1")) / (2 * size("mn5") / size("mn4"))

    circuit = {
        "I_bias_uA": _sig(dev["mn3"]["id"] * 1e6), "I_tail_uA": _sig(dev["mn4"]["id"] * 1e6),
        "I_2_uA": _sig(dev["mn5"]["id"] * 1e6),
        "I_total_uA": _sig((dev["mn3"]["id"] + dev["mn4"]["id"] + dev["mn5"]["id"]) * 1e6),
        "A1_stage1": _sig(a1), "A2_stage2": _sig(a2), "gain_estimate": _sig(a1 * a2),
        "gm1_over_2piCc_MHz": _sig(gbw / 1e6), "p2_gm6_over_2piCL_MHz": _sig(p2 / 1e6),
        "zero_MHz": None if zero_hz is None else _sig(zero_hz / 1e6), "zero_type": zero_type,
        "one_over_gm6_ohm": _sig(inv_gm6), "Rc_ohm": rc, "Cc_pF": _sig(cc * 1e12),
        "balance_ratio_sizes": _sig(balance_ratio, 3),
        "balance_V_net5_minus_net4_mV": _sig(balance * 1e3),
        "v_stage1_out_V": _sig(nodes["net5"]), "v_out_dc_V": _sig(vout), "v_tail_V": _sig(nodes["net3"]),
    }

    if abs(balance) > BALANCE_WARN:
        warnings.append(f"stage 1 unbalanced: V(net5) - V(net4) = {balance*1e3:.0f} mV "
                        "(balance condition S_mp3/S_mp1 = 2*S_mn5/S_mn4 not met)")
    if vout > VDD - RAIL_WARN:
        warnings.append(f"output DC level at VDD: V(net6) = {vout:.3f} V, mp3 sources more than mn5 "
                        f"sinks (balance ratio {balance_ratio:.2f} > 1): smaller S_mp3 or larger S_mn5")
    elif vout < RAIL_WARN:
        warnings.append(f"output DC level at ground: V(net6) = {vout:.3f} V, mn5 sinks more than mp3 "
                        f"sources (balance ratio {balance_ratio:.2f} < 1): larger S_mp3 or smaller S_mn5")

    ref = ugbw if ugbw else gbw
    ref_name = "measured UGBW" if ugbw else "gm1/(2*pi*Cc)"
    if p2 < ref:
        notes.append(f"2nd pole gm6/(2*pi*CL) = {p2/1e6:.3g} MHz is below the {ref_name} "
                     f"({ref/1e6:.3g} MHz): UGBW is limited by gm6 (mp3), not by gm1/Cc")
    else:
        notes.append(f"2nd pole at {p2/1e6:.3g} MHz = {p2/ref:.2g} x {ref_name}")
    if zero_hz is not None:
        notes.append(f"{zero_type.split()[0]} zero at {zero_hz/1e6:.3g} MHz "
                     f"(Rc = {rc:.0f} ohm vs 1/gm6 = {inv_gm6:.0f} ohm)")
    weakest = max(("mn1", "mp1", "mp3", "mn5"), key=lambda d: dev[d]["gds"] / dev[d]["gm"])
    notes.append(f"gain estimate A1*A2 = {a1:.3g} * {a2:.3g} = {a1*a2:.4g}; lowest intrinsic gain "
                 f"gm/gds among the signal devices: {weakest} ({dev[weakest]['gm']/dev[weakest]['gds']:.3g})")

    return {"devices": table, "circuit": circuit, "warnings": warnings, "notes": notes}


def compare(a, b, rel_tol=0.05):
    """Quantities of two derived operating points (derive output) that differ.

    Numbers are listed when they change by more than rel_tol (relative); labels (region,
    inversion, zero type) when they change at all. Returns
    {"devices": {dev: {key: [a, b]}}, "circuit": {key: [a, b]},
     "warnings_only_in_a": [...], "warnings_only_in_b": [...]}.
    """
    def changed(x, y):
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            scale = max(abs(x), abs(y))
            return scale > 0 and abs(x - y) > rel_tol * scale
        return x != y

    devices = {}
    for d in DEVICES:
        diff = {k: [a["devices"][d][k], b["devices"][d][k]] for k in a["devices"][d]
                if k != "role" and changed(a["devices"][d][k], b["devices"][d][k])}
        if diff:
            devices[d] = diff
    circuit = {k: [a["circuit"][k], b["circuit"][k]] for k in a["circuit"]
               if changed(a["circuit"][k], b["circuit"][k])}
    # a warning is identified by its text before the ':' (the numbers after it differ)
    key = lambda w: w.split(":")[0]
    keys_a, keys_b = {key(w) for w in a["warnings"]}, {key(w) for w in b["warnings"]}
    return {"devices": devices, "circuit": circuit,
            "warnings_only_in_a": [w for w in a["warnings"] if key(w) not in keys_b],
            "warnings_only_in_b": [w for w in b["warnings"] if key(w) not in keys_a]}
