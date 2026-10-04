import re

from reporting.formatting import format_count, format_inr, format_pct
from reporting.report_generator import REPORT_TITLE, REPORT_YEAR


NUMBER_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
RESELLER_ID_RE = re.compile(r"\bR\d{3}\b")
HEADING_RE = re.compile(
    r"^(?:(?:April|May|June) (?:Category|Regional) Update|Inactive Reseller)$"
)
EMPTY_REPORT_TEXT = "No alerts were generated for this period."

# Deliberately independent from the generator's own tables.
DIRECTION_WORDS = {
    "CATEGORY_GROWTH": ("increased", "increasing"),
    "CATEGORY_DECLINE": ("declined", "decreasing"),
    "REGION_GROWTH": ("increased", "increasing"),
    "REGION_DECLINE": ("declined", "decreasing"),
}
SECTION_LABEL = {"category": "Category Update", "region": "Regional Update"}


class ReportValidationError(Exception):
    """Raised when the report does not faithfully reflect the alerts."""

    def __init__(self, issues):
        self.issues = list(issues)
        super().__init__(
            "Report validation failed:\n  - " + "\n  - ".join(self.issues)
        )


def _flat(paragraph):
    return re.sub(r"\s+", " ", paragraph).strip()


def _tokens(text):
    return [t.rstrip(",") for t in NUMBER_RE.findall(text)]


def _plain(formatted):
    """Strip the rupee sign and percent sign so only the number remains."""
    return formatted.replace("\u20b9", "").replace("%", "")


def _describe(alert):
    return f"{alert.get('alert_type')} {alert.get('entity')} {alert.get('period')}"


def _expected_heading(alert):
    if alert["entity_type"] == "reseller":
        return "Inactive Reseller"
    return f"{alert['period']} {SECTION_LABEL[alert['entity_type']]}"


def _expected_parts(alert):
    """Substrings a faithful paragraph for this alert must contain."""
    data = alert["data"]
    sev = f"Severity: {alert['severity']}"

    if alert["alert_type"] in DIRECTION_WORDS:
        past, present = DIRECTION_WORDS[alert["alert_type"]]
        return [
            (alert["entity"], "entity name"),
            (f"{past} by {format_pct(data['change_pct'])} in {alert['period']}",
             "direction, percentage or period"),
            (f"{present} by {format_inr(data['change_amount'])} compared with "
             f"{data['previous_period']}", "GMV change or comparison month"),
            (f"from {format_inr(data['previous_gmv'])} to "
             f"{format_inr(data['current_gmv'])}", "previous/current GMV"),
            (sev, "severity"),
        ]

    return [
        (f"Reseller {alert['entity']}", "reseller ID"),
        (data["reseller_name"], "reseller name"),
        (f"in {data['city']} ({data['region']})", "city or region"),
        ("no delivered orders", "inactivity statement"),
        (f"Delivered orders: {format_count(data['delivered_orders'])}",
         "delivered orders"),
        (f"GMV: {format_inr(data['gmv'])}", "GMV"),
        (sev, "severity"),
    ]


def _allowed_numbers(alert):
    data = alert["data"]

    if alert["alert_type"] in DIRECTION_WORDS:
        return {
            _plain(format_pct(data["change_pct"])),
            _plain(format_inr(data["change_amount"])),
            _plain(format_inr(data["previous_gmv"])),
            _plain(format_inr(data["current_gmv"])),
        }

    return {
        format_count(data["delivered_orders"]),
        _plain(format_inr(data["gmv"])),
    }


def _text_without_names(paragraph, alert):
    """Remove names/IDs that legitimately contain digits before scanning."""
    text = paragraph
    if alert["alert_type"] == "RESELLER_INACTIVE":
        text = text.replace(alert["data"]["reseller_name"], "")
    return text.replace(alert["entity"], "")


