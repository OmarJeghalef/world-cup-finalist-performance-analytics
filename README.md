# 2026 World Cup Finalist Performance Analytics

An end-to-end cloud data analytics portfolio project that collects, processes, stores, analyzes, and visualizes 2026 FIFA World Cup match-performance data using Python, pandas, Azure, SQL, and Power BI.

The current version focuses on comparing Spain and Argentina throughout the 2026 World Cup and examining how their tournament performances differed during the final.

## Project Goal

The goal of this project is to build a repeatable analytics pipeline that:

1. Extracts World Cup competition, team, match, score, and tournament-stage data from a football API.
2. Saves raw API responses as timestamped JSON files.
3. Cleans and transforms match data using Python and pandas.
4. Validates processed datasets before cloud storage and database loading.
5. Stores raw and processed files in Azure Blob Storage.
6. Loads validated relational datasets into Azure SQL Database.
7. Analyzes team performance using SQL.
8. Prepares dashboard-ready SQL views for Power BI.
9. Builds an interactive Power BI dashboard comparing tournament and final-match performance.

## Analysis Questions

This project is focused on answering questions such as:

* How did Spain and Argentina perform throughout the 2026 World Cup?
* How did each team perform by tournament round?
* Did each finalist reach the final through attack, defense, or both?
* How did goals scored and conceded change throughout the tournament?
* Which matches were the biggest turning points?
* How did each team’s final performance compare with its tournament average?
* Which metrics changed most significantly during the final?
* Why was Argentina less effective in the final than during the rest of the tournament?
* Which areas of Spain’s performance helped it control the final?

## Technology Stack

Currently implemented:

* Python
* pandas
* requests
* python-dotenv
* football-data.org API
* Git
* GitHub

Planned:

* Azure Blob Storage
* Azure SQL Database
* SQL
* SQLAlchemy
* Power BI Desktop
* DAX

## Project Structure

```text
config/
└── settings.py

data/
├── raw/
│   ├── api/
│   └── reference/
├── processed/
└── validation/

src/
├── extract/
│   ├── __init__.py
│   └── test_api_connection.py
├── transform/
├── validate/
└── load/

sql/

dashboard/
└── screenshots/

docs/
├── data_sources.md
└── project_log.md

tests/

notebooks/

README.md
requirements.txt
.env.example
.gitignore
```

## Current Progress

* Created the GitHub repository and project structure.
* Created and configured a Python virtual environment.
* Installed the initial Python dependencies.
* Added secure environment-variable configuration.
* Added `.gitignore` rules for credentials, generated files, and the virtual environment.
* Connected successfully to the football-data.org API.
* Retrieved the FIFA World Cup competition and 2026 season information.
* Confirmed access to all 104 tournament matches.

## Running the API Connection Test

After activating the virtual environment and configuring the local `.env` file, run the connection test from the project root:

```bash
python -m src.extract.test_api_connection
```

## Extract

`src/extract/extract_world_cup_data.py` retrieves competition and match data from
the football-data.org API.

The script saves timestamped raw JSON files for:

- World Cup competition metadata
- All tournament matches
- Spain matches
- Argentina matches
- Extraction-run metadata

Generated raw files are stored in:

```text
data/raw/api/
````