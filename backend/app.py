"""
Flask Backend Server
REST API + WebSocket for the Multi-Agent RL Traffic Simulation.

Endpoints:
    POST /start-simulation   - Start a new simulation
    POST /train-agents       - Start training agents
    POST /stop-training       - Stop training
    GET  /simulation-state   - Get current simulation state
    GET  /metrics            - Get training metrics
    POST /step-simulation    - Advance simulation by one step
    POST /configure          - Update simulation parameters

WebSocket:
    /live-traffic            - Real-time state broadcast
"""

import os
import json
import time
import threading
import numpy as np

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

from environment.traffic_env import TrafficEnvironment
from agents.multi_agent_controller import MultiAgentController
from training.trainer import Trainer

# ─── App Setup ────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ─── Global State ─────────────────────────────────────────────────────────────

simulation_config = {
    'grid_size': 6,
    'num_agents': 4,
    'road_spacing': 100.0,
    'max_steps': 1000,
}

rl_config = {
    'gamma': 0.95,
    'epsilon': 1.0,
    'epsilon_min': 0.01,
    'epsilon_decay': 0.995,
    'learning_rate': 0.001,
    'batch_size': 32,
    'buffer_size': 10000,
    'target_update_freq': 10,
}

env = None
controller = None
trainer = None
sim_running = False
sim_thread = None
train_thread = None


def _init_simulation():
    """Initialize environment and controller."""
    global env, controller, trainer
    env = TrafficEnvironment(
        grid_size=simulation_config['grid_size'],
        num_agents=simulation_config['num_agents'],
        road_spacing=simulation_config['road_spacing'],
        max_steps=simulation_config['max_steps'],
    )
    controller = MultiAgentController(
        num_agents=simulation_config['num_agents'],
        state_size=env.state_size,
        action_size=env.action_size,
        config=rl_config,
    )
    trainer = Trainer(env, controller, config={
        'episodes': 100,
        'target_update_freq': rl_config['target_update_freq'],
        'checkpoint_dir': 'models',
    })


# ─── REST Endpoints ──────────────────────────────────────────────────────────

@app.route('/start-simulation', methods=['POST'])
def start_simulation():
    """Start a new simulation (optionally with config overrides)."""
    global sim_running, sim_thread

    data = request.get_json(silent=True) or {}

    # Apply config overrides
    if 'num_agents' in data:
        simulation_config['num_agents'] = int(data['num_agents'])
    if 'grid_size' in data:
        simulation_config['grid_size'] = int(data['grid_size'])

    _init_simulation()
    observations = env.reset()

    # Start background simulation loop
    sim_running = True
    sim_thread = threading.Thread(target=_simulation_loop, daemon=True)
    sim_thread.start()

    return jsonify({
        'status': 'simulation_started',
        'config': simulation_config,
        'state': env.get_state_for_render(),
    })


@app.route('/stop-simulation', methods=['POST'])
def stop_simulation():
    """Stop the running simulation."""
    global sim_running
    sim_running = False
    return jsonify({'status': 'simulation_stopped'})


@app.route('/step-simulation', methods=['POST'])
def step_simulation():
    """Advance simulation by one step (manual mode)."""
    if env is None or controller is None:
        return jsonify({'error': 'No simulation running'}), 400

    observations = env._get_all_observations()
    actions = controller.get_actions(observations)
    next_obs, rewards, dones, info = env.step(actions)

    return jsonify({
        'state': env.get_state_for_render(),
        'rewards': {str(k): float(v) for k, v in rewards.items()},
        'dones': {str(k): v for k, v in dones.items()},
    })


@app.route('/train-agents', methods=['POST'])
def train_agents():
    """Start training agents in background."""
    global train_thread

    if env is None:
        _init_simulation()

    data = request.get_json(silent=True) or {}
    episodes = int(data.get('episodes', 50))

    def _train():
        trainer.config['episodes'] = episodes
        trainer.max_episodes = episodes

        def on_episode(metrics):
            socketio.emit('training_update', metrics, namespace='/live-traffic')

        trainer.train(episodes=episodes, callback=on_episode)

    train_thread = threading.Thread(target=_train, daemon=True)
    train_thread.start()

    return jsonify({
        'status': 'training_started',
        'episodes': episodes,
    })


@app.route('/stop-training', methods=['POST'])
def stop_training():
    """Stop ongoing training."""
    if trainer:
        trainer.stop()
    return jsonify({'status': 'training_stopped'})


@app.route('/simulation-state', methods=['GET'])
def simulation_state():
    """Get current simulation state."""
    if env is None:
        return jsonify({'error': 'No simulation running'}), 400
    return jsonify(env.get_state_for_render())


@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get training metrics."""
    result = {}
    if controller:
        result['controller'] = controller.get_metrics()
    if trainer:
        result['training'] = trainer.get_progress()
    return jsonify(result)


@app.route('/configure', methods=['POST'])
def configure():
    """Update simulation/RL configuration."""
    data = request.get_json(silent=True) or {}

    for key in ['grid_size', 'num_agents', 'road_spacing', 'max_steps']:
        if key in data:
            simulation_config[key] = data[key]

    for key in ['gamma', 'epsilon', 'epsilon_min', 'epsilon_decay',
                'learning_rate', 'batch_size', 'buffer_size']:
        if key in data:
            rl_config[key] = data[key]

    return jsonify({
        'status': 'configured',
        'simulation_config': simulation_config,
        'rl_config': rl_config,
    })


# ─── WebSocket Events ────────────────────────────────────────────────────────

@socketio.on('connect', namespace='/live-traffic')
def on_connect():
    print('[WS] Client connected to /live-traffic')
    if env:
        emit('simulation_state', env.get_state_for_render())


@socketio.on('disconnect', namespace='/live-traffic')
def on_disconnect():
    print('[WS] Client disconnected from /live-traffic')


@socketio.on('request_state', namespace='/live-traffic')
def on_request_state():
    if env:
        emit('simulation_state', env.get_state_for_render())


# ─── Background Simulation Loop ──────────────────────────────────────────────

def _simulation_loop():
    """Background loop that steps the simulation and emits state via WebSocket."""
    global sim_running

    observations = env._get_all_observations()

    while sim_running:
        # Use A*-based path-following: cars move along computed paths
        next_obs, rewards, dones, info = env.step_with_pathfinding()

        # Collect RL agent actions for training (stored as experiences)
        rl_actions = controller.get_actions(observations)
        controller.store_experiences(observations, rl_actions, rewards, next_obs, dones)

        observations = next_obs

        # Broadcast state
        state = env.get_state_for_render()
        state['rewards'] = {str(k): float(v) for k, v in rewards.items()}
        socketio.emit('simulation_state', state, namespace='/live-traffic')

        # Reset if episode done
        if all(dones.values()):
            observations = env.reset()
            controller.reset_agent_rewards()

        time.sleep(0.1)  # ~10 FPS


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=" * 60)
    print("  MARL Traffic Simulation Backend")
    print("  Multi-Agent Reinforcement Learning Framework")
    print("=" * 60)
    print(f"  Grid: {simulation_config['grid_size']}x{simulation_config['grid_size']}")
    print(f"  Agents: {simulation_config['num_agents']}")
    print("=" * 60)
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)
