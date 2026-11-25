"""Correctness tests for A*, Dijkstra, and Brute-Force Route Search."""
import math
import tempfile
import unittest
from pathlib import Path
import networkx as nx
from src.algorithms import (
    astar,
    brute_force,
    brute_force_route_search,
    compare,
    dijkstra,
    haversine_heuristic,
    optimality_gaps,
    reconstruct,
    route_cost,
    sequential_route_order,
    tour_with_pathfinder,
)
from src.road_data import (
    distance_matrix,
    full_route_coordinates,
    route_distance_from_legs,
    to_adjacency,
)
from src.scalability import run_scalability, save_scalability_csv


ASYMMETRIC = [
    [0, 2, 9, 10],
    [1, 0, 6, 4],
    [15, 7, 0, 8],
    [6, 3, 12, 0],
]


def tiny_road_graph():
    """Tiny OSM-like graph with edge lengths ≥ geographic meters (A* heuristic stays admissible)."""
    graph = nx.DiGraph()
    for node, lat, lon in [(0, 40.0, -74.0), (1, 40.01, -74.0), (2, 40.01, -74.01), (3, 40.0, -74.01)]:
        graph.add_node(node, y=lat, x=lon)
    side = 1200
    diagonal = 1700
    for u, v, length in [
        (0, 1, side), (1, 0, side),
        (1, 2, side), (2, 1, side),
        (2, 3, side), (3, 2, side),
        (3, 0, side), (0, 3, side),
        (0, 2, diagonal), (2, 0, diagonal),
        (1, 3, diagonal), (3, 1, diagonal),
    ]:
        graph.add_edge(u, v, length=length)
    return graph


class TestCorrectnessAudit(unittest.TestCase):
    def test_dijkstra_known_path(self):
        graph = {'A': [('B', 4), ('C', 1)], 'C': [('B', 2), ('D', 5)], 'B': [('D', 1)], 'D': []}
        distances, previous, explored = dijkstra(graph, 'A', 'D')
        self.assertEqual(distances['D'], 4)
        self.assertEqual(reconstruct(previous, 'A', 'D'), ['A', 'C', 'B', 'D'])
        self.assertGreaterEqual(explored, 1)

    def test_dijkstra_rejects_negative_weight(self):
        with self.assertRaises(ValueError):
            dijkstra({'A': [('B', -1)], 'B': []}, 'A', 'B')

    def test_dijkstra_source_equals_target(self):
        distances, previous, _ = dijkstra({'A': [('B', 1)], 'B': []}, 'A', 'A')
        self.assertEqual(distances['A'], 0.0)
        self.assertEqual(reconstruct(previous, 'A', 'A'), ['A'])

    def test_astar_matches_dijkstra_on_tiny_graph(self):
        graph = tiny_road_graph()
        adjacency = to_adjacency(graph)
        distances_d, previous_d, _ = dijkstra(adjacency, 0, 2)
        distances_a, previous_a, _ = astar(adjacency, 0, 2, haversine_heuristic(graph, 2))
        self.assertEqual(distances_d[2], distances_a[2])
        self.assertEqual(reconstruct(previous_d, 0, 2), reconstruct(previous_a, 0, 2))

    def test_brute_force_enumerates_all_orders(self):
        route, cost, examined, exact = brute_force_route_search(ASYMMETRIC)
        self.assertTrue(exact)
        self.assertEqual(examined, math.factorial(3))
        self.assertEqual(route[0], 0)
        self.assertEqual(route[-1], 0)
        self.assertEqual(set(route[1:-1]), {1, 2, 3})
        self.assertEqual(cost, route_cost(ASYMMETRIC, route))
        alias_route, alias_cost, _ = brute_force(ASYMMETRIC)
        self.assertEqual(alias_cost, cost)
        self.assertEqual(route_cost(ASYMMETRIC, alias_route), cost)

    def test_tour_with_pathfinder_same_order_distances(self):
        graph = tiny_road_graph()
        adjacency = to_adjacency(graph)
        stops = [0, 1, 2, 3]
        order = sequential_route_order(len(stops))
        d_route, d_cost, _, _ = tour_with_pathfinder(adjacency, graph, stops, order, 'dijkstra')
        a_route, a_cost, _, _ = tour_with_pathfinder(adjacency, graph, stops, order, 'astar')
        self.assertEqual(d_route, a_route)
        self.assertAlmostEqual(d_cost, a_cost, places=9)

    def test_optimality_gap_formula(self):
        graph = tiny_road_graph()
        stops = [0, 1, 2, 3]
        adjacency = to_adjacency(graph)
        matrix = distance_matrix(graph, stops)
        results = optimality_gaps(compare(graph, stops, adjacency, matrix))
        exact = [row for row in results if row['exact']]
        self.assertTrue(exact)
        optimal = min(row['distance_m'] for row in exact)
        for row in results:
            expected = round(100 * (row['distance_m'] / optimal - 1), 2)
            self.assertEqual(row['Optimality gap (%)'], expected)

    def test_optimality_gap_unavailable_without_exact(self):
        graph = tiny_road_graph()
        stops = [0, 1, 2, 3]
        adjacency = to_adjacency(graph)
        matrix = distance_matrix(graph, stops)
        results = optimality_gaps(
            compare(graph, stops, adjacency, matrix, selected=["Dijkstra's Algorithm"])
        )
        self.assertIsNone(results[0]['Optimality gap (%)'])

    def test_route_geometry_matches_matrix_distance(self):
        graph = tiny_road_graph()
        stops = [0, 1, 2, 3]
        matrix = distance_matrix(graph, stops)
        route, cost, _, exact = brute_force_route_search(matrix)
        self.assertTrue(exact)
        rebuilt = route_distance_from_legs(graph, stops, route)
        self.assertAlmostEqual(cost, rebuilt, places=9)
        coords = full_route_coordinates(graph, stops, route)
        self.assertGreaterEqual(len(coords), len(route))

    def test_directed_adjacency_keeps_one_way(self):
        graph = nx.DiGraph()
        graph.add_node(1, y=0, x=0)
        graph.add_node(2, y=0, x=1)
        graph.add_edge(1, 2, length=10)
        adjacency = to_adjacency(graph)
        self.assertEqual(adjacency[1], [(2, 10.0)])
        self.assertEqual(adjacency[2], [])

    def test_scalability_shared_matrix_and_csv(self):
        graph = tiny_road_graph()
        rows = run_scalability(graph, counts=[3], trials=2, seed=1)
        self.assertTrue(rows)
        ok = [row for row in rows if row['status'] == 'ok']
        self.assertTrue(ok)
        self.assertIn('min_runtime_ms', ok[0])
        self.assertIn('max_runtime_ms', ok[0])
        self.assertIsNotNone(ok[0]['avg_runtime_ms'])
        gaps = {row['short_name']: row['optimality_gap_percent'] for row in ok}
        self.assertEqual(gaps['Brute Force'], 0.0)
        self.assertEqual(gaps['Dijkstra'], gaps['A*'])
        with tempfile.TemporaryDirectory() as folder:
            path = save_scalability_csv(rows, Path(folder) / 'scale.csv')
            self.assertTrue(path.is_file())


if __name__ == '__main__':
    unittest.main()
