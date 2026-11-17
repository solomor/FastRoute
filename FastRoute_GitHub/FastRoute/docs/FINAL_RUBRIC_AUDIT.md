# Final Rubric Audit — FastRoute / CPS 3440 Fall 2026

## Critical finding: original assignment document not found

A full search of the FastRoute project folder (and common nearby locations under Downloads / Documents / Desktop / OneDrive) found **no original CPS 3440 project instructions PDF/DOCX, no grading rubric, and no CLO checklist from the professor**.

Files searched for (examples): `*rubric*`, `*assign*`, `*CPS*`, `*3440*`, `*syllabus*`, `*CLO*`, `*.pdf`, `*.docx`.

**Please provide the original assignment / rubric file** (PDF, DOCX, or Canvas export). Until that document is available, **point values cannot be verified** and this audit cannot award or deny rubric points with certainty.

Do **not** treat the table below as the professor’s official rubric. It is an **interim evidence map** against deliverables that commonly appear in Analysis of Algorithms final projects and against features already implemented in FastRoute. Status values reflect **code/docs evidence**, not self-grading.

## Interim requirement map (points unknown)

| Requirement | Points | Evidence in FastRoute | Status | Missing work |
|---|---:|---|---|---|
| Student-implemented Dijkstra on road graph | Unknown | `src/algorithms.py` `dijkstra`; used by `src/road_data.py` `distance_matrix` | Complete | Provide official rubric to confirm weight |
| Exact TSP: Brute Force | Unknown | `brute_force` in `src/algorithms.py`; UI cap ≤9 | Complete | Confirm required naming / complexity write-up matches syllabus |
| Exact TSP: Held-Karp DP | Unknown | `held_karp` in `src/algorithms.py`; UI cap ≤16 | Complete | Confirm DP exposition / pseudocode required in paper |
| Heuristic: Nearest Neighbor | Unknown | `nearest_neighbor` | Complete | — |
| Heuristic improvement: 2-Opt | Unknown | `two_opt` / `nearest_neighbor_two_opt` | Complete | — |
| Real road distances (not Euclidean-only) | Unknown | OSMnx drive graph + Dijkstra matrix; Folium street geometry | Complete | — |
| Interactive visualization / demo | Unknown | Streamlit `app.py`, live Leaflet animation, Dijkstra lab | Complete | Screenshots for GitHub/paper still missing |
| Fair experimental comparison | Unknown | Shared matrix in `compare` / `run_scalability`; prep time excluded | Complete | Refresh full offline benchmark CSV after methodology update |
| Complexity analysis (time/space) | Unknown | README table; Learn section; **no dedicated academic paper section yet** | Partially complete | Write paper section with pseudocode + proofs-of-correctness style explanations |
| Algorithmic efficiency vs computational hardness discussion | Unknown | `docs/ALGORITHMIC_EFFICIENCY_ANALYSIS.md` (audit-created) | Partially complete | Must appear in research paper / presentation, not only docs |
| Real-world / historical dataset use | Unknown | `data/food_delivery_dataset.csv`, `data/grubhub.csv`, Dataset Explorer | Complete | Document licensing/source provenance if professor requires citations |
| Automated tests | Unknown | `tests/` — 39 tests passing (2026-11-04 local run) | Complete | Keep suite green after any late edits |
| Research paper / written report | Unknown | **No paper PDF/DOCX found in repo** | Missing | Draft full paper using checklist |
| CLO reflections (if required) | Unknown | Not found | Cannot verify | Need assignment text |
| GitHub repository with meaningful history | Unknown | **No `.git` directory; `git` CLI not available in shell** | Missing | Initialize repo, meaningful commits, remote |
| Professional README + install instructions | Unknown | Root `README.md` (Windows PowerShell) | Complete | Add screenshots |
| GitHub Pages / project website | Unknown | No `docs/` site or `gh-pages` content published | Missing / Cannot verify | Confirm if required; if yes, build and deploy |
| Presentation (10–12 min + Q&A) | Unknown | Outline in `docs/PRESENTATION_CHECKLIST.md`; no slide deck in repo | Partially complete | Build slides; rehearse demo |
| Team contribution statement | Unknown | `CONTRIBUTIONS.md` is a stub only | Missing | Record real member work |
| License / OSM attribution | Unknown | OSM attribution in README; **no LICENSE file** | Partially complete | Add LICENSE if required; keep ODbL attribution |

### Totals

| Item | Value |
|---|---|
| Official rubric points available | **Unknown — assignment document not found** |
| Official points complete | **Cannot calculate** |
| Interim “Complete” rows above | 10 |
| Interim “Partially complete” | 4 |
| Interim “Missing” | 4 |
| Interim “Cannot verify” | 2 |

## Immediate ask

Upload or place the original CPS 3440 final-project instructions and grading rubric into this repository (for example `docs/assignment/`) and re-run Phase 1 so the table can use the **professor’s exact categories, terminology, and point values**.
