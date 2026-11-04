"""
Unit tests for Milestone 3: the TD3 agent (td3/agent.py) and the runner (td3_runner.py).

    1. select_action        shape, range, deterministic part, noise std
    2. update_parameters    TD target by hand (incl. done -> no bootstrap), delayed actor
                            update, soft target update with tau
    3. learning             TD3 finds the optimum of a toy "design" problem whose
                            structure is the same as the circuit env (s' depends on a only)
    4. runner               full td3_runner.main() with ngspice mocked: simulation budget,
                            logs, plots, Solutions folder

Run from CAD/:   python -m pytest test_td3_agent.py -v
(add  -m "not slow"  to skip the learning test)
"""
import copy
import csv
import json
import os
import types

import numpy as np
import pytest
import torch
from gymnasium.spaces import Box

from td3 import TD3, ReplayBuffer

STATE_DIM, ACTION_DIM = 7, 20


def make_args(**kw):
    a = dict(gamma=0.99, tau=0.005, noise_sigma=0.1, actor_update_interval=2,
             pi_lr=3e-4, q_lr=1e-3)
    a.update(kw)
    return types.SimpleNamespace(**a)


def make_agent(**kw):
    torch.manual_seed(0)
    np.random.seed(0)
    space = Box(low=-np.ones(ACTION_DIM), high=np.ones(ACTION_DIM))
    return TD3(STATE_DIM, space, make_args(**kw))


def random_batch(n=64, done_frac=0.1):
    g = torch.Generator().manual_seed(1)
    s = torch.randn(n, STATE_DIM, generator=g)
    a = torch.rand(n, ACTION_DIM, generator=g) * 2 - 1
    s2 = torch.randn(n, STATE_DIM, generator=g)
    r = torch.randn(n, 1, generator=g)
    nd = (torch.rand(n, 1, generator=g) > done_frac).float()
    return s, a, s2, r, nd


def params(net):
    return [p.detach().clone() for p in net.parameters()]


def changed(before, net):
    return any(not torch.equal(b, p) for b, p in zip(before, net.parameters()))


# ----------------------------------------------------------------------------
# 1. select_action
# ----------------------------------------------------------------------------
def test_select_action_shape_and_range():
    agent = make_agent(noise_sigma=2.0)          # huge noise -> clipping must kick in
    for _ in range(50):
        a = agent.select_action(np.random.randn(STATE_DIM).astype(np.float32))
        assert isinstance(a, np.ndarray) and a.shape == (ACTION_DIM,)
        assert np.all(a >= -1.0) and np.all(a <= 1.0)


def test_select_action_accepts_tensor():
    agent = make_agent()
    a = agent.select_action(torch.randn(STATE_DIM))
    assert a.shape == (ACTION_DIM,)


def test_select_action_deterministic_part_and_noise_std():
    agent = make_agent(noise_sigma=0.1)
    s = np.zeros(STATE_DIM, dtype=np.float32)
    mu = agent.select_action(s, explore=False)
    with torch.no_grad():
        expected = agent.actor(torch.zeros(1, STATE_DIM)).numpy().flatten()
    np.testing.assert_allclose(mu, expected, atol=1e-6)

    samples = np.array([agent.select_action(s) for _ in range(4000)]) - mu
    # mu is near 0 at init, so clipping at +-1 is negligible for sigma = 0.1
    assert abs(samples.mean()) < 0.01
    assert samples.std() == pytest.approx(0.1, rel=0.05)


# ----------------------------------------------------------------------------
# 2. update_parameters
# ----------------------------------------------------------------------------
def test_critic_loss_matches_hand_computed_td_target():
    agent = make_agent()
    agent.policy_noise = 0.0                      # remove the random smoothing for the check
    s, a, s2, r, nd = random_batch()
    with torch.no_grad():
        q1t, q2t = agent.critic_target(s2, agent.actor_target(s2))
        y = r + nd * agent.discount * torch.min(q1t, q2t)
        q1, q2 = agent.critic(s, a)
        expected = ((q1 - y) ** 2).mean() + ((q2 - y) ** 2).mean()
    losses = agent.update_parameters((s, a, s2, r, nd))
    assert losses['critic_loss'] == pytest.approx(expected.item(), rel=1e-5)


def test_done_means_no_bootstrap():
    agent = make_agent()
    s, a, s2, r, _ = random_batch()
    nd = torch.zeros_like(r)                      # every transition terminal -> y = r
    with torch.no_grad():
        q1, q2 = agent.critic(s, a)
        expected = ((q1 - r) ** 2).mean() + ((q2 - r) ** 2).mean()
    losses = agent.update_parameters((s, a, s2, r, nd))
    assert losses['critic_loss'] == pytest.approx(expected.item(), rel=1e-5)


