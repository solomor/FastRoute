# Algorithmic Efficiency vs. Computational Hardness

## 1. Problem
FastRoute builds a closed delivery tour on a directed road network:
warehouse → deliveries → warehouse, minimizing road length in meters.

Two computational stages:

1. **Shortest paths** between stops (Dijkstra / A*) — polynomial-time graph search.  
2. **Delivery order search** (Brute Force) — combinatorial; exhaustive cost grows as n!.

## 2. Dijkstra
Binary-heap Dijkstra is `O((V + E) log V)` for typical implementations. FastRoute uses it to:

- build the pairwise road-distance matrix, and  
- chain shortest paths for a fixed sample stop order (Compare All).

The Bad ladder tier uses linear-scan extract-min (implementation inefficiency). The Best tier uses bidirectional search (implementation optimization). Both still solve shortest paths.

## 3. A* Search
A* adds an admissible haversine heuristic in meters. On the same stop order, A* and Dijkstra must report the same tour distance when the heuristic is admissible. A* often settles fewer nodes.

**A* does not solve TSP.** It finds shortest paths for a fixed stop order. A* Bad/Semi/Best keep that **same sample order** (nearest-neighbor reordering was removed from the active ladder — see `OPTIMIZATION_TIER_COMPARABILITY.md`).

## 4. Brute-Force Route Search
Brute Force tries delivery permutations on the Dijkstra matrix. Exhaustive time is `O(n! × n)`. Exact mode is limited to small n (≤9). Larger n uses **sampled** search and must never be labeled a guaranteed optimum.

## 5. Why A*/Dijkstra can lose on total tour length
They follow the sampled stop order. Brute Force may reorder deliveries and find a shorter closed tour on the same matrix.

## 6. Runtime vs distance
Runtime measures computational work. Distance measures solution quality. A fast pathfinder on a fixed order is not automatically the shortest multi-stop tour.

## 7. Algorithmic Efficiency vs. Computational Hardness

| Concept | In FastRoute |
|---|---|
| **Inefficient algorithm / implementation** | Linear-scan Dijkstra; A* with h=0; tiny BF sample budgets |
| **Efficient course algorithm** | Heap Dijkstra; haversine A*; exact BF for tiny n |
| **Inherent hardness** | Choosing among n! delivery orders (TSP-style). Exact search is impractical as n grows even with a perfect implementation |

Improving Dijkstra’s heap does **not** make exhaustive TSP easy. Sampling BF makes large-n runs finish but **sacrifices** a proof of optimality. Related harder problems include metric TSP approximations and capacitated vehicle routing (often NP-hard).

## 8. Measured behavior
Use:

- `results/pathfinder_graph_scale.csv` for Dijkstra vs A* vs graph size  
- `results/brute_force_delivery_scale.csv` for order-search factorial growth  
- `results/scalability_results.csv` for multi-stop Compare All scaling  

Never invent numbers. Label skipped / unmeasured sizes honestly.

## 9. Terms
| Term | Meaning |
|---|---|
| Exact order search | Exhaustive Brute Force — optimal matrix tour when `exact=True` |
| Sampled order search | Budgeted permutations — best found, not proven optimal |
| Shortest-path engines | A* and Dijkstra — optimal road paths for a fixed order |
| Optimality gap | Percent longer than exhaustive BF on the same matrix, else unavailable |
