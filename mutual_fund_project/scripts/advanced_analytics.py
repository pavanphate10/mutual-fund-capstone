"""Generate advanced analytics deliverables for the mutual fund project."""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "05_advanced_analytics.ipynb"
VAR_CVAR_PATH = PROJECT_ROOT / "var_cvar_report.csv"
ROLLING_SHARPE_CHART_PATH = PROJECT_ROOT / "rolling_sharpe_chart.png"

TRADING_DAYS = 252
ROLLING_WINDOW = 90
KEY_FUND_COUNT = 5
SIP_AT_RISK_DAYS = 35
MIN_SIP_TRANSACTIONS = 6


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    nav = pd.read_csv(PROCESSED_DIR / "nav_history.csv", parse_dates=["date"])
    scheme_performance = pd.read_csv(PROCESSED_DIR / "scheme_performance.csv")
    fund_master = pd.read_csv(PROCESSED_DIR / "fund_master.csv")
    transactions = pd.read_csv(
        PROCESSED_DIR / "investor_transactions.csv",
        parse_dates=["transaction_date"],
    )
    holdings = pd.read_csv(PROCESSED_DIR / "portfolio_holdings.csv")
    return nav, scheme_performance, fund_master, transactions, holdings


def compute_daily_returns(nav: pd.DataFrame) -> pd.DataFrame:
    returns = nav.sort_values(["amfi_code", "date"]).copy()
    returns["daily_return"] = returns.groupby("amfi_code")["nav"].pct_change()
    return returns


