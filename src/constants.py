"""Shared project constants with no internal imports (avoids Streamlit reload cycles)."""

PLACE = 'Jersey City, New Jersey, USA'
MAX_DELIVERY_DESTINATIONS = 1000
# Above this stop count, map polylines stay on streets but are point-budgeted for the browser.
LARGE_ROUTE_SIMPLIFY_STOPS = 120
# Max lat/lon vertices kept across one algorithm's map polyline on large tours.
LARGE_ROUTE_MAP_POINT_BUDGET = 12_000
MAX_MAP_MARKERS = 250
DEFAULT_MAX_SNAP_M = 500.0
# Exhaustive (n!) only stays interactive up to this many deliveries.
BRUTE_FORCE_EXACT_MAX_STOPS = 9
# Beyond that, Brute Force still runs up to MAX_DELIVERY_DESTINATIONS by
# evaluating a bounded sample of delivery orders (not a full proof of optimality).
BRUTE_FORCE_SAMPLE_BUDGET = 25_000
# Optimization-ladder budgets for Brute-Force Route Search (nested, same seed).
# Best extends Semi which extends Bad — larger budget ≠ faster algorithm.
BRUTE_FORCE_BAD_BUDGET = 100
BRUTE_FORCE_SEMI_BUDGET = BRUTE_FORCE_SAMPLE_BUDGET
BRUTE_FORCE_BEST_BUDGET = 300_000
BRUTE_FORCE_BEST_SEEDS = 1  # single nested seed sequence (not independent multi-seed)
# Hard participation limit — same as the app delivery slider.
BRUTE_FORCE_MAX_STOPS = MAX_DELIVERY_DESTINATIONS

MERGED_AREA_COMPONENTS = {
    'NYC / NJ metro (merged caches)': [
        'New York',
        'Jersey City, New Jersey, USA',
        'Brooklyn, New York, USA',
        'Queens, New York, USA',
        'Manhattan, New York, USA',
        'Bronx, New York, USA',
        'Staten Island, New York, USA',
    ],
}


def default_visible_algorithms(results, delivery_count=None):
    """Show every computed algorithm by default (map layering keeps both pathfinders readable)."""
    del delivery_count  # kept for call-site compatibility
    return [row['Algorithm'] for row in results]

