"""Download and pickle OpenStreetMap drive graphs for every PLACE_PRESET.

Run:
  .venv\\Scripts\\python.exe -m scripts.warm_graph_cache
  .venv\\Scripts\\python.exe -m scripts.warm_graph_cache --only "Hoboken, New Jersey, USA"
"""
from __future__ import annotations
import argparse
import time
from src.road_data import PLACE_PRESETS, download_graph, graph_cache_path, has_cached_graph


def main():
    parser = argparse.ArgumentParser(description='Pre-cache OSM road graphs for FastRoute presets.')
    parser.add_argument('--only', action='append', default=[], help='Cache only this place name (repeatable).')
    parser.add_argument('--force', action='store_true', help='Re-download even when a cache file exists.')
    parser.add_argument('--timeout', type=int, default=180, help='Overpass timeout seconds per place.')
    args = parser.parse_args()
    places = args.only or list(PLACE_PRESETS)
    ok, skipped, failed = [], [], []
    for index, place in enumerate(places, start=1):
        path = graph_cache_path(place)
        if has_cached_graph(place) and not args.force:
            print(f'[{index}/{len(places)}] SKIP cached  {place} -> {path.name}')
            skipped.append(place)
            continue
        print(f'[{index}/{len(places)}] DOWNLOAD     {place}')
        started = time.perf_counter()
        try:
            graph = download_graph(place, use_cache=not args.force, timeout_s=args.timeout)
            elapsed = time.perf_counter() - started
            print(
                f'             OK {len(graph.nodes):,} nodes / {len(graph.edges):,} edges '
                f'in {elapsed:.1f}s -> {path.name}'
            )
            ok.append(place)
        except Exception as exc:
            print(f'             FAIL {place}: {exc}')
            failed.append((place, str(exc)))
    print('\nSummary')
    print(f'  cached/downloaded: {len(ok)}')
    print(f'  already present:   {len(skipped)}')
    print(f'  failed:            {len(failed)}')
    for place, reason in failed:
        print(f'   - {place}: {reason}')
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
