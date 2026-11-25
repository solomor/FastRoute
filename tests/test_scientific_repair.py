"""Regression tests for the scientific-accuracy repair (NN removal, streaming BF, gaps)."""
import unittest
import networkx as nx
from src.algorithms import (
    brute_force_route_search,
    compare,
    haversine_heuristic_cached,
    optimality_gaps,
    problem_identity,
    tour_with_pathfinder,
)
from src.road_data import distance_matrix, to_adjacency


def tiny_graph():
    graph = nx.DiGraph()
    for node, lat, lon in [(0, 40.0, -74.0), (1, 40.01, -74.0), (2, 40.01, -74.01), (3, 40.0, -74.01)]:
        graph.add_node(node, y=lat, x=lon)
    for u, v, length in [
        (0, 1, 1200), (1, 0, 1200),
        (1, 2, 1200), (2, 1, 1200),
        (2, 3, 1200), (3, 2, 1200),
        (3, 0, 1200), (0, 3, 1200),
        (0, 2, 1700), (2, 0, 1700),
        (1, 3, 1700), (3, 1, 1700),
    ]:
        graph.add_edge(u, v, length=length)
    return graph


class TestScientificRepair(unittest.TestCase):
    def setUp(self):
        self.graph = tiny_graph()
        self.stops = [0, 1, 2, 3]
        self.adjacency = to_adjacency(self.graph)
        self.matrix = distance_matrix(self.graph, self.stops)

    def test_streaming_sampled_bf_deterministic(self):
        # Force sampled mode: budget < 3! = 6
        meta = {}
        a = brute_force_route_search(self.matrix, max_permutations=4, seed=99, meta_out=meta)
        b = brute_force_route_search(self.matrix, max_permutations=4, seed=99)
        self.assertEqual(a[0], b[0])
        self.assertAlmostEqual(a[1], b[1], places=9)
        self.assertEqual(a[2], b[2])
        self.assertFalse(a[3])
        self.assertEqual(meta['search_mode'], 'sampled_with_replacement')
        self.assertFalse(meta['unique_permutations_tracked'])
        self.assertEqual(a[2], 4)

    def test_exact_bf_still_enumerates(self):
        meta = {}
        route, cost, examined, exact = brute_force_route_search(self.matrix, meta_out=meta)
        self.assertTrue(exact)
        self.assertEqual(examined, 6)  # 3! for 3 deliveries
        self.assertEqual(meta['search_mode'], 'exact')

    def test_cached_astar_matches_standard_distance(self):
        order = [0, 1, 2, 3, 0]
        _, d1, _, _ = tour_with_pathfinder(self.adjacency, self.graph, self.stops, order, 'astar')
        _, d2, _, _ = tour_with_pathfinder(self.adjacency, self.graph, self.stops, order, 'astar_cached')
        self.assertAlmostEqual(d1, d2, places=6)

    def test_optimality_gap_none_when_not_exact(self):
        results = compare(
            self.graph,
            self.stops,
            self.adjacency,
            self.matrix,
            selected=['A* Search Algorithm', "Dijkstra's Algorithm"],
        )
        # Force a fake sampled BF without exact flag
        results.append({
            'Algorithm': 'Brute-Force Route Search',
            'distance_m': 5000,
            'exact': False,
            'status': 'ok',
        })
        optimality_gaps(results)
        for row in results:
            self.assertIsNone(row['Optimality gap (%)'])
            self.assertIn(row['optimality_status'], {
                'exact_reference_unavailable',
                'sampled_search_only',
            })

    def test_optimality_gap_with_exact_reference(self):
        results = optimality_gaps(compare(self.graph, self.stops, self.adjacency, self.matrix))
        gaps = {row['Algorithm']: row['Optimality gap (%)'] for row in results}
        self.assertEqual(gaps['Brute-Force Route Search'], 0.0)
        self.assertIsNotNone(gaps["Dijkstra's Algorithm"])
        self.assertGreaterEqual(gaps["Dijkstra's Algorithm"], -1e-9)

    def test_problem_identity_fields(self):
        pid = problem_identity(self.stops, place='Test')
        self.assertEqual(pid['depot'], 0)
        self.assertEqual(pid['ordered_delivery_nodes'], [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