def compute_var_cvar(
    nav_returns: pd.DataFrame,
    scheme_performance: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    metadata = scheme_performance.set_index("amfi_code")

    for amfi_code, group in nav_returns.groupby("amfi_code", sort=True):
        returns = group["daily_return"].dropna()
        if returns.empty:
            var_95 = np.nan
            cvar_95 = np.nan
            observation_count = 0
        else:
            var_95 = float(returns.quantile(0.05))
            cvar_95 = float(returns.loc[returns <= var_95].mean())
            observation_count = int(returns.shape[0])

        meta = metadata.loc[amfi_code]
        rows.append(
            {
                "amfi_code": amfi_code,
                "scheme_name": meta["scheme_name"],
                "fund_house": meta["fund_house"],
                "category": meta["category"],
                "plan": meta["plan"],
                "risk_grade": meta["risk_grade"],
                "sharpe_ratio": meta["sharpe_ratio"],
                "var_95": var_95,
                "cvar_95": cvar_95,
                "var_95_pct": var_95 * 100 if pd.notna(var_95) else np.nan,
                "cvar_95_pct": cvar_95 * 100 if pd.notna(cvar_95) else np.nan,
                "return_observations": observation_count,
            }
        )

    return pd.DataFrame(rows).sort_values("var_95").reset_index(drop=True)


def compute_rolling_sharpe(nav_returns: pd.DataFrame) -> pd.DataFrame:
    series = nav_returns.sort_values(["amfi_code", "date"]).copy()

    grouped = series.groupby("amfi_code")["daily_return"]
    rolling_mean = grouped.transform(lambda s: s.rolling(ROLLING_WINDOW).mean())
    rolling_std = grouped.transform(lambda s: s.rolling(ROLLING_WINDOW).std())

    series["rolling_sharpe_90d"] = (rolling_mean / rolling_std) * np.sqrt(TRADING_DAYS)
    return series


def select_key_funds(
    rolling_sharpe: pd.DataFrame,
    scheme_performance: pd.DataFrame,
) -> pd.DataFrame:
    top_codes = (
        scheme_performance.sort_values(["aum_crore", "sharpe_ratio"], ascending=[False, False])
        .head(KEY_FUND_COUNT)["amfi_code"]
        .tolist()
    )
    scheme_names = scheme_performance[["amfi_code", "scheme_name"]].drop_duplicates()
    return rolling_sharpe.loc[rolling_sharpe["amfi_code"].isin(top_codes)].merge(
        scheme_names,
        on="amfi_code",
        how="left",
    )


def render_rolling_sharpe_chart(key_funds: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(14, 8))

    for amfi_code, group in key_funds.groupby("amfi_code", sort=False):
        series = group.sort_values("date")
        ax.plot(
            series["date"],
            series["rolling_sharpe_90d"],
            linewidth=2,
            label=series["scheme_name"].iloc[0],
        )

    ax.set_title("Rolling 90-Day Sharpe Ratio for 5 Key Funds")
    ax.set_xlabel("Date")
    ax.set_ylabel("Rolling Sharpe Ratio")
    ax.axhline(0, color="#444444", linewidth=1, linestyle="--")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(ROLLING_SHARPE_CHART_PATH, dpi=200, bbox_inches="tight")
    plt.close(fig)


def compute_investor_cohorts(
    transactions: pd.DataFrame,
    scheme_performance: pd.DataFrame,
) -> pd.DataFrame:
    investor_first_year = (
        transactions.groupby("investor_id")["transaction_date"].min().dt.year.rename("cohort_year")
    )
    cohort_data = transactions.merge(investor_first_year, on="investor_id", how="left")

    sip_only = cohort_data.loc[cohort_data["transaction_type"] == "SIP"].copy()
    avg_sip = sip_only.groupby("cohort_year")["amount_inr"].mean().rename("avg_sip_amount_inr")

    invested = cohort_data.loc[
        cohort_data["transaction_type"].isin(["SIP", "Lumpsum"])
    ].groupby("cohort_year")["amount_inr"].sum().rename("total_invested_inr")

    fund_pref = (
        cohort_data.loc[cohort_data["transaction_type"].isin(["SIP", "Lumpsum"])]
        .groupby(["cohort_year", "amfi_code"])["amount_inr"]
        .sum()
        .reset_index()
        .sort_values(["cohort_year", "amount_inr", "amfi_code"], ascending=[True, False, True])
        .drop_duplicates("cohort_year")
        .merge(
            scheme_performance[["amfi_code", "scheme_name"]],
            on="amfi_code",
            how="left",
        )
        .rename(
            columns={
                "amfi_code": "top_fund_amfi_code",
                "scheme_name": "top_fund_preference",
                "amount_inr": "top_fund_invested_inr",
            }
        )
        .set_index("cohort_year")
    )

    investor_count = investor_first_year.value_counts().rename_axis("cohort_year").rename("investor_count")

    cohort_summary = pd.concat([investor_count, avg_sip, invested, fund_pref], axis=1).reset_index()
    return cohort_summary.sort_values("cohort_year").reset_index(drop=True)


def compute_sip_continuity(transactions: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float]]:
    sip = transactions.loc[transactions["transaction_type"] == "SIP"].copy()
    sip = sip.sort_values(["investor_id", "transaction_date"])
    sip["gap_days"] = sip.groupby("investor_id")["transaction_date"].diff().dt.days

    eligible = sip.groupby("investor_id").filter(lambda frame: len(frame) >= MIN_SIP_TRANSACTIONS)
    investor_gaps = (
        eligible.groupby("investor_id")
        .agg(
            sip_transactions=("transaction_date", "size"),
            avg_gap_days=("gap_days", "mean"),
            median_gap_days=("gap_days", "median"),
            latest_sip_date=("transaction_date", "max"),
        )
        .reset_index()
    )
    investor_gaps["continuity_status"] = np.where(
        investor_gaps["avg_gap_days"] > SIP_AT_RISK_DAYS,
        "at-risk",
        "healthy",
    )

    summary = {
        "eligible_investors": int(investor_gaps.shape[0]),
        "at_risk_investors": int((investor_gaps["continuity_status"] == "at-risk").sum()),
        "continuity_rate": float((investor_gaps["continuity_status"] == "healthy").mean()),
        "avg_gap_days_overall": float(investor_gaps["avg_gap_days"].mean()),
    }
    return investor_gaps.sort_values(["avg_gap_days", "sip_transactions"], ascending=[False, False]), summary


