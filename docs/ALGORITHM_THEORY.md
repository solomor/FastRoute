# Algorithm theory — FastRoute (CPS 3440)

Student-implemented solvers only: **Dijkstra**, **A\***, **Brute-Force Route Search**.

## Shared pipeline

1. Build a directed OSM road graph (nonnegative edge lengths in **meters**).  
2. Choose warehouse + delivery stops (sampled intersections or snapped dataset coordinates).  
3. **Pathfinding stage:** Dijkstra / A* compute shortest roads between consecutive stops.  
4. **Order-search stage (optional):** Brute Force searches delivery permutations on a Dijkstra distance matrix.

A* does **not** solve the multi-stop TSP by itself. It finds shortest paths for a given order.

---

## 1. Dijkstra’s Algorithm

**Purpose:** Shortest path on a directed graph with nonnegative weights.  
**Input:** Adjacency list `{u: [(v, w), ...]}`, source, optional target.  
**Output:** Distances, previous pointers, nodes settled.

### Pseudocode (heap / Semi tier)

```
DIJKSTRA(G, s, t):
  dist[s] ← 0; dist[v] ← ∞ for v ≠ s
  prev ← {}
  PQ ← {(0, s)}
  while PQ not empty:
    (d, u) ← extract-min(PQ)
    if d > dist[u]: continue          # stale heap entry
    if u = t: break                   # early stop (Semi)
    for each edge (u, v, w) in G:
      if dist[u] + w < dist[v]:
        dist[v] ← dist[u] + w
        prev[v] ← u
        insert (dist[v], v) into PQ
  return dist, prev
```

**Data structures:** binary heap (`heapq`), distance map, previous map.  
**Correctness:** Classic Dijkstra invariant for nonnegative weights; stale larger keys ignored.  
**Time (Semi):** O((V+E) log V) with binary heap.  
**Space:** O(V+E).  
**Best case:** target near source → early stop settles few nodes.  
**Worst case:** explore nearly all reachable vertices.  
**Assumptions:** no negative edges; directed one-way streets honored.  
**Limitations:** does not reorder deliveries.

**Bad tier:** linear-scan extract-min ≈ O(V² + E).  
**Best tier:** bidirectional heap search (same objective, fewer expansions when it helps).

---

## 2. A* Search

**Purpose:** Goal-directed shortest path with a heuristic.  
**Input:** Graph, source, target, heuristic h(v).  
**Output:** Distances/g-scores, previous, nodes settled.

### Pseudocode (haversine / Semi tier)

```
ASTAR(G, s, t, h):
  g[s] ← 0; closed ← ∅
  PQ ← {(h(s), 0, s)}
  while PQ not empty:
    (f, d, u) ← extract-min(PQ)
    if u ∈ closed: continue
    if d > g[u]: continue
    closed ← closed ∪ {u}
    if u = t: break
    for each edge (u, v, w):
      if g[u] + w < g[v]:
        g[v] ← g[u] + w
        prev[v] ← u
        insert (g[v] + h(v), g[v], v) into PQ
  return g, prev
```

**Heuristic:** great-circle meters between node coordinates and target (`haversine_heuristic`).  
Edge lengths are OSM road meters; chord distance ≤ road length under normal OSM data → **admissible**. On planar-ish street networks it is treated as consistent enough for practice; we **verify** A* distance equals Dijkstra on the same pair in tests.

**Bad tier:** h(v)=0 (uninformed; same sample delivery order).  
**Semi tier:** haversine heuristic; **same sample delivery order**.  
**Best tier:** cached haversine (`haversine_heuristic_cached` — precomputed radians + memo); **same sample delivery order**. Distances must match Semi within numerical tolerance. Nearest-neighbor order is **not** used (it would change the combinatorial problem).

**Time:** O((V+E) log V) typical; often fewer settlements than Dijkstra with a good h.  
**Space:** O(V+E); Best adds O(V) coordinate/heuristic caches reused across tour legs.

---

## 3. Brute-Force Delivery Route Search

**Purpose:** Search delivery **orders** on a complete distance matrix (depot = index 0).  
**Input:** (n×n) nonnegative matrix of road distances; optional sample budget.  
**Output:** Closed route `[0, …, 0]`, cost, permutations examined, `exact` flag.

### Pseudocode

```
BRUTE_FORCE(matrix, budget=None, seed):
  deliveries ← {1..n-1}
  best ← ∞; keep only best route
  consider identity order first
  if budget is None and |deliveries| ≤ 9:
    for every permutation π of deliveries:   # exhaustive
      score [0]+π+[0]
    return best, exact=True
  else:                                     # streaming sample WITH REPLACEMENT
    rng ← Random(seed)
    while evaluations < budget:
      π ← shuffle(deliveries)                # may repeat prior draws
      score [0]+π+[0]                        # discard π after scoring
    return best, exact=False                 # uniqueness NOT claimed
```

**Correctness (exhaustive):** evaluates every tour; returns a minimum-cost Hamiltonian cycle on the matrix with fixed depot.  
**Sampled mode:** seeded random draws with replacement; retains only the best route — **not** a uniqueness-filtered sample set.  
**Time:** O(n! · n) exhaustive; O(B · n) sampled candidate scoring.  
**Auxiliary search space:** O(n) in streaming sampled mode (no budget-sized `seen` set), excluding the O(n²) distance matrix.  
**Hardness:** order search is TSP-style; factorial growth — improving the implementation does not remove combinatorial explosion. Nested ladder budgets (100 → 25 000 → 300 000, same seed) trade **more work for potentially better quality**, not speed.

---

## Algorithmic Efficiency vs. Computational Hardness

**Efficiency** means better data structures and search control for a problem in P (or a fixed instance size): heap Dijkstra vs linear-scan Dijkstra; A* heuristic vs h=0.

**Hardness** means the multi-stop **order** problem grows as n!: exhaustive Brute Force becomes impractical long before road graphs run out of memory. Sampled search trades the optimality guarantee for runtime.

FastRoute therefore separates:

- pathfinding benchmarks (graph size; Dijkstra vs A*), and  
- order-search benchmarks (delivery count; exhaustive vs sampled).  
