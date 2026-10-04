def format_inr(value):
    """Format a rupee amount, e.g. 92270.0 -> '\u20b992,270'.

    Whole-number amounts are shown without decimals. A value with a
    fractional part keeps two decimals instead of being silently rounded.
    """
    value = abs(float(value))

    if value == int(value):
        return f"\u20b9{int(value):,}"

    return f"\u20b9{value:,.2f}"


def format_pct(value):
    """Format a percentage magnitude, e.g. -18.84 -> '18.84%'."""
    return f"{abs(float(value)):.2f}%"


def format_count(value):
    return f"{int(value):,}"
