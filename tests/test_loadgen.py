from __future__ import annotations

import unittest

from tools.loadgen import percentile


class LoadGeneratorTests(unittest.TestCase):
    def test_nearest_rank_percentile(self) -> None:
        self.assertEqual(percentile([], 0.95), 0.0)
        self.assertEqual(percentile([4, 1, 3, 2], 0.50), 2)
        self.assertEqual(percentile([4, 1, 3, 2], 0.95), 4)


if __name__ == "__main__":
    unittest.main()
