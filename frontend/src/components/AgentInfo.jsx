/**
 * AgentInfo — Live agent state display.
 * Shows selected car's position, velocity, action, reward, and Q-values.
 */

import React from 'react';

const ACTION_NAMES = ['Accelerate', 'Decelerate', 'Turn Left', 'Turn Right', 'Maintain', 'Stop'];
const ACTION_ICONS = ['⬆️', '⬇️', '⬅️', '➡️', '➖', '🛑'];

export default function AgentInfo({ state, selectedAgent, agentMetrics }) {
    if (selectedAgent === null || selectedAgent === undefined || !state || !state.cars) {
        return (
            <div className="glass-card p-5">
                <div className="flex items-center gap-3 mb-3">
                    <div className="w-3 h-3 rounded-full bg-neon-purple animate-glow" />
                    <h2 className="text-lg font-bold text-white tracking-wide">Agent Inspector</h2>
                </div>
                <p className="text-gray-500 text-sm text-center py-8">
                    Click on a car in the simulation to inspect its state
                </p>
            </div>
        );
    }

    const car = state.cars.find(c => c.id === selectedAgent);
    if (!car) return null; 

    const agentInfo = agentMetrics?.find(a => a.agent_id === selectedAgent);

    return (
        <div className="glass-card p-5 space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full bg-neon-purple animate-glow" />
                    <h2 className="text-lg font-bold text-white tracking-wide">Agent {car.id}</h2>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${car.alive
                        ? car.reached_destination
                            ? 'bg-neon-green/20 text-neon-green'
                            : 'bg-neon-blue/20 text-neon-blue'
                        : 'bg-neon-pink/20 text-neon-pink'
                    }`}>
                    {car.alive ? (car.reached_destination ? 'ARRIVED' : 'ACTIVE') : 'CRASHED'}
                </span>
            </div>

            {/* Position & Velocity */}
            <div className="grid grid-cols-2 gap-3">
                <InfoBlock label="Position" value={`(${car.x.toFixed(1)}, ${car.y.toFixed(1)})`} />
                <InfoBlock label="Velocity" value={`(${car.vx.toFixed(1)}, ${car.vy.toFixed(1)})`} />
                <InfoBlock label="Speed" value={car.speed.toFixed(2)} />
                <InfoBlock label="Lane" value={car.lane} />
            </div>

            {/* Destination */}
            <div className="glass-card-sm p-3">
                <div className="text-xs text-gray-500 mb-1">Destination</div>
                <div className="text-sm font-mono text-neon-green">
                    ({car.dest_x.toFixed(1)}, {car.dest_y.toFixed(1)})
                </div>
                <div className="text-xs text-gray-500 mt-1">
                    Distance: {Math.sqrt((car.x - car.dest_x) ** 2 + (car.y - car.dest_y) ** 2).toFixed(1)}
                </div>
            </div>

            {/* Agent Training Stats */}
            {agentInfo && (
                <>
                    <div className="border-t border-dark-border" />
                    <div className="space-y-2">
                        <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                            Learning Stats
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                            <InfoBlock label="Epsilon" value={agentInfo.epsilon?.toFixed(4)} />
                            <InfoBlock label="Buffer" value={agentInfo.buffer_size} />
                            <InfoBlock label="Train Steps" value={agentInfo.train_steps} />
                            <InfoBlock label="Total Reward" value={agentInfo.total_reward?.toFixed(1)} />
                        </div>
                    </div>
                </>
            )}

            {/* Reward if in live simulation */}
            {state.rewards && state.rewards[selectedAgent] !== undefined && (
                <div className="glass-card-sm p-3">
                    <div className="text-xs text-gray-500 mb-1">Current Reward</div>
                    <div className={`text-xl font-bold font-mono ${state.rewards[selectedAgent] > 0 ? 'text-neon-green' : 'text-neon-pink'
                        }`}>
                        {state.rewards[selectedAgent].toFixed(2)}
                    </div>
                </div>
            )}
        </div>
    );
}

function InfoBlock({ label, value }) {
    return (
        <div className="glass-card-sm p-2.5">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</div>
            <div className="text-sm font-mono text-white mt-0.5">{value}</div>
        </div>
    );
}
