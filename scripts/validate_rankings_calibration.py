from __future__ import annotations

"""
Validate ranking calibration by comparing legacy and calibrated outputs.
"""

import argparse
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ranking.build_rankings import build_rankings


DEFAULT_INPUT = Path("data/mart/investment/factor_snapshot_latest.parquet")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ranking calibration (before vs after).")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=DEFAULT_INPUT,
        help="Input factor_snapshot_latest parquet path.",
    )
    return parser.parse_args()


def _legacy_trend_score(df: pd.DataFrame) -> pd.Series:
    score = pd.Series(0.0, index=df.index)
    score += ((df["close"] > df["ma_20"]).fillna(False)).astype(float) * 10.0
    score += ((df["ma_20"] > df["ma_50"]).fillna(False)).astype(float) * 10.0
    score += ((df["ma_50"] > df["ma_200"]).fillna(False)).astype(float) * 10.0
    return score.clip(lower=0.0, upper=30.0)


def _legacy_percentile_score(series: pd.Series, low_fill_percentile: float) -> pd.Series:
    rank_pct = series.rank(method="average", pct=True, ascending=True)
    rank_pct = rank_pct.fillna(low_fill_percentile).clip(lower=0.0, upper=1.0)
    return rank_pct * 10.0


def _legacy_percentile_penalty(series: pd.Series, null_penalty_percentile: float) -> pd.Series:
    rank_pct = series.rank(method="average", pct=True, ascending=True)
    rank_pct = rank_pct.fillna(null_penalty_percentile).clip(lower=0.0, upper=1.0)
    return -(rank_pct * 10.0)


def build_legacy_rankings(snapshot_df: pd.DataFrame) -> pd.DataFrame:
    """
    Reproduce the pre-calibration scoring for side-by-side comparison.
    """
    df = snapshot_df.copy()
    df["trend_score"] = _legacy_trend_score(df)

    momentum_cols = ["ret_20d", "ret_60d", "ret_120d", "ret_252d"]
    for c in momentum_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[f"{c}_score"] = _legacy_percentile_score(df[c], low_fill_percentile=0.25)
    df["momentum_score"] = df[[f"{c}_score" for c in momentum_cols]].sum(axis=1).clip(lower=0.0, upper=40.0)

    risk_cols = ["volatility_20d", "volatility_60d"]
    for c in risk_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[f"{c}_penalty"] = _legacy_percentile_penalty(df[c], null_penalty_percentile=0.75)
    df["risk_penalty"] = df[[f"{c}_penalty" for c in risk_cols]].sum(axis=1).clip(lower=-20.0, upper=0.0)

    df["composite_score"] = (
        df["trend_score"] + df["momentum_score"] + df["risk_penalty"]
    ).clip(lower=0.0, upper=70.0)

    df["decision"] = "AVOID"
    df.loc[df["composite_score"] >= 25.0, "decision"] = "WATCH"
    df.loc[df["composite_score"] >= 40.0, "decision"] = "HOLD"
    df.loc[df["composite_score"] >= 55.0, "decision"] = "BUY"

    ranked = df.sort_values(
        ["composite_score", "ticker", "source_ticker"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    ranked["rank_overall"] = pd.RangeIndex(start=1, stop=len(ranked) + 1, step=1)
    return ranked


def print_summary(label: str, df: pd.DataFrame) -> None:
    print(f"\n===== {label} =====")
    print(f"row_count: {len(df):,}")
    print("score_summaries:")
    for col in ["trend_score", "momentum_score", "risk_penalty", "composite_score"]:
        s = pd.to_numeric(df[col], errors="coerce")
        print(
            f"  {col}: min={s.min():.6f} max={s.max():.6f} mean={s.mean():.6f}"
        )

    print("decision_distribution:")
    decision_counts = df["decision"].value_counts().reindex(["BUY", "HOLD", "WATCH", "AVOID"], fill_value=0)
    for d, c in decision_counts.items():
        print(f"  {d}: {int(c)}")

    print(f"trend_score_unique_count: {df['trend_score'].nunique(dropna=True)}")
    print(
        f"risk_penalty_min_max: ({pd.to_numeric(df['risk_penalty'], errors='coerce').min():.6f}, "
        f"{pd.to_numeric(df['risk_penalty'], errors='coerce').max():.6f})"
    )

    print("top_10_ranked_assets:")
    top10 = df.nsmallest(10, "rank_overall")[
        ["rank_overall", "ticker", "asset_type", "composite_score", "decision"]
    ]
    print(top10.to_string(index=False))


def main() -> None:
    args = parse_args()
    if not args.input_parquet.exists():
        raise FileNotFoundError(f"Input parquet not found: {args.input_parquet}")

    snapshot = pd.read_parquet(args.input_parquet)
    legacy = build_legacy_rankings(snapshot)
    calibrated = build_rankings(snapshot)

    print_summary("BEFORE (LEGACY)", legacy)
    print_summary("AFTER (CALIBRATED)", calibrated)


if __name__ == "__main__":
    main()
