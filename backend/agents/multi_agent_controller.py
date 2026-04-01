"""
Multi-Agent Controller
Manages a pool of DQN agents with decentralized learning.
Each agent learns independently but shares the environment state.
"""

from agents.dqn_agent import DQNAgent


class MultiAgentController:
    """
    Controller that manages N independent DQN agents.

    Responsibilities:
        - Create and manage agent pool
        - Distribute observations and collect actions
        - Orchestrate per-agent experience storage and training
        - Track per-agent and aggregate metrics
    """

    def __init__(self, num_agents, state_size=8, action_size=6, config=None):
        self.num_agents = num_agents
        self.state_size = state_size
        self.action_size = action_size
        self.config = config or {}

        self.agents = {}
        for i in range(num_agents):
            self.agents[i] = DQNAgent(
                agent_id=i,
                state_size=state_size,
                action_size=action_size,
                config=self.config
            )

        self.episode_count = 0
        self.total_collisions = 0
        self.total_destinations = 0
        self.episode_rewards = []

    def get_actions(self, observations):
        """
        Get actions for all agents given their observations.
        observations: dict {agent_id: state_array}
        Returns: dict {agent_id: action_int}
        """
        actions = {}
        for agent_id, obs in observations.items():
            if agent_id in self.agents:
                actions[agent_id] = self.agents[agent_id].act(obs)
            else:
                actions[agent_id] = 4  # maintain speed
        return actions

    def store_experiences(self, observations, actions, rewards, next_observations, dones):
        """Store transitions for all agents."""
        for agent_id in observations:
            if agent_id in self.agents:
                self.agents[agent_id].remember(
                    observations[agent_id],
                    actions.get(agent_id, 4),
                    rewards.get(agent_id, 0.0),
                    next_observations.get(agent_id, observations[agent_id]),
                    dones.get(agent_id, False)
                )

    def train_all(self):
        """Train all agents on their replay buffers. Returns average loss."""
        total_loss = 0.0
        count = 0
        for agent in self.agents.values():
            loss = agent.replay()
            total_loss += loss
            count += 1
        return total_loss / count if count > 0 else 0.0

    def update_targets(self):
        """Update target networks for all agents."""
        for agent in self.agents.values():
            agent.update_target_network()

    def end_episode(self, info):
        """Record episode-level metrics."""
        self.episode_count += 1
        self.total_collisions += info.get('collisions', 0)
        self.total_destinations += info.get('destinations', 0)
        total_reward = sum(a.total_reward for a in self.agents.values())
        self.episode_rewards.append(total_reward)

    def reset_agent_rewards(self):
        """Reset per-episode reward tracking for all agents."""
        for agent in self.agents.values():
            agent.total_reward = 0.0

    def resize(self, new_num_agents):
        """Add or remove agents to match the new count."""
        if new_num_agents > self.num_agents:
            for i in range(self.num_agents, new_num_agents):
                self.agents[i] = DQNAgent(
                    agent_id=i,
                    state_size=self.state_size,
                    action_size=self.action_size,
                    config=self.config
                )
        elif new_num_agents < self.num_agents:
            for i in range(new_num_agents, self.num_agents):
                if i in self.agents:
                    del self.agents[i]
        self.num_agents = new_num_agents

    def get_metrics(self):
        """Get aggregate metrics for API/frontend."""
        return {
            'episode_count': self.episode_count,
            'total_collisions': self.total_collisions,
            'total_destinations': self.total_destinations,
            'episode_rewards': self.episode_rewards[-100:],  # last 100
            'agents': [a.get_info() for a in self.agents.values()],
        }

    def save_all(self, directory):
        """Save all agent models."""
        import os
        os.makedirs(directory, exist_ok=True)
        for agent_id, agent in self.agents.items():
            agent.save(os.path.join(directory, f'agent_{agent_id}.weights.h5'))

    def load_all(self, directory):
        """Load all agent models."""
        import os
        for agent_id, agent in self.agents.items():
            path = os.path.join(directory, f'agent_{agent_id}.weights.h5')
            if os.path.exists(path):
                agent.load(path)
