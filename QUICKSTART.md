# Report Generator - Quick Start Guide

## What is this?

The **Report Generator** is an automated system that:
- Executes SQL queries from the Oracle database
- Generates CSV reports from query results
- Sends reports via email to designated recipients

It's designed to run as a scheduled job (via Control-M or cron) for periodic report distribution.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.6.8 or higher |
| Oracle Client | Oracle Instant Client |
| Database | Oracle with cx_Oracle |

---

## Directory Structure

```
report_generator/
├── main.py              # Main entry point
├── config.ini           # Configuration file
├── README.md            # Detailed documentation
├── QUICKSTART.md        # This file
├── src/                 # Source code
│   ├── services/        # Core services (email, database, CSV)
│   ├── models/          # Data models
│   └── utils/           # Utilities (config, date calculation)
├── logs/                # Log files (auto-created)
├── temp/                # Temporary CSV files (auto-created)
└── libs/                # Local Python dependencies
```

---

## Quick Setup

### 1. Configure the System

Edit `config.ini` with your environment settings:

```ini
[database]
host = your-db-host
port = 1521
service_name = YOUR_SERVICE
username = YOUR_USER
password = YOUR_PASSWORD

[email]
smtp_server = your-smtp-server
smtp_port = 25
smtp_use_tls = yes
smtp_require_auth = yes
smtp_username = your-smtp-user
smtp_password = your-smtp-password
from_email = reports@yourcompany.com
from_name = Report System
```

### 2. Set Oracle Environment (if needed)

```bash
export ORACLE_HOME=/path/to/oracle/client
export LD_LIBRARY_PATH=$ORACLE_HOME/lib:$LD_LIBRARY_PATH
```

---

## How to Run

### Basic Command

```bash
python main.py <interval> <date>
```

| Parameter | Description | Format |
|-----------|-------------|--------|
| `interval` | Report frequency type | See intervals below |
| `date` | Base date for report | `YYYY-MM-DD` |

### Available Intervals

| Interval | Description |
|----------|-------------|
| `daily` | Daily reports |
| `bi-daily` | Every two days |
| `weekly` | Weekly reports |
| `monthly` | Monthly reports |
| `quarterly` | Quarterly reports |
| `yearly` | Annual reports |
| `yesterday` | Previous day's data |
| `last_bd` | Last business day |

---

## Examples

### Run Daily Report
```bash
python main.py daily 2026-01-22
```

### Run Weekly Report
```bash
python main.py weekly 2026-01-22
```

### Run Last Business Day Report
```bash
python main.py last_bd 2026-01-22
```

### Run with Python 3 explicitly
```bash
python3 main.py daily 2026-01-22
```

---

## Checking Results

### Log Files

Logs are saved to the `logs/` directory:
```
logs/report_generator_daily_20260122.log
```

Log filename format: `report_generator_<interval>_<YYYYMMDD>.log`

### View Recent Logs
```bash
tail -100 logs/report_generator_daily_20260122.log
```

### Check for Errors
```bash
grep -i error logs/report_generator_daily_20260122.log
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success - all reports processed |
| `1` | Failure - one or more reports failed |

---

## Scheduling with Control-M / Cron

### Cron Example (Daily at 6 AM)
```cron
0 6 * * * cd /opt/report_generator && python3 main.py daily $(date +\%Y-\%m-\%d) >> /var/log/report_generator_cron.log 2>&1
```

### Control-M
Configure the job to run:
```
Command: python3 /opt/report_generator/main.py daily %%ODATE
Working Directory: /opt/report_generator
```

---

## Troubleshooting

### "No module named 'cx_Oracle'"
Install Oracle client and cx_Oracle:
```bash
pip install cx_Oracle
```

### "ORA-12170: TNS connect timeout"
Check database connectivity:
```bash
tnsping YOUR_SERVICE
```

### "SMTP authentication failed"
Verify SMTP credentials in `config.ini` and check:
- `smtp_use_tls = yes` (if server requires TLS)
- `smtp_require_auth = yes`

### "Permission denied" on logs directory
Create the logs directory:
```bash
mkdir -p logs temp
chmod 755 logs temp
```

---

## Output Summary

After execution, you'll see a summary:
```
============================================================
Report Generation Summary:
  Total Reports: 5
  Successful: 5
  Failed: 0
============================================================
```

---

## For More Information

See the detailed documentation in `README.md` for:
- Processing modes (Bulk, Per-BU, Per-Manager)
- Database table schemas
- Query parameter reference
- Advanced configuration options

---

## Support

For issues:
1. Check the log file for detailed error messages
2. Verify database connectivity
3. Verify SMTP server accessibility
4. Review `config.ini` settings
