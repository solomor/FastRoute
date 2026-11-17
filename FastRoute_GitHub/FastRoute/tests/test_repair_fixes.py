"""Tests for Priority-1 correctness repairs (snapping, visibility, HTML, gaps, duplicates)."""
import math
import tempfile
import unittest
from pathlib import Path
import networkx as nx
from src.algorithms import compare, optimality_gaps, WORK_COUNTER_UNITS
from src.datasets import coordinate_pair_label, dataset_validation_summary, file_digest, list_datasets
from src.map_viz import build_live_animation_html
from src.report import build_experiment_report, report_to_html
from src.results_explain import understanding_results_text
from src.road_data import (
    DEFAULT_MAX_SNAP_M,
    distance_matrix,
    geographic_distance_m,
    nearest_node,
    snap_coordinates,
    to_adjacency,
)
from src.dijkstra_viz import is_reachable, sample_intersection_choices, sample_reachable_pair
from src.route_prep import prepare_dataset_experiment
import pandas as pd


def tiny_graph():
    graph = nx.DiGraph()
    for node, lat, lon in [
        (10, 40.0, -74.0),
        (20, 40.001, -74.0),
        (30, 40.002, -74.0),
        (40, 41.0, -74.0),  # far node
    ]:
        graph.add_node(node, y=lat, x=lon)
    for u, v in [(10, 20), (20, 10), (20, 30), (30, 20), (30, 10), (10, 30)]:
        graph.add_edge(u, v, length=100)
    return graph


