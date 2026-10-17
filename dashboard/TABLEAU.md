# Tableau Public dashboard

[Open the published workbook](https://public.tableau.com/app/profile/sanket.chandrashekhar.sakhare/viz/EquityDataQualityandBacktestPipeline/Equitydashboard). The checked-in [screenshot](tableau_screenshot.png) was captured from its public page.

Use `tableau_public_data.csv` as a single data source in Tableau Public web authoring. It contains monthly **normalized adjusted price indices**, grouped quality counts, and backtest summaries. It does not include the vendor's daily OHLC rows.

Create four worksheets and place them on one dashboard titled **Equity data quality and momentum**:

| Worksheet | Filter `panel` to | Columns | Rows | Marks / detail |
|---|---|---|---|---|
| Adjusted price index | `price_index` | `date` (continuous month) | `SUM(value)` | Line; `ticker` on Color, ticker filter shown. Index starts at 100 for each ticker's first observed month. |
| Quality flags | `quality_count` | `series` | `SUM(value)` | Bar; show labels. |
| Growth of 1 | `wealth` | `date` (continuous month) | `SUM(value)` | Line; `series` on Color. |
| Backtest summary | `backtest_metric` | `series` | `metric` | Text marks using `SUM(value)`, formatted as percentage. |

The published dashboard uses a 1000 × 900 fixed canvas and a 2 × 2 layout: price index and growth above, quality flags and backtest metrics below. The workbook title is **Equity Data Quality and Backtest Pipeline**.

To update it, rerun the pipeline and `python src/export_tableau.py`, then replace the workbook's uploaded CSV in Tableau Public web authoring and publish the revised workbook. CSV-backed Tableau Public workbooks do not refresh automatically. Document the new run dates and results in the README.

The price index is normalized independently for each ticker. This allows comparison without disclosing raw daily vendor data, but its level is **not** a GBX share price. The universe is a current-stock sample, so the backtest has survivorship bias. Tableau Public makes published workbooks and their underlying data broadly accessible, so review the CSV before publishing.
