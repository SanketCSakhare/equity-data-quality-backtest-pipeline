select to_date(trade_date) as trade_date, ticker, isin, action_type,
       try_to_double(dividend) as dividend,
       try_to_double(split_ratio) as split_ratio,
       try_to_double(close) as close,
       try_to_double(adj_close) as adj_close
from {{ source('raw', 'corporate_actions') }}
