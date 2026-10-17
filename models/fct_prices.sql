select to_date(p.trade_date) as trade_date, p.ticker, p.isin,
       s.company_name, s.sector, s.currency,
       try_to_double(p."OPEN") as open_price, try_to_double(p.high) as high,
       try_to_double(p.low) as low, try_to_double(p.close) as close,
       try_to_double(p.adj_close) as adj_close, try_to_double(p.volume) as volume,
       try_to_double(p.pre_split_nominal_close) as pre_split_nominal_close,
       try_to_double(p.dividend_adjustment_factor) as dividend_adjustment_factor
from {{ source('raw', 'prices') }} p
join {{ ref('dim_security') }} s
  on p.ticker = s.ticker and p.isin = s.isin
 and to_date(p.trade_date) between s.isin_valid_from and coalesce(s.isin_valid_to, '9999-12-31'::date)
