"""Optional guided walkthrough for first-time users."""

DEMO_STEPS = [
    {
        'title': 'Welcome to FastRoute',
        'body': (
            'FastRoute compares A*, Dijkstra, and Brute-Force Route Search on real city streets. '
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
            'Dijkstra finds shortest road distances between every pair of selected stops. '
            'That matrix is the shared input for Brute-Force Route Search.'
        ),
    },
    {
        'title': 'Run the three algorithms',
        'body': (
            'Click Compare All. A* and Dijkstra draw tours along shortest road paths in the sampled '
            'stop order. Brute-Force Route Search tries every delivery order (with a size cap).'
        ),
    },
    {
        'title': 'Watch routes draw on the map',
        'body': (
            'On the map toolbar, press Play all to draw each colored route live along real streets. '
            'Green = A*, Orange = Dijkstra, Blue = Brute Force.'
        ),
    },
    {
        'title': 'Compare the results',
        'body': (
            'Open Compare Results to see distance, runtime, memory, work counters, and optimality gaps. '
            'Remember: fastest is not always shortest.'
        ),
    },
    {
        'title': 'Why the algorithms differed',
        'body': (
            'Read What Do These Results Mean? for an automatic explanation built only from measured '
            'values in the current experiment.'
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
