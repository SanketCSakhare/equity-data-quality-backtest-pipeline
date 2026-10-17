select ticker, lse_tidm, company_name, isin, sector, currency,
       to_date(isin_valid_from) as isin_valid_from,
       to_date(isin_valid_to) as isin_valid_to, lse_url
from {{ source('raw', 'security_master') }}
