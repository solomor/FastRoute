# Final Rubric Audit — FastRoute / CPS 3440 Fall 2026

**Assignment source:** official Algorithm Engineering Portfolio Project text (archived in `docs/assignment/`).  
**Track:** 4 — Delivery Route Optimization.  
**Date:** 2026-11-25 (post GitHub root migration + Pages algorithm update).  
This audit estimates readiness from **repo evidence**. It is **not** a grade prediction.

## Scorecard (100 points)

| Category | Pts | Est. earned now | Status | Evidence | Gap to full credit |
|---|---:|---:|---|---|---|
| A. Real-World Problem & Dataset | 8 | **7–8** | Verified (software) | OSM + Grubhub; provenance docs | Cite download date + node/edge counts from FINAL pack |
| B. Algorithm Design & Implementation | 20 | **18–20** | Verified | Student Dijkstra/A*/BF; Bad→Semi→Best without NN order change; streaming BF | Defend student code in presentation |
| C. Complexity, Correctness & CLO Analysis | 17 | **12–15** | Partially complete | Theory docs + tests + CLO prompts in pack | Finish CLO prose in the paper |
| D. Experimental Design & Benchmarking | 15 | **12–14** | Verified / incomplete targets documented | Pathfinder 1k/10k completed; 100k incomplete (57 508 nodes); BF scale CSVs | Optional larger authentic OSM if available |
| E. Results, Visualization & Interpretation | 10 | **7–9** | Implemented but paper write-up pending | Maps, charts, improvement story, FINAL pack | Theory-vs-observed narrative in paper |
| F. GitHub Repository & Software Engineering | 10 | **7–9** | Verified | Public repo, LICENSE, tests, root layout, meaningful commits | Issues/PRs / screenshots optional polish |
| G. GitHub Pages Portfolio Website | 8 | **6–8** | Verified | https://solomor.github.io/FastRoute/ — Dijkstra / A* / Brute Force | Screenshots / paper & slides links when ready |
| H. Technical Paper | 7 | **1–2** | Partially complete | Evidence pack + prompts; no submitted 6–10 page PDF yet | Draft/edit/submit paper |
| I. Presentation & Technical Defense | 5 | **1–2** | Partially complete | Prompts/checklist | Slide deck + rehearsal |
| **TOTAL** | **100** | **~70–85** | — | Software + GitHub/Pages in place | Close H–I (paper + slides) for remaining points |

## Scientific repair highlights

- Active solvers: **Dijkstra**, **A\***, **Brute-Force Route Search** (Held-Karp / NN / 2-Opt retired).  
- A* Best = cached haversine, **same order** as Bad/Semi (NN removed from active ladder).  
- BF sampled mode = streaming with replacement (no budget-sized `seen` set).  
- Improvement story = Dijkstra original order vs BF order + Dijkstra.  
- Optimality gaps only when exhaustive BF exists; never fake 0%.  
- 100k graph target marked **incomplete**, not completed.

## Remaining limitations

- No authentic ≥100 000-node OSM graph in local caches.  
- Final PDF / slides still required for full rubric coverage.  
- Historical results archived under `results/historical/` — do not mix with new claims.
