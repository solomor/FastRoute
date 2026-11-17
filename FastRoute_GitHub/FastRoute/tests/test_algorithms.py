import math
import unittest
from src.algorithms import (dijkstra, reconstruct, brute_force, held_karp,
                            nearest_neighbor, two_opt, route_cost)

class TestAlgorithms(unittest.TestCase):
    def setUp(self):
        self.matrix = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]

    def test_dijkstra(self):
        g = {'A': [('B', 4), ('C', 1)], 'C': [('B', 2)], 'B': []}
        dist, prev, _ = dijkstra(g, 'A', 'B')
        self.assertEqual(dist['B'], 3)
        self.assertEqual(reconstruct(prev, 'A', 'B'), ['A', 'C', 'B'])

    def test_exact_agreement(self):
        b = brute_force(self.matrix)
        h = held_karp(self.matrix)
        self.assertEqual(b[1], 80)
        self.assertEqual(h[1], b[1])

    def test_heuristics_valid(self):
        for fn in (nearest_neighbor, lambda m: two_opt(m, nearest_neighbor(m)[0])):
            route, cost, _ = fn(self.matrix)
            self.assertEqual(route[0], 0)
            self.assertEqual(route[-1], 0)
            self.assertEqual(set(route[1:-1]), {1, 2, 3})
            self.assertEqual(cost, route_cost(self.matrix, route))
            self.assertGreaterEqual(cost, 80)

    def test_one_stop(self):
        self.assertEqual(held_karp([[0]])[1], 0)
        self.assertEqual(brute_force([[0]])[1], 0)

if __name__ == '__main__':
    unittest.main()
