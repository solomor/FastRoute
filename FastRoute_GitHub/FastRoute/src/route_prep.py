"""Prepare algorithm results with street-level geometries for the dashboard."""
from .algorithms import compare, optimality_gaps
from .road_data import (
    DEFAULT_MAX_SNAP_M,
    distance_matrix,
    full_route_coordinates,
    points_in_bounds,
    route_distance_from_legs,
    route_leg_coordinates,
    sample_stops,
    snap_coordinates,
    stop_coordinates,
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
    local = points_in_bounds(valid, lat_col, lon_col, graph)
    if len(local) < delivery_count + 1:
        raise ValueError(
            f'Only {len(local)} valid {dataset_name} points fall inside the downloaded road area '
            f'using columns {lat_col}/{lon_col}. '
            'Choose a matching OpenStreetMap area, a different coordinate pair, '
            'or lower the delivery count.'
        )
    sample = local.sample(n=delivery_count + 1, random_state=seed).reset_index(drop=True)
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
        # Keep warehouse if it was accepted; otherwise first accepted becomes warehouse.
        raw_points = accepted_points
    else:
        stops = snap['nodes']
        raw_points = points
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
    return experiment


def available_stop_sources():
    sources = ['OpenStreetMap sampled intersections']
    for item in list_datasets():
        if item['coordinates']:
            sources.append(item['name'])
    return sources


def _run(graph, stops, selected_algorithms, source, raw_points=None):
    matrix = distance_matrix(graph, stops)
    results = optimality_gaps(compare(matrix, selected=selected_algorithms))
    coords = stop_coordinates(graph, stops)
    for row in results:
        row['coordinates'] = full_route_coordinates(graph, stops, row['Route'])
        row['legs'] = route_leg_coordinates(graph, stops, row['Route'])
        reconstructed = route_distance_from_legs(graph, stops, row['Route'])
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
    }
