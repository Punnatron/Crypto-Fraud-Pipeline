"""Transform Kaggle crypto fraud data from raw_data to production.

Run from the project root:
    python transform.py

The script keeps raw_data unchanged, builds an enriched fact table, and
creates dashboard-ready aggregate tables in the production schema.
"""

from pathlib import Path
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ---------------------------------------------------------------------
# 1. PROJECT CONFIGURATION
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

RAW_SCHEMA = "raw_data"
PRODUCTION_SCHEMA = "production"

FACT_TABLE = "fact_crypto_transactions"
WRITE_CHUNK_SIZE = 500  # Keep multi-row INSERT below PostgreSQL parameter limits.

REQUIRED_RAW_TABLES = {
    "crypto_fraud_master",
    "transactions",
    "tokens",
    "wallets",
    "data_dictionary",
}

INTEGER_COLUMNS = [
    "token_is_major",
    "is_dex",
    "new_wallet_flag",
    "wallet_txn_count_total",
    "tx_burst_count_5m",
    "pair_txn_count",
    "hour_of_day",
    "is_night",
    "is_manipulative",
]

NUMERIC_COLUMNS = [
    "token_liquidity_score",
    "base_amount",
    "price_usd",
    "notional_usd",
    "log_notional",
    "gas_fee_usd",
    "wallet_age_days",
    "time_since_prev_tx_sec",
    "counterparty_diversity",
    "counterparty_reuse_ratio",
    "round_trip_score",
    "token_volume_zscore_1h",
    "price_deviation_vwap_pct",
    "notional_zscore_wallet",
]

TEXT_COLUMNS = [
    "tx_id",
    "wallet_from",
    "wallet_to",
    "token",
    "exchange",
    "venue_type",
    "manipulation_type",
]


# ---------------------------------------------------------------------
# 2. DATABASE CONNECTION AND SOURCE VALIDATION
# ---------------------------------------------------------------------

def create_db_engine():
    """Create a PostgreSQL connection using the project's .env file."""
    required = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"]
    missing = [name for name in required if not os.getenv(name)]

    if missing:
        raise ValueError(
            "Missing environment variables in .env: " + ", ".join(missing)
        )

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB"),
    )

    return create_engine(url, pool_pre_ping=True)


