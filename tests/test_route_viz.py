import unittest
import networkx as nx
from src.algorithms import (
    ALGORITHMS,
    ALGORITHM_COLORS,
    brute_force_route_search,
    compare,
    optimality_gaps,
    route_cost,
    sequential_route_order,
    tour_with_pathfinder,
)
from src.map_viz import (
    animation_frame_coords,
    build_comparison_map,
    build_live_animation_html,
    progressive_algorithm_overlays,
)
from src.road_data import (
    distance_matrix,
    full_route_coordinates,
    nearest_node,
    route_distance_from_legs,
    route_leg_coordinates,
    snap_coordinates,
    to_adjacency,
)


def tiny_road_graph():
    graph = nx.DiGraph()
    coords = {
        0: (40.00, -74.00),
        1: (40.01, -74.00),
        2: (40.01, -74.01),
        3: (40.00, -74.01),
        4: (40.005, -74.005),
    }
    for node, (lat, lon) in coords.items():
        graph.add_node(node, y=lat, x=lon)
    # Lengths stay at/above geographic meters so haversine A* remains admissible.
    edges = [
        (0, 1, 1200), (1, 0, 1200),
        (1, 2, 1200), (2, 1, 1200),
        (2, 3, 1200), (3, 2, 1200),
        (3, 0, 1200), (0, 3, 1200),
        (0, 4, 900), (4, 0, 900),
        (4, 2, 900), (2, 4, 900),
        (1, 4, 900), (4, 1, 900),
        (3, 4, 900), (4, 3, 900),
        (0, 2, 1700), (2, 0, 1700),
        (1, 3, 1700), (3, 1, 1700),
    ]
    for u, v, length in edges:
        graph.add_edge(u, v, length=length)
    return graph


class TestRouteVisualization(unittest.TestCase):
    def setUp(self):
        self.graph = tiny_road_graph()
        self.stops = [0, 1, 2, 3]
        self.adjacency = to_adjacency(self.graph)
        self.matrix = distance_matrix(self.graph, self.stops)

    def test_brute_force_closed_tour(self):
        route, cost, examined, exact = brute_force_route_search(self.matrix)
        self.assertTrue(exact)
        self.assertEqual(route[0], 0)
        self.assertEqual(route[-1], 0)
        self.assertEqual(set(route[1:-1]), {1, 2, 3})
        self.assertEqual(route_cost(self.matrix, route), cost)
        self.assertEqual(examined, 6)

    def test_astar_and_dijkstra_same_sample_order_distance(self):
        order = sequential_route_order(len(self.stops))
        _, d_cost, _, _ = tour_with_pathfinder(
            self.adjacency, self.graph, self.stops, order, 'dijkstra'
        )
        _, a_cost, _, _ = tour_with_pathfinder(
            self.adjacency, self.graph, self.stops, order, 'astar'
        )
        self.assertAlmostEqual(d_cost, a_cost, places=6)

    def test_reconstructed_distance_matches_matrix_route(self):
        results = compare(self.graph, self.stops, self.adjacency, self.matrix)
        for row in results:
            reconstructed = route_distance_from_legs(self.graph, self.stops, row['Route'])
            self.assertAlmostEqual(reconstructed, row['distance_m'], places=6)
            coords = full_route_coordinates(self.graph, self.stops, row['Route'])
            self.assertGreaterEqual(len(coords), 2)
            legs = route_leg_coordinates(self.graph, self.stops, row['Route'])
            self.assertEqual(len(legs), len(row['Route']) - 1)

    def test_snap_and_nearest_node(self):
        node, meters = nearest_node(self.graph, 40.0001, -74.0001)
        self.assertEqual(node, 0)
        self.assertLess(meters, 100)
        snapped = snap_coordinates(self.graph, [(40.01, -74.00), (40.00, -74.01), (40.005, -74.005)])
        self.assertEqual(len(snapped['nodes']), 3)
        self.assertEqual(snapped['stats']['accepted'], 3)
        self.assertGreaterEqual(snapped['stats']['unique_nodes'], 1)

    def test_compare_all_colors_and_gaps(self):
        results = optimality_gaps(compare(self.graph, self.stops, self.adjacency, self.matrix))
        self.assertEqual(len(results), len(ALGORITHMS))
        names = {row['Algorithm'] for row in results}
        self.assertEqual(names, set(ALGORITHMS))
        for row in results:
            self.assertEqual(row['Color'], ALGORITHM_COLORS[row['Algorithm']])
            if row['exact']:
                self.assertEqual(row['Optimality gap (%)'], 0.0)
            else:
                self.assertGreaterEqual(row['Optimality gap (%)'], 0.0)

    def test_folium_map_and_animation_helpers(self):
        results = compare(self.graph, self.stops, self.adjacency, self.matrix)
        for row in results:
            row['coordinates'] = full_route_coordinates(self.graph, self.stops, row['Route'])
            row['legs'] = route_leg_coordinates(self.graph, self.stops, row['Route'])
        stop_coords = [(self.graph.nodes[s]['y'], self.graph.nodes[s]['x']) for s in self.stops]
        fmap = build_comparison_map(stop_coords, results)
        html = fmap.get_root().render()
        self.assertIn('leaflet', html.lower())
        partial = animation_frame_coords(results[0]['legs'], 2)
        self.assertGreaterEqual(len(partial), 2)
        overlays, statuses, highlights = progressive_algorithm_overlays(results, 2, self.matrix)
        self.assertEqual(len(overlays), len(results))
        self.assertEqual(len(statuses), len(results))
        self.assertTrue(highlights)
        animated = build_comparison_map(
            stop_coords,
            results,
            partial_routes=overlays,
            draw_full_routes=False,
            highlight_stops=highlights,
        )
        self.assertIn('progress', animated.get_root().render().lower())
        live = build_live_animation_html(stop_coords, results, autoplay=True, speed='Fast')
        self.assertIn('leaflet', live.lower())
        self.assertIn('Play all', live)
        self.assertIn('setInterval', live)

    def test_adjacency_nonnegative(self):
        adjacency = to_adjacency(self.graph)
        for _, edges in adjacency.items():
            for _, weight in edges:
                self.assertGreaterEqual(weight, 0)


if __name__ == '__main__':
    unittest.main()
