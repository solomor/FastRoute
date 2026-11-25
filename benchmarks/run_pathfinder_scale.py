"""Dijkstra vs A* on real OSM graphs of increasing size (node counts).

Run:
  .venv\\Scripts\\python.exe -m benchmarks.run_pathfinder_scale

Measures shortest-path search only (not multi-stop TSP order search).
Graph load/cache time is excluded from solver timings.
"""
from __future__ import annotations

import csv
import json
import platform
import statistics
import sys
import time
import tracemalloc
from datetime import datetime, timezone
from pathlib import Path

from src.algorithms import astar, dijkstra, haversine_heuristic, reconstruct
from src.dijkstra_viz import is_reachable, sample_reachable_pair
from src.road_data import download_graph, to_adjacency

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'results'
FIGURES = ROOT / 'figures'

# Target size classes → concrete cached OSM places (actual counts recorded at runtime).
# Never fabricate nodes. 100k/1M complete only when actual_nodes >= target.
SIZE_TARGETS = [
    {'label': '1k_nodes', 'target_nodes': 1_000, 'place': 'Jersey City, New Jersey, USA'},
    {'label': '10k_nodes', 'target_nodes': 10_000, 'place': 'Manhattan, New York, USA'},
    {'label': '100k_nodes', 'target_nodes': 100_000, 'place': 'NYC / NJ metro (merged caches)'},
    # Optional 1M: same largest cache; will mark incomplete unless a larger authentic graph exists.
    {'label': '1M_nodes_optional', 'target_nodes': 1_000_000, 'place': 'NYC / NJ metro (merged caches)', 'optional': True},
]


def _target_status(actual_nodes, target_nodes):
    pct = 100.0 * actual_nodes / target_nodes if target_nodes else 0.0
    if actual_nodes >= target_nodes:
        status = 'completed'
    elif actual_nodes >= target_nodes * 0.9:
        status = 'near_target_incomplete'
    else:
        status = 'incomplete'
    return status, round(pct, 2)

PAIRS_PER_GRAPH = 5
TRIALS = 3
SEED = 42


def _env_info():
    return {
        'python': sys.version.split()[0],
        'platform': platform.platform(),
        'machine': platform.machine(),
        'processor': platform.processor(),
        'measured_at_utc': datetime.now(timezone.utc).isoformat(),
        'timing': 'time.perf_counter around student dijkstra/astar only; graph load excluded',
        'memory': 'tracemalloc peak during each trial (Python allocator, not OS RSS)',
    }


def _time_pathfinder(adjacency, graph, source, target, kind, trials=TRIALS):
    times, memories, ops_list, distances = [], [], [], []
    for _ in range(trials):
        tracemalloc.start()
        start = time.perf_counter()
        if kind == 'dijkstra':
            dist, prev, ops = dijkstra(adjacency, source, target)
        else:
            dist, prev, ops = astar(
                adjacency, source, target, haversine_heuristic(graph, target)
            )
        elapsed_ms = (time.perf_counter() - start) * 1000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        if target not in dist:
            raise ValueError('unreachable pair slipped through')
        path = reconstruct(prev, source, target)
        if not path:
            raise ValueError('empty path')
        times.append(elapsed_ms)
        memories.append(peak / 1024)
        ops_list.append(ops)
        distances.append(dist[target])
    return {
        'avg_runtime_ms': round(statistics.mean(times), 5),
        'min_runtime_ms': round(min(times), 5),
        'max_runtime_ms': round(max(times), 5),
        'avg_peak_memory_kb': round(statistics.mean(memories), 3),
        'avg_nodes_settled': round(statistics.mean(ops_list), 2),
        'distance_m': distances[0],
        'trials': trials,
    }


