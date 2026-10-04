# Agent Specification: Reseller Monitoring Orchestrator

## 1. What the "agent" is

The agent is an **orchestrator, not an AI model**. It runs a fixed list of
steps in a fixed order, stops at the first failure, and hands the finished
report to a human. It contains no LLM, no API call and no generated text.
Running it twice on the same data gives byte-identical results.

Implementation: `agent/mock_runner.py` (`run_pipeline()`), started by
`python run_pipeline.py`.

## 2. Workflow

```text
START
  -> Validate dataset
  -> Run SQL analytics
  -> Apply business rules
  -> Generate alerts
  -> Generate report
  -> Validate report
  -> Human review
END
```

## 3. Inputs

| Input | Location | Notes |
| --- | --- | --- |
| Reseller data | `data/resellers.csv` | 24 resellers |
| Order data | `data/orders.csv` | 900 orders, April-June 2026 |
| Database | `data/meesho_reseller.db` | the analytics layer reads this, not the CSVs |
| SQL queries | `src/sql/01-05_*.sql` | the only place business metrics are calculated |

`python run_pipeline.py` regenerates the dataset first (seed 42, always
identical). `--skip-generate` reuses the files already in `data/`.

## 4. Outputs

| Output | Location | Content |
| --- | --- | --- |
| Alerts | `outputs/alerts.json` | every alert, values exactly as produced by the rules layer |
| Report | `outputs/monthly_report.txt` | template-based text, validated against the alerts |
| Regional summary | `outputs/regional_summary.csv` | per-region totals and May/June changes, copied from SQL |
| Console progress | stdout | `[1/6]` to `[6/6]` messages |

## 4a. Alert structure

Every alert has the same top-level fields:

| Field | Meaning |
| --- | --- |
| `alert_type` | `CATEGORY_GROWTH`, `CATEGORY_DECLINE`, `REGION_GROWTH`, `REGION_DECLINE`, `RESELLER_INACTIVE` |
| `severity` | `HIGH` or `NORMAL` (rule in section 6) |
| `period` | month of the change, or `April-June` for inactivity |
| `entity_type` | `category`, `region` or `reseller` |
| `entity` | category name, region name or reseller ID |
| `data` | the verified values from SQL (GMV, change %, change amount, ...) |

## 5. Steps

| # | Progress message | Action | Code | Stops the run when |
| --- | --- | --- | --- | --- |
| 1 | Validating dataset... | Check counts, duplicates, missing values, foreign keys, statuses, zero-order resellers, CSV/DB agreement | `validate_data()` | any check fails (`DataValidationError`) |
| 2 | Running SQL analytics... | Run the SQL files and load the results as DataFrames | `get_category_mom()`, `get_reseller_activity()`, `get_region_metrics()`, `get_region_mom()` | a query or the database fails |
| 3 | Applying alert rules... | Apply the business rules, combine all alerts, save `alerts.json` | `create_alerts()`, `save_alerts()` | the saved JSON does not match the in-memory alerts |
| 4 | Generating report... | Fill text templates from the alert values | `generate_report()` | an alert has an unknown type or missing values (`ReportGenerationError`) |
| 5 | Validating report... | Prove the report matches the alerts, then save the report and regional summary | `validate_report()` | any mismatch (`ReportValidationError`) |
| 6 | Ready for human review. | Print output locations and wait for a person | - | - |

## 6. Business rules

| Rule | Definition |
| --- | --- |
| Metrics | only `status = 'Delivered'` orders count; GMV = `quantity x unit_price` |
| Category change | alert when `abs(change_pct) >= 15` AND `abs(change_amount) >= 30,000` |
| Regional change | same thresholds (`REGION_PERCENT_THRESHOLD`, `REGION_GMV_THRESHOLD`) |
| Inactive reseller | alert when `delivered_orders == 0` |
| Severity (change alerts) | `HIGH` when `abs(change_pct) >= 30` AND `abs(change_amount) >= 60,000` (twice the alert thresholds), otherwise `NORMAL` |
| Severity (inactive reseller) | always `NORMAL`: there is no measured GMV impact to rank |

Changing any threshold means updating `src/rules.py`, the tests, the README
and the committed outputs together.

## 7. Failure conditions

The agent **fails loudly**: any failure raises an exception, the run stops,
and no later step executes.

| Failure | Exception | Result |
| --- | --- | --- |
| Data file missing, wrong counts, duplicates, bad foreign key | `DataValidationError` | stops at step 1 |
| Alert with unknown type or missing values | `ReportGenerationError` | stops at step 4 |
| Report differs from the alerts in any way | `ReportValidationError` (lists every issue) | stops at step 5 |

Before it starts, the agent deletes any old `monthly_report.txt`, so a
failed run can never leave a stale report that looks current. The report
and regional summary are written only after report validation passes.

## 8. Human review requirements

The pipeline never publishes or sends anything itself. After step 6 a
person must review `outputs/monthly_report.txt` before it is shared.

The reviewer should confirm that:

1. The alert counts in the header make sense for the business period.
2. Spot-checked figures match the source data (the validator already proves
   report = alerts; the person judges whether the alerts make business sense).
3. The inactive reseller (R024) is shown and is genuinely inactive.
4. Severity labels follow the documented rule.

Only after approval is the report sent to stakeholders. Rejecting the report
means fixing the data or rules, re-running the pipeline and reviewing again.
