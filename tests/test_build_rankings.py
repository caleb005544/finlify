from __future__ import annotations

import unittest

import pandas as pd

from src.ranking.build_rankings import _trend_score, build_rankings


def _make_snapshot(n: int = 12) -> pd.DataFrame:
    rows: list[dict] = []
    for i in range(1, n + 1):
        ticker = f"T{i:03d}"
        rows.append(
            {
                "source_ticker": f"{ticker}.US",
                "ticker": ticker,
                "asset_type": "stock" if i % 2 else "etf",
                "date": "2026-03-05",
                "close": 100.0 + i,
                "ret_20d": -0.10 + (i * 0.01),
                "ret_60d": -0.08 + (i * 0.012),
                "ret_120d": -0.05 + (i * 0.015),
                "ret_252d": -0.03 + (i * 0.02),
                "ma_20": 98.0 + i,
                "ma_50": 97.0 + i,
                "ma_200": 96.0 + i,
                "volatility_20d": 0.10 + (i * 0.01),
                "volatility_60d": 0.12 + (i * 0.009),
                "dist_from_52w_high": -0.20 + (i * 0.01),
                "dist_from_52w_low": 0.10 + (i * 0.01),
                "is_active": True,
                "source": "sp500_core",
            }
        )
    return pd.DataFrame(rows)


class TestBuildRankings(unittest.TestCase):
    def test_schema_happy_path(self) -> None:
        snapshot = _make_snapshot(12)
        ranked = build_rankings(snapshot)

        self.assertEqual(len(ranked), len(snapshot))
        for col in [
            "trend_score",
            "momentum_score",
            "risk_penalty",
            "composite_score",
            "decision",
            "decision_reason",
            "rank_overall",
            "rank_within_asset_type",
        ]:
            self.assertIn(col, ranked.columns)

    def test_trend_score_not_binary_only(self) -> None:
        df = pd.DataFrame(
            [
                {"close": 110.0, "ma_20": 100.0, "ma_50": 100.0, "ma_200": 100.0},
                {"close": 105.0, "ma_20": 100.0, "ma_50": 100.0, "ma_200": 100.0},
                {"close": 101.0, "ma_20": 100.0, "ma_50": 100.0, "ma_200": 100.0},
            ]
        )
        trend = _trend_score(df)
        self.assertGreater(trend.iloc[0], trend.iloc[1])
        self.assertGreater(trend.iloc[1], trend.iloc[2])
        self.assertGreater(trend.nunique(), 1)

    def test_softened_risk_penalty_range(self) -> None:
        snapshot = _make_snapshot(20)
        ranked = build_rankings(snapshot)
        self.assertGreaterEqual(float(ranked["risk_penalty"].min()), -10.0)
        self.assertLessEqual(float(ranked["risk_penalty"].max()), 0.0)

    def test_percentile_decision_buckets(self) -> None:
        rows: list[dict] = []
        for i in range(1, 11):
            ticker = f"P{i:03d}"
            rows.append(
                {
                    "source_ticker": f"{ticker}.US",
                    "ticker": ticker,
                    "asset_type": "stock" if i <= 5 else "etf",
                    "date": "2026-03-05",
                    "close": 100.0,
                    "ret_20d": i * 0.01,
                    "ret_60d": i * 0.011,
                    "ret_120d": i * 0.012,
                    "ret_252d": i * 0.013,
                    "ma_20": 100.0,
                    "ma_50": 100.0,
                    "ma_200": 100.0,
                    "volatility_20d": 0.20,
                    "volatility_60d": 0.20,
                    "dist_from_52w_high": -0.10,
                    "dist_from_52w_low": 0.10,
                    "is_active": True,
                    "source": "sp500_core",
                }
            )

        ranked = build_rankings(pd.DataFrame(rows))
        decisions = set(ranked["decision"].tolist())
        self.assertTrue({"BUY", "HOLD", "WATCH", "AVOID"}.issubset(decisions))

        top_rows = ranked.nsmallest(2, "rank_overall")
        self.assertTrue((top_rows["decision"] == "BUY").all())
        self.assertLess(float(top_rows["composite_score"].max()), 55.0)

    def test_deterministic_ordering(self) -> None:
        snapshot = pd.DataFrame(
            [
                {
                    "source_ticker": "CCC.US",
                    "ticker": "CCC",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "close": 100.0,
                    "ret_20d": 0.01,
                    "ret_60d": 0.01,
                    "ret_120d": 0.01,
                    "ret_252d": 0.01,
                    "ma_20": 100.0,
                    "ma_50": 100.0,
                    "ma_200": 100.0,
                    "volatility_20d": 0.2,
                    "volatility_60d": 0.2,
                    "dist_from_52w_high": -0.1,
                    "dist_from_52w_low": 0.1,
                    "is_active": True,
                    "source": "sp500_core",
                },
                {
                    "source_ticker": "AAA.US",
                    "ticker": "AAA",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "close": 100.0,
                    "ret_20d": 0.01,
                    "ret_60d": 0.01,
                    "ret_120d": 0.01,
                    "ret_252d": 0.01,
                    "ma_20": 100.0,
                    "ma_50": 100.0,
                    "ma_200": 100.0,
                    "volatility_20d": 0.2,
                    "volatility_60d": 0.2,
                    "dist_from_52w_high": -0.1,
                    "dist_from_52w_low": 0.1,
                    "is_active": True,
                    "source": "sp500_core",
                },
                {
                    "source_ticker": "BBB.US",
                    "ticker": "BBB",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "close": 100.0,
                    "ret_20d": 0.01,
                    "ret_60d": 0.01,
                    "ret_120d": 0.01,
                    "ret_252d": 0.01,
                    "ma_20": 100.0,
                    "ma_50": 100.0,
                    "ma_200": 100.0,
                    "volatility_20d": 0.2,
                    "volatility_60d": 0.2,
                    "dist_from_52w_high": -0.1,
                    "dist_from_52w_low": 0.1,
                    "is_active": True,
                    "source": "sp500_core",
                },
            ]
        )

        ranked1 = build_rankings(snapshot)
        ranked2 = build_rankings(snapshot)

        self.assertListEqual(ranked1["rank_overall"].tolist(), ranked2["rank_overall"].tolist())
        self.assertListEqual(ranked1["ticker"].tolist(), ["AAA", "BBB", "CCC"])


if __name__ == "__main__":
    unittest.main()

