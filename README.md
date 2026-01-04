# Report Generator System

Automated report generation and email distribution service for Oracle database systems.

## Overview

The Report Generator System processes reports based on configured intervals and distributes them via email to designated recipients. It supports multiple processing modes to handle different distribution requirements.

## Processing Modes

The system supports three main processing modes:

### 1. Single Query Bulk Email (`SINGLE_QUERY_BULK_EMAIL`)

**Used for:** Mador and Compliance reports

**Flow:**
1. Execute the report query once with date parameters
2. Generate a single CSV file with all results
3. Send one email to all recipients with the same CSV attachment

**Configuration:**
- `bu_indicator`: `mador` or `compliance`
- `recipient_source`: `distribution_list` (from report_config table)

**Example Use Case:**
- A compliance report that needs to be sent to all compliance officers
- All recipients receive identical data

---

### 2. Per Recipient Query Email (`PER_RECIPIENT_QUERY_EMAIL`)

**Used for:** Branches and Merchav reports (standard processing)

**Flow:**
1. Group recipients by `bu_identifier`
2. For each BU group:
   - Execute the report query with `:bu` parameter
   - Generate one CSV file per BU group
   - Send email to all recipients in that BU group
3. Each BU receives data filtered for their specific branch

**Configuration:**
- `bu_indicator`: `branches` or `merchav`
- `recipient_source`: `database` (fetched from actone.acm_users)
- `requires_bu_parameter`: `true`

**Example Use Case:**
- Branch reports where each branch receives data specific to their BU
- Multiple branches, each with their own filtered dataset

---

### 3. Per Manager Query Email (`PER_MANAGER_QUERY_EMAIL`)

**Used for:** Branches with multiple managers (manager-based processing)

**Flow:**
1. Check if any recipient's BU is in the `manager_bu_list` configuration
2. For BUs in the manager list:
   - Fetch manager IDs from `mizrahi_custom.referant` table using:
     ```sql
     SELECT DISTINCT tz_menahel_snif 
     FROM mizrahi_custom.referant 
     WHERE mispar_snif = :bu
     ```
   - For each manager ID:
     - Execute the report query with both `:bu_identifier` and `:manager_id` parameters
     - Generate a separate CSV file for each manager
     - Send personalized email to that specific manager
3. For BUs not in the manager list:
   - Use standard per-BU processing (mode 2)

**Configuration:**
- `bu_indicator`: `branches`
- `recipient_source`: `database`
- `manager_bu_list`: Comma-separated list of BU identifiers in `config.ini`
  ```ini
  [branches]
  manager_bu_list = 461,462,463
  ```

**Query Requirements:**
The report query must support optional `:manager_id` parameter:
```sql
WHERE bu.bu_identifier = :bu_identifier
  AND (:manager_id IS NULL OR r.tz_menahel_snif = :manager_id)
```

**Example Use Case:**
- Branch 461 has two managers
- Each manager receives a personalized report filtered by their manager ID
- The same branch number is used, but data is filtered per manager

---

## Configuration

### config.ini Structure

```ini
[database]
host = localhost
port = 1521
service_name = FREEPDB1
username = MIZRAHI_CUSTOM
password = <password>

[email]
smtp_server = <smtp-server>
smtp_port = 25
smtp_use_tls = yes
smtp_require_auth = yes
smtp_username = <username>
smtp_password = <password>
from_email = <from-email>
from_name = Automated Report System

[branches]
# Comma-separated list of BU identifiers that use manager-based processing
manager_bu_list = 461,462,463
```

### Report Configuration (report_config table)

Each report is configured with:
- `report_id`: Unique identifier
- `report_name`: Display name
- `sql_query`: SQL query with bind variables (`:start_date`, `:end_date`, `:bu`, `:bu_identifier`, `:manager_id`)
- `interval_desc`: Processing interval (daily, weekly, etc.)
- `distribution_list`: Email addresses (for distribution_list mode)
- `bu_indicator`: Processing mode indicator (`mador`, `branches`, `merchav`, `compliance`)
- `mail_subject`: Email subject line
- `mail_body`: Email body text

---

## Processing Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Report Processing                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────┐
        │   Determine Processing Mode       │
        │   (based on bu_indicator)        │
        └───────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Mode 1:     │   │   Mode 2:    │   │   Mode 3:    │
│   Bulk Email  │   │   Per BU     │   │   Per Manager│
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
   Execute once      Group by BU         Check manager list
   Send to all       Execute per BU      Fetch manager IDs
                     Send per group      Execute per manager
                                         Send per manager
