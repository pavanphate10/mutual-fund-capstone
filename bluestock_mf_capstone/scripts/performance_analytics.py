"""Generate performance analytics deliverables for the mutual fund capstone."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd
from scipy.stats import linregress


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "04_performance_analytics.ipynb"
SCORECARD_PATH = REPORTS_DIR / "fund_scorecard.csv"
ALPHA_BETA_PATH = REPORTS_DIR / "alpha_beta.csv"
CHART_PATH = REPORTS_DIR / "benchmark_comparison_chart.png"

RISK_FREE_RATE = 0.065
TRADING_DAYS = 252


@dataclass
class DrawdownResult:
    max_drawdown: float
    peak_date: pd.Timestamp | None
    trough_date: pd.Timestamp | None
    recovery_date: pd.Timestamp | None


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nav = pd.read_csv(PROCESSED_DIR / "nav_history.csv", parse_dates=["date"])
    benchmarks = pd.read_csv(
        PROCESSED_DIR / "benchmark_indices.csv",
        parse_dates=["date"],
    )
    fund_master = pd.read_csv(PROCESSED_DIR / "fund_master.csv")
    return nav, benchmarks, fund_master


def compute_daily_returns(nav: pd.DataFrame) -> pd.DataFrame:
    data = nav.copy().sort_values(["amfi_code", "date"])
    data["daily_return"] = data.groupby("amfi_code")["nav"].pct_change()
    return data


def trailing_cagr(nav_group: pd.DataFrame, years: int) -> float:
    end_date = nav_group["date"].max()
    start_cutoff = end_date - pd.Timedelta(days=int(round(365.25 * years)))
    eligible = nav_group.loc[nav_group["date"] <= start_cutoff]
    if eligible.empty:
        return np.nan

    start_row = eligible.iloc[-1]
    end_row = nav_group.iloc[-1]
    elapsed_years = (end_row["date"] - start_row["date"]).days / 365.25
    if elapsed_years <= 0:
        return np.nan
    return (end_row["nav"] / start_row["nav"]) ** (1 / elapsed_years) - 1


def downside_std(returns: pd.Series) -> float:
    downside = returns[returns < 0]
    if downside.empty:
        return np.nan
    return downside.std(ddof=0)


def compute_drawdown(nav_group: pd.DataFrame) -> DrawdownResult:
    series = nav_group.sort_values("date").reset_index(drop=True)
    running_max = series["nav"].cummax()
    drawdown = series["nav"] / running_max - 1
    trough_idx = drawdown.idxmin()
    peak_value = running_max.iloc[trough_idx]
    peak_idx = series.loc[:trough_idx, "nav"].eq(peak_value).to_numpy().nonzero()[0][-1]

    recovery_idx = None
    recovery_candidates = series.index[(series.index > trough_idx) & (series["nav"] >= peak_value)]
    if len(recovery_candidates) > 0:
        recovery_idx = int(recovery_candidates[0])

    return DrawdownResult(
        max_drawdown=float(drawdown.iloc[trough_idx]),
        peak_date=series.loc[peak_idx, "date"],
        trough_date=series.loc[trough_idx, "date"],
        recovery_date=series.loc[recovery_idx, "date"] if recovery_idx is not None else None,
    )


def rank_to_score(rank_series: pd.Series) -> pd.Series:
    if len(rank_series) <= 1:
        return pd.Series([100.0] * len(rank_series), index=rank_series.index)
    return (len(rank_series) - rank_series) / (len(rank_series) - 1) * 100


def build_metrics(
    nav_returns: pd.DataFrame,
    benchmarks: pd.DataFrame,
    fund_master: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nifty100 = benchmarks.loc[benchmarks["index_name"] == "NIFTY100", ["date", "close_value"]].copy()
    nifty100 = nifty100.sort_values("date")
    nifty100["benchmark_return"] = nifty100["close_value"].pct_change()
    nifty100_returns = nifty100[["date", "benchmark_return"]]

    metrics: list[dict[str, object]] = []
    daily_returns_export = nav_returns.merge(
        fund_master[["amfi_code", "scheme_name", "expense_ratio_pct", "benchmark"]],
        on="amfi_code",
        how="left",
    )

    for amfi_code, group in nav_returns.groupby("amfi_code", sort=True):
        group = group.sort_values("date").reset_index(drop=True)
        returns = group["daily_return"].dropna()
        drawdown = compute_drawdown(group)
        meta = fund_master.loc[fund_master["amfi_code"] == amfi_code].iloc[0]

        merged = group[["date", "daily_return"]].merge(
            nifty100_returns,
            on="date",
            how="inner",
        ).dropna()

        if len(merged) >= 2:
            regression = linregress(merged["benchmark_return"], merged["daily_return"])
            alpha_daily = float(regression.intercept)
            beta = float(regression.slope)
        else:
            alpha_daily = np.nan
            beta = np.nan

        mean_daily = returns.mean()
        std_daily = returns.std(ddof=0)
        rf_daily = RISK_FREE_RATE / TRADING_DAYS

        sharpe = np.nan
        if pd.notna(std_daily) and std_daily > 0:
            sharpe = ((mean_daily - rf_daily) / std_daily) * np.sqrt(TRADING_DAYS)

        sortino = np.nan
        downside = downside_std(returns)
        if pd.notna(downside) and downside > 0:
            sortino = ((mean_daily - rf_daily) / downside) * np.sqrt(TRADING_DAYS)

        metrics.append(
            {
                "amfi_code": amfi_code,
                "scheme_name": meta["scheme_name"],
                "fund_house": meta["fund_house"],
                "benchmark": meta["benchmark"],
                "expense_ratio_pct": meta["expense_ratio_pct"],
                "daily_return_mean": mean_daily,
                "daily_return_std": std_daily,
                "daily_return_days": int(returns.shape[0]),
                "cagr_1yr": trailing_cagr(group, 1),
                "cagr_3yr": trailing_cagr(group, 3),
                "cagr_5yr": trailing_cagr(group, 5),
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "alpha_daily": alpha_daily,
                "alpha_annual": alpha_daily * TRADING_DAYS if pd.notna(alpha_daily) else np.nan,
                "beta": beta,
                "max_drawdown": drawdown.max_drawdown,
                "drawdown_peak_date": drawdown.peak_date,
                "drawdown_trough_date": drawdown.trough_date,
                "drawdown_recovery_date": drawdown.recovery_date,
            }
        )

    metrics_df = pd.DataFrame(metrics).sort_values("amfi_code").reset_index(drop=True)
    alpha_beta = metrics_df[
        [
            "amfi_code",
            "scheme_name",
            "fund_house",
            "alpha_daily",
            "alpha_annual",
            "beta",
            "drawdown_peak_date",
            "drawdown_trough_date",
            "drawdown_recovery_date",
        ]
    ].copy()
    alpha_beta["alpha_annual_pct"] = alpha_beta["alpha_annual"] * 100

    return metrics_df, alpha_beta, daily_returns_export


def compute_tracking_errors(
    nav_returns: pd.DataFrame,
    benchmarks: pd.DataFrame,
    top_funds: Iterable[int],
) -> pd.DataFrame:
    benchmark_returns = benchmarks.copy().sort_values(["index_name", "date"])
    benchmark_returns["benchmark_return"] = benchmark_returns.groupby("index_name")["close_value"].pct_change()
    benchmark_returns = benchmark_returns[benchmark_returns["index_name"].isin(["NIFTY50", "NIFTY100"])]

    rows: list[dict[str, object]] = []
    for amfi_code in top_funds:
        fund_slice = nav_returns.loc[nav_returns["amfi_code"] == amfi_code, ["date", "daily_return"]].dropna()
        for benchmark_name in ["NIFTY50", "NIFTY100"]:
            bench_slice = benchmark_returns.loc[
                benchmark_returns["index_name"] == benchmark_name,
                ["date", "benchmark_return"],
            ].dropna()
            merged = fund_slice.merge(bench_slice, on="date", how="inner")
            tracking_error = np.nan
            if not merged.empty:
                active_return = merged["daily_return"] - merged["benchmark_return"]
                tracking_error = active_return.std(ddof=0) * np.sqrt(TRADING_DAYS)
            rows.append(
                {
                    "amfi_code": amfi_code,
                    "benchmark_name": benchmark_name,
                    "tracking_error": tracking_error,
                }
            )
    return pd.DataFrame(rows)


def build_scorecard(metrics_df: pd.DataFrame) -> pd.DataFrame:
    scorecard = metrics_df.copy()
    scorecard["rank_3yr_return"] = scorecard["cagr_3yr"].rank(ascending=False, method="min")
    scorecard["rank_sharpe"] = scorecard["sharpe_ratio"].rank(ascending=False, method="min")
    scorecard["rank_alpha"] = scorecard["alpha_annual"].rank(ascending=False, method="min")
    scorecard["rank_expense_inverse"] = scorecard["expense_ratio_pct"].rank(ascending=True, method="min")
    scorecard["rank_max_dd_inverse"] = scorecard["max_drawdown"].rank(ascending=False, method="min")

    scorecard["score_3yr_return"] = rank_to_score(scorecard["rank_3yr_return"])
    scorecard["score_sharpe"] = rank_to_score(scorecard["rank_sharpe"])
    scorecard["score_alpha"] = rank_to_score(scorecard["rank_alpha"])
    scorecard["score_expense"] = rank_to_score(scorecard["rank_expense_inverse"])
    scorecard["score_max_dd"] = rank_to_score(scorecard["rank_max_dd_inverse"])

    scorecard["fund_score"] = (
        0.30 * scorecard["score_3yr_return"]
        + 0.25 * scorecard["score_sharpe"]
        + 0.20 * scorecard["score_alpha"]
        + 0.15 * scorecard["score_expense"]
        + 0.10 * scorecard["score_max_dd"]
    ).round(2)

    scorecard = scorecard.sort_values(
        ["fund_score", "cagr_3yr", "sharpe_ratio"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    scorecard["overall_rank"] = np.arange(1, len(scorecard) + 1)
    return scorecard


def validate_distribution(nav_returns: pd.DataFrame) -> dict[str, object]:
    returns = nav_returns["daily_return"].dropna()
    summary = returns.describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99]).to_dict()
    extreme_ratio = float((returns.abs() > 0.10).mean())
    reasonable = (
        summary["1%"] > -0.08
        and summary["99%"] < 0.08
        and extreme_ratio < 0.01
    )
    return {
        "count": int(summary["count"]),
        "mean": float(summary["mean"]),
        "std": float(summary["std"]),
        "min": float(summary["min"]),
        "1%": float(summary["1%"]),
        "5%": float(summary["5%"]),
        "50%": float(summary["50%"]),
        "95%": float(summary["95%"]),
        "99%": float(summary["99%"]),
        "max": float(summary["max"]),
        "pct_abs_gt_10pct": extreme_ratio,
        "looks_reasonable": reasonable,
    }


def render_benchmark_chart(
    nav_returns: pd.DataFrame,
    benchmarks: pd.DataFrame,
    scorecard: pd.DataFrame,
) -> None:
    top_five = scorecard.head(5)[["amfi_code", "scheme_name"]]
    end_date = nav_returns["date"].max()
    start_cutoff = end_date - pd.Timedelta(days=int(round(365.25 * 3)))

    fund_window = nav_returns.loc[
        (nav_returns["amfi_code"].isin(top_five["amfi_code"])) & (nav_returns["date"] >= start_cutoff),
        ["amfi_code", "date", "nav"],
    ].merge(top_five, on="amfi_code", how="left")

    benchmark_window = benchmarks.loc[
        benchmarks["index_name"].isin(["NIFTY50", "NIFTY100"]) & (benchmarks["date"] >= start_cutoff),
        ["date", "index_name", "close_value"],
    ].copy()

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(14, 8))

    for amfi_code, group in fund_window.groupby("amfi_code"):
        series = group.sort_values("date").copy()
        series["normalized"] = 100 * series["nav"] / series["nav"].iloc[0]
        label = series["scheme_name"].iloc[0]
        ax.plot(series["date"], series["normalized"], linewidth=2, label=label)

    benchmark_palette = {"NIFTY50": "#222222", "NIFTY100": "#cc5500"}
    for benchmark_name, group in benchmark_window.groupby("index_name"):
        series = group.sort_values("date").copy()
        series["normalized"] = 100 * series["close_value"] / series["close_value"].iloc[0]
        ax.plot(
            series["date"],
            series["normalized"],
            linestyle="--",
            linewidth=2.5,
            color=benchmark_palette.get(benchmark_name),
            label=benchmark_name,
        )

    ax.set_title("Top 5 Fund Scorecard Winners vs NIFTY50 and NIFTY100 (Trailing 3 Years)")
    ax.set_ylabel("Normalized Growth (Base = 100)")
    ax.set_xlabel("Date")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(CHART_PATH, dpi=200, bbox_inches="tight")
    plt.close(fig)


def table_block(dataframe: pd.DataFrame, columns: list[str] | None = None, rows: int = 10) -> str:
    table = dataframe if columns is None else dataframe[columns]
    return "```text\n" + table.head(rows).to_string(index=False) + "\n```"


def build_notebook(
    distribution_summary: dict[str, object],
    metrics_df: pd.DataFrame,
    scorecard: pd.DataFrame,
    alpha_beta: pd.DataFrame,
    tracking_errors: pd.DataFrame,
) -> None:
    notebook = nbformat.v4.new_notebook()

    top_sharpe = metrics_df.sort_values("sharpe_ratio", ascending=False).reset_index(drop=True)
    cagr_table = metrics_df[
        ["scheme_name", "cagr_1yr", "cagr_3yr", "cagr_5yr"]
    ].sort_values("cagr_3yr", ascending=False)
    tracking_view = tracking_errors.merge(
        scorecard[["amfi_code", "scheme_name", "overall_rank"]],
        on="amfi_code",
        how="left",
    ).sort_values(["overall_rank", "benchmark_name"])

    notebook.cells = [
        nbformat.v4.new_markdown_cell(
            "# Performance Analytics\n"
            "This notebook summarizes return, risk, regression, drawdown, scorecard, "
            "and benchmark-comparison analytics for the 40 mutual fund schemes in the capstone dataset."
        ),
        nbformat.v4.new_markdown_cell(
            "## Data Coverage and Assumptions\n"
            "- Input files came from `data/processed/nav_history.csv`, `fund_master.csv`, and `benchmark_indices.csv`.\n"
            "- NAV and benchmark history spans **2022-01-03 to 2026-05-29**.\n"
            "- Daily returns use `nav_t / nav_t-1 - 1`.\n"
            "- Sharpe and Sortino use a **6.5% annual risk-free rate** with 252 trading days.\n"
            "- Alpha and beta come from `scipy.stats.linregress` of fund daily returns against `NIFTY100` daily returns.\n"
            "- Because the available history is under five years, trailing **5-year CAGR is unavailable** and remains `NaN` for all schemes."
        ),
        nbformat.v4.new_markdown_cell(
            "## Daily Return Distribution Check\n"
            f"- Observations: **{distribution_summary['count']}**\n"
            f"- Mean daily return: **{distribution_summary['mean']:.5f}**\n"
            f"- Daily volatility: **{distribution_summary['std']:.5f}**\n"
            f"- 1st / 99th percentiles: **{distribution_summary['1%']:.4f}** / **{distribution_summary['99%']:.4f}**\n"
            f"- Share of days with |return| > 10%: **{distribution_summary['pct_abs_gt_10pct']:.2%}**\n"
            f"- Distribution looks reasonable: **{distribution_summary['looks_reasonable']}**"
        ),
        nbformat.v4.new_markdown_cell(
            "## CAGR Comparison\n"
            + table_block(
                cagr_table.assign(
                    cagr_1yr=lambda df: (df["cagr_1yr"] * 100).round(2),
                    cagr_3yr=lambda df: (df["cagr_3yr"] * 100).round(2),
                    cagr_5yr=lambda df: (df["cagr_5yr"] * 100).round(2),
                ),
                rows=12,
            )
        ),
        nbformat.v4.new_markdown_cell(
            "## Sharpe and Sortino Leaders\n"
            + table_block(
                top_sharpe.assign(
                    sharpe_ratio=lambda df: df["sharpe_ratio"].round(3),
                    sortino_ratio=lambda df: df["sortino_ratio"].round(3),
                    alpha_annual_pct=lambda df: (df["alpha_annual"] * 100).round(2),
                )[
                    ["scheme_name", "sharpe_ratio", "sortino_ratio", "alpha_annual_pct", "beta"]
                ],
                rows=12,
            )
        ),
        nbformat.v4.new_markdown_cell(
            "## Alpha / Beta Snapshot\n"
            + table_block(
                alpha_beta.assign(
                    alpha_daily=lambda df: df["alpha_daily"].round(6),
                    alpha_annual_pct=lambda df: df["alpha_annual_pct"].round(2),
                    beta=lambda df: df["beta"].round(3),
                )[
                    [
                        "scheme_name",
                        "alpha_daily",
                        "alpha_annual_pct",
                        "beta",
                        "drawdown_peak_date",
                        "drawdown_trough_date",
                        "drawdown_recovery_date",
                    ]
                ],
                rows=12,
            )
        ),
        nbformat.v4.new_markdown_cell(
            "## Fund Scorecard\n"
            + table_block(
                scorecard.assign(
                    cagr_3yr_pct=lambda df: (df["cagr_3yr"] * 100).round(2),
                    sharpe_ratio=lambda df: df["sharpe_ratio"].round(3),
                    alpha_annual_pct=lambda df: (df["alpha_annual"] * 100).round(2),
                    max_drawdown_pct=lambda df: (df["max_drawdown"] * 100).round(2),
                )[
                    [
                        "overall_rank",
                        "scheme_name",
                        "fund_score",
                        "cagr_3yr_pct",
                        "sharpe_ratio",
                        "alpha_annual_pct",
                        "expense_ratio_pct",
                        "max_drawdown_pct",
                    ]
                ],
                rows=15,
            )
        ),
        nbformat.v4.new_markdown_cell(
            "## Tracking Error for Top 5 Funds\n"
            + table_block(
                tracking_view.assign(
                    tracking_error_pct=lambda df: (df["tracking_error"] * 100).round(2)
                )[
                    ["overall_rank", "scheme_name", "benchmark_name", "tracking_error_pct"]
                ],
                rows=10,
            )
            + "\nBenchmark comparison chart exported to `benchmark_comparison_chart.png`."
        ),
    ]

    nbformat.write(notebook, NOTEBOOK_PATH)


def main() -> None:
    nav, benchmarks, fund_master = load_inputs()
    nav_returns = compute_daily_returns(nav)
    distribution_summary = validate_distribution(nav_returns)
    metrics_df, alpha_beta, _ = build_metrics(nav_returns, benchmarks, fund_master)
    scorecard = build_scorecard(metrics_df)
    top_funds = scorecard.head(5)["amfi_code"].tolist()
    tracking_errors = compute_tracking_errors(nav_returns, benchmarks, top_funds)

    scorecard_export = scorecard.copy()
    scorecard_export["cagr_1yr_pct"] = scorecard_export["cagr_1yr"] * 100
    scorecard_export["cagr_3yr_pct"] = scorecard_export["cagr_3yr"] * 100
    scorecard_export["cagr_5yr_pct"] = scorecard_export["cagr_5yr"] * 100
    scorecard_export["alpha_annual_pct"] = scorecard_export["alpha_annual"] * 100
    scorecard_export["max_drawdown_pct"] = scorecard_export["max_drawdown"] * 100

    tracking_wide = tracking_errors.pivot(
        index="amfi_code",
        columns="benchmark_name",
        values="tracking_error",
    ).reset_index().rename_axis(None, axis=1)
    tracking_wide = tracking_wide.rename(
        columns={
            "NIFTY50": "tracking_error_nifty50",
            "NIFTY100": "tracking_error_nifty100",
        }
    )
    scorecard_export = scorecard_export.merge(tracking_wide, on="amfi_code", how="left")

    scorecard_export.to_csv(SCORECARD_PATH, index=False)
    alpha_beta.to_csv(ALPHA_BETA_PATH, index=False)
    render_benchmark_chart(nav_returns, benchmarks, scorecard)
    build_notebook(distribution_summary, metrics_df, scorecard, alpha_beta, tracking_errors)


if __name__ == "__main__":
    main()
