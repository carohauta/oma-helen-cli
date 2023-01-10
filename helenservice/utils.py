import calendar
from datetime import date, datetime

def get_month_date_range_by_date(date: date) -> tuple[date, date]:
    """
    Get the start date and end date of the month of the given date.
    """
    wanted_month_first_day = datetime.today().replace(day=1, month=date.month)
    wanted_month_last_day = datetime.today().replace(day=calendar.monthrange(wanted_month_first_day.year, date.month)[-1], month=date.month)

    return wanted_month_first_day.date(), wanted_month_last_day.date()