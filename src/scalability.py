"""Interactive scalability experiments using measured solver timings only."""
import csv
import statistics
import time
import tracemalloc
from pathlib import Path
from .algorithms import (
    ALGORITHMS,
    ALGORITHM_SHORT,
    compare,
    optimality_gaps,
)
from .constants import BRUTE_FORCE_MAX_STOPS
from .road_data import distance_matrix, largest_scc_nodes, sample_stops, to_adjacency

# Multi-scale delivery counts for CPS 3440 experiments.
# Small n: exact BF meaningful. Medium: sampled BF + pathfinders. Large: pathfinders (matrix cost grows fast).
DEFAULT_COUNTS = [4, 6, 8, 9, 12, 16, 25, 50, 100, 1000]
# Stress sizes for A*/Dijkstra. 10k / 100k run only when the loaded road SCC is large enough.
LARGE_PATHFINDER_COUNTS = [1_000, 10_000, 100_000]
RESULTS_DIR = Path(__file__).resolve().parents[1] / 'results'
UNAVAILABLE = 'unavailable'
# Above this delivery count, skip Brute Force in scalability runs (matrix build dominates).
BRUTE_FORCE_SCALABILITY_MAX = 25


def max_delivery_capacity(graph):
    """Largest delivery count that can be sampled from the biggest SCC (warehouse + deliveries)."""
    scc = largest_scc_nodes(graph)
    return max(0, len(scc) - 1)


def available_scale_counts(graph, counts=None):
    """Keep only delivery counts the current road graph can actually support."""
    counts = list(counts or (DEFAULT_COUNTS + LARGE_PATHFINDER_COUNTS))
    capacity = max_delivery_capacity(graph)
    return [n for n in sorted(set(counts)) if n <= capacity]


def unavailable_scale_counts(graph, counts=None):
    counts = list(counts or LARGE_PATHFINDER_COUNTS)
    capacity = max_delivery_capacity(graph)
    return [
        {'deliveries': n, 'reason': f'Road SCC only supports ≤ {capacity} deliveries (need {n + 1} nodes)'}
        for n in sorted(set(counts))
        if n > capacity
    ]


def _empty_metrics(deliveries, name, short, trials, skipped):
    return {
        'deliveries': deliveries,
        'algorithm': name,
        'short_name': short,
        'status': 'skipped',
        'skip_reason': skipped,
        'trials': trials,
        'avg_runtime_ms': None,
        'min_runtime_ms': None,
        'max_runtime_ms': None,
        'avg_distance_km': None,
        'avg_peak_memory_kb': None,
        'avg_operations': None,
        'optimality_gap_percent': None,
        'optimality_gap_note': UNAVAILABLE,
    }


def run_scalability(graph, counts=None, trials=3, seed=42, selected=None):
    """Benchmark A*, Dijkstra, and Brute-Force Route Search across delivery counts."""
    counts = counts or DEFAULT_COUNTS
    selected = selected or list(ALGORITHMS)
    rows = []
    adjacency = to_adjacency(graph)
    capacity = max_delivery_capacity(graph)
    for deliveries in counts:
        if deliveries > capacity:
            reason = (
                f'Graph SCC supports ≤ {capacity} deliveries; '
                f'{deliveries} needs {deliveries + 1} mutually reachable nodes'
            )
            for name in ALGORITHMS:
                if name not in selected:
                    continue
                rows.append(_empty_metrics(deliveries, name, ALGORITHM_SHORT[name], trials, reason))
            continue
        # Large stress sizes: pathfinders only (BF matrix is impractical).
        active = list(selected)
        if deliveries >= 1_000:
            active = [name for name in active if name != 'Brute-Force Route Search'] or [
                'A* Search Algorithm',
                "Dijkstra's Algorithm",
            ]
        stops = sample_stops(graph, deliveries + 1, seed=seed)
        needs_matrix = (
            'Brute-Force Route Search' in active
            and deliveries <= BRUTE_FORCE_MAX_STOPS
            and deliveries <= BRUTE_FORCE_SCALABILITY_MAX
        )
        matrix = distance_matrix(graph, stops) if needs_matrix else None
        batch = []
        exact_distances = []
        for name in ALGORITHMS:
            if name not in selected:
                continue
            short = ALGORITHM_SHORT[name]
            skipped = None
            if name not in active and name == 'Brute-Force Route Search' and deliveries >= 1_000:
                skipped = 'Brute-Force skipped at ≥1000 deliveries in scalability (pathfinders only)'
            elif name == 'Brute-Force Route Search' and deliveries > BRUTE_FORCE_MAX_STOPS:
                skipped = f'Brute-Force Route Search capped at {BRUTE_FORCE_MAX_STOPS} deliveries'
            elif name == 'Brute-Force Route Search' and deliveries > BRUTE_FORCE_SCALABILITY_MAX:
                skipped = (
                    f'Brute-Force scalability skipped above {BRUTE_FORCE_SCALABILITY_MAX} deliveries '
                    '(full pairwise matrix build dominates; use A*/Dijkstra for large-n scaling)'
                )
            if skipped:
                batch.append(_empty_metrics(deliveries, name, short, trials, skipped))
                continue
            runtimes = []
            distances = []
            memories = []
            operations = []
            last_distance_m = None
            exact = False
            for _ in range(trials):
                tracemalloc.start()
                start = time.perf_counter()
                result_rows = compare(graph, stops, adjacency, matrix, selected=[name])
                elapsed = (time.perf_counter() - start) * 1000
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                row = result_rows[0]
                runtimes.append(elapsed)
                distances.append(row['distance_m'] / 1000)
                memories.append(peak / 1024)
                operations.append(row['Operations / states'])
                last_distance_m = row['distance_m']
                exact = bool(row.get('exact'))
            if exact and last_distance_m is not None:
                exact_distances.append(last_distance_m)
            batch.append({
                'deliveries': deliveries,
                'algorithm': name,
                'short_name': short,
                'status': 'ok',
                'skip_reason': None,
                'trials': trials,
                'avg_runtime_ms': round(statistics.mean(runtimes), 5),
                'min_runtime_ms': round(min(runtimes), 5),
                'max_runtime_ms': round(max(runtimes), 5),
                'avg_distance_km': round(statistics.mean(distances), 5),
                'avg_peak_memory_kb': round(statistics.mean(memories), 3),
                'avg_operations': round(statistics.mean(operations), 2),
                'distance_m': last_distance_m,
                'exact': exact,
                'optimality_gap_percent': None,
                'optimality_gap_note': UNAVAILABLE,
            })
        optimal = min(exact_distances) if exact_distances else None
        for row in batch:
            if row['status'] != 'ok':
                rows.append(row)
                continue
            if optimal is None:
                row['optimality_gap_percent'] = None
                row['optimality_gap_note'] = UNAVAILABLE
            else:
                gap = round(100 * (row['distance_m'] / optimal - 1), 2)
                row['optimality_gap_percent'] = gap
                row['optimality_gap_note'] = 'measured against Brute-Force Route Search on same matrix'
            row.pop('distance_m', None)
            row.pop('exact', None)
            rows.append(row)
    return rows


def save_scalability_csv(rows, path=None):
    path = Path(path) if path else RESULTS_DIR / 'scalability_results.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('No scalability rows to save')
    fieldnames = list(rows[0].keys())
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path
