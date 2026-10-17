# One-page Power BI report

The pipeline writes the four CSVs below to `data/processed/`. Import them with **Get data → Text/CSV** in Power BI Desktop, then build one 16:9 page named **Equity data quality and momentum**. Set `trade_date`, `month` to Date and return/price columns to Decimal Number. The preview image in `dashboard/preview.png` shows the intended layout using the same run outputs; it is not a Power BI capture.

| Area | Visual | Dataset | Fields |
|---|---|---|---|
| Header | cards | `prices.csv`, `quality_issues.csv` | distinct ticker count, row count, issue count |
| Upper left | line chart | `prices.csv` | trade_date, adj_close, ticker slicer |
| Upper right | bar chart | `quality_issues.csv` | issue_type, issue count |
| Lower left | line chart | `backtest_monthly.csv` | month, momentum_wealth, benchmark_wealth |
| Lower right | table | `backtest_metrics.csv` | strategy, total_return, annualized_return, annualized_volatility, max_drawdown |
| Footer | table | `corporate_actions.csv` | date, ticker, action_type, dividend, split_ratio, close, adj_close |

Suggested measures:

```dax
Securities = DISTINCTCOUNT(prices[ticker])
Price rows = COUNTROWS(prices)
Quality issues = COUNTROWS(quality_issues)
Split events = CALCULATE(COUNTROWS(corporate_actions), corporate_actions[action_type] = "split")
Dividend events = CALCULATE(COUNTROWS(corporate_actions), corporate_actions[action_type] = "dividend")
```

Use a ticker slicer for the price chart and issue table. Keep the backtest measures unfiltered by ticker: they describe the fixed 20-name universe. Format returns as percentages and wealth as an index starting at 1. Add a text note: **Current-stock universe; no fees, slippage, or FX; Yahoo adjusted close; research example only.**

Power BI Desktop or a signed-in workspace is required to save a `.pbix` or `.pbip`. The CSVs and this layout are ready for that step.
