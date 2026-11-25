# Benchmark results

## Current (use these in the paper)

| File | Meaning |
|---|---|
| `scalability_results.csv` | Delivery-count scalability (solver timings) |
| `scalability_large_pathfinders.csv` | Large-n A*/Dijkstra extension |
| `pathfinder_graph_scale.csv` + `_manifest.json` | Dijkstra vs A* by authentic OSM graph size |
| `brute_force_delivery_scale.csv` + `_manifest.json` | Exhaustive / sampled BF by delivery count |
| `benchmark_results.csv` | Offline multi-scale suite |
| `test_results_*.txt` | Unit-test logs |

## Historical (superseded — do not mix with current claims)

Copies under `historical/*.historical` preserve pre-repair / earlier runs.  
Prefer **current** CSVs and manifests for any new paper tables or charts.
