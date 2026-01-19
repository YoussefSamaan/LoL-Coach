# Data Ingestion Pipeline

This directory contains the logic for ingesting data from the Riot Games API, processing it, and preparing it for the AI model.

## Architecture

We use a **Pipeline Design Pattern** to orchestrate the ingestion process.

### Core Components

#### 1. Logic Modules
These files contain the core business logic, independent of the pipeline structure.
- **`crawler.py`**: Handles all interactions with the Riot API. It fetches high-ELO ladder rankings to find player **PUUIDs**, scans their match history for **Match IDs**, and downloads the full **Match JSON** data.
- **`processor.py`**: Handles parsing of raw Match JSON files. It extracts relevant fields (picks, bans, win/loss), maps Champion IDs to names, and saves the result as a structured dataset (Parquet or CSV).
- **`ddragon.py`**: Fetches static data (Champion ID mappings) from Riot's DataDragon CDN.

#### 2. Pipeline Orchestration
- **`pipeline.py`**: Defines `IngestPipeline` (an ordered list of steps) and `PipelineContext` (shared state passed between steps).
- **`steps.py`**: Wraps the logic modules into concrete pipeline steps:
  - `FetchStaticDataStep`: Ensures champion mappings exist.
  - `ScanLadderStep`: Finds high-ELO players to use as seed data.
  - `ScanHistoryStep`: Finds recent matches for those players.
  - `DownloadContentStep`: Downloads the raw match data.
  - `ProcessDataStep`: Converts raw JSONs into a clean dataset.
  - `CleanupStep`: Optionally removes raw files after processing.
- **`main.py`**: The entry point. It loads configuration, assembles the pipeline, and executes it.

## Configuration

The pipeline is configured via **`backend/app/config/definitions/ingest.yaml`**.
Key settings include:
- **`sources`**: Which ranks (Tier/Division) to scan for players.
- **`defaults`**: Default region and queue type.
- **`paths`**: Input/output directories.

## Usage

To run the full ingestion pipeline:

```bash
# From the backend directory
python -m app.ingest.main
```

### Options

- **`--since [TIMESTAMP]`**: Only fetch matches played/created after this Unix timestamp.
- **`--cleanup-raw`**: Delete the raw JSON files after processing to save space.
- **`--format [parquet|csv]`**: Choose the output format (default: `parquet`).
- **`--note [TEXT]`**: Add a note to the run ID (logging only; does not affect output paths).

Example:
```bash
python -m app.ingest.main --since 1704067200 --cleanup-raw --format csv
```
