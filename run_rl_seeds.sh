#!/usr/bin/env bash
# Extra seeds of the final TD3 configuration (and of the SAC baseline), run in parallel,
# so the milestone-3 comparison has a mean and a spread instead of one run per method.
#
#   bash run_rl_seeds.sh                 (TD3 seeds 7 and 42, SAC seed 7; 5000 sims each)
#   SEEDS="7 42" SAC_SEEDS="" bash run_rl_seeds.sh
#   GAMMA=0.0 SEEDS="7 42 1 2" SAC_SEEDS="" bash run_rl_seeds.sh      (gamma-0 config -> final_g0_s<seed>)
#
# The final TD3 run (final_g099) used: --w 128 --gamma 0.99, everything else at its default
# (noise 0.1, batch 128, pi_lr 3e-4, q_lr 1e-3), seed 123456. Outputs go to
# output_figs/final_g099_s<seed>/ and output_figs/sac_baseline_s<seed>/ like every RL run.
# Do NOT start this while an agy sweep is running: the sweep hides output_figs/ and solutions/.
set -uo pipefail
cd "$(dirname "$0")"
SEEDS="${SEEDS:-7 42}"
SAC_SEEDS="${SAC_SEEDS-7}"          # SAC_SEEDS="" means: no SAC run
SIMS="${SIMS:-5000}"
GAMMA="${GAMMA:-0.99}"
PREFIX="${PREFIX:-$([ "$GAMMA" = "0.0" ] && echo final_g0 || echo final_g099)}"
PY="${PY:-.venv/bin/python}"
PY39="${PY39:-.venv39/bin/python}"     # SAC baseline is compiled for Python 3.9
# one torch process must not grab all cores when several runs share the machine
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-2}"

if pgrep -x agy >/dev/null; then echo "agy is running: start the seeds after the sweep."; exit 1; fi
echo "=== RL seeds started $(date +%T) on $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)"
pids=()
for s in $SEEDS; do
  id="${PREFIX}_s$s"
  rm -f "solutions/$id.csv"
  $PY -u td3_runner.py --max_sims "$SIMS" --seed "$s" --run_id "$id" --w 128 --gamma "$GAMMA" \
      > "output_figs/$id.log" 2>&1 &
  pids+=($!); echo "    TD3 seed $s -> output_figs/$id (pid $!)"
done
for s in $SAC_SEEDS; do
  id="sac_baseline_s$s"
  if [ -f "output_figs/$id/summary.json" ]; then echo "    skip SAC seed $s (done)"; continue; fi
  $PY39 -u baseline_runner.py --max_sims "$SIMS" --seed "$s" --run_id "$id" > "output_figs/$id.log" 2>&1 &
  pids+=($!); echo "    SAC seed $s -> output_figs/$id (pid $!)"
done
wait "${pids[@]}"
echo "=== RL seeds done $(date +%T)"
for d in output_figs/${PREFIX}_s* output_figs/sac_baseline_s*; do
  [ -f "$d/summary.json" ] && $PY -c "
import json,sys; s=json.load(open('$d/summary.json'))
print('    $d: best FoM %.4f, first feasible at sims %s, runtime %.0f s' % (s['best_fom'], s.get('first_feasible_step_and_sims'), s.get('runtime_s', 0)))"
done
