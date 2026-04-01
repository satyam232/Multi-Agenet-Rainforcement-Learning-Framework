"""
Training Pipeline
Runs training episodes, manages the environment-agent loop,
logs metrics, and saves model checkpoints.
"""

import os
import time
import json
import numpy as np

from environment.traffic_env import TrafficEnvironment
from agents.multi_agent_controller import MultiAgentController


class Trainer:
    """
    Manages the RL training loop.

    Training Flow:
        1. Reset environment
        2. For each step:
            a. Agents observe
            b. Agents choose actions
            c. Environment steps
            d. Agents store experiences
            e. Agents train on replay buffer
        3. Update target networks periodically
        4. Log metrics and save checkpoints
    """

    def __init__(self, env, controller, config=None):
        self.env = env
        self.controller = controller
        self.config = config or {}

        self.max_episodes = self.config.get('episodes', 100)
        self.target_update_freq = self.config.get('target_update_freq', 10)
        self.checkpoint_freq = self.config.get('checkpoint_freq', 50)
        self.checkpoint_dir = self.config.get('checkpoint_dir', 'models')

        self.training_history = []
        self.is_training = False
        self.current_episode = 0

    def train(self, episodes=None, callback=None):
        """
        Run training for the specified number of episodes.

        Args:
            episodes: Number of episodes to train (overrides config)
            callback: Optional function called after each episode with metrics dict
        """
        num_episodes = episodes or self.max_episodes
        self.is_training = True

        for episode in range(num_episodes):
            if not self.is_training:
                break

            self.current_episode = episode + 1
            episode_metrics = self._run_episode()

            # Update target networks
            if (episode + 1) % self.target_update_freq == 0:
                self.controller.update_targets()

            # Save checkpoints
            if (episode + 1) % self.checkpoint_freq == 0:
                self.controller.save_all(self.checkpoint_dir)

            self.training_history.append(episode_metrics)

            if callback:
                callback(episode_metrics)

        self.is_training = False
        self.controller.save_all(self.checkpoint_dir)
        return self.training_history

    def _run_episode(self):
        """Run a single training episode."""
        observations = self.env.reset()
        self.controller.reset_agent_rewards()

        episode_reward = 0.0
        episode_collisions = 0
        episode_destinations = 0
        losses = []
        step = 0

        while True:
            # Get actions
            actions = self.controller.get_actions(observations)

            # Step environment
            next_observations, rewards, dones, info = self.env.step(actions)

            # Store experiences
            self.controller.store_experiences(
                observations, actions, rewards, next_observations, dones
            )

            # Train agents
            loss = self.controller.train_all()
            losses.append(loss)

            episode_reward += sum(rewards.values())
            episode_collisions += len(info.get('collisions', []))
            episode_destinations += len(info.get('destinations', []))

            observations = next_observations
            step += 1

            # Check if all done
            if all(dones.values()):
                break

        # Record episode metrics
        self.controller.end_episode({
            'collisions': episode_collisions,
            'destinations': episode_destinations,
        })

        metrics = {
            'episode': self.current_episode,
            'total_reward': round(episode_reward, 2),
            'avg_reward': round(episode_reward / max(self.env.num_agents, 1), 2),
            'collisions': episode_collisions,
            'destinations_reached': episode_destinations,
            'steps': step,
            'avg_loss': round(float(np.mean(losses)) if losses else 0.0, 6),
            'avg_speed': round(float(self.env.metrics['avg_speed']), 2),
            'congestion': round(float(self.env.metrics['congestion']), 4),
            'epsilon': round(self.controller.agents[0].epsilon, 4) if self.controller.agents else 0,
        }

        return metrics

    def stop(self):
        """Stop training."""
        self.is_training = False

    def get_progress(self):
        """Get current training progress."""
        return {
            'is_training': self.is_training,
            'current_episode': self.current_episode,
            'total_episodes': self.max_episodes,
            'history': self.training_history[-50:],  # last 50 episodes
        }
