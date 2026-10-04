import json
import os

import pytest

import run_pipeline as entry_point
from agent.mock_runner import run_pipeline
from generate_dataset import generate_data
from validate_dataset import DataValidationError


def test_pipeline_runs_end_to_end(tmp_path):
    report = run_pipeline(output_dir=str(tmp_path), verbose=False)

    assert report.startswith("MEESHO RESELLER GROWTH & ALERT REPORT")
    for name in ("alerts.json", "monthly_report.txt", "regional_summary.csv"):
        assert (tmp_path / name).exists()


def test_pipeline_outputs_are_consistent(tmp_path):
    report = run_pipeline(output_dir=str(tmp_path), verbose=False)

    alerts = json.loads((tmp_path / "alerts.json").read_text(encoding="utf-8"))
    assert len(alerts) == 13
    assert (tmp_path / "monthly_report.txt").read_text(encoding="utf-8") == report


def test_pipeline_is_deterministic(tmp_path):
    first = run_pipeline(output_dir=str(tmp_path / "a"), verbose=False)
    second = run_pipeline(output_dir=str(tmp_path / "b"), verbose=False)

    assert first == second
    assert ((tmp_path / "a" / "alerts.json").read_text(encoding="utf-8")
            == (tmp_path / "b" / "alerts.json").read_text(encoding="utf-8"))


def test_pipeline_prints_the_six_progress_steps(tmp_path, capsys):
    run_pipeline(output_dir=str(tmp_path), verbose=True)
    lines = capsys.readouterr().out.splitlines()

    assert lines[:6] == [
        "[1/6] Validating dataset...",
        "[2/6] Running SQL analytics...",
        "[3/6] Applying alert rules...",
        "[4/6] Generating report...",
        "[5/6] Validating report...",
        "[6/6] Ready for human review.",
    ]


def test_pipeline_stops_on_bad_data_and_leaves_no_report(
        tmp_path, copied_data_dir):
    out = tmp_path / "out"
    run_pipeline(output_dir=str(out), verbose=False)  # a good earlier run
    assert (out / "monthly_report.txt").exists()

    orders = os.path.join(copied_data_dir, "orders.csv")
    with open(orders, encoding="utf-8") as f:
        lines = f.readlines()
    with open(orders, "w", encoding="utf-8") as f:
        f.writelines(lines[:-1])

    with pytest.raises(DataValidationError):
        run_pipeline(output_dir=str(out), data_dir=copied_data_dir,
                     verbose=False)

    # The stale report from the earlier run must not survive a failed run.
    assert not (out / "monthly_report.txt").exists()


def test_pipeline_runs_on_freshly_generated_data(tmp_path):
    data = tmp_path / "data"
    generate_data(str(data), verbose=False)

    report = run_pipeline(output_dir=str(tmp_path / "out"),
                          data_dir=str(data), verbose=False)

    assert "Total alerts: 13" in report


def test_entry_point_skip_generate(capsys):
    assert entry_point.main(["--skip-generate", "--quiet"]) == 0
    assert capsys.readouterr().out == ""


def test_committed_outputs_are_up_to_date():
    """The example outputs in outputs/ must match what the pipeline makes."""
    outputs = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "outputs")

    with open(os.path.join(outputs, "monthly_report.txt"),
              encoding="utf-8") as f:
        committed = f.read()

    assert committed == run_pipeline(output_dir=outputs, verbose=False)
