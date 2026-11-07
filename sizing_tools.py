"""Python backend of the LLM sizing harness: one persistent sizing experiment.

All MCP tools (mcp_server.py) call methods of a single SizingExperiment, so the TD3
agent, replay buffer, candidate history, trace log and memory persist across calls.

Explainability / bookkeeping written to harness_runs/<run_id>/:
    log.csv        one row per simulator call (designs from the LLM, RL resets and RL
                   steps): elapsed time, simulator calls, source, agent, parent design,
                   changed parameters, rationale, specs, reward, running best.
    memory.jsonl   short notes the agents write for each other (context passing).
    summary.json   counters and best design, rewritten after every tool call.
    op_data.jsonl  transistor operating point (Id, gm, gds, Vgs, Vth, Vds, Vdsat, node
                   voltages) of every simulated design, saved by the same simulation
                   (optional task 2; read through operating_point / compare_operating_points).
    quick_analyses.jsonl  every cheap analysis run by quick_analysis (subset of op/ac/noise/
                   short tran, optional PVT corner): parameters, corner, specs, operating
                   point. These are NOT candidates and NOT simulator calls (optional task 2).
"""

import csv
import json
import math
import os
import subprocess
import time
from datetime import datetime
from numbers import Real
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

os.environ.setdefault("MPLBACKEND", "Agg")
from circuit_env import CircuitEnv
from ngspice_interface.op_data import compare as compare_op, derive as derive_op, read_op_data
from ngspice_interface.quick_analysis import (ANALYSES, SHORT_TRAN_STOP, SPECS_BY_ANALYSIS,
                                              QuickDUT, model_processes)
from td3 import ReplayBuffer, TD3


SPEC_UNITS = {
    "area": "m^2", "current": "A", "gain": "V/V", "noise": "V RMS",
    "phm": "deg", "slewRate": "V/us", "ugbw": "Hz",
}
MAX_STEPS_PER_CALL = 1000
MEMORY_KINDS = ("plan", "observation", "decision", "result", "lesson", "model")
# "model": the modeler's complete design model of this run, rewritten as a new version on evidence
MEMORY_MAX_CHARS = {"model": 4000}   # every other kind: 2000
MAX_QUICK_VARIANTS = 10
QUICK_TEMP_RANGE = (-40.0, 125.0)    # degC
QUICK_VDD_RANGE = (0.9, 1.5)         # V
# circuit quantities returned per quick variant (the full table: include_devices=True)
QUICK_CIRCUIT_KEYS = ("I_total_uA", "I_tail_uA", "I_2_uA", "A1_stage1", "A2_stage2", "gain_estimate",
                      "gm1_over_2piCc_MHz", "p2_gm6_over_2piCL_MHz", "zero_MHz", "zero_type",
                      "balance_ratio_sizes", "v_out_dc_V")
LOG_FIELDS = ["sim_call", "elapsed_s", "candidate_id", "source", "agent", "parent_id",
              "changes", "rationale", "reward", "best_reward", "feasible", "violated",
              "failed", "specs", "parameters"]


