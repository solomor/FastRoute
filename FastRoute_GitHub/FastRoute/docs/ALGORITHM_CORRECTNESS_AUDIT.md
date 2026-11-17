# Algorithm Correctness Audit

Source of truth: `src/algorithms.py`, `src/road_data.py`, `src/route_prep.py`, and the unit tests under `tests/`.

Audit date: 2026-11-04. Claims below are limited to what the code and tests support.

---

## 1. Dijkstra

### What it does
Computes single-source shortest paths on a directed adjacency list with nonnegative edge weights. Used to build the road-distance matrix between warehouse/delivery intersections.

### How it is implemented
- Binary heap via `heapq` (`O((V+E) log V)` with the usual lazy-decrease pattern).
- Distance dictionary + predecessor map.
- Optional early exit when `target` is settled.
- Rejects negative weights.
- Optional `record_steps` for visualization; default return signature unchanged.

### Correctness findings
- Known-path test: A→C→B distance 3 (`tests/test_algorithms.py`, `tests/test_correctness_audit.py`).
- Directed one-way behavior verified (reverse unreachable).
- Unreachable targets: missing distance; `reconstruct` returns `[]`.
- Source == target returns `[source]`.
- Road conversion `to_adjacency` keeps direction and nonnegative lengths; parallel edges take min length.

### Time complexity
`O((V + E) log V)` with binary heap (as implemented).

### Space complexity
`O(V + E)` for the graph view plus `O(V)` for distances/previous/heap occupancy.

### Problems found
- Lazy heap may retain obsolete entries (standard and correct, but `explored` counts settled pops after stale skip, not unique nodes only when duplicates remain — acceptable for demo counters).
- Visualization step recording sorts a frontier preview and adds overhead **only** when `record_steps=True`.

### Recommended fixes
- None required for correctness. Optionally document that operation counters are educational, not asymptotic proofs.

---

## 2. Brute Force

### What it does
Enumerates every permutation of delivery indices `{1..n-1}`, forms closed tours `[0, …, 0]`, and keeps the minimum cost.

### How it is implemented
`itertools.permutations` over delivery stops; depot fixed at index 0.

### Correctness findings
- Classic 4-node matrix optimal cost 80 matches Held-Karp.
- Asymmetric matrix: examines exactly `(n-1)!` orders; closed tour; no duplicates.
- UI/solver skip when deliveries > 9 (`BRUTE_FORCE_MAX_STOPS`).

### Time complexity
`O((n-1)! · n)` with full tour cost recomputation each permutation (`n =` matrix order including depot).

### Space complexity
`O(n)` for the current route (plus permutation iterator state).

### Problems found
- None for correctness within the cap. Factorial cost is intentional.

### Recommended fixes
- Keep cap documented in paper/presentation so graders understand skips are intentional.

---

## 3. Held-Karp

### What it does
Exact subset DP over visited delivery masks with reconstruction of an optimal closed tour.

### How it is implemented
`dp[(mask, last)] = (cost, predecessor)`; fills by subset size; closes with return to depot; reconstructs order by walking predecessors.

### Correctness findings
- Agrees with Brute Force on symmetric and asymmetric small matrices (tests).
- Returns closed tours visiting each delivery once.
- Capped at 16 deliveries in UI/benchmarks.

### Time complexity
`O(n² 2ⁿ)` (standard Held-Karp; `n` includes depot in the usual TSP indexing with `2^{n-1}` delivery masks).

### Space complexity
`O(n 2ⁿ)` DP states.

### Problems found
- None observed on tested instances. Optimal routes may differ in order when multiple optima exist; costs match.

### Recommended fixes
- In the paper, state clearly that agreement is on **cost**, not necessarily identical permutation.

---

## 4. Nearest Neighbor

### What it does
From the depot, repeatedly appends the nearest unvisited delivery under the directed matrix, then returns to depot.

### How it is implemented
`min(remaining, key=lambda v: (matrix[current][v], v))` for deterministic ties.

### Correctness findings
- Valid closed tours; each delivery once; cost matches `route_cost`.
- Uses directed distances (asymmetric matrix tests).

### Time complexity
`O(n²)` selections.

### Space complexity
`O(n)`.

### Problems found
- No optimality guarantee (expected for a greedy heuristic).

### Recommended fixes
- Emphasize in presentation that “fast” ≠ “shortest”.

---

## 5. Nearest Neighbor + 2-Opt

### What it does
Seeds NN, then repeatedly tries reversing segments `[i..j]` and accepts strictly improving full-tour costs (supports directed costs via full recomputation).

### How it is implemented
Up to `max_passes=40`; first improvement within a pass continues scanning; stops when a pass finds no improvement. Optional swap history for animation.

### Correctness findings
- Tests show final cost ≤ seed cost; recorded swaps are improving; tour validity preserved.
- Full recomputation is slower than classic undirected delta formulas but correct for asymmetric road matrices.

### Time complexity
Worst-case roughly `O(p · n³)` with full rescoring per candidate (`p` passes, `O(n²)` pairs, `O(n)` cost).

### Space complexity
`O(n)` (+ swap history if recorded).

### Problems found
- Not globally optimal; may stop at local minima.
- Operation counter mixes NN examinations + 2-Opt candidate evaluations (documented as “operations”, not a single theoretical unit).

### Recommended fixes
- Keep reporting NN initial distance vs improved distance (already in Compare results).

---

## Cross-cutting pipeline checks

| Check | Evidence | Status |
|---|---|---|
| Same matrix for all solvers in one experiment | `route_prep._run` → `compare(matrix)` | Pass |
| Street geometry distance matches matrix tour | `route_distance_from_legs` tests | Pass |
| Stops from largest strongly connected component | `sample_stops` | Pass |
| One-way streets preserved | directed `DiGraph` / adjacency tests | Pass |

**Overall:** Implementations are consistent with tests. Do not claim formal proofs beyond what the course requires; the code behavior matches the educational descriptions.
