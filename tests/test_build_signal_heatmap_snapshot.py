from __future__ import annotations

import unittest

import pandas as pd

from src.visualization.build_signal_heatmap_snapshot import (
    SIGNAL_HEATMAP_COLS,
    build_signal_heatmap_snapshot,
)


class TestBuildSignalHeatmapSnapshot(unittest.TestCase):
    def test_build_signal_heatmap_snapshot_columns_and_sorting(self) -> None:
        ranking = pd.DataFrame(
            [
                {
                    "ticker": "BBB",
                    "asset_type": "stock",
                    "decision": "HOLD",
                    "confidence": 60,
                    "regime": "MIXED",
                    "risk_level": "MEDIUM",
                    "horizon_days": 60,
                    "composite_score": 38.0,
                    "rank_overall": 2,
                    "extra_col": "ignored",
                },
                {
                    "ticker": "AAA",
                    "asset_type": "stock",
                    "decision": "BUY",
                    "confidence": 82,
                    "regime": "TRENDING",
                    "risk_level": "LOW",
                    "horizon_days": 90,
                    "composite_score": 52.0,
                    "rank_overall": 1,
                    "extra_col": "ignored",
                },
            ]
        )

        out = build_signal_heatmap_snapshot(ranking)

        self.assertListEqual(out.columns.tolist(), SIGNAL_HEATMAP_COLS)
        self.assertListEqual(out["ticker"].tolist(), ["AAA", "BBB"])
        self.assertListEqual(out["rank_overall"].tolist(), [1, 2])


if __name__ == "__main__":
    unittest.main()
