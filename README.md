# Meesho-Reseller-Growth
Meesho Reseller Growth & Alert Monitoring Pipeline
README: setup, how to run every stage, and how it maps to the workflow pattern
1. Overview
A deterministic, rule-based pipeline that monitors reseller performance across categories, regions and individual resellers. It turns three months of synthetic order data (April to June 2026) into validated alerts and a stakeholder report.
The core principle: real numbers are computed by SQL first, business rules decide what matters, templates write the report from those verified values, and a validator proves the report matches the alerts before a human reviews it. No LLM and no AI-generated numbers are used anywhere.
Dataset -> Validate -> SQLite -> SQL analytics -> Rules -> Alerts
        -> Report draft -> Report validation -> Human review
2. Requirements and Setup
•	Python 3.10 or newer
•	pandas (data frames) and pytest (tests); everything else is the Python standard library
•	No API keys, accounts, internet access or environment variables are needed
Install (Windows PowerShell)
git clone <repository-url>
cd <repository>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
On macOS or Linux, activate the environment with: source .venv/bin/activate
3. How to Regenerate the Dataset
python src\generate_dataset.py
This rewrites three files in the data/ folder:
•	data/resellers.csv: 24 resellers, six per region (North, South, East, West)
•	data/orders.csv: 900 orders, 300 per month
•	data/meesho_reseller.db: SQLite database with resellers and orders tables and a foreign key
Generation is fully deterministic. A fresh random generator with seed 42 is created on every call, so the CSV files are identical on every run and every machine. R024 is given no orders on purpose, to test the inactive-reseller rule. The SQLite file has the same contents every time, but its bytes can differ between runs.
Do not change the seed or the category weights casually: the expected alerts depend on them.
4. How to Run Every Stage, in Order
Run the stages one at a time, or run all of them with a single command (see below).
#	Stage	Command	What it does
1	Generate dataset	python src\generate_dataset.py	Creates the CSV files and the SQLite database (seed 42).
2	Validate dataset	python src\validate_dataset.py	Checks counts, duplicates, missing values, foreign keys, statuses, CSV vs database. Stops with an error if anything is wrong.
3	Analytics, rules, report	python agent\mock_runner.py	Runs SQL analytics, applies the rules, saves alerts.json, generates and validates the report, writes outputs/.
4	Tests	pytest	Runs the 124 automated tests.

Single command
python run_pipeline.py
This runs stages 1 to 3 end to end, prints the report, and stops for human review. Options:
•	--skip-generate: reuse the existing files in data/ instead of regenerating them
•	--quiet: print only errors
Expected progress output:
[1/6] Validating dataset...
[2/6] Running SQL analytics...
[3/6] Applying alert rules...
[4/6] Generating report...
[5/6] Validating report...
[6/6] Ready for human review.
5. Runs With Zero API Keys
The whole pipeline runs with no API keys set. This was checked in three ways:
•	The code imports only the Python standard library plus pandas (and pytest in the tests).
•	A search of every .py file finds no reference to an LLM or AI provider, API key, HTTP library, socket or environment variable.
•	The full pipeline and all 124 tests were run with an empty environment (no variables set at all) and passed.
To check it yourself on Windows PowerShell, remove any key variables and run:
Remove-Item Env:ANTHROPIC_API_KEY, Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
python run_pipeline.py
pytest
6. Workflow Pattern Mapping
Each stage implements one step of the pattern: compute real numbers via SQL first, then hand off to rules, then to reporting, then validate, then a human reviews.
Stage	Files	Pattern it implements
Intake	src/generate_dataset.py, src/validate_dataset.py	Data is created reproducibly and validated before anything uses it. Bad data stops the run (fail loudly).
Compute real numbers (SQL)	src/sql/01 to 05, src/analytics.py	All business metrics are calculated once, in SQL, on delivered orders only. SQL is the single source of facts.
Hand off to rules	src/rules.py	Python only decides whether the SQL facts meet a documented rule. It never recalculates a metric. Output: alerts with one shared structure.
Summary and report draft	reporting/report_generator.py	Template text built only from verified alert values. No generated numbers and no LLM.
Validate reporting	reporting/report_validator.py	Independently proves every alert appears once, every number matches, and nothing unsupported appears. Any mismatch raises an error.
Orchestrate and review	agent/mock_runner.py, agent/specification.md, run_pipeline.py	Intake -> Summary -> Report Draft -> Validate -> Human review. Fixed steps, stops on first failure, never publishes by itself.
7. Business Rules
Rule	Definition
Metrics	Only orders with status Delivered count. GMV = quantity x unit price.
Category change alert	|change %| >= 15 AND |change amount| >= Rs 30,000 (both required).
Regional change alert	Same thresholds, held in separate named constants.
Inactive reseller	Alert when delivered orders = 0 (R024).
Severity: change alerts	HIGH when |change %| >= 30 AND |change amount| >= Rs 60,000; otherwise NORMAL.
Severity: inactive reseller	Always NORMAL (no measured GMV impact to rank).

