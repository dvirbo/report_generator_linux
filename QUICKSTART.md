# Report Generator - Quick Start

## Introduction

Report Generator is an automated reporting service that:
- Loads active report definitions from `report_config`
- Executes report SQL against Oracle
- Generates CSV output
- Sends emails to the correct recipients by BU and processing mode

It is typically triggered by a scheduler (Control-M/cron) and returns:
- `0` when all reports succeed
- `1` when one or more reports fail

## Project Overview (Current Workflow)

### 1 Load Reports
The app loads active reports by interval (`daily`, `weekly`, `last_bd`, etc.) from `report_config`.

### 2 Resolve Processing Mode
Each report uses `bu_indicator` to decide behavior:
- `mador` / `compliance`: single query and bulk email
- `branches` / `merchav`: per-BU processing

### 3 Fetch Recipients
Primary recipients come from DB login names in `config.ini` (`[recipients]`) for branches, merchav, and compliance; mador uses `distribution_list` as the primary source. Every report also **appends** `distribution_list` emails at send time (deduplicated). DB recipients include:
- `email`
- `bu_identifier`
- `manager_id` (from `child_users.user_identifier`)

### 4 Execute Query
- Per-BU flow sends `bu` / `bu_identifier`
- Manager flow uses each recipient’s `manager_id` directly (no separate `get_manager_ids` lookup in report flow)

### 5 Deliver Email
- If query returns data: generate CSV and email
- If no data: send or skip based on `send_on_no_data`

## Run

```bash
python3 main.py <interval> <DD/MM/YYYY>