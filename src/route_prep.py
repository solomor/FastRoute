"""Prepare algorithm results with street-level geometries for the dashboard."""
from pathlib import Path

from .algorithms import compare, optimality_gaps
from .constants import DEFAULT_MAX_SNAP_M, LARGE_ROUTE_SIMPLIFY_STOPS, MAX_DELIVERY_DESTINATIONS
from .road_data import (
    apply_map_point_budget,
    distance_matrix,
    filter_stops_to_scc,
    points_in_bounds,
    route_distance_from_legs,
    route_leg_coordinates,
    sample_stops,
    snap_coordinates,
    stop_coordinates,
    street_legs_for_route,
    to_adjacency,
)
from .datasets import (
    clean_coordinates,
    coordinate_pair_label,
    dataset_coordinates,
    dataset_validation_summary,
    list_datasets,
    load_dataset,
)


def prepare_osm_experiment(graph, delivery_count, seed, selected_algorithms=None):
    if selected_algorithms is not None and len(selected_algorithms) == 0:
        raise ValueError('Select at least one algorithm before running an experiment.')
    if delivery_count < 1 or delivery_count > MAX_DELIVERY_DESTINATIONS:
        raise ValueError(f'Delivery count must be between 1 and {MAX_DELIVERY_DESTINATIONS}.')
    stops = sample_stops(graph, delivery_count + 1, seed)
    return _run(graph, stops, selected_algorithms, source='OpenStreetMap sampled intersections')


def prepare_dataset_experiment(
    graph,
    dataset_name,
    delivery_count,
    seed,
    selected_algorithms=None,
    warehouse_index=0,
    coordinate_pair=None,
    max_snap_m=DEFAULT_MAX_SNAP_M,
    exclude_far_snaps=True,
):
    if selected_algorithms is not None and len(selected_algorithms) == 0:
        raise ValueError('Select at least one algorithm before running an experiment.')
    if delivery_count < 1 or delivery_count > MAX_DELIVERY_DESTINATIONS:
        raise ValueError(f'Delivery count must be between 1 and {MAX_DELIVERY_DESTINATIONS}.')
    frame = load_dataset(dataset_name)
    pairs = dataset_coordinates(dataset_name)
    if not pairs:
        raise ValueError(f'{dataset_name} has no latitude/longitude columns')
    if coordinate_pair is None:
        lat_col, lon_col = pairs[0]
    else:
        lat_col, lon_col = coordinate_pair[0], coordinate_pair[1]
        normalized = {(a, b) for a, b in pairs}
        if (lat_col, lon_col) not in normalized:
            raise ValueError(
                f'Coordinate pair ({lat_col}, {lon_col}) is not available for {dataset_name}. '
                f'Available pairs: {pairs}'
            )
    validation = dataset_validation_summary(frame, lat_col, lon_col)
    valid = clean_coordinates(frame, lat_col, lon_col)
    # Wider padding helps large metro merges keep more dataset rows.
    padding = 0.05 if delivery_count >= 200 else 0.01
    local = points_in_bounds(valid, lat_col, lon_col, graph, padding=padding)
    if len(local) < delivery_count + 1:
        raise ValueError(
            f'Only {len(local)} valid {dataset_name} points fall inside the downloaded road area '
            f'using columns {lat_col}/{lon_col} (need {delivery_count + 1}). '
            'Choose **NYC / NJ metro (merged caches)** or **New York**, a matching coordinate pair, '
            'or lower the delivery count.'
        )
    target = delivery_count + 1
    # Oversample so snap / SCC filtering can still leave enough reachable stops.
    oversample = min(len(local), max(target, int(target * 1.35) + 25))
    sample = local.sample(n=oversample, random_state=seed).reset_index(drop=True)
    if warehouse_index < 0 or warehouse_index >= len(sample):
        warehouse_index = 0
    order = [warehouse_index] + [i for i in range(len(sample)) if i != warehouse_index]
    points = [(float(sample.loc[i, lat_col]), float(sample.loc[i, lon_col])) for i in order]
    snap = snap_coordinates(graph, points, max_snap_m=max_snap_m)
    if snap['stats']['rejected'] and not exclude_far_snaps:
        raise ValueError(
            f"{snap['stats']['rejected']} sampled point(s) snapped farther than {max_snap_m} m from a road. "
            'Increase the snap limit or enable excluding far points.'
        )
    if exclude_far_snaps:
        accepted_points = [
            (row['original_lat'], row['original_lon'])
            for row in snap['records'] if row['accepted']
        ]
        stops = [row['node'] for row in snap['records'] if row['accepted']]
        if len(stops) < 2:
            raise ValueError(
                'After applying the snap-distance limit, fewer than two locations remain. '
                'Increase the maximum snap distance or choose different points.'
            )
        raw_points = accepted_points
    else:
        stops = snap['nodes']
        raw_points = points

    stops, raw_points, dropped_scc = filter_stops_to_scc(graph, stops, raw_points)
    if len(stops) < 2:
        raise ValueError(
            'After keeping only mutually reachable road intersections, fewer than two stops remain. '
            'Use the NYC / NJ metro merged area or a single large city cache.'
        )
    if len(stops) > target:
        stops = stops[:target]
        raw_points = raw_points[:target]
    if len(stops) < target:
        raise ValueError(
            f'Only {max(0, len(stops) - 1)} mutually reachable snapped destinations remain '
            f'(requested {delivery_count}). '
            'Use **NYC / NJ metro (merged caches)** or **New York**, raise the snap limit, '
            'or lower the delivery count.'
        )

    experiment = _run(
        graph,
        stops,
        selected_algorithms,
        source=(
            f'{dataset_name} · {coordinate_pair_label(lat_col, lon_col)} '
            f'({lat_col}, {lon_col}) snapped to OSM roads'
        ),
        raw_points=raw_points,
    )
    experiment['coordinate_pair'] = (lat_col, lon_col)
    experiment['coordinate_pair_label'] = coordinate_pair_label(lat_col, lon_col)
    experiment['snap'] = snap
    experiment['dataset_validation'] = validation
    experiment['in_bounds_rows'] = len(local)
    experiment['usable_coordinate_rows'] = len(valid)
    experiment['dropped_outside_scc'] = dropped_scc
    experiment['requested_delivery_count'] = delivery_count
    experiment['actual_stop_count'] = max(0, len(stops) - 1)
    return experiment


