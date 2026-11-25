"""Reproducible routing experiments on real OpenStreetMap roads.

Run: python -m benchmarks.run_benchmarks

Timing isolates each solver from graph download. For Brute-Force Route Search,
Dijkstra matrix construction is also excluded from solver runtime.
No hardcoded performance numbers are written — every row is measured.
"""
import csv
import statistics
import time
import tracemalloc
from pathlib import Path
from src.algorithms import (
    ALGORITHMS,
    ALGORITHM_SHORT,
    compare,
)
from src.constants import BRUTE_FORCE_MAX_STOPS
from src.road_data import PLACE, download_graph, sample_stops, distance_matrix, to_adjacency
from src.scalability import (
    BRUTE_FORCE_SCALABILITY_MAX,
    DEFAULT_COUNTS,
    LARGE_PATHFINDER_COUNTS,
    run_scalability,
    save_scalability_csv,
)

UNAVAILABLE = 'unavailable'


def run_offline_benchmark(place=PLACE, sizes=None, trials=5, seed=42):
    """Return measured rows for the offline CLI benchmark."""
    sizes = sizes or list(DEFAULT_COUNTS)
    graph = download_graph(place)
    adjacency = to_adjacency(graph)
    prep_note = (
        'OSM download/cache load is excluded from solver runtime. '
        'Dijkstra matrix construction is excluded from Brute-Force Route Search timing; '
        'A* and Dijkstra tour timings include their own path searches.'
    )
    rows = []
    for n in sizes:
        stops = sample_stops(graph, n + 1, seed=seed)
        build_matrix = n <= BRUTE_FORCE_SCALABILITY_MAX and n <= BRUTE_FORCE_MAX_STOPS
        matrix = None
        matrix_ms = 0.0
        if build_matrix:
            matrix_start = time.perf_counter()
            matrix = distance_matrix(graph, stops)
            matrix_ms = (time.perf_counter() - matrix_start) * 1000
        exact_distances = []
        batch = []
        for name in ALGORITHMS:
            short = ALGORITHM_SHORT[name]
            skip_reason = None
            if name == 'Brute-Force Route Search' and n > BRUTE_FORCE_MAX_STOPS:
                skip_reason = f'Brute-Force Route Search capped at {BRUTE_FORCE_MAX_STOPS} deliveries'
            elif name == 'Brute-Force Route Search' and n > BRUTE_FORCE_SCALABILITY_MAX:
                skip_reason = (
                    f'Brute-Force scalability skipped above {BRUTE_FORCE_SCALABILITY_MAX} deliveries '
                    '(matrix build dominates)'
                )
            if skip_reason:
                batch.append({
                    'deliveries': n,
                    'algorithm': name,
                    'short_name': short,
                    'status': 'skipped',
                    'skip_reason': skip_reason,
                    'trials': trials,
                    'avg_runtime_ms': None,
                    'min_runtime_ms': None,
                    'max_runtime_ms': None,
                    'avg_distance_km': None,
                    'peak_memory_kb': None,
                    'operations_or_states': None,
                    'optimality_gap_percent': None,
                    'optimality_gap_note': UNAVAILABLE,
                    'matrix_build_ms': round(matrix_ms, 5),
                    'prep_note': prep_note,
                })
                continue
            times = []
            memories = []
            result = None
            for _ in range(trials):
                tracemalloc.start()
                start = time.perf_counter()
                result_rows = compare(graph, stops, adjacency, matrix, selected=[name])
                times.append((time.perf_counter() - start) * 1000)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                result = result_rows[0]
                memories.append(peak / 1024)
            distance_m = result['distance_m']
            if result.get('exact'):
                exact_distances.append(distance_m)
            batch.append({
                'deliveries': n,
                'algorithm': name,
                'short_name': short,
                'status': 'ok',
                'skip_reason': None,
                'trials': trials,
                'avg_runtime_ms': round(statistics.mean(times), 5),
                'min_runtime_ms': round(min(times), 5),
                'max_runtime_ms': round(max(times), 5),
                'avg_distance_km': round(distance_m / 1000, 5),
                'peak_memory_kb': round(statistics.mean(memories), 3),
                'operations_or_states': result['Operations / states'],
                'distance_m': distance_m,
                'exact': bool(result.get('exact')),
                'optimality_gap_percent': None,
                'optimality_gap_note': UNAVAILABLE,
                'matrix_build_ms': round(matrix_ms, 5),
                'prep_note': prep_note,
            })
        optimal = min(exact_distances) if exact_distances else None
        for row in batch:
            if row['status'] == 'ok' and optimal is not None:
                gap = round(100 * (row['distance_m'] / optimal - 1), 2)
                row['optimality_gap_percent'] = gap
                row['optimality_gap_note'] = 'measured against Brute-Force Route Search on same matrix'
            row.pop('distance_m', None)
            row.pop('exact', None)
            rows.append(row)
            print(row)
    return rows, graph


def main():
    # Core multi-scale suite (matches DEFAULT_COUNTS). Use trials=3 for overnight CI-friendly runs.
    rows, graph = run_offline_benchmark(sizes=list(DEFAULT_COUNTS), trials=3, seed=42)
    path = Path('results/benchmark_results.csv')
    path.parent.mkdir(exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Saved {path}')

    scale_rows = run_scalability(graph, counts=list(DEFAULT_COUNTS), trials=3, seed=42)
    scale_path = save_scalability_csv(scale_rows)
    print(f'Saved {scale_path}')

    # Large-n pathfinder-only extension: 1k / 10k / 100k when the graph SCC allows it.
    from src.scalability import available_scale_counts
    large_counts = available_scale_counts(graph, LARGE_PATHFINDER_COUNTS)
    print(f'Large pathfinder counts available on this graph: {large_counts}')
    large_rows = run_scalability(
        graph,
        counts=list(large_counts) or [1_000],
        trials=1,
        seed=42,
        selected=['A* Search Algorithm', "Dijkstra's Algorithm"],
    )
    large_path = Path('results/scalability_large_pathfinders.csv')
    save_scalability_csv(large_rows, large_path)
    print(f'Saved {large_path}')


if __name__ == '__main__':
    main()
