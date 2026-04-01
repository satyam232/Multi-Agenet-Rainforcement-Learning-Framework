/**
 * REST API client for the Flask backend.
 */

const API_BASE = 'http://localhost:5001';

export async function startSimulation(config = {}) {
    const res = await fetch(`${API_BASE}/start-simulation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    });
    return res.json();
}

export async function stopSimulation() {
    const res = await fetch(`${API_BASE}/stop-simulation`, { method: 'POST' });
    return res.json();
}

export async function trainAgents(episodes = 50) {
    const res = await fetch(`${API_BASE}/train-agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ episodes }),
    });
    return res.json();
}

export async function stopTraining() {
    const res = await fetch(`${API_BASE}/stop-training`, { method: 'POST' });
    return res.json();
}

export async function getSimulationState() {
    const res = await fetch(`${API_BASE}/simulation-state`);
    return res.json();
}

export async function getMetrics() {
    const res = await fetch(`${API_BASE}/metrics`);
    return res.json();
}

export async function configure(config) {
    const res = await fetch(`${API_BASE}/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    });
    return res.json();
}
