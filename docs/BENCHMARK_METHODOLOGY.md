# Benchmark Methodology

## Purpose
Measure how FastRoute’s three student algorithms behave as the number of deliveries grows, using **real OpenStreetMap road distances**.

## Fairness rules
1. **Same graph.** One OSM driving network is loaded (cache preferred).
2. **Same stops.** For each delivery count `n`, FastRoute samples `n + 1` intersections (warehouse + deliveries) with a fixed seed.
3. **Same matrix.** One directed distance matrix is built with Dijkstra before Brute-Force Route Search runs. A* and Dijkstra tours use the same stop sample.
4. **Solver-only timing.** `time.perf_counter()` wraps only the selected solver call. OSM download/cache load is excluded. Matrix construction is excluded from Brute-Force Route Search timing. Offline benchmarks also record `matrix_build_ms` separately.
5. **Repeated trials.** Interactive scalability defaults to multiple trials; offline CLI uses several trials. Averages reduce timing noise. Min and max runtime are also stored.
6. **Memory.** Peak allocations during the solve are measured with `tracemalloc` (Python allocator view — useful for comparison, not a full OS RSS audit).
7. **Caps / skips.** Brute-Force Route Search skips above 9 deliveries. Skipped rows are labeled with a reason — never filled with fake numbers.
8. **Optimality gap.** Computed only when Brute-Force Route Search finished on that same matrix:
   `((distance − optimal_exact_distance) / optimal_exact_distance) × 100`.
   Otherwise the gap is labeled **unavailable**.

## What is recorded
| Field | Meaning |
|---|---|
| deliveries | Number of delivery stops (warehouse excluded from the count) |
| algorithm | Full solver name |
| trials | Number of timed repetitions |
| avg / min / max runtime_ms | Solver milliseconds |
| avg_distance_km | Tour length from the measured solve |
| peak / avg memory KB | tracemalloc peak during solves |
| operations / states | Algorithm counter (nodes settled or permutations evaluated) |
| optimality_gap_percent | Only when brute-force reference exists |
| status / skip_reason | `ok` or `skipped` |

## Delivery-count scales
Default multi-scale suite (`DEFAULT_COUNTS`): **4, 6, 8, 9, 12, 16, 25, 50, 100**.

- Brute-Force Route Search participates through **25** deliveries in scalability runs (exact ≤9; sampled above).
- Above 25, BF is skipped so the pairwise matrix build does not dominate; A* and Dijkstra continue.
- Optional large pathfinder extension: **250, 500** → `results/scalability_large_pathfinders.csv`.

## Separated paper benchmarks

```powershell
# Dijkstra vs A* vs OSM graph size (records actual node counts; never fakes 100k/1M)
.\.venv\Scripts\python.exe -m benchmarks.run_pathfinder_scale

# Brute Force order-search only (exhaustive 4–9; sampled 12/16/25)
.\.venv\Scripts\python.exe -m benchmarks.run_brute_force_scale
```

Tier fairness notes: `docs/OPTIMIZATION_TIER_COMPARABILITY.md`.

## How to run
```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m streamlit run app.py
# In the app: step 5 · Scalability & Export → Run scalability experiment

# Offline multi-stop CLI:
.venv\Scripts\python.exe -m benchmarks.run_benchmarks

# Export HTML/CSV figure companions for the paper:
.venv\Scripts\python.exe scripts\export_benchmark_figures.py
```

Outputs:
- `results/scalability_results.csv` (app / shared helper)
- `results/benchmark_results.csv` (offline CLI)
- `results/scalability_large_pathfinders.csv` (large-n A*/Dijkstra)
- `results/pathfinder_graph_scale.csv` + manifest
- `results/brute_force_delivery_scale.csv` + manifest
- `figures/*.html` + companion CSVs

## Charts
The Streamlit Experiments section plots runtime, distance, memory, and operations vs deliveries from **session-measured** rows only. Do not paste invented series into the research paper.
