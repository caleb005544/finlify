from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_ROOT = REPO_ROOT / "output" / "pipeline_runs"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


PIPELINE_STEPS: list[dict[str, Any]] = [
    {
        "step_no": 1,
        "step_name": "initial_ingest",
        "script": "src/ingestion/initial_ingest.py",
        "module": "src.ingestion.initial_ingest",
        "stop_on_failure": True,
        "outputs": [
            {"path": "data/raw/stock_price_stooq/stock_prices.parquet", "type": "parquet", "check_rows": True},
        ],
    },
    {
        "step_no": 2,
        "step_name": "build_ticker_master",
        "script": "src/transform/build_ticker_master.py",
        "module": "src.transform.build_ticker_master",
        "stop_on_failure": True,
        "outputs": [
            {"path": "data/staging/stock_price_stooq/ticker_master.parquet", "type": "parquet", "check_rows": True},
        ],
    },
    {
        "step_no": 3,
        "step_name": "build_latest_snapshot",
        "script": "src/transform/build_latest_snapshot.py",
        "module": "src.transform.build_latest_snapshot",
        "stop_on_failure": False,
        "outputs": [
            {"path": "data/staging/stock_price_stooq/latest_snapshot.parquet", "type": "parquet", "check_rows": True},
        ],
    },
    {
        "step_no": 4,
        "step_name": "build_price_features",
        "script": "src/features/build_price_features.py",
        "module": "src.features.build_price_features",
        "stop_on_failure": True,
        "outputs": [
            {"path": "data/mart/investment/factor_features.parquet", "type": "parquet", "check_rows": True},
        ],
    },
    {
        "step_no": 5,
        "step_name": "build_factor_snapshot_latest",
        "script": "src/ranking/build_factor_snapshot_latest.py",
        "module": "src.ranking.build_factor_snapshot_latest",
        "stop_on_failure": True,
        "outputs": [
            {
                "path": "data/mart/investment/factor_snapshot_latest.parquet",
                "type": "parquet",
                "check_rows": True,
            },
        ],
    },
    {
        "step_no": 6,
        "step_name": "build_rankings",
        "script": "src/ranking/build_rankings.py",
        "module": "src.ranking.build_rankings",
        "stop_on_failure": True,
        "outputs": [
            {"path": "data/mart/investment/top_ranked_assets.parquet", "type": "parquet", "check_rows": True},
            {"path": "data/mart/investment/top_ranked_assets.csv", "type": "csv", "check_rows": True},
        ],
    },
    {
        "step_no": 7,
        "step_name": "build_signal_heatmap_snapshot",
        "script": "src/visualization/build_signal_heatmap_snapshot.py",
        "module": "src.visualization.build_signal_heatmap_snapshot",
        "stop_on_failure": True,
        "outputs": [
            {
                "path": "data/visualization/investment/signal_heatmap_snapshot.csv",
                "type": "csv",
                "check_rows": True,
            },
        ],
    },
    {
        "step_no": 8,
        "step_name": "build_visualization_exports",
        "script": "src/visualization/build_visualization_exports.py",
        "module": "src.visualization.build_visualization_exports",
        "stop_on_failure": True,
        "outputs": [
            {
                "path": "data/visualization/investment/price_history_for_pbi.csv",
                "type": "csv",
                "check_rows": True,
            },
            {
                "path": "data/visualization/investment/latest_ranking_for_pbi.csv",
                "type": "csv",
                "check_rows": True,
            },
        ],
    },
    {
        "step_no": 9,
        "step_name": "build_sarimax_forecast",
        "script": "src/features/build_sarimax_forecast.py",
        "module": "src.features.build_sarimax_forecast",
        "stop_on_failure": False,
        "outputs": [
            {
                "path": "data/visualization/investment/asset_forecast_for_streamlit.csv",
                "type": "csv",
                "check_rows": True,
            },
        ],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Finlify pipeline scripts in canonical order.")
    parser.add_argument("--from-step", type=int, default=1, help="Start from this step number (inclusive).")
    parser.add_argument("--to-step", type=int, default=len(PIPELINE_STEPS), help="End at this step number (inclusive).")
    parser.add_argument("--run-id", type=str, default=None, help="Optional run ID. Default: UTC timestamp.")
    parser.add_argument("--dry-run", action="store_true", help="Print/run plan only; do not execute scripts.")
    return parser.parse_args()


def csv_row_count(path: Path) -> int:
    # Lightweight line count: header is expected as first row.
    with path.open("r", encoding="utf-8", errors="replace") as f:
        lines = sum(1 for _ in f)
    return max(lines - 1, 0)


def parquet_row_count(path: Path) -> int:
    return int(pq.ParquetFile(path).metadata.num_rows)


def run_output_checks(step: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    checks: list[dict[str, Any]] = []
    all_passed = True

    for target in step["outputs"]:
        rel_path = target["path"]
        file_type = target["type"]
        check_rows = bool(target.get("check_rows", False))
        abs_path = REPO_ROOT / rel_path

        exists = abs_path.exists()
        non_empty = bool(exists and abs_path.stat().st_size > 0)
        row_count: int | None = None
        row_count_ok: bool | None = None
        check_error: str | None = None

        if exists and non_empty and check_rows:
            try:
                if file_type == "csv":
                    row_count = csv_row_count(abs_path)
                elif file_type == "parquet":
                    row_count = parquet_row_count(abs_path)
                else:
                    check_error = f"Unsupported output type: {file_type}"
            except Exception as exc:  # noqa: BLE001
                check_error = f"row_count_check_failed: {type(exc).__name__}: {exc}"

            if check_error is None:
                row_count_ok = row_count is not None and row_count > 0
            else:
                row_count_ok = False

        passed = exists and non_empty and ((not check_rows) or bool(row_count_ok))
        if not passed:
            all_passed = False

        checks.append(
            {
                "path": rel_path,
                "type": file_type,
                "exists": exists,
                "non_empty": non_empty,
                "row_count": row_count,
                "row_count_ok": row_count_ok,
                "passed": passed,
                "check_error": check_error,
            }
        )

    return checks, all_passed


def write_step_log(
    log_path: Path,
    step: dict[str, Any],
    command: list[str],
    started_at: str,
    ended_at: str,
    returncode: int | None,
    output_checks: list[dict[str, Any]],
    stdout_text: str,
    stderr_text: str,
) -> None:
    lines: list[str] = []
    lines.append(f"step_no: {step['step_no']}")
    lines.append(f"step_name: {step['step_name']}")
    lines.append(f"script: {step['script']}")
    lines.append(f"started_at: {started_at}")
    lines.append(f"ended_at: {ended_at}")
    lines.append(f"returncode: {returncode}")
    lines.append(f"command: {' '.join(command)}")
    lines.append("")
    lines.append("output_checks:")
    lines.append(json.dumps(output_checks, indent=2))
    lines.append("")
    lines.append("stdout:")
    lines.append(stdout_text.rstrip("\n"))
    lines.append("")
    lines.append("stderr:")
    lines.append(stderr_text.rstrip("\n"))
    lines.append("")
    log_path.write_text("\n".join(lines), encoding="utf-8")


def execute_step(step: dict[str, Any], run_dir: Path, dry_run: bool) -> dict[str, Any]:
    started_at = utc_now_iso()
    log_path = run_dir / f"step_{step['step_no']}_{step['step_name']}.log"
    command = [sys.executable, "-m", step["module"]]

    if dry_run:
        ended_at = utc_now_iso()
        write_step_log(
            log_path=log_path,
            step=step,
            command=command,
            started_at=started_at,
            ended_at=ended_at,
            returncode=None,
            output_checks=[],
            stdout_text="[dry-run] command not executed.",
            stderr_text="",
        )
        return {
            "step_no": step["step_no"],
            "step_name": step["step_name"],
            "script": step["script"],
            "status": "dry_run",
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_sec": 0.0,
            "log_path": str(log_path.relative_to(REPO_ROOT)),
            "output_checks": [],
            "error_message": None,
        }

    proc = subprocess.run(  # noqa: S603
        command,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    ended_at = utc_now_iso()

    checks, checks_passed = run_output_checks(step)
    has_exec_error = proc.returncode != 0
    has_validation_error = not checks_passed
    failure = has_exec_error or has_validation_error

    if failure and step["stop_on_failure"]:
        status = "failed"
    elif failure and not step["stop_on_failure"]:
        status = "warning"
    else:
        status = "success"

    error_parts: list[str] = []
    if has_exec_error:
        error_parts.append(f"script_return_code={proc.returncode}")
    if has_validation_error:
        error_parts.append("output_validation_failed")
    error_message = "; ".join(error_parts) if error_parts else None

    started_dt = datetime.fromisoformat(started_at)
    ended_dt = datetime.fromisoformat(ended_at)
    duration_sec = (ended_dt - started_dt).total_seconds()

    write_step_log(
        log_path=log_path,
        step=step,
        command=command,
        started_at=started_at,
        ended_at=ended_at,
        returncode=proc.returncode,
        output_checks=checks,
        stdout_text=proc.stdout,
        stderr_text=proc.stderr,
    )

    return {
        "step_no": step["step_no"],
        "step_name": step["step_name"],
        "script": step["script"],
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_sec": duration_sec,
        "log_path": str(log_path.relative_to(REPO_ROOT)),
        "output_checks": checks,
        "error_message": error_message,
    }


def main() -> int:
    args = parse_args()
    run_id = args.run_id or default_run_id()

    if args.from_step < 1 or args.to_step > len(PIPELINE_STEPS):
        print(f"Invalid step range. Must be within 1..{len(PIPELINE_STEPS)}", file=sys.stderr)
        return 2
    if args.from_step > args.to_step:
        print("--from-step must be <= --to-step", file=sys.stderr)
        return 2

    selected_steps = [s for s in PIPELINE_STEPS if args.from_step <= s["step_no"] <= args.to_step]

    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    start_ts = utc_now_iso()
    steps_result: list[dict[str, Any]] = []
    hard_failed = False
    stop_after_idx: int | None = None

    for idx, step in enumerate(selected_steps):
        result = execute_step(step=step, run_dir=run_dir, dry_run=args.dry_run)
        steps_result.append(result)
        print(f"[step {step['step_no']}] {step['step_name']} -> {result['status']}")

        if result["status"] == "failed":
            hard_failed = True
            stop_after_idx = idx
            break

    if stop_after_idx is not None:
        for step in selected_steps[stop_after_idx + 1 :]:
            steps_result.append(
                {
                    "step_no": step["step_no"],
                    "step_name": step["step_name"],
                    "script": step["script"],
                    "status": "not_run",
                    "started_at": None,
                    "ended_at": None,
                    "duration_sec": None,
                    "log_path": None,
                    "output_checks": [],
                    "error_message": "not_run_due_to_prior_hard_failure",
                }
            )

    end_ts = utc_now_iso()

    if args.dry_run:
        overall_status = "dry_run"
    elif hard_failed:
        overall_status = "failed"
    elif any(s["status"] == "warning" for s in steps_result):
        overall_status = "warning"
    else:
        overall_status = "success"

    summary = {
        "run_id": run_id,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "overall_status": overall_status,
        "steps": sorted(steps_result, key=lambda x: x["step_no"]),
    }

    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Run ID: {run_id}")
    print(f"Summary: {summary_path.relative_to(REPO_ROOT)}")
    print(f"Overall status: {overall_status}")

    return 1 if overall_status == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
