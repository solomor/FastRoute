"""Beginner-friendly educational copy for FastRoute."""
from .constants import BRUTE_FORCE_EXACT_MAX_STOPS, BRUTE_FORCE_SAMPLE_BUDGET, MAX_DELIVERY_DESTINATIONS


DIJKSTRA_LESSON = {
    'name': "Dijkstra's Algorithm",
    'simple': 'Finds the shortest road path between two intersections using nonnegative street lengths.',
    'time': 'O((V + E) log V) with a binary heap (lazy decrease-key style)',
    'space': 'O(V + E) auxiliary space is a safe bound for this lazy-heap implementation',
    'note': (
        'V = road intersections, E = directed road connections. '
        'Dijkstra prepares pairwise road costs and can also draw a full multi-stop tour '
        'by chaining shortest paths in a fixed stop order.'
    ),
}


ALGORITHM_LESSONS = [
    {
        'name': 'A* Search Algorithm',
        'color': '#22C55E',
        'exact': False,
        'simple': (
            'Like Dijkstra, but uses a straight-line geographic estimate to aim toward the destination. '
            'It still finds a shortest road path when the heuristic never overestimates.'
        ),
        'steps': [
            'Start at the warehouse or current intersection.',
            'Score each candidate by distance traveled so far plus an estimated remaining distance.',
            'Always expand the most promising intersection next.',
            'Stop when the destination is settled, then reconstruct the path.',
        ],
        'time': 'O((V + E) log V) typical with a binary heap',
        'space': 'O(V + E)',
        'optimal': 'Yes for shortest paths when the heuristic is admissible (as with haversine meters here).',
        'pros': ['Often explores fewer intersections than Dijkstra.', 'Same optimal road distance as Dijkstra.'],
        'cons': ['Needs a good heuristic.', 'Does not by itself choose the best multi-stop delivery order.'],
        'when': 'Use to compare informed search against Dijkstra on real street networks.',
    },
    {
        'name': "Dijkstra's Algorithm",
        'color': '#F59E0B',
        'exact': False,
        'simple': 'Expands the closest unsettled intersection until the destination is reached.',
        'steps': [
            'Set the start distance to 0 and all others to infinity.',
            'Repeatedly settle the intersection with the smallest known distance.',
            'Relax outgoing road edges and update better distances.',
            'Reconstruct the path from predecessor links.',
        ],
        'time': DIJKSTRA_LESSON['time'],
        'space': DIJKSTRA_LESSON['space'],
        'optimal': 'Yes for shortest paths with nonnegative road lengths.',
        'pros': ['Classic, easy to explain.', 'Builds the road-distance matrix used by brute-force order search.'],
        'cons': ['May explore more of the map than A*.', 'Does not reorder deliveries by itself.'],
        'when': 'Use as the baseline shortest-path engine and matrix builder.',
    },
    {
        'name': 'Brute-Force Route Search',
        'color': '#3B82F6',
        'exact': True,
        'simple': 'Tries every possible delivery order and keeps the shortest full tour.',
        'steps': [
            'Fix the warehouse as the start and end of the tour.',
            'List every possible order of the delivery stops.',
            'Add up the road distance for each full tour using the distance matrix.',
            'Keep the order with the smallest total distance.',
        ],
        'time': 'O(n! × n)',
        'space': 'O(n) for the current tour (plus permutation generation overhead)',
        'optimal': 'Yes — it guarantees an optimal delivery order for the distance matrix.',
        'pros': ['Always finds the shortest tour among all orders.', 'Easy to understand on tiny examples.'],
        'cons': [
            'Factorial growth: each extra stop multiplies the work.',
            f'Full enumeration stays interactive only up to about {BRUTE_FORCE_EXACT_MAX_STOPS} deliveries.',
            f'Above that (up to {MAX_DELIVERY_DESTINATIONS}), FastRoute samples ≤ {BRUTE_FORCE_SAMPLE_BUDGET:,} orders — not a full proof.',
        ],
        'when': 'Best for proving the optimal multi-stop order on small instances; still usable as sampled search on large ones.',
    },
]


def pipeline_steps():
    return [
        'Download the OpenStreetMap driving road network for the chosen area.',
        'Convert roads into a directed graph of intersections and edge lengths (meters).',
        'Use Dijkstra (and optionally A*) to compute shortest road distances between stops.',
        'Build an n×n road-distance matrix (including the warehouse).',
        'Run A*, Dijkstra, and Brute-Force Route Search on those stops.',
        'Reconstruct the street geometry along each chosen route.',
        'Draw the colored routes on the interactive map and report measurements.',
    ]


def limitations_copy():
    return {
        'supports': [
            'One warehouse / depot',
            'One vehicle',
            'Multiple delivery stops',
            'Closed delivery tour',
            'Road-distance optimization in meters',
            'Student Dijkstra, A*, and brute-force order search',
        ],
        'does_not': [
            'Live traffic travel times',
            'Vehicle capacity limits',
            'Delivery time windows',
            'Multiple warehouses',
            'Multi-driver routing',
        ],
    }
