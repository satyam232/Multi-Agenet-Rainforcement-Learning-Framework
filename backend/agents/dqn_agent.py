"""
Deep Q-Network (DQN) Agent using TensorFlow/Keras.
Implements experience replay, target network, and epsilon-greedy exploration.
"""

import numpy as np
import random
from collections import deque

# Use environment variable to suppress TF warnings
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


class ReplayBuffer:
    """Experience replay buffer for DQN training."""

    def __init__(self, capacity=10000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size):
        batch = random.sample(self.buffer, min(len(self.buffer), batch_size))
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states, dtype=np.float32),
            np.array(actions, dtype=np.int32),
            np.array(rewards, dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones, dtype=np.float32),
        )

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    """
    Deep Q-Network agent for multi-agent traffic RL.

    Architecture:
        Input(state_size) → Dense(128, relu) → Dense(128, relu) → Dense(64, relu) → Dense(action_size, linear)

    Features:
        - Experience replay with configurable buffer
        - Target network with periodic hard sync
        - Epsilon-greedy with linear decay
    """

    def __init__(self, agent_id, state_size=14, action_size=6, config=None):
        self.agent_id = agent_id
        self.state_size = state_size
        self.action_size = action_size

        # Defaults
        cfg = config or {}
        self.gamma = cfg.get('gamma', 0.95)
        self.epsilon = cfg.get('epsilon', 1.0)
        self.epsilon_min = cfg.get('epsilon_min', 0.01)
        self.epsilon_decay = cfg.get('epsilon_decay', 0.995)
        self.learning_rate = cfg.get('learning_rate', 0.001)
        self.batch_size = cfg.get('batch_size', 32)
        self.target_update_freq = cfg.get('target_update_freq', 10)

        self.replay_buffer = ReplayBuffer(capacity=cfg.get('buffer_size', 10000))

        # Build networks
        self.q_network = self._build_network()
        self.target_network = self._build_network()
        self.update_target_network()

        self.train_step_counter = 0
        self.total_reward = 0.0

    def _build_network(self):
        """Build the Q-network."""
        model = keras.Sequential([
            layers.Input(shape=(self.state_size,)),
            layers.Dense(128, activation='relu', kernel_initializer='he_uniform'),
            layers.Dense(128, activation='relu', kernel_initializer='he_uniform'),
            layers.Dense(64, activation='relu', kernel_initializer='he_uniform'),
            layers.Dense(self.action_size, activation='linear'),
        ])
        model.compile(
            optimizer=keras.optimizers.legacy.Adam(learning_rate=self.learning_rate),
            loss='huber'
        )
        return model

    def act(self, state):
        """Select action using epsilon-greedy policy."""
        if np.random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)
        state = np.reshape(state, [1, self.state_size])
        q_values = self.q_network.predict(state, verbose=0)[0]
        return int(np.argmax(q_values))

    def get_q_values(self, state):
        """Get Q-values for all actions given a state."""
        state = np.reshape(state, [1, self.state_size])
        return self.q_network.predict(state, verbose=0)[0].tolist()

    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay buffer."""
        self.replay_buffer.push(state, action, reward, next_state, done)
        self.total_reward += reward

    def replay(self):
        """Train on a mini-batch from replay buffer."""
        if len(self.replay_buffer) < self.batch_size:
            return 0.0

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(self.batch_size)

        # Compute target Q values
        target_q = self.target_network.predict(next_states, verbose=0)
        max_target_q = np.max(target_q, axis=1)

        targets = self.q_network.predict(states, verbose=0)
        for i in range(len(actions)):
            if dones[i]:
                targets[i][actions[i]] = rewards[i]
            else:
                targets[i][actions[i]] = rewards[i] + self.gamma * max_target_q[i]

        history = self.q_network.fit(states, targets, epochs=1, verbose=0, batch_size=self.batch_size)
        loss = history.history['loss'][0]

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        self.train_step_counter += 1
        return loss

    def update_target_network(self):
        """Hard-copy weights from Q-network to target network."""
        self.target_network.set_weights(self.q_network.get_weights())

    def save(self, filepath):
        """Save Q-network weights."""
        self.q_network.save_weights(filepath)

    def load(self, filepath):
        """Load Q-network weights."""
        self.q_network.load_weights(filepath)
        self.update_target_network()

    def get_info(self):
        """Get agent info dict for API/frontend."""
        return {
            'agent_id': self.agent_id,
            'epsilon': round(self.epsilon, 4),
            'total_reward': round(self.total_reward, 2),
            'buffer_size': len(self.replay_buffer),
            'train_steps': self.train_step_counter,
        }
