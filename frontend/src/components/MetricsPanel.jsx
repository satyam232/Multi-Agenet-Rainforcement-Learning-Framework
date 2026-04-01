/**
 * MetricsPanel — Training metrics visualization using Recharts.
 * Displays reward graphs, collision rate, congestion, and per-agent stats.
 */

import React from 'react';
import {
    LineChart, Line, AreaChart, Area, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;
    return (
        <div className="glass-card-sm p-3 text-xs">
            <p className="text-gray-400 mb-1">Episode {label}</p>
            {payload.map((entry, i) => (
                <p key={i} style={{ color: entry.color }}>
                    {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
                </p>
            ))}
        </div>
    );
};

export default function MetricsPanel({ trainingHistory, currentMetrics }) {
    const rewardData = (trainingHistory || []).map((ep) => ({
        episode: ep.episode,
        reward: ep.total_reward,
        avgReward: ep.avg_reward,
    }));

    const lossData = (trainingHistory || []).map((ep) => ({
        episode: ep.episode,
        loss: ep.avg_loss,
        epsilon: ep.epsilon,
    }));

    const performanceData = (trainingHistory || []).map((ep) => ({
        episode: ep.episode,
        collisions: ep.collisions,
        destinations: ep.destinations_reached,
        congestion: ep.congestion * 100,
    }));

    return (
        <div className="space-y-4">
            {/* Summary Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <StatCard
                    label="Total Reward"
                    value={currentMetrics?.total_reward?.toFixed(1) || '0'}
                    color="text-neon-blue"
                    icon="💰"
                />
                <StatCard
                    label="Collisions"
                    value={currentMetrics?.collisions || 0}
                    color="text-neon-pink"
                    icon="💥"
                />
                <StatCard
                    label="Pickups"
                    value={currentMetrics?.persons_picked_up || currentMetrics?.destinations_reached || 0}
                    color="text-neon-green"
                    icon="🧑"
                />
                <StatCard
                    label="Congestion"
                    value={((currentMetrics?.congestion || 0) * 100).toFixed(1) + '%'}
                    color="text-neon-purple"
                    icon="🚦"
                />
            </div>

            {/* Reward Chart */}
            {rewardData.length > 0 && (
                <div className="glass-card p-4">
                    <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-neon-blue" />
                        Reward Over Episodes
                    </h3>
                    <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={rewardData}>
                            <defs>
                                <linearGradient id="rewardGrad" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.4} />
                                    <stop offset="100%" stopColor="#00d4ff" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="episode" stroke="#475569" fontSize={10} />
                            <YAxis stroke="#475569" fontSize={10} />
                            <Tooltip content={<CustomTooltip />} />
                            <Area
                                type="monotone"
                                dataKey="reward"
                                stroke="#00d4ff"
                                fill="url(#rewardGrad)"
                                strokeWidth={2}
                                name="Total Reward"
                            />
                            <Line
                                type="monotone"
                                dataKey="avgReward"
                                stroke="#a855f7"
                                strokeWidth={1.5}
                                dot={false}
                                name="Avg Reward"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Performance Chart */}
            {performanceData.length > 0 && (
                <div className="glass-card p-4">
                    <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-neon-green" />
                        Performance Metrics
                    </h3>
                    <ResponsiveContainer width="100%" height={180}>
                        <BarChart data={performanceData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="episode" stroke="#475569" fontSize={10} />
                            <YAxis stroke="#475569" fontSize={10} />
                            <Tooltip content={<CustomTooltip />} />
                            <Bar dataKey="collisions" fill="#f43f5e" name="Collisions" radius={[2, 2, 0, 0]} />
                            <Bar dataKey="destinations" fill="#00ff88" name="Destinations" radius={[2, 2, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Loss & Epsilon Chart */}
            {lossData.length > 0 && (
                <div className="glass-card p-4">
                    <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-neon-purple" />
                        Training Loss & Exploration
                    </h3>
                    <ResponsiveContainer width="100%" height={160}>
                        <LineChart data={lossData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                            <XAxis dataKey="episode" stroke="#475569" fontSize={10} />
                            <YAxis yAxisId="left" stroke="#475569" fontSize={10} />
                            <YAxis yAxisId="right" orientation="right" stroke="#475569" fontSize={10} />
                            <Tooltip content={<CustomTooltip />} />
                            <Line yAxisId="left" type="monotone" dataKey="loss" stroke="#facc15" strokeWidth={1.5} dot={false} name="Loss" />
                            <Line yAxisId="right" type="monotone" dataKey="epsilon" stroke="#a855f7" strokeWidth={1.5} dot={false} name="Epsilon" />
                            <Legend wrapperStyle={{ fontSize: 10, color: '#94a3b8' }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}

function StatCard({ label, value, color, icon }) {
    return (
        <div className="stat-card flex items-center gap-3">
            <span className="text-xl">{icon}</span>
            <div>
                <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
                <div className="text-xs text-gray-500">{label}</div>
            </div>
        </div>
    );
}
