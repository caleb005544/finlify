from __future__ import annotations

"""
Build Finlify ranked asset table from latest factor snapshot.
"""

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_INPUT_PARQUET = Path("data/mart/investment/factor_snapshot_latest.parquet")
DEFAULT_OUTPUT_PARQUET = Path("data/mart/investment/top_ranked_assets.parquet")
DEFAULT_OUTPUT_CSV = Path("data/mart/investment/top_ranked_assets.csv")
ALLOWED_DECISIONS = {"BUY", "HOLD", "WATCH", "AVOID"}
ALLOWED_REGIMES = {"TRENDING", "MIXED", "RISK_OFF"}
ALLOWED_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}
ALLOWED_HORIZON_DAYS = {30, 60, 90}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ranked assets from latest factor snapshot.")
    parser.add_argument(
        "--input-parquet",
        type=Path,
        default=DEFAULT_INPUT_PARQUET,
        help="Input factor snapshot latest parquet path.",
    )
    parser.add_argument(
        "--output-parquet",
        type=Path,
        default=DEFAULT_OUTPUT_PARQUET,
        help="Output ranked assets parquet path.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_OUTPUT_CSV,
        help="CSV output path.",
    )
    return parser.parse_args()


def _validate_input_schema(df: pd.DataFrame) -> None:
    required = {
        "source_ticker",
        "ticker",
        "asset_type",
        "date",
        "close",
        "ret_20d",
        "ret_60d",
        "ret_120d",
        "ret_252d",
        "ma_20",
        "ma_50",
        "ma_200",
        "volatility_20d",
        "volatility_60d",
        "dist_from_52w_high",
        "dist_from_52w_low",
        "is_active",
        "source",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input is missing required columns: {missing}")


def _trend_score(df: pd.DataFrame) -> pd.Series:
    close = pd.to_numeric(df["close"], errors="coerce")
    ma_20 = pd.to_numeric(df["ma_20"], errors="coerce")
    ma_50 = pd.to_numeric(df["ma_50"], errors="coerce")
    ma_200 = pd.to_numeric(df["ma_200"], errors="coerce")

    # This preserves ranking power based on distance from moving averages, not only binary above/below states.
    close_vs_ma20 = ((close / ma_20) - 1.0).replace([float("inf"), float("-inf")], pd.NA)
    close_vs_ma50 = ((close / ma_50) - 1.0).replace([float("inf"), float("-inf")], pd.NA)
    close_vs_ma200 = ((close / ma_200) - 1.0).replace([float("inf"), float("-inf")], pd.NA)

    s20 = _percentile_score(close_vs_ma20, low_fill_percentile=0.25)
    s50 = _percentile_score(close_vs_ma50, low_fill_percentile=0.25)
    s200 = _percentile_score(close_vs_ma200, low_fill_percentile=0.25)
    return (s20 + s50 + s200).clip(lower=0.0, upper=30.0)


def _percentile_score(series: pd.Series, low_fill_percentile: float) -> pd.Series:
    """
    Convert cross-sectional percentile rank to 0-10 score.
    Nulls are filled with a conservative low/neutral percentile.
    """
    rank_pct = series.rank(method="average", pct=True, ascending=True)
    rank_pct = rank_pct.fillna(low_fill_percentile).clip(lower=0.0, upper=1.0)
    return rank_pct * 10.0


def _percentile_penalty(series: pd.Series, null_penalty_percentile: float) -> pd.Series:
    """
    Convert cross-sectional percentile rank to 0 to -10 penalty.
    Higher values map to more negative penalty. Nulls use conservative penalty.
    """
    rank_pct = series.rank(method="average", pct=True, ascending=True)
    rank_pct = rank_pct.fillna(null_penalty_percentile).clip(lower=0.0, upper=1.0)
    # Softer penalty keeps risk important without overpowering trend and momentum.
    return -(rank_pct * 5.0)


def _decision_reason(df: pd.DataFrame) -> pd.Series:
    reason_map = {
        "BUY": "Strong cross-sectional trend and momentum with manageable volatility",
        "HOLD": "Above-average factor profile with balanced trend and risk",
        "WATCH": "Mixed factor profile; monitor for stronger confirmation",
        "AVOID": "Weak relative ranking or elevated risk versus peers",
    }
    return df["decision"].map(reason_map).fillna(reason_map["AVOID"]).astype("string")


def _derive_regime(df: pd.DataFrame) -> pd.Series:
    trend = pd.to_numeric(df["trend_score"], errors="coerce")
    momentum = pd.to_numeric(df["momentum_score"], errors="coerce")
    risk_abs = pd.to_numeric(df["risk_penalty"], errors="coerce").abs()
    ret_20d = pd.to_numeric(df["ret_20d"], errors="coerce")
    ret_60d = pd.to_numeric(df["ret_60d"], errors="coerce")
    positive_stack = trend + momentum

    regime = pd.Series("MIXED", index=df.index, dtype="string")
    regime = regime.mask(df["decision"].eq("AVOID"), "RISK_OFF")

    trending_mask = (
        ~df["decision"].eq("AVOID")
        & (ret_20d > 0)
        & (ret_60d > 0)
        & (trend >= 18)
        & (momentum >= 24)
        & (risk_abs <= 4)
    )
    regime = regime.mask(trending_mask, "TRENDING")

    risk_off_mask = (
        ~trending_mask
        & ~df["decision"].eq("AVOID")
        & ((risk_abs >= 7) | (positive_stack < 30))
    )
    regime = regime.mask(risk_off_mask, "RISK_OFF")
    return regime


def _derive_risk_level(df: pd.DataFrame) -> pd.Series:
    risk_abs = pd.to_numeric(df["risk_penalty"], errors="coerce").abs()
    volatility_20d = pd.to_numeric(df["volatility_20d"], errors="coerce")
    volatility_60d = pd.to_numeric(df["volatility_60d"], errors="coerce")
    dist_from_52w_high = pd.to_numeric(df["dist_from_52w_high"], errors="coerce")
    volatility_anchor = pd.concat([volatility_20d, volatility_60d], axis=1).max(axis=1, skipna=True)

    risk_level = pd.Series("LOW", index=df.index, dtype="string")
    risk_level = risk_level.mask((risk_abs >= 7) | (volatility_anchor >= 0.035), "HIGH")
    medium_mask = (
        ~risk_level.eq("HIGH")
        & ((risk_abs >= 4) | (volatility_anchor >= 0.020) | (dist_from_52w_high <= -0.20))
    )
    risk_level = risk_level.mask(medium_mask, "MEDIUM")
    return risk_level


def _derive_confidence(df: pd.DataFrame) -> pd.Series:
    base_map = {"BUY": 75, "HOLD": 60, "WATCH": 45, "AVOID": 35}

    confidence = df["decision"].map(base_map).fillna(35).astype(float)
    composite = pd.to_numeric(df["composite_score"], errors="coerce")
    trend = pd.to_numeric(df["trend_score"], errors="coerce")
    momentum = pd.to_numeric(df["momentum_score"], errors="coerce")
    risk_abs = pd.to_numeric(df["risk_penalty"], errors="coerce").abs()
    signal_balance_gap = (trend - momentum).abs()

    confidence = confidence + ((composite >= 50) * 10) + (((composite >= 40) & (composite < 50)) * 5)
    confidence = confidence - ((composite < 20) * 5)

    confidence = confidence - ((risk_abs >= 7) * 15) - (((risk_abs >= 4) & (risk_abs < 7)) * 8)

    confidence = confidence + ((signal_balance_gap <= 5) * 5) - ((signal_balance_gap >= 12) * 5)

    buy_boost = df["decision"].eq("BUY") & (trend >= 20) & (momentum >= 25)
    avoid_boost = df["decision"].eq("AVOID") & (risk_abs >= 7)
    confidence = confidence + (buy_boost * 5) + (avoid_boost * 5)

    return confidence.clip(lower=0, upper=100).round().astype(int)


def _derive_horizon_days(df: pd.DataFrame) -> pd.Series:
    trend = pd.to_numeric(df["trend_score"], errors="coerce")
    momentum = pd.to_numeric(df["momentum_score"], errors="coerce")

    horizon = pd.Series(60, index=df.index, dtype="int64")
    short_mask = df["regime"].eq("RISK_OFF") | df["decision"].eq("WATCH") | df["risk_level"].eq("HIGH")
    horizon = horizon.mask(short_mask, 30)

    long_mask = df["regime"].eq("TRENDING") & (trend >= momentum) & ~short_mask
    horizon = horizon.mask(long_mask, 90)

    medium_trending_mask = df["regime"].eq("TRENDING") & (momentum > trend) & ~short_mask
    horizon = horizon.mask(medium_trending_mask, 60)
    return horizon


def _rank_deterministic(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(
        ["composite_score", "ticker", "source_ticker"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)

    out["rank_overall"] = pd.RangeIndex(start=1, stop=len(out) + 1, step=1)
    out["rank_within_asset_type"] = (
        out.groupby("asset_type", sort=False)
        .cumcount()
        .add(1)
        .astype(int)
    )
    return out


def _validate_output(ranked: pd.DataFrame, input_rows: int) -> None:
    if len(ranked) != input_rows:
        raise ValueError(f"Row count mismatch: output={len(ranked)} input={input_rows}")

    if ranked["source_ticker"].duplicated().any():
        raise ValueError("Duplicate source_ticker found in output.")

    if ranked["ticker"].duplicated().any():
        dup = ranked.loc[ranked["ticker"].duplicated(keep=False), "ticker"].head(5).tolist()
        raise ValueError(f"Duplicate ticker found in output, sample={dup}")

    if not pd.api.types.is_numeric_dtype(ranked["composite_score"]):
        raise ValueError("composite_score is not numeric.")

    expected_overall = list(range(1, len(ranked) + 1))
    actual_overall = ranked["rank_overall"].astype(int).tolist()
    if actual_overall != expected_overall:
        raise ValueError("rank_overall has gaps or is not sequential from 1..N.")

    for asset_type, g in ranked.groupby("asset_type"):
        expected = list(range(1, len(g) + 1))
        actual = g["rank_within_asset_type"].astype(int).tolist()
        if actual != expected:
            raise ValueError(f"rank_within_asset_type invalid for asset_type={asset_type}")

    bad_decisions = set(ranked["decision"].dropna().unique()) - ALLOWED_DECISIONS
    if bad_decisions:
        raise ValueError(f"Unexpected decision values: {sorted(bad_decisions)}")

    bad_regimes = set(ranked["regime"].dropna().unique()) - ALLOWED_REGIMES
    if bad_regimes:
        raise ValueError(f"Unexpected regime values: {sorted(bad_regimes)}")

    bad_risk_levels = set(ranked["risk_level"].dropna().unique()) - ALLOWED_RISK_LEVELS
    if bad_risk_levels:
        raise ValueError(f"Unexpected risk_level values: {sorted(bad_risk_levels)}")

    if not pd.api.types.is_integer_dtype(ranked["confidence"]):
        raise ValueError("confidence is not integer typed.")
    if ((ranked["confidence"] < 0) | (ranked["confidence"] > 100)).any():
        raise ValueError("confidence contains values outside 0..100.")

    if not pd.api.types.is_integer_dtype(ranked["horizon_days"]):
        raise ValueError("horizon_days is not integer typed.")
    bad_horizons = set(ranked["horizon_days"].dropna().astype(int).unique()) - ALLOWED_HORIZON_DAYS
    if bad_horizons:
        raise ValueError(f"Unexpected horizon_days values: {sorted(bad_horizons)}")


def build_rankings(snapshot_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute trend/momentum/risk scores, composite score, labels, and ranks.
    """
    _validate_input_schema(snapshot_df)
    if snapshot_df.empty:
        raise ValueError("Input snapshot is empty.")

    df = snapshot_df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Score components
    df["trend_score"] = _trend_score(df)

    momentum_cols = ["ret_20d", "ret_60d", "ret_120d", "ret_252d"]
    for c in momentum_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[f"{c}_score"] = _percentile_score(df[c], low_fill_percentile=0.25)
    df["momentum_score"] = df[[f"{c}_score" for c in momentum_cols]].sum(axis=1).clip(lower=0.0, upper=40.0)

    risk_cols = ["volatility_20d", "volatility_60d"]
    for c in risk_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[f"{c}_penalty"] = _percentile_penalty(df[c], null_penalty_percentile=0.75)
    df["risk_penalty"] = df[[f"{c}_penalty" for c in risk_cols]].sum(axis=1).clip(lower=-10.0, upper=0.0)

    df["composite_score"] = (
        df["trend_score"] + df["momentum_score"] + df["risk_penalty"]
    ).clip(lower=0.0, upper=70.0)

    # Percentile bucketing stabilizes decision distribution across different market regimes.
    score_pct = df["composite_score"].rank(method="average", pct=True)
    df["decision"] = "AVOID"
    df.loc[score_pct >= 0.30, "decision"] = "WATCH"
    df.loc[score_pct >= 0.70, "decision"] = "HOLD"
    df.loc[score_pct >= 0.90, "decision"] = "BUY"

    df["decision_reason"] = _decision_reason(df)
    ranked = _rank_deterministic(df)
    regime = _derive_regime(ranked)
    regime = regime.mask(
        (ranked["decision"] == "BUY") & regime.eq("RISK_OFF"),
        "MIXED",
    )
    regime = regime.mask(
        (ranked["decision"] == "WATCH") & regime.eq("TRENDING"),
        "MIXED",
    )
    ranked["regime"] = regime
    ranked["risk_level"] = _derive_risk_level(ranked)
    ranked["confidence"] = _derive_confidence(ranked)
    ranked["horizon_days"] = _derive_horizon_days(ranked)

    out_cols = [
        "source_ticker",
        "ticker",
        "asset_type",
        "date",
        "close",
        "trend_score",
        "momentum_score",
        "risk_penalty",
        "composite_score",
        "decision",
        "rank_overall",
        "rank_within_asset_type",
        "ret_20d",
        "ret_60d",
        "ret_120d",
        "ret_252d",
        "volatility_20d",
        "volatility_60d",
        "dist_from_52w_high",
        "dist_from_52w_low",
        "is_active",
        "source",
        "decision_reason",
        "confidence",
        "regime",
        "risk_level",
        "horizon_days",
    ]
    ranked = ranked[out_cols].sort_values(["rank_overall", "ticker"], kind="mergesort").reset_index(drop=True)
    _validate_output(ranked, input_rows=len(snapshot_df))
    return ranked


def main() -> None:
    args = parse_args()
    if not args.input_parquet.exists():
        raise FileNotFoundError(f"Input parquet not found: {args.input_parquet}")

    snapshot = pd.read_parquet(args.input_parquet)
    ranked = build_rankings(snapshot)

    args.output_parquet.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_parquet(args.output_parquet, index=False)
    print(f"Ranked assets parquet written: {args.output_parquet}")
    print(f"Rows: {len(ranked):,}")

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    ranked.to_csv(args.output_csv, index=False, encoding="utf-8")
    print(f"Ranked assets csv written: {args.output_csv}")


if __name__ == "__main__":
    main()
