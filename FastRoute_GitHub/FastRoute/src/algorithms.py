"""Student-readable routing algorithms. Matrix entries are directed travel costs."""
import heapq
import itertools
import math
import time


def dijkstra(graph, source, target=None, record_steps=False):
    """Shortest paths on a directed nonnegative-weight adjacency list.

    graph: {node: [(neighbor, weight), ...]}
    Complexity: O((V+E) log V) with a binary heap.

    When record_steps is True, also returns a list of settle/relax events for visualization.
    The default path stays unchanged for normal matrix construction.
    """
    distances = {source: 0.0}
    previous = {}
    heap = [(0.0, source)]
    explored = 0
    steps = []
    while heap:
        distance, node = heapq.heappop(heap)
        if distance > distances.get(node, math.inf):
            continue
        explored += 1
        if record_steps:
            frontier_preview = sorted(
                ((dist, n) for dist, n in heap if dist <= distances.get(n, math.inf)),
                key=lambda item: item[0],
            )[:5]
            steps.append({
                'event': 'settle',
                'node': node,
                'distance': distance,
                'explored': explored,
                'next_frontier': [
                    {'node': n, 'distance': dist} for dist, n in frontier_preview
                ],
            })
        if node == target:
            break
        for neighbor, weight in graph.get(node, []):
            if weight < 0:
                raise ValueError('Dijkstra requires nonnegative weights')
            candidate = distance + weight
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                previous[neighbor] = node
                heapq.heappush(heap, (candidate, neighbor))
                if record_steps:
                    steps.append({
                        'event': 'relax',
                        'from': node,
                        'to': neighbor,
                        'distance': candidate,
                        'explored': explored,
                    })
    if record_steps:
        return distances, previous, explored, steps
    return distances, previous, explored


def reconstruct(previous, source, target):
    if source == target:
        return [source]
    path = [target]
    while path[-1] != source:
        if path[-1] not in previous:
            return []
        path.append(previous[path[-1]])
    return path[::-1]


def route_cost(matrix, route):
    return sum(matrix[a][b] for a, b in zip(route, route[1:]))


def brute_force(matrix):
    """Exact factorial baseline; depot index 0; return to depot."""
    n = len(matrix)
    if n == 1:
        return [0, 0], 0.0, 1
    best = (math.inf, None)
    examined = 0
    for order in itertools.permutations(range(1, n)):
        route = [0, *order, 0]
        cost = route_cost(matrix, route)
        examined += 1
        if cost < best[0]:
            best = (cost, route)
    return best[1], best[0], examined


def nearest_neighbor(matrix):
    """Greedy nearest unvisited stop; O(n^2)."""
    n = len(matrix)
    remaining = set(range(1, n))
    route = [0]
    examined = 0
    while remaining:
        current = route[-1]
        for _ in remaining:
            examined += 1
        next_stop = min(remaining, key=lambda v: (matrix[current][v], v))
        route.append(next_stop)
        remaining.remove(next_stop)
    route.append(0)
    return route, route_cost(matrix, route), examined


def two_opt(matrix, initial_route, max_passes=40, record_swaps=False):
    """2-opt local search with full cost recomputation; supports directed costs.

    When record_swaps is True, also returns a list of improving swaps for animation.
    """
    best = initial_route[:]
    best_cost = route_cost(matrix, best)
    examined = 0
    swaps = []
    for _ in range(max_passes):
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                candidate = best[:i] + list(reversed(best[i:j + 1])) + best[j + 1:]
                cost = route_cost(matrix, candidate)
                examined += 1
                if cost + 1e-9 < best_cost:
                    if record_swaps:
                        swaps.append({
                            'i': i,
                            'j': j,
                            'before_cost': best_cost,
                            'after_cost': cost,
                            'route': candidate[:],
                        })
                    best, best_cost = candidate, cost
                    improved = True
        if not improved:
            break
    if record_swaps:
        return best, best_cost, examined, swaps
    return best, best_cost, examined


def nearest_neighbor_two_opt(matrix, max_passes=40, record_swaps=False):
    """Nearest Neighbor seed followed by 2-Opt improvement."""
    seed_route, seed_cost, seed_ops = nearest_neighbor(matrix)
    if record_swaps:
        improved, cost, ops, swaps = two_opt(matrix, seed_route, max_passes=max_passes, record_swaps=True)
        return improved, cost, seed_ops + ops, {
            'initial_route': seed_route,
            'initial_distance_m': seed_cost,
            'swaps': swaps,
            'swap_count': len(swaps),
        }
    improved, cost, ops = two_opt(matrix, seed_route, max_passes=max_passes)
    return improved, cost, seed_ops + ops


