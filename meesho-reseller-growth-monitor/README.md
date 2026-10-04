# Meesho Reseller Growth & Alert Monitoring Pipeline

A deterministic, end-to-end data analytics pipeline for monitoring reseller performance across **categories**, **regions**, and **individual resellers**.

The project simulates a Meesho reseller monitoring workflow in which business and category managers need to identify significant category movements, inactive resellers, and regional performance changes from monthly order data.

The pipeline is intentionally **deterministic and rule-based**. It does not use an LLM or AI-generated numbers:

| Layer | Responsibility |
| --- | --- |
| SQL | Calculates business facts |
| Python rules | Makes business decisions |
| Templates | Communicate verified results |
| Validators | Prove the data and the report are correct |
| Orchestrator | Controls the workflow |

> Every number in a report must come from a verified SQL/Python result. The reporting layer never invents a number.

Run everything with one command:

```powershell
python run_pipeline.py
pytest
```

---

## Table of Contents

1. [Project Objective](#1-project-objective)
2. [Project Status](#2-project-status)
3. [Technology Stack](#3-technology-stack)
4. [Repository Structure](#4-repository-structure)
5. [Getting Started](#5-getting-started)
6. [Dataset Generation](#6-dataset-generation)
7. [Intentional Business Patterns](#7-intentional-business-patterns)
8. [Data Validation](#8-data-validation)
9. [Database](#9-database)
10. [SQL Analytics Layer](#10-sql-analytics-layer)
11. [Python Rules Engine](#11-python-rules-engine)
12. [Current Rule Results](#12-current-rule-results)
13. [Reporting and Report Validation](#13-reporting-and-report-validation)
14. [Orchestrator and Entry Point](#14-orchestrator-and-entry-point)
15. [Testing](#15-testing)
16. [Example Outputs](#16-example-outputs)
17. [Design Principles](#17-design-principles)
18. [Design Decisions](#18-design-decisions)
19. [Limitations](#19-limitations)
20. [Future Improvements](#20-future-improvements)
21. [Rules for Contributors](#21-rules-for-contributors)
22. [Architecture](#22-architecture)
23. [Definition of Done](#23-definition-of-done)

---

## 1. Project Objective

Build a small but complete data-driven monitoring system that answers four business questions:

1. **Which categories changed enough to matter?**
2. **Which resellers are inactive?**
3. **Which regions are contributing, and how are they changing?**
4. **How can these findings be turned into a reliable stakeholder report without inventing numbers?**

Pipeline flow:

```text
Synthetic Reseller + Order Data
            |
            v
      Data Validation
            |
            v
       SQLite Database
            |
            v
       SQL Analytics
            |
            v
      Python Rule Engine
            |
            v
          Alerts
            |
            v
   Deterministic Reporting
            |
            v
     Output Validation
            |
            v
       Human Review
```

---

## 2. Project Status

All roadmap steps are complete.

| Component | Status |
| --- | --- |
| Synthetic dataset generation | Done |
| CSV generation | Done |
| SQLite database creation | Done |
| Data validation (`validate_data()`, fails loudly) | Done |
| Category analytics | Done |
| Reseller activity analytics | Done |
| Regional analytics | Done |
| Category month-over-month analysis | Done |
| Regional month-over-month analysis | Done |
| Category alert rules | Done |
| Inactive reseller rule | Done |
| Regional alert rules | Done |
| Combined alert output with a shared structure | Done |
| Alert persistence (`outputs/alerts.json`) | Done |
| Automated pytest test suite | Done |
| Deterministic report generator | Done |
| Report validation | Done |
| Agent / orchestrator specification | Done |
| Mock agent runner | Done |
| Single end-to-end entry point | Done |
| Example outputs | Done |

---

## 3. Technology Stack

- **Python 3**
- **pandas**: DataFrames for query results and validation
- **SQLite**: local, file-based database
- **SQL**: all business metrics, including `LAG()` window functions
- **CSV / JSON**: raw data export and alert persistence
- **pytest**: test framework

Standard-library modules used: `sqlite3`, `csv`, `json`, `random`, `os`, `re`, `argparse`, `datetime`.

No external LLM or API is required.

---

## 4. Repository Structure

```text
meesho-reseller-growth-monitor/
│
├── data/
│   ├── resellers.csv
│   ├── orders.csv
│   └── meesho_reseller.db
│
├── src/
│   ├── generate_dataset.py      # generate_data(): CSVs + SQLite DB (seed 42)
│   ├── validate_dataset.py      # validate_data(): data quality checks
│   ├── analytics.py             # run_query() + get_*() helpers -> DataFrames
│   ├── rules.py                 # business rules -> alerts, create_alerts()
│   ├── persistence.py           # save alerts / report / regional summary
│   └── sql/
│       ├── 01_category_metrics.sql
│       ├── 02_reseller_activity.sql
│       ├── 03_region_metrics.sql
│       ├── 04_category_mom.sql
│       └── 05_region_mom.sql
│
├── reporting/
│   ├── formatting.py            # display formatting only (never calculates)
│   ├── report_generator.py      # alerts -> template-based text
│   └── report_validator.py      # proves the report matches the alerts
│
├── agent/
│   ├── specification.md         # orchestrator specification
│   └── mock_runner.py           # run_pipeline(): the orchestrator
│
├── tests/
│   ├── conftest.py
│   ├── test_dataset.py
│   ├── test_database.py
│   ├── test_analytics.py
│   ├── test_rules.py
│   ├── test_persistence.py
│   ├── test_reporting.py
│   └── test_pipeline.py
│
├── outputs/
│   ├── alerts.json
│   ├── monthly_report.txt
│   └── regional_summary.csv
│
├── run_pipeline.py              # single entry point
├── pytest.ini
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 5. Getting Started

### Installation (Windows PowerShell)

```powershell
git clone <repository-url>
cd <repository>

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate`.

### Run the whole pipeline

```powershell
python run_pipeline.py
```

This regenerates the dataset, validates it, runs the SQL analytics, applies the rules, saves the alerts, generates and validates the report, writes `outputs/`, and stops for human review.

| Option | Effect |
| --- | --- |
| `--skip-generate` | Reuse the existing files in `data/` instead of regenerating them |
| `--quiet` | Print only errors |

### Run the individual stages

```powershell
python src\generate_dataset.py    # 1. Create CSVs and SQLite DB
python src\validate_dataset.py    # 2. Validate the data
python agent\mock_runner.py       # 3. Analytics -> rules -> report -> validation
```

### Run the tests

```powershell
pytest
```

---

## 6. Dataset Generation

**File:** `src/generate_dataset.py`

The generator creates a reproducible synthetic dataset using a fixed seed. Each call to `generate_data()` creates a fresh `random.Random(42)`, so the same data is produced on every run, however many times it is called.

### Resellers

24 resellers (`R001` to `R024`), six per region:

| Region | Cities |
| --- | --- |
| North | Delhi, Jaipur, Lucknow |
| South | Bengaluru, Chennai, Hyderabad |
| East | Kolkata, Patna, Bhubaneswar |
| West | Mumbai, Pune, Ahmedabad |

### Orders

900 orders, 300 per month (April, May, June 2026).

**Categories:** Ethnic Wear, Western Wear, Kids Wear, Home & Kitchen, Beauty & Personal Care. Each category has six products and its own price range.

**Quantity:** 1 to 5 units per order.

**Status probabilities:**

| Status | Probability |
| --- | --- |
| Delivered | 70% |
| Returned | 15% |
| Cancelled | 10% |
| Pending | 5% |

---

## 7. Intentional Business Patterns

The dataset is not completely random. Patterns were deliberately introduced so the monitoring system has meaningful events to detect.

**Ethnic Wear** (share of monthly orders): a large spike followed by a decline.

| April | May | June |
| --- | --- | --- |
| 20% | 34% | 18% |

**Home & Kitchen** (share of monthly orders): a May dip followed by a June recovery.

| April | May | June |
| --- | --- | --- |
| 20% | 14% | 22% |

**Inactive reseller:** `R024` never receives any orders. This gives the inactivity rule an explicit edge case.

---

## 8. Data Validation

**File:** `src/validate_dataset.py`

`validate_data()` runs every check, prints the results, and **raises `DataValidationError` listing every failed check**. The pipeline stops if the data is wrong.

Checks performed:

- Reseller and order row counts
- Missing values
- Duplicate IDs
- Monthly order counts
- Order status distribution
- Foreign-key consistency (every order references a real reseller)
- Resellers without orders
- Database row counts match the CSV files
- SQLite `foreign_key_check` is clean

Expected results:

| Check | Expected |
| --- | --- |
| Resellers | 24 |
| Orders | 900 |
| Orders per month | 300 / 300 / 300 |
| Delivered | 644 |
| Returned | 118 |
| Cancelled | 93 |
| Pending | 45 |
| Missing values | 0 |
| Duplicate IDs | 0 |
| Invalid reseller references | 0 |
| Resellers with no orders | `R024` only |

---

## 9. Database

**File:** `data/meesho_reseller.db`

| Table | Primary key | Notes |
| --- | --- | --- |
| `resellers` | `reseller_id` | Name, city, region, join date |
| `orders` | `order_id` | Foreign key `reseller_id` references `resellers` |

The analytics layer queries this database, not the CSV files.

---

## 10. SQL Analytics Layer

SQL queries live in `src/sql/`, separate from Python, so the business calculations stay readable and easy to change. `src/analytics.py` provides a `run_query()` helper that executes a `.sql` file and returns a pandas DataFrame.

All metrics count **only** orders where `status = 'Delivered'`.

**GMV = `quantity × unit_price`**

| SQL file | Python function | Output columns |
| --- | --- | --- |
| `01_category_metrics.sql` | `get_category_metrics()` | month, category, order_count, units_sold, gmv |
| `02_reseller_activity.sql` | `get_reseller_activity()` | reseller_id, reseller_name, region, city, delivered_orders, gmv |
| `03_region_metrics.sql` | `get_region_metrics()` | region, reseller_count, delivered_orders, gmv |
| `04_category_mom.sql` | `get_category_mom()` | category, month, current_gmv, previous_gmv, change_pct, change_amount |
| `05_region_mom.sql` | `get_region_mom()` | region, month, current_gmv, previous_gmv, change_pct, change_amount |

### Notes

- **Reseller activity** uses a `LEFT JOIN` on purpose, so resellers with zero orders stay visible. This is how `R024` is detected.
- **Category and regional MoM** use the `LAG()` window function to compare each category or region with the previous month.

### Current regional GMV

| Region | GMV |
| --- | ---: |
| South | ₹743,211 |
| East | ₹742,880 |
| North | ₹664,797 |
| West | ₹560,339 |

### Current regional month-over-month

| Region | Month | Current GMV | Previous GMV | Change % | Change (₹) |
| --- | --- | ---: | ---: | ---: | ---: |
| East | May | ₹251,739 | ₹201,839 | +24.72% | +49,900 |
| North | May | ₹239,687 | ₹169,759 | +41.19% | +69,928 |
| South | May | ₹216,173 | ₹273,875 | −21.07% | −57,702 |
| West | May | ₹201,956 | ₹187,882 | +7.49% | +14,074 |
| East | June | ₹289,302 | ₹251,739 | +14.92% | +37,563 |
| North | June | ₹255,351 | ₹239,687 | +6.54% | +15,664 |
| South | June | ₹253,163 | ₹216,173 | +17.11% | +36,990 |
| West | June | ₹170,501 | ₹201,956 | −15.58% | −31,455 |

---

## 11. Python Rules Engine

**File:** `src/rules.py`

SQL calculates the facts. Python decides whether those facts meet a business rule. This separation is intentional.

### Significant category change

```python
PERCENT_THRESHOLD = 15.0
GMV_THRESHOLD = 30000.0
```

A category change is significant only when **both** conditions hold:

```text
|change_pct|    >= 15%
AND
|change_amount| >= ₹30,000
```

Requiring both prevents alerts caused by large percentages on small absolute amounts.

| Direction | Alert type |
| --- | --- |
| Positive | `CATEGORY_GROWTH` |
| Negative | `CATEGORY_DECLINE` |

### Significant regional change

Regions use the same rule through their own named constants (`REGION_PERCENT_THRESHOLD`, `REGION_GMV_THRESHOLD`), so they can be changed independently if the business needs it.

| Direction | Alert type |
| --- | --- |
| Positive | `REGION_GROWTH` |
| Negative | `REGION_DECLINE` |

### Inactive reseller

A reseller is inactive when `delivered_orders == 0`.

Alert type: `RESELLER_INACTIVE`

### Severity

Severity is calculated by an explicit rule, defined in `src/rules.py`:

| Alert | Severity |
| --- | --- |
| Category / regional change | `HIGH` when `|change_pct| >= 30%` AND `|change_amount| >= ₹60,000` (twice the alert thresholds); otherwise `NORMAL` |
| Inactive reseller | always `NORMAL` (an inactive reseller has no measured GMV impact to rank) |

### Shared alert structure

`create_alerts(category_mom, reseller_activity, region_mom)` combines every source. All alerts have the same top-level fields:

| Field | Meaning |
| --- | --- |
| `alert_type` | `CATEGORY_GROWTH`, `CATEGORY_DECLINE`, `REGION_GROWTH`, `REGION_DECLINE`, `RESELLER_INACTIVE` |
| `severity` | `HIGH` or `NORMAL` |
| `period` | Month of the change, or `April-June` for inactivity |
| `entity_type` | `category`, `region` or `reseller` |
| `entity` | Category name, region name or reseller ID |
| `data` | The verified values from the SQL layer |

---

## 12. Current Rule Results

The current dataset produces **13 alerts**: 7 category alerts, 5 regional alerts and 1 inactive reseller alert.

### Category alerts

| Month | Category | Change % | Change (₹) | Type | Severity |
| --- | --- | ---: | ---: | --- | --- |
| May | Ethnic Wear | +42.23% | +92,270 | Growth | HIGH |
| May | Home & Kitchen | −18.84% | −36,275 | Decline | NORMAL |
| June | Beauty & Personal Care | +42.65% | +46,509 | Growth | NORMAL |
| June | Ethnic Wear | −46.68% | −145,052 | Decline | HIGH |
| June | Home & Kitchen | +96.31% | +150,471 | Growth | HIGH |
| June | Kids Wear | +33.47% | +39,323 | Growth | NORMAL |
| June | Western Wear | −15.04% | −32,489 | Decline | NORMAL |

### Regional alerts

| Month | Region | Change % | Change (₹) | Type | Severity |
| --- | --- | ---: | ---: | --- | --- |
| May | East | +24.72% | +49,900 | Growth | NORMAL |
| May | North | +41.19% | +69,928 | Growth | HIGH |
| May | South | −21.07% | −57,702 | Decline | NORMAL |
| June | South | +17.11% | +36,990 | Growth | NORMAL |
| June | West | −15.58% | −31,455 | Decline | NORMAL |

East in June (+14.92%) just misses the 15% threshold and correctly raises no alert.

### Inactive reseller alert

| Reseller | Region | City | Delivered orders | GMV |
| --- | --- | --- | ---: | ---: |
| R024 | West | Ahmedabad | 0 | ₹0 |

### Example alert object

```json
{
  "alert_type": "CATEGORY_GROWTH",
  "severity": "HIGH",
  "period": "May",
  "entity_type": "category",
  "entity": "Ethnic Wear",
  "data": {
    "current_gmv": 310767.0,
    "previous_gmv": 218497.0,
    "change_pct": 42.23,
    "change_amount": 92270.0,
    "previous_period": "April"
  }
}
```

---

## 13. Reporting and Report Validation

### Report generator

**File:** `reporting/report_generator.py`

`generate_report(alerts)` converts verified alert objects into readable, template-based text. It only formats values that already exist in the alerts: it never calculates a percentage or a GMV, and it raises `ReportGenerationError` for an unknown alert type or missing values.

```text
May Category Update

Ethnic Wear increased by 42.23% in May,
with GMV increasing by ₹92,270 compared with April.
GMV moved from ₹218,497 to ₹310,767. Severity: HIGH.

Inactive Reseller

Reseller R024 (Reseller 24) in Ahmedabad (West) had no delivered orders
during the monitoring period.
Delivered orders: 0, GMV: ₹0. Severity: NORMAL.
```

No GPT, LLM, OpenAI API, or AI-generated explanations are used.

### Report validator

**File:** `reporting/report_validator.py`

`validate_report(report, alerts)` re-derives what each paragraph must contain and raises `ReportValidationError`, listing every problem, if anything differs. It verifies that:

- every alert appears in the report, exactly once, and no alert disappears
- category and region names match
- reseller IDs match, and no unknown reseller ID appears
- percentages and GMV values match
- direction (increase / decrease) and severity match
- each alert sits under the correct section heading
- the header counts match the alerts
- no unsupported number or unbacked paragraph appears

---

## 14. Orchestrator and Entry Point

**Files:** `agent/specification.md`, `agent/mock_runner.py`, `run_pipeline.py`

The "agent" is an **orchestrator, not an AI model**: a fixed sequence of steps that stops at the first failure and ends with human review.

```text
START -> Validate dataset -> Run SQL analytics -> Apply business rules
      -> Generate alerts -> Generate report -> Validate report
      -> Human review -> END
```

```text
[1/6] Validating dataset...
[2/6] Running SQL analytics...
[3/6] Applying alert rules...
[4/6] Generating report...
[5/6] Validating report...
[6/6] Ready for human review.
```

`run_pipeline()` returns the validated report. Before it starts it removes any old `monthly_report.txt`, and it writes the report only after validation passes, so a failed run can never leave a stale report behind. See `agent/specification.md` for inputs, outputs, rules, failure conditions and human review requirements.

`run_pipeline.py` adds the first step, generating the dataset, and prints the report for review.

---

## 15. Testing

```powershell
pytest
```

| Area | What is tested |
| --- | --- |
| Dataset | 24 resellers, 900 orders, 300 orders/month, 644 delivered, R024 has no orders, generation is deterministic, validation fails loudly on tampered data |
| Database | CSV and DB counts and rows match, foreign keys valid, primary keys, R024 present |
| Analytics | 644 delivered orders in every query, regional and category totals, GMV agrees across queries, MoM values cross-checked against an independent pandas calculation |
| Rules | 7 category alerts, 5 regional alerts, 1 inactive reseller (R024), exact threshold boundaries, severity rule, shared alert structure |
| Persistence | `alerts.json` round-trips exactly, regional summary values come straight from SQL |
| Reporting | All alerts represented, numbers match source data, no unsupported figures, generator errors, and 14 kinds of deliberately corrupted reports plus dropped and duplicated alerts are all rejected by the validator |
| Pipeline | End-to-end run, deterministic output, six progress steps, stops on bad data and leaves no stale report, committed outputs are up to date |

---

## 16. Example Outputs

Committed in `outputs/` so reviewers can see what the system produces:

```text
outputs/
├── alerts.json            # all 13 alerts, values exactly as produced by the rules
├── monthly_report.txt     # validated, template-based report
└── regional_summary.csv   # per-region totals and May/June changes (from SQL)
```

A test fails if these files fall out of date with the pipeline.

---

## 17. Design Principles

1. **No LLM in the core pipeline.** Results must be reproducible and auditable.
2. **SQL is the single source of facts.** Metrics are calculated once, in SQL.
3. **Rules are explicit.** Thresholds are named constants, not magic numbers.
4. **Reporting only communicates.** The report generator must not recalculate metrics such as `(current - previous) / previous`. It formats values already produced by the SQL/rules layer.
5. **Fail loudly.** Validation and reporting raise errors rather than silently produce an incorrect report.
6. **Nothing is hidden.** Edge cases such as zero-order resellers must stay visible.

---

## 18. Design Decisions

- **Regional alerts reuse the category thresholds** (≥15% and ≥₹30,000) through separate named constants. The README originally gave no regional rule, and reusing the documented one avoids inventing numbers.
- **Severity has two levels, defined by an explicit rule** (see section 11), because the README requires any severity to be documented. Inactive resellers are always `NORMAL`.
- **Alerts carry `previous_period`** (e.g. `April`) from the rules layer, so the report can say "compared with April" without doing any logic of its own.
- **The validator is independent of the generator.** It only shares the number formatters, so a generator bug cannot hide itself.
- **Outputs are written only after validation passes**, and an old report is deleted first.
- **CSV files use `\n` line endings** so the generated files are byte-identical on every operating system.
- **`create_alerts()` takes the month-over-month DataFrames** (not the plain category metrics), because the rules need `change_pct` and `change_amount`.
- **The print-only `src/test_*.py` scripts were replaced** by the `tests/` suite, as pytest would otherwise try to collect them.

---

## 19. Limitations

- The data is synthetic and covers only three months, so the first month (April) has no comparison and cannot raise a change alert.
- Month names are hard-coded (`April`, `May`, `June`) in the SQL and in `MONTH_ORDER`; supporting more months needs a small change in both.
- Thresholds are fixed for every category and region. A small category and a large category are judged by the same absolute ₹30,000 bar.
- Severity is a simple two-level rule and does not weigh how important a category or region is.
- Human review is a manual step: the pipeline stops and prints the report, but does not record an approval.
- `data/meesho_reseller.db` is a binary file, so SQLite may produce a byte-different file each time the dataset is regenerated, even though its contents are identical.

---

## 20. Future Improvements

- Record the human approval (reviewer, timestamp, decision) alongside the outputs.
- Add per-category and per-region thresholds.
- Add reseller-level trend alerts (for example, a sharp drop in a reseller's GMV), not only inactivity.
- Support any number of months instead of April to June.
- Export the report to HTML or PDF.
- Add a scheduled run and email delivery after approval.
- Add an optional, clearly separate LLM add-on for narrative commentary that can never change the verified numbers.

---

## 21. Rules for Contributors

**Do not change the dataset casually.**
The dataset is deliberately designed to exercise the alert rules. Changing the random seed or category weights changes the expected results.

**Do not change thresholds without documenting it.**
If the category rule (`>= 15%` AND `>= ₹30,000`), the regional rule or the severity rule changes, update `rules.py`, the tests, this README, `agent/specification.md` and the expected outputs.

**Do not let the reporting layer calculate business metrics.**
Reporting communicates results. The SQL/rules layer produces them.

**Do not introduce an LLM.**
Any LLM experiment must be a separate, optional add-on and must never replace the verified pipeline.

**Do not hide inactive resellers.**
The `LEFT JOIN` in `02_reseller_activity.sql` is intentional. Changing it to an `INNER JOIN` would make `R024` disappear.

**Do not recreate completed parts** unless a bug is found. Build on the existing implementation.

---

## 22. Architecture

```text
                    DATA GENERATOR
                         |
                         v
              resellers.csv / orders.csv
                         |
                         v
                  DATA VALIDATION
                         |
                         v
                  SQLite DATABASE
                         |
          +--------------+--------------+
          |              |              |
          v              v              v
      CATEGORY       RESELLER        REGION
      MoM SQL          SQL          MoM SQL
          |              |              |
          +--------------+--------------+
                         |
                         v
                  PYTHON RULES
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
          Category   Inactive     Regional
           Alerts    Resellers     Alerts
             |           |           |
             +-----------+-----------+
                         |
                         v
                  ALERT COLLECTION  --->  outputs/alerts.json
                         |
                         v
             DETERMINISTIC REPORTING
                         |
                         v
                REPORT VALIDATION
                         |
                         v
            outputs/monthly_report.txt
            outputs/regional_summary.csv
                         |
                         v
                 MOCK ORCHESTRATOR
                         |
                         v
                   HUMAN REVIEW
```

---

## 23. Definition of Done

- [x] Dataset generates successfully
- [x] Dataset validation passes
- [x] SQLite database builds successfully
- [x] All current SQL queries execute successfully
- [x] Category rules work
- [x] Inactive reseller rule works
- [x] pytest test suite passes
- [x] Regional MoM is implemented
- [x] Regional rules work
- [x] Alerts are persisted
- [x] Deterministic report is generated
- [x] Report values are validated
- [x] Agent specification exists
- [x] Mock runner executes the workflow
- [x] One command runs the complete pipeline
- [x] Example outputs are included
- [x] README explains the final architecture
- [x] GitHub repository is clean
