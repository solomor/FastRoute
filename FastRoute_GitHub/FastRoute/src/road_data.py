"""Download real OpenStreetMap streets with OSMnx, then use our own Dijkstra."""
import math
import pickle
import re
from pathlib import Path
import networkx as nx
from .algorithms import dijkstra, reconstruct

PLACE = 'Jersey City, New Jersey, USA'
GRAPH_DIR = Path(__file__).resolve().parents[1] / 'data' / 'graphs'
# Prefer accurately named local caches. Areas marked for download are not faked from nearby roads.
PLACE_PRESETS = [
    # Verified local caches (name matches the road geography)
    'Jersey City, New Jersey, USA',
    'New York',
    'Manhattan, New York, USA',
    'Brooklyn, New York, USA',
    'Queens, New York, USA',
    'Bronx, New York, USA',
    'Staten Island, New York, USA',
    'Lower Manhattan, New York, USA',
    'Midtown Manhattan, New York, USA',
    'Harlem, New York, USA',
    'Long Island City, New York, USA',
    'Williamsburg, New York, USA',
    'Downtown Brooklyn, New York, USA',
    'Park Slope, New York, USA',
    'Bushwick, New York, USA',
    'Astoria, New York, USA',
    'Flushing, New York, USA',
    'Jamaica, New York, USA',
    # Need a real OSM download — do not fake these from nearby city caches
    'Hoboken, New Jersey, USA',
    'Union City, New Jersey, USA',
    'Weehawken, New Jersey, USA',
    'West New York, New Jersey, USA',
    'Bayonne, New Jersey, USA',
    'Kearny, New Jersey, USA',
    'Elizabeth, New Jersey, USA',
    'Fort Lee, New Jersey, USA',
    'Secaucus, New Jersey, USA',
    'North Bergen, New Jersey, USA',
    'Paterson, New Jersey, USA',
    'New Brunswick, New Jersey, USA',
    'Princeton, New Jersey, USA',
    'Trenton, New Jersey, USA',
    'Yonkers, New York, USA',
    'New Rochelle, New York, USA',
    'White Plains, New York, USA',
    'Philadelphia, Pennsylvania, USA',
    'Cambridge, Massachusetts, USA',
    'Somerville, Massachusetts, USA',
    'Providence, Rhode Island, USA',
    'New Haven, Connecticut, USA',
    'Ann Arbor, Michigan, USA',
    'Evanston, Illinois, USA',
    'Berkeley, California, USA',
    'Palo Alto, California, USA',
]


def _ensure_pyproj():
    """Load pyproj before OSMnx. GeoPandas keeps a failed import for the whole process."""
    import importlib
    import sys
    existing = sys.modules.get('pyproj')
    if existing is not None and not hasattr(existing, 'CRS'):
        for name in list(sys.modules):
            if name == 'pyproj' or name.startswith('pyproj.'):
                del sys.modules[name]
    try:
        pyproj = importlib.import_module('pyproj')
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            'Road download needs pyproj, and Windows blocked that library '
            f'({exc}). In this folder run: .venv\\Scripts\\python.exe -m pip install --force-reinstall pyproj'
        ) from exc
    if not hasattr(pyproj, 'CRS'):
        raise RuntimeError('pyproj did not finish loading. Restart the app and try again.')
    compat = sys.modules.get('geopandas._compat')
    if compat is not None:
        compat.HAS_PYPROJ = True


def _place_slug(place):
    return re.sub(r'[^a-z0-9]+', '_', place.lower()).strip('_')[:100] or 'place'


def graph_cache_path(place=PLACE):
    return GRAPH_DIR / f'{_place_slug(place)}.pkl'


def list_cached_places():
    """Return preset place names that already have a local graph cache."""
    return [place for place in PLACE_PRESETS if has_cached_graph(place)]


def osm_area_options():
    """OpenStreetMap area dropdown values: cached presets first, then others."""
    cached = [place for place in PLACE_PRESETS if has_cached_graph(place)]
    pending = [place for place in PLACE_PRESETS if not has_cached_graph(place)]
    return cached + pending


def osm_area_label(place):
    """Sidebar label showing whether the area is already cached locally."""
    if has_cached_graph(place):
        return f'{place}  (cached)'
    return f'{place}  (needs download)'


