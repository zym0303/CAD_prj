#!/usr/bin/env bash
# Milestone 3 robustness runs, all in one background job:
#   (a) the final comparison with more seeds: TD3 final config (--w 128 --gamma 0.99) seeds 1, 2
#       and the TAs' SAC baseline seeds 7, 42, 5000 simulations each (adds to seeds 123456 / 7 / 42
#       of TD3 and 123456 of SAC that already exist);
#   (b) the hyperparameter sweep of run_sweep.sh repeated with seeds 7 and 42, 2000 simulations
#       each (12 configs x 2 seeds), so every cell of the sweep table gets 3 seeds.
#
#   nohup bash run_rl_overnight.sh > rl_overnight.log 2>&1 &
#
# Runs up to $PAR jobs in parallel (each is one ngspice + a small torch model). Outputs go to
# output_figs/<id>/ and solutions/<id>.csv as usual; a finished run (summary.json present) is
# skipped, so the script can be restarted. Do NOT start an agy sweep while this runs: the sweep
# scripts move output_figs/ and solutions/ out of the project.
set -uo pipefail
cd "$(dirname "$0")"
PAR="${PAR:-8}"
# one torch process must not grab all cores: 8 jobs x 24 threads overloaded the machine (load 36)
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-2}"
PY="${PY:-.venv/bin/python}"            # TD3
PY39="${PY39:-.venv39/bin/python}"      # SAC baseline (compiled for Python 3.9)
mkdir -p output_figs solutions

if pgrep -x agy >/dev/null; then echo "agy is running: start this after the harness sweep."; exit 1; fi
echo "=== started $(date +%T) on $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD), $PAR parallel"

# job list: "<run_id>|<python>|<runner>|<args>"  (long 5000-sim runs first)
JOBS=()
for s in 1 2;  do JOBS+=("final_g099_s$s|$PY|td3_runner.py|--max_sims 5000 --seed $s --w 128 --gamma 0.99"); done
for s in 7 42; do JOBS+=("sac_baseline_s$s|$PY39|baseline_runner.py|--max_sims 5000 --seed $s"); done
for s in 7 42; do
  JOBS+=("sw_base_s$s|$PY|td3_runner.py|--max_sims 2000 --seed $s")
  for n in 0.05 0.2 0.3; do JOBS+=("sw_noise${n}_s$s|$PY|td3_runner.py|--max_sims 2000 --seed $s --noise_sigma $n"); done
  for g in 0.5 0.0;      do JOBS+=("sw_gamma${g}_s$s|$PY|td3_runner.py|--max_sims 2000 --seed $s --gamma $g"); done
  for b in 64 256;       do JOBS+=("sw_batch${b}_s$s|$PY|td3_runner.py|--max_sims 2000 --seed $s --batch_size $b"); done
  for w in 128 1000;     do JOBS+=("sw_w${w}_s$s|$PY|td3_runner.py|--max_sims 2000 --seed $s --w $w"); done
  JOBS+=("sw_lr_slow_s$s|$PY|td3_runner.py|--max_sims 2000 --seed $s --pi_lr 1e-4 --q_lr 3e-4")
  JOBS+=("sw_lr_fast_s$s|$PY|td3_runner.py|--max_sims 2000 --seed $s --pi_lr 1e-3 --q_lr 1e-3")
done

run_job() {   # one run, foreground
  local id=$1 py=$2 runner=$3 args=$4 start=$(date +%s)
  rm -f "solutions/$id.csv"
  $py -u "$runner" --run_id "$id" $args > "output_figs/$id.log" 2>&1
  local code=$?
  if [ -f "output_figs/$id/summary.json" ]; then
    $PY -c "import json; s=json.load(open('output_figs/$id/summary.json')); print('    done $id: best FoM %.4f, first feasible %s, %d failed sims, %d s' % (s['best_fom'], s.get('first_feasible_step_and_sims'), s.get('n_failed_sims', -1), $(date +%s)-$start))"
  else
    echo "    FAILED $id (exit $code): see output_figs/$id.log"
  fi
}

running=0
for job in "${JOBS[@]}"; do
  IFS='|' read -r id py runner args <<< "$job"
  if [ -f "output_figs/$id/summary.json" ]; then echo "    skip $id (done)"; continue; fi
  while [ "$running" -ge "$PAR" ]; do wait -n; running=$((running-1)); done
  echo "    start $id  ($(date +%T), load $(cut -d' ' -f1 /proc/loadavg))"
  run_job "$id" "$py" "$runner" "$args" &
  running=$((running+1))
done
wait
echo "=== all done $(date +%T)"
