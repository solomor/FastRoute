# FastRoute — Interactive Delivery Route Algorithm Visualization

CPS 3440 · Analysis of Algorithms · Fall 2026

FastRoute compares three student algorithms on **real OpenStreetMap streets**:

- **A* Search Algorithm** — shortest road paths with a geographic heuristic
- **Dijkstra's Algorithm** — shortest road paths (also builds the distance matrix)
- **Brute-Force Route Search** — exact delivery-order search on that matrix

Each family also has an **optimization ladder**: **Bad → Semi → Best** (Compare Results), so you can show a weak baseline, a solid course version, and a stronger optimized variant.

Tour shape:

**warehouse → deliveries → warehouse**

The objective is **road length in meters**, not live traffic travel time.

## Why this project exists

Real delivery planning combines shortest-path search on a road network with multi-stop ordering. FastRoute shows A* vs Dijkstra on the same streets, and how brute-force order search finds a better tour when the delivery count is small enough — with street-level maps, measured timings, and beginner-friendly explanations.

## Main features

### Build & watch
- Dark-navy Streamlit dashboard with section navigation
- **Compare All** runs A*, Dijkstra, and Brute-Force Route Search on the same stops
- Route colors: Green A* · Orange Dijkstra · Blue Brute Force
- Live Leaflet drawing (Play all / Pause / Resume / Reset) without Streamlit page reloads
- Warehouse + stop markers, show/hide routes, live draw speed

### Compare results
- Distance, runtime, operations/states, peak memory, optimality gap
- **What Do These Results Mean?** auto-explanation from measured values only
- Route-quality snapshot: shortest, fastest, lowest memory, exact order search
- Optimality-gap formula when brute force ran

### Learn How It Works
- Beginner explanation of the delivery problem
- Per-algorithm simple language, steps, time/space complexity, pros/cons
- Clear split: A*/Dijkstra find road paths; brute force chooses stop order
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
- **Download all paper evidence (CSV + screenshots)** → zip with tables, PNGs, chart/map HTML, docs, and CLO/paper prompts (`portfolio_evidence_pack/`)

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
| A* Search | O((V+E) log V) typical binary heap | O(V+E) | Yes for shortest paths with admissible heuristic |
| Dijkstra | O((V+E) log V) binary heap | O(V+E) | Yes for nonnegative weights |
| Brute-Force Route Search | O(n! × n) | O(n) | Yes for delivery order on the matrix |

UI caps: up to **1000 delivery destinations**. Brute-Force Route Search is **exact** up to 9 deliveries; above that it still runs (up to 1000) by sampling delivery orders (not a full `n!` proof). For large counts use **NYC / NJ metro (merged caches)** or **New York** (optionally with Grubhub). The map may simplify geometry above ~120 stops while distances still use full road paths. Solver timings exclude OSM download; brute-force timing also excludes matrix construction.

**Optimality gap** (only when Brute-Force Route Search ran on the same matrix):

`((Distance − Optimal Distance) / Optimal Distance) × 100`

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

**Primary:** OpenStreetMap roads (ODbL, © OpenStreetMap contributors) + **Grubhub restaurant listings** for NYC/NJ stop coordinates ([Kaggle source](https://www.kaggle.com/datasets/polartech/grubhub-restaurant-data); license listed Unknown on Kaggle — cite the URL).

**Secondary only:** `food_delivery_dataset.csv` (India geography) — do not use as the main NJ/NY routing demo.

See `data/README.md` and `docs/DATASET_METHODOLOGY.md` for fields, preprocessing, limitations, and citation text. CSV coordinates are experiment stop inputs after snapping — not proven multi-stop driver tours.

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
