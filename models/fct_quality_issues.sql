select ticker, to_date(trade_date) as trade_date, issue_type,
       try_to_double(value) as value, detail
from {{ source('raw', 'quality_issues') }}
