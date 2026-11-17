# Benchmark Methodology

## Purpose
Measure how FastRoute’s four delivery-order algorithms behave as the number of deliveries grows, using **real OpenStreetMap road distances** and **student Dijkstra**, without mixing preprocessing time into solver runtime.

## Fairness rules
1. **Same graph.** One OSM driving network is loaded (cache preferred).
2. **Same stops.** For each delivery count `n`, FastRoute samples `n + 1` intersections (warehouse + deliveries) with a fixed seed.
3. **Same matrix.** One directed distance matrix is built with Dijkstra before any TSP solver runs. Every algorithm in that size class uses that matrix.
4. **Solver-only timing.** `time.perf_counter()` wraps only the TSP call. OSM download/cache load and matrix construction are excluded from solver runtime. Offline benchmarks also record `matrix_build_ms` separately.
5. **Repeated trials.** Interactive scalability defaults to multiple trials; offline CLI uses 5 trials. Averages reduce timing noise. Min and max runtime are also stored.
6. **Memory.** Peak allocations during the solve are measured with `tracemalloc` (Python allocator view — useful for comparison, not a full OS RSS audit).
7. **Caps / skips.** Brute Force skips above 9 deliveries; Held-Karp skips above 16. Skipped rows are labeled with a reason — never filled with fake numbers.
8. **Optimality gap.** Computed only when at least one exact solver finished on that same matrix:
   `((heuristic_or_exact_distance − optimal_exact_distance) / optimal_exact_distance) × 100`.
   Otherwise the gap is labeled **unavailable**.

## What is recorded
| Field | Meaning |
|---|---|
| deliveries | Number of delivery stops (warehouse excluded from the count) |
| algorithm | Full solver name |
| trials | Number of timed repetitions |
| avg / min / max runtime_ms | Solver milliseconds |
| avg_distance_km | Tour length from the measured matrix cost |
| peak / avg memory KB | tracemalloc peak during solves |
| operations / states | Algorithm counter (permutations, DP states, or greedy/2-Opt examinations) |
| optimality_gap_percent | Only when exact reference exists |
| status / skip_reason | `ok` or `skipped` |

## How to run
```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m streamlit run app.py
# In the app: Experiments and Reports → Run scalability experiment

# Offline CLI (downloads/uses cached OSM area):
.venv\Scripts\python.exe -m benchmarks.run_benchmarks
```

Outputs:
- `results/scalability_results.csv` (app / shared helper)
- `results/benchmark_results.csv` (offline CLI)

## Existing measured sample
`results/scalability_results.csv` was refreshed on 2026-11-04 against cached **Jersey City** roads (`seed=42`, `trials=3`, deliveries **4,6,8,10,12,14,16**). Brute Force rows at 10+ are labeled skipped (cap 9). Values are real `tracemalloc` / `perf_counter` measurements, not placeholders. Re-run before citing if code or graph changes.

## Charts
The Streamlit Experiments section plots runtime, distance, memory, and operations vs deliveries from **session-measured** rows only. Do not paste invented series into the research paper.
