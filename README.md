# Crypto Fraud & Market Manipulation Analytics

**An Automated Data Engineering and Business Intelligence Project**

An end-to-end data engineering pipeline for analyzing cryptocurrency transaction patterns, exploring simulated market manipulation behavior, and visualizing analytical insights through Looker Studio.

---

## 1. Project Overview

Crypto Fraud & Market Manipulation Analytics is an automated Data Engineering and Business Intelligence project developed to organize, process, and analyze cryptocurrency transaction data.

The project implements an end-to-end data pipeline that extracts raw CSV datasets, loads them into a PostgreSQL database, performs data cleaning and transformation using Python and Pandas, and publishes aggregated analytical datasets to Google Sheets.

The processed data is then connected to Looker Studio to create interactive dashboards for exploring transaction patterns, wallet behavior, token risk, and market-related trends.

**Important:** The selected dataset contains simulated data for educational and analytical purposes. It does not represent verified real-world cryptocurrency exchange transactions or actual fraud incidents.

## 2. Project Objectives

The main objectives are:

- Develop an automated data ingestion pipeline.
- Store raw datasets in PostgreSQL using Docker.
- Perform data cleaning and transformation with Python and Pandas.
- Create analytical features and aggregation tables.
- Publish processed analytical datasets to Google Sheets.
- Develop interactive Looker Studio dashboards.
- Automate the complete pipeline through a single Python command.

## 3. Dataset Description

The project uses a simulated cryptocurrency fraud dataset obtained from Kaggle.

A total of five CSV files are used:

| Dataset | Rows | Description |
|---|---:|---|
| `crypto_fraud_master.csv` | 500,000 | Main transaction dataset |
| `transactions.csv` | 500,000 | Basic transaction records |
| `tokens.csv` | 40 | Cryptocurrency token information |
| `wallets.csv` | 8,000 | Wallet information |
| `data_dictionary.csv` | 31 | Dataset column definitions |

**Total raw table rows:** 1,008,071

**Main dataset:** `crypto_fraud_master.csv`

**Note:** `crypto_fraud_master.csv` and `transactions.csv` contain matching transaction IDs. They are stored as separate source tables and are not treated as separate sets of unique transactions.

The dataset is used to explore transaction patterns and simulated market manipulation labels.

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.14 | Pipeline development and execution |
| Pandas | Data cleaning and transformation |
| SQLAlchemy | Database connectivity |
| PostgreSQL 16 | Relational database management |
| Docker Compose | Database container management |
| gspread | Google Sheets API integration |
| gspread-dataframe | Publishing Pandas DataFrames to Google Sheets |
| Google Sheets | Cloud-based analytical data staging |
| Looker Studio | Business intelligence and data visualization |
| Git & GitHub | Source code management and version control |

## 5. System Architecture

The project follows an end-to-end Data Engineering Pipeline consisting of data ingestion, storage, transformation, publication, and visualization.

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
          Orchestrates all pipeline stages
