/**
 * Socket.IO client for real-time traffic state updates.
 */

import { io } from 'socket.io-client';

const SOCKET_URL = 'http://localhost:5001/live-traffic';

let socket = null;

export function connectSocket(onState, onTraining) {
    if (socket && socket.connected) return socket;

    socket = io(SOCKET_URL, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionAttempts: 10,
    });

    socket.on('connect', () => {
        console.log('[Socket] Connected to /live-traffic');
    });

    socket.on('disconnect', () => {
        console.log('[Socket] Disconnected');
    });

    socket.on('simulation_state', (data) => {
        if (onState) onState(data);
    });

    socket.on('training_update', (data) => {
        if (onTraining) onTraining(data);
    });

    socket.on('connect_error', (err) => {
        console.warn('[Socket] Connection error:', err.message);
    });

    return socket;
}

export function disconnectSocket() {
    if (socket) {
        socket.disconnect();
        socket = null;
    }
}

export function requestState() {
    if (socket && socket.connected) {
        socket.emit('request_state');
    }
}
