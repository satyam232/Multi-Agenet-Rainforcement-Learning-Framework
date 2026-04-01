/**
 * ControlPanel — Simulation controls (start, pause, reset, configure).
 */

import React, { useState } from 'react';

export default function ControlPanel({
    onStart,
    onStop,
    onTrain,
    onStopTraining,
    isRunning,
    isTraining,
}) {
    const [numAgents, setNumAgents] = useState(4);
    const [gridSize, setGridSize] = useState(6);
    const [trainEpisodes, setTrainEpisodes] = useState(50);

    return (
        <div className="glass-card p-5 space-y-5">
            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-neon-blue animate-pulse-neon" />
                <h2 className="text-lg font-bold text-white tracking-wide">Control Panel</h2>
            </div>

            {/* Simulation Controls */}
            <div className="space-y-3">
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Simulation
                </label>
                <div className="flex gap-2">
                    {!isRunning ? (
                        <button
                            onClick={() => onStart({ num_agents: numAgents, grid_size: gridSize })}
                            className="btn-neon btn-neon-green flex-1 flex items-center justify-center gap-2"
                            id="btn-start-simulation"
                        >
                            <span>▶</span> Start
                        </button>
                    ) : (
                        <button
                            onClick={onStop}
                            className="btn-neon btn-neon-pink flex-1 flex items-center justify-center gap-2"
                            id="btn-stop-simulation"
                        >
                            <span>■</span> Stop
                        </button>
                    )}
                </div>
            </div>

            {/* Configuration */}
            <div className="space-y-3">
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Configuration
                </label>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Agents</span>
                        <span className="text-sm font-mono text-neon-blue">{numAgents}</span>
                    </div>
                    <input
                        type="range"
                        min="2"
                        max="12"
                        value={numAgents}
                        onChange={(e) => setNumAgents(parseInt(e.target.value))}
                        className="w-full h-1.5 bg-dark-surface rounded-lg appearance-none cursor-pointer accent-neon-blue"
                        id="slider-num-agents"
                    />
                </div>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Grid Size</span>
                        <span className="text-sm font-mono text-neon-purple">{gridSize}×{gridSize}</span>
                    </div>
                    <input
                        type="range"
                        min="3"
                        max="10"
                        value={gridSize}
                        onChange={(e) => setGridSize(parseInt(e.target.value))}
                        className="w-full h-1.5 bg-dark-surface rounded-lg appearance-none cursor-pointer accent-neon-purple"
                        id="slider-grid-size"
                    />
                </div>
            </div>

            {/* Divider */}
            <div className="border-t border-dark-border" />

            {/* Training Controls */}
            <div className="space-y-3">
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Training
                </label>

                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-300">Episodes</span>
                        <span className="text-sm font-mono text-neon-green">{trainEpisodes}</span>
                    </div>
                    <input
                        type="range"
                        min="10"
                        max="500"
                        step="10"
                        value={trainEpisodes}
                        onChange={(e) => setTrainEpisodes(parseInt(e.target.value))}
                        className="w-full h-1.5 bg-dark-surface rounded-lg appearance-none cursor-pointer accent-neon-green"
                        id="slider-train-episodes"
                    />
                </div>

                <div className="flex gap-2">
                    {!isTraining ? (
                        <button
                            onClick={() => onTrain(trainEpisodes)}
                            className="btn-neon btn-neon-purple flex-1 flex items-center justify-center gap-2"
                            id="btn-train-agents"
                        >
                            <span>🧠</span> Train
                        </button>
                    ) : (
                        <button
                            onClick={onStopTraining}
                            className="btn-neon btn-neon-pink flex-1 flex items-center justify-center gap-2"
                            id="btn-stop-training"
                        >
                            <span className="spinner inline-block" /> Stop
                        </button>
                    )}
                </div>
            </div>

            {/* Status Indicator */}
            <div className="glass-card-sm p-3 space-y-2">
                <div className="flex items-center gap-2">
                    <div
                        className={`pulse-dot ${isRunning ? 'bg-neon-green text-neon-green' : 'bg-gray-500 text-gray-500'}`}
                    />
                    <span className="text-xs text-gray-400">
                        {isRunning ? 'Simulation Running' : isTraining ? 'Training in Progress' : 'Idle'}
                    </span>
                </div>
            </div>
        </div>
    );
}
