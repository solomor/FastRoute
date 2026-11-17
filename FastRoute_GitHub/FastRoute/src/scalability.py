"""Interactive scalability experiments using measured solver timings only."""
import csv
import statistics
import time
import tracemalloc
from pathlib import Path
from .algorithms import (
    ALGORITHMS,
    ALGORITHM_SHORT,
    BRUTE_FORCE_MAX_STOPS,
    HELD_KARP_MAX_STOPS,
    nearest_neighbor_two_opt,
)
from .road_data import distance_matrix, sample_stops

DEFAULT_COUNTS = [4, 6, 8, 10, 12, 14, 16]
RESULTS_DIR = Path(__file__).resolve().parents[1] / 'results'
UNAVAILABLE = 'unavailable'


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
    """Benchmark algorithms across delivery counts on one fixed OSM graph.

    For each delivery count, all applicable algorithms share the same stop sample
    and Dijkstra distance matrix. Solver runtime excludes download and matrix build.
    """
    counts = counts or DEFAULT_COUNTS
    selected = selected or list(ALGORITHMS)
    rows = []
    for deliveries in counts:
        stops = sample_stops(graph, deliveries + 1, seed=seed)
        matrix = distance_matrix(graph, stops)
        batch = []
        exact_distances = []
        for name in ALGORITHMS:
            if name not in selected:
                continue
            short = ALGORITHM_SHORT[name]
            skipped = None
            if name.startswith('Brute Force') and deliveries > BRUTE_FORCE_MAX_STOPS:
                skipped = f'Brute Force capped at {BRUTE_FORCE_MAX_STOPS} deliveries'
            elif name.startswith('Held-Karp') and deliveries > HELD_KARP_MAX_STOPS:
                skipped = f'Held-Karp capped at {HELD_KARP_MAX_STOPS} deliveries'
            if skipped:
                batch.append(_empty_metrics(deliveries, name, short, trials, skipped))
                continue
            runtimes = []
            distances = []
            memories = []
            operations = []
            last_distance_m = None
            for _ in range(trials):
                tracemalloc.start()
                start = time.perf_counter()
                if name.startswith('Nearest Neighbor + 2-Opt'):
                    route, distance, ops = nearest_neighbor_two_opt(matrix, record_swaps=False)
                else:
                    route, distance, ops = ALGORITHMS[name](matrix)
                elapsed = (time.perf_counter() - start) * 1000
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                runtimes.append(elapsed)
                distances.append(distance / 1000)
                memories.append(peak / 1024)
                operations.append(ops)
                last_distance_m = distance
            if '(exact)' in name and last_distance_m is not None:
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
                'exact': '(exact)' in name,
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
                row['optimality_gap_note'] = 'measured against exact solvers on same matrix'
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
