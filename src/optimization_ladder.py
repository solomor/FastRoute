"""Bad → Semi → Best optimization tiers for each FastRoute algorithm family.

Scientific rules:
- Dijkstra / A* tiers share the same graph, depot, stops, delivery order, and weights.
- A* Best may only optimize heuristic evaluation (cache), never change stop order.
- Brute-Force tiers use nested sampling budgets with one seed (Best ⊇ Semi ⊇ Bad).
- Reverse adjacency for bidirectional Dijkstra is built once per ladder run and reused.
"""
import time
import tracemalloc
from .algorithms import (
    brute_force_route_search,
    reverse_adjacency,
    sequential_route_order,
    tour_with_pathfinder,
)
from .constants import (
    BRUTE_FORCE_BAD_BUDGET,
    BRUTE_FORCE_BEST_BUDGET,
    BRUTE_FORCE_EXACT_MAX_STOPS,
    BRUTE_FORCE_SEMI_BUDGET,
)
from .road_data import distance_matrix, to_adjacency

TIER_ORDER = ('Bad', 'Semi', 'Best')

TIER_COLORS = {
    'Bad': '#EF4444',
    'Semi': '#F59E0B',
    'Best': '#22C55E',
}

# What each tier changes (shown in the UI / paper pack).
LADDER_SPECS = {
    "Dijkstra's Algorithm": {
        'Bad': {
            'pathfinder': 'dijkstra_naive',
            'label': 'Dijkstra Bad — linear-scan extract-min (O(V²) style)',
            'work_unit': 'nodes settled (naive Dijkstra)',
        },
        'Semi': {
            'pathfinder': 'dijkstra',
            'label': 'Dijkstra Semi — binary heap + stop at target',
            'work_unit': 'nodes settled (heap Dijkstra)',
        },
        'Best': {
            'pathfinder': 'dijkstra_bidirectional',
            'label': 'Dijkstra Best — bidirectional binary-heap search',
            'work_unit': 'nodes settled (bidirectional Dijkstra)',
        },
    },
    'A* Search Algorithm': {
        'Bad': {
            'pathfinder': 'astar_zero',
            'label': 'A* Bad — heuristic = 0 (uninformed), same sample order',
            'work_unit': 'nodes settled (A* h=0)',
        },
        'Semi': {
            'pathfinder': 'astar',
            'label': 'A* Semi — haversine heuristic, same sample order',
            'work_unit': 'nodes settled (A* haversine)',
        },
        'Best': {
            'pathfinder': 'astar_cached',
            'label': 'A* Best — cached haversine heuristic, same sample order',
            'work_unit': 'nodes settled (A* cached haversine)',
        },
    },
    'Brute-Force Route Search': {
        'Bad': {
            'budget': BRUTE_FORCE_BAD_BUDGET,
            'label': (
                f'Brute Force Bad — nested sample ≤ {BRUTE_FORCE_BAD_BUDGET:,} orders '
                f'(same seed; quality via budget, not speed)'
            ),
            'work_unit': 'permutations evaluated',
        },
        'Semi': {
            'budget': BRUTE_FORCE_SEMI_BUDGET,
            'label': (
                f'Brute Force Semi — exact ≤ {BRUTE_FORCE_EXACT_MAX_STOPS} deliveries, '
                f'else nested sample ≤ {BRUTE_FORCE_SEMI_BUDGET:,} (extends Bad)'
            ),
            'work_unit': 'permutations evaluated',
        },
        'Best': {
            'budget': BRUTE_FORCE_BEST_BUDGET,
            'label': (
                f'Brute Force Best — exact ≤ {BRUTE_FORCE_EXACT_MAX_STOPS}, else nested '
                f'sample ≤ {BRUTE_FORCE_BEST_BUDGET:,} (extends Semi; same seed)'
            ),
            'work_unit': 'permutations evaluated',
        },
    },
}


def _short(family):
    return {
        "Dijkstra's Algorithm": 'Dijkstra',
        'A* Search Algorithm': 'A*',
        'Brute-Force Route Search': 'BF',
    }[family]