class TestRepairFixes(unittest.TestCase):
    def test_haversine_not_degrees(self):
        # ~111 km per degree latitude near equator approximation
        meters = geographic_distance_m(0.0, 0.0, 1.0, 0.0)
        self.assertGreater(meters, 100_000)
        self.assertLess(meters, 120_000)

    def test_shared_nodes_allowed_and_no_silent_far_move(self):
        graph = tiny_graph()
        # Two points near node 10 should both snap to 10, not be forced onto a distant unique node.
        result = snap_coordinates(graph, [(40.0, -74.0), (40.0001, -74.0)], max_snap_m=500)
        self.assertEqual(result['nodes'], [10, 10])
        self.assertEqual(result['stats']['accepted'], 2)
        self.assertEqual(result['stats']['unique_nodes'], 1)
        self.assertGreater(result['stats']['shared_node_locations'], 0)
        for record in result['records']:
            self.assertEqual(record['original_lat'], record['original_lat'])
            self.assertIn('snapped_lat', record)
            self.assertTrue(record['accepted'])
            self.assertLess(record['snap_distance_m'], 50)

    def test_max_snap_distance_rejects_far_points(self):
        graph = tiny_graph()
        # Point near far node 40 with a tiny limit should reject if nearest is still too far from cluster...
        # Use a point near 40 with max_snap 1 meter relative to denser nodes? nearest is 40 itself.
        near_far = snap_coordinates(graph, [(41.0, -74.0)], max_snap_m=1)
        self.assertEqual(near_far['nodes'], [40])
        # Point between dense area and far node: force reject by using impossible tiny limit away from all nodes.
        rejected = snap_coordinates(graph, [(40.5, -74.0)], max_snap_m=10)
        self.assertEqual(rejected['stats']['rejected'], 1)
        self.assertEqual(rejected['nodes'], [])
        self.assertFalse(rejected['records'][0]['accepted'])

    def test_shared_node_matrix_zero_leg(self):
        graph = tiny_graph()
        stops = [10, 10, 20]
        matrix = distance_matrix(graph, stops)
        self.assertEqual(matrix[0][1], 0.0)
        self.assertEqual(matrix[1][0], 0.0)
        self.assertGreater(matrix[0][2], 0.0)
        results = compare(matrix)
        for row in results:
            self.assertEqual(row['Route'][0], 0)
            self.assertEqual(row['Route'][-1], 0)
            self.assertEqual(set(row['Route'][1:-1]), {1, 2})

    def test_empty_route_visibility_does_not_force_all(self):
        stop_coords = [(40.0, -74.0), (40.01, -74.0), (40.01, -74.01)]
        routes = [{
            'Algorithm': 'Nearest Neighbor (greedy)',
            'Color': '#F59E0B',
            'Distance (km)': 1.0,
            'coordinates': stop_coords + [stop_coords[0]],
        }]
        html = build_live_animation_html(stop_coords, routes, show_algorithms=[], autoplay=False)
        self.assertIn('No algorithm routes are visible', html)
        self.assertIn('"routes":[]', html.replace(' ', ''))

    def test_map_bounds_include_route_geometry(self):
        stop_coords = [(40.0, -74.0), (40.01, -74.0)]
        long_route = [(40.0, -74.0), (40.05, -74.02), (40.01, -74.0), (40.0, -74.0)]
        routes = [{
            'Algorithm': 'Nearest Neighbor (greedy)',
            'Color': '#F59E0B',
            'Distance (km)': 2.0,
            'coordinates': long_route,
        }]
        html = build_live_animation_html(stop_coords, routes, show_algorithms=['Nearest Neighbor (greedy)'])
        self.assertIn('40.05', html)

    def test_html_report_escapes_markup(self):
        experiment = {
            'place': '<script>alert(1)</script>',
            'source': 'Food & "special" <b>source</b>',
            'delivery_count': 3,
            'seed': 1,
            'network_nodes': 10,
            'network_edges': 20,
            'results': [{
                'Algorithm': 'Nearest Neighbor (greedy)',
                'Distance (km)': 1.2,
                'distance_m': 1200,
                'Runtime (ms)': 1.0,
                'Peak memory (KB)': 2.0,
                'Operations / states': 5,
                'Algorithm-Specific Work Counter': 5,
                'Work unit': WORK_COUNTER_UNITS['Nearest Neighbor (greedy)'],
                'Optimality gap (%)': None,
                'exact': False,
                'Route': [0, 1, 2, 0],
            }],
        }
        report = build_experiment_report(experiment)
        html = report_to_html(report)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertIn('&amp;', html)

    def test_zero_optimal_gap_safe(self):
        results = [{
            'Algorithm': 'Brute Force (exact)',
            'distance_m': 0.0,
            'exact': True,
        }, {
            'Algorithm': 'Nearest Neighbor (greedy)',
            'distance_m': 5.0,
            'exact': False,
        }]
        gaps = optimality_gaps(results)
        self.assertEqual(gaps[0]['Optimality gap (%)'], 0.0)
        self.assertIsNone(gaps[1]['Optimality gap (%)'])

    def test_work_units_present_and_not_ranked_in_text(self):
        matrix = [[0, 1, 2], [1, 0, 3], [2, 3, 0]]
        results = optimality_gaps(compare(matrix))
        for row in results:
            self.assertIn(row['Work unit'], WORK_COUNTER_UNITS.values())
        text = '\n'.join(understanding_results_text({'results': results}))
        self.assertIn('not comparable across algorithms', text.lower())
        self.assertNotIn('Most computation:', text)

    def test_dijkstra_choices_from_scc_and_reachable_pair(self):
        graph = tiny_graph()
        choices = sample_intersection_choices(graph, count=10, seed=1)
        ids = {item['id'] for item in choices}
        self.assertTrue(ids.issubset({10, 20, 30}))  # strongly connected core, not only far node
        pair = sample_reachable_pair(graph, seed=3)
        self.assertIsNotNone(pair)
        self.assertTrue(is_reachable(graph, pair[0], pair[1]))

    def test_coordinate_pair_labels(self):
        self.assertEqual(
            coordinate_pair_label('Delivery_location_latitude', 'Delivery_location_longitude'),
            'Customer / delivery location',
        )
        self.assertEqual(
            coordinate_pair_label('Restaurant_latitude', 'Restaurant_longitude'),
            'Restaurant location',
        )

    def test_dataset_validation_summary(self):
        frame = pd.DataFrame({
            'lat': [40.7, None, 91, 40.7, 0],
            'lon': [-74.0, -74.0, 20, -74.0, 0],
        })
        summary = dataset_validation_summary(frame, 'lat', 'lon')
        self.assertEqual(summary['original_rows'], 5)
        self.assertEqual(summary['usable_coordinate_rows'], 2)  # two valid 40.7,-74.0 rows; invalid/missing excluded
        self.assertEqual(summary['duplicate_coordinates_among_usable'], 1)
        self.assertGreaterEqual(summary['missing_or_non_numeric'], 1)

    def test_duplicate_dataset_listing_skipped(self):
        names = [item['name'] for item in list_datasets()]
        # Built-in Grubhub should appear once; identical data/user copy must not add a second choice.
        self.assertEqual(names.count('Grubhub restaurant listings'), 1)
        self.assertNotIn('grubhub', [n.lower() for n in names if n != 'Grubhub restaurant listings'])

    def test_nearest_node_returns_meters(self):
        graph = tiny_graph()
        node, meters = nearest_node(graph, 40.0, -74.0)
        self.assertEqual(node, 10)
        self.assertLess(meters, 1.0)


if __name__ == '__main__':
    unittest.main()
