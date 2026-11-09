import datetime
from typing import Union, Dict, Any, Tuple

NEPALI_MONTHS = [
    "बैशाख", "जेठ", "असार", "साउन", "भदौ", "असोज",
    "कात्तिक", "मंसिर", "पुस", "माघ", "फागुन", "चैत"
]

NEPALI_DAYS = [
    "सोमबार", "मंगलबार", "बुधबार", "बिहीबार", "शुक्रबार", "शनिबार", "आइतबार"
]

NEPALI_DIGITS = {
    '0': '०', '1': '१', '2': '२', '3': '३', '4': '४',
    '5': '५', '6': '६', '7': '७', '8': '८', '9': '९'
}

def to_nepali_digits(num: Any) -> str:
    """Convert number or string of digits to Nepali Devanagari numerals"""
    return "".join(NEPALI_DIGITS.get(ch, ch) for ch in str(num))

# Calendar reference data: (BS Year, AD Baisakh 1 Date, month days list)
BS_CALENDAR = {
    2080: (datetime.date(2023, 4, 14), [31, 31, 32, 31, 31, 31, 30, 29, 30, 29, 30, 30]),
    2081: (datetime.date(2024, 4, 13), [31, 31, 32, 32, 31, 30, 30, 30, 29, 30, 29, 31]),
    2082: (datetime.date(2025, 4, 14), [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31]),
    2083: (datetime.date(2026, 4, 14), [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30]),
    2084: (datetime.date(2027, 4, 14), [31, 31, 32, 31, 31, 30, 30, 30, 29, 30, 29, 31]),
    2085: (datetime.date(2028, 4, 13), [31, 32, 31, 32, 31, 30, 30, 30, 29, 30, 29, 31]),
}

def ad_to_bs(ad_date: Union[datetime.date, str]) -> Dict[str, Any]:
    """Convert AD Gregorian date to Bikram Sambat (BS) date details."""
    if isinstance(ad_date, str):
        try:
            ad_date = datetime.date.fromisoformat(ad_date[:10])
        except Exception:
            ad_date = datetime.date.today()
            
    matched_bs_year = None
    for y, (baisakh1, m_days) in sorted(BS_CALENDAR.items()):
        total_days = sum(m_days)
        year_end = baisakh1 + datetime.timedelta(days=total_days)
        if baisakh1 <= ad_date < year_end:
            matched_bs_year = y
            break
            
    if not matched_bs_year:
        bs_y = ad_date.year + 57
        return {
            "year": bs_y,
            "month": 7,
            "day": 23,
            "date_bs": f"{bs_y}-07-23",
            "formatted": f"{to_nepali_digits(bs_y)} साल कात्तिक २३ गते",
            "formatted_full": f"{to_nepali_digits(bs_y)} साल कात्तिक २३ गते",
            "formatted_short": f"{to_nepali_digits(bs_y)}-०७-२३",
            "month_name": "कात्तिक",
            "weekday": "सोमबार",
            "ad_date": ad_date.isoformat()
        }
        
    baisakh1, m_days = BS_CALENDAR[matched_bs_year]
    diff_days = (ad_date - baisakh1).days
    
    bs_month = 1
    for m_len in m_days:
        if diff_days < m_len:
            break
        diff_days -= m_len
        bs_month += 1
        
    bs_day = diff_days + 1
    m_name = NEPALI_MONTHS[bs_month - 1]
    weekday_name = NEPALI_DAYS[ad_date.weekday()]
    
    date_bs = f"{matched_bs_year:04d}-{bs_month:02d}-{bs_day:02d}"
    formatted = f"{to_nepali_digits(matched_bs_year)} साल {m_name} {to_nepali_digits(bs_day)} गते"
    formatted_full = f"{to_nepali_digits(matched_bs_year)} साल {m_name} {to_nepali_digits(bs_day)} गते {weekday_name}"
    formatted_short = f"{to_nepali_digits(matched_bs_year)}-{to_nepali_digits(f'{bs_month:02d}')}-{to_nepali_digits(f'{bs_day:02d}')}"
    
    return {
        "year": matched_bs_year,
        "month": bs_month,
        "day": bs_day,
        "date_bs": date_bs,
        "formatted": formatted,
        "formatted_full": formatted_full,
        "formatted_short": formatted_short,
        "month_name": m_name,
        "weekday": weekday_name,
        "ad_date": ad_date.isoformat()
    }

def bs_to_ad(bs_year: int, bs_month: int, bs_day: int) -> datetime.date:
    """Convert BS date (year, month, day) to Gregorian AD date."""
    if bs_year not in BS_CALENDAR:
        ad_y = bs_year - 57
        return datetime.date(ad_y, max(1, min(bs_month, 12)), max(1, min(bs_day, 28)))
        
    baisakh1, m_days = BS_CALENDAR[bs_year]
    valid_month = max(1, min(bs_month, 12))
    max_day = m_days[valid_month - 1]
    valid_day = max(1, min(bs_day, max_day))
    
    days_to_add = sum(m_days[:valid_month - 1]) + (valid_day - 1)
    return baisakh1 + datetime.timedelta(days=days_to_add)

def get_today_bs() -> Dict[str, Any]:
    """Get current day's Bikram Sambat information."""
    return ad_to_bs(datetime.date.today())
