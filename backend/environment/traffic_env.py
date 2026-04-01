"""
Traffic Environment Simulator
OpenAI Gym-style multi-agent traffic environment with grid road network,
traffic signals, collision detection, congestion, and passenger pickup.

Key design:
  - Persons spawn at random intersections; cars navigate to pick them up.
  - Optimal car-person assignment: closest available car is assigned.
  - A* pathfinding on the intersection graph for optimal routing.
  - Cars are constrained to road segments (no free-space drift).
  - Traffic-light-aware edge costs for intelligent route planning.
"""

import numpy as np
import random
import math
import heapq


# ─── Traffic Signal ──────────────────────────────────────────────────────────

class TrafficSignal:
    """Traffic signal at an intersection."""

    def __init__(self, position, cycle_length=80):
        self.position = np.array(position, dtype=np.float32)
        self.cycle_length = cycle_length
        self.timer = random.randint(0, cycle_length - 1)
        self.state = 0  # 0 = green, 1 = red

    def step(self):
        self.timer += 1
        if self.timer >= self.cycle_length:
            self.timer = 0
            self.state = 1 - self.state

    def get_state(self):
        return self.state

    @property
    def time_until_change(self):
        return self.cycle_length - self.timer


# ─── Person (Passenger) ─────────────────────────────────────────────────────

class Person:
    """A person waiting to be picked up at an intersection."""

    _next_id = 0

    def __init__(self, grid_size, road_spacing, occupied_positions=None):
        self.person_id = Person._next_id
        Person._next_id += 1
        self.grid_size = grid_size
        self.road_spacing = road_spacing
        self.picked_up = False
        self.assigned_car_id = None
        self.wait_time = 0  # how long they've been waiting

        # Spawn on a random intersection, avoiding occupied ones
        occupied = occupied_positions or set()
        attempts = 0
        while attempts < 100:
            ix = random.randint(0, grid_size - 1)
            iy = random.randint(0, grid_size - 1)
            if (ix, iy) not in occupied:
                break
            attempts += 1

        self.ix = ix
        self.iy = iy
        self.x = float(ix * road_spacing)
        self.y = float(iy * road_spacing)

    @property
    def position(self):
        return np.array([self.x, self.y])

    @staticmethod
    def reset_id_counter():
        Person._next_id = 0


# ─── Car ─────────────────────────────────────────────────────────────────────

class Car:
    """Individual car (agent body) in the environment."""

    def __init__(self, car_id, grid_size, road_spacing):
        self.car_id = car_id
        self.grid_size = grid_size
        self.road_spacing = road_spacing
        self.max_coord = (grid_size - 1) * road_spacing
        self.reset()

    def reset(self):
        # Spawn at a random intersection
        ix = random.randint(0, self.grid_size - 1)
        iy = random.randint(0, self.grid_size - 1)
        self.x = float(ix * self.road_spacing)
        self.y = float(iy * self.road_spacing)
        self.ix = ix  # current grid-x index
        self.iy = iy  # current grid-y index

        heading = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.vx, self.vy = float(heading[0]), float(heading[1])

        self.speed = 6.0
        self.alive = True
        self.reached_destination = False
        self.lane = random.randint(0, 1)
        self.steps_alive = 0
        self.total_reward = 0.0
        self.waiting_at_red = False
        self.pickups = 0  # how many persons this car has picked up

        # Target person (assigned by environment)
        self.target_person_id = None
        self.dest_x = self.x
        self.dest_y = self.y

        # A* path — list of (ix, iy) waypoints (excluding current position)
        self.path = []
        # World-coordinate path for frontend rendering
        self.path_world = []

    @property
    def position(self):
        return np.array([self.x, self.y])

    @property
    def velocity(self):
        return np.array([self.vx, self.vy])

    @property
    def dest_distance(self):
        return math.sqrt((self.x - self.dest_x) ** 2 + (self.y - self.dest_y) ** 2)


# ─── Traffic Environment ────────────────────────────────────────────────────

