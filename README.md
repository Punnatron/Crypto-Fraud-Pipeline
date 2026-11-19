
# Crypto Fraud & Market Manipulation Analytics

An Automated Data Engineering and Business Intelligence Project for analyzing cryptocurrency transaction patterns, detecting simulated market manipulation behavior, and visualizing insights through Looker Studio.

## 1. Project Overview

This project develops an end-to-end Automated Data Pipeline using a Kaggle cryptocurrency fraud dataset.

The system extracts raw CSV files, loads them into a local PostgreSQL database, performs data cleaning and transformation with Python and Pandas, publishes aggregated analytical datasets to Google Sheets, and presents insights through an interactive Looker Studio dashboard.

**Important:** The selected dataset contains simulated data for educational and analytical purposes. It does not represent verified real-world cryptocurrency exchange transactions or actual fraud incidents.

## 2. Project Objectives

- Build an automated data ingestion pipeline.
- Store raw datasets in PostgreSQL using Docker.
- Perform data cleaning and transformation with Pandas.
- Create analytical features and aggregated datasets.
- Publish processed data to Google Sheets.
- Develop an interactive BI dashboard.
- Automate the complete pipeline using a single Python command.

## 3. Dataset Description

Main dataset: `crypto_fraud_master.csv`

The project uses five CSV files:

| Dataset | Rows | Description |
|---|---:|---|
| crypto_fraud_master.csv | 500,000 | Main transaction dataset |
| transactions.csv | 500,000 | Basic transaction records |
| tokens.csv | 40 | Cryptocurrency token information |
| wallets.csv | 8,000 | Wallet information |
| data_dictionary.csv | 31 | Column definitions |

Total raw table rows: 1,008,071.

Note: `crypto_fraud_master.csv` and `transactions.csv` contain matching transaction IDs. They are not treated as separate sets of unique transactions.

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.14 | Pipeline development |
| Pandas | Data cleaning and transformation |
| SQLAlchemy | Database connectivity |
| PostgreSQL 16 | Relational database |
| Docker Compose | Database container management |
| gspread | Google Sheets API integration |
| gspread-dataframe | DataFrame publication |
| Google Sheets | Cloud staging |
| Looker Studio | Data visualization |
| Git & GitHub | Version control |

## 5. System Architecture

```text
Kaggle Dataset (CSV)
        |
        v
    ingest.py
        |
        v
PostgreSQL - raw_data
        |
        v
   transform.py
        |
        v
PostgreSQL - production
        |
        v
    publish.py
        |
        v
    Google Sheets
        |
        v
   Looker Studio
        |
        v
 Interactive Dashboard

run_pipeline.py
Orchestrates all pipeline stages.
```

## 6. Database Structure

Database: `crypto_fraud_db`

### Raw Schema

- crypto_fraud_master
- transactions
- tokens
- wallets
- data_dictionary

### Production Schema

Main fact table:

- fact_crypto_transactions

Aggregation tables:

- agg_overview
- agg_manipulation_type
- agg_venue_type
- agg_token_risk
- agg_wallet_age
- agg_hourly_risk
- agg_daily_risk
- agg_behavior_by_label
- agg_price_volume_by_label
- agg_notional_by_label

## 7. Data Transformation

The transformation process includes:

1. Source validation and record matching.
2. Duplicate and missing-value checks.
3. Timestamp and numeric data type validation.
4. Joining transaction records with token and wallet information.
5. Feature engineering, including:
   - transaction_date
   - transaction_month
   - timestamp_hour
   - timestamp_is_night
   - wallet_age_group
   - manipulation_label
6. Aggregation for business analysis.
7. Loading processed data into the production schema.

## 8. Business Questions

The analysis addresses the following questions:

1. What proportion of transactions are labeled as market manipulation?
2. How do wash trade, pump and dump, and ramping categories differ?
3. Do CEX and DEX transactions have different manipulation rates?
4. How do manipulation rates vary across cryptocurrency tokens?
5. Are new wallets more frequently labeled as manipulative?
6. Does transaction value differ between labeled groups?
7. Are transaction bursts and counterparty reuse associated with manipulation labels?
8. How does manipulation activity vary by hour?
9. Do price deviation and trading volume deviation differ between the two groups?

## 9. Dashboard

The Looker Studio dashboard contains:

- 4 KPI scorecards
- 11 analytical charts
- 3 analytical sections/pages

Dashboard link:

https://lookerstudio.google.com/

Google Sheets:

https://docs.google.com/spreadsheets/d/1Rk0GB6KOoJX2yWt3iD2_n5RSEVA9pK1RyUymkcZydjE/edit

## 10. Project Structure

```text
Crypto-Fraud-Pipeline/
|
|-- data/
|-- ingest.py
|-- transform.py
|-- publish.py
|-- run_pipeline.py
|-- docker-compose.yml
|-- requirements.txt
|-- .env.example
|-- .gitignore
|-- README.md
```

Sensitive credentials and local datasets are excluded from Git.

## 11. Installation and Setup

### Prerequisites

- Python 3.14
- Docker Desktop
- Git
- Google Cloud Project
- Google Sheets API
- Google Drive API

### Step 1: Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Crypto-Fraud-Pipeline
```

### Step 2: Prepare the dataset

Place all five CSV files inside the `data/` directory.

The dataset files are not included in this repository.

### Step 3: Create Python virtual environment

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 5: Configure environment variables

```powershell
Copy-Item .env.example .env
```

Edit `.env` and configure PostgreSQL and Google Sheets settings.

### Step 6: Configure Google Credentials

1. Enable Google Sheets API and Google Drive API.
2. Create a Google Cloud Service Account.
3. Generate a JSON service account key.
4. Store it locally as `credentials.json`.
5. Share the destination Google Spreadsheet with the Service Account email as Editor.

Never upload `credentials.json` or `.env` to GitHub.

### Step 7: Start PostgreSQL

```powershell
docker compose up -d
```

### Step 8: Execute the complete pipeline

```powershell
python run_pipeline.py
```

The pipeline executes the following stages:

1. Data Ingestion
2. Data Transformation
3. Google Sheets Publication

## 12. Execution Results

The pipeline was successfully executed in the development environment.

- 5 raw CSV tables loaded.
- 500,000 main transaction records processed.
- 10 aggregation tables created.
- 10 Google Sheets worksheets published.
- End-to-end pipeline execution completed successfully.

## 13. Security Notes

The following files must not be committed:

- `.env`
- `credentials.json`
- `.venv/`
- `.venv-1/`
- Raw CSV dataset files

Refer to `.gitignore` for the exclusion rules.

## 14. Project Limitations

- The dataset uses simulated data.
- The project is an educational analytics prototype.
- Manipulation labels are supplied by the dataset, not independently verified real-world fraud findings.
- The system does not execute real cryptocurrency trades or connect to a live exchange.

## 15. Contributors

- Member 1: Data Engineering and Infrastructure
- Member 2: Data Transformation and Analytics
- Member 3: Google Sheets Publication and Visualization

---

**Project:** Crypto Fraud & Market Manipulation Analytics

**Course:** Data Engineering / Business Intelligence Project
