"""Generate advanced analytics outputs for the mutual fund project."""

from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
NOTEBOOK_PATH = PROJECT_ROOT / "Advanced_Analytics.ipynb"
VAR_CVAR_PATH = PROJECT_ROOT / "var_cvar_report.csv"
ROLLING_SHARPE_CHART_PATH = PROJECT_ROOT / "rolling_sharpe_chart.png"
RECOMMENDER_PATH = PROJECT_ROOT / "recommender.py"

TRADING_DAYS = 252
ROLLING_WINDOW = 90
KEY_FUND_COUNT = 5
MIN_SIP_TRANSACTIONS = 6
SIP_RISK_GAP_DAYS = 35

RISK_APPETITE_MAP = {
    "Low": ["Low"],
    "Moderate": ["Moderate", "Moderately High"],
    "High": ["High", "Very High"],
}


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load all processed datasets with light date parsing."""
    nav = pd.read_csv(PROCESSED_DIR / "nav_history.csv", parse_dates=["date"])
    scheme_performance = pd.read_csv(PROCESSED_DIR / "scheme_performance.csv")
    transactions = pd.read_csv(
        PROCESSED_DIR / "investor_transactions.csv",
        parse_dates=["transaction_date"],
    )
    holdings = pd.read_csv(PROCESSED_DIR / "portfolio_holdings.csv", parse_dates=["portfolio_date"])
    fund_master = pd.read_csv(PROCESSED_DIR / "fund_master.csv", parse_dates=["launch_date"])
    return nav, scheme_performance, transactions, holdings, fund_master


def compute_daily_returns(nav: pd.DataFrame) -> pd.DataFrame:
    """Compute daily NAV returns fund by fund."""
    nav_returns = nav.sort_values(["amfi_code", "date"]).copy()
    nav_returns["daily_return"] = nav_returns.groupby("amfi_code")["nav"].pct_change()
    return nav_returns


def compute_var_cvar(nav_returns: pd.DataFrame, scheme_performance: pd.DataFrame) -> pd.DataFrame:
    """Historical 95% VaR and CVaR for every scheme."""
    risk_summary = (
        nav_returns.dropna(subset=["daily_return"])
        .groupby("amfi_code")["daily_return"]
        .agg(
            VaR_95=lambda s: s.quantile(0.05),
            CVaR_95=lambda s: s[s <= s.quantile(0.05)].mean(),
        )
        .reset_index()
    )

    var_cvar = (
        scheme_performance[["amfi_code", "scheme_name"]]
        .drop_duplicates()
        .merge(risk_summary, on="amfi_code", how="left")
        .sort_values(["VaR_95", "CVaR_95", "scheme_name"], ascending=[True, True, True])
        .reset_index(drop=True)
    )
    return var_cvar


def compute_rolling_sharpe(nav_returns: pd.DataFrame) -> pd.DataFrame:
    """Compute 90-day rolling Sharpe ratio by scheme."""
    rolling = nav_returns.sort_values(["amfi_code", "date"]).copy()
    grouped = rolling.groupby("amfi_code")["daily_return"]
    rolling_mean = grouped.transform(lambda s: s.rolling(ROLLING_WINDOW).mean())
    rolling_std = grouped.transform(lambda s: s.rolling(ROLLING_WINDOW).std())
    rolling["rolling_sharpe"] = (rolling_mean / rolling_std) * np.sqrt(TRADING_DAYS)
    return rolling


def select_key_funds(
    rolling_sharpe: pd.DataFrame,
    scheme_performance: pd.DataFrame,
) -> pd.DataFrame:
    """Pick five key funds by AUM and plot-ready metadata."""
    key_codes = (
        scheme_performance.sort_values(["aum_crore", "sharpe_ratio"], ascending=[False, False])
        .head(KEY_FUND_COUNT)["amfi_code"]
        .tolist()
    )
    metadata = scheme_performance[["amfi_code", "scheme_name"]].drop_duplicates()
    key_funds = rolling_sharpe.loc[rolling_sharpe["amfi_code"].isin(key_codes)].merge(
        metadata,
        on="amfi_code",
        how="left",
    )
    return key_funds.sort_values(["scheme_name", "date"]).reset_index(drop=True)


def save_rolling_sharpe_chart(key_funds: pd.DataFrame) -> None:
    """Render rolling Sharpe line chart for five key funds."""
    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(14, 8))

    for scheme_name, fund_data in key_funds.groupby("scheme_name", sort=False):
        ax.plot(
            fund_data["date"],
            fund_data["rolling_sharpe"],
            linewidth=2,
            label=scheme_name,
        )

    ax.axhline(0, color="#666666", linestyle="--", linewidth=1)
    ax.set_title("Rolling 90-Day Sharpe Ratio")
    ax.set_xlabel("Date")
    ax.set_ylabel("Sharpe Ratio")
    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()
    fig.savefig(ROLLING_SHARPE_CHART_PATH, dpi=200, bbox_inches="tight")
    plt.close(fig)


def compute_cohort_analysis(
    transactions: pd.DataFrame,
    scheme_performance: pd.DataFrame,
) -> pd.DataFrame:
    """Build investor cohorts from each investor's first transaction year."""
    first_year = (
        transactions.groupby("investor_id")["transaction_date"]
        .min()
        .dt.year.rename("cohort_year")
    )
    cohort_data = transactions.merge(first_year, on="investor_id", how="left")
    invested_mask = cohort_data["transaction_type"].isin(["SIP", "Lumpsum"])

    avg_sip_amount = (
        cohort_data.loc[cohort_data["transaction_type"] == "SIP"]
        .groupby("cohort_year")["amount_inr"]
        .mean()
        .rename("avg_sip_amount")
    )
    total_invested = (
        cohort_data.loc[invested_mask]
        .groupby("cohort_year")["amount_inr"]
        .sum()
        .rename("total_invested")
    )
    investor_count = first_year.value_counts().rename_axis("cohort_year").rename("investor_count")

    top_fund = (
        cohort_data.loc[invested_mask]
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
        .set_index("cohort_year")["scheme_name"]
        .rename("top_fund")
    )

    cohort_summary = (
        pd.concat([avg_sip_amount, total_invested, investor_count, top_fund], axis=1)
        .reset_index()
        .sort_values("cohort_year")
        .reset_index(drop=True)
    )
    return cohort_summary