def compute_hhi(
    holdings: pd.DataFrame,
    scheme_performance: pd.DataFrame,
    fund_master: pd.DataFrame,
) -> pd.DataFrame:
    equity_codes = (
        fund_master.loc[
            fund_master["category"].str.contains("equity", case=False, na=False),
            ["amfi_code"],
        ]
        .drop_duplicates()
        .merge(
            scheme_performance[
                ["amfi_code", "scheme_name", "fund_house", "category", "plan", "risk_grade"]
            ].drop_duplicates(),
            on="amfi_code",
            how="left",
        )
    )

    equity_holdings = holdings.merge(equity_codes, on="amfi_code", how="inner")
    hhi = (
        equity_holdings.assign(weight_decimal=equity_holdings["weight_pct"] / 100)
        .groupby(["amfi_code", "scheme_name", "fund_house", "category", "plan", "risk_grade"])
        .agg(
            hhi=("weight_decimal", lambda s: float(np.square(s).sum())),
            holdings_count=("stock_symbol", "nunique"),
            top_sector=("sector", lambda s: s.value_counts().index[0] if not s.empty else np.nan),
            top_holding_weight_pct=("weight_pct", "max"),
        )
        .reset_index()
        .sort_values("hhi", ascending=False)
        .reset_index(drop=True)
    )
    hhi["concentration_label"] = pd.cut(
        hhi["hhi"],
        bins=[-np.inf, 0.10, 0.18, np.inf],
        labels=["Diversified", "Balanced", "Concentrated"],
    )
    return hhi


def top_funds_by_risk_appetite(scheme_performance: pd.DataFrame) -> pd.DataFrame:
    appetite_map = {
        "Low": ["Low"],
        "Moderate": ["Moderate", "Moderately High"],
        "High": ["High", "Very High"],
    }

    tables: list[pd.DataFrame] = []
    for appetite, grades in appetite_map.items():
        subset = (
            scheme_performance.loc[scheme_performance["risk_grade"].isin(grades)]
            .sort_values(["sharpe_ratio", "aum_crore"], ascending=[False, False])
            .head(3)
            .copy()
        )
        subset.insert(0, "risk_appetite", appetite)
        tables.append(
            subset[
                [
                    "risk_appetite",
                    "amfi_code",
                    "scheme_name",
                    "fund_house",
                    "risk_grade",
                    "sharpe_ratio",
                    "return_3yr_pct",
                    "aum_crore",
                ]
            ]
        )

    return pd.concat(tables, ignore_index=True)


def table_block(dataframe: pd.DataFrame, rows: int = 10) -> str:
    return "```text\n" + dataframe.head(rows).to_string(index=False) + "\n```"


def format_currency(value: float) -> str:
    return f"INR {value:,.0f}"


