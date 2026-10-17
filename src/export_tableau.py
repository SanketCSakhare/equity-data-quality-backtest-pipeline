"""Export a compact, public-facing Tableau data source from pipeline results."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUT = ROOT / "dashboard/tableau_public_data.csv"


def main():
    prices = pd.read_csv(DATA / "prices.csv", parse_dates=["trade_date"])
    issues = pd.read_csv(DATA / "quality_issues.csv")
    monthly = pd.read_csv(DATA / "backtest_monthly.csv", parse_dates=["month"])
    metrics = pd.read_csv(DATA / "backtest_metrics.csv")
    records = []

    # Monthly normalized price indices are analytical summaries, not vendor OHLC rows.
    for ticker, group in prices.groupby("ticker"):
        series = group.set_index("trade_date")["adj_close"].resample("ME").last().dropna()
        base = series.iloc[0]
        for day, value in series.items():
            records.append(("price_index", day.date().isoformat(), ticker, ticker,
                            "Adjusted price index", round(float(value / base * 100), 4), "index"))

    quality = {
        "Missing peer days": int(issues.issue_type.eq("missing_peer_day").sum()),
        "Raw jumps >20%": int(issues.issue_type.eq("raw_jump_gt_20pct").sum()),
        "Adjusted jumps >20%": int(issues.issue_type.eq("adjusted_jump_gt_20pct").sum()),
        "Duplicate / invalid": int(issues.issue_type.isin(["duplicate_row", "invalid_price"]).sum()),
    }
    for label, count in quality.items():
        records.append(("quality_count", "", label, "", "Quality flags", count, "count"))

    for row in monthly.itertuples():
        records.append(("wealth", row.month.date().isoformat(), "Top-five momentum", "",
                        "Growth of 1", round(float(row.momentum_wealth), 6), "index"))
        records.append(("wealth", row.month.date().isoformat(), "Equal-weight benchmark", "",
                        "Growth of 1", round(float(row.benchmark_wealth), 6), "index"))

    for row in metrics.itertuples():
        for field, label in [("total_return", "Total return"),
                             ("annualized_return", "Annualized return"),
                             ("annualized_volatility", "Annualized volatility"),
                             ("max_drawdown", "Maximum drawdown")]:
            records.append(("backtest_metric", "", "Top-five momentum" if row.strategy == "momentum" else "Equal-weight benchmark",
                            "", label, round(float(getattr(row, field)), 6), "fraction"))

    result = pd.DataFrame(records, columns=["panel", "date", "series", "ticker", "metric", "value", "unit"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUT, index=False)
    print(f"{len(result)} Tableau summary rows: {OUT}")


if __name__ == "__main__":
    main()

