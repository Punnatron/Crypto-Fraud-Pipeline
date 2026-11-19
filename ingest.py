
from pathlib import Path
import os
import sys

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# ============================================
# 1. PROJECT CONFIGURATION
# ============================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")

SCHEMA_NAME = "raw_data"

CSV_FILES = {
    "crypto_fraud_master.csv": "crypto_fraud_master",
    "transactions.csv": "transactions",
    "tokens.csv": "tokens",
    "wallets.csv": "wallets",
    "data_dictionary.csv": "data_dictionary",
}

EXPECTED_ROWS = {
    "crypto_fraud_master": 500_000,
    "transactions": 500_000,
    "tokens": 40,
    "wallets": 8_000,
    "data_dictionary": 31,
}

READ_CHUNK_SIZE = 25_000
INSERT_CHUNK_SIZE = 1_000


# ============================================
# 2. DATABASE CONNECTION
# ============================================

def create_db_engine():

    required = [
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]

    missing = [
        key for key in required
        if not os.getenv(key)
    ]

    if missing:
        raise ValueError(
            f"Missing environment variables: {missing}"
        )

    connection_url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB"),
    )

    return create_engine(
        connection_url,
        pool_pre_ping=True
    )


# ============================================
# 3. CREATE RAW DATA SCHEMA
# ============================================

def create_raw_schema(engine):

    with engine.begin() as connection:

        connection.execute(
            text(
                "CREATE SCHEMA IF NOT EXISTS raw_data"
            )
        )

    print("Schema raw_data created successfully")


# ============================================
# 4. INGEST CSV
# ============================================

def ingest_csv(engine, file_name, table_name):

    file_path = DATA_DIR / file_name

    if not file_path.is_file():
        raise FileNotFoundError(
            f"CSV not found: {file_path}"
        )

    print("\n" + "=" * 55)
    print(f"INGESTING: {file_name}")
    print("=" * 55)

    total_rows = 0
    first_chunk = True

    reader = pd.read_csv(
        file_path,
        chunksize=READ_CHUNK_SIZE,
        encoding="utf-8-sig",
        low_memory=False
    )

    # ใช้ Transaction ต่อหนึ่งตาราง
    # หากเกิด Error ระหว่างนำเข้าตารางนี้
    # จะ Rollback การเปลี่ยนแปลงของตารางนี้
    with engine.begin() as connection:

        for batch_number, df in enumerate(reader, start=1):

            mode = "replace" if first_chunk else "append"

            df.to_sql(
                name=table_name,
                con=connection,
                schema=SCHEMA_NAME,
                if_exists=mode,
                index=False,
                method="multi",
                chunksize=INSERT_CHUNK_SIZE
            )

            total_rows += len(df)
            first_chunk = False

            print(
                f"Batch {batch_number}: "
                f"{total_rows:,} rows loaded"
            )

    if first_chunk:
        raise ValueError(
            f"CSV contains no data rows: {file_name}"
        )

    # ตรวจสอบจำนวนแถวจริงใน PostgreSQL
    with engine.connect() as connection:

        actual_rows = connection.execute(
            text(
                f'SELECT COUNT(*) '
                f'FROM "{SCHEMA_NAME}"."{table_name}"'
            )
        ).scalar_one()

    expected = EXPECTED_ROWS[table_name]

    print("\nVerification:")
    print(f"Expected rows: {expected:,}")
    print(f"Actual rows:   {actual_rows:,}")

    if actual_rows == expected:
        print(f"PASS: {table_name}")
    else:
        print(
            f"WARNING: Expected {expected:,} "
            f"but found {actual_rows:,}"
        )

    return actual_rows


# ============================================
# 5. MAIN PIPELINE
# ============================================

def main():

    print("\n")
    print("=" * 55)
    print("CRYPTO FRAUD - DATA INGESTION")
    print("=" * 55)

    engine = None

    try:

        # ตรวจสอบไฟล์ CSV ทั้งหมดก่อนเริ่ม
        for file_name in CSV_FILES:

            file_path = DATA_DIR / file_name

            if not file_path.is_file():
                raise FileNotFoundError(
                    f"Missing Dataset: {file_path}"
                )

        print("\nAll CSV files found!")

        # เชื่อมต่อ Database
        engine = create_db_engine()

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("PostgreSQL connection successful!")

        # สร้าง Schema
        create_raw_schema(engine)

        # นำเข้าข้อมูลทุกไฟล์
        results = {}

        for file_name, table_name in CSV_FILES.items():

            results[table_name] = ingest_csv(
                engine,
                file_name,
                table_name
            )

        # สรุปผลทั้งหมด
        print("\n")
        print("=" * 55)
        print("INGESTION SUMMARY")
        print("=" * 55)

        total_rows = 0
        all_passed = True

        for table_name, actual_rows in results.items():

            expected = EXPECTED_ROWS[table_name]
            status = (
                "PASS" if actual_rows == expected
                else "CHECK"
            )

            print(
                f"{table_name:<25} "
                f"{actual_rows:>10,} "
                f"[{status}]"
            )

            total_rows += actual_rows

            if actual_rows != expected:
                all_passed = False

        print("-" * 55)
        print(f"TOTAL ROWS: {total_rows:,}")

        if all_passed:
            print("\nALL DATASETS INGESTED SUCCESSFULLY!")
        else:
            print("\nPLEASE CHECK ROW COUNTS!")

    except Exception as error:

        print("\nINGESTION FAILED!")
        print(f"Reason: {error}")

        sys.exit(1)

    finally:

        if engine is not None:
            engine.dispose()


# ============================================
# 6. PROGRAM ENTRY POINT
# ============================================

if __name__ == "__main__":
    main()