class TrafficEnvironment:
    """
    Multi-agent traffic grid environment with passenger pickup.

    State per agent (14-dim):
        [x, y, vx, vy, dest_dx, dest_dy,
         nearest_car_dist, nearest_car_angle,
         signal_state, signal_timer_frac,
         speed_norm, lane,
         has_target, target_dist_norm]

    Actions (6 discrete):
        0: accelerate
        1: decelerate
        2: turn left
        3: turn right
        4: maintain speed
        5: stop
    """

    ACTIONS = {
        0: 'accelerate',
        1: 'decelerate',
        2: 'turn_left',
        3: 'turn_right',
        4: 'maintain',
        5: 'stop'
    }

    def __init__(self, grid_size=6, num_agents=4, road_spacing=100.0, max_steps=1000):
        self.grid_size = grid_size
        self.num_agents = num_agents
        self.road_spacing = road_spacing
        self.max_steps = max_steps
        self.state_size = 14
        self.action_size = 6
        self.current_step = 0
        self.max_coord = (grid_size - 1) * road_spacing

        # How many persons to keep on the grid simultaneously
        self.num_persons = max(2, num_agents)  # at least 2, or as many as agents

        # Build traffic signals at intersections
        self.signals = []
        for i in range(grid_size):
            for j in range(grid_size):
                pos = [i * road_spacing, j * road_spacing]
                cycle = random.randint(60, 100)
                self.signals.append(TrafficSignal(pos, cycle_length=cycle))

        self.cars = []
        self.persons = []
        self.pickup_events = []  # Track pickup locations for tick marks
        self.metrics = {
            'collisions': 0,
            'destinations_reached': 0,
            'persons_picked_up': 0,
            'avg_speed': 0.0,
            'congestion': 0.0,
            'total_reward': 0.0,
        }

    def reset(self):
        """Reset environment and return initial observations."""
        self.current_step = 0
        Person.reset_id_counter()
        self.pickup_events = []
        self.cars = [Car(i, self.grid_size, self.road_spacing) for i in range(self.num_agents)]

        # Stagger signal timers
        for idx, sig in enumerate(self.signals):
            sig.timer = (idx * 7) % sig.cycle_length
            sig.state = 0 if sig.timer < sig.cycle_length // 2 else 1

        # Spawn initial persons
        self.persons = []
        self._spawn_persons(self.num_persons)

        # Assign cars to nearest persons
        self._assign_cars_to_persons()

        self.metrics = {
            'collisions': 0,
            'destinations_reached': 0,
            'persons_picked_up': 0,
            'avg_speed': 0.0,
            'congestion': 0.0,
            'total_reward': 0.0,
        }
        return self._get_all_observations()

    # ------------------------------------------------------------------
    #  Person Management
    # ------------------------------------------------------------------

    def _get_occupied_person_positions(self):
        """Get set of grid positions where persons already exist."""
        return {(p.ix, p.iy) for p in self.persons if not p.picked_up}

    def _spawn_persons(self, count):
        """Spawn `count` new persons at unoccupied intersections."""
        occupied = self._get_occupied_person_positions()
        for _ in range(count):
            p = Person(self.grid_size, self.road_spacing, occupied)
            self.persons.append(p)
            occupied.add((p.ix, p.iy))

    def _assign_cars_to_persons(self):
        """Assign each unassigned car to the nearest unassigned person (greedy) and compute A* paths."""
        available_persons = [p for p in self.persons if not p.picked_up and p.assigned_car_id is None]
        unassigned_cars = [c for c in self.cars if c.alive and not c.reached_destination and c.target_person_id is None]

        # Sort by distance pairs (greedy closest-first assignment)
        pairs = []
        for car in unassigned_cars:
            for person in available_persons:
                dist = np.linalg.norm(car.position - person.position)
                pairs.append((dist, car, person))

        pairs.sort(key=lambda x: x[0])

        assigned_cars = set()
        assigned_persons = set()

        for dist, car, person in pairs:
            if car.car_id in assigned_cars or person.person_id in assigned_persons:
                continue
            # Assign
            car.target_person_id = person.person_id
            car.dest_x = person.x
            car.dest_y = person.y
            person.assigned_car_id = car.car_id
            assigned_cars.add(car.car_id)
            assigned_persons.add(person.person_id)

            # Compute A* path from car's current grid position to person's grid position
            self._compute_path_for_car(car, person.ix, person.iy)

    # ------------------------------------------------------------------
    #  Step
    # ------------------------------------------------------------------

    def step(self, actions):
        """Execute one step for all agents."""
        self.current_step += 1
        rewards = {}
        dones = {}
        info = {'collisions': [], 'destinations': [], 'pickups': []}

        # Update traffic signals
        for sig in self.signals:
            sig.step()

        # Increment person wait times
        for p in self.persons:
            if not p.picked_up:
                p.wait_time += 1

        # Apply actions and move cars
        for car in self.cars:
            if not car.alive or car.reached_destination:
                continue

            action = actions.get(car.car_id, 4)
            self._apply_action(car, action)

            # Move
            car.x += car.vx * car.speed
            car.y += car.vy * car.speed
            car.steps_alive += 1

            # Bounce off boundaries
            if car.x <= 0:
                car.x = 0.0
                if car.vx < 0:
                    car.vx = -car.vx
            elif car.x >= self.max_coord:
                car.x = self.max_coord
                if car.vx > 0:
                    car.vx = -car.vx
            if car.y <= 0:
                car.y = 0.0
                if car.vy < 0:
                    car.vy = -car.vy
            elif car.y >= self.max_coord:
                car.y = self.max_coord
                if car.vy > 0:
                    car.vy = -car.vy

        # Calculate rewards
        for car in self.cars:
            if not car.alive or car.reached_destination:
                rewards[car.car_id] = 0.0
                dones[car.car_id] = True
                continue

            reward = -0.1  # small time penalty

            # ── Check pickup ──────────────────────────────────────
            if car.target_person_id is not None:
                target_person = self._get_person_by_id(car.target_person_id)
                if target_person and not target_person.picked_up:
                    dist = car.dest_distance

                    # Progress reward (getting closer)
                    prev_x = car.x - car.vx * car.speed
                    prev_y = car.y - car.vy * car.speed
                    prev_dist = math.sqrt((prev_x - car.dest_x) ** 2 + (prev_y - car.dest_y) ** 2)
                    progress = prev_dist - dist
                    reward += progress * 0.5

                    # Pickup check
                    if dist < 20.0:
                        reward += 50.0
                        target_person.picked_up = True
                        car.pickups += 1
                        car.target_person_id = None
                        self.metrics['persons_picked_up'] += 1
                        self.metrics['destinations_reached'] += 1
                        info['pickups'].append({
                            'car_id': car.car_id,
                            'person_id': target_person.person_id,
                        })
                else:
                    # Person was somehow already picked up (shouldn't happen), clear assignment
                    car.target_person_id = None
                    car.dest_x = car.x
                    car.dest_y = car.y

            # ── Collision check ───────────────────────────────────
            for other in self.cars:
                if other.car_id == car.car_id or not other.alive:
                    continue
                pair_dist = np.linalg.norm(car.position - other.position)
                if pair_dist < 10.0:
                    reward -= 50.0
                    car.alive = False
                    self.metrics['collisions'] += 1
                    info['collisions'].append(car.car_id)
                    # Release person assignment
                    if car.target_person_id is not None:
                        p = self._get_person_by_id(car.target_person_id)
                        if p:
                            p.assigned_car_id = None
                        car.target_person_id = None
                    break

            # ── Traffic signal compliance ─────────────────────────
            nearest_sig = self._nearest_signal(car)
            if nearest_sig is not None:
                sig_dist = np.linalg.norm(car.position - nearest_sig.position)
                is_red = nearest_sig.state == 1
                if sig_dist < 12.0 and is_red and car.speed > 1.0:
                    reward -= 3.0
                    car.waiting_at_red = True
                elif sig_dist < 12.0 and is_red and car.speed <= 1.0:
                    reward += 0.5
                    car.waiting_at_red = True
                else:
                    car.waiting_at_red = False

            car.total_reward += reward
            rewards[car.car_id] = reward
            dones[car.car_id] = not car.alive

        # ── Spawn new persons to replace picked-up ones ───────────
        active_persons = [p for p in self.persons if not p.picked_up]
        if len(active_persons) < self.num_persons:
            num_to_spawn = self.num_persons - len(active_persons)
            self._spawn_persons(num_to_spawn)

        # ── Re-assign unassigned cars ─────────────────────────────
        self._assign_cars_to_persons()

        # ── Update metrics ────────────────────────────────────────
        alive_cars = [c for c in self.cars if c.alive]
        self.metrics['avg_speed'] = float(np.mean([c.speed for c in alive_cars])) if alive_cars else 0.0
        self.metrics['congestion'] = self._calculate_congestion()
        self.metrics['total_reward'] = sum(rewards.values())

        # Episode termination
        all_done = (all(not c.alive for c in self.cars)
                    or self.current_step >= self.max_steps)
        if all_done:
            for car in self.cars:
                dones[car.car_id] = True

        observations = self._get_all_observations()
        return observations, rewards, dones, info

    # ------------------------------------------------------------------
    #  Actions
    # ------------------------------------------------------------------

    def _apply_action(self, car, action):
        """Apply discrete action to a car."""
        if action == 0:  # accelerate
            car.speed = min(car.speed + 1.0, 10.0)
        elif action == 1:  # decelerate
            car.speed = max(car.speed - 1.0, 0.0)
        elif action == 2:  # turn left
            car.vx, car.vy = car.vy, -car.vx
        elif action == 3:  # turn right
            car.vx, car.vy = -car.vy, car.vx
        elif action == 4:  # maintain
            pass
        elif action == 5:  # stop
            car.speed = 0.0

    # ------------------------------------------------------------------
    #  A* Pathfinding on Intersection Graph
    # ------------------------------------------------------------------

    def _get_signal_at(self, ix, iy):
        """Get the traffic signal at grid intersection (ix, iy)."""
        idx = ix * self.grid_size + iy
        if 0 <= idx < len(self.signals):
            return self.signals[idx]
        return None

    def _astar_path(self, start_ix, start_iy, goal_ix, goal_iy):
        """
        A* pathfinding on the intersection graph.
        Returns list of (ix, iy) waypoints from start to goal (inclusive of goal, exclusive of start).
        Edge cost = road_spacing + red-light penalty at destination node.
        """
        if start_ix == goal_ix and start_iy == goal_iy:
            return []

        gs = self.grid_size
        # Heuristic: Manhattan distance in grid units
        def h(ix, iy):
            return (abs(ix - goal_ix) + abs(iy - goal_iy)) * self.road_spacing

        # Priority queue: (f_cost, counter, ix, iy)
        counter = 0
        open_set = [(h(start_ix, start_iy), counter, start_ix, start_iy)]
        came_from = {}
        g_score = {(start_ix, start_iy): 0.0}

        while open_set:
            f, _, cx, cy = heapq.heappop(open_set)

            if cx == goal_ix and cy == goal_iy:
                # Reconstruct path
                path = []
                node = (goal_ix, goal_iy)
                while node in came_from:
                    path.append(node)
                    node = came_from[node]
                path.reverse()
                return path

            # Explore 4-connected neighbors
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                nx, ny = cx + dx, cy + dy
                if nx < 0 or nx >= gs or ny < 0 or ny >= gs:
                    continue

                # Edge cost = base road distance + traffic signal penalty
                edge_cost = self.road_spacing
                sig = self._get_signal_at(nx, ny)
                if sig and sig.state == 1:  # red light
                    # Add penalty proportional to wait time (encourages green-light routes)
                    edge_cost += sig.time_until_change * 1.5

                tentative_g = g_score[(cx, cy)] + edge_cost
                if (nx, ny) not in g_score or tentative_g < g_score[(nx, ny)]:
                    g_score[(nx, ny)] = tentative_g
                    f_score = tentative_g + h(nx, ny)
                    came_from[(nx, ny)] = (cx, cy)
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, nx, ny))

        # No path found (shouldn't happen on a fully connected grid)
        return []

    def _compute_path_for_car(self, car, goal_ix, goal_iy):
        """Compute and store A* path for a car."""
        car.path = self._astar_path(car.ix, car.iy, goal_ix, goal_iy)
        car.path_world = [
            (ix * self.road_spacing, iy * self.road_spacing) for ix, iy in car.path
        ]

    # ------------------------------------------------------------------
    #  Path-Following Movement (replaces old smart nav heuristic)
    # ------------------------------------------------------------------

    def step_with_pathfinding(self):
        """
        Step the simulation with A*-based path-following for all cars.
        Cars move along their computed paths, constrained to road segments.
        Returns: (observations, rewards, dones, info)
        """
        self.current_step += 1
        rewards = {}
        dones = {}
        info = {'collisions': [], 'destinations': [], 'pickups': []}

        # Update traffic signals
        for sig in self.signals:
            sig.step()

        # Increment person wait times
        for p in self.persons:
            if not p.picked_up:
                p.wait_time += 1

        # Move each car along its A* path
        for car in self.cars:
            if not car.alive or car.reached_destination:
                continue
            self._move_car_along_path(car)
            car.steps_alive += 1

        # Calculate rewards
        for car in self.cars:
            if not car.alive or car.reached_destination:
                rewards[car.car_id] = 0.0
                dones[car.car_id] = True
                continue

            reward = -0.1  # small time penalty

            # ── Check pickup ──────────────────────────────────────
            if car.target_person_id is not None:
                target_person = self._get_person_by_id(car.target_person_id)
                if target_person and not target_person.picked_up:
                    dist = car.dest_distance

                    # Progress reward (getting closer)
                    prev_dist = getattr(car, '_prev_dest_dist', dist)
                    progress = prev_dist - dist
                    reward += progress * 0.5
                    car._prev_dest_dist = dist

                    # Pickup check
                    if dist < 20.0:
                        reward += 50.0
                        target_person.picked_up = True
                        car.pickups += 1
                        car.speed = 0.0
                        car.reached_destination = True
                        car.path = []
                        car.path_world = []
                        self.metrics['persons_picked_up'] += 1
                        self.metrics['destinations_reached'] += 1
                        # Record pickup event for tick mark rendering
                        self.pickup_events.append({
                            'car_id': car.car_id,
                            'person_id': target_person.person_id,
                            'x': float(car.x),
                            'y': float(car.y),
                            'step': self.current_step,
                        })
                        info['pickups'].append({
                            'car_id': car.car_id,
                            'person_id': target_person.person_id,
                        })
                        # Keep target info so the car stays here
                        # car.target_person_id = None  # don't clear — car has completed
                else:
                    car.target_person_id = None
                    car.dest_x = car.x
                    car.dest_y = car.y
                    car.path = []
                    car.path_world = []

            # ── Collision check ───────────────────────────────────
            for other in self.cars:
                if other.car_id == car.car_id or not other.alive:
                    continue
                pair_dist = np.linalg.norm(car.position - other.position)
                if pair_dist < 10.0:
                    reward -= 50.0
                    car.alive = False
                    self.metrics['collisions'] += 1
                    info['collisions'].append(car.car_id)
                    if car.target_person_id is not None:
                        p = self._get_person_by_id(car.target_person_id)
                        if p:
                            p.assigned_car_id = None
                        car.target_person_id = None
                        car.path = []
                        car.path_world = []
                    break

            # ── Traffic signal compliance reward ──────────────────
            nearest_sig = self._nearest_signal(car)
            if nearest_sig is not None:
                sig_dist = np.linalg.norm(car.position - nearest_sig.position)
                is_red = nearest_sig.state == 1
                if sig_dist < 12.0 and is_red and car.speed > 1.0:
                    reward -= 3.0
                elif sig_dist < 12.0 and is_red and car.speed <= 1.0:
                    reward += 0.5

            car.total_reward += reward
            rewards[car.car_id] = reward
            dones[car.car_id] = not car.alive

        # ── Spawn new persons to replace picked-up ones ───────────
        active_persons = [p for p in self.persons if not p.picked_up]
        if len(active_persons) < self.num_persons:
            num_to_spawn = self.num_persons - len(active_persons)
            self._spawn_persons(num_to_spawn)

        # ── Re-assign unassigned cars ─────────────────────────────
        self._assign_cars_to_persons()

        # ── Update metrics ────────────────────────────────────────
        alive_cars = [c for c in self.cars if c.alive]
        self.metrics['avg_speed'] = float(np.mean([c.speed for c in alive_cars])) if alive_cars else 0.0
        self.metrics['congestion'] = self._calculate_congestion()
        self.metrics['total_reward'] = sum(rewards.values())

        # Episode termination
        all_done = (all(not c.alive for c in self.cars)
                    or self.current_step >= self.max_steps)
        if all_done:
            for car in self.cars:
                dones[car.car_id] = True

        observations = self._get_all_observations()
        return observations, rewards, dones, info

    def _move_car_along_path(self, car):
        """
        Move a car along its A* path, constrained to road segments.
        The car travels from its current (x, y) toward the next waypoint.
        When it reaches a waypoint, it pops the waypoint and continues.
        Stops at red lights before entering an intersection.
        """
        if not car.path:
            # No path — stay put
            car.speed = 0.0
            car.waiting_at_red = False
            return

        # Target: next waypoint in world coordinates
        next_ix, next_iy = car.path[0]
        target_x = float(next_ix * self.road_spacing)
        target_y = float(next_iy * self.road_spacing)

        dx = target_x - car.x
        dy = target_y - car.y
        dist_to_next = math.sqrt(dx * dx + dy * dy)

        # ── Check traffic signal at the NEXT intersection ─────────
        sig = self._get_signal_at(next_ix, next_iy)
        if sig and sig.state == 1:  # red
            # If close to intersection, stop and wait
            if dist_to_next < 25.0:
                car.speed = max(car.speed - 2.0, 0.0)
                car.waiting_at_red = True
                if dist_to_next < 15.0:
                    car.speed = 0.0
                    return
        else:
            car.waiting_at_red = False
            # Resume speed if was waiting
            if car.speed < 6.0:
                car.speed = min(car.speed + 1.5, 6.0)

        # ── Set heading toward next waypoint (axis-aligned) ────────
        # Determine movement axis and snap non-moving coordinate to road
        if abs(dx) >= abs(dy):
            # Moving horizontally — snap y to current road
            car.vx = 1.0 if dx > 0 else -1.0
            car.vy = 0.0
            car.y = float(car.iy * self.road_spacing)  # snap to road
        else:
            # Moving vertically — snap x to current road
            car.vx = 0.0
            car.vy = 1.0 if dy > 0 else -1.0
            car.x = float(car.ix * self.road_spacing)  # snap to road

        # ── Move along segment ────────────────────────────────────
        move_dist = car.speed
        if move_dist >= dist_to_next and dist_to_next > 0:
            # Arrived at waypoint — snap to it
            car.x = target_x
            car.y = target_y
            car.ix = next_ix
            car.iy = next_iy
            car.path.pop(0)
            if car.path_world:
                car.path_world.pop(0)
            # Use remaining movement to start toward next waypoint
            remaining = move_dist - dist_to_next
            if car.path and remaining > 0:
                next2_ix, next2_iy = car.path[0]
                t2x = float(next2_ix * self.road_spacing)
                t2y = float(next2_iy * self.road_spacing)
                d2x = t2x - car.x
                d2y = t2y - car.y
                d2 = math.sqrt(d2x * d2x + d2y * d2y)
                if d2 > 0:
                    if abs(d2x) >= abs(d2y):
                        car.vx = 1.0 if d2x > 0 else -1.0
                        car.vy = 0.0
                        car.y = float(car.iy * self.road_spacing)
                    else:
                        car.vx = 0.0
                        car.vy = 1.0 if d2y > 0 else -1.0
                        car.x = float(car.ix * self.road_spacing)
                    step = min(remaining, d2)
                    car.x += car.vx * step
                    car.y += car.vy * step
        elif dist_to_next > 0:
            # Normal movement along segment
            car.x += car.vx * move_dist
            car.y += car.vy * move_dist

        # ── Clamp to grid boundaries ──────────────────────────────
        car.x = max(0.0, min(car.x, self.max_coord))
        car.y = max(0.0, min(car.y, self.max_coord))

    # ------------------------------------------------------------------
    #  Legacy: get_smart_actions (kept for backward compatibility)
    # ------------------------------------------------------------------

    def get_smart_actions(self):
        """Legacy wrapper — returns maintain actions. Use step_with_pathfinding() instead."""
        return {car.car_id: 4 for car in self.cars}

    # ------------------------------------------------------------------
    #  Helpers
    # ------------------------------------------------------------------

    def _get_person_by_id(self, person_id):
        for p in self.persons:
            if p.person_id == person_id:
                return p
        return None

    def _nearest_signal(self, car):
        min_dist = float('inf')
        nearest = None
        for sig in self.signals:
            dist = np.linalg.norm(car.position - sig.position)
            if dist < min_dist:
                min_dist = dist
                nearest = sig
        return nearest

    def _get_all_observations(self):
        obs = {}
        for car in self.cars:
            obs[car.car_id] = self._get_observation(car)
        return obs

    def _get_observation(self, car):
        """
        14-dim observation:
        [x, y, vx, vy, dest_dx, dest_dy,
         nearest_car_dist, nearest_car_angle,
         signal_state, signal_timer_frac,
         speed_norm, lane,
         has_target, target_dist_norm]
        """
        if not car.alive:
            return np.zeros(self.state_size, dtype=np.float32)

        max_c = self.max_coord if self.max_coord > 0 else 1.0

        # Direction to destination
        dest_dx = (car.dest_x - car.x) / max_c
        dest_dy = (car.dest_y - car.y) / max_c

        # Nearest car
        nearest_dist = 999.0
        nearest_angle = 0.0
        for other in self.cars:
            if other.car_id == car.car_id or not other.alive:
                continue
            d = np.linalg.norm(car.position - other.position)
            if d < nearest_dist:
                nearest_dist = d
                diff = other.position - car.position
                nearest_angle = math.atan2(diff[1], diff[0])

        # Nearest signal
        sig = self._nearest_signal(car)
        sig_state = float(sig.get_state()) if sig else 0.0
        sig_timer_frac = float(sig.time_until_change / sig.cycle_length) if sig else 0.5

        has_target = 1.0 if car.target_person_id is not None else 0.0
        target_dist = car.dest_distance / max_c if car.target_person_id is not None else 1.0

        state = np.array([
            car.x / max_c,
            car.y / max_c,
            car.vx,
            car.vy,
            dest_dx,
            dest_dy,
            min(nearest_dist / max_c, 1.0),
            nearest_angle / math.pi,
            sig_state,
            sig_timer_frac,
            car.speed / 10.0,
            float(car.lane),
            has_target,
            target_dist,
        ], dtype=np.float32)

        return state

    def _calculate_congestion(self):
        alive = [c for c in self.cars if c.alive]
        if len(alive) < 2:
            return 0.0
        total = 0.0
        count = 0
        for i, c1 in enumerate(alive):
            for c2 in alive[i + 1:]:
                dist = np.linalg.norm(c1.position - c2.position)
                total += 1.0 / (dist + 1.0)
                count += 1
        return total / count if count > 0 else 0.0

    def get_state_for_render(self):
        """Get full state dict for frontend rendering."""
        return {
            'step': self.current_step,
            'cars': [
                {
                    'id': c.car_id,
                    'x': float(c.x),
                    'y': float(c.y),
                    'vx': float(c.vx),
                    'vy': float(c.vy),
                    'speed': float(c.speed),
                    'alive': c.alive,
                    'reached_destination': c.reached_destination,
                    'lane': c.lane,
                    'dest_x': float(c.dest_x),
                    'dest_y': float(c.dest_y),
                    'waiting_at_red': getattr(c, 'waiting_at_red', False),
                    'target_person_id': c.target_person_id,
                    'pickups': c.pickups,
                    'path': getattr(c, 'path_world', []),
                }
                for c in self.cars
            ],
            'persons': [
                {
                    'id': p.person_id,
                    'x': float(p.x),
                    'y': float(p.y),
                    'picked_up': p.picked_up,
                    'assigned_car_id': p.assigned_car_id,
                    'wait_time': p.wait_time,
                }
                for p in self.persons if not p.picked_up
            ],
            'signals': [
                {
                    'x': float(s.position[0]),
                    'y': float(s.position[1]),
                    'state': s.get_state(),
                    'timer_frac': float(s.time_until_change / s.cycle_length),
                }
                for s in self.signals
            ],
            'pickup_events': [
                {
                    'car_id': ev['car_id'],
                    'person_id': ev['person_id'],
                    'x': ev['x'],
                    'y': ev['y'],
                    'step': ev['step'],
                }
                for ev in self.pickup_events
            ],
            'metrics': {
                'step': self.current_step,
                'collisions': self.metrics['collisions'],
                'destinations_reached': self.metrics['destinations_reached'],
                'persons_picked_up': self.metrics['persons_picked_up'],
                'avg_speed': float(self.metrics['avg_speed']),
                'congestion': float(self.metrics['congestion']),
                'total_reward': float(self.metrics['total_reward']),
            },
            'grid_size': self.grid_size,
            'road_spacing': self.road_spacing,
        }
