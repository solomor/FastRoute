# Dataset Methodology

Statistics below were measured from the CSV files on disk on 2026-11-04. Do not invent additional provenance beyond what is known.

## Important caveat
Historical delivery-related CSVs provide **records and coordinates**. They are **not** proven multi-stop driver route histories. FastRoute uses coordinates as candidate stop locations that are snapped onto an OSM road graph for algorithmic experiments.

## Built-in datasets

### Food delivery records — `data/food_delivery_dataset.csv`
| Property | Measured value |
|---|---|
| Rows | 38,964 |
| Columns | 22 |
| Duplicate rows | 0 |
| Coordinate columns | `Restaurant_latitude/longitude`, `Delivery_location_latitude/longitude` |
| Restaurant lat range | ≈ 9.96 … 30.91 |
| Restaurant lon range | ≈ 72.77 … 88.43 |
| Geographic reading | Coordinates consistent with **India**, not New Jersey |
| Notable nulls | Age 1,019; Ratings 1,055; `Time_Orderd` 835 |
| `City` values | Mostly categorical labels (`Metropolitian`, `Urban`, `Semi-Urban`), not US city names |

**Interpretation for FastRoute:** Useful for exploring tabular delivery attributes, but points generally **do not fall inside** Jersey City / NYC OSM downloads. Choosing this stop source with a NJ/NY map will often yield few or zero in-bounds points after filtering.

### Grubhub restaurant listings — `data/grubhub.csv`
| Property | Measured value |
|---|---|
| Rows | 8,088 |
| Columns | 27 |
| Duplicate rows | 0 |
| Coordinate columns | `latitude/longitude`, `searched_lat/searched_lng` |
| Restaurant lat range | ≈ 33.66 … 42.48 |
| Restaurant lon range | ≈ −118.42 … −70.98 |
| `searched_metro` | NY 3519, CH 1980, LA 1487, BO 1102 |
| `searched_state` | NY, IL, CA, MA, NJ (among others) |
| Notable nulls | `is_gh` 231; `restaurant_tags` 22 |

**Interpretation:** Restaurant listing / search scrape style data with US metros. Overlaps Brooklyn / New York / NJ OSM areas much better than the food-delivery India file.

## Loading and preprocessing (`src/datasets.py`, `src/road_data.py`)
1. List built-in sources and optional user files under `data/user/`.
2. Detect or register latitude/longitude column pairs.
3. `clean_coordinates` drops missing, non-finite, out-of-range, and (0,0) coordinates.
4. When used for routing, `points_in_bounds` keeps rows near the downloaded graph bbox.
5. `snap_coordinates` maps each selected lat/lon to its **true nearest** OSM intersection using haversine meters. Shared nodes are allowed. Points beyond the configured max snap distance are rejected/reported rather than silently relocated.
6. Dijkstra builds the directed road-distance matrix on those intersections.

## Licensing / attribution
- Road network: OpenStreetMap via OSMnx — © OpenStreetMap contributors (ODbL). See README.
- CSV provenance / redistribution license: **not documented inside this repository**. If the course requires citations, the team must supply the original download URLs/licenses before the paper is finalized.

## User uploads
Dataset Explorer can add CSV/JSON files. Same caveat applies: coordinates become experiment inputs after cleaning and snapping; they are not automatically “true historical routes.”
