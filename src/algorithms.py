"""Student-readable routing algorithms for FastRoute.

Compared solvers:
1. A* Search — shortest road paths with a geographic heuristic
2. Dijkstra — shortest road paths with a binary heap
3. Brute-Force Route Search — exact delivery-order search on a road-distance matrix

Each family also has Bad → Semi → Best optimization tiers (see optimization_ladder).
"""
import heapq
import itertools
import math
import random
import time
from .constants import (
    BRUTE_FORCE_EXACT_MAX_STOPS,
    BRUTE_FORCE_MAX_STOPS,
    BRUTE_FORCE_SAMPLE_BUDGET,
)


def dijkstra_naive(graph, source, target=None, early_stop=False):
    """Bad / baseline Dijkstra: repeated linear scan for the unsettled minimum.

    Same shortest-path answers as heap Dijkstra on nonnegative graphs, but
    extract-min is O(V) each step → about O(V² + E). When early_stop is False
    (default for the Bad tier), the search does not stop at the target.
    """
    nodes = set(graph)
    for u, edges in graph.items():
        nodes.add(u)
        for v, _weight in edges:
            nodes.add(v)
    distances = {source: 0.0}
    previous = {}
    unsettled = set(nodes)
    explored = 0
    while unsettled:
        node = min(unsettled, key=lambda n: distances.get(n, math.inf))
        if distances.get(node, math.inf) == math.inf:
            break
        unsettled.remove(node)
        explored += 1
        if early_stop and target is not None and node == target:
            break
        for neighbor, weight in graph.get(node, []):
            if weight < 0:
                raise ValueError('Dijkstra requires nonnegative weights')
            candidate = distances[node] + weight
            if candidate < distances.get(neighbor, math.inf):
                distances[neighbor] = candidate
                previous[neighbor] = node
    return distances, previous, explored


