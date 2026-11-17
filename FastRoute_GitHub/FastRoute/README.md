# FastRoute — Interactive Delivery Route Algorithm Visualization

CPS 3440 · Analysis of Algorithms · Fall 2026

FastRoute compares four delivery-routing algorithms on **real OpenStreetMap streets**. A student-implemented **Dijkstra** algorithm builds a road-distance matrix; then **Brute Force**, **Held-Karp**, **Nearest Neighbor**, and **Nearest Neighbor + 2-Opt** choose tour orders for:

**warehouse → deliveries → warehouse**

The objective is **road length in meters**, not live traffic travel time.

## Why this project exists

Real delivery planning is a traveling-salesperson style problem on a road network. Exact methods prove optimality on small instances; heuristics scale further. FastRoute makes that trade-off visible with street-level maps, measured timings, and beginner-friendly explanations for students and instructors.

## Main features

### Build & watch
- Dark-navy Streamlit dashboard with section navigation
- **Compare All** runs the selected solvers on one shared distance matrix
- Route colors: Blue Brute Force · Green Held-Karp · Orange Nearest Neighbor · Red NN + 2-Opt
- Live Leaflet drawing (Play all / Pause / Resume / Reset) without Streamlit page reloads
- Warehouse + stop markers, show/hide routes, live draw speed

### Compare results
- Distance, runtime, operations/states, peak memory, optimality gap
- **Understanding Your Results** auto-explanation from measured values only
- Route-quality snapshot: shortest, fastest, lowest memory, 2-Opt savings
- Optimality-gap formula and exact-vs-heuristic labels

### Learn How It Works
- Beginner explanation of the delivery problem
- Per-algorithm simple language, steps, time/space complexity, pros/cons
- Clear split: Dijkstra finds road paths; TSP solvers choose stop order
- End-to-end pipeline diagram text
- Project limitations (one vehicle, no traffic, no capacity/windows, etc.)

### Watch Dijkstra
- Interactive Dijkstra lab on the real OSM graph
- Start/destination intersection pickers
- Step / auto play of settle & relax events from the student algorithm
- Final shortest path distance in meters and kilometers

### Experiments & reports
- Scalability runs for delivery counts (respecting exact-algorithm caps)
- Charts for runtime / distance / memory / operations vs deliveries
- CSV export of measured scalability rows
- **Generate Experiment Report** → JSON, CSV, printable HTML

### Datasets
- Built-in `food_delivery_dataset.csv` and `grubhub.csv`
- Upload/drop files via Dataset Explorer (`data/user/`)
- Coordinates snapped to OSM intersections inside the downloaded area
- Historical CSV rows are **not** claimed to be multi-stop driver traces

### Engineering
- Local road-graph cache in `data/graphs/`
- Many area presets (NJ towns, NYC boroughs, neighborhoods). Rebuild local caches with:
  `python -m scripts.build_local_area_caches` (offline crop from New York/Jersey City) or
  `python -m scripts.warm_graph_cache` (live Overpass download when the network allows)
- Unit tests for algorithms, datasets, viz, Dijkstra steps, reports
- Benchmark script for offline scalability CSV

## Algorithm summary

| Algorithm | Time (as implemented) | Space | Optimal? |
|---|---|---|---|
| Dijkstra | O((V+E) log V) binary heap | O(V) | Yes for nonnegative weights |
| Brute Force | O(n! × n) | O(n) | Yes |
| Held-Karp | O(n² 2ⁿ) | O(n 2ⁿ) | Yes |
| Nearest Neighbor | O(n²) | O(n) | No |
| NN + 2-Opt | O(p × n³) worst (full rescoring) | O(n) | No |

UI caps: Brute Force ≤ 9 deliveries; Held-Karp ≤ 16. Solver timings exclude OSM download and matrix construction.

**Optimality gap** (only when an exact solver ran on the same matrix):

`((Heuristic Distance − Optimal Distance) / Optimal Distance) × 100`

## Windows install & run

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m unittest discover -s tests -v
streamlit run app.py
```

Without activation:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m streamlit run app.py
```

Open http://localhost:8501

Offline benchmark (solver timings exclude OSM download + Dijkstra matrix build):

```powershell
.venv\Scripts\python.exe -m benchmarks.run_benchmarks
```

Clean submission ZIP (excludes `.venv`, graph caches, bytecode):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\make_submission_zip.ps1
```

### Demo Mode
In the sidebar, open **Demo Mode** and click **Load Demo Experiment** for a reproducible 6-stop Jersey City scenario (uses cache when available).

## How to interpret results

- **Distance** = tour road length (quality)
- **Runtime** = solver CPU time only (speed)
- **Memory** = peak traced allocations during the solve
- Fastest ≠ shortest
- Blank optimality gap means no exact reference was available

## Data & attribution

- Roads: OpenStreetMap via OSMnx · © OpenStreetMap contributors · ODbL
- Delivery CSVs: user-supplied food-delivery and Grubhub files in `data/`
- Dataset columns provide coordinates/attributes; they do not automatically equal historical multi-stop routes

## Repository layout

```
app.py
pages/1_Dataset_Explorer.py
src/algorithms.py
src/road_data.py
src/map_viz.py
src/route_prep.py
src/datasets.py
src/dashboard.py
src/learn_content.py
src/results_explain.py
src/dijkstra_viz.py
src/scalability.py
src/report.py
src/guided_demo.py
tests/
benchmarks/
data/
.streamlit/config.toml
```

## Limitations

One warehouse, one vehicle, closed tour, distance-only objective. No live traffic, capacity, time windows, multi-depot, or multi-driver optimization. Exact solvers are capped for UI responsiveness.

## Academic audit docs

Submission readiness materials (audits, methodology, checklists) live in `docs/`:

- `docs/FINAL_SUBMISSION_READINESS.md` — overall readiness
- `docs/FINAL_RUBRIC_AUDIT.md` — rubric mapping (**needs official assignment PDF**)
- `docs/ALGORITHM_CORRECTNESS_AUDIT.md`
- `docs/BENCHMARK_METHODOLOGY.md`
- `docs/ALGORITHMIC_EFFICIENCY_ANALYSIS.md`
- `docs/DATASET_METHODOLOGY.md`
- `docs/RESEARCH_PAPER_CHECKLIST.md`
- `docs/GITHUB_SUBMISSION_CHECKLIST.md`
- `docs/PRESENTATION_CHECKLIST.md`
- `docs/TEAM_CONTRIBUTIONS_CHECKLIST.md`
