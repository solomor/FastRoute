"""Brute-Force Route Search scalability (delivery counts — separate from pathfinding).

Run:
  .venv\\Scripts\\python.exe -m benchmarks.run_brute_force_scale

Exhaustive: 4, 6, 8, 9 deliveries.
Sampled (explicitly labeled): 12, 16, 25 with fixed budgets.
"""
from __future__ import annotations

import csv
import json
import math
import platform
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

from src.algorithms import brute_force_route_search
from src.constants import (
    BRUTE_FORCE_BAD_BUDGET,
    BRUTE_FORCE_EXACT_MAX_STOPS,
    BRUTE_FORCE_SAMPLE_BUDGET,
)
from src.road_data import PLACE, distance_matrix, download_graph, sample_stops

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'

EXHAUSTIVE_COUNTS = [4, 6, 8, 9]
SAMPLED_COUNTS = [12, 16, 25]
TRIALS = 3
SEED = 42
PLACE_NAME = PLACE


def _env_info():
    return {
        'python': sys.version.split()[0],
        'platform': platform.platform(),
        'measured_at_utc': datetime.now(timezone.utc).isoformat(),
        'timing': 'Solver-only around brute_force_route_search; matrix build excluded and recorded separately',
        'memory': 'tracemalloc peak during brute-force solve',
    }


def run(place=PLACE_NAME, trials=TRIALS, seed=SEED):
    graph = download_graph(place)
    rows = []
    for deliveries in EXHAUSTIVE_COUNTS + SAMPLED_COUNTS:
        stops = sample_stops(graph, deliveries + 1, seed=seed)
        matrix_start = time.perf_counter()
        matrix = distance_matrix(graph, stops)
        matrix_ms = (time.perf_counter() - matrix_start) * 1000
        mode = 'exhaustive' if deliveries <= BRUTE_FORCE_EXACT_MAX_STOPS else 'sampled'
        budget = None if mode == 'exhaustive' else BRUTE_FORCE_SAMPLE_BUDGET
        times, memories, ops_list, distances, exact_flags = [], [], [], [], []
        for trial in range(trials):
            tracemalloc.start()
            start = time.perf_counter()
            route, cost, ops, exact = brute_force_route_search(
                matrix,
                max_permutations=budget,
                seed=seed + trial,
            )
            elapsed = (time.perf_counter() - start) * 1000
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            times.append(elapsed)
            memories.append(peak / 1024)
            ops_list.append(ops)
            distances.append(cost)
            exact_flags.append(exact)
            assert route[0] == 0 and route[-1] == 0
            assert len(set(route[1:-1])) == deliveries
        exact = all(exact_flags)
        rows.append({
            'deliveries': deliveries,
            'search_mode': 'exhaustive' if exact else 'sampled',
            'claimed_mode': mode,
            'max_permutations_budget': budget if budget is not None else 'full_n_factorial',
            'factorial_n': math.factorial(deliveries),
            'trials': trials,
            'avg_runtime_ms': round(statistics.mean(times), 5),
            'min_runtime_ms': round(min(times), 5),
            'max_runtime_ms': round(max(times), 5),
            'avg_peak_memory_kb': round(statistics.mean(memories), 3),
            'avg_permutations_evaluated': round(statistics.mean(ops_list), 2),
            'avg_distance_km': round(statistics.mean(distances) / 1000, 5),
            'verified_optimal': bool(exact),
            'optimality_note': (
                'Exhaustive enumeration — proven optimum on this matrix'
                if exact else
                'Sampled / capped search — NOT a guaranteed global optimum'
            ),
            'matrix_build_ms': round(matrix_ms, 5),
            'place': place,
            'seed': seed,
            'bad_tier_budget_reference': BRUTE_FORCE_BAD_BUDGET,
            'semi_tier_budget_reference': BRUTE_FORCE_SAMPLE_BUDGET,
        })
        print(
            f'n={deliveries} mode={"exhaustive" if exact else "sampled"} '
            f'runtime={rows[-1]["avg_runtime_ms"]}ms ops={rows[-1]["avg_permutations_evaluated"]} '
            f'optimal={exact}'
        )

    RESULTS.mkdir(exist_ok=True)
    out_csv = RESULTS / 'brute_force_delivery_scale.csv'
    with out_csv.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        'experiment': 'brute_force_delivery_scale',
        'description': 'Order-search scalability; separate from Dijkstra/A* pathfinding',
        'environment': _env_info(),
        'exhaustive_counts': EXHAUSTIVE_COUNTS,
        'sampled_counts': SAMPLED_COUNTS,
        'results_csv': str(out_csv.relative_to(ROOT)).replace('\\', '/'),
        'notes': [
            'Exhaustive Brute Force is never run at 1000+ deliveries.',
            'Sampled rows must not be cited as mathematical optima.',
            'Factorial growth explains why exhaustive search becomes impractical.',
        ],
    }
    man_path = RESULTS / 'brute_force_delivery_scale_manifest.json'
    man_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Saved {out_csv}')
    print(f'Saved {man_path}')
    return rows, manifest


def main():
    run()


if __name__ == '__main__':
    main()
