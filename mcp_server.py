"""Expose the sizing experiment (sizing_tools.py) to the LLM agents as a stdio MCP server.

stdout is reserved for the MCP protocol: everything the course code prints goes to stderr.

    agy mcp add --type stdio --env PATH="$PATH" cad -- "$PWD/../.venv/bin/python" "$PWD/mcp_server.py"
"""

import argparse
from contextlib import redirect_stdout
import os
from pathlib import Path
import sys
from threading import Lock
from typing import Any, Optional

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import StrictBool, StrictFloat, StrictInt

with redirect_stdout(sys.stderr):
    from sizing_tools import SizingExperiment


def create_server(experiment):
    """Register tools for one experiment; serialize calls that share its state."""
    server = MCPServer(
        "CAD sizing",
        description="Two-stage Miller opamp sizing: simulation, cheap analyses (op/ac/noise/"
                    "short tran, PVT corners), transistor operating point, TD3 RL sizer, "
                    "trace and shared memory.",
    )
    lock = Lock()

    def call(method, **arguments):
        with lock, redirect_stdout(sys.stderr):
            try:
                experiment.tick()
                return getattr(experiment, method)(**arguments)
            except (ValueError, RuntimeError) as error:
                raise ToolError(str(error)) from error

    @server.tool()
    def design_space() -> dict[str, Any]:
        """Parameter grids (min, max, step, unit), spec targets, hard constraints and the
        FoM definition. No simulation. Call once at the start instead of reading files."""
        return call("design_space")

    @server.tool()
    def simulate(parameters: dict[str, StrictFloat | StrictInt], rationale: str,
                 agent: str, base_id: Optional[StrictInt] = None) -> dict[str, Any]:
        """Simulate ONE design (costs one simulator call; the budget is small).

        parameters: physical values on the YAML grid (multiplicities are counts, widths and
        lengths in meters, cap in farads, res in ohms). It may be PARTIAL: only give the
        parameters you change; the others are copied from base_id (default: current best).
        rationale: required. Which spec you expect to change, in which direction, and the
        circuit reason (e.g. "raise Cc: moves the 2nd pole/zero, expect PM up, UGBW down").
        agent: your role name (e.g. "sizer"). Off-grid values are rejected with the nearest
        allowed values. Repeated designs are not re-simulated. Returns id, specs,
        normalized specs, reward (FoM), feasible, violated constraints and the changes,
        plus op_warnings when the bias is broken (a device in triode, output at a rail).
        """
        return call("simulate", parameters=parameters, rationale=rationale, agent=agent, base_id=base_id)

    @server.tool()
    def warmup(n_steps: StrictInt, around_best: StrictBool = True, n_params: StrictInt = 3,
               max_steps: StrictInt = 2, top_k: StrictInt = 3) -> dict[str, Any]:
        """Add n_steps designs to the RL replay buffer (1..1000), no learning, one
        simulation each. around_best=True (default): sparse local search, i.e. neighbours of
        the top_k best designs (feasible first) that change only n_params parameters by
        1..max_steps grid steps. Gives many feasible designs (Pareto data) and local data for
        the critic. around_best=False: uniformly random designs."""
        return call("warmup", n_steps=n_steps, around_best=around_best, n_params=n_params,
                    max_steps=max_steps, top_k=top_k)

    @server.tool()
    def sweep(parameter: str, values: list[StrictFloat | StrictInt], rationale: str,
              agent: str, base_id: Optional[StrictInt] = None) -> dict[str, Any]:
        """Simulate 2..10 values of ONE parameter on a fixed base design (default: the best)
        in a single call: len(values) simulator calls but one decision. Use it for 1-D fine
        tuning (Rc, Cc, one multiplicity) instead of several simulate calls. Values must be
        on the grid. Returns each value's id, reward, feasibility and key specs."""
        return call("sweep", parameter=parameter, values=values, rationale=rationale,
                    agent=agent, base_id=base_id)

    @server.tool()
    def train(n_steps: StrictInt, noise_sigma: Optional[StrictFloat] = None) -> dict[str, Any]:
        """Run the TD3 RL sizer for n_steps steps (1..1000): it proposes designs, simulates
        them and learns from the shared replay buffer. Costs ~1.1 simulations per step.
        Needs replay_size >= 128 (warmup and/or seed_rl first). Prefer batches of 100-300
        and check improved_best before continuing. noise_sigma (0.01..0.5, default 0.1)
        sets the exploration noise: smaller = finer local search around the actor's design."""
        return call("train", n_steps=n_steps, noise_sigma=noise_sigma)

    @server.tool()
    def seed_rl(k: StrictInt = 5, repeat: StrictInt = 1, only_feasible: StrictBool = False,
                anchor_steps: StrictInt = 0) -> dict[str, Any]:
        """Copy the k best LLM-simulated designs into the RL replay buffer (no simulation),
        each repeat times (1..10). anchor_steps (e.g. 300) also pretrains the TD3 actor to
        propose the best expert design (behaviour cloning), so RL explores around it
        instead of starting from random designs. Costs no simulations. Call before train."""
        return call("seed_rl", k=k, repeat=repeat, only_feasible=only_feasible, anchor_steps=anchor_steps)

    @server.tool()
    def get_status(k: StrictInt = 5) -> dict[str, Any]:
        """Counters (simulator calls, RL steps, elapsed time) and the k best designs
        (1..20) with parameters, specs, reward and violated constraints. No simulation."""
        return call("get_status", k=k)

    @server.tool()
    def get_lineage(candidate_id: StrictInt) -> dict[str, Any]:
        """The chain of designs that led to a candidate: for each step the agent, the
        changed parameters, the rationale and the result. Use it to explain a solution."""
        return call("get_lineage", candidate_id=candidate_id)

    @server.tool()
    def operating_point(candidate_id: Optional[StrictInt] = None) -> dict[str, Any]:
        """Transistor-level DC operating point of an ALREADY SIMULATED design (default: the
        best). 0 simulator calls: the data was saved by that design's own simulation.

        Returns warnings (devices in triode or close to it; output at a rail = balance
        condition broken, with the side to fix), notes (2nd pole vs UGBW, Rc zero, gain
        estimate), circuit values (I_bias, I_tail, I_2, stage gains A1/A2, gm1/(2pi Cc),
        p2 = gm6/(2pi CL), zero, balance ratio of the sizes, DC levels) and per device Id,
        gm, gds, Vgs, Vth, Vov, Vds, Vdsat, saturation margin, region, inversion, gm/Id,
        gm/gds. Use it to find WHY a spec fails before choosing a lever."""
        return call("operating_point", candidate_id=candidate_id)

    @server.tool()
    def compare_operating_points(id_a: StrictInt, id_b: StrictInt) -> dict[str, Any]:
        """What changed electrically between two simulated designs, e.g. parent -> child to
        explain a failed prediction, or expert design -> RL best. 0 simulator calls.
        Returns parameter changes, specs of both, device and circuit quantities that moved
        by more than 5 % (with region/inversion changes) and warnings that appeared or
        disappeared."""
        return call("compare_operating_points", id_a=id_a, id_b=id_b)

    @server.tool()
    def quick_analysis(variants: list[dict[str, StrictFloat | StrictInt]], rationale: str,
                       agent: str, analyses: list[str] = ["op"],
                       base_id: Optional[StrictInt] = None,
                       corner: Optional[dict[str, str | StrictFloat | StrictInt]] = None,
                       include_devices: StrictBool = False) -> dict[str, Any]:
        """CHEAP screening of 1..10 variants BEFORE spending simulator calls. NOT a simulator
        call and NOT a candidate (never best, Pareto front or RL data): confirm the variant you
        choose with simulate. Each run is counted in quick_runs.

        variants: partial parameter dicts applied to base_id (default: the best), e.g.
        [{"mn5": 10}, {"mn5": 12}]; {} = the base design itself.
        analyses: any of "op" (~0.01 s: exact current, transistor operating point, bias
        warnings), "ac" (~0.01 s: exact gain, UGBW, PM), "noise" (~0.01 s: exact noise),
        "tran" (~0.1 s: slew rate from a short 5 us transient). Area is always given.
        corner: optional PVT corner, e.g. {"process": "SS", "temp": 80, "voltage": 1.1};
        default TT, 27 C, 1.2 V (the corner of simulate).
        Per variant: measured specs, violated hard constraints among them, not_measured,
        reward/feasible if all 7 specs were measured, otherwise fom_if_feasible (the FoM if
        the unmeasured specs pass; area and current are exact), and with "op": op_warnings,
        op_notes and key circuit values (full device table: include_devices=True)."""
        return call("quick_analysis", variants=variants, analyses=analyses, rationale=rationale,
                    agent=agent, base_id=base_id, corner=corner, include_devices=include_devices)

    @server.tool()
    def corner_check(rationale: str, agent: str, candidate_id: Optional[StrictInt] = None,
                     variant: Optional[dict[str, StrictFloat | StrictInt]] = None,
                     analyses: list[str] = ["op", "ac", "noise", "tran"]) -> dict[str, Any]:
        """CHEAP robustness check of one design over the 12 PVT corners {TT,SS,FF} x
        {1.2 V, 1.0 V} x {0 C, 100 C} (~1 s, 12 quick runs, 0 simulator calls, not a candidate).
        candidate_id: a simulated design (default: the best); variant: optional partial
        parameter dict applied to it, e.g. {"cap": 7e-13}.
        Returns worst_case (worst value of every spec and the corner that sets it),
        worst_case_fom and feasible_in_all_corners (the FoM of the PVT-robust mode),
        failing_corners, and per corner the specs and violated hard constraints."""
        return call("corner_check", rationale=rationale, agent=agent, candidate_id=candidate_id,
                    variant=variant, analyses=analyses)

    @server.tool()
    def write_memory(agent: str, kind: str, content: str) -> dict[str, Any]:
        """Leave a SHORT note (<= 2000 chars) for the other agents. kind is one of
        plan, observation, decision, result, lesson, model. Write conclusions, not raw data.
        kind "model" (modeler only, <= 4000 chars): the COMPLETE current design model of
        this run, written as a new version each time it changes."""
        return call("write_memory", agent=agent, kind=kind, content=content)

    @server.tool()
    def read_memory(agent: str = "", kind: str = "", last_n: StrictInt = 10) -> dict[str, Any]:
        """Read the most recent notes of the other agents, optionally filtered by agent
        and/or kind. Read this before acting instead of asking for the full history.
        read_memory(kind="model", last_n=1) gives the current design model."""
        return call("read_memory", agent=agent, kind=kind, last_n=last_n)

    return server


def main():
    parser = argparse.ArgumentParser(description="CAD sizing MCP server (stdio)")
    parser.add_argument("--seed", type=int, default=123456)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--replay-size", type=int, default=100_000)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()
    # Existing course code resolves model/netlist paths relative to the project.
    os.chdir(Path(__file__).resolve().parent)
    with redirect_stdout(sys.stderr):
        experiment = SizingExperiment(args.seed, args.batch_size, args.replay_size, args.run_id)
    create_server(experiment).run(transport="stdio")


if __name__ == "__main__":
    main()
