# FastRoute: Delivery Route Optimization

**FastRoute** is an interactive delivery-route optimization system that compares exact and heuristic routing algorithms on real road networks. A student-implemented Dijkstra algorithm computes road distances between locations, and four route-order algorithms (Brute Force, Held-Karp, Nearest Neighbor, and Nearest Neighbor + 2-Opt) decide the order in which a vehicle visits its delivery stops.

CPS 3440 Analysis of Algorithms · Fall 2026

- **Project website:** https://solomor.github.io/FastRoute/
- **Technical paper:** coming soon
- **Presentation:** coming soon

<!-- TODO: add a screenshot of the Streamlit app, e.g. ![FastRoute app](docs/img/app-screenshot.png) -->

---

## The Problem

A single vehicle leaves a warehouse, visits every delivery stop exactly once, and returns to the warehouse. The goal is to minimize the total road distance.

This involves two algorithmic problems:

1. **Shortest road path** between two locations. Solved efficiently with Dijkstra's algorithm.
2. **Delivery order** of the stops. A variant of the Traveling Salesperson Problem (TSP), which is NP-hard.

The project shows the difference between an *inefficient algorithm*, which can be fixed with a better approach, and an *inherently hard problem*, which requires trading optimality for speed.

## Dataset

| Source | Size | Use |
|---|---|---|
| Food Delivery dataset (Kaggle) | 38,964 rows | Geographic coordinates used to build delivery scenarios |
| [Grubhub Restaurant Data](https://www.kaggle.com/datasets/polartech/grubhub-restaurant-data) (Kaggle) | 8,088 rows | Restaurant locations as a second coordinate source |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) via OSMnx | Area-dependent | Directed road network (intersections and road segments) |

**Preprocessing:** validate coordinates → snap each point to the nearest road intersection → build a road-distance matrix with Dijkstra → run the route-order algorithms.

**Limitations:** FastRoute optimizes road-network distance, not live traffic or travel time. The datasets provide real locations used to construct scenarios; they are not live delivery orders.

Road data © OpenStreetMap contributors, available under the Open Database License (ODbL).

## Algorithms Implemented

| Algorithm | Type | Guaranteed optimal? |
|---|---|---|
| Dijkstra | Shortest road path between two locations | Yes (non-negative weights) |
| Brute Force | Exact: enumerates every delivery order | Yes |
| Held-Karp | Exact: dynamic programming over subsets of stops | Yes |
| Nearest Neighbor | Greedy heuristic: always visits the closest unvisited stop | No |
| Nearest Neighbor + 2-Opt | Local search: improves the greedy route by reversing segments | No |

All algorithms are implemented by the team, not called from a library.

## Complexity Summary

V = road intersections, E = road segments, n = delivery stops, p = 2-Opt improvement passes.

| Algorithm | Time | Space |
|---|---|---|
| Dijkstra (binary heap) | O((V + E) log V) | O(V + E) |
| Brute Force | O(n! × n) | O(n) |
| Held-Karp | O(n² × 2ⁿ) | O(n × 2ⁿ) |
| Nearest Neighbor | O(n²) | O(n) |
| NN + 2-Opt | O(p × n³) | O(n) |

The app caps Brute Force at 9 stops and Held-Karp at 16 stops so it stays responsive.

## Experimental Results

Benchmarks compare runtime, peak memory (tracemalloc), route distance, and optimality gap for 4 to 16 deliveries, using the same stops and distance matrix for every algorithm.

<!-- TODO: add the final benchmark tables and charts here (from results/ and figures/). Do not add unverified numbers. -->

*Final measured results will be added after the benchmark run is complete.*

## Technologies

Python · Streamlit · OSMnx · NetworkX · pyproj · pandas · Plotly · Folium · HTML/CSS/JavaScript · GitHub Pages

## Installation

Requires Python 3.10 or newer and Git.

```bash
git clone https://github.com/solomor/FastRoute.git
cd FastRoute/FastRoute_GitHub/FastRoute
pip install -r requirements.txt
```

## How to Run

```bash
streamlit run app.py
```

On Windows you can also run `start_fastroute.bat` (Command Prompt) or `start_fastroute.ps1` (PowerShell) from the same folder.

The app opens in your browser. Choose an area or dataset, select delivery stops, pick the algorithms to run, and compare the results.

## Testing

```bash
python -m pytest tests
```

## Project Structure

```
FastRoute/
├── docs/                      # GitHub Pages website
└── FastRoute_GitHub/FastRoute/
    ├── app.py                 # Streamlit application
    ├── src/                   # Algorithms, road data, visualization
    ├── tests/                 # Automated tests
    ├── benchmarks/            # Performance experiments
    ├── data/                  # Datasets
    ├── docs/                  # Methodology and technical notes
    ├── pages/                 # Additional Streamlit pages
    ├── scripts/               # Helper scripts
    ├── requirements.txt
    ├── CONTRIBUTIONS.md
    └── start_fastroute.bat / start_fastroute.ps1
```

## Contributors

| Member | Role |
|---|---|
| Carlos Funez | Software implementation · Presentation slides |
| Calelle Polynice | Technical paper |
| Omar Soliman | Dataset research · Presentation slides |
| Wari Lojano | Project website |

Detailed contributions are listed in [CONTRIBUTIONS.md](FastRoute_GitHub/FastRoute/CONTRIBUTIONS.md).
