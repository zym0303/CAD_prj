#!/usr/bin/env bash
# N fresh LLM-harness runs (default 3, Gemini 3.8 Flash High) on the current code, start to finish:
#   1. hide earlier results (hide_past_runs.sh) so the runs cannot read them
#   2. run_harness_batch.sh: N agy runs, each moved out of the project when it ends
#   3. restore everything (also when a run fails or you press Ctrl-C), new runs included
#   4. figure of the new runs (best FoM vs. simulations, Pareto front)
#
#   nohup bash sweep_flash_high.sh > sweep_high.log 2>&1 &
#   N=5 MODEL=gemini-3.8-flash-medium TAG=medium bash sweep_flash_high.sh
#
# While it runs: do NOT git stash / checkout / pull (that brings the hidden files back and
# changes the code under the running harness). Look at the results, edit nothing.
#
# Outputs: harness_runs/, solutions/, output_figs/<run_id>/ as usual, plus in
# ~/CAD_prj_sweeps/<TAG>_<date>/ (outside the repo): agy transcripts, token_usage.csv,
# results.csv, fig.png and git.txt (branch, commit and uncommitted changes of the code used)
set -uo pipefail
cd "$(dirname "$0")"

N="${N:-3}"; MODEL="${MODEL:-gemini-3.8-flash-high}"; TAG="${TAG:-flash_high}"
STAMP=$(date +%Y%m%d_%H%M)
export CAD_ARCHIVE="${CAD_ARCHIVE:-$HOME/CAD_prj_archive_$STAMP}"   # new, empty archive per sweep
SWEEP="$HOME/CAD_prj_sweeps/${TAG}_$STAMP"
export TRANSCRIPTS="$SWEEP/agy_transcripts" TOKEN_CSV="$SWEEP/token_usage.csv"

if pgrep -x agy >/dev/null; then echo "Close the open agy session first."; exit 1; fi
if git status --porcelain | grep -q '^ D\|^D '; then
  echo "git shows deleted files: an earlier hide was not restored. Run restore_past_runs.sh first."; exit 1
fi
mkdir -p "$TRANSCRIPTS"
{ echo "branch: $(git rev-parse --abbrev-ref HEAD)"; echo "commit: $(git log --oneline -1)";
  echo "model: $MODEL"; echo; git status --short; echo; git diff HEAD; } > "$SWEEP/git.txt"

bash hide_past_runs.sh || exit 1
trap 'echo "=== restoring project data"; bash restore_past_runs.sh' EXIT

N="$N" MODEL="$MODEL" bash run_harness_batch.sh
status=$?

bash restore_past_runs.sh && trap - EXIT

runs=$(tail -n +2 "$TOKEN_CSV" 2>/dev/null | cut -d, -f1 | tr '\n' ' ')
if [ -n "$runs" ]; then
  .venv/bin/python plot_harness_runs.py --title "LLM harness, $MODEL: $N runs ($STAMP)" \
      --out "harness_${TAG}_$STAMP" $runs
  cp "output_figs/comparison/harness_${TAG}_$STAMP.png" "$SWEEP/fig.png"
  cp "output_figs/comparison/harness_${TAG}_$STAMP.csv" "$SWEEP/results.csv"
  echo "=== tokens"; column -s, -t "$TOKEN_CSV" | cut -c1-200
fi
echo "=== sweep done (batch exit $status). Results: $SWEEP"
