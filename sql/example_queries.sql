-- Identifier coverage and price grain
select count(*) price_rows, count(distinct ticker) securities,
       count_if(isin is null) missing_isin
from EQUITY_RESEARCH.ANALYTICS.FCT_PRICES;

-- Quality issue report table
select issue_type, count(*) issue_count, count(distinct ticker) affected_tickers
from EQUITY_RESEARCH.ANALYTICS.FCT_QUALITY_ISSUES
group by 1 order by issue_count desc;

-- Dividend/split event and adjusted price context
select a.trade_date, a.ticker, a.action_type, a.dividend, a.split_ratio,
       p.close, p.adj_close, p.pre_split_nominal_close
from EQUITY_RESEARCH.ANALYTICS.FCT_CORPORATE_ACTIONS a
join EQUITY_RESEARCH.ANALYTICS.FCT_PRICES p
  on a.trade_date=p.trade_date and a.ticker=p.ticker
order by a.trade_date desc;
