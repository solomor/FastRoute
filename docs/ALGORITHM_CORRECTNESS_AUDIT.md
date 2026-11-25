# Algorithm correctness audit (post scientific repair)

Date: 2026-11-24. Source backup: `checkpoints/scientific_repair_20261124_185857.zip`.

## Dijkstra
- Nonnegative directed edges; binary-heap and naive variants agree on distances in tests.
- Bidirectional Best reuses one reverse adjacency per ladder run; distances match unidirectional heap Dijkstra within tolerance.
- Unreachable targets raise / reconstruct empty path as before.

## A*
- Uses an admissible haversine heuristic in meters on OSM node coordinates.
- Bad (h=0), Semi (haversine), Best (cached haversine) share the **same sample delivery order**.
- Nearest-neighbor order was **removed** from the active A* ladder (misleading tour comparison).
- Tests require Bad/Semi/Best tour distances to match within numerical tolerance.

## Brute-Force Route Search
- Exhaustive for ≤9 deliveries (default).
- Sampled mode is **streaming with replacement**: O(B×n) scoring time, O(n) auxiliary search space excluding the O(n²) matrix; no budget-sized `seen` set.
- Uniqueness of sampled permutations is **not** claimed.
- Ladder budgets are nested with one seed: 100 → 25 000 → 300 000.

## Optimality gaps
- Gaps use **exhaustive** Brute-Force Route Search as the exact reference when present on the same problem identity.
- Missing gaps stay `None` (never shown as 0%).
- Sampled BF alone → status `sampled_search_only`.

## Improvement story
- Before: original sample order + Dijkstra.
- After: BF-chosen order + same Dijkstra engine.
- Do not reuse historical NN-based ~92% distance claims.