def compute_sip_continuity(transactions: pd.DataFrame) -> pd.DataFrame:
    """Assess SIP continuity based on average inter-transaction gap."""
    sip_transactions = transactions.loc[transactions["transaction_type"] == "SIP"].copy()
    sip_transactions = sip_transactions.sort_values(["investor_id", "transaction_date"])
    sip_transactions["gap_days"] = (
        sip_transactions.groupby("investor_id")["transaction_date"].diff().dt.days
    )

    eligible = sip_transactions.groupby("investor_id").filter(
        lambda frame: len(frame) >= MIN_SIP_TRANSACTIONS
    )
    sip_status = (
        eligible.groupby("investor_id")["gap_days"]
        .mean()
        .reset_index(name="avg_gap_days")
        .sort_values(["avg_gap_days", "investor_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
    sip_status["status"] = np.where(
        sip_status["avg_gap_days"] > SIP_RISK_GAP_DAYS,
        "at_risk",
        "healthy",
    )
    return sip_status


def compute_hhi(holdings: pd.DataFrame, fund_master: pd.DataFrame) -> pd.DataFrame:
    """Compute sector concentration using the portfolio HHI."""
    equity_funds = fund_master.loc[
        fund_master["category"].str.contains("equity", case=False, na=False),
        ["amfi_code", "scheme_name"],
    ].drop_duplicates()

    hhi = (
        holdings.merge(equity_funds, on="amfi_code", how="inner")
        .assign(weight_decimal=lambda df: df["weight_pct"] / 100)
        .groupby("scheme_name")["weight_decimal"]
        .apply(lambda s: np.square(s).sum())
        .reset_index(name="HHI")
        .sort_values(["HHI", "scheme_name"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return hhi


def compute_recommendations(
    scheme_performance: pd.DataFrame,
    risk_appetite: str,
) -> pd.DataFrame:
    """Return top 3 recommendations for a mapped risk appetite."""
    if risk_appetite not in RISK_APPETITE_MAP:
        valid = ", ".join(RISK_APPETITE_MAP)
        raise ValueError(f"Unsupported risk appetite '{risk_appetite}'. Choose one of: {valid}.")

    risk_grades = RISK_APPETITE_MAP[risk_appetite]
    recommendations = (
        scheme_performance.loc[scheme_performance["risk_grade"].isin(risk_grades)]
        .sort_values(["sharpe_ratio", "aum_crore"], ascending=[False, False])
        .head(3)
        .copy()
    )
    return recommendations[
        ["scheme_name", "risk_grade", "sharpe_ratio", "return_3yr_pct", "aum_crore"]
    ].reset_index(drop=True)


def build_insights(
    var_cvar: pd.DataFrame,
    cohorts: pd.DataFrame,
    sip_continuity: pd.DataFrame,
    hhi: pd.DataFrame,
    scheme_performance: pd.DataFrame,
) -> list[str]:
    """Prepare five notebook-ready insight statements."""
    highest_var = var_cvar.iloc[0]
    top_cohort = cohorts.sort_values("total_invested", ascending=False).iloc[0]
    sip_health_pct = (sip_continuity["status"] == "healthy").mean()
    most_diversified = hhi.sort_values("HHI", ascending=True).iloc[0]
    most_concentrated = hhi.iloc[0]
    best_sharpe = scheme_performance.sort_values(
        ["sharpe_ratio", "aum_crore"], ascending=[False, False]
    ).iloc[0]

    return [
        (
            f"Highest tail risk sits with **{highest_var['scheme_name']}**, where the 95% historical "
            f"VaR is **{highest_var['VaR_95']:.4f}** and the conditional loss measure CVaR is "
            f"**{highest_var['CVaR_95']:.4f}**."
        ),
        (
            f"Cohort **{int(top_cohort['cohort_year'])}** invests the most overall, contributing "
            f"**INR {top_cohort['total_invested']:,.0f}** with **{top_cohort['top_fund']}** as the top preference."
        ),
        (
            f"SIP continuity is healthy for **{sip_health_pct:.1%}** of investors who made at least "
            f"{MIN_SIP_TRANSACTIONS} SIPs, leaving the remainder flagged as at risk."
        ),
        (
            f"The most diversified equity fund is **{most_diversified['scheme_name']}** with HHI "
            f"**{most_diversified['HHI']:.3f}**, while **{most_concentrated['scheme_name']}** is the most "
            f"concentrated at **{most_concentrated['HHI']:.3f}**."
        ),
        (
            f"On risk-adjusted returns, **{best_sharpe['scheme_name']}** leads the universe with a "
            f"Sharpe ratio of **{best_sharpe['sharpe_ratio']:.2f}**."
        ),
    ]


def df_preview_code(name: str, rows: int = 10) -> str:
    return f"{name}.head({rows})"


def build_notebook(insights: list[str]) -> None:
    """Create a notebook with the required sections and executable cells."""
    notebook = nbformat.v4.new_notebook()

    imports_code = textwrap.dedent(
        """
        from pathlib import Path

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        import seaborn as sns

        sns.set_theme(style="whitegrid")

        PROJECT_ROOT = Path.cwd()
        PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
        TRADING_DAYS = 252
        ROLLING_WINDOW = 90
        KEY_FUND_COUNT = 5
        MIN_SIP_TRANSACTIONS = 6
        SIP_RISK_GAP_DAYS = 35

        RISK_APPETITE_MAP = {
            "Low": ["Low"],
            "Moderate": ["Moderate", "Moderately High"],
            "High": ["High", "Very High"],
        }
        """
    ).strip()

    loading_code = textwrap.dedent(
        """
        nav = pd.read_csv(PROCESSED_DIR / "nav_history.csv", parse_dates=["date"])
        scheme_performance = pd.read_csv(PROCESSED_DIR / "scheme_performance.csv")
        investor_transactions = pd.read_csv(
            PROCESSED_DIR / "investor_transactions.csv",
            parse_dates=["transaction_date"],
        )
        portfolio_holdings = pd.read_csv(
            PROCESSED_DIR / "portfolio_holdings.csv",
            parse_dates=["portfolio_date"],
        )
        fund_master = pd.read_csv(PROCESSED_DIR / "fund_master.csv", parse_dates=["launch_date"])

        nav.head()
        """
    ).strip()

    helpers_code = textwrap.dedent(
        """
        def compute_daily_returns(nav_df: pd.DataFrame) -> pd.DataFrame:
            nav_df = nav_df.sort_values(["amfi_code", "date"]).copy()
            nav_df["daily_return"] = nav_df.groupby("amfi_code")["nav"].pct_change()
            return nav_df


        def compute_var_cvar(nav_returns_df: pd.DataFrame, perf_df: pd.DataFrame) -> pd.DataFrame:
            risk_df = (
                nav_returns_df.dropna(subset=["daily_return"])
                .groupby("amfi_code")["daily_return"]
                .agg(
                    VaR_95=lambda s: s.quantile(0.05),
                    CVaR_95=lambda s: s[s <= s.quantile(0.05)].mean(),
                )
                .reset_index()
            )
            return (
                perf_df[["amfi_code", "scheme_name"]]
                .drop_duplicates()
                .merge(risk_df, on="amfi_code", how="left")
                .sort_values(["VaR_95", "CVaR_95", "scheme_name"], ascending=[True, True, True])
                .reset_index(drop=True)
            )


        def compute_rolling_sharpe(nav_returns_df: pd.DataFrame) -> pd.DataFrame:
            nav_returns_df = nav_returns_df.sort_values(["amfi_code", "date"]).copy()
            grouped = nav_returns_df.groupby("amfi_code")["daily_return"]
            rolling_mean = grouped.transform(lambda s: s.rolling(ROLLING_WINDOW).mean())
            rolling_std = grouped.transform(lambda s: s.rolling(ROLLING_WINDOW).std())
            nav_returns_df["rolling_sharpe"] = (rolling_mean / rolling_std) * np.sqrt(TRADING_DAYS)
            return nav_returns_df


        def select_key_funds(rolling_df: pd.DataFrame, perf_df: pd.DataFrame) -> pd.DataFrame:
            key_codes = (
                perf_df.sort_values(["aum_crore", "sharpe_ratio"], ascending=[False, False])
                .head(KEY_FUND_COUNT)["amfi_code"]
                .tolist()
            )
            meta = perf_df[["amfi_code", "scheme_name"]].drop_duplicates()
            return (
                rolling_df.loc[rolling_df["amfi_code"].isin(key_codes)]
                .merge(meta, on="amfi_code", how="left")
                .sort_values(["scheme_name", "date"])
                .reset_index(drop=True)
            )


        def compute_cohort_analysis(transactions_df: pd.DataFrame, perf_df: pd.DataFrame) -> pd.DataFrame:
            first_year = (
                transactions_df.groupby("investor_id")["transaction_date"]
                .min()
                .dt.year.rename("cohort_year")
            )
            cohort_df = transactions_df.merge(first_year, on="investor_id", how="left")
            invested_mask = cohort_df["transaction_type"].isin(["SIP", "Lumpsum"])

            avg_sip_amount = (
                cohort_df.loc[cohort_df["transaction_type"] == "SIP"]
                .groupby("cohort_year")["amount_inr"]
                .mean()
                .rename("avg_sip_amount")
            )
            total_invested = (
                cohort_df.loc[invested_mask]
                .groupby("cohort_year")["amount_inr"]
                .sum()
                .rename("total_invested")
            )
            investor_count = (
                first_year.value_counts().rename_axis("cohort_year").rename("investor_count")
            )
            top_fund = (
                cohort_df.loc[invested_mask]
                .groupby(["cohort_year", "amfi_code"])["amount_inr"]
                .sum()
                .reset_index()
                .sort_values(["cohort_year", "amount_inr", "amfi_code"], ascending=[True, False, True])
                .drop_duplicates("cohort_year")
                .merge(perf_df[["amfi_code", "scheme_name"]], on="amfi_code", how="left")
                .set_index("cohort_year")["scheme_name"]
                .rename("top_fund")
            )
            return (
                pd.concat([avg_sip_amount, total_invested, investor_count, top_fund], axis=1)
                .reset_index()
                .sort_values("cohort_year")
                .reset_index(drop=True)
            )


        def compute_sip_continuity(transactions_df: pd.DataFrame) -> pd.DataFrame:
            sip_df = transactions_df.loc[transactions_df["transaction_type"] == "SIP"].copy()
            sip_df = sip_df.sort_values(["investor_id", "transaction_date"])
            sip_df["gap_days"] = sip_df.groupby("investor_id")["transaction_date"].diff().dt.days
            eligible = sip_df.groupby("investor_id").filter(lambda frame: len(frame) >= MIN_SIP_TRANSACTIONS)
            status_df = (
                eligible.groupby("investor_id")["gap_days"]
                .mean()
                .reset_index(name="avg_gap_days")
                .sort_values(["avg_gap_days", "investor_id"], ascending=[False, True])
                .reset_index(drop=True)
            )
            status_df["status"] = np.where(status_df["avg_gap_days"] > SIP_RISK_GAP_DAYS, "at_risk", "healthy")
            return status_df


        def recommend_funds(risk_appetite: str, perf_df: pd.DataFrame) -> pd.DataFrame:
            risk_grades = RISK_APPETITE_MAP[risk_appetite]
            ranked = (
                perf_df.loc[perf_df["risk_grade"].isin(risk_grades)]
                .sort_values(["sharpe_ratio", "aum_crore"], ascending=[False, False])
                .head(3)
                .copy()
            )
            return ranked[["scheme_name", "risk_grade", "sharpe_ratio", "return_3yr_pct", "aum_crore"]]


        def compute_hhi(holdings_df: pd.DataFrame, master_df: pd.DataFrame) -> pd.DataFrame:
            equity_funds = master_df.loc[
                master_df["category"].str.contains("equity", case=False, na=False),
                ["amfi_code", "scheme_name"],
            ].drop_duplicates()
            return (
                holdings_df.merge(equity_funds, on="amfi_code", how="inner")
                .assign(weight_decimal=lambda df: df["weight_pct"] / 100)
                .groupby("scheme_name")["weight_decimal"]
                .apply(lambda s: np.square(s).sum())
                .reset_index(name="HHI")
                .sort_values(["HHI", "scheme_name"], ascending=[False, True])
                .reset_index(drop=True)
            )
        """
    ).strip()

    analysis_setup_code = textwrap.dedent(
        """
        nav_returns = compute_daily_returns(nav)
        var_cvar = compute_var_cvar(nav_returns, scheme_performance)
        rolling_sharpe = compute_rolling_sharpe(nav_returns)
        key_funds = select_key_funds(rolling_sharpe, scheme_performance)
        cohort_summary = compute_cohort_analysis(investor_transactions, scheme_performance)
        sip_continuity = compute_sip_continuity(investor_transactions)
        hhi_summary = compute_hhi(portfolio_holdings, fund_master)
        moderate_recommendations = recommend_funds("Moderate", scheme_performance)
        """
    ).strip()

    sharpe_plot_code = textwrap.dedent(
        """
        plt.figure(figsize=(14, 8))
        for scheme_name, fund_data in key_funds.groupby("scheme_name", sort=False):
            plt.plot(fund_data["date"], fund_data["rolling_sharpe"], linewidth=2, label=scheme_name)

        plt.axhline(0, color="#666666", linestyle="--", linewidth=1)
        plt.title("Rolling 90-Day Sharpe Ratio")
        plt.xlabel("Date")
        plt.ylabel("Sharpe Ratio")
        plt.legend(loc="best")
        plt.tight_layout()
        plt.show()
        """
    ).strip()

    notebook.cells = [
        nbformat.v4.new_markdown_cell("# Imports\nLoad the libraries used throughout the advanced analytics workflow."),
        nbformat.v4.new_code_cell(imports_code),
        nbformat.v4.new_markdown_cell("# Data Loading\nRead the processed mutual fund datasets and inspect the core NAV table."),
        nbformat.v4.new_code_cell(loading_code),
        nbformat.v4.new_markdown_cell(
            "# Helper Functions\nModular helper functions keep the analysis reusable, testable, and easier to maintain."
        ),
        nbformat.v4.new_code_cell(helpers_code),
        nbformat.v4.new_code_cell(analysis_setup_code),
        nbformat.v4.new_markdown_cell(
            "# VaR and CVaR Analysis\nHistorical VaR uses the 5th percentile of daily returns, while CVaR measures the average loss beyond that threshold."
        ),
        nbformat.v4.new_code_cell(df_preview_code("var_cvar", 10)),
        nbformat.v4.new_markdown_cell(
            "# Rolling Sharpe Analysis\nThe 90-day rolling Sharpe ratio shows how risk-adjusted returns evolve over time for five key funds."
        ),
        nbformat.v4.new_code_cell(sharpe_plot_code),
        nbformat.v4.new_markdown_cell(
            "# Cohort Analysis\nInvestors are grouped by their first transaction year to compare periodic commitment and cumulative invested amounts."
        ),
        nbformat.v4.new_code_cell(df_preview_code("cohort_summary", 10)),
        nbformat.v4.new_markdown_cell(
            "# SIP Continuity Analysis\nInvestors with at least six SIP transactions are flagged based on their average gap between installments."
        ),
        nbformat.v4.new_code_cell(df_preview_code("sip_continuity", 10)),
        nbformat.v4.new_markdown_cell(
            "# Recommender System\nFunds are mapped to risk appetite buckets and ranked by Sharpe ratio in descending order."
        ),
        nbformat.v4.new_code_cell('recommend_funds("Moderate", scheme_performance)'),
        nbformat.v4.new_markdown_cell(
            "# HHI Concentration\nPortfolio concentration is measured with the Herfindahl-Hirschman Index using disclosed holding weights."
        ),
        nbformat.v4.new_code_cell(df_preview_code("hhi_summary", 10)),
        nbformat.v4.new_markdown_cell(
            "# Advanced Insights\n" + "\n".join(f"{idx}. {insight}" for idx, insight in enumerate(insights, start=1))
        ),
    ]

    nbformat.write(notebook, NOTEBOOK_PATH)


def build_recommender_module() -> None:
    """Write the standalone recommender module requested in the deliverables."""
    recommender_code = textwrap.dedent(
        '''
        """Mutual fund recommender ranked by Sharpe ratio within a risk appetite bucket."""

        from __future__ import annotations

        from pathlib import Path

        import pandas as pd


        PROJECT_ROOT = Path(__file__).resolve().parent
        SCHEME_PERFORMANCE_PATH = PROJECT_ROOT / "data" / "processed" / "scheme_performance.csv"

        RISK_APPETITE_MAP = {
            "Low": ["Low"],
            "Moderate": ["Moderate", "Moderately High"],
            "High": ["High", "Very High"],
        }


        def recommend_funds(risk_appetite: str) -> pd.DataFrame:
            """Return the top 3 funds for a given risk appetite."""
            normalized = risk_appetite.strip().title()
            if normalized not in RISK_APPETITE_MAP:
                valid = ", ".join(RISK_APPETITE_MAP)
                raise ValueError(f"Unsupported risk appetite '{risk_appetite}'. Choose one of: {valid}.")

            scheme_performance = pd.read_csv(SCHEME_PERFORMANCE_PATH)
            recommendations = (
                scheme_performance.loc[
                    scheme_performance["risk_grade"].isin(RISK_APPETITE_MAP[normalized])
                ]
                .sort_values(["sharpe_ratio", "aum_crore"], ascending=[False, False])
                .head(3)
                .copy()
            )
            return recommendations[
                ["scheme_name", "risk_grade", "sharpe_ratio", "return_3yr_pct", "aum_crore"]
            ].reset_index(drop=True)
        '''
    ).strip() + "\n"
    RECOMMENDER_PATH.write_text(recommender_code, encoding="utf-8")


def main() -> int:
    nav, scheme_performance, transactions, holdings, fund_master = load_inputs()

    nav_returns = compute_daily_returns(nav)
    var_cvar = compute_var_cvar(nav_returns, scheme_performance)
    rolling_sharpe = compute_rolling_sharpe(nav_returns)
    key_funds = select_key_funds(rolling_sharpe, scheme_performance)
    cohorts = compute_cohort_analysis(transactions, scheme_performance)
    sip_continuity = compute_sip_continuity(transactions)
    hhi = compute_hhi(holdings, fund_master)
    insights = build_insights(var_cvar, cohorts, sip_continuity, hhi, scheme_performance)

    var_cvar.to_csv(VAR_CVAR_PATH, index=False)
    save_rolling_sharpe_chart(key_funds)
    build_recommender_module()
    build_notebook(insights)

    print(f"Wrote {VAR_CVAR_PATH.name}")
    print(f"Wrote {ROLLING_SHARPE_CHART_PATH.name}")
    print(f"Wrote {RECOMMENDER_PATH.name}")
    print(f"Wrote {NOTEBOOK_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