```

---

## Manager-Based Processing Detailed Flow

```
For each report with bu_indicator = 'branches':
    │
    ├─► Get recipients from database
    │
    ├─► Group recipients by bu_identifier
    │
    ├─► For each BU group:
    │   │
    │   ├─► Is BU in manager_bu_list?
    │   │   │
    │   │   ├─► YES: Manager-based processing
    │   │   │   │
    │   │   │   ├─► Fetch manager IDs from referant table
    │   │   │   │   SELECT DISTINCT tz_menahel_snif 
    │   │   │   │   FROM mizrahi_custom.referant 
    │   │   │   │   WHERE mispar_snif = :bu
    │   │   │   │
    │   │   │   ├─► For each manager ID:
    │   │   │   │   │
    │   │   │   │   ├─► Execute query with:
    │   │   │   │   │   - :bu_identifier = BU identifier
    │   │   │   │   │   - :manager_id = manager ID
    │   │   │   │   │
    │   │   │   │   ├─► Generate CSV file
    │   │   │   │   │
    │   │   │   │   ├─► Match manager to recipient (by order)
    │   │   │   │   │
    │   │   │   │   └─► Send email to manager
    │   │   │   │
    │   │   │   └─► Log delivery for each manager
    │   │   │
    │   │   └─► NO: Standard per-BU processing
    │   │       │
    │   │       ├─► Execute query with :bu parameter
    │   │       │
    │   │       ├─► Generate CSV file
    │   │       │
    │   │       └─► Send email to all recipients in BU group
    │   │
    │   └─► Continue to next BU group
    │
    └─► Complete processing
```

---

## Query Parameter Reference

### Available Bind Variables

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `:start_date` | Conditional | Start date for report period | `2025-01-01` |
| `:end_date` | Conditional | End date for report period | `2025-01-31` |
| `:bu` | Conditional | Branch identifier (numeric) | `461` |
| `:bu_identifier` | Conditional | Branch identifier (string) | `'461'` |
| `:manager_id` | Optional | Manager ID for filtering | `'12345'` or `NULL` |

### Query Examples

**Standard Branch Query:**
```sql
SELECT * FROM alerts 
WHERE alert_date BETWEEN :start_date AND :end_date
  AND bu_identifier = :bu
```

**Manager-Based Query:**
```sql
SELECT * FROM alerts a
JOIN referant r ON r.tz_referant = a.owner_identifier
WHERE alert_date BETWEEN :start_date AND :end_date
  AND bu.bu_identifier = :bu_identifier
  AND (:manager_id IS NULL OR r.tz_menahel_snif = :manager_id)
```

---

## Usage

### Command Line

```bash
python main.py <interval> <yyyy-mm-dd>
```

**Examples:**
```bash
# Daily report for 2025-01-15
python main.py daily 2025-01-15

# Weekly report for 2025-01-15
python main.py weekly 2025-01-15

# Last business day report
python main.py last_bd 2025-01-15
```

### Valid Intervals

- `daily` - Daily reports
- `bi-daily` - Bi-daily reports
- `weekly` - Weekly reports
- `monthly` - Monthly reports
- `quarterly` - Quarterly reports
- `yearly` - Yearly reports
- `yesterday` - Yesterday's data
- `last_bd` - Last business day

---

## Logging

The system logs to:
- **File**: `logs/report_generator_<interval>_<YYYYMMDD>.log`
- **Database**: `report_execution_log` and `report_email_delivery_log` tables

Log levels can be configured in `config.ini`:
```ini
[logging]
level = DEBUG
log_to_database = yes
log_to_file = yes
log_to_console = no
```

---

## Error Handling

- **No Data**: Reports with no data are logged but no email is sent
- **Query Errors**: Errors are logged and processing continues with next report
- **Email Failures**: Email delivery failures are logged per recipient
- **Missing Parameters**: Validation errors are raised before query execution

---

## Database Tables

### Configuration Tables
- `report_config` - Report definitions and SQL queries
- `mizrahi_custom.referant` - Manager-to-branch mapping

### Logging Tables
- `report_execution_log` - Report execution history
- `report_email_delivery_log` - Email delivery tracking

### User Tables
- `actone.acm_users` - User and recipient information
- `actone.acm_user_group_members` - User group relationships
- `actone.acm_md_business_units` - Business unit definitions

---

## Troubleshooting

### Manager-based processing not working

1. **Check configuration:**
   - Verify BU is in `manager_bu_list` in `config.ini`
   - Ensure `bu_indicator = 'branches'` in report_config

2. **Check manager IDs:**
   - Verify manager IDs exist in `mizrahi_custom.referant` table
   - Check that `tz_menahel_snif` is populated for the BU

3. **Check query:**
   - Ensure query supports `:manager_id` parameter
   - Verify query uses `(:manager_id IS NULL OR ...)` pattern

### Email not sending

1. **Check SMTP configuration:**
   - Verify SMTP server and credentials
   - Test TLS/STARTTLS settings
   - Check firewall/network connectivity

2. **Check email logs:**
   - Review `report_email_delivery_log` table
   - Check application logs for SMTP errors

### Query execution errors

1. **Check bind variables:**
   - Verify all required parameters are provided
   - Check parameter names match query bind variables (case-insensitive)

2. **Check database connection:**
   - Verify database credentials
   - Test connection timeout settings

---

## Version

- Python: 3.6.8+
- Database: Oracle (cx_Oracle)
- Dependencies: See requirements.txt

---

## Support

For issues or questions, check the logs and database execution logs for detailed error information.

