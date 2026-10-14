"""
Tiny pure-Python Gregorian -> Jalali (Persian) calendar helpers.

No third-party dependency; based on the well-known 33-year-cycle algorithm.
"""

JALALI_MONTHS = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_persian_digits(value) -> str:
    """'2026' -> '۲۰۲۶'."""
    return str(value).translate(_PERSIAN_DIGITS)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_days_before_month = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        (365 * gy)
        + ((gy2 + 3) // 4)
        - ((gy2 + 99) // 100)
        + ((gy2 + 399) // 400)
        - 80
        + gd
        + g_days_before_month[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def format_jalali(value, style: str = "long") -> str:
    """
    Format a date/datetime (already in the desired time zone).

    style="long"  -> '۱۹ مهر ۱۴۰۵'
    style="short" -> '۱۴۰۵/۰۷/۱۹'
    """
    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    if style == "short":
        return to_persian_digits(f"{jy:04d}/{jm:02d}/{jd:02d}")
    return f"{to_persian_digits(jd)} {JALALI_MONTHS[jm - 1]} {to_persian_digits(jy)}"
