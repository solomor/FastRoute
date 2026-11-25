import unittest
import networkx as nx
from src.algorithms import compare, optimality_gaps
from src.improvement import (
    build_improvement_story,
    middle_algorithm,
    nearest_neighbor_order,
    rank_algorithms,
)
from src.road_data import distance_matrix, to_adjacency


class TestImprovement(unittest.TestCase):
    def setUp(self):
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
        self.matrix = distance_matrix(self.graph, self.stops)

    def test_middle_algorithm_picks_center_rank(self):
        results = optimality_gaps(compare(self.graph, self.stops, self.adjacency, self.matrix))
        ranked = rank_algorithms(results)
        mid = middle_algorithm(results)
        self.assertEqual(mid['Algorithm'], ranked[len(ranked) // 2]['Algorithm'])

    def test_nearest_neighbor_helper_still_closes_tour_historically(self):
        order = nearest_neighbor_order(self.matrix)
        self.assertEqual(order[0], 0)
        self.assertEqual(order[-1], 0)
        self.assertEqual(len(order), len(self.stops) + 1)

    def test_build_improvement_story_uses_dijkstra_and_bf_order(self):
        results = optimality_gaps(compare(self.graph, self.stops, self.adjacency, self.matrix))
        experiment = {
            'results': results,
            'stops': self.stops,
            'matrix': self.matrix,
            'seed': 42,
            'map_simplified': False,
            'stop_coords': [(40.0, -74.0), (40.01, -74.0), (40.01, -74.01), (40.0, -74.01)],
        }
        story = build_improvement_story(experiment, self.graph)
        self.assertEqual(story['experiment_type'], 'dijkstra_order_vs_brute_force_order')
        self.assertIn('baseline', story)
        self.assertIn('improved', story)
        self.assertIn('timings', story)
        self.assertIn('search', story)
        self.assertTrue(story['narrative'])
        self.assertNotIn('nearest-neighbor', story['settings_label'].lower())
        self.assertLessEqual(story['improved']['distance_m'], story['baseline']['distance_m'] + 1e-6)
        self.assertIn('distance_matrix_prep_ms', story['timings'])
        self.assertIn('route_search_ms', story['timings'])


if __name__ == '__main__':
    unittest.main()