def held_karp(matrix):
    """Exact subset DP, O(n^2 2^n) time, O(n 2^n) states."""
    n = len(matrix)
    if n == 1:
        return [0, 0], 0.0, 1
    # (visited mask, final node) -> (cost, predecessor)
    dp = {}
    for j in range(1, n):
        dp[(1 << (j - 1), j)] = (matrix[0][j], 0)
    states = len(dp)
    for size in range(2, n):
        for subset in itertools.combinations(range(1, n), size):
            mask = sum(1 << (v - 1) for v in subset)
            for last in subset:
                prev_mask = mask ^ (1 << (last - 1))
                cost, prev = min(
                    (dp[(prev_mask, before)][0] + matrix[before][last], before)
                    for before in subset if before != last
                )
                dp[(mask, last)] = (cost, prev)
                states += 1
    full = (1 << (n - 1)) - 1
    total, last = min((dp[(full, j)][0] + matrix[j][0], j) for j in range(1, n))
    reversed_order = []
    mask = full
    while last != 0:
        reversed_order.append(last)
        _, prev = dp[(mask, last)]
        mask ^= 1 << (last - 1)
        last = prev
    route = [0, *reversed_order[::-1], 0]
    return route, total, states


ALGORITHMS = {
    'Brute Force (exact)': brute_force,
    'Held-Karp (exact)': held_karp,
    'Nearest Neighbor (greedy)': nearest_neighbor,
    'Nearest Neighbor + 2-Opt': nearest_neighbor_two_opt,
}

ALGORITHM_COLORS = {
    'Brute Force (exact)': '#3B82F6',
    'Held-Karp (exact)': '#22C55E',
    'Nearest Neighbor (greedy)': '#F59E0B',
    'Nearest Neighbor + 2-Opt': '#EF4444',
}

ALGORITHM_SHORT = {
    'Brute Force (exact)': 'Brute Force',
    'Held-Karp (exact)': 'Held-Karp',
    'Nearest Neighbor (greedy)': 'Nearest Neighbor',
    'Nearest Neighbor + 2-Opt': 'NN + 2-Opt',
}

BRUTE_FORCE_MAX_STOPS = 9
HELD_KARP_MAX_STOPS = 16

# Counters are algorithm-specific and must not be ranked against each other.
WORK_COUNTER_UNITS = {
    'Brute Force (exact)': 'permutations evaluated',
    'Held-Karp (exact)': 'DP states evaluated',
    'Nearest Neighbor (greedy)': 'candidates examined',
    'Nearest Neighbor + 2-Opt': 'NN candidate checks + 2-Opt evaluations',
}


def compare(matrix, selected=None):
    """Run selected TSP algorithms on a road-distance matrix (meters).

    matrix length includes the depot, so deliveries = len(matrix) - 1.
    """
    import tracemalloc
    results = []
    deliveries = len(matrix) - 1
    for name, fn in ALGORITHMS.items():
        if selected is not None and name not in selected:
            continue
        # Exact methods are intentionally capped to keep the demo responsive.
        if name.startswith('Brute Force') and deliveries > BRUTE_FORCE_MAX_STOPS:
            continue
        if name.startswith('Held-Karp') and deliveries > HELD_KARP_MAX_STOPS:
            continue
        detail = None
        tracemalloc.start()
        start = time.perf_counter()
        if name.startswith('Nearest Neighbor + 2-Opt'):
            route, distance, operations, detail = nearest_neighbor_two_opt(matrix, record_swaps=True)
        else:
            route, distance, operations = fn(matrix)
        elapsed = (time.perf_counter() - start) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        work_unit = WORK_COUNTER_UNITS.get(name, 'algorithm-specific units')
        row = {
            'Algorithm': name,
            'Distance (km)': round(distance / 1000, 3),
            'Runtime (ms)': round(elapsed, 4),
            'Operations / states': operations,
            'Algorithm-Specific Work Counter': operations,
            'Work unit': work_unit,
            'Route': route,
            'distance_m': distance,
            'Peak memory (KB)': round(peak / 1024, 2),
            'Color': ALGORITHM_COLORS[name],
            'Short name': ALGORITHM_SHORT[name],
            'exact': '(exact)' in name,
        }
        if detail is not None:
            row['Initial distance (km)'] = round(detail['initial_distance_m'] / 1000, 3)
            row['2-Opt swaps'] = detail['swap_count']
            row['2-Opt history'] = detail['swaps']
            row['Initial route'] = detail['initial_route']
        results.append(row)
    return results


def optimality_gaps(results):
    """Attach optimality gaps using the best exact distance when available."""
    exact = [row['distance_m'] for row in results if row.get('exact')]
    optimal = min(exact) if exact else None
    for row in results:
        if optimal is None:
            row['Optimality gap (%)'] = None
        elif optimal == 0:
            # Avoid divide-by-zero; a zero-length optimum only matches zero-length tours.
            row['Optimality gap (%)'] = 0.0 if row['distance_m'] == 0 else None
        else:
            row['Optimality gap (%)'] = round(100 * (row['distance_m'] / optimal - 1), 2)
    return results
