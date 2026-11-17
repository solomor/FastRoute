# Algorithmic Efficiency Analysis

Educational analysis for CPS 3440. Distances are **road meters**, not live travel time.

## 1. Delivery routing as a TSP
A warehouse and a set of delivery stops must be visited so that each stop appears once and the vehicle returns to the warehouse. If travel cost between every pair is known (here: shortest-path road distance), the decision problem is a classic **Traveling Salesperson Problem (TSP)** on a complete distance matrix.

## 2. Factorial growth of orderings
With `n` delivery stops (depot fixed), the number of distinct delivery orders is `n!`.

| Deliveries `n` | Orders `n!` |
|---:|---:|
| 4 | 24 |
| 5 | 120 |
| 6 | 720 |
| 7 | 5,040 |
| 8 | 40,320 |
| 9 | 362,880 |
| 10 | 3,628,800 |
| 12 | 479,001,600 |

## 3. Why Brute Force becomes impractical
Brute Force evaluates every order (and spends linear work summing edges). By ~10–12 deliveries, factorial growth makes exhaustive search too slow for interactive use. FastRoute therefore caps Brute Force at 9 deliveries.

## 4. How Held-Karp improves on Brute Force
Held-Karp stores the best way to reach each subset of deliveries ending at a particular stop. Overlapping subproblems are reused instead of re-enumerating full permutations. Complexity drops from factorial toward `O(n² 2ⁿ)`.

## 5. Why Held-Karp remains exponential
`2ⁿ` subsets still grow exponentially. Memory and time explode for large `n`. FastRoute caps Held-Karp at 16 deliveries for responsiveness.

## 6. Why Nearest Neighbor helps on larger instances
Nearest Neighbor builds one tour in `O(n²)` time. It scales to sizes where exact methods are skipped, at the cost of possibly longer routes.

## 7. How 2-Opt improves a heuristic route
2-Opt reorders segments of an existing tour and keeps changes that shorten the measured matrix cost. It often reduces Nearest Neighbor distance but can stop at a local minimum.

## 8. Faster ≠ shorter
Runtime measures **computational work**. Distance measures **solution quality**. Nearest Neighbor is usually fastest; exact methods (when they finish) guarantee the shortest matrix tour.

## 9. Experiments vs theory
Measured scalability rows (see `results/scalability_results.csv`) show Brute Force runtime rising sharply with `n`, Held-Karp rising more slowly than factorial but still steeply, and heuristics staying small. Exact distances match each other when both run; heuristics may sit above the optimum (positive optimality gap) or match it on easy instances.

## 10. Efficiency vs computational hardness
- **Algorithmic efficiency** asks how resource use grows for a chosen method (big-O, measured ms/memory).
- **Computational hardness** reminds us that exact TSP remains intractable in the general case; heuristics trade guarantees for speed.

### Distinctions graders care about
| Concept | Meaning in FastRoute |
|---|---|
| Exact algorithm | Brute Force, Held-Karp — optimal matrix tour when they complete |
| Heuristic | Nearest Neighbor, NN+2-Opt — fast, not guaranteed optimal |
| Shortest road distance | Objective (meters along OSM edges) |
| Solver runtime | TSP time only |
| Complexity | Asymptotic growth class |

Do not confuse road distance with traffic travel time. FastRoute does not model live congestion.
