# Real-world dataset

The app downloads the **OpenStreetMap (OSM) driving road network** for the area entered by the user, defaulting to **Jersey City, New Jersey, USA**, using OSMnx's `graph_from_place`.

- Source: https://www.openstreetmap.org/
- Data license: Open Database License (ODbL), https://www.openstreetmap.org/copyright
- Acquisition: live download via OSMnx; no fabricated road network is shipped.
- Records: number of nodes/edges depends on date, geographic boundary, and OSM updates; the app reports the actual counts.
- Fields: OSM node latitude/longitude; directed edges and `length` (meters).
- Preprocessing: OSMnx simplifies the road network; parallel edges are reduced to their minimum distance for our adjacency list. Stops are sampled from the largest strongly connected component to ensure round-trip reachability.
- Missing data: edges without finite nonnegative length are excluded; the experiment fails if any selected stop is unreachable.
- Limitations: stops are sampled intersections rather than actual customer addresses; lengths approximate road travel distance, not traffic time; road closures and vehicle restrictions are not modeled. The system is a research prototype, not a live dispatch/navigation service.
- Reproducibility: area name, stop count and seed are included in exported metadata. OSM changes over time; record acquisition date separately for your paper.

For the full project, document the download date, graph counts, hardware, Python/library versions, and dataset limitations in the paper.