def run(pairs_per_graph=PAIRS_PER_GRAPH, trials=TRIALS, seed=SEED):
    rows = []
    blocked = []
    for spec in SIZE_TARGETS:
        place = spec['place']
        print(f'Loading {place} ...')
        load_start = time.perf_counter()
        graph = download_graph(place)
        load_ms = (time.perf_counter() - load_start) * 1000
        n_nodes = len(graph.nodes)
        n_edges = len(graph.edges)
        print(f'  nodes={n_nodes} edges={n_edges} load_ms={load_ms:.1f}')

        target_nodes = spec['target_nodes']
        status, pct = _target_status(n_nodes, target_nodes)
        if status != 'completed':
            blocked.append({
                'label': spec['label'],
                'target_nodes': target_nodes,
                'actual_nodes': n_nodes,
                'actual_edges': n_edges,
                'percent_of_target': pct,
                'target_status': status,
                'optional': bool(spec.get('optional')),
                'reason': (
                    f'Authentic OSM graph has {n_nodes} nodes '
                    f'({pct}% of target {target_nodes:,}). '
                    'Not labeled completed; nodes were not fabricated.'
                ),
            })
            print(f'  TARGET STATUS={status} actual={n_nodes} target={target_nodes} ({pct}%)')
            # Still measure on the largest available authentic graph for incomplete large targets.
            if spec.get('optional') and status != 'completed':
                print('  optional incomplete target — skip pair timing to avoid duplicate merged-cache runs')
                continue

        adjacency = to_adjacency(graph)
        for pair_index in range(pairs_per_graph):
            pair = sample_reachable_pair(graph, seed=seed + pair_index * 17)
            if pair is None:
                print(f'  pair {pair_index}: skipped (no reachable sample)')
                continue
            source, target = pair
            if not is_reachable(graph, source, target):
                continue
            dij = _time_pathfinder(adjacency, graph, source, target, 'dijkstra', trials)
            ast = _time_pathfinder(adjacency, graph, source, target, 'astar', trials)
            agree = abs(dij['distance_m'] - ast['distance_m']) <= 1e-6
            base = {
                'size_label': spec['label'],
                'target_nodes': target_nodes,
                'actual_nodes': n_nodes,
                'actual_edges': n_edges,
                'percent_of_target': pct,
                'target_status': status,
                'place': place,
                'dataset_source': 'OpenStreetMap via OSMnx (local cache)',
                'graph_nodes': n_nodes,
                'graph_edges': n_edges,
                'graph_load_ms': round(load_ms, 3),
                'pair_index': pair_index,
                'source': source,
                'target': target,
                'seed': seed + pair_index * 17,
                'distance_agreement': agree,
            }
            rows.append({
                **base,
                'algorithm': "Dijkstra's Algorithm",
                'short_name': 'Dijkstra',
                **{k: dij[k] for k in dij},
            })
            rows.append({
                **base,
                'algorithm': 'A* Search Algorithm',
                'short_name': 'A*',
                **{k: ast[k] for k in ast},
            })
            print(
                f'  pair {pair_index}: dist={dij["distance_m"]:.1f}m '
                f'Dijkstra {dij["avg_runtime_ms"]:.2f}ms / {dij["avg_nodes_settled"]} settles · '
                f'A* {ast["avg_runtime_ms"]:.2f}ms / {ast["avg_nodes_settled"]} settles · agree={agree}'
            )

    RESULTS.mkdir(exist_ok=True)
    out_csv = RESULTS / 'pathfinder_graph_scale.csv'
    if rows:
        with out_csv.open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    manifest = {
        'experiment': 'pathfinder_graph_scale',
        'description': 'Dijkstra vs A* on authentic OSM graphs; same reachable pairs',
        'environment': _env_info(),
        'pairs_per_graph': pairs_per_graph,
        'trials_per_pair': trials,
        'base_seed': seed,
        'results_csv': str(out_csv.relative_to(ROOT)).replace('\\', '/'),
        'row_count': len(rows),
        'graphs_measured': sorted({(r['place'], r['graph_nodes'], r['graph_edges']) for r in rows}),
        'target_completion_policy': (
            'completed only if actual_nodes >= target_nodes; '
            'reaching ~50% of a target is incomplete, never completed'
        ),
        'blocked_or_notes': blocked + [
            {
                'note': '100,000-node and 1,000,000-node targets are not fabricated. '
                        'Largest authentic merged NYC/NJ cache is measured with target_status=incomplete '
                        'when below target.'
            }
        ],
    }
    man_path = RESULTS / 'pathfinder_graph_scale_manifest.json'
    man_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Saved {out_csv}')
    print(f'Saved {man_path}')
    return rows, manifest


def main():
    run()


if __name__ == '__main__':
    main()