def resolve_cache_path(place=PLACE):
    """Find an exact or close local cache for a typed place name."""
    exact = graph_cache_path(place)
    if exact.is_file():
        return exact
    slug = _place_slug(place)
    if not GRAPH_DIR.is_dir():
        return None
    files = list(GRAPH_DIR.glob('*.pkl'))
    for path in files:
        stem = path.stem
        # Prefer exact / prefix matches only. Avoid "new_york" matching
        # every "*_new_york_usa" typed place that is not actually cached.
        if stem == slug or stem.startswith(slug + '_') or slug.startswith(stem + '_'):
            return path
    # Common aliases: "New York City" / "NYC" -> new_york
    aliases = {
        'nyc': 'new_york',
        'new_york_city': 'new_york',
        'new_york_ny': 'new_york',
        'new_york_new_york': 'new_york',
        'new_york_usa': 'new_york',
        'jersey_city': 'jersey_city_new_jersey_usa',
        'hoboken': 'hoboken_new_jersey_usa',
        'union_city': 'union_city_new_jersey_usa',
        'weehawken': 'weehawken_new_jersey_usa',
        'west_new_york': 'west_new_york_new_jersey_usa',
        'bayonne': 'bayonne_new_jersey_usa',
        'secaucus': 'secaucus_new_jersey_usa',
        'north_bergen': 'north_bergen_new_jersey_usa',
        'kearny': 'kearny_new_jersey_usa',
        'harrison': 'harrison_new_jersey_usa',
        'newark': 'newark_new_jersey_usa',
        'elizabeth': 'elizabeth_new_jersey_usa',
        'paterson': 'paterson_new_jersey_usa',
        'passaic': 'passaic_new_jersey_usa',
        'hackensack': 'hackensack_new_jersey_usa',
        'fort_lee': 'fort_lee_new_jersey_usa',
        'englewood': 'englewood_new_jersey_usa',
        'teaneck': 'teaneck_new_jersey_usa',
        'montclair': 'montclair_new_jersey_usa',
        'bloomfield': 'bloomfield_new_jersey_usa',
        'new_brunswick': 'new_brunswick_new_jersey_usa',
        'princeton': 'princeton_new_jersey_usa',
        'trenton': 'trenton_new_jersey_usa',
        'brooklyn': 'brooklyn_new_york_usa',
        'manhattan': 'manhattan_new_york_usa',
        'queens': 'queens_new_york_usa',
        'bronx': 'bronx_new_york_usa',
        'the_bronx': 'bronx_new_york_usa',
        'staten_island': 'staten_island_new_york_usa',
        'yonkers': 'yonkers_new_york_usa',
        'new_rochelle': 'new_rochelle_new_york_usa',
        'white_plains': 'white_plains_new_york_usa',
        'long_island_city': 'long_island_city_new_york_usa',
        'lic': 'long_island_city_new_york_usa',
        'lower_manhattan': 'lower_manhattan_new_york_usa',
        'midtown': 'midtown_manhattan_new_york_usa',
        'midtown_manhattan': 'midtown_manhattan_new_york_usa',
        'harlem': 'harlem_new_york_usa',
        'williamsburg': 'williamsburg_new_york_usa',
        'downtown_brooklyn': 'downtown_brooklyn_new_york_usa',
        'park_slope': 'park_slope_new_york_usa',
        'bushwick': 'bushwick_new_york_usa',
        'astoria': 'astoria_new_york_usa',
        'flushing': 'flushing_new_york_usa',
        'jamaica': 'jamaica_new_york_usa',
        'philadelphia': 'philadelphia_pennsylvania_usa',
        'philly': 'philadelphia_pennsylvania_usa',
        'cambridge': 'cambridge_massachusetts_usa',
        'somerville': 'somerville_massachusetts_usa',
        'providence': 'providence_rhode_island_usa',
        'new_haven': 'new_haven_connecticut_usa',
        'ann_arbor': 'ann_arbor_michigan_usa',
        'evanston': 'evanston_illinois_usa',
        'berkeley': 'berkeley_california_usa',
        'palo_alto': 'palo_alto_california_usa',
    }
    target = aliases.get(slug)
    if target:
        path = GRAPH_DIR / f'{target}.pkl'
        if path.is_file():
            return path
    return None


def has_cached_graph(place=PLACE):
    return resolve_cache_path(place) is not None


def save_graph(graph, place=PLACE):
    path = graph_cache_path(place)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pickle.dumps(graph, protocol=pickle.HIGHEST_PROTOCOL))
    return path


