/**
 * App.jsx — Main application layout for MARL Traffic Simulation Dashboard.
 * Three-column layout: Controls | Simulation Canvas | Metrics + Agent Info
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import SimulationCanvas from './components/SimulationCanvas';
import ControlPanel from './components/ControlPanel';
import MetricsPanel from './components/MetricsPanel';
import AgentInfo from './components/AgentInfo';
import { startSimulation, stopSimulation, trainAgents, stopTraining, getMetrics } from './services/api';
import { connectSocket, disconnectSocket } from './services/socket';

export default function App() {
    const [simState, setSimState] = useState(null);
    const [isRunning, setIsRunning] = useState(false);
    const [isTraining, setIsTraining] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState(null);
    const [trainingHistory, setTrainingHistory] = useState([]);
    const [currentMetrics, setCurrentMetrics] = useState({});
    const [agentMetrics, setAgentMetrics] = useState([]);
    const metricsInterval = useRef(null);

    // Socket connection
    useEffect(() => {
        const socket = connectSocket(
            // On simulation state
            (data) => {
                setSimState(data);
                if (data.metrics) {
                    setCurrentMetrics(data.metrics);
                }
            },
            // On training update
            (data) => {
                setTrainingHistory((prev) => [...prev, data]);
            }
        );

        return () => {
            disconnectSocket();
            if (metricsInterval.current) clearInterval(metricsInterval.current);
        };
    }, []);

    // Poll metrics periodically when training
    useEffect(() => {
        if (isTraining) {
            metricsInterval.current = setInterval(async () => {
                try {
                    const data = await getMetrics();
                    if (data.controller?.agents) {
                        setAgentMetrics(data.controller.agents);
                    }
                } catch (e) { /* ignore */ }
            }, 3000);
        } else {
            if (metricsInterval.current) {
                clearInterval(metricsInterval.current);
                metricsInterval.current = null;
            }
        }
        return () => {
            if (metricsInterval.current) clearInterval(metricsInterval.current);
        };
    }, [isTraining]);

    const handleStart = useCallback(async (config) => {
        try {
            const res = await startSimulation(config);
            if (res.state) setSimState(res.state);
            setIsRunning(true);
            setSelectedAgent(null);
        } catch (e) {
            console.error('Failed to start simulation:', e);
        }
    }, []);

    const handleStop = useCallback(async () => {
        try {
            await stopSimulation();
            setIsRunning(false);
        } catch (e) {
            console.error('Failed to stop simulation:', e);
        }
    }, []);

    const handleTrain = useCallback(async (episodes) => {
        try {
            setTrainingHistory([]);
            setIsTraining(true);
            await trainAgents(episodes);
        } catch (e) {
            console.error('Failed to start training:', e);
            setIsTraining(false);
        }
    }, []);

    const handleStopTraining = useCallback(async () => {
        try {
            await stopTraining();
            setIsTraining(false);
        } catch (e) {
            console.error('Failed to stop training:', e);
        }
    }, []);

    return (
        <div className="min-h-screen bg-dark-bg grid-bg">
            {/* Header */}
            <header className="border-b border-dark-border bg-dark-bg/80 backdrop-blur-lg sticky top-0 z-50">
                <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-blue to-neon-purple flex items-center justify-center text-sm font-bold">
                                🚗
                            </div>
                            <div>
                                <h1 className="text-lg font-bold text-white leading-tight">
                                    MARL Traffic Simulation
                                </h1>
                                <p className="text-[10px] text-gray-500 font-mono tracking-wider">
                                    MULTI-AGENT REINFORCEMENT LEARNING
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="hidden md:flex items-center gap-2 text-xs text-gray-500">
                            <span className="px-2 py-1 rounded bg-dark-surface font-mono">DQN</span>
                            <span className="px-2 py-1 rounded bg-dark-surface font-mono">TensorFlow</span>
                            <span className="px-2 py-1 rounded bg-dark-surface font-mono">Flask</span>
                        </div>
                        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold ${isRunning
                            ? 'bg-neon-green/10 text-neon-green border border-neon-green/20'
                            : isTraining
                                ? 'bg-neon-purple/10 text-neon-purple border border-neon-purple/20'
                                : 'bg-gray-800 text-gray-400 border border-gray-700'
                            }`}>
                            <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-neon-green animate-pulse' : isTraining ? 'bg-neon-purple animate-pulse' : 'bg-gray-500'
                                }`} />
                            {isRunning ? 'LIVE' : isTraining ? 'TRAINING' : 'IDLE'}
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-[1600px] mx-auto px-6 py-6">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    {/* Left: Controls + Agent Info */}
                    <div className="lg:col-span-3 space-y-5">
                        <ControlPanel
                            onStart={handleStart}
                            onStop={handleStop}
                            onTrain={handleTrain}
                            onStopTraining={handleStopTraining}
                            isRunning={isRunning}
                            isTraining={isTraining}
                        />
                        <AgentInfo
                            state={simState}
                            selectedAgent={selectedAgent}
                            agentMetrics={agentMetrics}
                        />
                    </div>

                    {/* Center: Simulation Canvas */}
                    <div className="lg:col-span-5 flex flex-col items-center">
                        <div className="w-full">
                            <div className="glass-card p-4">
                                <div className="flex items-center justify-between mb-3">
                                    <h2 className="text-sm font-semibold text-gray-300 flex items-center gap-2">
                                        <span className="w-2 h-2 rounded-full bg-neon-blue" />
                                        Traffic Simulation
                                    </h2>
                                    {simState && (
                                        <span className="text-xs font-mono text-gray-500">
                                            Step {simState.step} | Grid {simState.grid_size}×{simState.grid_size}
                                        </span>
                                    )}
                                </div>
                                <SimulationCanvas
                                    state={simState}
                                    selectedAgent={selectedAgent}
                                    onSelectAgent={setSelectedAgent}
                                />
                                {/* Mini legend  */}
                                <div className="flex items-center gap-4 mt-3 text-[10px] text-gray-500">
                                    <span className="flex items-center gap-1">
                                        <span className="w-2 h-2 rounded-full bg-neon-green" /> Green Signal
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <span className="w-2 h-2 rounded-full bg-neon-pink" /> Red Signal
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <span className="w-3 h-2 rounded bg-neon-blue" /> Car
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <span className="w-2 h-2 rounded bg-neon-pink/30" /> Congestion
                                    </span>
                                    <span className="flex items-center gap-1">
                                        <span className="text-[10px]">🧑</span> Person
                                    </span>
                                </div>
                            </div>
                        </div>

                        {/* Welcome overlay when no simulation */}
                        {!simState && (
                            <div className="glass-card p-8 mt-4 text-center animate-slide-up w-full">
                                <div className="text-4xl mb-4">🚦</div>
                                <h2 className="text-xl font-bold text-white mb-2">
                                    Welcome to MARL Traffic Simulation
                                </h2>
                                <p className="text-sm text-gray-400 max-w-md mx-auto mb-4">
                                    Multi-Agent Reinforcement Learning framework for distributed autonomous
                                    decision making in dynamic traffic environments.
                                </p>
                                <div className="flex flex-wrap justify-center gap-2 text-xs text-gray-500">
                                    <span className="px-3 py-1.5 rounded-full bg-dark-surface border border-dark-border">
                                        🧠 Deep Q-Network
                                    </span>
                                    <span className="px-3 py-1.5 rounded-full bg-dark-surface border border-dark-border">
                                        🚗 Multi-Agent RL
                                    </span>
                                    <span className="px-3 py-1.5 rounded-full bg-dark-surface border border-dark-border">
                                        📊 Real-time Viz
                                    </span>
                                </div>
                                <p className="text-xs text-gray-600 mt-4">
                                    Click <strong>Start</strong> in the Control Panel to begin. →
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Right: Metrics */}
                    <div className="lg:col-span-4">
                        <MetricsPanel
                            trainingHistory={trainingHistory}
                            currentMetrics={currentMetrics}
                        />
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-dark-border mt-8 py-4">
                <div className="max-w-[1600px] mx-auto px-6 flex items-center justify-between text-xs text-gray-600">
                    <span>MARL Traffic Framework — Research Project</span>
                    <span className="font-mono">DQN • TensorFlow • Flask • React</span>
                </div>
            </footer>
        </div>
    );
}
