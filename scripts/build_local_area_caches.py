"""Build accurately named area caches from New York / Jersey City parent graphs.

Each area is cropped around its real geographic center so the label matches the map.
"""
from __future__ import annotations
import math
import networkx as nx
from src.road_data import (
    PLACE_PRESETS,
    geographic_distance_m,
    graph_bounds,
    graph_cache_path,
    load_cached_graph,
    save_graph,
)

# Real place centers (lat, lon) and preferred crop radius in meters.
PLACE_SPECS = {
    'Hoboken, New Jersey, USA': ((40.7433, -74.0324), 2200),
    'Union City, New Jersey, USA': ((40.7796, -74.0238), 2200),
    'Weehawken, New Jersey, USA': ((40.7696, -74.0204), 1800),
    'West New York, New Jersey, USA': ((40.7856, -74.0093), 1800),
    'Bayonne, New Jersey, USA': ((40.6687, -74.1143), 3500),
    'Kearny, New Jersey, USA': ((40.7684, -74.1454), 3000),
    'Elizabeth, New Jersey, USA': ((40.6640, -74.2107), 3500),
    'Fort Lee, New Jersey, USA': ((40.8509, -73.9701), 2500),
    'Brooklyn, New York, USA': ((40.6500, -73.9500), 9000),
    'Manhattan, New York, USA': ((40.7830, -73.9710), 9000),
    'Queens, New York, USA': ((40.7280, -73.7950), 11000),
    'Bronx, New York, USA': ((40.8450, -73.8650), 7000),
    'Staten Island, New York, USA': ((40.5800, -74.1500), 9000),
    'Yonkers, New York, USA': ((40.9312, -73.8987), 4000),
    'New Rochelle, New York, USA': ((40.9115, -73.7826), 3500),
    'Long Island City, New York, USA': ((40.7440, -73.9490), 1800),
    'Lower Manhattan, New York, USA': ((40.7120, -74.0060), 1600),
    'Midtown Manhattan, New York, USA': ((40.7540, -73.9840), 1600),
    'Harlem, New York, USA': ((40.8120, -73.9460), 2000),
    'Williamsburg, New York, USA': ((40.7080, -73.9570), 1600),
    'Downtown Brooklyn, New York, USA': ((40.6930, -73.9860), 1400),
    'Park Slope, New York, USA': ((40.6710, -73.9810), 1600),
    'Bushwick, New York, USA': ((40.6940, -73.9210), 1800),
    'Astoria, New York, USA': ((40.7640, -73.9230), 2000),
    'Flushing, New York, USA': ((40.7650, -73.8330), 2200),
    'Jamaica, New York, USA': ((40.7030, -73.7960), 2500),
}


def nodes_within_radius(graph, lat, lon, radius_m):
    keep = []
    for node, data in graph.nodes(data=True):
        if geographic_distance_m(lat, lon, data['y'], data['x']) <= radius_m:
            keep.append(node)
    return keep


def merge_subgraphs(parents, node_sets):
    merged = nx.DiGraph()
    for (name, graph), nodes in zip(parents.items(), node_sets):
        if not nodes:
            continue
        sub = graph.subgraph(nodes)
        merged.add_nodes_from(sub.nodes(data=True))
        merged.add_edges_from(sub.edges(data=True))
    return merged


def largest_scc(graph, min_nodes=40):
    if len(graph.nodes) < min_nodes:
        return None
    component = max(nx.strongly_connected_components(graph), key=len)
    strong = graph.subgraph(component).copy()
    if len(strong.nodes) < min_nodes:
        return None
    return strong


def validate(graph, lat, lon, max_nearest_m=900):
    nearest = math.inf
    for _, data in graph.nodes(data=True):
        nearest = min(nearest, geographic_distance_m(lat, lon, data['y'], data['x']))
    if nearest > max_nearest_m:
        return False, f'nearest node {nearest:.0f} m from named center'
    south, north, west, east = graph_bounds(graph)
    if not (south <= lat <= north and west <= lon <= east):
        # Allow tiny float / waterfront miss if a road node is still close.
        if nearest > 400:
            return False, 'named center outside graph bounds'
    return True, f'nearest road {nearest:.0f} m'


def build_place(place, parents):
    (lat, lon), radius = PLACE_SPECS[place]
    node_sets = [nodes_within_radius(graph, lat, lon, radius) for graph in parents.values()]
    if sum(len(nodes) for nodes in node_sets) < 40:
        return None, f'too few parent nodes within {radius} m'
    merged = merge_subgraphs(parents, node_sets)
    strong = largest_scc(merged)
    if strong is None:
        return None, 'no strong component large enough'
    ok, reason = validate(strong, lat, lon)
    if not ok:
        return None, reason
    return strong, reason


def main():
    parents = {}
    for name in ('New York', 'Jersey City, New Jersey, USA'):
        graph = load_cached_graph(name)
        if graph is not None:
            parents[name] = graph
            print(f'Parent ready: {name} ({len(graph.nodes):,} nodes)')
    if not parents:
        raise SystemExit('Need New York and/or Jersey City caches.')

    built, removed, failed = [], [], []
    for place in PLACE_PRESETS:
        if place not in PLACE_SPECS:
            continue
        path = graph_cache_path(place)
        graph, detail = build_place(place, parents)
        if graph is None:
            if path.is_file() and place not in parents:
                path.unlink()
                removed.append(place)
            failed.append((place, detail))
            print(f'FAIL {place}: {detail}')
            continue
        save_graph(graph, place)
        south, north, west, east = graph_bounds(graph)
        print(
            f'OK   {place}: {len(graph.nodes):,} nodes / {len(graph.edges):,} edges '
            f'({detail}; lat {south:.4f}-{north:.4f}, lon {west:.4f}-{east:.4f})'
        )
        built.append(place)

    print('\nSummary')
    print(f'  accurate caches saved: {len(built)}')
    print(f'  removed bad caches:    {len(removed)}')
    print(f'  unavailable from local parents: {len(failed)}')
    for place, reason in failed:
        print(f'   - {place}: {reason}')


if __name__ == '__main__':
    main()
