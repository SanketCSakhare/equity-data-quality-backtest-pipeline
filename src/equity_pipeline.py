"""Reproducible FTSE equity ingestion, quality checks and monthly momentum test."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/reference/security_master.csv"
OUT = ROOT / "data/processed"


def security_master() -> pd.DataFrame:
    master = pd.read_csv(MASTER, parse_dates=["isin_valid_from", "isin_valid_to"])
    assert master["ticker"].nunique() == 20
    assert not master.duplicated(["ticker", "isin_valid_from"]).any()
    return master


def fetch_prices(start: str, end: str, tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    import yfinance as yf

    rows: list[pd.DataFrame] = []
    failures = []
    for ticker in tickers:
        try:
            frame = yf.Ticker(ticker).history(
                start=start, end=end, interval="1d", auto_adjust=False,
                actions=True, repair=False,
            )
            if frame.empty:
                raise ValueError("empty history")
            frame = frame.reset_index().rename(columns={"Date": "trade_date"})
            frame["trade_date"] = pd.to_datetime(frame["trade_date"]).dt.tz_localize(None).dt.normalize()
            frame["ticker"] = ticker
            frame = frame.rename(columns={
                "Open": "open", "High": "high", "Low": "low", "Close": "close",
                "Adj Close": "adj_close", "Volume": "volume",
                "Dividends": "dividend", "Stock Splits": "split_ratio",
            })
            for column in ["open", "high", "low", "close", "adj_close", "volume", "dividend", "split_ratio"]:
                if column not in frame:
                    frame[column] = 0.0 if column in ("dividend", "split_ratio") else np.nan
            rows.append(frame[["trade_date", "ticker", "open", "high", "low", "close", "adj_close", "volume", "dividend", "split_ratio"]])
        except Exception as exc:
            failures.append({"ticker": ticker, "error": str(exc)})
    if not rows:
        raise RuntimeError(f"No ticker data downloaded: {failures}")
    return pd.concat(rows, ignore_index=True), pd.DataFrame(failures, columns=["ticker", "error"])


def attach_identifiers(prices: pd.DataFrame, master: pd.DataFrame) -> pd.DataFrame:
    merged = prices.merge(master, on="ticker", how="left")
    valid = (merged.trade_date >= merged.isin_valid_from) & (
        merged.isin_valid_to.isna() | (merged.trade_date <= merged.isin_valid_to)
    )
    merged = merged.loc[valid].copy()
    if len(merged) != len(prices):
        raise ValueError(f"Identifier coverage failed: {len(prices) - len(merged)} price rows unmapped or multiply mapped")
    if merged.duplicated(["ticker", "trade_date"]).any():
        raise ValueError("Identifier date ranges overlap")
    return merged.sort_values(["ticker", "trade_date"]).reset_index(drop=True)


def corporate_actions(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = prices.sort_values(["ticker", "trade_date"]).copy()
    # Yahoo's Close is normally split adjusted, but not cash-dividend adjusted.
    # Restore a pre-split nominal basis for illustration, using future split factors.
    factors = frame["split_ratio"].where(frame["split_ratio"] > 0, 1.0)
    frame["future_split_factor"] = factors.iloc[::-1].groupby(frame["ticker"].iloc[::-1]).cumprod().iloc[::-1] / factors
    frame["pre_split_nominal_close"] = frame["close"] * frame["future_split_factor"]
    frame["dividend_adjustment_factor"] = frame["adj_close"] / frame["close"]
    frame["raw_daily_return"] = frame.groupby("ticker")["close"].pct_change(fill_method=None)
    frame["adjusted_daily_return"] = frame.groupby("ticker")["adj_close"].pct_change(fill_method=None)
    actions = frame.loc[(frame.dividend.fillna(0) != 0) | (frame.split_ratio.fillna(0) != 0),
                        ["trade_date", "ticker", "isin", "dividend", "split_ratio", "close", "adj_close", "pre_split_nominal_close"]].copy()
    actions["action_type"] = np.where(actions.split_ratio.ne(0), "split", "dividend")
    return frame, actions


def quality_issues(prices: pd.DataFrame, expected_tickers: list[str]) -> pd.DataFrame:
    issues: list[dict] = []
    def add(ticker, day, issue, value=None, detail=""):
        issues.append({"ticker": ticker, "trade_date": day, "issue_type": issue, "value": value, "detail": detail})

    for row in prices.loc[prices.duplicated(["ticker", "trade_date"], keep=False)].itertuples():
        add(row.ticker, row.trade_date, "duplicate_row")
    for field in ["open", "high", "low", "close", "adj_close"]:
        for row in prices.loc[prices[field].isna() | (prices[field] <= 0)].itertuples():
            add(row.ticker, row.trade_date, "invalid_price", getattr(row, field), field)
    for ticker in expected_tickers:
        sample = prices.loc[prices.ticker.eq(ticker)].sort_values("trade_date")
        if sample.empty:
            add(ticker, pd.NaT, "missing_ticker", detail="No rows returned")
            continue
        # Peer-union dates approximate trading sessions; flag for review, not proof of error.
        peers = set(prices.loc[prices.trade_date.between(sample.trade_date.min(), sample.trade_date.max()), "trade_date"])
        for day in sorted(peers - set(sample.trade_date)):
            add(ticker, day, "missing_peer_day", detail="Peer-union calendar")
        clean = sample.drop_duplicates("trade_date", keep="first")
        for field, kind in [("close", "raw_jump_gt_20pct"), ("adj_close", "adjusted_jump_gt_20pct")]:
            change = clean[field].pct_change(fill_method=None)
            for row, val in zip(clean.loc[change.abs() > .20].itertuples(), change.loc[change.abs() > .20]):
                add(ticker, row.trade_date, kind, float(val), field)
    return pd.DataFrame(issues, columns=["ticker", "trade_date", "issue_type", "value", "detail"])


def backtest(prices: pd.DataFrame, top_n: int = 5) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    clean = prices.drop_duplicates(["ticker", "trade_date"]).copy()
    month_end = (clean.pivot(index="trade_date", columns="ticker", values="adj_close")
                 .resample("ME").last().dropna(how="all"))
    monthly_return = month_end.pct_change(fill_method=None)
    signal = month_end.pct_change(12, fill_method=None)
    records = []
    holdings = []
    for i in range(12, len(month_end) - 1):
        signal_date, hold_date = month_end.index[i], month_end.index[i + 1]
        eligible = signal.iloc[i].dropna().index
        if len(eligible) < top_n:
            continue
        winners = signal.iloc[i][eligible].nlargest(top_n).index.tolist()
        # A missing holding-period return is an incomplete month, not a reason
        # to select a different stock with information from the future.
        if monthly_return.iloc[i + 1][eligible].isna().any():
            continue
        selected_return = float(monthly_return.iloc[i + 1][winners].mean())
        benchmark_return = float(monthly_return.iloc[i + 1][eligible].mean())
        records.append({"signal_date": signal_date, "month": hold_date, "momentum_return": selected_return,
                        "benchmark_return": benchmark_return, "eligible_count": len(eligible)})
        holdings.extend({"signal_date": signal_date, "month": hold_date, "ticker": t,
                         "trailing_12m_return": float(signal.at[signal_date, t])} for t in winners)
    result = pd.DataFrame(records)
    if result.empty:
        raise ValueError("Insufficient history for a 12-month signal")
    for label in ["momentum", "benchmark"]:
        result[f"{label}_wealth"] = (1 + result[f"{label}_return"]).cumprod()
    metrics = []
    for label in ["momentum", "benchmark"]:
        wealth = result[f"{label}_wealth"]
        returns = result[f"{label}_return"]
        wealth_with_start = pd.concat([pd.Series([1.0]), wealth.reset_index(drop=True)], ignore_index=True)
        metrics.append({"strategy": label, "months": len(result),
                        "total_return": float(wealth.iloc[-1] - 1),
                        "annualized_return": float(wealth.iloc[-1] ** (12 / len(result)) - 1),
                        "annualized_volatility": float(returns.std(ddof=1) * np.sqrt(12)),
                        "max_drawdown": float((wealth_with_start / wealth_with_start.cummax() - 1).min())})
    return result, pd.DataFrame(holdings), pd.DataFrame(metrics)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help="Inclusive YYYY-MM-DD; default five years before end")
    parser.add_argument("--end", help="Exclusive YYYY-MM-DD; default tomorrow")
    args = parser.parse_args()
    end = pd.Timestamp(args.end or (date.today() + pd.Timedelta(days=1)).isoformat())
    start = pd.Timestamp(args.start) if args.start else end - pd.DateOffset(years=5)
    master = security_master()
    tickers = sorted(master.ticker.unique())
    raw, failures = fetch_prices(start.date().isoformat(), end.date().isoformat(), tickers)
    issues = quality_issues(raw, tickers)
    quality_summary = (issues.groupby("issue_type", dropna=False)
                       .agg(issue_count=("ticker", "size"), affected_tickers=("ticker", "nunique"))
                       .reset_index())
    mapped = attach_identifiers(raw, master)
    prices, actions = corporate_actions(mapped)
    performance, holdings, metrics = backtest(prices)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, data in {"prices": prices, "corporate_actions": actions, "quality_issues": issues,
                       "quality_summary": quality_summary,
                       "backtest_monthly": performance, "backtest_holdings": holdings,
                       "backtest_metrics": metrics, "download_failures": failures}.items():
        data.to_csv(OUT / f"{name}.csv", index=False)
    (OUT / "run_manifest.json").write_text(json.dumps({"start": str(start.date()), "end_exclusive": str(end.date()),
        "tickers_requested": len(tickers), "tickers_downloaded": raw.ticker.nunique(), "price_rows": len(prices),
        "quality_issues": issues.issue_type.value_counts().to_dict(), "download_failures": failures.to_dict("records")}, indent=2))
    print((OUT / "run_manifest.json").read_text())
    print(metrics.to_string(index=False))


if __name__ == "__main__":
    main()
