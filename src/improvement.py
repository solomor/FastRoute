"""Before/after improvement story using only approved algorithm families.

Before: original sample delivery order + Dijkstra shortest-path engine.
After: delivery order from Brute-Force Route Search + same Dijkstra engine.

Nearest-neighbor stop ordering is no longer used in the active improvement workflow
(it changed the combinatorial problem and was scientifically misleading as an
“A*/Dijkstra improvement”). Historical NN helpers remain below for archive tests only.
"""
import time
import tracemalloc
from .algorithms import (
    ALGORITHM_SHORT,
    WORK_COUNTER_UNITS,
    brute_force_route_search,
    sequential_route_order,
    tour_with_pathfinder,
)
from .constants import BRUTE_FORCE_EXACT_MAX_STOPS, BRUTE_FORCE_SAMPLE_BUDGET, LARGE_ROUTE_SIMPLIFY_STOPS
from .road_data import (
    apply_map_point_budget,
    distance_matrix,
    geographic_distance_m,
    route_distance_from_legs,
    stop_coordinates,
    street_legs_for_route,
    to_adjacency,
)

IMPROVED_COLOR = '#A78BFA'
BASELINE_COLOR = '#F59E0B'


def rank_algorithms(results, key='distance_m'):
    """Best first. Primary key then runtime."""
    return sorted(
        results,
        key=lambda row: (row.get(key, float('inf')), row.get('Runtime (ms)', float('inf'))),
    )


