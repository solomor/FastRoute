# CPS 3440 — Algorithm Engineering Portfolio Project (Fall 2026)

Source: instructor assignment text provided by the team (2026-11-22).  
**Project value:** 100 points · **Course weight:** 20% · **Format:** individual or team (2–4 recommended)

## Track selected by FastRoute

**Track 4 — Delivery Route Optimization**  
Algorithm directions: greedy, dynamic programming, shortest paths, TSP-related exact/heuristic methods.  
Study route optimization and the distinction between inefficient algorithms and hard problems.

## Required algorithmic comparison (map to FastRoute)

| Required approach | FastRoute mapping |
|---|---|
| Algorithm 1 — Baseline | Brute-Force Route Search (exact order search on the distance matrix; establishes optimum / comparison point for small *n*) |
| Algorithm 2 — Efficient course-based | Dijkstra’s Algorithm (student-implemented shortest paths on OSM roads; also builds the pairwise matrix) |
| Algorithm 3 — Alternative / optimized | A* Search Algorithm (same path problem with admissible geographic heuristic) |

Supporting “same algorithm, better settings” stories (Bad→Semi→Best ladder; Dijkstra sample order vs Brute-Force order + Dijkstra; larger nested BF budgets) strengthen the optimization narrative but do **not** replace the three core solvers.

## Final deliverables checklist

1. GitHub repository  
2. GitHub Pages project website  
3. Technical paper (6–10 pages)  
4. Presentation + demo  

## Grading (100 points)

| Category | Points |
|---|---:|
| A. Real-World Problem & Dataset | 8 |
| B. Algorithm Design & Implementation | 20 |
| C. Complexity, Correctness & CLO Analysis | 17 |
| D. Experimental Design & Benchmarking | 15 |
| E. Results, Visualization & Interpretation | 10 |
| F. GitHub Repository & Software Engineering | 10 |
| G. GitHub Pages Professional Portfolio Website | 8 |
| H. Technical Paper | 7 |
| I. Presentation & Technical Defense | 5 |
| **TOTAL** | **100** |

## CLO reflection questions (must appear in paper)

- **A — Efficiency:** one concrete result showing why efficiency matters  
- **B — Complexity:** one major algorithm’s time/space + whether measurements matched theory  
- **C — Hardness:** inefficient algorithm vs computationally hard problem  
- **D — Selection:** which algorithms investigated; which to recommend and why  

Full section requirements (paper outline, README list, Pages site sections, Git workflow, resume bullets) are in the instructor PDF pages 1–13.
