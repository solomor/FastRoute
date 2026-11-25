import math
import unittest
import networkx as nx
from src.algorithms import (
    astar,
    brute_force,
    compare,
    dijkstra,
    haversine_heuristic,
    reconstruct,
    route_cost,
    sequential_route_order,
    tour_with_pathfinder,
)
from src.road_data import distance_matrix, to_adjacency


class TestAlgorithms(unittest.TestCase):
    def setUp(self):
        self.matrix = [
            [0, 2, 9, 10],
            [1, 0, 6, 4],
            [15, 7, 0, 8],
            [6, 3, 12, 0],
        ]
        self.graph = nx.DiGraph()
        for node, lat, lon in [(0, 40.0, -74.0), (1, 40.01, -74.0), (2, 40.01, -74.01), (3, 40.0, -74.01)]:
            self.graph.add_node(node, y=lat, x=lon)
        for u, v, length in [
            (0, 1, 1200), (1, 0, 1200),
            (1, 2, 1200), (2, 1, 1200),
            (2, 3, 1200), (3, 2, 1200),
            (3, 0, 1200), (0, 3, 1200),
            (0, 2, 1700), (2, 0, 1700),
            (1, 3, 1700), (3, 1, 1700),
        ]:
            self.graph.add_edge(u, v, length=length)
        self.stops = [0, 1, 2, 3]
        self.adjacency = to_adjacency(self.graph)

    def test_dijkstra(self):
        g = {'A': [('B', 4), ('C', 1)], 'C': [('B', 2), ('D', 5)], 'B': [('D', 1)], 'D': []}
        distances, previous, _ = dijkstra(g, 'A', 'D')
        self.assertEqual(distances['D'], 4)
        self.assertEqual(reconstruct(previous, 'A', 'D'), ['A', 'C', 'B', 'D'])

    def test_astar_matches_dijkstra(self):
        distances_d, _, _ = dijkstra(self.adjacency, 0, 2)
        distances_a, _, _ = astar(self.adjacency, 0, 2, haversine_heuristic(self.graph, 2))
        self.assertEqual(distances_d[2], distances_a[2])

    def test_brute_force(self):
        route, cost, examined = brute_force(self.matrix)
        self.assertEqual(examined, math.factorial(3))
        self.assertEqual(route[0], 0)
        self.assertEqual(route[-1], 0)
        self.assertEqual(cost, route_cost(self.matrix, route))

    def test_compare_three_algorithms(self):
        matrix = distance_matrix(self.graph, self.stops)
        results = compare(self.graph, self.stops, self.adjacency, matrix)
        self.assertEqual(len(results), 3)
        by_name = {row['Algorithm']: row for row in results}
        self.assertAlmostEqual(
            by_name['A* Search Algorithm']['distance_m'],
            by_name["Dijkstra's Algorithm"]['distance_m'],
            places=9,
        )
        self.assertEqual(by_name['A* Search Algorithm']['Route'], sequential_route_order(4))
        self.assertTrue(by_name['Brute-Force Route Search']['exact'])

    def test_tour_pathfinders_agree(self):
        order = sequential_route_order(4)
        _, d_cost, _, _ = tour_with_pathfinder(self.adjacency, self.graph, self.stops, order, 'dijkstra')
        _, a_cost, _, _ = tour_with_pathfinder(self.adjacency, self.graph, self.stops, order, 'astar')
        self.assertAlmostEqual(d_cost, a_cost, places=9)

    def test_brute_force_single_stop(self):
        self.assertEqual(brute_force([[0]])[1], 0)


if __name__ == '__main__':
    unittest.main()
