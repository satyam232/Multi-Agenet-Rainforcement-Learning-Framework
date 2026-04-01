/**
 * SimulationCanvas — HTML5 Canvas renderer for the traffic simulation.
 * Draws road grid, traffic signals, cars, persons/passengers, and congestion heatmap.
 */

import React, { useRef, useEffect, useCallback } from 'react';

// Car colors for different agents
const CAR_COLORS = [
    '#00d4ff', '#00ff88', '#a855f7', '#f43f5e',
    '#facc15', '#fb923c', '#34d399', '#818cf8',
    '#f472b6', '#38bdf8', '#4ade80', '#c084fc',
];

export default function SimulationCanvas({ state, selectedAgent, onSelectAgent }) {
    const canvasRef = useRef(null);
    const animRef = useRef(null);
    const prevCarsRef = useRef({});

    const CANVAS_SIZE = 600;
    const PADDING = 40;

    const draw = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas || !state) return;

        const ctx = canvas.getContext('2d');
        const { cars, signals, persons, pickup_events, grid_size, road_spacing } = state;

        const scale = (CANVAS_SIZE - 2 * PADDING) / ((grid_size - 1) * road_spacing);

        const toCanvas = (x, y) => [
            PADDING + x * scale,
            PADDING + y * scale,
        ];

        // Clear
        ctx.fillStyle = '#0a0e1a';
        ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

        // Draw grid background glow
        const grd = ctx.createRadialGradient(CANVAS_SIZE / 2, CANVAS_SIZE / 2, 50, CANVAS_SIZE / 2, CANVAS_SIZE / 2, CANVAS_SIZE / 2);
        grd.addColorStop(0, 'rgba(0, 212, 255, 0.03)');
        grd.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = grd;
        ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

        // Draw roads (horizontal and vertical lines)
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
        const roadWidth = 28;

        for (let i = 0; i < grid_size; i++) {
            const y = PADDING + i * road_spacing * scale;
            ctx.lineWidth = roadWidth;
            ctx.beginPath();
            ctx.moveTo(PADDING - 10, y);
            ctx.lineTo(CANVAS_SIZE - PADDING + 10, y);
            ctx.stroke();
        }
        for (let i = 0; i < grid_size; i++) {
            const x = PADDING + i * road_spacing * scale;
            ctx.lineWidth = roadWidth;
            ctx.beginPath();
            ctx.moveTo(x, PADDING - 10);
            ctx.lineTo(x, CANVAS_SIZE - PADDING + 10);
            ctx.stroke();
        }

        // Draw lane markings (dashed)
        ctx.setLineDash([6, 8]);
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        ctx.lineWidth = 1;

        for (let i = 0; i < grid_size; i++) {
            const y = PADDING + i * road_spacing * scale;
            ctx.beginPath();
            ctx.moveTo(PADDING, y);
            ctx.lineTo(CANVAS_SIZE - PADDING, y);
            ctx.stroke();
        }
        for (let i = 0; i < grid_size; i++) {
            const x = PADDING + i * road_spacing * scale;
            ctx.beginPath();
            ctx.moveTo(x, PADDING);
            ctx.lineTo(x, CANVAS_SIZE - PADDING);
            ctx.stroke();
        }
        ctx.setLineDash([]);

        // Draw congestion heatmap overlay
        if (cars && cars.length > 1) {
            const heatmapRes = 20;
            const cellSize = CANVAS_SIZE / heatmapRes;
            for (let gx = 0; gx < heatmapRes; gx++) {
                for (let gy = 0; gy < heatmapRes; gy++) {
                    const cx = (gx + 0.5) * cellSize;
                    const cy = (gy + 0.5) * cellSize;
                    let density = 0;
                    cars.forEach((c) => {
                        if (!c.alive) return;
                        const [px, py] = toCanvas(c.x, c.y);
                        const dist = Math.sqrt((px - cx) ** 2 + (py - cy) ** 2);
                        if (dist < 80) density += 1 / (dist + 10);
                    });
                    if (density > 0.02) {
                        const alpha = Math.min(density * 3, 0.35);
                        ctx.fillStyle = `rgba(244, 63, 94, ${alpha})`;
                        ctx.fillRect(gx * cellSize, gy * cellSize, cellSize, cellSize);
                    }
                }
            }
        }

        // Draw traffic signals
        if (signals) {
            signals.forEach((sig) => {
                const [sx, sy] = toCanvas(sig.x, sig.y);
                // Glow
                const sigGlow = ctx.createRadialGradient(sx, sy, 0, sx, sy, 18);
                const sigColor = sig.state === 0 ? '0, 255, 136' : '244, 63, 94';
                sigGlow.addColorStop(0, `rgba(${sigColor}, 0.4)`);
                sigGlow.addColorStop(1, `rgba(${sigColor}, 0)`);
                ctx.fillStyle = sigGlow;
                ctx.fillRect(sx - 18, sy - 18, 36, 36);

                // Signal dot
                ctx.beginPath();
                ctx.arc(sx, sy, 5, 0, Math.PI * 2);
                ctx.fillStyle = sig.state === 0 ? '#00ff88' : '#f43f5e';
                ctx.fill();
                ctx.strokeStyle = sig.state === 0 ? 'rgba(0, 255, 136, 0.6)' : 'rgba(244, 63, 94, 0.6)';
                ctx.lineWidth = 2;
                ctx.stroke();
            });
        }

        // ─── Draw Persons (Passengers) ──────────────────────────────────
        if (persons && persons.length > 0) {
            persons.forEach((person) => {
                if (person.picked_up) return;
                const [px, py] = toCanvas(person.x, person.y);

                // Pulsing glow ring behind the person
                const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 400 + person.id);
                const glowRadius = 14 + pulse * 4;
                const personGlow = ctx.createRadialGradient(px, py, 0, px, py, glowRadius);
                personGlow.addColorStop(0, `rgba(250, 204, 21, ${0.3 + pulse * 0.2})`);
                personGlow.addColorStop(1, 'rgba(250, 204, 21, 0)');
                ctx.fillStyle = personGlow;
                ctx.beginPath();
                ctx.arc(px, py, glowRadius, 0, Math.PI * 2);
                ctx.fill();

                // Draw person icon (stick figure)
                const assignedCar = person.assigned_car_id;
                const color = assignedCar !== null && assignedCar !== undefined
                    ? CAR_COLORS[assignedCar % CAR_COLORS.length]
                    : '#facc15';

                // Head
                ctx.beginPath();
                ctx.arc(px, py - 8, 4, 0, Math.PI * 2);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.strokeStyle = 'rgba(0,0,0,0.4)';
                ctx.lineWidth = 1;
                ctx.stroke();

                // Body
                ctx.beginPath();
                ctx.moveTo(px, py - 4);
                ctx.lineTo(px, py + 3);
                ctx.strokeStyle = color;
                ctx.lineWidth = 2;
                ctx.stroke();

                // Arms (waving)
                const wave = Math.sin(Date.now() / 300 + person.id * 2) * 0.3;
                ctx.beginPath();
                ctx.moveTo(px - 5, py - 2 + wave * 3);
                ctx.lineTo(px, py - 1);
                ctx.lineTo(px + 5, py - 2 - wave * 3);
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.5;
                ctx.stroke();

                // Legs
                ctx.beginPath();
                ctx.moveTo(px, py + 3);
                ctx.lineTo(px - 4, py + 9);
                ctx.moveTo(px, py + 3);
                ctx.lineTo(px + 4, py + 9);
                ctx.strokeStyle = color;
                ctx.lineWidth = 1.5;
                ctx.stroke();

                // Person ID label
                ctx.font = 'bold 8px JetBrains Mono';
                ctx.fillStyle = '#facc15';
                ctx.textAlign = 'center';
                ctx.fillText(`P${person.id}`, px, py + 18);

                // Draw assignment line from person to their assigned car
                if (assignedCar !== null && assignedCar !== undefined && cars) {
                    const car = cars.find(c => c.id === assignedCar && c.alive);
                    if (car) {
                        const [carX, carY] = toCanvas(car.x, car.y);
                        ctx.beginPath();
                        ctx.setLineDash([4, 4]);
                        ctx.moveTo(px, py);
                        ctx.lineTo(carX, carY);
                        ctx.strokeStyle = `${color}44`;
                        ctx.lineWidth = 1;
                        ctx.stroke();
                        ctx.setLineDash([]);
                    }
                }
            });
        }

        // ─── Draw A* Paths for each car ──────────────────────────────────
        if (cars) {
            cars.forEach((car) => {
                if (!car.alive || !car.path || car.path.length === 0) return;
                const color = CAR_COLORS[car.id % CAR_COLORS.length];
                const [startX, startY] = toCanvas(car.x, car.y);

                // Draw path polyline
                ctx.beginPath();
                ctx.moveTo(startX, startY);
                car.path.forEach(([wpx, wpy]) => {
                    const [wx, wy] = toCanvas(wpx, wpy);
                    ctx.lineTo(wx, wy);
                });
                ctx.strokeStyle = color + '55';  // semi-transparent
                ctx.lineWidth = 4;
                ctx.setLineDash([8, 5]);
                ctx.stroke();
                ctx.setLineDash([]);

                // Draw glow dots at each waypoint
                car.path.forEach(([wpx, wpy], i) => {
                    const [wx, wy] = toCanvas(wpx, wpy);
                    const isLast = i === car.path.length - 1;

                    // Glow
                    const wpGlow = ctx.createRadialGradient(wx, wy, 0, wx, wy, isLast ? 10 : 6);
                    wpGlow.addColorStop(0, color + '66');
                    wpGlow.addColorStop(1, color + '00');
                    ctx.fillStyle = wpGlow;
                    ctx.beginPath();
                    ctx.arc(wx, wy, isLast ? 10 : 6, 0, Math.PI * 2);
                    ctx.fill();

                    // Dot
                    ctx.beginPath();
                    ctx.arc(wx, wy, isLast ? 4 : 2.5, 0, Math.PI * 2);
                    ctx.fillStyle = isLast ? '#facc15' : color + 'aa';
                    ctx.fill();
                });
            });
        }

        // ─── Draw Cars (with smooth interpolation) ──────────────────────
        if (cars) {
            cars.forEach((car) => {
                const color = CAR_COLORS[car.id % CAR_COLORS.length];
                const isSelected = selectedAgent === car.id;

                // Smooth interpolation from previous position
                const prevKey = `car_${car.id}`;
                const prev = prevCarsRef.current[prevKey];
                let drawX = car.x;
                let drawY = car.y;
                if (prev && car.alive) {
                    const lerpFactor = 0.3;
                    drawX = prev.x + (car.x - prev.x) * lerpFactor;
                    drawY = prev.y + (car.y - prev.y) * lerpFactor;
                }
                prevCarsRef.current[prevKey] = { x: drawX, y: drawY };

                const [cx, cy] = toCanvas(drawX, drawY);

                if (!car.alive) {
                    // Collision explosion effect
                    ctx.beginPath();
                    ctx.arc(cx, cy, 12, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(244, 63, 94, 0.5)';
                    ctx.fill();
                    ctx.font = '12px JetBrains Mono';
                    ctx.fillStyle = '#f43f5e';
                    ctx.textAlign = 'center';
                    ctx.fillText('💥', cx, cy + 4);
                    return;
                }

                // Selection ring
                if (isSelected) {
                    ctx.beginPath();
                    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
                    ctx.strokeStyle = '#facc15';
                    ctx.lineWidth = 2;
                    ctx.stroke();
                }

                // Waiting indicator (brake lights)
                if (car.waiting_at_red) {
                    const brakeGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, 16);
                    brakeGlow.addColorStop(0, 'rgba(244, 63, 94, 0.25)');
                    brakeGlow.addColorStop(1, 'rgba(244, 63, 94, 0)');
                    ctx.fillStyle = brakeGlow;
                    ctx.beginPath();
                    ctx.arc(cx, cy, 16, 0, Math.PI * 2);
                    ctx.fill();
                }

                // Car body
                const angle = Math.atan2(car.vy, car.vx);
                ctx.save();
                ctx.translate(cx, cy);
                ctx.rotate(angle);

                // Car shadow
                ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
                ctx.fillRect(-9, -5, 18, 10);

                // Car rectangle
                ctx.fillStyle = color;
                ctx.fillRect(-8, -4, 16, 8);

                // Windshield
                ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
                ctx.fillRect(3, -3, 4, 6);

                // Direction indicator
                ctx.fillStyle = '#facc15';
                ctx.beginPath();
                ctx.moveTo(8, 0);
                ctx.lineTo(11, -2);
                ctx.lineTo(11, 2);
                ctx.closePath();
                ctx.fill();

                ctx.restore();

                // For stopped/completed cars — show success state
                if (car.reached_destination) {
                    // Green success ring
                    const successPulse = 0.6 + 0.4 * Math.sin(Date.now() / 500);
                    ctx.beginPath();
                    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
                    ctx.strokeStyle = `rgba(0, 255, 136, ${successPulse * 0.7})`;
                    ctx.lineWidth = 2.5;
                    ctx.stroke();

                    // Tick label
                    ctx.font = 'bold 9px JetBrains Mono';
                    ctx.fillStyle = '#00ff88';
                    ctx.textAlign = 'center';
                    ctx.fillText(`A${car.id} ✓`, cx, cy - 12);
                } else {
                    // Agent ID label + pickup count
                    ctx.font = 'bold 9px JetBrains Mono';
                    ctx.fillStyle = color;
                    ctx.textAlign = 'center';
                    const pickupLabel = car.pickups > 0 ? ` 🧑${car.pickups}` : '';
                    ctx.fillText(`A${car.id}${pickupLabel}`, cx, cy - 12);

                    // Speed indicator bar
                    const speedBarWidth = car.speed * 2;
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.4)';
                    ctx.fillRect(cx - 9, cy + 10, 18, 3);
                    ctx.fillStyle = car.speed > 7 ? '#f43f5e' : car.speed > 4 ? '#facc15' : '#00ff88';
                    ctx.fillRect(cx - 9, cy + 10, Math.min(speedBarWidth, 18), 3);
                }
            });
        }

        // ─── Draw Pickup Tick Marks ✓ ────────────────────────────────────
        if (pickup_events && pickup_events.length > 0) {
            pickup_events.forEach((ev) => {
                const [ex, ey] = toCanvas(ev.x, ev.y);
                const evColor = CAR_COLORS[ev.car_id % CAR_COLORS.length];
                const age = (state.step || 0) - ev.step;

                // Animated expanding ring (fades with age)
                const ringAlpha = Math.max(0.1, 0.8 - age * 0.005);
                const ringRadius = 12 + Math.min(age * 0.1, 8);
                const tickGlow = ctx.createRadialGradient(ex, ey, 0, ex, ey, ringRadius);
                tickGlow.addColorStop(0, `rgba(0, 255, 136, ${ringAlpha * 0.5})`);
                tickGlow.addColorStop(1, `rgba(0, 255, 136, 0)`);
                ctx.fillStyle = tickGlow;
                ctx.beginPath();
                ctx.arc(ex, ey, ringRadius, 0, Math.PI * 2);
                ctx.fill();

                // Green circle background
                ctx.beginPath();
                ctx.arc(ex, ey, 8, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(0, 255, 136, ${ringAlpha * 0.3})`;
                ctx.fill();
                ctx.strokeStyle = `rgba(0, 255, 136, ${ringAlpha})`;
                ctx.lineWidth = 1.5;
                ctx.stroke();

                // Tick mark ✓
                ctx.beginPath();
                ctx.moveTo(ex - 4, ey);
                ctx.lineTo(ex - 1, ey + 3);
                ctx.lineTo(ex + 5, ey - 3);
                ctx.strokeStyle = '#00ff88';
                ctx.lineWidth = 2.5;
                ctx.lineCap = 'round';
                ctx.lineJoin = 'round';
                ctx.stroke();
                ctx.lineCap = 'butt';
                ctx.lineJoin = 'miter';

                // Pickup label
                ctx.font = 'bold 7px JetBrains Mono';
                ctx.fillStyle = `rgba(0, 255, 136, ${ringAlpha})`;
                ctx.textAlign = 'center';
                ctx.fillText(`P${ev.person_id}`, ex, ey + 16);
            });
        }

        // Legend
        ctx.font = '10px Inter';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.textAlign = 'left';
        ctx.fillText(`Step: ${state.step || 0}`, 8, 14);
        ctx.fillText(`Cars: ${cars ? cars.filter(c => c.alive).length : 0}`, 8, 26);
        if (persons) {
            ctx.fillText(`Persons: ${persons.filter(p => !p.picked_up).length}`, 8, 38);
        }
        if (pickup_events) {
            ctx.fillText(`Pickups: ${pickup_events.length}`, 8, 50);
        }

    }, [state, selectedAgent]);

    useEffect(() => {
        // Use requestAnimationFrame for smooth person animations
        const animate = () => {
            draw();
            animRef.current = requestAnimationFrame(animate);
        };
        animate();
        return () => {
            if (animRef.current) cancelAnimationFrame(animRef.current);
        };
    }, [draw]);

    const handleClick = (e) => {
        if (!state || !state.cars) return;
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        const scale = (CANVAS_SIZE - 2 * PADDING) / ((state.grid_size - 1) * state.road_spacing);

        for (const car of state.cars) {
            const cx = PADDING + car.x * scale;
            const cy = PADDING + car.y * scale;
            if (Math.sqrt((mx - cx) ** 2 + (my - cy) ** 2) < 15) {
                onSelectAgent && onSelectAgent(car.id);
                return;
            }
        }
        onSelectAgent && onSelectAgent(null);
    };

    return (
        <canvas
            ref={canvasRef}
            width={CANVAS_SIZE}
            height={CANVAS_SIZE}
            onClick={handleClick}
            className="simulation-canvas cursor-crosshair"
            style={{ width: '100%', maxWidth: `${CANVAS_SIZE}px`, height: 'auto', aspectRatio: '1' }}
        />
    );
}
