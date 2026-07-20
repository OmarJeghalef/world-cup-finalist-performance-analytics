# 2026 World Cup Finalist Performance Analytics

A cloud-based data analytics project comparing Spain and Argentina throughout the 2026 FIFA World Cup and examining how their tournament-level performances differed during the final.

## Project Goal

Build an end-to-end analytics pipeline using Python, pandas, Azure Blob Storage, Azure SQL Database, SQL, and Power BI.

The project will answer two main questions:

1. How did Spain and Argentina perform throughout the tournament?
2. Which performance factors changed most significantly during the final?

## Planned Architecture

Football API and verified match statistics
↓
Python extraction
↓
Azure Blob Storage
↓
pandas transformation and validation
↓
Azure SQL Database
↓
SQL reporting views
↓
Power BI dashboard

## Current Status

* [x] Repository structure
* [x] Python virtual environment
* [x] Dependency management
* [x] Secure environment configuration
* [ ] API connection
* [ ] Raw data extraction
* [ ] Data transformation
* [ ] Data validation
* [ ] Azure Blob Storage
* [ ] Azure SQL Database
* [ ] SQL analysis
* [ ] Power BI dashboard

## Technology Stack

* Python
* pandas
* REST APIs
* Azure Blob Storage
* Azure SQL Database
* SQL
* Power BI
* Git
* GitHub

## Planned Analysis

The project will compare Spain and Argentina across the full 2026 World Cup tournament and analyze how their performances changed during the final.

Planned metrics include:

* Match results
* Wins, draws, and losses
* Goals scored
* Goals conceded
* Goal difference
* Clean sheets
* Win margins
* Shots
* Shots on target
* Expected goals
* Possession
* Pass accuracy
* Performance by tournament round
* Final-match performance compared with tournament averages

## Planned Power BI Dashboard

The Power BI dashboard will contain two main pages.

### Page 1: Tournament Performance

This page will compare Spain and Argentina throughout the tournament.

Planned visuals include:

* KPI cards for wins, goals scored, goals conceded, goal difference, and clean sheets
* Match-by-match goals scored and conceded
* Cumulative goal difference
* Round-by-round performance
* Tournament path comparison
* Spain versus Argentina tournament averages

### Page 2: Final Match Analysis

This page will compare each team’s final-match performance with its previous tournament averages.

Planned visuals include:

* Tournament average versus final performance
* Shots and shots on target comparison
* Expected goals comparison
* Possession comparison
* Passing accuracy comparison
* Percentage change by metric
* Key factors that explain the final result

## Repository Structure

```text
world-cup-finalist-performance-analytics/
├── README.md
├── .gitignore
├── .env.example
├── requirements.txt
├── config/
│   └── settings.py
├── data/
│   ├── raw/
│   │   ├── api/
│   │   └── reference/
│   ├── processed/
│   └── validation/
├── src/
│   ├── extract/
│   ├── transform/
│   ├── validate/
│   └── load/
├── sql/
├── dashboard/
│   └── screenshots/
├── docs/
├── tests/
└── notebooks/
```

## Security

API keys, Azure credentials, database passwords, storage connection strings, and other sensitive information will be stored in a local `.env` file.

The `.env` file will not be committed to GitHub.

A public `.env.example` file will document the required environment variables without exposing real credentials.

## Project Status

This project is currently in development.

The first milestone is setting up the repository, Python environment, dependencies, secure configuration, and football API connection.