def build_insights(
    var_cvar: pd.DataFrame,
    cohorts: pd.DataFrame,
    sip_summary: dict[str, float],
    hhi: pd.DataFrame,
    recommender_table: pd.DataFrame,
) -> list[str]:
    worst_var = var_cvar.iloc[0]
    worst_cvar = var_cvar.sort_values("cvar_95").iloc[0]
    top_cohort = cohorts.sort_values("total_invested_inr", ascending=False).iloc[0]
    top_sip_cohort = cohorts.sort_values("avg_sip_amount_inr", ascending=False).iloc[0]
    concentrated = hhi.iloc[0]
    best_low = recommender_table.loc[recommender_table["risk_appetite"] == "Low"].iloc[0]

    return [
        (
            f"Funds with the deepest left-tail risk were led by **{worst_var['scheme_name']}**, "
            f"whose 95% one-day VaR reached **{worst_var['var_95_pct']:.2f}%**, while "
            f"**{worst_cvar['scheme_name']}** had the weakest conditional tail outcome at "
            f"**{worst_cvar['cvar_95_pct']:.2f}%**."
        ),
        (
            f"The most valuable investor vintage was cohort **{int(top_cohort['cohort_year'])}**, "
            f"with total invested volume of **{format_currency(top_cohort['total_invested_inr'])}** "
            f"and a top fund preference for **{top_cohort['top_fund_preference']}**."
        ),
        (
            f"Cohort **{int(top_sip_cohort['cohort_year'])}** posted the highest average SIP size at "
            f"**{format_currency(top_sip_cohort['avg_sip_amount_inr'])}**, suggesting newer or more affluent "
            f"investors are committing larger periodic tickets."
        ),
        (
            f"SIP continuity remained healthy for **{sip_summary['continuity_rate']:.1%}** of investors with "
            f"at least {MIN_SIP_TRANSACTIONS} SIPs, leaving **{sip_summary['at_risk_investors']}** investors flagged "
            f"as at-risk because their average gap exceeded {SIP_AT_RISK_DAYS} days."
        ),
        (
            f"The most concentrated disclosed equity portfolio was **{concentrated['scheme_name']}** with an "
            f"HHI of **{concentrated['hhi']:.3f}**, whereas the low-risk recommendation leader remained "
            f"**{best_low['scheme_name']}** on Sharpe ratio within the mapped appetite bucket."
        ),
    ]