def validate_source_tables(engine):
    """Check required raw tables and key relationships before transforming."""
    with engine.connect() as conn:
        existing = set(
            conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = :schema
                    """
                ),
                {"schema": RAW_SCHEMA},
            ).scalars().all()
        )

        missing = REQUIRED_RAW_TABLES - existing
        if missing:
            raise RuntimeError(
                f"Missing tables in {RAW_SCHEMA}: {sorted(missing)}. "
                "Run python ingest.py first."
            )

        master_count = conn.execute(
            text(f'SELECT COUNT(*) FROM "{RAW_SCHEMA}"."crypto_fraud_master"')
        ).scalar_one()
        transaction_count = conn.execute(
            text(f'SELECT COUNT(*) FROM "{RAW_SCHEMA}"."transactions"')
        ).scalar_one()

        master_unique_ids = conn.execute(
            text(
                f'SELECT COUNT(DISTINCT tx_id) '
                f'FROM "{RAW_SCHEMA}"."crypto_fraud_master"'
            )
        ).scalar_one()
        transaction_unique_ids = conn.execute(
            text(
                f'SELECT COUNT(DISTINCT tx_id) '
                f'FROM "{RAW_SCHEMA}"."transactions"'
            )
        ).scalar_one()

        matched_ids = conn.execute(
            text(
                f'''SELECT COUNT(*)
                    FROM "{RAW_SCHEMA}"."crypto_fraud_master" m
                    INNER JOIN "{RAW_SCHEMA}"."transactions" t
                    ON m.tx_id = t.tx_id'''
            )
        ).scalar_one()

        token_duplicates = conn.execute(
            text(
                f'''SELECT COUNT(*) FROM (
                    SELECT token
                    FROM "{RAW_SCHEMA}"."tokens"
                    GROUP BY token
                    HAVING COUNT(*) > 1
                ) d'''
            )
        ).scalar_one()

        wallet_duplicates = conn.execute(
            text(
                f'''SELECT COUNT(*) FROM (
                    SELECT wallet
                    FROM "{RAW_SCHEMA}"."wallets"
                    GROUP BY wallet
                    HAVING COUNT(*) > 1
                ) d'''
            )
        ).scalar_one()

    print("\nSOURCE VALIDATION")
    print("-" * 55)
    print(f"crypto_fraud_master rows : {master_count:,}")
    print(f"transactions rows        : {transaction_count:,}")
    print(f"master unique tx_id      : {master_unique_ids:,}")
    print(f"transactions unique ids  : {transaction_unique_ids:,}")
    print(f"matched transaction IDs  : {matched_ids:,}")
    print(f"duplicate token keys     : {token_duplicates:,}")
    print(f"duplicate wallet keys    : {wallet_duplicates:,}")

    if master_count != master_unique_ids:
        raise ValueError("crypto_fraud_master contains duplicate tx_id values.")
    if transaction_count != transaction_unique_ids:
        raise ValueError("transactions contains duplicate tx_id values.")
    if master_count != transaction_count or matched_ids != master_count:
        raise ValueError(
            "transactions and crypto_fraud_master do not contain the same tx_id set."
        )
    if token_duplicates or wallet_duplicates:
        raise ValueError("Dimension tables contain duplicate join keys.")

    print("Source validation passed.")


def read_source_data(engine):
    """Read the detailed fact and its small lookup tables into DataFrames."""
    print("\nReading source tables into Pandas DataFrames...")

    master = pd.read_sql_query(
        text(f'SELECT * FROM "{RAW_SCHEMA}"."crypto_fraud_master"'), engine
    )
    tokens = pd.read_sql_query(
        text(f'SELECT * FROM "{RAW_SCHEMA}"."tokens"'), engine
    )
    wallets = pd.read_sql_query(
        text(f'SELECT * FROM "{RAW_SCHEMA}"."wallets"'), engine
    )

    print(f"Master DataFrame : {len(master):,} rows")
    print(f"Tokens DataFrame : {len(tokens):,} rows")
    print(f"Wallets DataFrame: {len(wallets):,} rows")

    return master, tokens, wallets


# ---------------------------------------------------------------------
# 3. CLEANING AND FEATURE ENGINEERING
# ---------------------------------------------------------------------

def clean_master_data(master):
    """Clean types and keys without silently inventing missing values."""
    df = master.copy()
    original_rows = len(df)

    # Normalize text whitespace and selected categorical values.
    for col in TEXT_COLUMNS:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    df["token"] = df["token"].str.upper()
    df["venue_type"] = df["venue_type"].str.upper()
    df["manipulation_type"] = df["manipulation_type"].str.lower()

    # Remove exact duplicate rows only. Conflicting duplicate transaction IDs
    # are rejected because selecting one would discard information arbitrarily.
    exact_duplicates = int(df.duplicated().sum())
    if exact_duplicates:
        df = df.drop_duplicates().copy()

    duplicate_ids = int(df["tx_id"].duplicated().sum())
    if duplicate_ids:
        raise ValueError(
            f"Found {duplicate_ids:,} duplicate tx_id values after removing "
            "exact duplicate rows. Please inspect raw_data before continuing."
        )

    # Convert timestamp and fail clearly if any timestamp cannot be parsed.
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    invalid_timestamps = int(df["timestamp"].isna().sum())
    if invalid_timestamps:
        raise ValueError(
            f"Found {invalid_timestamps:,} missing/invalid timestamps."
        )

    # Convert numeric fields. Do not impute values without a business rule.
    for col in NUMERIC_COLUMNS + INTEGER_COLUMNS:
        converted = pd.to_numeric(df[col], errors="coerce")
        invalid_numeric = int(converted.isna().sum())
        if invalid_numeric:
            raise ValueError(
                f"Column {col} has {invalid_numeric:,} missing or invalid numeric values."
            )
        df[col] = converted

    # Ensure required identifiers and labels are populated.
    required = [
        "tx_id", "timestamp", "wallet_from", "wallet_to", "token",
        "venue_type", "manipulation_type", "is_manipulative",
    ]
    missing_required = df[required].isna().sum()
    missing_required = missing_required[missing_required > 0]
    if not missing_required.empty:
        raise ValueError(
            "Missing required values: " + missing_required.to_dict().__str__()
        )

    # Integer fields should contain whole numbers.
    for col in INTEGER_COLUMNS:
        if not (df[col] % 1 == 0).all():
            raise ValueError(f"Column {col} contains non-integer values.")
        df[col] = df[col].astype("int64")

    # Validate binary flags.
    binary_columns = [
        "token_is_major", "is_dex", "new_wallet_flag", "is_night", "is_manipulative"
    ]
    for col in binary_columns:
        values = set(df[col].dropna().unique().tolist())
        if not values.issubset({0, 1}):
            raise ValueError(f"Column {col} contains values outside 0/1: {values}")

    # Verify the label relationship; do not silently relabel transactions.
    expected_flag = (df["manipulation_type"] != "none").astype("int64")
    label_mismatches = int((expected_flag != df["is_manipulative"]).sum())
    if label_mismatches:
        raise ValueError(
            f"Found {label_mismatches:,} rows where manipulation_type and "
            "is_manipulative disagree."
        )

    missing_total = int(df.isna().sum().sum())
    print("\nCLEANING SUMMARY")
    print("-" * 55)
    print(f"Rows before cleaning : {original_rows:,}")
    print(f"Exact duplicate rows  : {exact_duplicates:,}")
    print(f"Rows after cleaning  : {len(df):,}")
    print(f"Missing values        : {missing_total:,}")
    print("Timestamp converted   : datetime")
    print("Numeric fields checked: PASS")
    print("Label consistency     : PASS")

    return df


def enrich_with_dimensions(df, tokens, wallets):
    """Join token, sender-wallet, and receiver-wallet reference attributes."""
    fact = df.copy()

    token_dim = tokens.copy()
    token_dim["token"] = token_dim["token"].astype("string").str.strip().str.upper()
    token_dim = token_dim.rename(
        columns={
            "is_major": "token_ref_is_major",
            "base_price_usd": "token_base_price_usd",
            "daily_volatility": "token_daily_volatility",
            "liquidity_score": "token_reference_liquidity_score",
        }
    )
    token_dim = token_dim[
        [
            "token", "token_ref_is_major", "token_base_price_usd",
            "token_daily_volatility", "token_reference_liquidity_score",
        ]
    ]

    wallet_dim = wallets.copy()
    wallet_dim["wallet"] = wallet_dim["wallet"].astype("string").str.strip()

    sender_dim = wallet_dim.rename(
        columns={
            "wallet": "wallet_from",
            "wallet_type": "sender_wallet_type",
        }
    )[["wallet_from", "sender_wallet_type"]]

    receiver_dim = wallet_dim.rename(
        columns={
            "wallet": "wallet_to",
            "wallet_type": "receiver_wallet_type",
        }
    )[["wallet_to", "receiver_wallet_type"]]

    fact = fact.merge(
        token_dim, on="token", how="left", validate="many_to_one", indicator="_token_join"
    )
    token_unmatched = int((fact["_token_join"] != "both").sum())
    fact = fact.drop(columns="_token_join")

    fact = fact.merge(
        sender_dim, on="wallet_from", how="left", validate="many_to_one", indicator="_sender_join"
    )
    sender_unmatched = int((fact["_sender_join"] != "both").sum())
    fact = fact.drop(columns="_sender_join")

    fact = fact.merge(
        receiver_dim, on="wallet_to", how="left", validate="many_to_one", indicator="_receiver_join"
    )
    receiver_unmatched = int((fact["_receiver_join"] != "both").sum())
    fact = fact.drop(columns="_receiver_join")

    print("\nJOIN SUMMARY")
    print("-" * 55)
    print(f"Unmatched token keys   : {token_unmatched:,}")
    print(f"Unmatched sender wallets: {sender_unmatched:,}")
    print(f"Unmatched receiver wallets: {receiver_unmatched:,}")

    if token_unmatched or sender_unmatched or receiver_unmatched:
        raise ValueError(
            "Some fact rows did not match a dimension table. Check token/wallet keys."
        )

    return fact


def add_features(fact):
    """Add date/time and analysis-friendly categories while preserving source fields."""
    df = fact.copy()

    df["transaction_date"] = df["timestamp"].dt.date
    df["transaction_month"] = df["timestamp"].dt.strftime("%Y-%m")

    # Timestamp-derived values are kept separately from source hour_of_day/is_night.
    df["timestamp_hour"] = df["timestamp"].dt.hour.astype("int64")
    df["timestamp_is_night"] = (
        (df["timestamp_hour"] < 6) | (df["timestamp_hour"] >= 22)
    ).astype("int64")

    df["source_hour_mismatch"] = (
        df["hour_of_day"] != df["timestamp_hour"]
    ).astype("int64")
    df["source_night_mismatch"] = (
        df["is_night"] != df["timestamp_is_night"]
    ).astype("int64")

    df["wallet_age_group"] = pd.Series(
        pd.NA, index=df.index, dtype="string"
    )
    df.loc[df["wallet_age_days"] < 7, "wallet_age_group"] = "New (<7 days)"
    df.loc[df["wallet_age_days"] >= 7, "wallet_age_group"] = "Established (7+ days)"

    df["manipulation_label"] = df["is_manipulative"].map(
        {0: "Not Manipulative", 1: "Manipulative"}
    ).astype("string")

    return df


# ---------------------------------------------------------------------
# 4. AGGREGATIONS FOR BUSINESS QUESTIONS / DASHBOARD
# ---------------------------------------------------------------------

def add_rate_columns(frame, numerator_col, denominator_col, output_col):
    denominator = frame[denominator_col].replace(0, pd.NA)
    frame[output_col] = (frame[numerator_col] / denominator * 100).fillna(0).round(2)
    return frame


def build_aggregations(fact):
    """Build dashboard-ready summary tables from the enriched fact DataFrame."""
    total_rows = len(fact)
    total_flagged = int(fact["is_manipulative"].sum())

    overview = pd.DataFrame(
        [
            {
                "total_transactions": total_rows,
                "manipulative_transactions": total_flagged,
                "not_manipulative_transactions": total_rows - total_flagged,
                "manipulation_rate_pct": round(total_flagged / total_rows * 100, 2),
                "total_notional_usd": round(fact["notional_usd"].sum(), 2),
                "average_notional_usd": round(fact["notional_usd"].mean(), 2),
                "average_notional_flagged_usd": round(
                    fact.loc[fact["is_manipulative"] == 1, "notional_usd"].mean(), 2
                ),
                "average_notional_not_flagged_usd": round(
                    fact.loc[fact["is_manipulative"] == 0, "notional_usd"].mean(), 2
                ),
                "unique_sender_wallets": int(fact["wallet_from"].nunique()),
                "unique_receiver_wallets": int(fact["wallet_to"].nunique()),
                "unique_tokens": int(fact["token"].nunique()),
                "first_transaction_timestamp": fact["timestamp"].min(),
                "last_transaction_timestamp": fact["timestamp"].max(),
                "source_hour_mismatch_count": int(fact["source_hour_mismatch"].sum()),
                "source_night_mismatch_count": int(fact["source_night_mismatch"].sum()),
            }
        ]
    )

    manipulation = (
        fact.groupby("manipulation_type", dropna=False)
        .agg(
            transaction_count=("tx_id", "count"),
            flagged_transactions=("is_manipulative", "sum"),
            total_notional_usd=("notional_usd", "sum"),
            average_notional_usd=("notional_usd", "mean"),
        )
        .reset_index()
    )
    manipulation["share_of_all_transactions_pct"] = (
        manipulation["transaction_count"] / total_rows * 100
    ).round(2)
    manipulation["share_of_flagged_transactions_pct"] = (
        manipulation["flagged_transactions"] / total_flagged * 100
        if total_flagged else 0
    )
    manipulation["share_of_flagged_transactions_pct"] = (
        manipulation["share_of_flagged_transactions_pct"].round(2)
    )
    manipulation = add_rate_columns(
        manipulation, "flagged_transactions", "transaction_count", "flagged_rate_pct"
    )

    venue = (
        fact.groupby("venue_type", dropna=False)
        .agg(
            transaction_count=("tx_id", "count"),
            flagged_transactions=("is_manipulative", "sum"),
            total_notional_usd=("notional_usd", "sum"),
            average_notional_usd=("notional_usd", "mean"),
        )
        .reset_index()
    )
    venue = add_rate_columns(
        venue, "flagged_transactions", "transaction_count", "flagged_rate_pct"
    )

    token = (
        fact.groupby(
            [
                "token", "token_is_major", "token_base_price_usd",
                "token_daily_volatility", "token_reference_liquidity_score",
            ],
            dropna=False,
        )
        .agg(
            transaction_count=("tx_id", "count"),
            flagged_transactions=("is_manipulative", "sum"),
            total_notional_usd=("notional_usd", "sum"),
            average_notional_usd=("notional_usd", "mean"),
        )
        .reset_index()
        .sort_values("flagged_transactions", ascending=False)
    )
    token = add_rate_columns(
        token, "flagged_transactions", "transaction_count", "flagged_rate_pct"
    )

    wallet_age = (
        fact.groupby("wallet_age_group", dropna=False)
        .agg(
            transaction_count=("tx_id", "count"),
            flagged_transactions=("is_manipulative", "sum"),
            average_wallet_age_days=("wallet_age_days", "mean"),
            average_notional_usd=("notional_usd", "mean"),
        )
        .reset_index()
    )
    wallet_age = add_rate_columns(
        wallet_age, "flagged_transactions", "transaction_count", "flagged_rate_pct"
    )

    hourly = (
        fact.groupby("timestamp_hour")
        .agg(
            transaction_count=("tx_id", "count"),
            flagged_transactions=("is_manipulative", "sum"),
            total_notional_usd=("notional_usd", "sum"),
        )
        .reset_index()
        .sort_values("timestamp_hour")
    )
    hourly = add_rate_columns(
        hourly, "flagged_transactions", "transaction_count", "flagged_rate_pct"
    )

    daily = (
        fact.groupby("transaction_date")
        .agg(
            transaction_count=("tx_id", "count"),
            flagged_transactions=("is_manipulative", "sum"),
            total_notional_usd=("notional_usd", "sum"),
        )
        .reset_index()
        .sort_values("transaction_date")
    )
    daily = add_rate_columns(
        daily, "flagged_transactions", "transaction_count", "flagged_rate_pct"
    )

    behavior = (
        fact.groupby(["is_manipulative", "manipulation_label"])
        .agg(
            transaction_count=("tx_id", "count"),
            average_tx_burst_count_5m=("tx_burst_count_5m", "mean"),
            median_tx_burst_count_5m=("tx_burst_count_5m", "median"),
            average_counterparty_reuse_ratio=("counterparty_reuse_ratio", "mean"),
            median_counterparty_reuse_ratio=("counterparty_reuse_ratio", "median"),
            average_counterparty_diversity=("counterparty_diversity", "mean"),
            average_round_trip_score=("round_trip_score", "mean"),
        )
        .reset_index()
    )

    price_volume = (
        fact.groupby(["is_manipulative", "manipulation_label"])
        .agg(
            transaction_count=("tx_id", "count"),
            average_price_deviation_vwap_pct=("price_deviation_vwap_pct", "mean"),
            median_price_deviation_vwap_pct=("price_deviation_vwap_pct", "median"),
            average_token_volume_zscore_1h=("token_volume_zscore_1h", "mean"),
            median_token_volume_zscore_1h=("token_volume_zscore_1h", "median"),
            average_notional_zscore_wallet=("notional_zscore_wallet", "mean"),
        )
        .reset_index()
    )

    notional = (
        fact.groupby(["is_manipulative", "manipulation_label"])
        .agg(
            transaction_count=("tx_id", "count"),
            total_notional_usd=("notional_usd", "sum"),
            average_notional_usd=("notional_usd", "mean"),
            median_notional_usd=("notional_usd", "median"),
            maximum_notional_usd=("notional_usd", "max"),
        )
        .reset_index()
    )

    return {
        "agg_overview": overview,
        "agg_manipulation_type": manipulation,
        "agg_venue_type": venue,
        "agg_token_risk": token,
        "agg_wallet_age": wallet_age,
        "agg_hourly_risk": hourly,
        "agg_daily_risk": daily,
        "agg_behavior_by_label": behavior,
        "agg_price_volume_by_label": price_volume,
        "agg_notional_by_label": notional,
    }


# ---------------------------------------------------------------------
# 5. WRITE PRODUCTION TABLES AND VERIFY
# ---------------------------------------------------------------------

def write_table(engine, table_name, dataframe):
    """Replace a production table with the latest transformed result."""
    dataframe.to_sql(
        name=table_name,
        con=engine,
        schema=PRODUCTION_SCHEMA,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=WRITE_CHUNK_SIZE,
    )
    print(f"Written production.{table_name}: {len(dataframe):,} rows")


def write_production_tables(engine, fact, aggregates):
    with engine.begin() as conn:
        conn.execute(
            text(f'CREATE SCHEMA IF NOT EXISTS "{PRODUCTION_SCHEMA}"')
        )

    write_table(engine, FACT_TABLE, fact)

    # Add a primary key and indexes useful for common dashboard filters.
    with engine.begin() as conn:
        conn.execute(
            text(
                f'''ALTER TABLE "{PRODUCTION_SCHEMA}"."{FACT_TABLE}"
                    ADD CONSTRAINT pk_fact_crypto_transactions PRIMARY KEY (tx_id)'''
            )
        )
        conn.execute(
            text(
                f'''CREATE INDEX IF NOT EXISTS idx_fact_crypto_timestamp
                    ON "{PRODUCTION_SCHEMA}"."{FACT_TABLE}" (timestamp)'''
            )
        )
        conn.execute(
            text(
                f'''CREATE INDEX IF NOT EXISTS idx_fact_crypto_token
                    ON "{PRODUCTION_SCHEMA}"."{FACT_TABLE}" (token)'''
            )
        )

    for table_name, dataframe in aggregates.items():
        write_table(engine, table_name, dataframe)


def verify_production_tables(engine):
    table_names = [FACT_TABLE]
    table_names.extend(
        [
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
    )

    print("\nPRODUCTION VERIFICATION")
    print("-" * 55)
    with engine.connect() as conn:
        for table_name in table_names:
            count = conn.execute(
                text(
                    f'SELECT COUNT(*) FROM "{PRODUCTION_SCHEMA}"."{table_name}"'
                )
            ).scalar_one()
            print(f"production.{table_name:<30} {count:>10,} rows")


# ---------------------------------------------------------------------
# 6. MAIN
# ---------------------------------------------------------------------

def main():
    print("\n" + "=" * 65)
    print("CRYPTO FRAUD - DATA TRANSFORMATION")
    print("=" * 65)

    engine = None
    try:
        engine = create_db_engine()

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("PostgreSQL connection successful!")

        validate_source_tables(engine)
        master, tokens, wallets = read_source_data(engine)

        cleaned = clean_master_data(master)
        enriched = enrich_with_dimensions(cleaned, tokens, wallets)
        fact = add_features(enriched)

        mismatch_hour = int(fact["source_hour_mismatch"].sum())
        mismatch_night = int(fact["source_night_mismatch"].sum())
        print("\nFEATURE ENGINEERING")
        print("-" * 55)
        print("Created: transaction_date, transaction_month")
        print("Created: timestamp_hour, timestamp_is_night")
        print("Created: wallet_age_group, manipulation_label")
        print(f"Source hour mismatches flagged: {mismatch_hour:,}")
        print(f"Source night mismatches flagged: {mismatch_night:,}")

        aggregates = build_aggregations(fact)
        print(f"\nCreated {len(aggregates)} aggregation tables in Pandas.")

        write_production_tables(engine, fact, aggregates)
        verify_production_tables(engine)

        print("\n" + "=" * 65)
        print("TRANSFORMATION COMPLETED SUCCESSFULLY!")
        print("=" * 65)

    except Exception as error:
        print("\nTRANSFORMATION FAILED!")
        print(f"Reason: {error}")
        sys.exit(1)

    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
