# Dataset Methodology

Statistics measured from local CSV files (2026-11-22). Provenance lives in `src/datasets.py` (`DATASET_PROVENANCE`) and `data/README.md`.

## Primary vs secondary

| Priority | Dataset | Use in FastRoute |
|---|---|---|
| **Primary graph** | OpenStreetMap driving network | Road distances, pathfinding |
| **Primary stops** | Grubhub restaurant listings | NYC/NJ coordinate stops snapped to OSM |
| Secondary | Food delivery records (India) | Tabular / Dataset Explorer only — not NJ/NY demos |
| Demo fallback | OSM sampled intersections | Reproducible when CSV snap yield is low |

## Important caveat

Historical delivery-related CSVs provide **records and coordinates**. They are **not** proven multi-stop driver route histories. FastRoute snaps coordinates onto an OSM road graph for algorithmic experiments.

## OpenStreetMap

- Source: https://www.openstreetmap.org/ via OSMnx  
- License: ODbL — © OpenStreetMap contributors  
- Cache: `data/graphs/`  
- Report actual `network_nodes` / `network_edges` from each experiment in the paper  

## Grubhub restaurant listings — `data/grubhub.csv`

| Property | Measured / documented value |
|---|---|
| Rows | 8,088 |
| Columns | 27 |
| Public source | https://www.kaggle.com/datasets/polartech/grubhub-restaurant-data |
| License on Kaggle | Unknown (cite URL; follow redistribution rules) |
| Coordinate columns | `latitude`/`longitude`, `searched_lat`/`searched_lng` |
| Restaurant lat range | ≈ 33.66 … 42.48 |
| Restaurant lon range | ≈ −118.42 … −70.98 |
| `searched_metro` | NY 3519, CH 1980, LA 1487, BO 1102 |
| Notable nulls | `is_gh` 231; `restaurant_tags` 22 |

**Interpretation:** Best built-in stop source for Brooklyn / New York / NJ OSM areas.

## Food delivery records — `data/food_delivery_dataset.csv`

| Property | Measured / documented value |
|---|---|
| Rows | 38,964 |
| Columns | 22 |
| Closest public schema | https://www.kaggle.com/datasets/saurabhbadole/zomato-delivery-operations-analytics-dataset |
| Coordinate columns | Restaurant_* and Delivery_location_* |
| Geographic reading | **India**, not New Jersey |
| Notable nulls | Age 1,019; Ratings 1,055; `Time_Orderd` 835 |

**Interpretation:** Do **not** pair with NJ/NY maps as the primary portfolio demo.

## Loading and preprocessing (`src/datasets.py`, `src/road_data.py`)

1. List built-in sources (Grubhub first) and optional user files under `data/user/`.  
2. Detect or register latitude/longitude column pairs.  
3. `clean_coordinates` drops missing, non-finite, out-of-range, and (0,0) coordinates.  
4. `points_in_bounds` keeps rows near the downloaded graph bbox.  
5. `snap_coordinates` maps each selected lat/lon to its true nearest OSM intersection (haversine meters). Shared nodes are allowed. Points beyond the max snap distance are rejected/reported.  
6. Dijkstra builds the directed road-distance matrix when Brute-Force Route Search needs it.  

## User uploads

Dataset Explorer can add CSV/JSON files. Same caveat: coordinates become experiment inputs after cleaning and snapping; they are not automatically “true historical routes.”
