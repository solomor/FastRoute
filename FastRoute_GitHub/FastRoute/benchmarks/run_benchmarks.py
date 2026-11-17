"""Reproducible routing experiments on real OpenStreetMap roads.

Run: python -m benchmarks.run_benchmarks

Timing isolates the TSP solver from graph download and Dijkstra matrix construction.
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
    BRUTE_FORCE_MAX_STOPS,
    HELD_KARP_MAX_STOPS,
)
from src.road_data import PLACE, download_graph, sample_stops, distance_matrix
from src.scalability import run_scalability, save_scalability_csv

UNAVAILABLE = 'unavailable'


def run_offline_benchmark(place=PLACE, sizes=None, trials=5, seed=42):
    """Return measured rows for the offline CLI benchmark."""
    sizes = sizes or [4, 6, 8, 10, 12, 15, 20, 30]
    graph = download_graph(place)
    prep_note = (
        'OSM download/cache load and Dijkstra distance-matrix construction '
        'are excluded from solver runtime.'
    )
    rows = []
    for n in sizes:
        stops = sample_stops(graph, n + 1, seed=seed)
        matrix_start = time.perf_counter()
        matrix = distance_matrix(graph, stops)
        matrix_ms = (time.perf_counter() - matrix_start) * 1000
        exact_distances = []
        batch = []
        for name, fn in ALGORITHMS.items():
            short = ALGORITHM_SHORT[name]
            if name.startswith('Brute Force') and n > BRUTE_FORCE_MAX_STOPS:
                batch.append({
                    'deliveries': n,
                    'algorithm': name,
                    'short_name': short,
                    'status': 'skipped',
                    'skip_reason': f'Brute Force capped at {BRUTE_FORCE_MAX_STOPS} deliveries',
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
            if name.startswith('Held-Karp') and n > HELD_KARP_MAX_STOPS:
                batch.append({
                    'deliveries': n,
                    'algorithm': name,
                    'short_name': short,
                    'status': 'skipped',
                    'skip_reason': f'Held-Karp capped at {HELD_KARP_MAX_STOPS} deliveries',
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
                result = fn(matrix)
                times.append((time.perf_counter() - start) * 1000)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                memories.append(peak / 1024)
            distance_m = result[1]
            if '(exact)' in name:
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
                'operations_or_states': result[2],
                'distance_m': distance_m,
                'exact': '(exact)' in name,
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
                row['optimality_gap_note'] = 'measured against exact solvers on same matrix'
            row.pop('distance_m', None)
            row.pop('exact', None)
            rows.append(row)
            print(row)
    return rows, graph


def main():
    rows, graph = run_offline_benchmark()
    path = Path('results/benchmark_results.csv')
    path.parent.mkdir(exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Saved {path}')

    # Also refresh the interactive scalability CSV using the same graph and fair matrix protocol.
    scale_rows = run_scalability(graph, counts=[4, 6, 8, 10, 12], trials=5, seed=42)
    scale_path = save_scalability_csv(scale_rows)
    print(f'Saved {scale_path}')


if __name__ == '__main__':
    main()