def to_builtin(value):
    """Convert NumPy values to JSON-compatible Python values."""
    if isinstance(value, np.ndarray):
        return to_builtin(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {key: to_builtin(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(item) for item in value]
    return value


def check_count(value, name, maximum):
    """Reject booleans, non-integers, and out-of-range requests."""
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer from 1 to {maximum}.")


def sig(x, digits=4):
    """Round to significant digits (keeps tool outputs short for the LLM)."""
    x = float(x)
    if x == 0 or not math.isfinite(x):
        return x
    return float(f"{x:.{digits}g}")


class SizingExperiment:
    """One TD3 agent, replay buffer, episode, candidate history and trace log.

    Use one experiment per process: the TD3 code uses the NumPy/PyTorch global RNGs.
    Hyperparameter defaults are the tuned values of milestone 3 (run final_g0).
    """

    def __init__(self, seed=123456, batch_size=128, replay_size=100_000, run_id=None,
                 gamma=0.0, noise_sigma=0.1, pi_lr=3e-4, q_lr=1e-3):
        check_count(replay_size, "replay_size", 1_000_000)
        check_count(batch_size, "batch_size", replay_size)
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError("seed must be an integer from 0 to 2**32 - 1.")
        np.random.seed(seed)
        torch.manual_seed(seed)
        self.seed = seed
        self.batch_size = batch_size
        self.run_id = run_id or "harness_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        self.t0 = time.time()
        self._clock_started = False

        self.env = CircuitEnv(run_id=self.run_id, success_threshold=0.0)
        # Direct design evaluations must not change the ongoing RL episode.
        self.evaluation_env = CircuitEnv(run_id=self.run_id + "_evaluate", success_threshold=0.0)
        self.env.action_space.seed(seed)
        Path(self.env.simulation_engine.output_files_folder).mkdir(parents=True, exist_ok=True)
        Path("solutions").mkdir(exist_ok=True)

        args = SimpleNamespace(gamma=gamma, tau=0.005, noise_sigma=noise_sigma,
                               actor_update_interval=2, pi_lr=pi_lr, q_lr=q_lr,
                               hidden_size=256, cuda=False)
        self.agent = TD3(self.env.observation_space.shape[0], self.env.action_space, args)
        self.replay = ReplayBuffer(self.env.observation_space.shape[0],
                                   self.env.action_space.shape[0], max_size=replay_size)
        self.observation = None  # None means the next RL step needs a reset.
        self.warmup_steps = 0
        self.training_steps = 0
        self.updates = 0
        self.seeded = 0
        self.simulator_calls = 0  # Attempts, including resets and failed calls.
        self.candidates = {}      # Parameter tuple -> latest measured candidate.
        self.by_id = {}           # Candidate id -> candidate.
        self.next_id = 1
        self.best = None
        self._last_clean = 0
        self.op_lookups = 0       # operating_point / compare_operating_points calls (0 simulations)
        self.model_versions = 0   # write_memory(kind="model") calls of the modeler
        self.quick_calls = 0      # quick_analysis tool calls
        self.quick_runs = 0       # cheap ngspice runs of quick_analysis (not simulator calls)
        self.quick_cache = {}     # (parameters, corner, analyses) -> result

        # Parameter grids, identical to CircuitEnv.action_refine.
        self.grids, self.is_int = {}, {}
        for name, rng in self.env.param_ranges.items():
            self.grids[name] = np.arange(rng["min"], rng["max"], rng["step"])
            self.is_int[name] = all(isinstance(x, int) for x in rng.values())
        self.param_names = list(self.grids)

        self.out_dir = Path("harness_runs") / self.run_id
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.out_dir / "log.csv"
        self.memory_path = self.out_dir / "memory.jsonl"
        self.op_path = self.out_dir / "op_data.jsonl"
        self.quick_path = self.out_dir / "quick_analyses.jsonl"
        with open(self.log_path, "w", newline="") as f:
            csv.writer(f).writerow(LOG_FIELDS)
        self.memory_path.touch()
        self.op_path.write_text("")
        self.quick_path.write_text("")

        # Cheap analyses (optional task 2): own DUT, same circuit, yaml and output folders.
        project = Path(os.getcwd())
        self.quick_engine = QuickDUT(
            str(project / "ngspice_interface" / "files" / "yaml_files" / f"{self.env.circuit_name}.yaml"),
            str(project / "no_backup" / "quick_netlists"))
        self.processes = model_processes(str(project / "ngspice_interface" / "files" / "spice_models"))

    def tick(self):
        """Start the runtime clock at the first tool call (not at server start)."""
        if not self._clock_started:
            self.t0, self._clock_started = time.time(), True

    # ------------------------------------------------------------------ tools
    def design_space(self) -> dict:
        """Parameter grids, targets, constraints and the FoM definition (no simulation)."""
        params = {}
        for name, grid in self.grids.items():
            rng = self.env.param_ranges[name]
            params[name] = {"min": to_builtin(grid[0]), "max": to_builtin(grid[-1]),
                            "step": rng["step"], "n_values": len(grid),
                            "unit": "count" if self.is_int[name] else
                                    ("F" if name == "cap" else "ohm" if name == "res" else "m")}
        return {
            "parameters": params,
            "targets": {k: {"value": v, "unit": SPEC_UNITS[k]} for k, v in self.env.dict_targets.items()},
            "hard_constraints": {k: ("<= target" if k in self.env.LOWER_IS_BETTER else ">= target")
                                 for k in self.env.hard_constraints},
            "optimization_targets": "minimize " + ", ".join(self.env.optimization_targets),
            "normalization": "z = (value - target) / (value + target), clipped to [-1, 1]",
            "fom": "infeasible: sum of hard-constraint violations (<0) + 0.05*(-z_area - z_current); "
                   "feasible: 0.3 + (-z_area - z_current). Higher is better; > 0.3 means feasible.",
            "run_id": self.run_id,
        }

    def simulate(self, parameters: dict, rationale: str = "", agent: str = "", base_id=None) -> dict:
        """Evaluate one design. `parameters` may be partial: missing values are copied
        from the base design (candidate base_id, default: the best candidate so far).
        Records the candidate and its lineage without touching RL state."""
        if not rationale.strip():
            raise ValueError("Give a rationale: why should this change improve the design?")
        base = None
        if len(parameters) < len(self.param_names):
            if base_id is None:
                base = self.best
            else:
                base = self.by_id.get(base_id)
                if base is None:
                    raise ValueError(f"Unknown base_id {base_id}.")
            if base is None:
                raise ValueError("No base design yet: give all 20 parameters "
                                 f"({', '.join(self.param_names)}).")
            parameters = {**base["parameters"], **parameters}
        params = self._validate_parameters(parameters)
        key = tuple(params[n] for n in self.param_names)
        if key in self.candidates:  # Never pay twice for the same design.
            out = self._compact(self.candidates[key], with_params=False)
            out["note"] = "Already simulated; no simulator call used."
            return out
        failed_before = self.evaluation_env.n_failed_sims
        specs = self.evaluation_env.simulate(params)
        self.simulator_calls += 1
        failed = self.evaluation_env.n_failed_sims > failed_before
        op = read_op_data(self.evaluation_env.simulation_engine)  # same simulation, no extra call
        changes = {} if base is None else {n: params[n] for n in self.param_names
                                           if params[n] != base["parameters"][n]}
        cand = self._record(self.evaluation_env, params, specs, "llm", failed,
                            agent=agent, rationale=rationale,
                            parent=None if base is None else base["id"], changes=changes, op=op)
        self._maybe_clean()
        self._write_summary()
        out = self._compact(cand, with_params=False)
        warnings = self._derive(cand)["warnings"] if cand["op"] else []
        if warnings:
            out["op_warnings"] = warnings
        return out

    def warmup(self, n_steps: int, around_best: bool = False, n_params: int = 3,
               max_steps: int = 2, top_k: int = 3) -> dict:
        """Append n_steps transitions, without updating weights. Default: random designs.
        around_best: neighbours of the top_k best (feasible first) designs, each changing
        only n_params random parameters by 1..max_steps grid steps (sparse local search)."""
        self._local = None
        if around_best:
            if self.best is None:
                raise ValueError("No design yet to explore around.")
            check_count(n_params, "n_params", len(self.param_names))
            check_count(max_steps, "max_steps", 5)
            check_count(top_k, "top_k", 10)
            ranked = sorted(self.candidates.values(), key=lambda c: (c["feasible"], c["reward"]), reverse=True)
            self._local = ([c["parameters"] for c in ranked[:top_k]], n_params, max_steps)
        return self._run_steps(n_steps, training=False)

    def _neighbour(self):
        """A sparse grid-step perturbation of one of the warmup centres, not yet simulated."""
        centres, n_params, max_steps = self._local
        steps = [s for s in range(-max_steps, max_steps + 1) if s]
        for _ in range(20):
            p = dict(centres[np.random.randint(len(centres))])
            for name in np.random.choice(self.param_names, size=n_params, replace=False):
                grid = self.grids[name]
                k = int(np.argmin(np.abs(grid - p[name])))
                p[name] = grid[int(np.clip(k + np.random.choice(steps), 0, len(grid) - 1))]
            if tuple(self._canon(p)[n] for n in self.param_names) not in self.candidates:
                break
        return self.param_to_action(p)

    def _canon(self, p):
        return {n: int(round(p[n])) if self.is_int[n] else float(f"{p[n]:.6e}") for n in self.param_names}

    def sweep(self, parameter: str, values: list, rationale: str, agent: str = "", base_id=None) -> dict:
        """Simulate a 1-D sweep of one parameter around a base design (one LLM decision,
        len(values) simulator calls). The base stays fixed during the sweep."""
        if parameter not in self.grids:
            raise ValueError(f"Unknown parameter {parameter}.")
        if not 2 <= len(values) <= 10:
            raise ValueError("Give 2..10 values.")
        base = self.by_id.get(base_id) if base_id is not None else self.best
        if base is None:
            raise ValueError("No base design.")
        rows = []
        for v in values:
            r = self.simulate({parameter: v}, rationale=f"[sweep {parameter}] {rationale}",
                              agent=agent, base_id=base["id"])
            rows.append({"value": v, "id": r["id"], "reward": r["reward"], "feasible": r["feasible"],
                         "violated": r["violated"],
                         "specs": {k: r["specs"][k] for k in ("current", "area", "phm", "ugbw", "slewRate")}})
            if r.get("op_warnings"):
                rows[-1]["op_warnings"] = r["op_warnings"]
        best = max(rows, key=lambda x: x["reward"])
        return {"base_id": base["id"], "parameter": parameter, "results": rows,
                "best_in_sweep": {"id": best["id"], "value": best["value"], "reward": best["reward"]}}

    def train(self, n_steps: int, noise_sigma: float = None) -> dict:
        """Collect n_steps policy transitions, one TD3 update per transition."""
        if noise_sigma is not None:
            if not 0.01 <= noise_sigma <= 0.5:
                raise ValueError("noise_sigma must be in [0.01, 0.5].")
            self.agent.expl_noise = noise_sigma
        if self.replay.size < self.batch_size:
            raise ValueError(f"Replay has {self.replay.size} experiences; need at least "
                             f"batch_size={self.batch_size}. Call warmup/seed_rl first.")
        return self._run_steps(n_steps, training=True)

    def seed_rl(self, k: int = 5, repeat: int = 1, only_feasible: bool = False,
                anchor_steps: int = 0) -> dict:
        """Put the k best LLM-evaluated designs into the replay buffer (no simulation).

        The next state depends only on the action in this environment, so a measured
        design is a valid transition (state = current observation, action = the design)."""
        check_count(k, "k", 50)
        check_count(repeat, "repeat", 10)
        pool = [c for c in self.candidates.values() if c["source"] == "llm" and not c["failed"]
                and (c["feasible"] or not only_feasible)]
        pool.sort(key=lambda c: c["reward"], reverse=True)
        chosen = pool[:k]
        for cand in chosen:
            action = self.param_to_action(cand["parameters"])
            nxt = np.array([cand["normalized_specs"][n] for n in self.env.dict_targets], dtype=np.float32)
            state = self.observation if self.observation is not None else nxt
            for _ in range(repeat):
                self.replay.push(state, action, cand["reward"], nxt, 0.0)
                self.seeded += 1
        anchor_loss = None
        if anchor_steps and chosen:
            # Behaviour cloning: pull the actor towards the best expert design, so TD3's
            # exploration starts around it instead of at a random point (0 simulations).
            check_count(anchor_steps, "anchor_steps", 2000)
            dev = next(self.agent.actor.parameters()).device
            target = torch.as_tensor(self.param_to_action(chosen[0]["parameters"]), device=dev).unsqueeze(0)
            for _ in range(anchor_steps):
                states = torch.as_tensor(self.replay.sample(min(int(self.replay.size), 128))[0],
                                         dtype=torch.float32, device=dev)
                loss = ((self.agent.actor(states) - target) ** 2).mean()
                self.agent.actor_optimizer.zero_grad()
                loss.backward()
                self.agent.actor_optimizer.step()
            self.agent.actor_target.load_state_dict(self.agent.actor.state_dict())
            anchor_loss = float(loss.detach())
        self._write_summary()
        return {"seeded_ids": [c["id"] for c in chosen], "transitions_added": len(chosen) * repeat,
                "replay_size": int(self.replay.size), "simulator_calls_used": 0,
                "anchored_to": chosen[0]["id"] if anchor_loss is not None else None,
                "anchor_loss": anchor_loss}

    def get_status(self, k: int = 5) -> dict:
        """Counters and the top-k distinct designs by reward (no simulation)."""
        check_count(k, "k", 20)
        ranked = sorted(self.candidates.values(), key=lambda c: c["reward"], reverse=True)
        feasible = [c for c in ranked if c["feasible"]]
        return {
            "run_id": self.run_id,
            "elapsed_s": round(time.time() - self.t0, 1),
            "simulator_calls": self.simulator_calls,
            "llm_designs": sum(c["source"] == "llm" for c in ranked),
            "rl_warmup_steps": self.warmup_steps,
            "rl_training_steps": self.training_steps,
            "rl_updates": self.updates,
            "replay_size": int(self.replay.size),
            "n_feasible": len(feasible),
            "op_lookups": self.op_lookups,
            "model_versions": self.model_versions,
            "quick_calls": self.quick_calls,
            "quick_runs": self.quick_runs,
            "best": [self._compact(c) for c in ranked[:k]],
            "best_feasible_id": feasible[0]["id"] if feasible else None,
        }

    def get_lineage(self, candidate_id: int) -> dict:
        """Chain of designs that led to a candidate, each with agent, changes and rationale."""
        chain, cand = [], self.by_id.get(candidate_id)
        if cand is None:
            raise ValueError(f"Unknown candidate_id {candidate_id}.")
        while cand is not None:
            chain.append({"id": cand["id"], "source": cand["source"], "agent": cand["agent"],
                          "changes": cand["changes"], "rationale": cand["rationale"],
                          "reward": sig(cand["reward"]), "feasible": cand["feasible"],
                          "violated": cand["violated"]})
            cand = self.by_id.get(cand["parent"])
        return {"lineage_oldest_first": chain[::-1]}

    def operating_point(self, candidate_id: int = None) -> dict:
        """Transistor-level operating point of a simulated design (default: the best).
        0 simulator calls: the data was saved by the design's own simulation."""
        cand = self._get_candidate(candidate_id)
        self.op_lookups += 1
        self._write_summary()
        d = self._derive(cand)
        # conclusions first, the full device table last
        return {"id": cand["id"], "source": cand["source"], "reward": sig(cand["reward"]),
                "feasible": cand["feasible"], "violated": cand["violated"],
                "warnings": d["warnings"], "notes": d["notes"], "circuit": d["circuit"],
                "devices": d["devices"]}

    def compare_operating_points(self, id_a: int, id_b: int) -> dict:
        """What changed between two simulated designs: parameters, specs, and the device and
        circuit quantities that moved by more than 5 % (0 simulator calls)."""
        a, b = self._get_candidate(id_a), self._get_candidate(id_b)
        self.op_lookups += 1
        self._write_summary()
        diff = compare_op(self._derive(a), self._derive(b))
        return {
            "a": {"id": a["id"], "source": a["source"], "reward": sig(a["reward"]), "feasible": a["feasible"]},
            "b": {"id": b["id"], "source": b["source"], "reward": sig(b["reward"]), "feasible": b["feasible"]},
            "parameter_changes": {n: [a["parameters"][n], b["parameters"][n]] for n in self.param_names
                                  if a["parameters"][n] != b["parameters"][n]},
            "spec_changes": {k: [sig(a["specs"][k]), sig(b["specs"][k])] for k in a["specs"]},
            "device_changes": diff["devices"], "circuit_changes": diff["circuit"],
            "warnings_only_in_a": diff["warnings_only_in_a"], "warnings_only_in_b": diff["warnings_only_in_b"],
        }

    def quick_analysis(self, variants: list, analyses: list = ("op",), rationale: str = "",
                       agent: str = "", base_id=None, corner: dict = None,
                       include_devices: bool = False) -> dict:
        """Cheap screening of 1..10 design variants (optional task 2): ngspice runs only the
        selected analyses (op, ac, noise, short 5 us tran), optionally at another PVT corner.
        The results are NOT candidates (never best, Pareto front or RL data) and do NOT count
        as simulator calls; they are counted in quick_runs and logged in quick_analyses.jsonl.
        A variant is a partial parameter dict applied to the base design (default: the best);
        {} analyses the base design itself (e.g. at another corner)."""
        if not rationale.strip():
            raise ValueError("Give a rationale: what do you want to learn from this analysis?")
        if not isinstance(variants, list) or not 1 <= len(variants) <= MAX_QUICK_VARIANTS:
            raise ValueError(f"Give 1..{MAX_QUICK_VARIANTS} variants (partial parameter dicts).")
        analyses = list(analyses) if isinstance(analyses, (list, tuple)) else []
        if not analyses or set(analyses) - set(ANALYSES):
            raise ValueError(f"analyses must be a non-empty subset of {list(ANALYSES)}.")
        analyses = tuple(a for a in ANALYSES if a in analyses)
        corner = self._validate_corner(corner)
        base = self.best if base_id is None else self.by_id.get(base_id)
        if base_id is not None and base is None:
            raise ValueError(f"Unknown base_id {base_id}.")
        designs = []                       # validate everything before running anything
        for v in variants:
            if not isinstance(v, dict):
                raise ValueError("Each variant must be a dict of parameter changes.")
            if len(v) < len(self.param_names) and base is None:
                raise ValueError("No base design yet: give all 20 parameters in each variant.")
            params = self._validate_parameters(v if base is None else {**base["parameters"], **v})
            designs.append(params)

        results = []
        for params in designs:
            key = (tuple(params[n] for n in self.param_names), tuple(sorted(corner.items())), analyses)
            cached = key in self.quick_cache
            if not cached:
                self.quick_cache[key] = self._quick_run(params, analyses, corner, rationale, agent)
            row = self._quick_view(self.quick_cache[key], params, base, corner, include_devices)
            if cached:
                row["cached"] = True
            results.append(row)
        self.quick_calls += 1
        self._write_summary()
        out = {"base_id": None if base is None else base["id"], "corner": corner,
               "analyses": list(analyses), "results": results,
               "quick_runs_total": self.quick_runs,
               "note": "Cheap analyses, not candidates: confirm a chosen variant with simulate."}
        if "tran" in analyses:
            out["tran"] = f"short transient ({SHORT_TRAN_STOP}s): slew rate of the first rising edge"
        return out

    def write_memory(self, agent: str, kind: str, content: str) -> dict:
        """Append a short note for the other agents (context passing)."""
        if kind not in MEMORY_KINDS:
            raise ValueError(f"kind must be one of {MEMORY_KINDS}.")
        limit = MEMORY_MAX_CHARS.get(kind, 2000)
        if not content.strip() or len(content) > limit:
            raise ValueError(f"content must be 1..{limit} characters for kind '{kind}'; summarize.")
        entry = {"t": round(time.time() - self.t0, 1), "sim_calls": self.simulator_calls,
                 "agent": agent, "kind": kind, "content": content.strip()}
        with open(self.memory_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        if kind == "model":
            self.model_versions += 1
            self._write_summary()
        return {"ok": True, "n_entries": sum(1 for _ in open(self.memory_path))}

    def read_memory(self, agent: str = "", kind: str = "", last_n: int = 10) -> dict:
        """Most recent memory entries, optionally filtered by agent and/or kind."""
        check_count(last_n, "last_n", 50)
        entries = [json.loads(line) for line in open(self.memory_path) if line.strip()]
        entries = [e for e in entries if (not agent or e["agent"] == agent)
                   and (not kind or e["kind"] == kind)]
        return {"entries": entries[-last_n:], "total_matching": len(entries)}

    # --------------------------------------------------------------- helpers
    def param_to_action(self, params):
        """Inverse of CircuitEnv.action_refine: the centre of each parameter's bin."""
        action = np.zeros(len(self.param_names), dtype=np.float32)
        for i, name in enumerate(self.param_names):
            grid = self.grids[name]
            k = int(np.argmin(np.abs(grid - params[name])))
            n = len(grid)
            action[i] = 0.0 if n == 1 else min(2.0 * (k + 0.5) / (n - 1) - 1.0, 1.0)
        return action

    def _validate_parameters(self, parameters):
        """Require every YAML parameter, finite numbers, and on-grid values."""
        unknown = set(parameters) - set(self.param_names)
        missing = set(self.param_names) - set(parameters)
        if unknown or missing:
            raise ValueError(f"Unknown parameters {sorted(unknown)}; missing {sorted(missing)}.")
        clean = {}
        for name in self.param_names:
            value = parameters[name]
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number.")
            grid = self.grids[name]
            step = self.env.param_ranges[name]["step"]
            k = int(np.argmin(np.abs(grid - value)))
            if abs(grid[k] - value) > 1e-6 * step:
                lo = grid[max(k - 1, 0)] if grid[k] > value else grid[k]
                hi = grid[k] if grid[k] > value else grid[min(k + 1, len(grid) - 1)]
                raise ValueError(f"{name}={value} is off-grid or out of range "
                                 f"[{grid[0]:.4g}, {grid[-1]:.4g}], step {step}; nearest "
                                 f"allowed: {lo:.4g} or {hi:.4g}.")
            clean[name] = int(grid[k]) if self.is_int[name] else float(f"{grid[k]:.6e}")
        return clean

    def _get_candidate(self, candidate_id):
        """A simulated design that has operating-point data (default: the best)."""
        cand = self.best if candidate_id is None else self.by_id.get(candidate_id)
        if cand is None:
            raise ValueError("No design yet." if candidate_id is None else f"Unknown candidate_id {candidate_id}.")
        if cand.get("op") is None:
            raise ValueError(f"No operating-point data for design {cand['id']} (its simulation failed).")
        return cand

    def _derive(self, cand):
        """Derived operating-point quantities of a candidate (see ngspice_interface/op_data.py)."""
        ugbw = cand["specs"].get("ugbw")
        return derive_op(cand["op"], cand["parameters"],
                         ugbw if ugbw is not None and math.isfinite(ugbw) and ugbw > 0 else None)

    def _validate_corner(self, corner):
        """Full PVT corner dict; missing keys come from the evaluation corner (TT, 27 C, 1.2 V)."""
        default = dict(self.evaluation_env.pvt_corner)    # {'process', 'voltage', 'temp'}
        corner = {} if corner is None else corner
        if not isinstance(corner, dict) or set(corner) - set(default):
            raise ValueError(f"corner keys: {sorted(default)}, e.g. {{'process': 'SS', 'temp': 80}}.")
        out = {**default, **corner}
        if out["process"] not in self.processes:
            raise ValueError(f"process must be one of {list(self.processes)}.")
        for name, (lo, hi) in (("temp", QUICK_TEMP_RANGE), ("voltage", QUICK_VDD_RANGE)):
            value = out[name]
            if isinstance(value, bool) or not isinstance(value, Real) or not lo <= value <= hi:
                raise ValueError(f"corner {name} must be a number in [{lo}, {hi}].")
            out[name] = float(value)
        return out

    def _quick_run(self, params, analyses, corner, rationale, agent):
        """One cheap ngspice run, counted in quick_runs and logged (never a candidate)."""
        error, specs, op, seconds = None, {}, None, None
        try:
            specs, op, seconds = self.quick_engine.run(params, analyses, process=corner["process"],
                                                       temp=corner["temp"], vdd=corner["voltage"])
        except Exception as err:          # a failed quick run must not stop the harness
            error = f"{type(err).__name__}: {err}"
        self.quick_runs += 1
        result = {"quick_id": self.quick_runs, "specs": specs, "op": op, "error": error}
        entry = {"quick_id": self.quick_runs, "t": round(time.time() - self.t0, 2),
                 "sim_calls": self.simulator_calls, "agent": agent, "rationale": rationale,
                 "analyses": list(analyses), "corner": corner, "ngspice_s": seconds,
                 "parameters": params, "specs": specs, "error": error, "op": op}
        with open(self.quick_path, "a") as f:
            f.write(json.dumps(to_builtin(entry)) + "\n")
        return result

    def _quick_view(self, result, params, base, corner, include_devices):
        """Short view of a quick run: measured specs, hard-constraint check, FoM, bias."""
        env = self.evaluation_env
        row = {"quick_id": result["quick_id"],
               "changes": {} if base is None else {n: params[n] for n in self.param_names
                                                   if params[n] != base["parameters"][n]}}
        if result["error"]:
            row["error"] = result["error"]
            return row
        specs = result["specs"]
        row["specs"] = {k: sig(v) for k, v in specs.items()}
        row["not_measured"] = [k for k in env.dict_targets if k not in specs]
        # only the measured specs are checked; unmeasured ones count as on target
        norm = env.normalize_specs({**env.dict_targets, **specs})
        row["violated"] = [h for h in env.hard_constraints if h in specs and
                           (norm[h] > 0 if h in env.LOWER_IS_BETTER else norm[h] < 0)]
        reward, feasible = env.reward_computation(norm)
        if not row["not_measured"]:
            row["reward"], row["feasible"] = sig(reward), bool(feasible)
        elif "current" in specs and not row["violated"]:
            # area and current are exact, so this is the FoM IF the unmeasured specs pass
            row["fom_if_feasible"] = sig(reward)
        if result["op"] is not None:
            ugbw = specs.get("ugbw")
            d = derive_op(result["op"], params,
                          ugbw if ugbw is not None and math.isfinite(ugbw) and ugbw > 0 else None,
                          vdd=corner["voltage"])
            if d["warnings"]:
                row["op_warnings"] = d["warnings"]
            row["op_notes"] = d["notes"]
            row["circuit"] = {k: d["circuit"][k] for k in QUICK_CIRCUIT_KEYS}
            if include_devices:
                row["devices"] = d["devices"]
        return row

    def _record(self, env, parameters, specs, source, failed, agent="", rationale="",
                parent=None, changes=None, op=None):
        """Score one measurement with the environment's own methods, store and log it.
        op: operating-point data of the same simulation (read_op_data), or None."""
        norm = env.normalize_specs(specs)
        reward, feasible = env.reward_computation(norm)
        violated = [s for s in env.hard_constraints
                    if (norm[s] > 0 if s in env.LOWER_IS_BETTER else norm[s] < 0)]
        cand = {"id": self.next_id, "source": source, "agent": agent, "rationale": rationale,
                "parent": parent, "changes": changes or {}, "parameters": dict(parameters),
                "specs": {k: float(v) for k, v in specs.items()}, "normalized_specs": norm,
                "reward": float(reward), "feasible": bool(feasible), "violated": violated,
                "failed": bool(failed), "sim_call": self.simulator_calls,
                "elapsed_s": round(time.time() - self.t0, 2), "op": op}
        self.next_id += 1
        if op is not None:
            with open(self.op_path, "a") as f:
                f.write(json.dumps({"id": cand["id"], "source": source, **op}) + "\n")
        self.by_id[cand["id"]] = cand
        if not failed and all(math.isfinite(v) for v in cand["specs"].values()):
            self.candidates[tuple(parameters[n] for n in self.param_names)] = cand
            if self.best is None or cand["reward"] > self.best["reward"]:
                self.best = cand
        with open(self.log_path, "a", newline="") as f:
            csv.writer(f).writerow([
                cand["sim_call"], cand["elapsed_s"], cand["id"], source, agent, parent or "",
                json.dumps(cand["changes"]), rationale, reward,
                self.best["reward"] if self.best else "", int(feasible), " ".join(violated),
                int(failed), json.dumps(cand["specs"]), json.dumps(cand["parameters"])])
        return cand

    def _compact(self, cand, with_params=True):
        """Short JSON view of a candidate for the LLM (saves context tokens)."""
        out = {"id": cand["id"], "source": cand["source"], "reward": sig(cand["reward"]),
               "feasible": cand["feasible"], "violated": cand["violated"],
               "specs": {k: sig(v) for k, v in cand["specs"].items()},
               "normalized": {k: sig(v, 3) for k, v in cand["normalized_specs"].items()}}
        if cand["failed"]:
            out["failed"] = True
        if with_params:
            out["parameters"] = cand["parameters"]
        else:
            out["changes"] = cand["changes"]
        return out

    def _run_steps(self, n_steps, training):
        """Run a bounded batch of RL steps; keep completed work if a step fails."""
        check_count(n_steps, "n_steps", MAX_STEPS_PER_CALL)
        calls0, best0 = self.simulator_calls, self.best["reward"] if self.best else -np.inf
        done_steps, updates, error = 0, 0, None
        phase = "rl_train" if training else "rl_warmup"
        for _ in range(n_steps):
            try:
                if self.observation is None and self.best is not None:
                    # s' depends only on the action, so start the episode from the best
                    # design's measured specs instead of paying for a random reset.
                    self.observation = np.array([self.best["normalized_specs"][n] for n in self.env.dict_targets],
                                                dtype=np.float32)
                    self.env.episode_steps, self.env.score = 0, 0.0
                elif self.observation is None:
                    s0, f0 = self.env.n_simulations, self.env.n_failed_sims
                    self.observation = self.env.reset()
                    self.simulator_calls += self.env.n_simulations - s0
                    self._record(self.env, self.env.param_values, self.env.real_specs,
                                 "rl_reset", self.env.n_failed_sims > f0, agent="td3",
                                 op=read_op_data(self.env.simulation_engine))
                if training:
                    action = self.agent.select_action(self.observation)
                elif getattr(self, "_local", None) is not None:
                    action = self._neighbour()
                else:
                    action = self.env.action_space.sample()
                s0, f0 = self.env.n_simulations, self.env.n_failed_sims
                next_obs, reward, done, info = self.env.step(action)
                self.simulator_calls += self.env.n_simulations - s0
                failed = self.env.n_failed_sims > f0
                self._record(self.env, info["params"], info["specs"], phase, failed, agent="td3",
                             op=read_op_data(self.env.simulation_engine))
                if not failed:
                    self.replay.push(self.observation, action, reward, next_obs, float(done))
                if training and self.replay.size >= self.batch_size:
                    self.agent.update_parameters(memory_batch=self.replay.sample(self.batch_size))
                    updates += 1
                self.observation = None if done else next_obs
                done_steps += 1
                if training:
                    self.training_steps += 1
                else:
                    self.warmup_steps += 1
                self._maybe_clean()
            except Exception as exc:  # Keep the work already done.
                error = f"{type(exc).__name__}: {exc}. Inspect get_status() before retrying."
                self.observation = None
                break
        self.updates += updates
        self._write_summary()
        status = self.get_status(3)
        best1 = self.best["reward"] if self.best else -np.inf
        status.update({"steps_completed": done_steps, "simulator_calls_used": self.simulator_calls - calls0,
                       "updates_performed": updates, "improved_best": bool(best1 > best0)})
        if error:
            status["error"] = error
        return status

    def _maybe_clean(self):
        """Empty no_backup/ every 100 simulator calls, like td3_runner.py."""
        if self.simulator_calls - self._last_clean >= 100 and Path("clean.sh").exists():
            subprocess.run(["bash", "clean.sh"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._last_clean = self.simulator_calls

    def _write_summary(self):
        summary = {"run_id": self.run_id, "elapsed_s": round(time.time() - self.t0, 1),
                   "simulator_calls": self.simulator_calls, "warmup_steps": self.warmup_steps,
                   "training_steps": self.training_steps, "updates": self.updates,
                   "seeded_transitions": self.seeded, "op_lookups": self.op_lookups,
                   "model_versions": self.model_versions,
                   "quick_calls": self.quick_calls, "quick_runs": self.quick_runs,
                   "best": None if self.best is None else {
                       k: self.best[k] for k in ("id", "source", "reward", "feasible",
                                                 "specs", "parameters")}}
        with open(self.out_dir / "summary.json", "w") as f:
            json.dump(to_builtin(summary), f, indent=2)
