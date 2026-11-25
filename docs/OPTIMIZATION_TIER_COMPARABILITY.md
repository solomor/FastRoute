# Optimization ladder — what each tier changes

FastRoute’s **Bad → Semi → Best** ladder is educational. Tiers are **not** always pure speedups of the identical computational problem. Use this table before writing “Best is X% faster.”

## Shared experiment inputs

Every tier in a ladder run uses:

- the same OSM road graph  
- the same snapped stop list / depot  
- the same delivery **order** for Dijkstra and A* families  
- the same edge weights / road-distance objective  
- the same random seed for Brute-Force nested sampling  

Reverse adjacency for Dijkstra Best is **built once per ladder run and reused**.

## Dijkstra family (same objective)

| Tier | What changes | Same tour objective? | Distance comparable? | What improves |
|---|---|---|---|---|
| **Bad** | Linear-scan extract-min Dijkstra (`O(V²)`-style) | Yes — shortest path each leg, **sample stop order** | Yes (should match Semi/Best path cost) | Baseline data structure |
| **Semi** | Binary heap + stop when target settled | Yes — same order | Yes | Priority queue + early stop |
| **Best** | Bidirectional binary-heap Dijkstra | Yes — same order | Yes | Search from both ends |

**Fair comparisons:** runtime, nodes settled, memory.  
**Expected:** same (or extremely close) road distance; Best/Semi usually settle fewer nodes than Bad.  
Do **not** artificially slow Bad/Semi; measure actual performance.

## A* family (same order; heuristic implementation only)

| Tier | What changes | Same tour objective? | Distance comparable? | What improves |
|---|---|---|---|---|
| **Bad** | A* with **h = 0** (uninformed), sample order | Yes | Yes vs Semi/Best | Shows cost of no heuristic |
| **Semi** | A* with **haversine** heuristic, sample order | Yes | Yes | Informed search |
| **Best** | **Cached** haversine (precomputed radians + memo), **same sample order** | Yes | Yes — distances must match Semi within tolerance | Less repeated trig / cache hits |

**Critical rule:** Do **not** change delivery order in A* Best. Nearest-neighbor order was removed from the active ladder because it made distance comparisons scientifically misleading.

Compare Bad vs Semi vs Best on **nodes settled / runtime** with **matched distance**.

## Brute-Force family (same matrix objective; nested search budgets)

| Tier | What changes | Same objective? | Distance comparable? | Optimality guarantee? |
|---|---|---|---|---|
| **Bad** | Nested sample ≤ 100 orders (seed S) | Minimize matrix tour length | Best-found only | **Never** (unless *n!* ≤ 100) |
| **Semi** | Exact ≤9 deliveries; else nested sample ≤ 25 000 (extends Bad, seed S) | Yes | Best-found; exact when exhaustive | Only when exhaustive |
| **Best** | Exact ≤9; else nested sample ≤ 300 000 (extends Semi, seed S) | Yes | Best-found; exact when exhaustive | Only when exhaustive |

Sampled mode is **streaming with replacement** (O(n) auxiliary search space excluding the O(n²) matrix). Uniqueness of draws is **not** claimed.

**Fair comparisons:** candidate evaluations, runtime, best-found distance, memory.  
A **larger search budget is not a faster algorithm** — it trades more work for potentially better route quality.

## Before/after improvement story

Active workflow (not NN):

1. **Before:** original sample order + Dijkstra  
2. **After:** Brute-Force order + **same** Dijkstra  

Report distance change only from measured values (0% improvement is allowed).

## Summary for the paper

1. Dijkstra Bad/Semi/Best → implementation optimization of **shortest paths** (same tour).  
2. A* Bad/Semi/Best → heuristic quality / caching on a **fixed** tour.  
3. Brute Force tiers → nested search-budget policy on TSP-style order search (factorial hardness).  
4. Improvement story → order search quality under a fixed pathfinding engine.  
