"""Publish production aggregate tables from PostgreSQL to Google Sheets.

Run from the project root:
    python publish.py

Only the ten dashboard aggregate tables are published. The 500,000-row fact
 table remains in local PostgreSQL to avoid unnecessary spreadsheet size and
 performance costs.
"""

from pathlib import Path
import os
import sys

import gspread
import pandas as pd
from dotenv import load_dotenv
from gspread.exceptions import WorksheetNotFound
from gspread_dataframe import set_with_dataframe
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ---------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

CREDENTIALS_FILE = BASE_DIR / os.getenv(
    "GOOGLE_CREDENTIALS_FILE", "credentials.json"
)
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID", "").strip()

PRODUCTION_SCHEMA = "production"

# Publish only dashboard-ready aggregates; do not upload the 500k-row fact.
TABLES_TO_PUBLISH = [
    "agg_overview",
    "agg_manipulation_type",
    "agg_venue_type",
    "agg_token_risk",
    "agg_wallet_age",
    "agg_hourly_risk",
    "agg_daily_risk",
    "agg_behavior_by_label",
    "agg_price_volume_by_label",
    "agg_notional_by_label",
]

# The script only needs spreadsheet access because the spreadsheet is opened
# directly by ID and is shared with the service-account email by the user.
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


# ---------------------------------------------------------------------
# 2. POSTGRESQL CONNECTION
# ---------------------------------------------------------------------

def create_db_engine():
    required = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError(
            "Missing database environment variables in .env: "
            + ", ".join(missing)
        )

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB"),
    )
    return create_engine(connection_url, pool_pre_ping=True)


# ---------------------------------------------------------------------
# 3. GOOGLE SHEETS CONNECTION
# ---------------------------------------------------------------------

def create_google_client():
    if not CREDENTIALS_FILE.is_file():
        raise FileNotFoundError(
            f"Google credentials file not found: {CREDENTIALS_FILE}. "
            "Place credentials.json in the project root or set "
            "GOOGLE_CREDENTIALS_FILE in .env."
        )

    if not SPREADSHEET_ID:
        raise ValueError(
            "GOOGLE_SPREADSHEET_ID is missing from .env. "
            "Add the ID copied from the Google Sheets URL."
        )

    return gspread.service_account(
        filename=str(CREDENTIALS_FILE),
        scopes=GOOGLE_SCOPES,
    )


# ---------------------------------------------------------------------
# 4. PUBLISH ONE DATAFRAME
# ---------------------------------------------------------------------

def get_or_create_worksheet(spreadsheet, title, dataframe):
    try:
        worksheet = spreadsheet.worksheet(title)
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=title,
            rows=max(len(dataframe) + 1, 100),
            cols=max(len(dataframe.columns), 1),
        )
    return worksheet


def publish_table(engine, spreadsheet, table_name):
    query = text(
        f'SELECT * FROM "{PRODUCTION_SCHEMA}"."{table_name}"'
    )
    dataframe = pd.read_sql_query(query, engine)

    worksheet = get_or_create_worksheet(
        spreadsheet, table_name, dataframe
    )

    # Replace only this table's worksheet, leaving other spreadsheet tabs intact.
    worksheet.clear()
    set_with_dataframe(
        worksheet,
        dataframe,
        include_index=False,
        include_column_header=True,
        resize=True,
        allow_formulas=False,
    )

    print(
        f"Published {PRODUCTION_SCHEMA}.{table_name}: "
        f"{len(dataframe):,} rows, {len(dataframe.columns):,} columns"
    )
    return len(dataframe)


# ---------------------------------------------------------------------
# 5. MAIN PUBLICATION PIPELINE
# ---------------------------------------------------------------------

def main():
    print("\n" + "=" * 65)
    print("CRYPTO FRAUD - GOOGLE SHEETS PUBLICATION")
    print("=" * 65)

    engine = None
    try:
        engine = create_db_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("PostgreSQL connection successful!")

        # Fail early if an expected production table is missing.
        with engine.connect() as connection:
            existing_tables = set(
                connection.execute(
                    text(
                        """SELECT table_name
                           FROM information_schema.tables
                           WHERE table_schema = :schema"""
                    ),
                    {"schema": PRODUCTION_SCHEMA},
                ).scalars().all()
            )
        missing_tables = set(TABLES_TO_PUBLISH) - existing_tables
        if missing_tables:
            raise RuntimeError(
                "Missing production tables: " + ", ".join(sorted(missing_tables))
                + ". Run python transform.py first."
            )
        print("All 10 production aggregation tables found.")

        client = create_google_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        print(f"Google Sheets connection successful: {spreadsheet.title}")

        results = {}
        for table_name in TABLES_TO_PUBLISH:
            results[table_name] = publish_table(
                engine, spreadsheet, table_name
            )

        print("\n" + "=" * 65)
        print("PUBLICATION SUMMARY")
        print("=" * 65)
        for table_name, row_count in results.items():
            print(f"{table_name:<32} {row_count:>8,} rows")
        print("\nALL AGGREGATION TABLES PUBLISHED SUCCESSFULLY!")
        print(f"Spreadsheet: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")

    except Exception as error:
        print("\nPUBLICATION FAILED!")
        print(f"Reason: {error}")
        print(
            "Check that Google Sheets API is enabled, the spreadsheet is shared "
            "with the service-account email as Editor, and .env values are correct."
        )
        sys.exit(1)
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
