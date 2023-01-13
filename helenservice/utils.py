import calendar
from datetime import date

def get_month_date_range_by_date(date_param: date) -> tuple[date, date]:
    """
    Get the start date and end date of the month of the given date.
    """
    wanted_month_first_day = date_param.replace(day=1)
    wanted_month_last_day = date_param.replace(day=calendar.monthrange(wanted_month_first_day.year, wanted_month_first_day.month)[-1])

    return wanted_month_first_day, wanted_month_last_day