"""Additional correctness / labeling tests for the final-project upgrade."""
import math
import unittest
import networkx as nx
from src.algorithms import (
    astar,
    brute_force_route_search,
    dijkstra,
    haversine_heuristic,
    reconstruct,
    zero_heuristic,
)
from src.optimization_ladder import LADDER_SPECS, TIER_ORDER, run_optimization_ladder
from src.road_data import distance_matrix, to_adjacency
from src.report import report_to_html


class TestUpgradeCorrectness(unittest.TestCase):
    def setUp(self):
        self.graph = nx.DiGraph()
        for node, lat, lon in [(0, 40.0, -74.0), (1, 40.01, -74.0), (2, 40.01, -74.01), (3, 40.0, -74.01)]:
            self.graph.add_node(node, y=lat, x=lon)
        for u, v, length in [
            (0, 1, 1000), (1, 2, 1000), (2, 3, 1000), (3, 0, 1000),
            (0, 2, 2500), (1, 3, 2500),
        ]:
            self.graph.add_edge(u, v, length=length)
        self.adj = to_adjacency(self.graph)

    def test_unreachable_target(self):
        g = {'A': [('B', 1)], 'B': [], 'C': []}
        dist, prev, _ = dijkstra(g, 'A', 'C')
        self.assertNotIn('C', dist)
        self.assertEqual(reconstruct(prev, 'A', 'C'), [])

    def test_astar_zero_matches_dijkstra_distance(self):
        d1, _, _ = dijkstra(self.adj, 0, 2)
        d2, _, _ = astar(self.adj, 0, 2, zero_heuristic)
        self.assertAlmostEqual(d1[2], d2[2], places=9)

    def test_astar_haversine_matches_dijkstra(self):
        d1, _, _ = dijkstra(self.adj, 0, 3)
        d2, _, _ = astar(self.adj, 0, 3, haversine_heuristic(self.graph, 3))
        self.assertAlmostEqual(d1[3], d2[3], places=9)

    def test_brute_force_visits_each_delivery_once(self):
        matrix = distance_matrix(self.graph, [0, 1, 2, 3])
        route, cost, ops, exact = brute_force_route_search(matrix)
        self.assertTrue(exact)
        self.assertEqual(route[0], 0)
        self.assertEqual(route[-1], 0)
        self.assertEqual(sorted(route[1:-1]), [1, 2, 3])
        self.assertEqual(ops, math.factorial(3))
        self.assertGreater(cost, 0)

    def test_sampled_brute_force_not_marked_exact(self):
        matrix = distance_matrix(self.graph, [0, 1, 2, 3])
        route, cost, ops, exact = brute_force_route_search(matrix, max_permutations=2, seed=0)
        self.assertFalse(exact)
        self.assertLessEqual(ops, 3)  # identity + limited samples
        self.assertEqual(route[0], 0)

    def test_ladder_specs_document_all_tiers(self):
        for family, tiers in LADDER_SPECS.items():
            for tier in TIER_ORDER:
                self.assertIn(tier, tiers)
                self.assertTrue(tiers[tier]['label'])

    def test_dijkstra_ladder_distances_agree(self):
        stops = [0, 1, 2, 3]
        matrix = distance_matrix(self.graph, stops)
        rows = run_optimization_ladder(
            self.graph, stops, matrix=matrix, families=["Dijkstra's Algorithm"], seed=1
        )
        distances = {row['tier']: row['distance_m'] for row in rows}
        self.assertAlmostEqual(distances['Bad'], distances['Semi'], places=6)
        self.assertAlmostEqual(distances['Semi'], distances['Best'], places=6)

    def test_html_report_escapes_angle_brackets(self):
        report = {
            'project': 'FastRoute',
            'generated_at_utc': 'now',
            'place': '<script>x</script>',
            'stop_source': 'test',
            'deliveries': 1,
            'seed': 1,
            'network_nodes': 1,
            'network_edges': 1,
            'metric': 'm',
            'results': [],
            'automatic_explanation': ['ok'],
            'limitations': ['none'],
        }
        html = report_to_html(report)
        self.assertNotIn('<script>x</script>', html)
        self.assertIn('&lt;script&gt;', html)


if __name__ == '__main__':
    unittest.main()