def _check_header(paragraph, alerts, issues):
    lines = paragraph.split("\n")

    if lines[0] != REPORT_TITLE:
        issues.append(f"Report does not start with the title {REPORT_TITLE!r}")

    expected = {
        "Total alerts": len(alerts),
        "Category alerts": sum(a["entity_type"] == "category" for a in alerts),
        "Regional alerts": sum(a["entity_type"] == "region" for a in alerts),
        "Inactive reseller alerts":
            sum(a["entity_type"] == "reseller" for a in alerts),
    }

    for label, count in expected.items():
        match = re.search(rf"^{label}: ([\d,]+)$", paragraph, re.MULTILINE)
        if not match:
            issues.append(f"Header is missing the line '{label}: N'")
        elif match.group(1) != format_count(count):
            issues.append(
                f"Header says {label}: {match.group(1)} "
                f"but the alerts contain {format_count(count)}"
            )

    allowed = {format_count(c) for c in expected.values()}
    allowed.add(str(REPORT_YEAR))
    for token in _tokens(paragraph):
        if token not in allowed:
            issues.append(f"Unsupported number in header: {token}")


def find_report_issues(report, alerts):
    """Return a list of problems (empty list means the report is valid)."""
    issues = []

    paragraphs = [p for p in report.strip().split("\n\n") if p.strip()]

    if not paragraphs:
        return ["Report is empty"]

    _check_header(paragraphs[0], alerts, issues)

    # Classify the remaining paragraphs and remember each one's heading.
    heading = None
    alert_paragraphs = []  # (heading, paragraph)

    for paragraph in paragraphs[1:]:
        if "\n" not in paragraph:
            if HEADING_RE.match(paragraph):
                heading = paragraph
            elif paragraph == EMPTY_REPORT_TEXT and not alerts:
                continue
            else:
                issues.append(f"Unexpected text in report: {paragraph!r}")
        else:
            alert_paragraphs.append((heading, paragraph))

    # Match every alert to its own paragraph.
    claimed = set()

    for alert in alerts:
        label = _describe(alert)
        parts = _expected_parts(alert)

        candidates = [
            i for i, (_, p) in enumerate(alert_paragraphs)
            if i not in claimed
            and alert["entity"] in p
            and (alert["alert_type"] == "RESELLER_INACTIVE"
                 or f"in {alert['period']}," in _flat(p) + ",")
        ]

        if not candidates:
            issues.append(f"Alert missing from report: {label}")
            continue

        # Prefer a candidate that matches every expected part.
        def missing_for(i):
            text = _flat(alert_paragraphs[i][1])
            return [what for needle, what in parts if needle not in text]

        best = min(candidates, key=lambda i: len(missing_for(i)))
        claimed.add(best)

        for what in missing_for(best):
            issues.append(f"Mismatch in {label}: {what} not found in report")

        found_heading, paragraph = alert_paragraphs[best]
        if found_heading != _expected_heading(alert):
            issues.append(
                f"Alert {label} is under heading {found_heading!r}, "
                f"expected {_expected_heading(alert)!r}"
            )

        allowed = _allowed_numbers(alert)
        scan_text = _text_without_names(paragraph, alert)
        for token in _tokens(scan_text):
            if token not in allowed:
                issues.append(
                    f"Unsupported number {token} in the paragraph for {label}"
                )

    for i, (_, paragraph) in enumerate(alert_paragraphs):
        if i not in claimed:
            issues.append(
                "Paragraph is not backed by any alert: "
                f"{_flat(paragraph)[:70]!r}"
            )

    # Reseller IDs anywhere in the report must belong to an alert.
    known_ids = {a["entity"] for a in alerts if a["entity_type"] == "reseller"}
    for reseller_id in sorted(set(RESELLER_ID_RE.findall(report))):
        if reseller_id not in known_ids:
            issues.append(f"Unsupported reseller ID in report: {reseller_id}")

    return issues


def validate_report(report, alerts):
    """Raise ReportValidationError if the report is not faithful."""
    issues = find_report_issues(report, alerts)

    if issues:
        raise ReportValidationError(issues)

    return True
