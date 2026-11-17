"""Additional correctness tests for CPS 3440 audit coverage."""
import math
import unittest
import networkx as nx
from src.algorithms import (
    brute_force,
    compare,
    dijkstra,
    held_karp,
    nearest_neighbor,
    nearest_neighbor_two_opt,
    optimality_gaps,
    reconstruct,
    route_cost,
    two_opt,
)
from src.road_data import (
    distance_matrix,
    full_route_coordinates,
    route_distance_from_legs,
    to_adjacency,
)
from src.scalability import run_scalability, save_scalability_csv
from pathlib import Path
import tempfile


ASYMMETRIC = [
    [0, 2, 9, 10],
    [1, 0, 6, 4],
    [15, 7, 0, 8],
    [6, 3, 12, 0],
]


def tiny_road_graph():
    graph = nx.DiGraph()
    for node, lat, lon in [(0, 40.0, -74.0), (1, 40.01, -74.0), (2, 40.01, -74.01), (3, 40.0, -74.01)]:
        graph.add_node(node, y=lat, x=lon)
    for u, v, length in [
        (0, 1, 100), (1, 0, 100),
        (1, 2, 100), (2, 1, 100),
        (2, 3, 100), (3, 2, 100),
        (3, 0, 100), (0, 3, 100),
        (0, 2, 500), (2, 0, 500),
        (1, 3, 500), (3, 1, 500),
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

    def test_brute_force_enumerates_all_orders(self):
        route, cost, examined = brute_force(ASYMMETRIC)
        self.assertEqual(examined, math.factorial(3))
        self.assertEqual(route[0], 0)
        self.assertEqual(route[-1], 0)
        self.assertEqual(set(route[1:-1]), {1, 2, 3})
        self.assertEqual(cost, route_cost(ASYMMETRIC, route))

    def test_held_karp_matches_brute_force_asymmetric(self):
        b_route, b_cost, _ = brute_force(ASYMMETRIC)
        h_route, h_cost, states = held_karp(ASYMMETRIC)
        self.assertEqual(b_cost, h_cost)
        self.assertEqual(route_cost(ASYMMETRIC, h_route), h_cost)
        self.assertEqual(h_route[0], 0)
        self.assertEqual(h_route[-1], 0)
        self.assertEqual(set(h_route[1:-1]), {1, 2, 3})
        self.assertGreater(states, 0)
        # Exact solvers may return different optimal orderings with equal cost.
        self.assertEqual(route_cost(ASYMMETRIC, b_route), route_cost(ASYMMETRIC, h_route))

    def test_nearest_neighbor_visits_each_once(self):
        route, cost, ops = nearest_neighbor(ASYMMETRIC)
        self.assertEqual(route[0], 0)
        self.assertEqual(route[-1], 0)
        self.assertEqual(len(route), 5)
        self.assertEqual(len(set(route[1:-1])), 3)
        self.assertEqual(cost, route_cost(ASYMMETRIC, route))
        self.assertGreater(ops, 0)

    def test_two_opt_never_worsens(self):
        seed_route, seed_cost, _ = nearest_neighbor(ASYMMETRIC)
        improved, improved_cost, _, detail = nearest_neighbor_two_opt(ASYMMETRIC, record_swaps=True)
        self.assertLessEqual(improved_cost + 1e-12, seed_cost)
        self.assertEqual(detail['initial_distance_m'], seed_cost)
        for swap in detail['swaps']:
            self.assertLess(swap['after_cost'] + 1e-12, swap['before_cost'])
        self.assertEqual(improved[0], 0)
        self.assertEqual(improved[-1], 0)
        self.assertEqual(set(improved[1:-1]), {1, 2, 3})

    def test_two_opt_rejects_worsening_candidate(self):
        # Start from an already-optimal small tour; 2-Opt must not increase cost.
        optimal_route, optimal_cost, _ = held_karp([[0, 1, 1], [1, 0, 1], [1, 1, 0]])
        route, cost, _ = two_opt([[0, 1, 1], [1, 0, 1], [1, 1, 0]], optimal_route)
        self.assertLessEqual(cost, optimal_cost + 1e-9)
        self.assertEqual(set(route[1:-1]), {1, 2})

    def test_optimality_gap_formula(self):
        results = optimality_gaps(compare(ASYMMETRIC))
        exact = [row for row in results if row['exact']]
        self.assertTrue(exact)
        optimal = min(row['distance_m'] for row in exact)
        for row in results:
            expected = round(100 * (row['distance_m'] / optimal - 1), 2)
            self.assertEqual(row['Optimality gap (%)'], expected)

    def test_optimality_gap_unavailable_without_exact(self):
        results = optimality_gaps(compare(ASYMMETRIC, selected=['Nearest Neighbor (greedy)']))
        self.assertIsNone(results[0]['Optimality gap (%)'])

    def test_route_geometry_matches_matrix_distance(self):
        graph = tiny_road_graph()
        stops = [0, 1, 2, 3]
        matrix = distance_matrix(graph, stops)
        route, cost, _ = held_karp(matrix)
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
        # Exact solvers present => gap must be measured, not invented.
        gaps = {row['short_name']: row['optimality_gap_percent'] for row in ok}
        self.assertEqual(gaps['Brute Force'], 0.0)
        self.assertEqual(gaps['Held-Karp'], 0.0)
        with tempfile.TemporaryDirectory() as folder:
            path = save_scalability_csv(rows, Path(folder) / 'scale.csv')
            self.assertTrue(path.is_file())


if __name__ == '__main__':
    unittest.main()
