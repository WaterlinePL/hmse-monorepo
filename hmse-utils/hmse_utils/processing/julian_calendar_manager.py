import datetime


def float_to_julian(day_num: float) -> float:
    return round(day_num % 365, 2)  # Simplification: 365 days in year


# This is used to determine first day of simulation, here we can detect leap years
def date_to_julian(date: str):
    # Format: M/D/YYYY
    fmt = "%m/%d/%Y"
    dt = datetime.datetime.strptime(date, fmt)
    return dt.timetuple().tm_yday - 1   # [0, 364]
