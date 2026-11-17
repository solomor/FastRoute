"""Optional guided walkthrough for first-time users."""

DEMO_STEPS = [
    {
        'title': 'Welcome to FastRoute',
        'body': (
            'FastRoute compares delivery-routing algorithms on real city streets. '
            'You will build a tour that starts at a warehouse, visits deliveries, and returns home.'
        ),
    },
    {
        'title': 'Choose a warehouse area',
        'body': (
            'In Build Your Delivery Route, pick an OpenStreetMap area such as Jersey City. '
            'The warehouse is stop 0 in the sampled intersections (or a chosen dataset row).'
        ),
    },
    {
        'title': 'Select delivery locations',
        'body': (
            'Choose how many deliveries to visit and a random seed. '
            'You can also use uploaded dataset coordinates that fall inside the map area.'
        ),
    },
    {
        'title': 'Download the road network',
        'body': (
            'FastRoute downloads (or loads a cache of) the OSM driving network, then converts it '
            'into a directed graph of intersections and road lengths in meters.'
        ),
    },
    {
        'title': 'Dijkstra builds the distance matrix',
        'body': (
            'Before the four tour algorithms run, Dijkstra finds shortest road distances between '
            'every pair of selected stops. That matrix is the shared input for fair comparison.'
        ),
    },
    {
        'title': 'Run the four algorithms',
        'body': (
            'Click Compare All. Brute Force and Held-Karp search for exact tours (with size caps). '
            'Nearest Neighbor and NN + 2-Opt produce fast heuristic tours.'
        ),
    },
    {
        'title': 'Watch routes draw on the map',
        'body': (
            'On the map toolbar, press Play all to draw each colored route live along real streets. '
            'Blue, green, orange, and red correspond to the four solvers.'
        ),
    },
    {
        'title': 'Compare the results',
        'body': (
            'Open Compare Results to see distance, runtime, memory, operations, and optimality gaps. '
            'Remember: fastest is not always shortest.'
        ),
    },
    {
        'title': 'Why the algorithms differed',
        'body': (
            'Read Understanding Your Results for an automatic explanation built only from measured values '
            'in the current experiment.'
        ),
    },
    {
        'title': 'Know the limitations',
        'body': (
            'FastRoute is a simplified model: one vehicle, one warehouse, distance-only optimization, '
            'no live traffic, capacity, or time windows. See Learn How It Works for details.'
        ),
    },
]


def clamp_step(index):
    if index < 0:
        return 0
    if index >= len(DEMO_STEPS):
        return len(DEMO_STEPS) - 1
    return index
