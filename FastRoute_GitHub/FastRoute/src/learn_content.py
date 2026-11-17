"""Beginner-friendly educational copy for FastRoute."""
from .algorithms import BRUTE_FORCE_MAX_STOPS, HELD_KARP_MAX_STOPS


DIJKSTRA_LESSON = {
    'name': 'Dijkstra (road distances)',
    'simple': 'Finds the shortest road path between two intersections using nonnegative street lengths.',
    'time': 'O((V + E) log V) with a binary heap (lazy decrease-key style)',
    'space': 'O(V + E) auxiliary space is a safe bound for this lazy-heap implementation (distance/previous maps plus heap entries)',
    'note': (
        'V = road intersections, E = directed road connections. '
        'Measured runtime is not the same as big-O complexity: constants, Python overhead, and graph size matter. '
        'Dijkstra prepares pairwise road costs; it does not choose the multi-stop delivery order.'
    ),
}


ALGORITHM_LESSONS = [
    {
        'name': 'Brute Force',
        'color': '#3B82F6',
        'exact': True,
        'simple': 'Tries every possible delivery order and keeps the shortest one.',
        'steps': [
            'Fix the warehouse as the start and end of the tour.',
            'List every possible order of the delivery stops.',
            'Add up the road distance for each full tour.',
            'Keep the order with the smallest total distance.',
        ],
        'time': 'O(n! × n)',
        'space': 'O(n) for the current tour (plus permutation generation overhead)',
        'optimal': 'Yes — it guarantees an optimal route for the distance matrix.',
        'pros': ['Always finds the shortest tour among all orders.', 'Easy to understand and verify on tiny examples.'],
        'cons': [
            'Factorial growth: each extra stop multiplies the work.',
            f'In this app it is capped at {BRUTE_FORCE_MAX_STOPS} deliveries for responsiveness.',
        ],
        'when': 'Best for teaching and for tiny instances where you need a proven optimum.',
    },
    {
        'name': 'Held-Karp',
        'color': '#22C55E',
        'exact': True,
        'simple': 'Remembers the best way to visit each subset of stops ending at a given stop, then builds the full tour from those pieces.',
        'steps': [
            'Store the best cost to reach each stop from the warehouse for every subset of visited deliveries.',
            'Grow the subset size one by one using previously saved answers.',
            'At the end, choose the best last stop and reconnect to the warehouse.',
            'Trace predecessors to recover the delivery order.',
        ],
        'time': 'O(n² 2ⁿ)',
        'space': 'O(n 2ⁿ) DP states',
        'optimal': 'Yes — it also guarantees an optimal route.',
        'pros': ['Much faster than Brute Force for moderate n.', 'Still exact, so it can validate heuristics.'],
        'cons': [
            'Memory and time still grow exponentially.',
            f'In this app it is capped at {HELD_KARP_MAX_STOPS} deliveries.',
        ],
        'when': 'Use when you need an exact answer on medium-sized tours and can afford the DP table.',
    },
    {
        'name': 'Nearest Neighbor',
        'color': '#F59E0B',
        'exact': False,
        'simple': 'From the current location, always go to the closest unvisited delivery, then return home.',
        'steps': [
            'Start at the warehouse.',
            'Look at every unvisited stop and pick the nearest by road distance.',
            'Repeat until every stop is visited.',
            'Return to the warehouse.',
        ],
        'time': 'O(n²)',
        'space': 'O(n)',
        'optimal': 'No — it can miss shorter global arrangements.',
        'pros': ['Very fast.', 'Simple to explain and implement.'],
        'cons': ['Can get trapped by locally good but globally poor choices.', 'No optimality guarantee.'],
        'when': 'Good baseline and a quick first route when response time matters.',
    },
    {
        'name': 'Nearest Neighbor + 2-Opt',
        'color': '#EF4444',
        'exact': False,
        'simple': 'Build a Nearest Neighbor tour, then try flipping pieces of the order to shorten the total distance.',
        'steps': [
            'Create an initial tour with Nearest Neighbor.',
            'Pick two edges in the tour and reconnect them in the 2-Opt way (reverse a segment).',
            'Accept the change only if the total road distance decreases.',
            'Repeat until no improving swap is found (or a pass limit is reached).',
        ],
        'time': 'O(p × n³) worst case in this implementation (full tour rescoring each candidate)',
        'space': 'O(n)',
        'optimal': 'No — it improves a starting route but may stop at a local optimum.',
        'pros': ['Often shortens the greedy tour.', 'Still much cheaper than exact search for larger n.'],
        'cons': ['Depends on the starting route.', 'Does not prove global optimality.'],
        'when': 'Use when you want a better heuristic route without paying for exact search.',
    },
]


def pipeline_steps():
    return [
        'Download the OpenStreetMap driving road network for the chosen area.',
        'Convert roads into a directed graph of intersections and edge lengths (meters).',
        'Use Dijkstra to compute shortest road distances between selected stops.',
        'Build an n×n road-distance matrix (including the warehouse).',
        'Run the four delivery-order algorithms on that matrix.',
        'Reconstruct the street geometry along each chosen order.',
        'Draw the colored routes on the interactive map and report measurements.',
    ]


def limitations_copy():
    return {
        'supports': [
            'One warehouse / depot',
            'One vehicle',
            'Multiple delivery locations',
            'One closed delivery tour returning to the warehouse',
            'Road-distance optimization in meters',
            'Exact and heuristic algorithm comparison',
        ],
        'does_not': [
            'Live traffic travel times',
            'Vehicle capacity / load limits',
            'Delivery time windows',
            'Multiple warehouses',
            'Multi-driver / multi-vehicle fleets',
            'Turn-by-turn commercial navigation',
        ],
    }