Alert structure (all alerts share it): alert_type, severity, period, entity_type, entity, data.
8. Current Results
The current dataset produces 13 alerts: 7 category, 5 regional and 1 inactive reseller.
Month	Entity	Change %	Change (Rs)	Type	Severity
May	Ethnic Wear	+42.23%	+92,270	Growth	HIGH
May	Home & Kitchen	-18.84%	-36,275	Decline	NORMAL
June	Beauty & Personal Care	+42.65%	+46,509	Growth	NORMAL
June	Ethnic Wear	-46.68%	-145,052	Decline	HIGH
June	Home & Kitchen	+96.31%	+150,471	Growth	HIGH
June	Kids Wear	+33.47%	+39,323	Growth	NORMAL
June	Western Wear	-15.04%	-32,489	Decline	NORMAL
May	East region	+24.72%	+49,900	Growth	NORMAL
May	North region	+41.19%	+69,928	Growth	HIGH
May	South region	-21.07%	-57,702	Decline	NORMAL
June	South region	+17.11%	+36,990	Growth	NORMAL
June	West region	-15.58%	-31,455	Decline	NORMAL
Apr-Jun	Reseller R024 (Ahmedabad, West)	-	-	Inactive	NORMAL

East in June (+14.92%) just misses the 15% threshold and correctly raises no alert.
9. Outputs
Written to the outputs/ folder on every run and committed as examples:
•	outputs/alerts.json: all 13 alerts, values exactly as produced by the rules
•	outputs/monthly_report.txt: the validated report
•	outputs/regional_summary.csv: per-region totals and May/June changes, copied from SQL
A failed run deletes any old report first and writes the new one only after validation passes, so a stale report can never look current.
10. Repository Structure
data/            resellers.csv, orders.csv, meesho_reseller.db
src/             generate_dataset.py, validate_dataset.py, analytics.py,
                 rules.py, persistence.py, sql/01..05_*.sql
reporting/       formatting.py, report_generator.py, report_validator.py
agent/           specification.md, mock_runner.py
tests/           conftest.py, test_dataset/database/analytics/rules/
                 persistence/reporting/pipeline.py
outputs/         alerts.json, monthly_report.txt, regional_summary.csv
run_pipeline.py  single entry point
11. Testing
pytest
124 tests cover the dataset (counts, determinism, validation failures), the database (CSV match, foreign keys), analytics (644 delivered orders everywhere, month-over-month cross-checked against an independent pandas calculation), the rules (exact threshold boundaries, severity), persistence, reporting (14 kinds of deliberately corrupted reports are all rejected, plus dropped and duplicated alerts) and the end-to-end pipeline (including that outputs/ stays up to date).
12. Design Principles
•	No LLM in the core pipeline: results are reproducible and auditable.
•	SQL is the single source of facts; the reporting layer never calculates a metric.
•	Thresholds are named constants, not magic numbers.
•	Fail loudly: validation and reporting raise errors instead of producing a wrong report.
•	Nothing is hidden: the LEFT JOIN keeps R024 visible. Do not change it to an INNER JOIN.
13. Limitations
•	The data is synthetic and covers three months; April has no comparison month, so it cannot raise a change alert.
•	Month names are hard-coded (April, May, June) in the SQL and in MONTH_ORDER.
•	One fixed threshold applies to every category and region, and severity is a simple two-level rule.
•	Human review is manual: the pipeline stops and prints the report but does not record an approval.
