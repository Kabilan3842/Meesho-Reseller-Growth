import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _path in (BASE_DIR, os.path.join(BASE_DIR, "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from analytics import (  # noqa: E402
    DB_FILE,
    get_category_mom,
    get_region_metrics,
    get_region_mom,
    get_reseller_activity,
)
from persistence import (  # noqa: E402
    OUTPUTS_DIR,
    load_alerts,
    save_alerts,
    save_regional_summary,
    save_report,
)
from reporting.report_generator import generate_report  # noqa: E402
from reporting.report_validator import validate_report  # noqa: E402
from rules import create_alerts  # noqa: E402
from validate_dataset import DATA_DIR, validate_data  # noqa: E402


TOTAL_STEPS = 6


def run_pipeline(output_dir=OUTPUTS_DIR, data_dir=DATA_DIR, db_file=None,
                 verbose=True):
    """Validate -> analytics -> rules -> report -> validate -> human review.

    Returns the validated report text. Any failure raises an exception and
    stops the run; a stale monthly report is removed first so a failed run
    can never leave an old report looking current.
    """
    if db_file is None:
        db_file = (
            DB_FILE if data_dir == DATA_DIR
            else os.path.join(data_dir, "meesho_reseller.db")
        )

    def progress(step, message):
        if verbose:
            print(f"[{step}/{TOTAL_STEPS}] {message}")

    alerts_path = os.path.join(output_dir, "alerts.json")
    report_path = os.path.join(output_dir, "monthly_report.txt")
    summary_path = os.path.join(output_dir, "regional_summary.csv")

    if os.path.exists(report_path):
        os.remove(report_path)

    progress(1, "Validating dataset...")
    validate_data(data_dir, verbose=False)

    progress(2, "Running SQL analytics...")
    category_mom = get_category_mom(db_file)
    reseller_data = get_reseller_activity(db_file)
    region_data = get_region_metrics(db_file)
    region_mom = get_region_mom(db_file)

    progress(3, "Applying alert rules...")
    alerts = create_alerts(category_mom, reseller_data, region_mom)
    save_alerts(alerts, alerts_path)

    if load_alerts(alerts_path) != alerts:
        raise RuntimeError("alerts.json does not match the generated alerts")

    progress(4, "Generating report...")
    report = generate_report(alerts)

    progress(5, "Validating report...")
    validate_report(report, alerts)

    save_report(report, report_path)
    save_regional_summary(region_data, region_mom, summary_path)

    progress(6, "Ready for human review.")
    if verbose:
        print(f"      Alerts : {alerts_path}")
        print(f"      Report : {report_path}")
        print(f"      Regions: {summary_path}")

    return report


if __name__ == "__main__":
    run_pipeline()
