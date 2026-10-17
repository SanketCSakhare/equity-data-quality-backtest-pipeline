# Observed run: 17 October 2026

Data window: 18 October 2021 to 16 October 2026 (inclusive). Yahoo Finance via `yfinance`, 20 current London-listed large-cap names. `SHEL.L` begins on 31 January 2022 because the current Shell line starts then. The fixed universe is a present-day selection and therefore carries survivorship bias.

| Measure | Result |
|---|---:|
| Price rows | 25,158 |
| Tickers downloaded / requested | 20 / 20 |
| Dividend events | 249 |
| Split / consolidation events | 3 |
| Peer-calendar gaps for review | 10 |
| Duplicate ticker-date rows | 0 |
| Nonpositive / null prices | 0 |
| Adjusted one-day moves above 20% | 2 |

The two adjusted jumps were both `RR.L`: +23.68% on 23 February 2023 and +21.19% on 26 July 2023. They are review flags, not automatically errors. The 10 missing-peer-day flags also require an exchange-calendar or issuer-event review before remediation.

The event table includes the GSK 0.8-for-1 event on 19 July 2022, Anglo American's 0.880734 ratio on 2 June 2025, and Unilever's 8-for-9 consolidation on 9 December 2025. Anglo American's ISIN changes from `GB00B1XZS820` to `GB00BTK05J60` on 2 June 2025; Unilever's changes from `GB00B10RZP78` to `GB00BVZK7T90` on 9 December 2025. Yahoo `Close` is already split adjusted; `pre_split_nominal_close` reverses future split factors for illustration, and `Adj Close` additionally reflects cash distributions. A dividend does not have to cause a visible same-day price decline because market movement can offset it.

## Backtest, 48 holding months

| Strategy | Total return | Annualized return | Annualized volatility | Maximum drawdown |
|---|---:|---:|---:|---:|
| 12-month momentum, top five | 155.57% | 26.44% | 14.82% | -12.82% |
| Equal-weight available universe | 80.96% | 15.98% | 11.31% | -8.35% |

At each month end, the signal uses the preceding 12 month-end adjusted closes. The top five are held equally over the following month. The benchmark equally weights securities with a valid signal. Both series reinvest distributions through Yahoo adjusted close. Returns exclude dealing costs, spreads, tax, FX, and market impact. The fixed current universe, data vendor adjustments, and issuer transformations mean these numbers are illustrative rather than investable performance.

Snowflake and Power BI were not connected in this run. The Snowflake loader, dbt models, SQL, CSV exports and Power BI page specification are supplied in the repo, but no warehouse query or native Power BI report was executed.
