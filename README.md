# Production-Ready Tableau ETL Automation (Hyper & TWBX Packaging)

Production-ready end-to-end ETL pipeline for generating Tableau Hyper extracts and building fully portable TWBX packages at scale.

## Overview

This project automates data extraction from SQL Server, generatesg Tableau Hyper files, and packages them into TWBX workbooks.

It is designed to replace manual BI workflows with a scalable, reproducible pipeline.

---

## Problem

Manual creation of Tableau extracts and packaging processes:

• ~2-4 hours per reporting cycle  
• High risk of human error in file paths and packaging  
• Performance degrades significantly when handling multi-millions row datasets 

---

## Solution

This project automates the full pipeline:

- Reduces report generation time by ~45% 
- Eliminates manual errors in TWBX packaging 
- Enables scalable processing of large datasets
- Produces fully portable Tableau workbooks (no absolute paths)
- Tested with datasets exceeding 5M+ rows in SQL Server environments

---

## Key Features

- Automated ETL pipeline for Tableau
- Hyper file generation at scale
- TWBX packaging without manual intervention
- Portable outputs (no hardcoded paths)
- Designed to handle datasets with 5M+ rows efficiently

---

## Tech Stack

- Python
- Tableau Hyper API
- SQL Server (ODBC / pyodbc)
- File system automation

---

## Project Structure

````
repo/
│
├── src/
│ ├── export_hyper.py
│ ├── build_tableau_package.py
│
├── .env.example
├── requirements.txt
├── README.md

````

---


## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Dys-b/Portfolio.git
cd Potfolio
```


### 2. Create environment variables

Create a .env file based on:
```bash
DB_SERVER=your_server
DB_DATABASE=your_database
DB_USER=your_user
DB_PASSWORD=your_password
```

### 3. Install dependencies
````
pip install -r requirements.txt

````

#### Step 1: Generate Hyper files
````
python src/export_hyper.py
````

#### Step 2: Build TWBX package
````
python src/build_tableau_package.py
````

## Output
- .hyper files (aggregated datasets).
- .twbx Tableau packaged workbooks.
- Fully portable (no absolute paths).

## Impact
- Eliminates manual BI processing.
- Improves scalability of Tableau workflows.
- Enables reproducible data pipelines.
- Reduces operational errors in report generation.


## Automation
- This project follows a production-style ETL approach and is designed to simulate real-world BI automation scenarios.
- This pipeline is designed to be scheduled (e.g., via cron or SQL Server Agent), enabling fully automated report generation workflows.
- Supports integration wih scheduling tools (e.g., SQL  Server Agent, cron jobs).

## Author
Developed as part of a data engineering and BI automation portfolio.