def middle_algorithm(results):
    """Return the middle-ranked result by distance (then runtime). Kept for UI compatibility."""
    if not results:
        return None
    ranked = rank_algorithms(results)
    return ranked[len(ranked) // 2]


def nearest_neighbor_order(matrix):
    """Historical helper only — not used by the active improvement workflow."""
    n = len(matrix)
    if n <= 1:
        return [0, 0]
    unvisited = set(range(1, n))
    route = [0]
    current = 0
    while unvisited:
        nxt = min(unvisited, key=lambda node: matrix[current][node])
        unvisited.remove(nxt)
        route.append(nxt)
        current = nxt
    route.append(0)
    return route


def geographic_nearest_neighbor_order(graph, stops):
    """Historical helper only — not used by the active improvement workflow."""
    n = len(stops)
    if n <= 1:
        return [0, 0]
    coords = stop_coordinates(graph, stops)
    unvisited = set(range(1, n))
    route = [0]
    current = 0
    while unvisited:
        cur_lat, cur_lon = coords[current]

        def score(node, lat0=cur_lat, lon0=cur_lon):
            lat, lon = coords[node]
            return geographic_distance_m(lat0, lon0, lat, lon)

        nxt = min(unvisited, key=score)
        unvisited.remove(nxt)
        route.append(nxt)
        current = nxt
    route.append(0)
    return route


def _coordinates_from_legs(legs):
    coords = []
    for index, leg in enumerate(legs):
        if index and leg:
            coords.extend(leg[1:])
        else:
            coords.extend(leg)
    return coords


def _attach_geometry(graph, stops, row, simplify_map):
    legs = street_legs_for_route(graph, stops, row['Route'], row.get('node_paths'))
    applied = False
    if simplify_map:
        legs, applied = apply_map_point_budget(legs)
    row['legs'] = legs
    row['coordinates'] = _coordinates_from_legs(legs)
    row['map_simplified'] = bool(applied)
    if row.get('node_paths') or simplify_map:
        row['Reconstructed distance (km)'] = row['Distance (km)']
        return row
    reconstructed = route_distance_from_legs(graph, stops, row['Route'])
    row['Reconstructed distance (km)'] = round(reconstructed / 1000, 3)
    return row


def _pathfinder_row(name, route, distance_m, runtime_ms, peak_bytes, operations, *, color, short, settings_label, node_paths, exact=False):
    return {
        'Algorithm': name,
        'Distance (km)': round(distance_m / 1000, 3),
        'Runtime (ms)': round(runtime_ms, 4),
        'Operations / states': operations,
        'Algorithm-Specific Work Counter': operations,
        'Work unit': WORK_COUNTER_UNITS.get(name, 'nodes settled'),
        'Route': route,
        'distance_m': distance_m,
        'Peak memory (KB)': round(peak_bytes / 1024, 2),
        'Color': color,
        'Short name': short,
        'exact': bool(exact),
        'pathfinder': 'dijkstra',
        'node_paths': node_paths,
        'settings_label': settings_label,
    }


def build_improvement_story(experiment, graph):
    """Original sample order (Dijkstra) vs BF-chosen order (Dijkstra), same graph/stops."""
    stops = experiment['stops']
    seed = int(experiment.get('seed') or 42)
    adjacency = to_adjacency(graph)
    sample_order = sequential_route_order(len(stops))
    simplify_map = bool(experiment.get('map_simplified')) or len(stops) > LARGE_ROUTE_SIMPLIFY_STOPS
    deliveries = max(0, len(stops) - 1)

    # --- Matrix prep (reported separately) ---
    matrix_start = time.perf_counter()
    matrix = experiment.get('matrix')
    if matrix is None:
        matrix = distance_matrix(graph, stops)
    matrix_prep_ms = (time.perf_counter() - matrix_start) * 1000

    # --- Before: sample order + Dijkstra ---
    tracemalloc.start()
    before_start = time.perf_counter()
    before_route, before_dist, before_ops, before_paths = tour_with_pathfinder(
        adjacency, graph, stops, sample_order, 'dijkstra'
    )
    before_path_ms = (time.perf_counter() - before_start) * 1000
    _, before_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    baseline = _pathfinder_row(
        "Dijkstra's Algorithm",
        before_route,
        before_dist,
        before_path_ms,
        before_peak,
        before_ops,
        color=BASELINE_COLOR,
        short='Dijkstra (original order)',
        settings_label='Before: original sample delivery order + Dijkstra shortest-path engine',
        node_paths=before_paths,
    )
    baseline = _attach_geometry(graph, stops, baseline, simplify_map)
    baseline['is_improved'] = False

    # --- Order search via Brute Force ---
    bf_meta = {}
    tracemalloc.start()
    search_start = time.perf_counter()
    if deliveries <= BRUTE_FORCE_EXACT_MAX_STOPS:
        bf_route, bf_cost, bf_ops, bf_exact = brute_force_route_search(
            matrix, seed=seed, meta_out=bf_meta
        )
        budget = bf_ops
    else:
        bf_route, bf_cost, bf_ops, bf_exact = brute_force_route_search(
            matrix, max_permutations=BRUTE_FORCE_SAMPLE_BUDGET, seed=seed, meta_out=bf_meta
        )
        budget = BRUTE_FORCE_SAMPLE_BUDGET
    search_ms = (time.perf_counter() - search_start) * 1000
    _, search_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # --- After: BF order + same Dijkstra engine ---
    tracemalloc.start()
    after_start = time.perf_counter()
    after_route, after_dist, after_ops, after_paths = tour_with_pathfinder(
        adjacency, graph, stops, bf_route, 'dijkstra'
    )
    after_path_ms = (time.perf_counter() - after_start) * 1000
    _, after_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # Sanity: matrix tour cost of BF order should match reconstructed Dijkstra tour closely.
    improved = _pathfinder_row(
        "Dijkstra's Algorithm",
        after_route,
        after_dist,
        after_path_ms,
        after_peak,
        after_ops,
        color=IMPROVED_COLOR,
        short='Dijkstra (BF order)',
        settings_label=(
            'After: Brute-Force Route Search delivery order + same Dijkstra shortest-path engine'
        ),
        node_paths=after_paths,
        exact=False,
    )
    improved = _attach_geometry(graph, stops, improved, simplify_map)
    improved['is_improved'] = True

    dist_delta_km = round(improved['Distance (km)'] - baseline['Distance (km)'], 3)
    if baseline['distance_m']:
        dist_delta_pct = round(100 * (improved['distance_m'] / baseline['distance_m'] - 1), 2)
    else:
        dist_delta_pct = None
    better_distance = improved['distance_m'] < baseline['distance_m'] - 1e-6
    end_to_end_ms = round(matrix_prep_ms + before_path_ms + search_ms + after_path_ms, 4)

    narrative = [
        '**Before:** original sample delivery order reconstructed with **Dijkstra** on the road graph.',
        '**After:** delivery order chosen by **Brute-Force Route Search**, then reconstructed with the '
        '**same Dijkstra** engine (same graph, depot, stops, edge weights).',
        f"Original route distance: **{baseline['Distance (km)']} km**.",
        f"Improved route distance: **{improved['Distance (km)']} km**.",
        f"Brute Force search mode: **{bf_meta.get('search_mode', 'unknown')}** · "
        f"exact={bf_exact} · budget/evaluations={budget:,} · seed={seed}.",
        f"Matrix BF tour cost: **{round(bf_cost / 1000, 3)} km** (order-search objective on the distance matrix).",
    ]
    if better_distance:
        narrative.append(
            f"Measured distance improvement: **{abs(dist_delta_km)} km**"
            + (f" ({abs(dist_delta_pct)}% shorter)." if dist_delta_pct is not None else ".")
        )
    elif abs(improved['distance_m'] - baseline['distance_m']) <= 1e-6:
        narrative.append(
            'Measured distance improvement: **0%** on this instance (BF order matched the sample order cost).'
        )
    else:
        narrative.append(
            f'Distance changed by {dist_delta_km} km on this instance (no improvement claimed).'
        )

    return {
        'baseline': baseline,
        'improved': improved,
        'rank_index': None,
        'ranked_names': ['Dijkstra original order', 'Brute Force order + Dijkstra'],
        'settings_label': improved['settings_label'],
        'distance_delta_km': dist_delta_km,
        'distance_delta_pct': dist_delta_pct,
        'runtime_delta_ms': round(after_path_ms - before_path_ms, 4),
        'improved_distance': better_distance,
        'narrative': narrative,
        'timings': {
            'original_pathfinding_ms': round(before_path_ms, 4),
            'route_search_ms': round(search_ms, 4),
            'improved_reconstruction_ms': round(after_path_ms, 4),
            'distance_matrix_prep_ms': round(matrix_prep_ms, 4),
            'total_end_to_end_ms': end_to_end_ms,
            'route_search_peak_kb': round(search_peak / 1024, 2),
        },
        'search': {
            'budget': budget,
            'exact': bool(bf_exact),
            'search_mode': bf_meta.get('search_mode'),
            'candidate_evaluations': bf_ops,
            'seed': seed,
            'matrix_tour_km': round(bf_cost / 1000, 3),
        },
        'experiment_type': 'dijkstra_order_vs_brute_force_order',
    }


def run_improved_variant(graph, stops, algorithm_name, matrix=None, seed=42):
    """Compatibility wrapper: always runs the Dijkstra↔BF order experiment."""
    del algorithm_name
    experiment = {
        'stops': stops,
        'matrix': matrix,
        'seed': seed,
        'map_simplified': len(stops) > LARGE_ROUTE_SIMPLIFY_STOPS,
        'results': [],
    }
    story = build_improvement_story(experiment, graph)
    return story['improved'], story['settings_label']