def test_delayed_actor_and_target_updates():
    agent = make_agent(actor_update_interval=2)
    batch = random_batch()

    a0, c0 = params(agent.actor), params(agent.critic)
    at0, ct0 = params(agent.actor_target), params(agent.critic_target)
    out = agent.update_parameters(batch)          # total_it = 1 -> critic only
    assert changed(c0, agent.critic)
    assert not changed(a0, agent.actor)
    assert not changed(at0, agent.actor_target) and not changed(ct0, agent.critic_target)
    assert 'actor_loss' not in out

    a1 = params(agent.actor)
    out = agent.update_parameters(batch)          # total_it = 2 -> actor + targets too
    assert changed(a1, agent.actor)
    assert changed(at0, agent.actor_target) and changed(ct0, agent.critic_target)
    assert 'actor_loss' in out


def test_soft_update_formula():
    agent = make_agent(tau=0.1)
    net, target = agent.actor, copy.deepcopy(agent.actor)
    with torch.no_grad():
        for p in target.parameters():
            p.add_(1.0)                           # target = net + 1
    before = params(target)
    agent._soft_update(net, target)
    for b, p, t in zip(before, net.parameters(), target.parameters()):
        torch.testing.assert_close(t, 0.1 * p + 0.9 * b)


# ----------------------------------------------------------------------------
# 3. learning on a toy problem with the same structure as the circuit env
# ----------------------------------------------------------------------------
@pytest.mark.slow
def test_td3_learns_toy_design_problem():
    """
    Hidden optimum a*. Reward = -mean((a - a*)^2); the next state depends only on the
    action (like an absolute design); episodes of 10 steps. A working TD3 must move mu(s)
    close to a* with a few thousand interactions.
    """
    torch.manual_seed(0)
    np.random.seed(0)
    a_star = np.random.uniform(-0.8, 0.8, ACTION_DIM)
    proj = np.random.randn(ACTION_DIM, STATE_DIM) / np.sqrt(ACTION_DIM)

    def env_step(a):
        return np.tanh(a @ proj).astype(np.float32), -float(np.mean((a - a_star) ** 2))

    space = Box(low=-np.ones(ACTION_DIM), high=np.ones(ACTION_DIM))
    agent = TD3(STATE_DIM, space, make_args(gamma=0.99, noise_sigma=0.1))
    buf = ReplayBuffer(STATE_DIM, ACTION_DIM, max_size=10_000)

    def run_episode(policy, learn):
        obs, _ = env_step(np.random.uniform(-1, 1, ACTION_DIM))
        for t in range(10):
            a = policy(obs)
            nxt, r = env_step(a)
            buf.push(obs, a, r, nxt, t == 9)
            obs = nxt
            if learn:
                agent.update_parameters(buf.sample(128))

    for _ in range(30):                           # 300 warmup steps
        run_episode(lambda o: np.random.uniform(-1, 1, ACTION_DIM), learn=False)
    random_err = np.mean((np.random.uniform(-1, 1, (1000, ACTION_DIM)) - a_star) ** 2)
    for _ in range(300):                          # 3000 learning steps
        run_episode(agent.select_action, learn=True)

    final = agent.select_action(np.zeros(STATE_DIM, dtype=np.float32), explore=False)
    err = np.mean((final - a_star) ** 2)
    assert err < 0.2 * random_err, f"policy error {err:.4f} vs random {random_err:.4f}"


# ----------------------------------------------------------------------------
# 4. the runner end-to-end, ngspice mocked
# ----------------------------------------------------------------------------
def fake_specs(params):
    """Smooth made-up circuit: specs improve with the multipliers; about half the designs feasible."""
    m = np.mean([v for k, v in params.items() if k.startswith('m')]) / 25.0      # 0.04 .. 1
    return {'area': 1e-9 + 3e-9 * m, 'current': 5e-5 + 4e-4 * m,
            'gain': 400 * m, 'noise': 0.01, 'phm': 70.0,
            'slewRate': 60 * m, 'ugbw': 2e8 * m}


def test_runner_end_to_end_mocked(tmp_path, monkeypatch):
    import shutil
    import td3_runner
    from circuit_env import CircuitEnv

    cad = os.path.dirname(os.path.abspath(__file__))
    for item in ('ngspice_interface', 'clean.sh'):
        src = os.path.join(cad, item)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(src, tmp_path / item)
    monkeypatch.chdir(tmp_path)

    def counted_fake(self, params):
        self.n_simulations += 1
        return fake_specs(params)
    monkeypatch.setattr(CircuitEnv, 'simulate', counted_fake)

    args = td3_runner.readParser(['--max_sims', '220', '--w', '50', '--batch_size', '32',
                                  '--run_id', 'test'])
    td3_runner.main(args)

    with open('output_figs/test/summary.json') as f:
        summary = json.load(f)
    assert summary['n_simulations'] <= 220                # budget respected (reset counted)
    assert summary['n_simulations'] >= 210
    with open('output_figs/test/history.csv') as f:
        hist = list(csv.DictReader(f))
    assert len(hist) == summary['env_steps']
    assert {r['phase'] for r in hist} == {'warmup', 'td3'}
    assert sum(r['phase'] == 'warmup' for r in hist) == 50
    for fig in ('max_reward.png', 'pareto.png', 'average_score.png'):
        assert os.path.isfile(f'output_figs/test/{fig}')
    sols = os.listdir('Solutions/test')
    assert 'pareto_solutions.csv' in sols
    assert any(f.endswith('.cir') for f in sols)
