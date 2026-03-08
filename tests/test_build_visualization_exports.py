from __future__ import annotations

import unittest

import pandas as pd

from src.visualization.build_visualization_exports import (
    LATEST_RANKING_COLS,
    PRICE_HISTORY_COLS,
    build_latest_ranking_export,
    build_price_history_export,
)


class TestBuildVisualizationExports(unittest.TestCase):
    def test_price_history_export_columns(self) -> None:
        historical = pd.DataFrame(
            [
                {
                    "date": "2026-03-05",
                    "ticker": "AAPL",
                    "source_ticker": "AAPL.US",
                    "asset_type": "stock",
                    "close": 260.25,
                    "ma_20": 267.47,
                    "ma_50": 264.55,
                    "ma_200": 243.73,
                    "source": "sp500_core",
                    "extra_col": 123,
                }
            ]
        )
        out = build_price_history_export(historical)
        self.assertListEqual(out.columns.tolist(), PRICE_HISTORY_COLS)

    def test_latest_ranking_includes_decision_order(self) -> None:
        ranking = pd.DataFrame(
            [
                {
                    "ticker": "AAPL",
                    "source_ticker": "AAPL.US",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "rank_overall": 1,
                    "rank_within_asset_type": 1,
                    "trend_score": 25.0,
                    "momentum_score": 30.0,
                    "risk_penalty": -4.0,
                    "composite_score": 51.0,
                    "decision": "HOLD",
                    "decision_reason": "Above-average factor profile with balanced trend and risk",
                    "source": "sp500_core",
                }
            ]
        )
        out = build_latest_ranking_export(ranking)
        self.assertIn("decision_order", out.columns)
        self.assertListEqual(out.columns.tolist(), LATEST_RANKING_COLS)

    def test_decision_order_mapping(self) -> None:
        ranking = pd.DataFrame(
            [
                {
                    "ticker": "TBUY",
                    "source_ticker": "TBUY.US",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "rank_overall": 1,
                    "rank_within_asset_type": 1,
                    "trend_score": 30.0,
                    "momentum_score": 30.0,
                    "risk_penalty": -2.0,
                    "composite_score": 58.0,
                    "decision": "BUY",
                    "decision_reason": "Strong cross-sectional trend and momentum with manageable volatility",
                    "source": "sp500_core",
                },
                {
                    "ticker": "THOLD",
                    "source_ticker": "THOLD.US",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "rank_overall": 2,
                    "rank_within_asset_type": 2,
                    "trend_score": 20.0,
                    "momentum_score": 20.0,
                    "risk_penalty": -3.0,
                    "composite_score": 37.0,
                    "decision": "HOLD",
                    "decision_reason": "Above-average factor profile with balanced trend and risk",
                    "source": "sp500_core",
                },
                {
                    "ticker": "TWATCH",
                    "source_ticker": "TWATCH.US",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "rank_overall": 3,
                    "rank_within_asset_type": 3,
                    "trend_score": 15.0,
                    "momentum_score": 15.0,
                    "risk_penalty": -4.0,
                    "composite_score": 26.0,
                    "decision": "WATCH",
                    "decision_reason": "Mixed factor profile; monitor for stronger confirmation",
                    "source": "sp500_core",
                },
                {
                    "ticker": "TAVOID",
                    "source_ticker": "TAVOID.US",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "rank_overall": 4,
                    "rank_within_asset_type": 4,
                    "trend_score": 5.0,
                    "momentum_score": 10.0,
                    "risk_penalty": -5.0,
                    "composite_score": 10.0,
                    "decision": "AVOID",
                    "decision_reason": "Weak relative ranking or elevated risk versus peers",
                    "source": "sp500_core",
                },
            ]
        )
        out = build_latest_ranking_export(ranking)
        mapping = dict(zip(out["decision"], out["decision_order"]))
        self.assertEqual(mapping["BUY"], 4)
        self.assertEqual(mapping["HOLD"], 3)
        self.assertEqual(mapping["WATCH"], 2)
        self.assertEqual(mapping["AVOID"], 1)

    def test_small_happy_path_without_errors(self) -> None:
        historical = pd.DataFrame(
            [
                {
                    "date": "2026-03-04",
                    "ticker": "AAPL",
                    "source_ticker": "AAPL.US",
                    "asset_type": "stock",
                    "close": 258.0,
                    "source": "sp500_core",
                },
                {
                    "date": "2026-03-05",
                    "ticker": "AAPL",
                    "source_ticker": "AAPL.US",
                    "asset_type": "stock",
                    "close": 260.25,
                    "source": "sp500_core",
                },
            ]
        )
        ranking = pd.DataFrame(
            [
                {
                    "ticker": "AAPL",
                    "source_ticker": "AAPL.US",
                    "asset_type": "stock",
                    "date": "2026-03-05",
                    "rank_overall": 1,
                    "rank_within_asset_type": 1,
                    "trend_score": 20.0,
                    "momentum_score": 20.0,
                    "risk_penalty": -3.0,
                    "composite_score": 37.0,
                    "decision": "HOLD",
                    "decision_reason": "Above-average factor profile with balanced trend and risk",
                    "source": "sp500_core",
                }
            ]
        )

        out_history = build_price_history_export(historical)
        out_ranking = build_latest_ranking_export(ranking)

        self.assertEqual(len(out_history), 2)
        self.assertEqual(len(out_ranking), 1)
        self.assertListEqual(out_history["ticker"].tolist(), ["AAPL", "AAPL"])
        self.assertEqual(int(out_ranking["decision_order"].iloc[0]), 3)


if __name__ == "__main__":
    unittest.main()

