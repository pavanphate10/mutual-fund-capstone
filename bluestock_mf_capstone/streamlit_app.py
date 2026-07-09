"""Alternative Streamlit dashboard for the mutual fund analytics project."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

try:
    import streamlit as st
except ImportError:  # pragma: no cover - runtime guard
    st = None

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"


def load_summary_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fund_master = pd.read_csv(PROCESSED_DIR / "fund_master.csv")
    scheme_performance = pd.read_csv(PROCESSED_DIR / "scheme_performance.csv")
    alpha_beta = pd.read_csv(REPORTS_DIR / "alpha_beta.csv")
    return fund_master, scheme_performance, alpha_beta


def run() -> None:
    if st is None:
        print("Install streamlit to launch the dashboard: pip install streamlit")
        return

    st.set_page_config(page_title="Bluestock MF Analytics", layout="wide")
    st.title("Bluestock Mutual Fund Analytics")
    st.caption("Interactive overview of processed mutual fund analytics data")

    fund_master, scheme_performance, alpha_beta = load_summary_data()

    with st.sidebar:
        st.header("Filters")
        fund_house = st.multiselect(
            "Fund house",
            sorted(set(fund_master["fund_house"].dropna().astype(str))),
            default=sorted(set(fund_master["fund_house"].dropna().astype(str)))[:5],
        )
        risk_grade = st.multiselect(
            "Risk grade",
            sorted(set(scheme_performance["risk_grade"].dropna().astype(str))),
            default=sorted(set(scheme_performance["risk_grade"].dropna().astype(str))),
        )
        min_sharpe = st.slider("Minimum Sharpe ratio", 0.0, 3.0, 0.0)

    filtered = scheme_performance.copy()
    if fund_house:
        filtered = filtered[filtered["fund_house"].astype(str).isin(fund_house)]
    if risk_grade:
        filtered = filtered[filtered["risk_grade"].astype(str).isin(risk_grade)]
    filtered = filtered[filtered["sharpe_ratio"] >= min_sharpe]

    col1, col2, col3 = st.columns(3)
    col1.metric("Funds", len(fund_master))
    col2.metric("Schemes", len(scheme_performance))
    col3.metric("Reports", len(list(REPORTS_DIR.glob("*.csv"))))

    st.subheader("Fund Overview")
    display_frame = filtered[["scheme_name", "fund_house", "risk_grade", "sharpe_ratio", "return_3yr_pct", "aum_crore"]].copy()
    display_frame = display_frame.sort_values(["sharpe_ratio", "return_3yr_pct"], ascending=[False, False]).head(20)
    st.dataframe(display_frame, use_container_width=True)

    st.subheader("Alpha and Beta Snapshot")
    alpha_view = alpha_beta[["scheme_name", "alpha_annual_pct", "beta"]].copy()
    alpha_view = alpha_view.sort_values("alpha_annual_pct", ascending=False).head(15)
    st.dataframe(alpha_view, use_container_width=True)

    st.subheader("Key Insights")
    st.write(
        f"Showing {len(display_frame)} schemes after applying the selected filters. "
        f"The strongest risk-adjusted performers are ranked by Sharpe ratio."
    )


if __name__ == "__main__":
    run()
