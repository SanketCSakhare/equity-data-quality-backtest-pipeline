"""Load CSV outputs into Snowflake using environment credentials; never stores secrets."""
import argparse
import csv
import os
from pathlib import Path

import snowflake.connector

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    "security_master": ROOT / "data/reference/security_master.csv",
    "prices": ROOT / "data/processed/prices.csv",
    "corporate_actions": ROOT / "data/processed/corporate_actions.csv",
    "quality_issues": ROOT / "data/processed/quality_issues.csv",
    "backtest_monthly": ROOT / "data/processed/backtest_monthly.csv",
    "backtest_metrics": ROOT / "data/processed/backtest_metrics.csv",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default="EQUITY_RESEARCH")
    parser.add_argument("--schema", default="RAW")
    args = parser.parse_args()
    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_WAREHOUSE"]
    missing = [x for x in required if not os.getenv(x)]
    if missing:
        raise SystemExit("Missing environment variables: " + ", ".join(missing))
    con = snowflake.connector.connect(account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        authenticator=os.getenv("SNOWFLAKE_AUTHENTICATOR", "externalbrowser"),
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"])
    try:
        with con.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS {args.database}")
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {args.database}.{args.schema}")
            cur.execute(f"CREATE FILE FORMAT IF NOT EXISTS {args.database}.{args.schema}.CSV_FORMAT TYPE=CSV SKIP_HEADER=1 FIELD_OPTIONALLY_ENCLOSED_BY='\"' EMPTY_FIELD_AS_NULL=TRUE")
            cur.execute(f"CREATE STAGE IF NOT EXISTS {args.database}.{args.schema}.CSV_STAGE FILE_FORMAT={args.database}.{args.schema}.CSV_FORMAT")
            for table, path in TABLES.items():
                if not path.exists():
                    raise FileNotFoundError(path)
                with path.open(newline="", encoding="utf-8-sig") as handle:
                    columns = next(csv.reader(handle))
                ddl = ", ".join(f'"{column.upper()}" VARCHAR' for column in columns)
                stage_path = f"@{args.database}.{args.schema}.CSV_STAGE/{table}"
                cur.execute(f"PUT file://{path.as_posix()} {stage_path} AUTO_COMPRESS=TRUE OVERWRITE=TRUE")
                cur.execute(f"CREATE OR REPLACE TABLE {args.database}.{args.schema}.{table.upper()} ({ddl})")
                cur.execute(f"COPY INTO {args.database}.{args.schema}.{table.upper()} FROM {stage_path} FILE_FORMAT=(FORMAT_NAME='{args.database}.{args.schema}.CSV_FORMAT')")
                cur.execute(f"SELECT COUNT(*) FROM {args.database}.{args.schema}.{table.upper()}")
                print(table, cur.fetchone()[0])
    finally:
        con.close()


if __name__ == "__main__":
    main()
