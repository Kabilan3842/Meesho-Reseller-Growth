from reporting.formatting import format_count, format_inr, format_pct


REPORT_TITLE = "MEESHO RESELLER GROWTH & ALERT REPORT"
REPORT_YEAR = 2026
MONITORING_PERIOD_LABEL = f"April-June {REPORT_YEAR}"

CHANGE_ALERT_TYPES = {
    "CATEGORY_GROWTH": ("category", "increased", "increasing"),
    "CATEGORY_DECLINE": ("category", "declined", "decreasing"),
    "REGION_GROWTH": ("region", "increased", "increasing"),
    "REGION_DECLINE": ("region", "declined", "decreasing"),
}
INACTIVE_ALERT_TYPE = "RESELLER_INACTIVE"

REQUIRED_ALERT_KEYS = ("alert_type", "severity", "period", "entity_type",
                       "entity", "data")
REQUIRED_CHANGE_DATA = ("current_gmv", "previous_gmv", "change_pct",
                        "change_amount", "previous_period")
REQUIRED_INACTIVE_DATA = ("reseller_name", "region", "city",
                          "delivered_orders", "gmv")


class ReportGenerationError(ValueError):
    """Raised when an alert cannot be turned into report text."""


def _check_alert(alert):
    missing = [k for k in REQUIRED_ALERT_KEYS if k not in alert]
    if missing:
        raise ReportGenerationError(f"Alert is missing keys {missing}: {alert}")

    alert_type = alert["alert_type"]

    if alert_type in CHANGE_ALERT_TYPES:
        required = REQUIRED_CHANGE_DATA
    elif alert_type == INACTIVE_ALERT_TYPE:
        required = REQUIRED_INACTIVE_DATA
    else:
        raise ReportGenerationError(f"Unknown alert_type: {alert_type!r}")

    missing = [k for k in required if k not in alert["data"]]
    if missing:
        raise ReportGenerationError(
            f"Alert data is missing {missing}: {alert}"
        )


def change_alert_paragraph(alert):
    """Paragraph for a category or region change alert."""
    entity_type, past_verb, present_verb = CHANGE_ALERT_TYPES[
        alert["alert_type"]
    ]
    data = alert["data"]

    if entity_type == "region":
        subject = f"{alert['entity']} region"
    else:
        subject = alert["entity"]

    return (
        f"{subject} {past_verb} by {format_pct(data['change_pct'])} "
        f"in {alert['period']},\n"
        f"with GMV {present_verb} by {format_inr(data['change_amount'])} "
        f"compared with {data['previous_period']}.\n"
        f"GMV moved from {format_inr(data['previous_gmv'])} "
        f"to {format_inr(data['current_gmv'])}. "
        f"Severity: {alert['severity']}."
    )


def inactive_alert_paragraph(alert):
    """Paragraph for an inactive reseller alert."""
    data = alert["data"]

    return (
        f"Reseller {alert['entity']} ({data['reseller_name']}) in "
        f"{data['city']} ({data['region']}) had no delivered orders\n"
        f"during the monitoring period.\n"
        f"Delivered orders: {format_count(data['delivered_orders'])}, "
        f"GMV: {format_inr(data['gmv'])}. "
        f"Severity: {alert['severity']}."
    )


def alert_paragraph(alert):
    _check_alert(alert)

    if alert["alert_type"] in CHANGE_ALERT_TYPES:
        return change_alert_paragraph(alert)

    return inactive_alert_paragraph(alert)


def header_paragraph(alerts):
    """Header with alert counts. Counting alerts is not a business metric."""
    category = sum(1 for a in alerts if a["entity_type"] == "category")
    region = sum(1 for a in alerts if a["entity_type"] == "region")
    inactive = sum(1 for a in alerts if a["entity_type"] == "reseller")

    return "\n".join([
        REPORT_TITLE,
        f"Monitoring period: {MONITORING_PERIOD_LABEL}",
        f"Total alerts: {format_count(len(alerts))}",
        f"Category alerts: {format_count(category)}",
        f"Regional alerts: {format_count(region)}",
        f"Inactive reseller alerts: {format_count(inactive)}",
    ])


def _section_title(alert):
    entity_type = alert["entity_type"]

    if entity_type == "category":
        return f"{alert['period']} Category Update"
    if entity_type == "region":
        return f"{alert['period']} Regional Update"

    return "Inactive Reseller"


def generate_report(alerts):
    """Return the full report text for a list of verified alerts."""
    for alert in alerts:
        _check_alert(alert)

    paragraphs = [header_paragraph(alerts)]

    if not alerts:
        paragraphs.append("No alerts were generated for this period.")
        return "\n\n".join(paragraphs) + "\n"

    # Group by section, keeping the order alerts first appear in,
    # but always list category, then regional, then inactive sections.
    sections = {}
    for alert in alerts:
        sections.setdefault(_section_title(alert), []).append(alert)

    rank = {"category": 0, "region": 1, "reseller": 2}
    ordered_titles = sorted(
        sections,
        key=lambda t: rank[sections[t][0]["entity_type"]],
    )

    for title in ordered_titles:
        paragraphs.append(title)
        for alert in sections[title]:
            paragraphs.append(alert_paragraph(alert))

    return "\n\n".join(paragraphs) + "\n"
