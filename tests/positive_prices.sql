select ticker, trade_date, close, adj_close
from {{ ref('fct_prices') }}
where close <= 0 or adj_close <= 0 or close is null or adj_close is null