def available_stop_sources():
    """OSM intersections always work; CSV sources only if the file is on disk."""
    sources = ['OpenStreetMap sampled intersections']
    for item in list_datasets():
        path = item.get('path')
        if item.get('coordinates') and path is not None and Path(path).is_file():
            sources.append(item['name'])
    return sources


def _needs_distance_matrix(selected_algorithms, stop_count):
    del stop_count  # matrix size follows the stop list; no separate delivery cap
    if selected_algorithms is None:
        return True
    return 'Brute-Force Route Search' in selected_algorithms


def _coordinates_from_legs(legs):
    coords = []
    for index, leg in enumerate(legs):
        if index and leg:
            coords.extend(leg[1:])
        else:
            coords.extend(leg)
    return coords


def _run(graph, stops, selected_algorithms, source, raw_points=None):
    adjacency = to_adjacency(graph)
    matrix = None
    if _needs_distance_matrix(selected_algorithms, len(stops)):
        matrix = distance_matrix(graph, stops)
    results = optimality_gaps(compare(graph, stops, adjacency, matrix, selected=selected_algorithms))
    coords = stop_coordinates(graph, stops)
    large_map = len(stops) > LARGE_ROUTE_SIMPLIFY_STOPS
    map_budgeted_any = False
    for row in results:
        # Always follow OSM street geometry — never stop-to-stop chords (those cut corners).
        legs = street_legs_for_route(graph, stops, row['Route'], row.get('node_paths'))
        applied = False
        if large_map:
            legs, applied = apply_map_point_budget(legs)
            map_budgeted_any = map_budgeted_any or applied
        row['legs'] = legs
        row['coordinates'] = _coordinates_from_legs(legs)
        if row.get('node_paths') or large_map:
            reconstructed = row['distance_m']
        else:
            reconstructed = route_distance_from_legs(graph, stops, row['Route'])
        row['map_simplified'] = bool(applied)
        row['Reconstructed distance (km)'] = round(reconstructed / 1000, 3)
        if abs(reconstructed - row['distance_m']) > 1.0:
            raise ValueError(
                f"Route geometry distance mismatch for {row['Algorithm']}: "
                f"matrix {row['distance_m']:.1f} m vs reconstructed {reconstructed:.1f} m"
            )
    return {
        'stops': stops,
        'stop_coords': coords,
        'raw_points': raw_points or coords,
        'matrix': matrix,
        'results': results,
        'source': source,
        'network_nodes': len(graph.nodes),
        'network_edges': len(graph.edges),
        'map_simplified': map_budgeted_any,
    }
