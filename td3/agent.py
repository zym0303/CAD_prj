import copy
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


class Actor(nn.Module):
	def __init__(self, state_dim, action_dim, max_action):
		super(Actor, self).__init__()

		self.l1 = nn.Linear(state_dim, 256)
		self.l2 = nn.Linear(256, 256)
		self.l3 = nn.Linear(256, action_dim)
		
		self.max_action = max_action
		

	def forward(self, state):
		a = F.relu(self.l1(state))
		a = F.relu(self.l2(a))
		return self.max_action * torch.tanh(self.l3(a))


class Critic(nn.Module):
	def __init__(self, state_dim, action_dim):
		super(Critic, self).__init__()

		# Q1 architecture
		self.l1 = nn.Linear(state_dim + action_dim, 256)
		self.l2 = nn.Linear(256, 256)
		self.l3 = nn.Linear(256, 1)

		# Q2 architecture
		self.l4 = nn.Linear(state_dim + action_dim, 256)
		self.l5 = nn.Linear(256, 256)
		self.l6 = nn.Linear(256, 1)


	def forward(self, state, action):
		sa = torch.cat([state, action], 1)

		q1 = F.relu(self.l1(sa))
		q1 = F.relu(self.l2(q1))
		q1 = self.l3(q1)

		q2 = F.relu(self.l4(sa))
		q2 = F.relu(self.l5(q2))
		q2 = self.l6(q2)
		return q1, q2


	def Q1(self, state, action):
		sa = torch.cat([state, action], 1)

		q1 = F.relu(self.l1(sa))
		q1 = F.relu(self.l2(q1))
		q1 = self.l3(q1)
		return q1


class TD3(object):
    def __init__(self, state_dim, action_space, args):
        self.max_action = float(action_space.high[0])
        self.discount = args.gamma
        self.tau = args.tau
        self.policy_noise = 0.2
        self.noise_clip = 0.5
        self.expl_noise = args.noise_sigma
        self.policy_freq = args.actor_update_interval

        self.action_dim = action_space.shape[0]
        self.actor = Actor(state_dim, self.action_dim, self.max_action).to(device)
        self.actor_target = copy.deepcopy(self.actor)
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=args.pi_lr)

        self.critic = Critic(state_dim, self.action_dim).to(device)
        self.critic_target = copy.deepcopy(self.critic)
        self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=args.q_lr)

        self.total_it = 0


    def select_action(self, state, explore=True):
        """
        Action selection for the TD3 agent: a = clip(mu(s) + eps, -max_action, max_action),
        with eps ~ N(0, (max_action * expl_noise)^2) independently for every action component.

        Args:
            state: The current state observation (numpy array or tensor), shape (state_dim,)
            explore: if False, return the deterministic action mu(s) without noise
                     (useful to evaluate the learned policy)

        Returns:
            action: The selected action as a numpy array, shape (action_dim,)
        """
        # 1. numpy / CPU tensor -> float tensor with a batch dimension: (1, state_dim)
        if isinstance(state, np.ndarray):
            state = torch.FloatTensor(state.reshape(1, -1))
        else:
            state = state.float().reshape(1, -1)
        state = state.to(device)

        # 2. deterministic action of the actor (no gradient graph needed to act)
        with torch.no_grad():
            mu = self.actor(state).cpu().numpy().flatten()

        # 3. Gaussian exploration noise (np.random is seeded by the runner -> reproducible)
        if explore:
            noise = np.random.normal(0.0, self.max_action * self.expl_noise, size=self.action_dim)
            action = mu + noise
        else:
            action = mu

        # 4. keep the action in the valid range; 5. numpy array
        return np.clip(action, -self.max_action, self.max_action)


    def update_parameters(self, memory_batch, update=None):
        """
        One TD3 learning step on a mini-batch from the replay buffer.

        Args:
            memory_batch: Tuple of (state, action, next_state, reward, not_done) tensors,
                          in the order returned by ReplayBuffer.sample; reward and not_done
                          have shape (batch, 1)
            update: Update step (not used in this implementation)

        Returns:
            dict with the critic loss and (on actor-update steps) the actor loss, for logging
        """
        # 1. counter (used for the delayed actor update)
        self.total_it += 1

        # 2. unpack in the ReplayBuffer.sample order
        state, action, next_state, reward, not_done = memory_batch

        with torch.no_grad():
            # 3. target policy smoothing: clipped Gaussian noise on the target action
            noise = (torch.randn_like(action) * self.policy_noise * self.max_action
                     ).clamp(-self.noise_clip * self.max_action, self.noise_clip * self.max_action)
            next_action = (self.actor_target(next_state) + noise
                           ).clamp(-self.max_action, self.max_action)

            # 4. clipped double-Q: pessimistic (min) estimate of both target critics
            target_Q1, target_Q2 = self.critic_target(next_state, next_action)
            target_Q = torch.min(target_Q1, target_Q2)
            # TD target y = r + gamma * (1 - done) * min Q'   -> shape (batch, 1)
            target_Q = reward + not_done * self.discount * target_Q

        # 5. both critics regress on the same target y
        current_Q1, current_Q2 = self.critic(state, action)
        critic_loss = F.mse_loss(current_Q1, target_Q) + F.mse_loss(current_Q2, target_Q)

        # 6. critic update
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        losses = {'critic_loss': critic_loss.item()}

        # 7. delayed policy update (every policy_freq critic updates)
        if self.total_it % self.policy_freq == 0:
            # maximize Q1(s, mu(s))  <=>  minimize -Q1(s, mu(s))
            actor_loss = -self.critic.Q1(state, self.actor(state)).mean()

            self.actor_optimizer.zero_grad()
            actor_loss.backward()
            self.actor_optimizer.step()

            # soft (Polyak) update of the target networks: theta' <- tau*theta + (1-tau)*theta'
            self._soft_update(self.critic, self.critic_target)
            self._soft_update(self.actor, self.actor_target)

            losses['actor_loss'] = actor_loss.item()

        return losses


    def _soft_update(self, net, target_net):
        with torch.no_grad():
            for param, target_param in zip(net.parameters(), target_net.parameters()):
                target_param.data.mul_(1.0 - self.tau).add_(self.tau * param.data)


    def save(self, filename):
        torch.save(self.critic.state_dict(), filename + "_critic")
        torch.save(self.critic_optimizer.state_dict(), filename + "_critic_optimizer")
        
        torch.save(self.actor.state_dict(), filename + "_actor")
        torch.save(self.actor_optimizer.state_dict(), filename + "_actor_optimizer")


    def load(self, filename):
        self.critic.load_state_dict(torch.load(filename + "_critic"))
        self.critic_optimizer.load_state_dict(torch.load(filename + "_critic_optimizer"))
        self.critic_target = copy.deepcopy(self.critic)

        self.actor.load_state_dict(torch.load(filename + "_actor"))
        self.actor_optimizer.load_state_dict(torch.load(filename + "_actor_optimizer"))
        self.actor_target = copy.deepcopy(self.actor)
        