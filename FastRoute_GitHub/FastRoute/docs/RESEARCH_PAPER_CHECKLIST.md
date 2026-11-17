# Research Paper Checklist

## Status of existing paper
**No research paper or formal written report (PDF/DOCX/Markdown paper body) was found in the FastRoute repository.**  
`presentation/`, `figures/`, and `docs/` previously had no paper draft. This checklist is a readiness guide, not a completed paper.

Professor-specific CLO reflection prompts: **Cannot verify** until the original assignment is provided.

## Section checklist

| # | Section | Status | Notes / evidence |
|---:|---|---|---|
| 1 | Introduction | Missing | Need motivation: delivery routing, AoA learning goals |
| 2 | Problem statement | Missing | Warehouse + deliveries + return; minimize road meters |
| 3 | Background / related concepts | Missing | TSP, shortest paths, exact vs heuristic |
| 4 | Dataset description | Partially ready | Use `docs/DATASET_METHODOLOGY.md` measured stats; add citations |
| 5 | Methodology | Partially ready | OSM → graph → Dijkstra matrix → four solvers; see `BENCHMARK_METHODOLOGY.md` |
| 6 | Algorithm descriptions | Partially ready | Code + Learn section + `ALGORITHM_CORRECTNESS_AUDIT.md` |
| 7 | Pseudocode | Missing | Not yet written as paper figures |
| 8 | Correctness explanations | Partially ready | Tests + audit doc; still need prose in paper |
| 9 | Time and space complexity | Partially ready | README / efficiency analysis; copy into paper carefully |
| 10 | Experimental setup | Partially ready | Caps, trials, seed, excluded prep time |
| 11 | Benchmark results | Partially ready | `results/scalability_results.csv` measured; refresh before citing |
| 12 | Charts and tables | Partially ready | App can plot; export figures into `figures/` for the paper |
| 13 | Results discussion | Missing | Must discuss measured gaps, ties, skips honestly |
| 14 | Algorithmic Efficiency vs Computational Hardness | Partially ready | `ALGORITHMIC_EFFICIENCY_ANALYSIS.md` — integrate into paper |
| 15 | Limitations | Partially ready | README + Learn limitations; expand in paper |
| 16 | Conclusion | Missing | — |
| 17 | References | Missing | OSM, algorithms textbooks/papers, dataset sources |
| 18 | Required CLO reflections | Cannot verify | Need assignment language |

## Rules for writing
- Use only measured distances/runtimes/memory from actual runs.
- Label skipped algorithms and unavailable gaps.
- Do not claim CSVs are multi-stop GPS traces.
- Do not invent references.

## Suggested paper filename once drafted
`docs/paper/FastRoute_CPS3440_Report.md` (or PDF export after review).
