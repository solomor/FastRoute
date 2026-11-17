# Team Contributions Checklist

`CONTRIBUTIONS.md` currently contains only a placeholder warning. **No individual contribution claims are recorded in the repository**, so this document does **not** assign work to named people.

## How to use this file
1. Each member lists **actual** work they can demo or explain.
2. Copy finalized bullets into `CONTRIBUTIONS.md` before submission.
3. Do not invent commits, hours, or authorship.

## Topic coverage map (roles to fill)

| Area | What “ready” looks like | Suggested evidence to attach |
|---|---|---|
| Dataset & preprocessing | Explain CSV columns, cleaning, in-bounds filter, snapping | Dataset Explorer demo; `DATASET_METHODOLOGY.md` |
| OSM road network | Download/cache, directed edges, SCC sampling | Sidebar presets; `road_data.py` |
| Dijkstra | Heap, relax/settle, unreachable, matrix build | Dijkstra lab + code walkthrough |
| Exact algorithms | Brute Force enumeration; Held-Karp DP reconstruct | Small `n` Compare All; tests |
| Heuristics | NN greedy choice; 2-Opt improving swaps only | Map colors orange/red; swap counts |
| Benchmarking | Shared matrix, trials, caps, excluded prep time | Experiments section; methodology doc |
| Visualization | Folium/Leaflet live draw, colors, markers | Play all animation |
| Testing | How to run unittest; what failures mean | `python -m unittest discover -s tests -v` |
| Research paper | Owns drafting sections / citations | Paper file once created |
| Presentation | Timing, demo machine, Q&A backups | `PRESENTATION_CHECKLIST.md` |

## Blank roster (fill with real names)

| Team member | Primary areas | Secondary areas | Demo responsibility |
|---|---|---|---|
| _TBD_ | | | |
| _TBD_ | | | |
| _TBD_ | | | |
| _TBD_ | | | |

## Integrity rule
If a member cannot explain a component without reading it line-by-line for the first time, do not list them as the owner of that component.
