#!/usr/bin/env bash
# Run the LLM harness N times in a row. Each run is a fresh agy session in print mode (it
# opens, runs the prompt to the end and exits by itself). After every run, its results are
# moved OUT of the project, so the next run cannot read them.
#
#   bash run_harness_batch.sh                         (5 runs)
#   N=3 bash run_harness_batch.sh                     (3 runs)
#   MODEL=gemini-3.8-flash-high bash run_harness_batch.sh
#
# Per run, in ~/CAD_prj_archive (or $CAD_ARCHIVE):
#   harness_runs/<run_id>/, solutions/<run_id>.csv, output_figs/<run_id>/   (the usual outputs)
#   agy_transcripts/<run_id>.jsonl   full agy trace (reasoning, tool calls, timing) for the report
#   agy_transcripts/<run_id>.db      agy's conversation record (source of the token counts)
#   token_usage.csv                  one row per run: LLM calls, input (cached / uncached), output
# Bring everything back afterwards with:  bash restore_past_runs.sh
set -uo pipefail
cd "$(dirname "$0")"

N="${N:-5}"
MODEL="${MODEL:-gemini-3.8-flash-high}"             # = "Gemini 3.8 Flash (High)"
PROMPT="${PROMPT:-Use the opamp-harness skill to size the opamp (full mode).}"
RUN_TIMEOUT="${RUN_TIMEOUT:-60m}"                   # safety limit per run
MAX_LOAD="${MAX_LOAD:-16}"   # wait before a run while the 1-min load is above this: an overloaded
                             # machine makes ngspice hit its 20 s timeout and almost every simulation fails
BRANCH=$(git rev-parse --abbrev-ref HEAD)   # do NOT git checkout / stash while the batch runs
ARCHIVE="${CAD_ARCHIVE:-$HOME/CAD_prj_archive}"
TRANSCRIPTS="${TRANSCRIPTS:-$ARCHIVE/agy_transcripts}"
TOKEN_CSV="${TOKEN_CSV:-$ARCHIVE/token_usage.csv}"
mkdir -p "$ARCHIVE/harness_runs" "$ARCHIVE/solutions" "$ARCHIVE/output_figs" "$TRANSCRIPTS"

mcp_running() { ps -eo comm,args | awk '$1 ~ /^python/ && /CAD_prj\/mcp_server\.py/' | grep -q .; }

for i in $(seq 1 "$N"); do
  echo "=== run $i/$N  started $(date +%T)  model=$MODEL  branch=$BRANCH  load $(cut -d' ' -f1 /proc/loadavg)"

  if [ "$(git rev-parse --abbrev-ref HEAD)" != "$BRANCH" ]; then
    echo "The git branch changed during the batch (now $(git rev-parse --abbrev-ref HEAD)): stopping."; exit 1
  fi

  if pgrep -x agy >/dev/null; then echo "Another agy session is open: close it first."; exit 1; fi
  for d in harness_runs solutions output_figs; do
    if [ -n "$(ls -A "$d" 2>/dev/null)" ]; then
      echo "$d/ is not empty: move old results out first (bash hide_past_runs.sh)."; exit 1
    fi
  done
  mkdir -p no_backup && bash clean.sh >/dev/null 2>&1     # old generated netlists out

  while :; do
    load=$(cut -d' ' -f1 /proc/loadavg)
    awk -v l="$load" -v m="$MAX_LOAD" 'BEGIN{exit !(l <= m)}' && break
    echo "    load $load > $MAX_LOAD: waiting 60 s before starting"; sleep 60
  done

  T=$(date +%Y%m%d_%H%M%S); start=$(date +%s)
  agy -p "$PROMPT" --model "$MODEL" --dangerously-skip-permissions \
      --output-format stream-json --print-timeout "$RUN_TIMEOUT" \
      > "$TRANSCRIPTS/agy_$T.jsonl" 2> "$TRANSCRIPTS/agy_$T.err"
  echo "    agy exited (code $?) after $(( $(date +%s) - start )) s"

  # let the MCP server finish its last write and exit with agy
  for _ in $(seq 1 30); do mcp_running || break; sleep 1; done
  if mcp_running; then echo "    MCP server still alive: stopping it"; pkill -f "CAD_prj/mcp_server.py"; sleep 2; fi

  run=$(ls -1 harness_runs 2>/dev/null | tail -1)
  if [ -z "$run" ]; then
    echo "    No harness run was created: see $TRANSCRIPTS/agy_$T.err"; exit 1
  fi
  mv "harness_runs/$run" "$ARCHIVE/harness_runs/"
  [ -e "solutions/$run.csv" ] && mv "solutions/$run.csv" "$ARCHIVE/solutions/"
  [ -e "output_figs/$run" ] && mv "output_figs/$run" "$ARCHIVE/output_figs/"
  mv "$TRANSCRIPTS/agy_$T.jsonl" "$TRANSCRIPTS/$run.jsonl"
  mv "$TRANSCRIPTS/agy_$T.err" "$TRANSCRIPTS/$run.err"
  rmdir harness_runs solutions output_figs 2>/dev/null

  # token usage: agy's own record of this conversation (newest conversation written during the run)
  conv=$(ls -t "$HOME/.gemini/antigravity-cli/conversations/"*.db 2>/dev/null | head -1)
  if [ -n "$conv" ] && [ "$(stat -c %Y "$conv")" -ge "$start" ]; then
    cp "$conv" "$TRANSCRIPTS/$run.db"
    python3 agy_token_usage.py "$TRANSCRIPTS/$run.db" --run-id "$run" --csv "$TOKEN_CSV" \
      | sed 's/^/    tokens: /' || echo "    could not read token usage from $conv"
  else
    echo "    no agy conversation found for this run: token usage not recorded"
  fi

  python3 - "$ARCHIVE/harness_runs/$run/summary.json" <<'PY' || true
import json, sys
s = json.load(open(sys.argv[1])); b = s.get("best") or {}
print(f"    {s.get('run_id')}: {s.get('simulator_calls')} sims, {s.get('elapsed_s')} s, "
      f"best FoM {b.get('reward')}, feasible {b.get('feasible')} | quick_analysis "
      f"{s.get('quick_calls')} calls / {s.get('quick_runs')} runs, corner_checks {s.get('corner_checks')}, "
      f"op_lookups {s.get('op_lookups')}  -> moved to archive")
PY
done
echo "=== all $N runs done at $(date +%T). Restore everything with: bash restore_past_runs.sh"
