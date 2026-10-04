import copy
import re

import pytest

from reporting.formatting import format_count, format_inr, format_pct
from reporting.report_generator import (
    ReportGenerationError,
    alert_paragraph,
    generate_report,
)
from reporting.report_validator import (
    ReportValidationError,
    find_report_issues,
    validate_report,
)


@pytest.fixture(scope="module")
def report(alerts):
    return generate_report(alerts)


# ---- formatting --------------------------------------------------------------

def test_formatting_helpers():
    assert format_inr(92270.0) == "\u20b992,270"
    assert format_inr(-36275.0) == "\u20b936,275"
    assert format_inr(0.0) == "\u20b90"
    assert format_inr(10.5) == "\u20b910.50"  # never silently rounded
    assert format_pct(-18.84) == "18.84%"
    assert format_count(1234) == "1,234"


# ---- generator ---------------------------------------------------------------

def test_report_contains_readme_sentences(report):
    assert ("Ethnic Wear increased by 42.23% in May,\n"
            "with GMV increasing by \u20b992,270 compared with April.") in report
    assert ("Home & Kitchen declined by 18.84% in May,\n"
            "with GMV decreasing by \u20b936,275 compared with April.") in report
    assert "Reseller R024 (Reseller 24) in Ahmedabad (West) had no delivered orders\nduring the monitoring period." in report


def test_report_has_section_headings(report):
    for heading in ("May Category Update", "June Category Update",
                    "May Regional Update", "June Regional Update",
                    "Inactive Reseller"):
        assert heading in report


def test_report_header_counts(report):
    assert "Total alerts: 13" in report
    assert "Category alerts: 7" in report
    assert "Regional alerts: 5" in report
    assert "Inactive reseller alerts: 1" in report


def test_every_alert_is_represented_in_the_report(alerts, report):
    for alert in alerts:
        assert alert_paragraph(alert) in report


def test_report_is_deterministic(alerts):
    assert generate_report(alerts) == generate_report(copy.deepcopy(alerts))


def test_report_numbers_match_source_alert_data(alerts, report):
    for alert in alerts:
        data = alert["data"]
        if alert["entity_type"] == "reseller":
            assert alert["entity"] in report
            continue
        assert format_pct(data["change_pct"]) in report
        assert format_inr(data["change_amount"]) in report
        assert format_inr(data["previous_gmv"]) in report
        assert format_inr(data["current_gmv"]) in report


def test_report_has_no_unsupported_figures(alerts, report):
    allowed = {"2026"}
    allowed |= {format_count(n) for n in (13, 7, 5, 1, 0)}
    for alert in alerts:
        data = alert["data"]
        for key in ("change_pct", "change_amount", "previous_gmv",
                    "current_gmv", "gmv"):
            if key in data:
                value = format_pct(data[key]) if key == "change_pct" else format_inr(data[key])
                allowed.add(value.replace("\u20b9", "").replace("%", ""))
    text = re.sub(r"R\d{3}|Reseller \d+", "", report)
    numbers = {n.rstrip(",") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}
    assert numbers <= allowed


def test_empty_alert_list_gives_a_valid_report():
    report = generate_report([])
    assert "Total alerts: 0" in report
    assert validate_report(report, []) is True


def test_generator_fails_on_unknown_alert_type(alerts):
    bad = copy.deepcopy(alerts[0])
    bad["alert_type"] = "SOMETHING_ELSE"
    with pytest.raises(ReportGenerationError):
        generate_report([bad])


def test_generator_fails_on_missing_data(alerts):
    bad = copy.deepcopy(alerts[0])
    del bad["data"]["change_pct"]
    with pytest.raises(ReportGenerationError):
        generate_report([bad])


def test_generator_fails_on_missing_keys():
    with pytest.raises(ReportGenerationError):
        generate_report([{"alert_type": "CATEGORY_GROWTH"}])


# ---- validator: accepts a faithful report ----------------------------------------

def test_validator_accepts_the_real_report(alerts, report):
    assert find_report_issues(report, alerts) == []
    assert validate_report(report, alerts) is True


# ---- validator: rejects every kind of corruption -----------------------------------

def _paragraph_index(report, needle):
    return next(i for i, p in enumerate(report.split("\n\n")) if needle in p)


CORRUPTIONS = {
    "wrong percentage": lambda r: r.replace("42.23%", "42.24%"),
    "wrong GMV change": lambda r: r.replace("\u20b992,270", "\u20b992,271"),
    "wrong previous GMV": lambda r: r.replace("\u20b9218,497", "\u20b9218,498"),
    "wrong direction": lambda r: r.replace("Ethnic Wear increased", "Ethnic Wear declined", 1),
    "wrong category name": lambda r: r.replace("Kids Wear increased", "Kid Wear increased"),
    "wrong reseller id": lambda r: r.replace("Reseller R024", "Reseller R023"),
    "wrong severity": lambda r: r.replace("Severity: HIGH.", "Severity: NORMAL.", 1),
    "wrong month": lambda r: r.replace("42.23% in May", "42.23% in June"),
    "wrong header count": lambda r: r.replace("Total alerts: 13", "Total alerts: 12"),
    "invented number": lambda r: r.replace("Severity: HIGH.", "Severity: HIGH. Up 5% more.", 1),
    "invented reseller": lambda r: r + "\nReseller R099 (Reseller 99) in Pune (West) had no delivered orders\nduring the monitoring period.\n",
    "invented alert paragraph": lambda r: r.rstrip("\n") + "\n\nFoo Wear rose by 9.99% in June,\nwith GMV up.\n",
    "wrong section": lambda r: r.replace("May Regional Update", "June Regional Update"),
    "unexpected line": lambda r: r.replace("Inactive Reseller\n", "Inactive Reseller\n\nTrust me, this is fine\n"),
}


@pytest.mark.parametrize("name", sorted(CORRUPTIONS))
def test_validator_rejects_corrupted_report(alerts, report, name):
    corrupted = CORRUPTIONS[name](report)
    assert corrupted != report, "corruption did not change the report"

    with pytest.raises(ReportValidationError):
        validate_report(corrupted, alerts)


@pytest.mark.parametrize("needle", [
    "Ethnic Wear increased", "Home & Kitchen declined", "Kids Wear increased",
    "East region increased", "West region declined", "Reseller R024",
])
def test_validator_rejects_a_disappearing_alert(alerts, report, needle):
    paragraphs = report.split("\n\n")
    del paragraphs[_paragraph_index(report, needle)]

    with pytest.raises(ReportValidationError) as error:
        validate_report("\n\n".join(paragraphs), alerts)

    assert any("missing" in issue.lower() for issue in error.value.issues)


def test_validator_rejects_a_duplicated_alert(alerts, report):
    paragraphs = report.split("\n\n")
    index = _paragraph_index(report, "Ethnic Wear increased")
    paragraphs.insert(index, paragraphs[index])

    with pytest.raises(ReportValidationError):
        validate_report("\n\n".join(paragraphs), alerts)


def test_validator_rejects_an_empty_report(alerts):
    with pytest.raises(ReportValidationError):
        validate_report("", alerts)


def test_validator_error_lists_all_issues(alerts, report):
    corrupted = report.replace("42.23%", "42.24%").replace("\u20b992,270", "\u20b992,271")

    with pytest.raises(ReportValidationError) as error:
        validate_report(corrupted, alerts)

    assert len(error.value.issues) >= 2
