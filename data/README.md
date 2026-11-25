# Real-world datasets

FastRoute’s **primary** geographic inputs for the CPS 3440 portfolio are:

1. **OpenStreetMap driving roads** (graph / distances)
2. **Grubhub restaurant listings** (stop coordinates inside NYC / NJ metros)

The India food-delivery CSV is kept as a **secondary** tabular example only.

## 1. OpenStreetMap road network (required)

- **Source:** https://www.openstreetmap.org/
- **Acquisition:** OSMnx `graph_from_place` (live Overpass) or local cache under `data/graphs/`
- **License:** Open Database License (ODbL) — https://www.openstreetmap.org/copyright  
  Attribution: © OpenStreetMap contributors
- **Fields used:** node `y`/`x` (lat/lon); directed edge `length` (meters)
- **Preprocessing:** OSMnx simplify; parallel edges reduced to minimum length; stops restricted to the largest strongly connected component for round-trip reachability
- **Limitations:** lengths are road distance, not live traffic time; sampled intersections are not customer addresses; turn restrictions / closures are not fully modeled
- **Reproducibility:** record area name, download/cache date, `network_nodes` / `network_edges` from the app, seed, and delivery count in the paper

Default demo area: **Jersey City, New Jersey, USA**. Large stop counts: **New York** or **NYC / NJ metro (merged caches)**.

## 2. Grubhub restaurant listings — `grubhub.csv` (primary stops)

| Property | Value |
|---|---|
| Local file | `data/grubhub.csv` (~8,088 rows, 27 columns) |
| Public source | [Kaggle — Grubhub Restaurant Data](https://www.kaggle.com/datasets/polartech/grubhub-restaurant-data) |
| Publisher | BarkingData / polartech |
| License on Kaggle | Unknown — cite URL; follow course redistribution rules |
| Fields used for routing | `latitude`/`longitude` (restaurant) or `searched_lat`/`searched_lng` |
| Useful geography | NY metro (~3.5k rows), plus IL/CA/MA/NJ search metros |
| Role in FastRoute | Candidate warehouse/delivery coordinates snapped onto OSM |

**Limitation:** these are restaurant/search points, **not** historical multi-stop driver routes.

## 3. Food delivery records — `food_delivery_dataset.csv` (secondary only)

| Property | Value |
|---|---|
| Local file | `data/food_delivery_dataset.csv` (~38,964 rows) |
| Closest public schema match | [Kaggle — Zomato Delivery Operations Analytics](https://www.kaggle.com/datasets/saurabhbadole/zomato-delivery-operations-analytics-dataset) |
| Geography | India (not NJ/NY) |
| Role in FastRoute | Tabular exploration / Dataset Explorer only |

**Do not** use this file as the primary stop source with Jersey City or NYC OSM graphs — almost all points fall outside the map.

## Pipeline (all CSV stop sources)

1. Choose lat/lon column pair  
2. `clean_coordinates` — drop missing, non-finite, out-of-range, `(0,0)`  
3. `points_in_bounds` — keep rows near the downloaded graph bbox  
4. `snap_coordinates` — nearest OSM node (haversine meters, max-snap limit)  
5. Keep mutually reachable stops (SCC filter)  
6. Run student Dijkstra / A* / Brute-Force Route Search  

## User uploads

Drop CSV/JSON under `data/user/` via Dataset Explorer. Same cleaning/snapping rules apply. Provenance for uploads is “user-supplied” unless you document otherwise.

## What to cite in the paper

- OSM + ODbL attribution and the exact place name / graph size from one run  
- Grubhub Kaggle URL + accessed date + row count  
- Explicit statement that CSVs supply **locations**, while OSM supplies **road distances**  
