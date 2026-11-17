# Presentation Checklist (≈10–12 minutes + ≈3 minutes Q&A)

Confirm timing with the professor’s assignment. The outline below matches a typical CPS 3440 demo length.

## Demo outline

| Min | Step | What to show | Speaker tip |
|---:|---|---|---|
| 0–1 | Introduce FastRoute | Problem: warehouse → deliveries → warehouse on real streets | Say objective is **meters of road**, not traffic ETA |
| 1–2 | OSM network | Sidebar area preset; cached graph loads | Mention OpenStreetMap attribution |
| 2–4 | Dijkstra | Watch Dijkstra lab: pick two intersections, Step/Auto | “Shortest path between two points” |
| 4–6 | Four algorithms | Learn cards or one-sentence each + colors | Blue exact BF, Green HK, Orange NN, Red NN+2-Opt |
| 6–8 | Compare All | Build route → Compare All → Play all on map | Same matrix for fairness |
| 8–9 | Results table | Distance vs runtime vs memory; optimality gap help | Fastest ≠ shortest |
| 9–10 | Scalability | Experiments chart or CSV snippet | Show Brute Force skip beyond cap |
| 10–11 | Findings | Understanding Your Results panel | Use measured numbers only |
| 11–12 | Limitations + close | One vehicle, no traffic, no capacity/windows | Invite questions |

Controls: Guided Demo mode can pace newcomers; exit it for the graded live run if needed.

## Likely professor questions (short accurate answers)

1. **Why not use NetworkX shortest_path for the matrix?**  
   Course goal is a student Dijkstra implementation; NetworkX/OSMnx supply the road graph, not the TSP solvers.

2. **Is the matrix symmetric?**  
   Not necessarily. One-way streets make directed distances; 2-Opt therefore rescoring full tours instead of undirected deltas.

3. **Why cap Brute Force at 9?**  
   `(n)!` growth; interactive UI would freeze. Skips are labeled, not faked.

4. **Does NN+2-Opt guarantee optimality?**  
   No. It never accepts a worse tour than its current best, but can miss the global optimum.

5. **What is optimality gap?**  
   Percent longer than the best exact solver on the **same** matrix. Unavailable if no exact solver ran.

6. **Did you optimize travel time?**  
   No. Road length in meters only; no live traffic API in the model.

7. **Are the CSV rows real driver tours?**  
   No. They supply coordinates/attributes; FastRoute snaps points to OSM intersections for experiments.

8. **How do you know Held-Karp is correct?**  
   It matches Brute Force cost on small tested matrices; DP reconstructs a closed tour.

9. **What does runtime exclude?**  
   OSM download/cache and Dijkstra matrix build; only the TSP solver call is timed.

10. **Space vs time for Held-Karp?**  
    Time about `O(n² 2ⁿ)`, space about `O(n 2ⁿ)` states — still exponential.

## Pre-flight checklist
- [ ] Streamlit starts on this machine
- [ ] Cached OSM area loads quickly
- [ ] Compare All draws four colored routes
- [ ] Live animation Play works without full page reload
- [ ] Scalability or saved CSV available as backup if live OSM is slow
- [ ] Each teammate can answer their assigned topic (see team checklist)
