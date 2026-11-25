"""Coverage for large delivery counts and merged metro graphs."""
import unittest
import networkx as nx
from src.algorithms import compare, optimality_gaps
from src.map_viz import _marker_indices
from src.constants import MAX_DELIVERY_DESTINATIONS, MERGED_AREA_COMPONENTS
from src.road_data import (
    filter_stops_to_scc,
    is_merged_place,
    largest_scc_nodes,
    sample_stops,
    to_adjacency,
)
from src.route_prep import _needs_distance_matrix, prepare_osm_experiment
from src.scalability import (
    LARGE_PATHFINDER_COUNTS,
    available_scale_counts,
    max_delivery_capacity,
    unavailable_scale_counts,
)
from src.portfolio_export import PAPER_EVIDENCE_ZIP_NAME, build_portfolio_zip


def connected_grid(n=40):
    """Build a geographic grid large enough for 1000-stop sampling tests at smaller n."""
    graph = nx.DiGraph()
    side = int(n ** 0.5) + 1
    nodes = []
    index = 0
    for r in range(side):
        for c in range(side):
            node = index
            index += 1
            lat = 40.0 + r * 0.001
            lon = -74.0 - c * 0.001
            graph.add_node(node, y=lat, x=lon)
            nodes.append(node)
            if c > 0:
                left = node - 1
                graph.add_edge(node, left, length=120)
                graph.add_edge(left, node, length=120)
            if r > 0:
                up = node - side
                graph.add_edge(node, up, length=120)
                graph.add_edge(up, node, length=120)
    return graph


class TestLargeScaleSupport(unittest.TestCase):
    def test_max_delivery_constant(self):
        self.assertEqual(MAX_DELIVERY_DESTINATIONS, 1000)

    def test_merged_place_registered(self):
        place = 'NYC / NJ metro (merged caches)'
        self.assertTrue(is_merged_place(place))
        self.assertGreaterEqual(len(MERGED_AREA_COMPONENTS[place]), 2)

    def test_sample_stops_supports_hundreds(self):
        graph = connected_grid(1600)
        stops = sample_stops(graph, 401, seed=7)
        self.assertEqual(len(stops), 401)
        self.assertEqual(len(set(stops)), 401)

    def test_matrix_needed_only_for_brute_force(self):
        self.assertFalse(_needs_distance_matrix(['A* Search Algorithm', "Dijkstra's Algorithm"], 501))
        self.assertTrue(_needs_distance_matrix(None, 50))
        self.assertTrue(_needs_distance_matrix(['Brute-Force Route Search'], 8))
        self.assertTrue(_needs_distance_matrix(['Brute-Force Route Search'], 500))

    def test_prepare_osm_skips_matrix_and_runs_pathfinders(self):
        graph = connected_grid(400)
        experiment = prepare_osm_experiment(
            graph,
            30,
            seed=1,
            selected_algorithms=['A* Search Algorithm', "Dijkstra's Algorithm"],
        )
        self.assertIsNone(experiment['matrix'])
        self.assertEqual(len(experiment['results']), 2)
        # Street-following legs (not stop-to-stop chords): some legs traverse >2 vertices.
        for row in experiment['results']:
            self.assertTrue(
                any(len(leg) > 2 for leg in row.get('legs') or []),
                msg=f"{row['Algorithm']} map legs look like stop-to-stop chords",
            )

    def test_large_tour_map_stays_on_street_paths(self):
        graph = connected_grid(900)
        experiment = prepare_osm_experiment(
            graph,
            150,
            seed=3,
            selected_algorithms=['A* Search Algorithm', "Dijkstra's Algorithm"],
        )
        self.assertGreater(len(experiment['stops']), 120)
        for row in experiment['results']:
            # Former bug: every leg was exactly warehouse/stop → next stop (2 points).
            self.assertTrue(
                any(len(leg) > 2 for leg in row.get('legs') or []),
                msg=f"{row['Algorithm']} still drawing stop-to-stop shortcuts",
            )

    def test_filter_stops_to_scc(self):
        graph = connected_grid(25)
        scc = largest_scc_nodes(graph)
        orphan = max(scc) + 100
        graph.add_node(orphan, y=41.0, x=-74.0)
        stops = [scc[0], orphan, scc[1]]
        kept, _, dropped = filter_stops_to_scc(graph, stops, [(0, 0), (1, 1), (2, 2)])
        self.assertEqual(dropped, 1)
        self.assertEqual(kept, [scc[0], scc[1]])

    def test_marker_subsampling(self):
        indices = _marker_indices(1000, max_markers=250)
        self.assertEqual(indices[0], 0)
        self.assertLessEqual(len(indices), 250)

    def test_compare_without_matrix(self):
        graph = connected_grid(36)
        stops = sample_stops(graph, 8, seed=2)
        adjacency = to_adjacency(graph)
        results = optimality_gaps(
            compare(graph, stops, adjacency, None, selected=["Dijkstra's Algorithm"])
        )
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]['Optimality gap (%)'])

    def test_scale_counts_respect_graph_capacity(self):
        small = connected_grid(400)
        self.assertLess(max_delivery_capacity(small), 1000)
        self.assertEqual(available_scale_counts(small, LARGE_PATHFINDER_COUNTS), [])
        big = connected_grid(1600)
        capacity = max_delivery_capacity(big)
        self.assertGreaterEqual(capacity, 1000)
        available = available_scale_counts(big, LARGE_PATHFINDER_COUNTS)
        self.assertIn(1000, available)
        self.assertNotIn(100_000, available)
        blocked = unavailable_scale_counts(big, LARGE_PATHFINDER_COUNTS)
        self.assertTrue(any(row['deliveries'] == 100_000 for row in blocked))

    def test_paper_evidence_zip_includes_improvement_and_ladder(self):
        self.assertTrue(PAPER_EVIDENCE_ZIP_NAME.startswith('paper_evidence_FINAL'))
        graph = connected_grid(64)
        experiment = prepare_osm_experiment(
            graph,
            5,
            seed=2,
            selected_algorithms=['A* Search Algorithm', "Dijkstra's Algorithm", 'Brute-Force Route Search'],
        )
        zip_bytes, pack_dir, notes = build_portfolio_zip(
            experiment, scalability_rows=[], graph=graph, auto_run_extras=True
        )
        self.assertTrue(zip_bytes)
        self.assertIn('paper_evidence_FINAL_', pack_dir.name)
        self.assertTrue((pack_dir / 'csv' / 'improvement_story.csv').is_file())
        self.assertTrue((pack_dir / 'csv' / 'optimization_ladder.csv').is_file())
        ladder_text = (pack_dir / 'csv' / 'optimization_ladder.csv').read_text(encoding='utf-8').lower()
        self.assertNotIn('nearest-neighbor', ladder_text)
        self.assertTrue(any('improvement' in note.lower() for note in notes))
        self.assertTrue(any('ladder' in note.lower() for note in notes))


if __name__ == '__main__':
    unittest.main()