def load_cached_graph(place=PLACE):
    path = resolve_cache_path(place)
    if path is None or not path.is_file():
        return None
    graph = pickle.loads(path.read_bytes())
    if len(graph.nodes) == 0:
        return None
    return graph


OVERPASS_MIRRORS = (
    'https://overpass-api.de/api',
    'https://overpass.kumi.systems/api',
    'https://overpass.openstreetmap.ru/api',
)


def download_graph(place=PLACE, use_cache=True, timeout_s=90):
    """Download a drive network, preferring a local cache when available.

    Local pickle caches avoid repeated Overpass downloads and let the app keep
    working when Windows Application Control blocks a fresh pyproj import.
    Tries several Overpass mirrors before failing.
    """
    if use_cache:
        cached = load_cached_graph(place)
        if cached is not None:
            return cached
    errors = []
    graph = None
    try:
        _ensure_pyproj()
        import osmnx as ox
        ox.settings.requests_timeout = timeout_s
        ox.settings.overpass_rate_limit = True
        for mirror in OVERPASS_MIRRORS:
            try:
                ox.settings.overpass_url = mirror
                graph = ox.graph_from_place(place, network_type='drive', simplify=True)
                break
            except Exception as exc:
                errors.append(f'{mirror}: {exc}')
                graph = None
    except Exception as exc:
        errors.append(str(exc))
        graph = None
    if graph is None:
        cached = load_cached_graph(place)
        if cached is not None:
            return cached
        detail = ' | '.join(errors[-3:]) if errors else 'unknown error'
        raise RuntimeError(
            f'Could not download roads for {place!r}. '
            'Use a smaller neighborhood (for example Jersey City or Brooklyn), '
            f'or pick a cached area. Details: {detail}'
        )
    if len(graph.nodes) == 0:
        raise RuntimeError('OpenStreetMap returned an empty road network')
    try:
        save_graph(graph, place)
    except OSError:
        pass
    return graph


def to_adjacency(graph):
    """Preserve direction; choose minimum length for parallel directed edges."""
    neighbors = {node: {} for node in graph.nodes}
    for u, v, attributes in graph.edges(data=True):
        length = float(attributes.get('length', math.inf))
        if math.isfinite(length) and length >= 0:
            neighbors[u][v] = min(neighbors[u].get(v, math.inf), length)
    return {u: list(v.items()) for u, v in neighbors.items()}


def sample_stops(graph, count, seed=42):
    """Choose reproducible stops from the largest strongly connected road component."""
    import random
    component = max(nx.strongly_connected_components(graph), key=len)
    nodes = sorted(component)
    if len(nodes) < count:
        raise ValueError('Not enough mutually reachable road intersections')
    return random.Random(seed).sample(nodes, count)


def distance_matrix(graph, stops):
    adjacency = to_adjacency(graph)
    matrix = []
    for start in stops:
        distances, _, _ = dijkstra(adjacency, start)
        row = [distances.get(target, math.inf) for target in stops]
        if any(not math.isfinite(value) for value in row):
            raise ValueError('Some stops are unreachable; choose a strongly connected component')
        matrix.append(row)
    return matrix


def graph_bounds(graph):
    lats = [data['y'] for _, data in graph.nodes(data=True)]
    lons = [data['x'] for _, data in graph.nodes(data=True)]
    return min(lats), max(lats), min(lons), max(lons)


DEFAULT_MAX_SNAP_M = 500.0


def geographic_distance_m(lat1, lon1, lat2, lon2):
    """Great-circle distance in meters (haversine). Do not treat degrees as meters."""
    radius = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def nearest_node(graph, lat, lon):
    """Return (node_id, snap_distance_m) for the geographically nearest intersection."""
    best_node = None
    best_m = math.inf
    for node, data in graph.nodes(data=True):
        dist_m = geographic_distance_m(lat, lon, data['y'], data['x'])
        if dist_m < best_m:
            best_m = dist_m
            best_node = node
    if best_node is None:
        raise ValueError('Road graph has no nodes to snap to')
    return best_node, best_m