```

### Pipeline Components

1. **Data Source:** Provides five raw CSV datasets from Kaggle.
2. **Data Ingestion:** Uses Python to load CSV files into PostgreSQL.
3. **Database Storage:** Stores source data in the `raw_data` schema.
4. **Data Transformation:** Uses Python and Pandas to clean, validate, join, and transform data.
5. **Data Aggregation:** Creates analytical tables in the `production` schema.
6. **Data Publication:** Publishes aggregated datasets to Google Sheets.
7. **Data Visualization:** Connects Google Sheets to Looker Studio for interactive reporting.

## 6. Database Structure

**Database Name:** `crypto_fraud_db`

The database is organized into two schemas to separate raw source data from processed analytical data.

### 6.1 Raw Schema

The `raw_data` schema stores the original CSV datasets.

Tables:

- `crypto_fraud_master`
- `transactions`
- `tokens`
- `wallets`
- `data_dictionary`

### 6.2 Production Schema

The `production` schema contains the processed fact table and analytical aggregation tables.

**Main Fact Table:**

- `fact_crypto_transactions`

**Aggregation Tables:**

1. `agg_overview`
2. `agg_manipulation_type`
3. `agg_venue_type`
4. `agg_token_risk`
5. `agg_wallet_age`
6. `agg_hourly_risk`
7. `agg_daily_risk`
8. `agg_behavior_by_label`
9. `agg_price_volume_by_label`
10. `agg_notional_by_label`

These tables are designed to support business analysis and provide structured datasets for dashboard visualization.

## 7. Data Transformation

The transformation process is performed using Python and Pandas.

The main steps include:

1. **Source Validation:** Validate source files and check transaction record matching.
2. **Data Quality Checks:** Check duplicate records and missing values.
3. **Data Type Validation:** Validate timestamp and numeric data types.
4. **Data Integration:** Join transaction records with token and wallet information.
5. **Feature Engineering:** Create additional analytical features, including:
   - `transaction_date`
   - `transaction_month`
   - `timestamp_hour`
   - `timestamp_is_night`
   - `wallet_age_group`
   - `manipulation_label`
6. **Data Aggregation:** Group and summarize processed records for business analysis.
7. **Production Loading:** Load the processed fact table and aggregation tables into the `production` schema.

## 8. Business Questions

The project focuses on nine business questions to explore cryptocurrency transaction patterns and simulated market manipulation behavior.

1. What proportion of transactions are labeled as market manipulation?
2. How do Wash Trade, Pump and Dump, and Ramping categories differ?
3. Do CEX and DEX transactions have different manipulation rates?
4. How do manipulation rates vary across cryptocurrency tokens?
5. Are new wallets more frequently labeled as manipulative than established wallets?
6. Does transaction value differ between labeled and non-labeled groups?
7. Are transaction bursts and counterparty reuse associated with manipulation labels?
8. How does manipulation activity vary by transaction hour?
9. Do price deviation and trading volume deviation differ between the two groups?

These questions guide the analytical process and determine the visualizations included in the Looker Studio dashboard.

## 9. Looker Studio Dashboard

The project includes an interactive Looker Studio dashboard consisting of two analytical pages.

### 9.1 Dashboard Overview

The dashboard contains:

- 4 KPI scorecards
- 11 analytical charts
- 2 analytical pages

**Page 1: Wallet & Behavioral Analysis**

Focuses on wallet behavior, transaction categories, token risk rankings, and behavioral patterns associated with manipulation labels.

**Page 2: Time & Market Analysis**

Focuses on transaction trends over time, price deviations, trading volume deviations, and market-related patterns.

### 9.2 Dashboard Link

[Open Crypto Fraud & Market Manipulation Analytics Dashboard](https://datastudio.google.com/reporting/a9afe694-3439-4358-8b15-af0797d4a615)

**Google Sheets Data Source:**

[Open Project Google Sheets](https://docs.google.com/spreadsheets/d/1Rk0GB6KOoJX2yWt3iD2_n5RSEVA9pK1RyUymkcZydjE/edit)

**Dashboard Sharing:** The Looker Studio report should be configured with "Anyone with the link can view" to allow access without requesting individual permission.

## 10. Project Structure

```text
Crypto-Fraud-Pipeline/
|
|-- data/
|   |-- crypto_fraud_master.csv
|   |-- transactions.csv
|   |-- tokens.csv
|   |-- wallets.csv
|   |-- data_dictionary.csv
|
|-- ingest.py
|-- transform.py
|-- publish.py
|-- run_pipeline.py
|
|-- docker-compose.yml
|-- requirements.txt
|
|-- .env.example
|-- .gitignore
|-- README.md
```

**Note:** The `data/` directory contains local dataset files used to run the pipeline. The raw CSV files are not included in the GitHub repository.

Sensitive credentials and environment configuration files are also excluded from version control.

## 11. Installation and Setup

### Prerequisites

Before running the project, ensure the following software and services are available:

- Python 3.14
- Docker Desktop
- Git
- Google Cloud Project
- Google Sheets API
- Google Drive API

### Step 1: Clone the Repository

Clone the project from GitHub:

```bash
git clone https://github.com/Punnatron/Crypto-Fraud-Pipeline.git
cd Crypto-Fraud-Pipeline
```

### Step 2: Prepare the Dataset

Download the five CSV files from the selected Kaggle dataset.

Place all five files inside the project's `data/` directory:

```text
data/
├── crypto_fraud_master.csv
├── transactions.csv
├── tokens.csv
├── wallets.csv
└── data_dictionary.csv
```

**Note:** The dataset files are not included in this repository and must be downloaded separately.

### Step 3: Create a Python Virtual Environment

For Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 4: Install Dependencies

Install the required Python packages:

```powershell
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables

