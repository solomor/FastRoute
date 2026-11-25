import unittest
import networkx as nx
from src.algorithms import (
    dijkstra,
    dijkstra_bidirectional,
    dijkstra_naive,
    reconstruct,
)
from src.optimization_ladder import LADDER_SPECS, run_optimization_ladder, ladder_summary_table
from src.road_data import distance_matrix, to_adjacency


class TestOptimizationLadder(unittest.TestCase):
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

    def test_naive_matches_heap_distance(self):
        d1, _, _ = dijkstra(self.adjacency, 0, 2)
        d2, _, _ = dijkstra_naive(self.adjacency, 0, 2, early_stop=True)
        self.assertAlmostEqual(d1[2], d2[2], places=9)

    def test_bidirectional_matches_heap_distance(self):
        d1, prev1, _ = dijkstra(self.adjacency, 0, 2)
        d2, prev2, _ = dijkstra_bidirectional(self.adjacency, 0, 2)
        self.assertAlmostEqual(d1[2], d2[2], places=9)
        self.assertEqual(reconstruct(prev1, 0, 2)[0], 0)
        self.assertEqual(reconstruct(prev2, 0, 2)[-1], 2)

    def test_ladder_returns_nine_rows(self):
        matrix = distance_matrix(self.graph, self.stops)
        rows = run_optimization_ladder(self.graph, self.stops, matrix=matrix, seed=42)
        self.assertEqual(len(rows), 9)
        tiers = {(row['family'], row['tier']) for row in rows}
        self.assertEqual(len(tiers), 9)
        summary = ladder_summary_table(rows)
        self.assertEqual(len(summary), 9)

    def test_astar_tiers_same_order_same_distance(self):
        matrix = distance_matrix(self.graph, self.stops)
        rows = run_optimization_ladder(
            self.graph,
            self.stops,
            matrix=matrix,
            families=['A* Search Algorithm'],
            seed=42,
        )
        by_tier = {row['tier']: row for row in rows}
        self.assertEqual(by_tier['Bad']['Route'], by_tier['Semi']['Route'])
        self.assertEqual(by_tier['Semi']['Route'], by_tier['Best']['Route'])
        self.assertAlmostEqual(by_tier['Bad']['distance_m'], by_tier['Semi']['distance_m'], places=6)
        self.assertAlmostEqual(by_tier['Semi']['distance_m'], by_tier['Best']['distance_m'], places=6)
        self.assertEqual(LADDER_SPECS['A* Search Algorithm']['Best']['pathfinder'], 'astar_cached')
        self.assertNotIn('nearest_neighbor', str(LADDER_SPECS['A* Search Algorithm']))

    def test_dijkstra_tiers_same_distance(self):
        matrix = distance_matrix(self.graph, self.stops)
        rows = run_optimization_ladder(
            self.graph,
            self.stops,
            matrix=matrix,
            families=["Dijkstra's Algorithm"],
            seed=42,
        )
        dists = [row['distance_m'] for row in rows]
        self.assertAlmostEqual(min(dists), max(dists), places=6)
        best = next(row for row in rows if row['tier'] == 'Best')
        self.assertTrue(best.get('reverse_adjacency_reused'))

    def test_bf_nested_budgets_same_seed_nonincreasing_distance(self):
        # Larger nested budget must not worsen best-found distance for same seed.
        big = nx.DiGraph()
        for i in range(8):
            big.add_node(i, y=40.0 + i * 0.01, x=-74.0)
        for i in range(7):
            big.add_edge(i, i + 1, length=1000)
            big.add_edge(i + 1, i, length=1000)
        for i in range(8):
            for j in range(i + 2, 8):
                big.add_edge(i, j, length=1000 * (j - i) + 50)
                big.add_edge(j, i, length=1000 * (j - i) + 50)
        stops = list(range(8))
        matrix = distance_matrix(big, stops)
        rows = run_optimization_ladder(
            big, stops, matrix=matrix, families=['Brute-Force Route Search'], seed=7
        )
        by_tier = {row['tier']: row for row in rows}
        self.assertLessEqual(by_tier['Semi']['distance_m'], by_tier['Bad']['distance_m'] + 1e-6)
        self.assertLessEqual(by_tier['Best']['distance_m'], by_tier['Semi']['distance_m'] + 1e-6)


if __name__ == '__main__':
    unittest.main()