def snap_coordinates(graph, points, max_snap_m=DEFAULT_MAX_SNAP_M, allow_shared_nodes=True):
    """Snap each (lat, lon) to its true nearest road node.

    Multiple deliveries may share the same OSM node. Locations are never silently
    moved to a distant unused intersection just to force unique IDs.

    Returns a dict with:
      nodes: accepted snapped node ids (order preserved; duplicates allowed)
      records: per-point details including original/snapped coords and meters
      stats: aggregate snapping statistics
    """
    if max_snap_m is not None and max_snap_m <= 0:
        raise ValueError('max_snap_m must be positive or None (unlimited)')
    records = []
    nodes = []
    for index, (lat, lon) in enumerate(points):
        node, snap_m = nearest_node(graph, float(lat), float(lon))
        snapped_lat = float(graph.nodes[node]['y'])
        snapped_lon = float(graph.nodes[node]['x'])
        accepted = max_snap_m is None or snap_m <= max_snap_m
        record = {
            'index': index,
            'original_lat': float(lat),
            'original_lon': float(lon),
            'node': node,
            'snapped_lat': snapped_lat,
            'snapped_lon': snapped_lon,
            'snap_distance_m': round(snap_m, 3),
            'accepted': accepted,
            'reason': None if accepted else f'Snap distance {snap_m:.1f} m exceeds limit {max_snap_m} m',
        }
        records.append(record)
        if accepted:
            nodes.append(node)
    accepted_records = [row for row in records if row['accepted']]
    node_counts = {}
    for node in nodes:
        node_counts[node] = node_counts.get(node, 0) + 1
    shared_locations = sum(1 for count in node_counts.values() if count > 1 for _ in range(count))
    snap_distances = [row['snap_distance_m'] for row in accepted_records]
    stats = {
        'requested': len(points),
        'accepted': len(accepted_records),
        'rejected': len(records) - len(accepted_records),
        'shared_node_locations': shared_locations,
        'unique_nodes': len(node_counts),
        'avg_snap_distance_m': round(sum(snap_distances) / len(snap_distances), 3) if snap_distances else None,
        'max_snap_distance_m': max(snap_distances) if snap_distances else None,
        'max_snap_limit_m': max_snap_m,
        'allow_shared_nodes': allow_shared_nodes,
    }
    return {'nodes': nodes, 'records': records, 'stats': stats}


def snap_nodes_only(graph, points, max_snap_m=DEFAULT_MAX_SNAP_M):
    """Convenience wrapper returning only accepted node ids (may contain duplicates)."""
    result = snap_coordinates(graph, points, max_snap_m=max_snap_m)
    if result['stats']['rejected']:
        raise ValueError(
            f"{result['stats']['rejected']} location(s) exceeded the {max_snap_m} m snap limit. "
            'Raise the limit, pick points closer to roads, or exclude far-away rows.'
        )
    if not result['nodes']:
        raise ValueError('No locations could be snapped to the road network')
    return result['nodes']


def points_in_bounds(frame, lat_col, lon_col, graph, padding=0.01):
    """Keep dataset rows whose coordinates fall inside the downloaded road area."""
    south, north, west, east = graph_bounds(graph)
    mask = (
        frame[lat_col].between(south - padding, north + padding)
        & frame[lon_col].between(west - padding, east + padding)
    )
    return frame.loc[mask].copy()


def stop_labels(count):
    return ['Warehouse' if i == 0 else f'Stop {i}' for i in range(count)]


def stop_coordinates(graph, stops):
    return [(graph.nodes[node]['y'], graph.nodes[node]['x']) for node in stops]


def route_leg_coordinates(graph, stops, order):
    """Return one street-level polyline per consecutive stop pair in the tour."""
    adjacency = to_adjacency(graph)
    legs = []
    for i, j in zip(order, order[1:]):
        _, previous, _ = dijkstra(adjacency, stops[i], stops[j])
        segment = reconstruct(previous, stops[i], stops[j])
        if not segment:
            raise ValueError('No road route between selected stops')
        legs.append([(graph.nodes[node]['y'], graph.nodes[node]['x']) for node in segment])
    return legs


def full_route_coordinates(graph, stops, order):
    legs = route_leg_coordinates(graph, stops, order)
    coords = []
    for index, leg in enumerate(legs):
        if index and leg:
            coords.extend(leg[1:])
        else:
            coords.extend(leg)
    return coords


def route_distance_from_legs(graph, stops, order):
    """Sum directed road lengths along the reconstructed tour (meters)."""
    adjacency = to_adjacency(graph)
    total = 0.0
    for i, j in zip(order, order[1:]):
        distances, previous, _ = dijkstra(adjacency, stops[i], stops[j])
        if stops[j] not in distances:
            raise ValueError('No road route between selected stops')
        path = reconstruct(previous, stops[i], stops[j])
        if not path:
            raise ValueError('No road route between selected stops')
        total += distances[stops[j]]
    return total