def dijkstra(graph, source, target=None, record_steps=False):
    """Semi / course Dijkstra: binary heap + stop when the target is settled.

    graph: {node: [(neighbor, weight), ...]}
    Complexity: O((V+E) log V) with a binary heap.
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


def reverse_adjacency(graph):
    """Build reverse adjacency for bidirectional search."""
    rev = {}
    for u, edges in graph.items():
        for v, weight in edges:
            rev.setdefault(v, []).append((u, weight))
    return rev


def dijkstra_bidirectional(graph, source, target, reverse_graph=None):
    """Best Dijkstra tier: bidirectional heap search on a directed graph.

    Expands forward from source and backward from target on the reverse
    adjacency list, tracking the best meeting node. Falls back to ordinary
    Dijkstra if the searches do not meet (should not happen on an SCC tour).
    """
    if source == target:
        return {source: 0.0}, {}, 0
    rev = reverse_graph if reverse_graph is not None else reverse_adjacency(graph)

    dist_f = {source: 0.0}
    dist_b = {target: 0.0}
    prev_f = {}
    prev_b = {}
    heap_f = [(0.0, source)]
    heap_b = [(0.0, target)]
    settled_f = set()
    settled_b = set()
    best = math.inf
    meet = None
    explored = 0

    def consider_meet(node):
        nonlocal best, meet
        if node in dist_f and node in dist_b:
            total = dist_f[node] + dist_b[node]
            if total < best:
                best = total
                meet = node

    def expand(heap, dist, prev, settled, other_settled, adj):
        nonlocal explored
        while heap:
            distance, node = heapq.heappop(heap)
            if node in settled or distance > dist.get(node, math.inf):
                continue
            settled.add(node)
            explored += 1
            consider_meet(node)
            for neighbor, weight in adj.get(node, []):
                if weight < 0:
                    raise ValueError('Dijkstra requires nonnegative weights')
                candidate = distance + weight
                if candidate < dist.get(neighbor, math.inf):
                    dist[neighbor] = candidate
                    prev[neighbor] = node
                    heapq.heappush(heap, (candidate, neighbor))
                    consider_meet(neighbor)
            return True
        return False

    while heap_f and heap_b:
        # Expand the side whose next unsettled key is smaller.
        next_f = heap_f[0][0]
        next_b = heap_b[0][0]
        if next_f <= next_b:
            expand(heap_f, dist_f, prev_f, settled_f, settled_b, graph)
        else:
            expand(heap_b, dist_b, prev_b, settled_b, settled_f, rev)

        top_f = heap_f[0][0] if heap_f else math.inf
        top_b = heap_b[0][0] if heap_b else math.inf
        # Only stop after both searches have a real meeting candidate and the
        # remaining frontier cannot improve it.
        if meet is not None and top_f + top_b >= best and settled_f and settled_b:
            # Require the meeting node to be settled on at least one side.
            if meet in settled_f or meet in settled_b:
                break

    if meet is None or best == math.inf:
        return dijkstra(graph, source, target)

    left = reconstruct(prev_f, source, meet)
    right = reconstruct(prev_b, target, meet)
    if not left or not right:
        return dijkstra(graph, source, target)
    path = left + list(reversed(right))[1:]
    previous = {b: a for a, b in zip(path, path[1:])}
    distances = {source: 0.0}
    running = 0.0
    for a, b in zip(path, path[1:]):
        weight = None
        for nxt, w in graph.get(a, []):
            if nxt == b:
                weight = w
                break
        if weight is None:
            return dijkstra(graph, source, target)
        running += weight
        distances[b] = running
    if abs(distances.get(target, math.inf) - best) > 1e-6:
        # Inconsistent stitch — trust unidirectional Dijkstra.
        return dijkstra(graph, source, target)
    return distances, previous, explored


def astar(graph, source, target, heuristic, record_steps=False):
    """A* shortest path on a directed nonnegative-weight adjacency list.

    heuristic(node) must be an admissible estimate of remaining road distance to target.
    Complexity: O((V+E) log V) with a binary heap in the common case.
    """
    if source == target:
        if record_steps:
            return {source: 0.0}, {}, 0, []
        return {source: 0.0}, {}, 0

    g_score = {source: 0.0}
    previous = {}
    heap = [(heuristic(source), 0.0, source)]
    explored = 0
    closed = set()
    steps = []

    while heap:
        f_score, distance, node = heapq.heappop(heap)
        if node in closed:
            continue
        if distance > g_score.get(node, math.inf):
            continue
        closed.add(node)
        explored += 1
        if record_steps:
            steps.append({
                'event': 'settle',
                'node': node,
                'distance': distance,
                'f_score': f_score,
                'explored': explored,
            })
        if node == target:
            break
        for neighbor, weight in graph.get(node, []):
            if weight < 0:
                raise ValueError('A* requires nonnegative weights')
            candidate = distance + weight
            if candidate < g_score.get(neighbor, math.inf):
                g_score[neighbor] = candidate
                previous[neighbor] = node
                estimate = candidate + heuristic(neighbor)
                heapq.heappush(heap, (estimate, candidate, neighbor))
                if record_steps:
                    steps.append({
                        'event': 'relax',
                        'from': node,
                        'to': neighbor,
                        'distance': candidate,
                        'f_score': estimate,
                        'explored': explored,
                    })

    if record_steps:
        return g_score, previous, explored, steps
    return g_score, previous, explored


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


def brute_force_route_search(matrix, max_permutations=None, seed=42, meta_out=None):
    """Delivery-order search; depot index 0; return to depot.

    Small instances (≤ BRUTE_FORCE_EXACT_MAX_STOPS deliveries) enumerate every
    permutation and are exact. Larger / budgeted instances use **streaming
    sampling with replacement**: seeded shuffles evaluated one-at-a-time while
    retaining only the best route (auxiliary search space O(n), excluding the
    O(n²) distance matrix). Repeated draws are allowed; uniqueness is not claimed.

    Returns (route, cost_m, examined, exact).
    If meta_out is a dict, it is filled with search diagnostics.
    """
    n = len(matrix)
    if n <= 1:
        if meta_out is not None:
            meta_out.clear()
            meta_out.update({
                'search_mode': 'exact',
                'sampling_budget': 1,
                'candidate_evaluations': 1,
                'exact': True,
                'seed': seed,
                'unique_permutations_tracked': False,
            })
        return [0, 0], 0.0, 1, True

    deliveries = n - 1
    budget = BRUTE_FORCE_SAMPLE_BUDGET if max_permutations is None else max_permutations
    if budget < 1:
        raise ValueError('max_permutations must be at least 1')

    best_cost = math.inf
    best_route = None
    examined = 0

    def consider(order):
        nonlocal best_cost, best_route, examined
        route = [0, *order, 0]
        cost = route_cost(matrix, route)
        examined += 1
        if cost < best_cost:
            best_cost = cost
            best_route = route

    # Always score the identity / sample order first.
    identity = list(range(1, n))
    consider(identity)

    total_orders = math.factorial(deliveries)
    # Default small instances always enumerate fully. An explicit tighter
    # max_permutations budget forces sampled mode even on tiny matrices.
    if max_permutations is None and deliveries <= BRUTE_FORCE_EXACT_MAX_STOPS:
        use_exact = True
    else:
        use_exact = total_orders <= budget
    if use_exact:
        for order in itertools.permutations(range(1, n)):
            if list(order) == identity:
                continue
            consider(order)
        if meta_out is not None:
            meta_out.clear()
            meta_out.update({
                'search_mode': 'exact',
                'sampling_budget': examined,
                'candidate_evaluations': examined,
                'exact': True,
                'seed': seed,
                'unique_permutations_tracked': True,
            })
        return best_route, best_cost, examined, True

    # Streaming sampled mode: O(B×n) scoring time, O(n) auxiliary search space.
    # No budget-sized `seen` set — sampling with replacement / repeated random draws.
    rng = random.Random(seed)
    deliveries_list = list(range(1, n))
    while examined < budget:
        rng.shuffle(deliveries_list)
        consider(list(deliveries_list))
    if meta_out is not None:
        meta_out.clear()
        meta_out.update({
            'search_mode': 'sampled_with_replacement',
            'sampling_budget': budget,
            'candidate_evaluations': examined,
            'exact': False,
            'seed': seed,
            'unique_permutations_tracked': False,
        })
    return best_route, best_cost, examined, False


def brute_force(matrix, max_permutations=None, seed=42):
    """Backwards-compatible wrapper returning (route, cost, examined)."""
    route, cost, examined, _exact = brute_force_route_search(
        matrix, max_permutations=max_permutations, seed=seed
    )
    return route, cost, examined


def sequential_route_order(stop_count):
    """Warehouse → stops in sample order → warehouse."""
    if stop_count <= 0:
        return [0, 0]
    return [0, *range(1, stop_count), 0]


def haversine_heuristic(graph, target):
    """Admissible straight-line heuristic in meters for A* on OSM nodes.

    Edge lengths must be in meters and never shorter than the geographic chord
    between their endpoints (true for normal OSM road lengths).
    """
    target_lat = float(graph.nodes[target]['y'])
    target_lon = float(graph.nodes[target]['x'])
    radius = 6_371_000.0

    def heuristic(node):
        data = graph.nodes[node]
        lat = float(data['y'])
        lon = float(data['x'])
        phi1, phi2 = math.radians(lat), math.radians(target_lat)
        d_phi = math.radians(target_lat - lat)
        d_lambda = math.radians(target_lon - lon)
        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        return 2 * radius * math.asin(min(1.0, math.sqrt(a)))

    return heuristic


def haversine_heuristic_cached(graph, target, coord_cache=None, value_cache=None):
    """Same admissible haversine heuristic with precomputed radians + per-target cache.

    Used by A* Best: identical distances to Semi, less repeated trig work.
    """
    radius = 6_371_000.0
    if coord_cache is None:
        coord_cache = {}
        for node, data in graph.nodes(data=True):
            coord_cache[node] = (math.radians(float(data['y'])), math.radians(float(data['x'])))
    if target not in coord_cache:
        data = graph.nodes[target]
        coord_cache[target] = (math.radians(float(data['y'])), math.radians(float(data['x'])))
    phi2, lam2 = coord_cache[target]
    if value_cache is None:
        value_cache = {}
    target_bucket = value_cache.setdefault(target, {})

    def heuristic(node, _bucket=target_bucket, _phi2=phi2, _lam2=lam2):
        cached = _bucket.get(node)
        if cached is not None:
            return cached
        phi1, lam1 = coord_cache[node]
        d_phi = _phi2 - phi1
        d_lambda = _lam2 - lam1
        a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(_phi2) * math.sin(d_lambda / 2) ** 2
        value = 2 * radius * math.asin(min(1.0, math.sqrt(a)))
        _bucket[node] = value
        return value

    return heuristic, coord_cache, value_cache


def zero_heuristic(_node):
    """Admissible but uninformed heuristic — A* Bad tier (behaves like Dijkstra)."""
    return 0.0


def tour_with_pathfinder(adjacency, graph, stops, order, pathfinder, reverse_graph=None):
    """Build a closed tour using Dijkstra or A* variants for every stop pair."""
    total = 0.0
    explored = 0
    node_paths = []
    rev = reverse_graph
    coord_cache = None
    value_cache = None
    for a, b in zip(order, order[1:]):
        source = stops[a]
        target = stops[b]
        if pathfinder == 'dijkstra_naive':
            # Early-stop keeps demos responsive; extract-min is still the slow O(V) scan.
            distances, previous, ops = dijkstra_naive(adjacency, source, target, early_stop=True)
        elif pathfinder == 'dijkstra':
            distances, previous, ops = dijkstra(adjacency, source, target)
        elif pathfinder == 'dijkstra_bidirectional':
            if rev is None:
                rev = reverse_adjacency(adjacency)
            distances, previous, ops = dijkstra_bidirectional(adjacency, source, target, rev)
        elif pathfinder == 'astar_zero':
            distances, previous, ops = astar(adjacency, source, target, zero_heuristic)
        elif pathfinder == 'astar':
            distances, previous, ops = astar(
                adjacency, source, target, haversine_heuristic(graph, target)
            )
        elif pathfinder == 'astar_cached':
            heuristic, coord_cache, value_cache = haversine_heuristic_cached(
                graph, target, coord_cache=coord_cache, value_cache=value_cache
            )
            distances, previous, ops = astar(adjacency, source, target, heuristic)
        else:
            raise ValueError(f'Unknown pathfinder: {pathfinder}')
        if target not in distances:
            raise ValueError('No road route between selected stops')
        path = reconstruct(previous, source, target)
        if not path:
            raise ValueError('No road route between selected stops')
        total += distances[target]
        explored += ops
        node_paths.append(path)
    return order, total, explored, node_paths


ALGORITHMS = {
    'A* Search Algorithm': 'astar',
    "Dijkstra's Algorithm": 'dijkstra',
    'Brute-Force Route Search': 'brute_force',
}

ALGORITHM_COLORS = {
    'A* Search Algorithm': '#22C55E',
    "Dijkstra's Algorithm": '#F59E0B',
    'Brute-Force Route Search': '#3B82F6',
}

ALGORITHM_SHORT = {
    'A* Search Algorithm': 'A*',
    "Dijkstra's Algorithm": 'Dijkstra',
    'Brute-Force Route Search': 'Brute Force',
}

WORK_COUNTER_UNITS = {
    'A* Search Algorithm': 'nodes settled by A*',
    "Dijkstra's Algorithm": 'nodes settled by Dijkstra',
    'Brute-Force Route Search': 'permutations evaluated',
}


def compare(graph, stops, adjacency, matrix, selected=None, place=None):
    """Run A*, Dijkstra, and/or Brute-Force Route Search on the same stops.

    - Dijkstra and A* follow the sampled stop order and differ in path search.
    - Brute-Force Route Search searches delivery orders on the Dijkstra matrix.
    """
    import tracemalloc

    results = []
    deliveries = len(stops) - 1
    sample_order = sequential_route_order(len(stops))
    pid = problem_identity(stops, place=place)

    for name in ALGORITHMS:
        if selected is not None and name not in selected:
            continue
        if name == 'Brute-Force Route Search' and deliveries > BRUTE_FORCE_MAX_STOPS:
            continue

        tracemalloc.start()
        start = time.perf_counter()
        node_paths = None
        exact = False
        bf_meta = {}
        if name == 'Brute-Force Route Search':
            if matrix is None:
                continue
            route, distance, operations, exact = brute_force_route_search(matrix, meta_out=bf_meta)
        elif name == "Dijkstra's Algorithm":
            route, distance, operations, node_paths = tour_with_pathfinder(
                adjacency, graph, stops, sample_order, 'dijkstra'
            )
        else:
            route, distance, operations, node_paths = tour_with_pathfinder(
                adjacency, graph, stops, sample_order, 'astar'
            )
        elapsed = (time.perf_counter() - start) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        row = {
            'Algorithm': name,
            'Distance (km)': round(distance / 1000, 3),
            'Runtime (ms)': round(elapsed, 4),
            'Operations / states': operations,
            'Algorithm-Specific Work Counter': operations,
            'Work unit': WORK_COUNTER_UNITS[name],
            'Route': route,
            'distance_m': distance,
            'Peak memory (KB)': round(peak / 1024, 2),
            'Color': ALGORITHM_COLORS[name],
            'Short name': ALGORITHM_SHORT[name],
            'exact': bool(exact) if name == 'Brute-Force Route Search' else False,
            'pathfinder': ALGORITHMS[name],
            'node_paths': node_paths,
            'problem_id': pid,
            'status': 'ok',
            'search_mode': bf_meta.get('search_mode') if name == 'Brute-Force Route Search' else 'shortest_path_tour',
            'sampling_budget': bf_meta.get('sampling_budget') if name == 'Brute-Force Route Search' else None,
        }
        if name == 'Brute-Force Route Search' and not exact:
            row['Work unit'] = 'candidate evaluations (sampled, with replacement)'
        results.append(row)
    return results


def problem_identity(stops, *, place=None, edge_weight='length_m', objective='road_distance'):
    """Fingerprint for delivery-order optimality comparisons on one fixed instance."""
    return {
        'place': place,
        'depot': stops[0] if stops else None,
        'ordered_delivery_nodes': list(stops[1:]) if stops and len(stops) > 1 else [],
        'stop_nodes': list(stops) if stops else [],
        'edge_weight': edge_weight,
        'objective': objective,
        'n_stops': len(stops) if stops else 0,
    }


def optimality_gaps(results, *, problem_id=None, require_same_problem=True):
    """Attach delivery-order optimality gaps only when exhaustive BF is available.

    Dijkstra/A* shortest paths being optimal does **not** make their tour order
    globally optimal. Gaps use exhaustive Brute-Force Route Search on the same
    problem identity only. Missing gaps stay None (never displayed as 0%).
    """
    if problem_id is not None:
        for row in results:
            row.setdefault('problem_id', problem_id)

    exact_refs = [
        row for row in results
        if row.get('exact') and row.get('Algorithm') == 'Brute-Force Route Search'
    ]
    if require_same_problem and problem_id is not None:
        exact_refs = [
            row for row in exact_refs
            if row.get('problem_id') in (None, problem_id)
        ]

    optimal = min((row['distance_m'] for row in exact_refs), default=None)
    for row in results:
        status = row.get('optimality_status')
        if row.get('status') in ('skipped', 'failed'):
            row['Optimality gap (%)'] = None
            row['optimality_status'] = row.get('status')
            continue
        if optimal is None:
            if row.get('Algorithm') == 'Brute-Force Route Search' and not row.get('exact'):
                row['Optimality gap (%)'] = None
                row['optimality_status'] = 'sampled_search_only'
            else:
                row['Optimality gap (%)'] = None
                row['optimality_status'] = 'exact_reference_unavailable'
            continue
        if optimal == 0:
            gap = 0.0 if row['distance_m'] == 0 else None
        else:
            gap = round(100 * (row['distance_m'] / optimal - 1), 2)
        if gap is not None and gap < -1e-6:
            row['Optimality gap (%)'] = gap
            row['optimality_status'] = 'comparability_error_negative_gap'
        else:
            row['Optimality gap (%)'] = gap
            row['optimality_status'] = 'exact_reference_available'
        if status:
            row['optimality_status'] = status
    return results
