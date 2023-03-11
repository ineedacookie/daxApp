from datetime import date, timedelta


def get_pay_period_dates(pay_period_type, period_begin_date):
    # Get today's date
    begin_date = None
    end_date = None
    today = date(2023, 3, 8)
    ignore_last_day = timedelta(days=1)

    # Determine the length of the pay period
    if pay_period_type == 'w':
        # Weekly pay period
        delta = timedelta(weeks=1)
    elif pay_period_type == 'b':
        # Bi-weekly pay period
        delta = timedelta(weeks=2)
    elif pay_period_type == 's':
        if today.day > 15:
            begin_date = date(today.year, today.month, 16)
            year = begin_date.year
            month = begin_date.month
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1
            end_date = date(year, month, 1) - ignore_last_day
        else:
            begin_date = date(today.year, today.month, 1)
            end_date = date(today.year, today.month, 15)
    elif pay_period_type == 'm':
        # Monthly pay period
        if not period_begin_date:
            period_begin_date = date(today.year, today.month, 1)

        days_adjust = period_begin_date.day - 1

        begin_date = date(today.year, today.month, 1)
        begin_date = begin_date + timedelta(days=days_adjust)
        if begin_date > today:
            year = begin_date.year
            month = begin_date.month
            if month == 1:
                year -= 1
                month = 12
            else:
                month -= 1

            begin_date = date(year, month, begin_date.day)

        year = begin_date.year
        month = begin_date.month
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        end_date = date(year, month, 1) - ignore_last_day
        end_date = end_date + timedelta(days=days_adjust)
    else:
        raise ValueError("Invalid pay period type")

    if begin_date is None and end_date is None:
        # Calculate the begin and end dates of the pay period
        end_date = period_begin_date + delta - ignore_last_day
        while end_date <= today:
            end_date = end_date + delta

        begin_date = end_date - delta + ignore_last_day

    return begin_date, end_date