def build_notebook(
    var_cvar: pd.DataFrame,
    key_funds: pd.DataFrame,
    cohorts: pd.DataFrame,
    sip_continuity: pd.DataFrame,
    sip_summary: dict[str, float],
    hhi: pd.DataFrame,
    recommender_table: pd.DataFrame,
) -> None:
    notebook = nbformat.v4.new_notebook()

    key_fund_names = key_funds["scheme_name"].drop_duplicates().tolist()
    insights = build_insights(var_cvar, cohorts, sip_summary, hhi, recommender_table)

    notebook.cells = [
        nbformat.v4.new_markdown_cell(
            "# Advanced Analytics\n"
            "This notebook consolidates tail-risk, rolling risk-adjusted return, investor behavior, "
            "SIP continuity, portfolio concentration, and recommendation outputs for the 40 mutual fund schemes."
        ),
        nbformat.v4.new_markdown_cell(
            "## Methodology\n"
            "- Historical VaR (95%) uses the 5th percentile of daily returns by fund.\n"
            "- CVaR (95%) uses the mean of daily returns that fall at or below the VaR threshold.\n"
            "- Rolling Sharpe ratio uses `returns.rolling(90).mean() / returns.rolling(90).std() * sqrt(252)`.\n"
            f"- The 5 key funds in the chart are the top {KEY_FUND_COUNT} schemes by AUM, with Sharpe ratio as a tiebreaker.\n"
            f"- SIP continuity flags investors as at-risk when average SIP gaps exceed {SIP_AT_RISK_DAYS} days after at least {MIN_SIP_TRANSACTIONS} SIP transactions.\n"
            "- HHI is calculated as the sum of squared portfolio weights in decimal form for disclosed equity holdings."
        ),
        nbformat.v4.new_markdown_cell(
            "## Advanced Insights\n"
            + "\n".join(f"{idx}. {text}" for idx, text in enumerate(insights, start=1))
        ),
        nbformat.v4.new_markdown_cell(
            "## VaR and CVaR Leaders\n"
            + table_block(
                var_cvar.assign(
                    var_95_pct=lambda df: df["var_95_pct"].round(2),
                    cvar_95_pct=lambda df: df["cvar_95_pct"].round(2),
                    sharpe_ratio=lambda df: df["sharpe_ratio"].round(2),
                )[
                    [
                        "scheme_name",
                        "risk_grade",
                        "sharpe_ratio",
                        "var_95_pct",
                        "cvar_95_pct",
                        "return_observations",
                    ]
                ],
                rows=12,
            )
        ),
        nbformat.v4.new_markdown_cell(
            "## Rolling 90-Day Sharpe Coverage\n"
            f"Tracked key funds: **{', '.join(key_fund_names)}**.\n\n"
            "The time-series plot is exported to `rolling_sharpe_chart.png` for direct use in the report deck or dashboard."
        ),
        nbformat.v4.new_markdown_cell(
            "## Investor Cohort Summary\n"
            + table_block(
                cohorts.assign(
                    avg_sip_amount_inr=lambda df: df["avg_sip_amount_inr"].round(0),
                    total_invested_inr=lambda df: df["total_invested_inr"].round(0),
                    top_fund_invested_inr=lambda df: df["top_fund_invested_inr"].round(0),
                )[
                    [
                        "cohort_year",
                        "investor_count",
                        "avg_sip_amount_inr",
                        "total_invested_inr",
                        "top_fund_preference",
                        "top_fund_invested_inr",
                    ]
                ],
                rows=10,
            )
        ),
        nbformat.v4.new_markdown_cell(
            "## SIP Continuity Summary\n"
            f"- Eligible investors: **{sip_summary['eligible_investors']}**\n"
            f"- At-risk investors: **{sip_summary['at_risk_investors']}**\n"
            f"- Continuity rate: **{sip_summary['continuity_rate']:.1%}**\n"
            f"- Average gap across eligible investors: **{sip_summary['avg_gap_days_overall']:.1f} days**\n\n"
            + table_block(
                sip_continuity.assign(
                    avg_gap_days=lambda df: df["avg_gap_days"].round(1),
                    median_gap_days=lambda df: df["median_gap_days"].round(1),
                )[
                    [
                        "investor_id",
                        "sip_transactions",
                        "avg_gap_days",
                        "median_gap_days",
                        "continuity_status",
                        "latest_sip_date",
                    ]
                ],
                rows=12,
            )
        ),
        nbformat.v4.new_markdown_cell(
            "## Equity Portfolio Concentration (HHI)\n"
            + table_block(
                hhi.assign(
                    hhi=lambda df: df["hhi"].round(3),
                    top_holding_weight_pct=lambda df: df["top_holding_weight_pct"].round(2),
                )[
                    [
                        "scheme_name",
                        "risk_grade",
                        "hhi",
                        "concentration_label",
                        "holdings_count",
                        "top_sector",
                        "top_holding_weight_pct",
                    ]
                ],
                rows=12,
            )
        ),
        nbformat.v4.new_markdown_cell(
            "## Recommendation Snapshot\n"
            + table_block(
                recommender_table.assign(
                    sharpe_ratio=lambda df: df["sharpe_ratio"].round(2),
                    return_3yr_pct=lambda df: df["return_3yr_pct"].round(2),
                ),
                rows=9,
            )
        ),
    ]

    nbformat.write(notebook, NOTEBOOK_PATH)


def main() -> int:
    nav, scheme_performance, fund_master, transactions, holdings = load_inputs()
    nav_returns = compute_daily_returns(nav)
    var_cvar = compute_var_cvar(nav_returns, scheme_performance)
    rolling_sharpe = compute_rolling_sharpe(nav_returns)
    key_funds = select_key_funds(rolling_sharpe, scheme_performance)
    cohorts = compute_investor_cohorts(transactions, scheme_performance)
    sip_continuity, sip_summary = compute_sip_continuity(transactions)
    hhi = compute_hhi(holdings, scheme_performance, fund_master)
    recommender_table = top_funds_by_risk_appetite(scheme_performance)

    var_cvar.to_csv(VAR_CVAR_PATH, index=False)
    render_rolling_sharpe_chart(key_funds)
    build_notebook(
        var_cvar=var_cvar,
        key_funds=key_funds,
        cohorts=cohorts,
        sip_continuity=sip_continuity,
        sip_summary=sip_summary,
        hhi=hhi,
        recommender_table=recommender_table,
    )

    print(f"Wrote {VAR_CVAR_PATH.name}")
    print(f"Wrote {ROLLING_SHARPE_CHART_PATH.name}")
    print(f"Wrote {NOTEBOOK_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
