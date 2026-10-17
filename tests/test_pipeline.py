import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from equity_pipeline import attach_identifiers, backtest, corporate_actions, quality_issues, security_master


class PipelineTests(unittest.TestCase):
    def test_isins_have_valid_check_digits(self):
        def valid(isin):
            expanded = "".join(str(int(char, 36)) for char in isin)
            total = 0
            for index, digit in enumerate(reversed(expanded)):
                value = int(digit) * (2 if index % 2 else 1)
                total += value // 10 + value % 10
            return total % 10 == 0
        self.assertTrue(security_master()["isin"].map(valid).all())

    def test_identifier_change_is_point_in_time(self):
        p = pd.DataFrame({"ticker": ["ULVR.L", "ULVR.L"],
                          "trade_date": pd.to_datetime(["2025-12-08", "2025-12-09"])})
        result = attach_identifiers(p, security_master())
        self.assertEqual(result["isin"].tolist(), ["GB00B10RZP78", "GB00BVZK7T90"])
        aal = pd.DataFrame({"ticker": ["AAL.L", "AAL.L"],
                            "trade_date": pd.to_datetime(["2025-05-30", "2025-06-02"])})
        self.assertEqual(attach_identifiers(aal, security_master())["isin"].tolist(),
                         ["GB00B1XZS820", "GB00BTK05J60"])

    def test_dividend_and_split_price_bases(self):
        p = pd.DataFrame({"ticker": ["X", "X", "X"],
                          "trade_date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
                          "close": [50.0, 50.0, 51.0], "adj_close": [49.0, 49.0, 51.0],
                          "dividend": [0.0, 0.0, 1.0], "split_ratio": [0.0, 2.0, 0.0], "isin": ["A"] * 3})
        result, actions = corporate_actions(p)
        self.assertEqual(result.pre_split_nominal_close.tolist(), [100.0, 50.0, 51.0])
        self.assertEqual(set(actions.action_type), {"split", "dividend"})

    def test_quality_catches_duplicates_bad_prices_and_peer_gap(self):
        dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-01", "2024-01-03"])
        p = pd.DataFrame({"ticker": ["A", "A", "A", "B", "B"], "trade_date": dates,
                          "open": [100, 0, 0, 100, 100], "high": [100, 100, 100, 100, 100],
                          "low": [100, 100, 100, 100, 100], "close": [100, 130, 130, 100, 100],
                          "adj_close": [100, 130, 130, 100, 100]})
        kinds = set(quality_issues(p, ["A", "B"]).issue_type)
        self.assertTrue({"duplicate_row", "invalid_price", "missing_peer_day", "adjusted_jump_gt_20pct"} <= kinds)

    def test_backtest_uses_prior_month_signal(self):
        months = pd.date_range("2023-01-31", periods=15, freq="ME")
        rows = [{"ticker": t, "trade_date": day, "adj_close": base * (1.04 if t == "A" else 1.01) ** i}
                for i, day in enumerate(months) for t, base in [("A", 100), ("B", 100)]]
        perf, holdings, metrics = backtest(pd.DataFrame(rows), top_n=1)
        self.assertEqual(len(perf), 2)
        self.assertEqual(set(holdings.ticker), {"A"})
        self.assertGreater(metrics.loc[metrics.strategy.eq("momentum"), "total_return"].iloc[0],
                           metrics.loc[metrics.strategy.eq("benchmark"), "total_return"].iloc[0])


if __name__ == "__main__":
    unittest.main()
