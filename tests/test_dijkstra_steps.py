import unittest
import networkx as nx
from src.algorithms import dijkstra, reconstruct, optimality_gaps, compare
from src.dijkstra_viz import build_dijkstra_trace
from src.report import build_experiment_report, report_to_csv_rows, report_to_html, report_to_json
from src.results_explain import route_quality, understanding_results_text
from src.road_data import to_adjacency
from src.scalability import run_scalability
from src.guided_demo import DEMO_STEPS, clamp_step


def tiny_graph():
    graph = nx.DiGraph()
    for node, lat, lon in [(0, 40.0, -74.0), (1, 40.01, -74.0), (2, 40.01, -74.01), (3, 40.0, -74.01)]:
        graph.add_node(node, y=lat, x=lon)
    side, diagonal = 1200, 1700
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


class TestDijkstraStepsAndReports(unittest.TestCase):
    def test_dijkstra_unreachable(self):
        g = {'A': [('B', 1)], 'B': [], 'C': []}
        distances, previous, _ = dijkstra(g, 'A', 'C')
        self.assertNotIn('C', distances)
        self.assertEqual(reconstruct(previous, 'A', 'C'), [])

    def test_dijkstra_directed(self):
        g = {'A': [('B', 2)], 'B': [('C', 2)], 'C': []}
        distances, previous, _ = dijkstra(g, 'A', 'C')
        self.assertEqual(distances['C'], 4)
        self.assertEqual(reconstruct(previous, 'A', 'C'), ['A', 'B', 'C'])
        reverse = dijkstra(g, 'C', 'A')[0]
        self.assertNotIn('A', reverse)

    def test_record_steps_optional(self):
        g = {'A': [('B', 1), ('C', 5)], 'B': [('C', 1)], 'C': []}
        plain = dijkstra(g, 'A', 'C')
        self.assertEqual(len(plain), 3)
        distances, previous, explored, steps = dijkstra(g, 'A', 'C', record_steps=True)
        self.assertEqual(distances['C'], 2)
        self.assertTrue(any(step['event'] == 'settle' for step in steps))
        self.assertGreaterEqual(explored, 1)
        self.assertEqual(reconstruct(previous, 'A', 'C'), ['A', 'B', 'C'])

    def test_dijkstra_trace_on_road_graph(self):
        graph = tiny_graph()
        trace = build_dijkstra_trace(graph, 0, 2)
        self.assertLessEqual(trace['distance_m'], 1700)
        self.assertEqual(trace['path'][0], 0)
        self.assertEqual(trace['path'][-1], 2)
        self.assertTrue(trace['steps'])

    def test_optimality_gap_and_explanations(self):
        graph = tiny_graph()
        stops = [0, 1, 2, 3]
        adjacency = to_adjacency(graph)
        from src.road_data import distance_matrix
        matrix = distance_matrix(graph, stops)
        results = optimality_gaps(compare(graph, stops, adjacency, matrix))
        quality = route_quality(results)
        self.assertIsNotNone(quality['shortest'])
        experiment = {
            'results': results,
            'place': 'test',
            'source': 'unit',
            'delivery_count': 3,
            'seed': 1,
            'network_nodes': 4,
            'network_edges': 6,
        }
        text = understanding_results_text(experiment)
        self.assertTrue(any('Shortest route' in line for line in text))
        report = build_experiment_report(experiment)
        self.assertIn('FastRoute', report_to_json(report))
        self.assertTrue(report_to_csv_rows(report))
        self.assertIn('Algorithm Results', report_to_html(report))

    def test_scalability_skips_brute_force(self):
        from src.constants import BRUTE_FORCE_EXACT_MAX_STOPS, BRUTE_FORCE_MAX_STOPS, MAX_DELIVERY_DESTINATIONS
        from src.algorithms import brute_force_route_search
        self.assertEqual(BRUTE_FORCE_EXACT_MAX_STOPS, 9)
        self.assertEqual(BRUTE_FORCE_MAX_STOPS, MAX_DELIVERY_DESTINATIONS)
        # Large-n mode returns a non-exact sampled tour instead of skipping.
        matrix = [[0, 1, 2, 3], [1, 0, 4, 5], [2, 4, 0, 6], [3, 5, 6, 0]]
        _route, _cost, examined, exact = brute_force_route_search(matrix, max_permutations=5, seed=1)
        self.assertFalse(exact)
        self.assertLessEqual(examined, 5)

    def test_guided_demo_navigation(self):
        self.assertGreaterEqual(len(DEMO_STEPS), 8)
        self.assertEqual(clamp_step(-3), 0)
        self.assertEqual(clamp_step(999), len(DEMO_STEPS) - 1)


if __name__ == '__main__':
    unittest.main()
