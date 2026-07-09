from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.recommender import recommend_funds


class RecommenderTests(unittest.TestCase):
    def test_recommender_loads_processed_data(self) -> None:
        result = recommend_funds("Moderate")
        self.assertGreater(len(result), 0)
        self.assertTrue({"scheme_name", "risk_grade", "sharpe_ratio", "return_3yr_pct", "aum_crore"}.issubset(set(result.columns)))


if __name__ == "__main__":
    unittest.main()