Create a local `.env` file from the example configuration:

```powershell
Copy-Item .env.example .env
```

Open `.env` and configure the PostgreSQL connection settings and Google Sheets configuration according to the project's requirements.

**Important:** Do not commit the `.env` file to GitHub.

### Step 6: Configure Google API Credentials

The project uses Google Sheets API to publish processed analytical data to Google Sheets.

Follow these steps to configure Google API credentials:

1. Open Google Cloud Console.
2. Create a new Google Cloud Project or select an existing project.
3. Enable **Google Sheets API**.
4. Enable **Google Drive API**.
5. Navigate to IAM & Admin and create a Google Cloud Service Account.
6. Generate a JSON key for the Service Account.
7. Download the JSON key and store it locally as `credentials.json`.
8. Open the destination Google Spreadsheet.
9. Share the spreadsheet with the Service Account email address.
10. Assign the Service Account **Editor** permission.

The `credentials.json` file is used for authentication when the pipeline connects to Google Sheets.

**Security Warning:**

Never upload or commit the following files to GitHub:

- `credentials.json`
- `.env`
- Private service account keys

These files must remain local and must be excluded through `.gitignore`.

### Step 7: Start PostgreSQL Using Docker Compose

Start the PostgreSQL database container:

```powershell
docker compose up -d
```

Docker Compose will start the database environment required by the project.

### Step 8: Execute the Complete Data Pipeline

Run the pipeline using:

```powershell
python run_pipeline.py
```

The main execution script orchestrates the following stages:

1. Data Ingestion
2. Data Transformation
3. Google Sheets Publication

After successful execution, the processed analytical datasets will be available in Google Sheets for Looker Studio visualization.

## 12. Execution Results

The pipeline was successfully executed in the development environment.

The execution results include:

- 5 raw CSV tables loaded into PostgreSQL.
- 500,000 main transaction records processed.
- 10 aggregation tables created.
- 10 Google Sheets worksheets published.
- End-to-end pipeline execution completed successfully.

The published datasets are used as the data source for the Looker Studio dashboard.

## 13. Security Notes

This project uses Google Service Account authentication to access Google Sheets.

The following files and directories must not be committed to GitHub:

- `.env`
- `credentials.json`
- `.venv/`
- `.venv-1/`
- Raw CSV dataset files

The `.gitignore` file contains exclusion rules to prevent sensitive credentials, local environments, and raw datasets from being included in version control.

**Never expose private Google Service Account credentials in a public repository.**

## 14. Project Limitations

The project has the following limitations:

- The dataset contains simulated data and does not represent verified real-world cryptocurrency transactions.
- The project is an educational Data Engineering and Business Intelligence prototype.
- Manipulation labels are supplied by the dataset and are not independently verified real-world fraud findings.
- The system does not execute real cryptocurrency trades.
- The system does not connect to a live cryptocurrency exchange.
- Analytical results depend on the quality and characteristics of the original dataset.

Therefore, the results should be interpreted as analytical findings from simulated data rather than evidence of actual market manipulation.

## 15. Contributors

This project was developed collaboratively by three members.

- **Member 1:** Data Engineering and Infrastructure
- **Member 2:** Data Transformation and Analytics
- **Member 3:** Google Sheets Publication and Visualization

---

## Project Information

**Project:** Crypto Fraud & Market Manipulation Analytics

**Course:** AIE321 – Data Engineering / Business Intelligence Project

**GitHub Repository:**

[https://github.com/Punnatron/Crypto-Fraud-Pipeline](https://github.com/Punnatron/Crypto-Fraud-Pipeline)

**Dashboard:**

[Looker Studio – Crypto Fraud & Market Manipulation Analytics](https://datastudio.google.com/reporting/a9afe694-3439-4358-8b15-af0797d4a615)

**Institution:** Bangkok University

