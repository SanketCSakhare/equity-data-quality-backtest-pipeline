select ticker, trade_date, count(*) as row_count
from {{ ref('fct_prices') }}
group by 1, 2
having count(*) > 1
