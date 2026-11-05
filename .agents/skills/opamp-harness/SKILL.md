---
name: opamp-harness
description: Orchestrates explainable sizing of the two-stage Miller opamp with the cad MCP tools. Use when asked to size, optimize or improve the opamp, or to run the sizing harness.
---

# Opamp sizing harness (orchestrator)

You coordinate five specialist agents. Each one has its own skill; read that skill
before acting in its role, and act ONLY in that role until it hands over.
If subagents are available, start each role as a subagent with its skill and pass it
only the memory it needs. Otherwise play the roles one after another in this session.

| Role (agent name) | Skill | Job | Tools |
|---|---|---|---|
| analyst | circuit-analyst | Explain topology, derive a first design from equations | design_space, simulate (1-2), write_memory |
| diagnoser | diagnoser | Find the binding spec of the current best and pick the lever | get_status, read_memory, write_memory |
| sizer | sizer | One targeted change per simulation, predicted then checked | simulate, read_memory, write_memory |
| rl | rl-strategist | Decide if and how to run the TD3 sizer, seeded with expert designs | seed_rl, warmup, train, get_status |
| reviewer | reviewer | Verify and explain the final solution | get_status, get_lineage, read_memory |

## Loop

1. analyst (once).
2. Repeat: diagnoser -> sizer. Budget for hand sizing: about 25 simulations.
3. Hand over to rl when the diagnoser reports a stall (3 sizer simulations in a row
   without a better reward) or when the design is feasible and only area/current
   remain. Afterwards one more diagnoser -> sizer round to polish the RL result.
4. reviewer (once) writes the final explanation.

## Rules for every role

- Context: start each role by calling `read_memory` (last 5-10 entries). Do not re-read
  the netlist or old tool outputs; the memory is the shared context.
- Memory: end each role with one `write_memory` entry (kind plan/observation/decision/
  result/lesson), at most a few sentences, with candidate ids and numbers.
- Every `simulate` call needs a rationale with a prediction (which spec moves, which way).
- Simulations are expensive. Never simulate to "see what happens".
- Narrate each decision for the user in 1-3 sentences: what, why, expected effect.
