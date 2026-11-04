#!/bin/bash
# Hyperparameter sweep for Milestone 3, one parameter at a time around the default
# (noise_sigma 0.1, batch 128, w 300, pi_lr 3e-4, q_lr 1e-3, gamma 0.99).
# Short runs (SIMS simulations each) to save time; the winner gets the full 5k run.
#
#   cd CAD && source .venv/bin/activate && bash run_sweep.sh            # all groups
#   bash run_sweep.sh noise                                              # one group
#
# Afterwards, compare a group, e.g.:
#   python compare_runs.py --runs sw_base:base sw_noise0.05:0.05 sw_noise0.2:0.2 sw_noise0.3:0.3 --max_sims 2000

SIMS=${SIMS:-2000}
SEED=${SEED:-123456}
GROUP=${1:-all}

run () {   # run <run_id> <extra args...>
  local id=$1; shift
  if [ -f "output_figs/$id/summary.json" ]; then echo "skip $id (done)"; return; fi
  echo "=== $id $* ==="
  python td3_runner.py --max_sims "$SIMS" --seed "$SEED" --run_id "$id" "$@" > "output_figs/$id.log" 2>&1
  python -c "import json; d=json.load(open('output_figs/$id/summary.json')); print('  best FoM', d['best_fom'], '| first feasible (step, sims)', d['first_feasible_step_and_sims'], '| runtime', d['runtime_s'], 's')"
}
mkdir -p output_figs

[[ $GROUP == all || $GROUP == base  ]] && run sw_base
[[ $GROUP == all || $GROUP == noise ]] && for s in 0.05 0.2 0.3;    do run sw_noise$s --noise_sigma $s; done
[[ $GROUP == all || $GROUP == gamma ]] && for g in 0.5 0.0;         do run sw_gamma$g --gamma $g; done
[[ $GROUP == all || $GROUP == batch ]] && for b in 64 256;          do run sw_batch$b --batch_size $b; done
[[ $GROUP == all || $GROUP == w     ]] && for w in 128 1000;        do run sw_w$w --w $w; done
[[ $GROUP == all || $GROUP == lr    ]] && run sw_lr_slow --pi_lr 1e-4 --q_lr 3e-4 \
                                       && run sw_lr_fast --pi_lr 1e-3 --q_lr 1e-3