def _run_pathfinder_tier(graph, stops, adjacency, order, family, tier, reverse_graph):
    spec = LADDER_SPECS[family][tier]
    tracemalloc.start()
    start = time.perf_counter()
    route, distance, operations, node_paths = tour_with_pathfinder(
        adjacency,
        graph,
        stops,
        order,
        spec['pathfinder'],
        reverse_graph=reverse_graph,
    )
    elapsed = (time.perf_counter() - start) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        'family': family,
        'tier': tier,
        'label': spec['label'],
        'Algorithm': f'{family} ({tier})',
        'Short name': f'{_short(family)} {tier}',
        'Distance (km)': round(distance / 1000, 3),
        'Runtime (ms)': round(elapsed, 4),
        'Operations / states': operations,
        'Algorithm-Specific Work Counter': operations,
        'Work unit': spec['work_unit'],
        'Route': route,
        'distance_m': distance,
        'Peak memory (KB)': round(peak / 1024, 2),
        'Color': TIER_COLORS[tier],
        'exact': False,
        'pathfinder': spec['pathfinder'],
        'node_paths': node_paths,
        'settings_label': spec['label'],
        'search_mode': 'shortest_path_tour',
        'status': 'ok',
        'sampling_budget': None,
        'reverse_adjacency_reused': reverse_graph is not None,
    }


def _run_brute_tier(matrix, family, tier, seed):
    spec = LADDER_SPECS[family][tier]
    deliveries = len(matrix) - 1
    meta = {}
    tracemalloc.start()
    start = time.perf_counter()
    if deliveries <= BRUTE_FORCE_EXACT_MAX_STOPS and tier in ('Semi', 'Best'):
        route, distance, ops, exact = brute_force_route_search(matrix, seed=seed, meta_out=meta)
        search_mode = 'exact'
        budget = ops
    else:
        route, distance, ops, exact = brute_force_route_search(
            matrix, max_permutations=spec['budget'], seed=seed, meta_out=meta
        )
        search_mode = meta.get('search_mode', 'sampled_with_replacement')
        budget = spec['budget']
    elapsed = (time.perf_counter() - start) * 1000
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        'family': family,
        'tier': tier,
        'label': spec['label'],
        'Algorithm': f'{family} ({tier})',
        'Short name': f'{_short(family)} {tier}',
        'Distance (km)': round(distance / 1000, 3),
        'Runtime (ms)': round(elapsed, 4),
        'Operations / states': ops,
        'Algorithm-Specific Work Counter': ops,
        'Work unit': spec['work_unit'] if exact else 'candidate evaluations (sampled, with replacement)',
        'Route': route,
        'distance_m': distance,
        'Peak memory (KB)': round(peak / 1024, 2),
        'Color': TIER_COLORS[tier],
        'exact': bool(exact),
        'pathfinder': 'brute_force',
        'node_paths': None,
        'settings_label': spec['label'],
        'search_mode': search_mode,
        'status': 'ok',
        'sampling_budget': budget,
        'seed': seed,
        'unique_permutations_tracked': bool(meta.get('unique_permutations_tracked')),
        'budget_note': (
            'Larger BF budgets trade more work for potentially better route quality; '
            'they are not claimed as faster algorithms.'
        ),
    }


def run_optimization_ladder(graph, stops, matrix=None, families=None, seed=42):
    """Run Bad/Semi/Best for each selected algorithm family on the same stops."""
    families = families or list(LADDER_SPECS)
    adjacency = to_adjacency(graph)
    # Built once and reused for Dijkstra Best (documented preprocessing cost separate).
    reverse_prep_start = time.perf_counter()
    reverse_graph = reverse_adjacency(adjacency)
    reverse_prep_ms = (time.perf_counter() - reverse_prep_start) * 1000
    shared_order = sequential_route_order(len(stops))

    needs_matrix = 'Brute-Force Route Search' in families
    if needs_matrix and matrix is None:
        matrix = distance_matrix(graph, stops)

    rows = []
    for family in families:
        if family not in LADDER_SPECS:
            raise ValueError(f'Unknown ladder family: {family}')
        for tier in TIER_ORDER:
            if family == 'Brute-Force Route Search':
                row = _run_brute_tier(matrix, family, tier, seed)
            else:
                row = _run_pathfinder_tier(
                    graph, stops, adjacency, shared_order, family, tier, reverse_graph
                )
                if family == "Dijkstra's Algorithm" and tier == 'Best':
                    row['reverse_adjacency_prep_ms'] = round(reverse_prep_ms, 4)
                    row['reverse_adjacency_reused'] = True
            rows.append(row)
    return rows


def ladder_summary_table(rows):
    """Compact table for UI / CSV export."""
    out = []
    for row in rows:
        out.append({
            'Family': row['family'],
            'Tier': row['tier'],
            'Setting': row['label'],
            'Distance (km)': row['Distance (km)'],
            'Runtime (ms)': row['Runtime (ms)'],
            'Work counter': row['Algorithm-Specific Work Counter'],
            'Work unit': row['Work unit'],
            'Peak memory (KB)': row['Peak memory (KB)'],
            'Search mode': row.get('search_mode'),
            'Exact': row.get('exact'),
            'Sampling budget': row.get('sampling_budget'),
            'Status': row.get('status', 'ok'),
        })
    return out
