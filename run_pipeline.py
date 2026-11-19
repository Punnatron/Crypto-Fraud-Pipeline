"""Run the complete Crypto Fraud Analytics pipeline.

Execution order:
    1. ingest.py     - load CSV files into PostgreSQL raw_data schema
    2. transform.py  - clean, enrich, aggregate, and write production tables
    3. publish.py    - publish production aggregate tables to Google Sheets

Run from the project root:
    python run_pipeline.py

Prerequisites:
    - Docker Desktop is running.
    - PostgreSQL container is healthy (docker compose up -d).
    - The project's .venv is activated and requirements are installed.
    - .env and credentials.json are configured.
"""

from pathlib import Path
import subprocess
import sys
import time


BASE_DIR = Path(__file__).resolve().parent

PIPELINE_STEPS = [
    ("STEP 1/3 - DATA INGESTION", "ingest.py"),
    ("STEP 2/3 - DATA TRANSFORMATION", "transform.py"),
    ("STEP 3/3 - GOOGLE SHEETS PUBLICATION", "publish.py"),
]


def main() -> int:
    """Run each pipeline stage in order and stop if any stage fails."""
    print("\n" + "=" * 72, flush=True)
    print("CRYPTO FRAUD ANALYTICS - AUTOMATED DATA PIPELINE", flush=True)
    print("=" * 72, flush=True)
    print(f"Project directory : {BASE_DIR}", flush=True)
    print(f"Python interpreter: {sys.executable}", flush=True)

    # Check all scripts before starting, so a missing file does not cause
    # the pipeline to stop after an earlier stage has already run.
    missing_files = [
        script_name
        for _, script_name in PIPELINE_STEPS
        if not (BASE_DIR / script_name).is_file()
    ]

    if missing_files:
        print("\nPIPELINE CANNOT START.", flush=True)
        print("Missing required script(s):", flush=True)
        for name in missing_files:
            print(f"  - {name}", flush=True)
        return 1

    overall_start = time.perf_counter()

    for step_number, (step_title, script_name) in enumerate(PIPELINE_STEPS, start=1):
        script_path = BASE_DIR / script_name
        step_start = time.perf_counter()

        print("\n" + "=" * 72, flush=True)
        print(step_title, flush=True)
        print(f"Running: {script_name}", flush=True)
        print("=" * 72, flush=True)

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(BASE_DIR),
                check=False,
            )
        except OSError as exc:
            elapsed = time.perf_counter() - step_start
            print(f"\nCould not start {script_name}: {exc}", flush=True)
            print(f"Step duration: {elapsed:.1f} seconds", flush=True)
            return 1

        elapsed = time.perf_counter() - step_start

        if result.returncode != 0:
            print("\n" + "!" * 72, flush=True)
            print(f"PIPELINE STOPPED: {script_name} failed.", flush=True)
            print(f"Exit code: {result.returncode}", flush=True)
            print(f"Step duration: {elapsed:.1f} seconds", flush=True)
            print(
                "Fix the error above, then run python run_pipeline.py again.",
                flush=True,
            )
            return result.returncode or 1

        print(f"\n{script_name} completed successfully.", flush=True)
        print(f"Step duration: {elapsed:.1f} seconds", flush=True)

    total_elapsed = time.perf_counter() - overall_start

    print("\n" + "=" * 72, flush=True)
    print("ALL PIPELINE STAGES COMPLETED SUCCESSFULLY!", flush=True)
    print(f"Total pipeline duration: {total_elapsed:.1f} seconds", flush=True)
    print("=" * 72, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
