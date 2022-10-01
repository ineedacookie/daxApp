import logging
from calendar import monthrange
from datetime import timedelta, date, datetime
from django.contrib import messages

import pytz
from django.shortcuts import render
from users.models import CustomUser  # Correct syntax

from .forms import ReportsForm
from .models import InOutTimeActions

SECONDS_IN_HOUR = 3600


class AssumedTimeAction:
    action_datetime = None
    type = None
    comment = None


def convert_front_end_date_to_utc(input_date, correct_timezone):
    new_date = input_date.replace(tzinfo=None)
    new_date = correct_timezone.localize(new_date).astimezone(pytz.utc)
    return new_date


def get_day_range_in_timezone(current_date, correct_timezone=pytz.utc):
    begin_date = correct_timezone.localize(current_date.replace(hour=0, minute=0, second=0, tzinfo=None)).astimezone(pytz.utc)
    end_date = correct_timezone.localize(current_date.replace(hour=23, minute=59, second=59, tzinfo=None)).astimezone(pytz.utc)
    return [begin_date, end_date]


def get_month_range_in_timezone(current_date, correct_timezone=pytz.utc):
    month_range = monthrange(current_date.year, current_date.month)
    begin_date = correct_timezone.localize(current_date.replace(day=1, hour=0, minute=0, second=0, tzinfo=None)).astimezone(pytz.utc)
    end_date = correct_timezone.localize(current_date.replace(day=month_range[1], hour=23, minute=59, second=59, tzinfo=None)).astimezone(pytz.utc)
    return [begin_date, end_date]


def get_timezone(user, employee=None):
    company_timezone = user.company.timezone
    dis_emp_time_in_their_timezone = user.company.display_employee_times_with_timezone
    if user.company.use_company_timezone:
        return_timezone = company_timezone
    elif dis_emp_time_in_their_timezone and employee and employee.timezone:
        return_timezone = employee.timezone
    else:
        if user.timezone:
            return_timezone = user.timezone
        else:
            return_timezone = company_timezone
    if not return_timezone:
        return_timezone = pytz.utc
    return return_timezone


def generate_report(request, page, page_arguments, correct_timezone = None):
    extends = page_arguments['extended_file']
    user_employee = page_arguments['user_employee']
    if not user_employee:
        origional_form = ReportsForm(request.POST, company=request.user.company)
    else:
        origional_form = ReportsForm(request.POST, company=request.user.company, user=request.user)
    if origional_form.is_valid():
        form = origional_form.cleaned_data
        """Grab employee list"""
        employee_list, employee_id_list = get_employee_list(request.user.company, form['selected_employees_list'])

        if not employee_list:
            logging.error("An invalid request to generate a report was received no employees selected")
            messages.warning(request, 'No employees selected')
            page_arguments['form'] = origional_form
            page_arguments['company'] = request.user.company
            page_arguments['extended_file'] = extends
            page_arguments['user_employee'] = user_employee
            page_arguments['correct_timezone'] = correct_timezone
            return render(request, page, page_arguments)

        """Get the correct timezone for the report"""
        if not correct_timezone:
            correct_timezone = get_timezone(request.user)

        """Grab time actions for date range"""
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(form, employee_id_list,
                                                                                request.user.company, correct_timezone)

        report_engine = Report(employee_list, time_actions_list, form, full_beg_date, full_end_date,
                               request.user.company, correct_timezone)

        page_arguments = report_engine.make_detailed_hours_report()

        """if there are no errors then pass link to the report and pass the page arguments. otherwise send errors to the forms page"""
        if not page_arguments['error']:
            page = form['report_type']
        else:
            if user_employee:
                messages.error(request, "Please contact your supervisor to fix the errors below")
            else:
                messages.error(request, "Please fix the errors below")
            page_arguments['form'] = origional_form
        page_arguments['company'] = request.user.company
        page_arguments['extended_file'] = extends
        page_arguments['user_employee'] = user_employee
        page_arguments['correct_timezone'] = correct_timezone
        return render(request, page, page_arguments)
    else:
        logging.error("An invalid request to generate a report was received")
        messages.warning(request, 'Please fix the error below')
        page_arguments['form'] = origional_form
        page_arguments['company'] = request.user.company
        page_arguments['extended_file'] = extends
        page_arguments['user_employee'] = user_employee
        page_arguments['correct_timezone'] = correct_timezone
        return render(request, page, page_arguments)


def get_employee_list(company, employee_ids):
    if '-1' in employee_ids:
        employee_list = CustomUser.objects.filter(company=company).exclude(
            role="c").values('id', 'first_name', 'middle_name',
                             'last_name').order_by('last_name',
                                                               'first_name')
    else:
        employee_list = CustomUser.objects.filter(company=company).filter(id__in=employee_ids).values('id',
                                                                                                      'first_name',
                                                                                                      'middle_name',
                                                                                                      'last_name').order_by(
            'last_name',
            'first_name')

    employee_id_list = []
    for employee in employee_list:
        employee_id_list.append(employee['id'])

    return employee_list, employee_id_list


def get_time_actions_list(form, employee_id_list, company, correct_timezone):
    full_beg_date, full_end_date = get_date_range(company.week_start_day, form['begin_date'], form['end_date'])
    filter_beg_date = convert_front_end_date_to_utc(full_beg_date, correct_timezone)
    filter_end_date = convert_front_end_date_to_utc(full_end_date, correct_timezone)
    time_actions_list = InOutTimeActions.objects.filter(user__in=employee_id_list).filter(
        date__range=[filter_beg_date, filter_end_date]).order_by('user', 'start')
    return full_beg_date.date(), full_end_date.date(), time_actions_list


class Report:
    def __init__(self, employee_list, time_actions_list, form, full_beg_date, full_end_date, company_settings,
                 correct_timezone):
        self.employee_list = employee_list
        self.time_actions_list = time_actions_list
        self.form = form
        self.full_beg_date = full_beg_date
        self.full_end_date = full_end_date
        self.company_settings = company_settings
        self.correct_timezone = correct_timezone

    def create_report_dict(self):
        """This function builds a dictionary that organizes employee times so it can be displayed on the report.

        Organization is like such
        return_dict = {
            employees: [
                {
                    name: 'last_name, first_name'
                    weeks: [
                        {
                            days: [
                                {
                                    date: datetime object,
                                    print_actions:[
                                        type + time string ex 'In 09:10 AM',
                                        ... additional actions
                                    ]
                                    previous: Boolean,
                                    total: Float,
                                    break: Float,
                                    overtime: Float,
                                    daily_overtime: Float,
                                    double_time: Float,
                                    total_with_break: Float,
                                    str_* for all float fields, replace * with the name of the field
                                },
                                ...     additional days
                            ],
                            start: datetime object,
                            end: datetime object,
                            total: Float,
                            break: Float,
                            overtime: Float,
                            previous_total: Float,
                            previous_breaks: Float,
                            previous_daily_overtime,
                            previous_double_time,
                            daily_overtime: Float,
                            weekly_overtime: Float,
                            double_time: Float,
                            total_with_break: Float,
                            regular: Float,
                            str_* for all float fields, replace * with the name of the field
                        },
                        ...     additional weeks
                    ],
                    total: Float,
                    break: Float,
                    overtime: Float,
                    daily_overtime: Float,
                    double_time: Float,
                    weekly_overtime: Float,
                    previous_total: Float,
                    previous_breaks: Float,
                    total_with_break: Float,
                    regular: Float,
                    str_* for all float fields, replace * with the name of the field
                },
                ...     additional employees
            ],

            total: Float,
            break: Float,
            overtime: Float,
            daily_overtime: Float,
            double_time: Float,
            weekly_overtime: Float,
            previous_total: Float,
            previous_breaks: Float,
            pay_total: float,
            total_with_break: Float,
            regular: Float,
            str_* for all float fields, replace * with the name of the field
        }

        """

        return_dict = {
            'date-range': (self.form['begin_date'].strftime('%m/%d/%y') + " - " + self.form['end_date'].strftime(
                '%m/%d/%y')),
            'employees': [],
            'form': self.form,
            'company': {'name': self.company_settings.name},
            'paid_breaks': self.company_settings.breaks_are_paid,
        }

        """Before the major lifting, we check to see if basic errors exist."""
        return_dict, self.time_actions_list = check_for_errors(self.employee_list, self.time_actions_list, return_dict,
                                                               self.correct_timezone)

        if return_dict['error']:
            return return_dict

        possible_weeks = []
        loop_date = self.full_beg_date
        while loop_date < self.full_end_date:
            possible_weeks.append({'start': loop_date, 'end': (loop_date + timedelta(days=6))})
            loop_date = loop_date + timedelta(days=7)

        employee_position = 0
        for employee in self.employee_list:
            employee_actions = self.time_actions_list[employee['id']]
            day_info = {}
            days = []
            week = 0  # this keeps track of what week we are on for actions
            week_info = {}
            weeks = []

            """Organize Time Actions into days, and weeks"""
            for time_action in employee_actions:
                """If day is already started"""
                if day_info:
                    """If the day has no changed then continue"""
                    if day_info['date'] == time_action.date.date():
                        day_info['actions'].append(time_action)
                    else:
                        """Otherwise add the day to the days array and calculate totals"""
                        days, day_info = self.add_day(days, day_info)

                        """Do we need to switch to a new week?"""
                        while not (possible_weeks[week]['start'] <= time_action.action_datetime.date() <=
                                   possible_weeks[week]['end']):
                            """If days, and first day info exists in week then add the week, this prevents against errors when there are no clock actions for the first week"""
                            if days and (
                                    possible_weeks[week]['start'] <= days[0]['date'] <= possible_weeks[week]['end']):
                                days, week_info, weeks = self.add_week(days, week_info, week, possible_weeks, weeks)
                            """Increment to a new week"""
                            week += 1
                        """Now add the existing clock action into the new day"""
                        day_info['date'] = time_action.action_datetime.date()
                        day_info['actions'] = []
                        day_info['actions'].append(time_action)

                        """If the date is from the previous week then mark the day as previous"""
                        if time_action.action_datetime.date() < self.form['begin_date']:
                            day_info['previous'] = True
                        else:
                            day_info['previous'] = False
                else:
                    """Otherwise just add the clock action"""
                    day_info['date'] = time_action.action_datetime.date()
                    day_info['actions'] = []
                    day_info['actions'].append(time_action)

                    """If the date is from the previous week then mark the day as previous"""
                    if time_action.action_datetime.date() < self.form['begin_date']:
                        day_info['previous'] = True
                    else:
                        day_info['previous'] = False

            """Apply the final day to our days array"""
            if day_info:
                days, day_info = self.add_day(days, day_info)

            """Apply the final week to our weeks array"""
            days, week_info, weeks, = self.add_week(days, week_info, week, possible_weeks, weeks)

            """Getting final totals for the employee"""
            emp_dict = return_dict['employees'][employee_position]
            emp_dict['weeks'] = weeks
            if self.form['other_hours_format'] == 'decimal':
                emp_dict['total'] = 0.0
                emp_dict['break'] = 0.0
                emp_dict['overtime'] = 0.0
                emp_dict['previous_total'] = 0.0
                emp_dict['previous_breaks'] = 0.0
                emp_dict['weekly_overtime'] = 0.0
                emp_dict['daily_overtime'] = 0.0
                emp_dict['double_time'] = 0.0
            else:
                emp_dict['total'] = 0
                emp_dict['break'] = 0
                emp_dict['overtime'] = 0
                emp_dict['previous_total'] = 0
                emp_dict['previous_breaks'] = 0
                emp_dict['weekly_overtime'] = 0
                emp_dict['daily_overtime'] = 0
                emp_dict['double_time'] = 0

            """ Get totals from the weeks compilied"""
            for week_info in weeks:
                emp_dict['total'] += week_info['total']
                emp_dict['break'] += week_info['break']
                emp_dict['previous_total'] += week_info['previous_total']
                emp_dict['previous_breaks'] += week_info['previous_breaks']
                try:
                    emp_dict['overtime'] += week_info['overtime']
                except Exception as e:
                    print(e)
                if self.company_settings.weekly_overtime:
                    emp_dict['weekly_overtime'] += week_info['weekly_overtime']
                if self.company_settings.daily_overtime:
                    emp_dict['daily_overtime'] += week_info['daily_overtime']
                if self.company_settings.double_time:
                    emp_dict['double_time'] += week_info['double_time']

            emp_dict['regular'] = emp_dict['total'] - emp_dict['overtime']
            if self.company_settings.double_time:
                emp_dict['regular'] = emp_dict['regular'] - emp_dict['double_time']
            emp_dict['total_with_break'] = emp_dict['total'] + emp_dict['break']

            emp_dict = self.convert_to_string(
                emp_dict, ['regular', 'total_with_break', 'total', 'previous_total',
                           'previous_breaks', 'overtime', 'daily_overtime',
                           'weekly_overtime', 'break'])

            return_dict['employees'][employee_position] = emp_dict
            employee_position += 1

        """Getting the final values for the whole report"""
        if self.form['other_hours_format'] == 'decimal':
            return_dict['total'] = 0.0
            return_dict['break'] = 0.0
            return_dict['overtime'] = 0.0
            return_dict['previous_total'] = 0.0
            return_dict['previous_breaks'] = 0.0
            return_dict['pay_total'] = 0.0
            return_dict['weekly_overtime'] = 0.0
            return_dict['daily_overtime'] = 0.0
            return_dict['double_time'] = 0.0
        else:
            return_dict['total'] = 0
            return_dict['break'] = 0
            return_dict['overtime'] = 0
            return_dict['previous_total'] = 0
            return_dict['previous_breaks'] = 0
            return_dict['pay_total'] = 0
            return_dict['weekly_overtime'] = 0
            return_dict['daily_overtime'] = 0
            return_dict['double_time'] = 0

        """Create string dates for the main dictionary"""
        return_dict['previous_begin_date'] = self.full_beg_date.strftime('%m/%d/%y')
        return_dict['begin_date'] = self.form['begin_date'].strftime('%m/%d/%y')
        return_dict['end_date'] = self.form['end_date'].strftime('%m/%d/%y')
        return_dict['todays_date'] = date.today().strftime('%m/%d/%y')
        return_dict['previous_date_range'] = self.full_beg_date.strftime('%m/%d/%y') + ' - ' + (
                self.form['begin_date'] - timedelta(days=1)).strftime('%m/%d/%y')

        """Cycle through all the employees and their times to get the report totals"""
        for final_employee in return_dict['employees']:
            return_dict['total'] += final_employee['total']
            return_dict['break'] += final_employee['break']
            return_dict['previous_total'] += final_employee['previous_total']
            return_dict['previous_breaks'] += final_employee['previous_breaks']
            return_dict['overtime'] += final_employee['overtime']
            if self.company_settings.weekly_overtime:
                return_dict['weekly_overtime'] += final_employee['weekly_overtime']
            if self.company_settings.daily_overtime:
                return_dict['daily_overtime'] += final_employee['daily_overtime']
            if self.company_settings.double_time:
                return_dict['double_time'] += final_employee['double_time']
            if self.form['display_grand_pay_total']:
                return_dict['pay_total'] += final_employee['pay_total']
        return_dict['regular'] = return_dict['total'] - return_dict['overtime']
        if self.company_settings.double_time:
            return_dict['regular'] = return_dict['regular'] - return_dict['double_time']
        return_dict['total_with_break'] = return_dict['total'] + return_dict['break']

        return_dict = self.convert_to_string(
            return_dict, ['regular', 'total_with_break', 'total', 'previous_total',
                          'previous_breaks', 'overtime', 'daily_overtime',
                          'weekly_overtime', 'break'])

        return return_dict

    def make_detailed_hours_report(self):
        """Creates a hours report"""
        return_dict = self.create_report_dict()
        return return_dict

    def add_day(self, days, day_info):
        """Otherwise add the day to the days array"""
        """Calculate day totals"""
        day_info['date_str'] = day_info['date'].strftime('%a %m/%d/%y')

        individual_actions = {}

        for action in day_info['actions']:
            if action.type == 't':
                start_str = 'In'
                end_str = 'Out'
            elif action.type == 'b':
                start_str = 'Begin Break',
                end_str = 'End Break',
            elif action.type == 'l':
                start_str = 'Begin Lunch',
                end_str = 'End Lunch',
            else:
                start_str = 'ERROR in add_day'
                end_str = 'ERROR in add_day'

            individual_actions[action.start] = start_str + action.start.strftime("%I:%M %p")
            individual_actions[action.end] = end_str + action.end.strftime("%I:%M %p")

        day_info['print_actions'] = []
        for i in sorted(individual_actions):
            day_info['print_actions'].append(individual_actions[i])

        self.calc_day_totals(day_info)
        day_info['actions'] = None

        days.append(day_info)
        day_info = {}
        return days, day_info

    def calc_day_totals(self, day_info):
        """Go through the actions and total up the daily total and break total for hourly and hour:minute"""
        if self.form['other_hours_format'] == 'decimal':
            day_info['total'] = 0.0
            day_info['break'] = 0.0
            day_info['overtime'] = 0.0
            day_info['daily_overtime'] = 0.0
            day_info['double_time'] = 0.0
        else:
            day_info['total'] = 0
            day_info['break'] = 0
            day_info['overtime'] = 0
            day_info['daily_overtime'] = 0
            day_info['double_time'] = 0

        for action in day_info['actions']:
            if action.type == 't':
                day_info['total'] += action.total_time
            elif action.type == 'b':
                day_info['break'] += action.total_time
                day_info['total'] -= action.total_time
            else:
                day_info['break'] += action.total_time
                day_info['total'] -= action.total_time

        """If daily overtime calculate overtime for the day, and possibly double time"""
        if self.company_settings.daily_overtime:
            """Adjust this if you want breaks to count towards overtime"""
            if self.company_settings.include_breaks_in_overtime_calculation:
                actual_time = day_info['total'] + day_info['break']
            else:
                actual_time = day_info['total']
            calc_daily_overtime_value = self.company_settings.daily_overtime_value
            if self.form['other_hours_format'] == 'hours_and_minutes':
                calc_daily_overtime_value = calc_daily_overtime_value * 60
            if actual_time > calc_daily_overtime_value:
                day_info['overtime'] = actual_time - calc_daily_overtime_value
            if self.company_settings.double_time:
                calc_double_time_value = self.company_settings.double_time_value
                if self.form['other_hours_format'] == 'hours_and_minutes':
                    calc_double_time_value = calc_double_time_value * 60
                if actual_time > calc_double_time_value:
                    day_info['double_time'] = actual_time - calc_double_time_value
                    day_info['overtime'] = day_info['overtime'] - day_info['double_time']
            day_info['daily_overtime'] = day_info['overtime']

        day_info['total_with_break'] = day_info['total'] + day_info['break']

        temp_day_info = self.convert_to_string(day_info,
                                               ['total', 'break', 'overtime', 'daily_overtime', 'double_time',
                                                'total_with_break'])

        return temp_day_info

    def convert_to_string(self, input_dict, list_of_keys):
        for key in list_of_keys:
            if self.form['other_hours_format'] == 'decimal':
                input_dict['str_' + key] = str(round(input_dict[key], 2))
            else:
                input_dict['str_' + key] = convert_minutes_to_hours_and_minutes(input_dict[key])
        return input_dict

    def add_week(self, days, week_info, week, possible_weeks, weeks):
        if days:
            week_info['begin_date'] = possible_weeks[week]['start'].strftime('%m/%d/%y')
            week_info['end_date'] = possible_weeks[week]['end'].strftime('%m/%d/%y')
            week_info['days'] = days
            if self.form['other_hours_format'] == 'decimal':
                week_info['total'] = 0.0
                week_info['regular'] = 0.0
                week_info['break'] = 0.0
                week_info['total_with_break'] = 0.0
                week_info['overtime'] = 0.0
                week_info['previous_total'] = 0.0
                week_info['previous_breaks'] = 0.0
                week_info['weekly_overtime'] = 0.0
                week_info['double_time'] = 0.0
                week_info['daily_overtime'] = 0.0
                week_info['previous_daily_overtime'] = 0.0
                week_info['previous_double_time'] = 0.0
            else:
                week_info['total'] = 0
                week_info['regular'] = 0
                week_info['break'] = 0
                week_info['total_with_break'] = 0
                week_info['overtime'] = 0
                week_info['previous_total'] = 0
                week_info['previous_breaks'] = 0
                week_info['weekly_overtime'] = 0
                week_info['double_time'] = 0
                week_info['daily_overtime'] = 0
                week_info['previous_daily_overtime'] = 0
                week_info['previous_double_time'] = 0

            """Total the regular hours and break hours"""
            for day in days:
                """If there are previous_hours account for the total and the breaks"""
                if day['previous']:
                    week_info['previous_total'] += day['total']
                    week_info['previous_breaks'] += day['break']
                else:
                    week_info['total'] += day['total']
                    week_info['break'] += day['break']

            """If daily overtime then calculate the total daily overtime for the week"""
            if self.company_settings.daily_overtime:
                for day in days:
                    if not day['previous']:
                        week_info['overtime'] += day['overtime']
                        week_info['daily_overtime'] += day['overtime']
                    else:
                        week_info['previous_daily_overtime'] += day['overtime']
                if self.company_settings.double_time:
                    for day in days:
                        if not day['previous']:
                            week_info['double_time'] += day['double_time']
                        else:
                            week_info['previous_double_time'] += day['double_time']

            """If weekly overtime then calculate the total weekly overtime for the week"""
            if self.company_settings.weekly_overtime:
                if self.company_settings.include_breaks_in_overtime_calculation:
                    actual_time = week_info['total'] + week_info['previous_total'] + week_info['break'] + week_info[
                        'previous_breaks']
                else:
                    actual_time = week_info['total'] + week_info['previous_total']

                """If daily overtime selected as well then calculate according to california laws"""
                if self.company_settings.daily_overtime:
                    """If double time make sure to account for it."""
                    if self.company_settings.double_time:
                        actual_time = actual_time - week_info['daily_overtime'] - week_info['double_time'] - week_info[
                            'previous_daily_overtime'] - week_info['previous_double_time']
                    else:
                        actual_time = actual_time - week_info['daily_overtime'] - week_info['previous_daily_overtime']
                """If the total hours pass the overtime threshold after all our adjustments then calculate weekly overtime."""
                calc_weekly_overtime_value = self.company_settings.weekly_overtime_value
                if self.form['other_hours_format'] == 'hours_and_minutes':
                    calc_weekly_overtime_value = calc_weekly_overtime_value * 60

                if actual_time > calc_weekly_overtime_value:
                    overtime_total = actual_time - calc_weekly_overtime_value
                    week_info[
                        'weekly_overtime'] = overtime_total
                    week_info['overtime'] += overtime_total
            days = []
        """Then add the week to the weeks array"""
        if week_info:
            week_info['regular'] = week_info['total'] - week_info['overtime']
            if self.company_settings.double_time:
                week_info['regular'] = week_info['regular'] - week_info['double_time']
            week_info['total_with_break'] = week_info['total'] + week_info['break']

            week_info = self.convert_to_string(week_info, ['regular', 'total_with_break', 'total', 'previous_total',
                                                           'previous_breaks', 'previous_daily_overtime',
                                                           'previous_double_time', 'overtime', 'daily_overtime',
                                                           'weekly_overtime', 'break'])
            week_info['number'] = week + 1
            weeks.append(week_info)
            week_info = {}
        return days, week_info, weeks

    def add_action(self, action, prev_action):
        """Cleans up actions and complies information about action pairs"""
        a_type = 'clock'
        if prev_action.type == 'i':
            prev_text = "In " + prev_action.action_datetime.strftime("%I:%M %p")
        elif prev_action.type == 'b':
            a_type = 'break'
            prev_text = "Begin Break " + prev_action.action_datetime.strftime("%I:%M %p")
        else:
            a_type = 'error'
            prev_text = "Error " + prev_action.action_datetime.strftime("%I:%M %p")

        if action.type == 'o':
            action_text = "Out " + action.action_datetime.strftime("%I:%M %p")
        elif action.type == 'e':
            action_text = "End Break " + action.action_datetime.strftime("%I:%M %p")
        else:
            action_text = "Error " + action.action_datetime.strftime("%I:%M %p")

        action_total = (
                               action.action_datetime.timestamp() - prev_action.action_datetime.timestamp()) / SECONDS_IN_HOUR
        append_dict = {'type': a_type,
                       'first_action': prev_text,
                       'second_action': action_text,
                       'comments': self.capture_comments(prev_action, action)}

        if self.form['other_hours_format'] == 'decimal':
            append_dict['total'] = round(action_total, 2)
            append_dict['str_total'] = str(round(action_total, 2))
        else:
            append_dict['total'] = int(self.form['other_rounding']) * round(
                action_total * 60 / int(self.form['other_rounding']))
            append_dict['str_total'] = convert_minutes_to_hours_and_minutes(append_dict['total'])
        return append_dict

    def capture_comments(self, first_action, second_action):
        comments = []
        if first_action.comment:
            comments.append(first_action.comment)
        if second_action.comment:
            comments.append(second_action.comment)
        return comments


def check_for_errors(employee_list, time_actions_list, return_dict, correct_timezone=pytz.utc):
    """This function goes through all employees and checks the time actions against each other making sure there are no errors
    If there is an error then it will add it to a list of errors and pass useful information for tracking down the information."""

    error_detected = False

    updated_time_actions_list_times = {}

    for employee in employee_list:
        employee_actions = time_actions_list.filter(user=employee['id'])
        full_name = employee['last_name'] + ', ' + employee['first_name']
        if employee['middle_name']:
            full_name += " " + employee['middle_name']
        return_dict['employees'].append({'name': full_name})
        errors = []
        updated_time_actions_list_times[employee['id']] = []

        """Simple test of integrity, This should catch possible errors before trying to total a persons times."""
        prev_action = None
        for time_action in employee_actions:
            time_action.action_datetime = time_action.action_datetime.astimezone(correct_timezone)
            if prev_action:
                if time_action.type == prev_action.type:
                    """If the previous time action matches the time actions type raise error"""
                    errors.append({"Error": "Duplicate time actions", 'action': prev_action, 'employee': employee,
                                   'link_date': prev_action.action_datetime.strftime('%Y%m%d'),
                                   'print_date': prev_action.action_datetime.strftime('%b %d, %Y %I:%M %p')})
                    error_detected = True
                elif time_action.type == 'b' and not prev_action.type == 'i':
                    errors.append({"Error": "Break started when employee is not clocked in", 'action': prev_action,
                                   'employee': employee, 'link_date': prev_action.action_datetime.strftime('%Y%m%d'),
                                   'print_date': prev_action.action_datetime.strftime('%b %d, %Y %I:%M %p')})
                    error_detected = True
                elif time_action.type == 'e' and not prev_action.type == 'b':
                    errors.append({"Error": "Break ended when there was no break start", 'action': prev_action,
                                   'employee': employee, 'link_date': prev_action.action_datetime.strftime('%Y%m%d'),
                                   'print_date': prev_action.action_datetime.strftime('%b %d, %Y %I:%M %p')})
                    error_detected = True
                elif time_action.type == 'o' and prev_action.type == 'b':
                    errors.append({"Error": "Clocked out when there was no break end", 'action': prev_action,
                                   'employee': employee, 'link_date': prev_action.action_datetime.strftime('%Y%m%d'),
                                   'print_date': prev_action.action_datetime.strftime('%b %d, %Y %I:%M %p')})
                    error_detected = True
                elif time_action.type == 'i' and not prev_action.type == 'o':
                    errors.append({"Error": "Clocked in when employee was not clocked out", 'action': prev_action,
                                   'employee': employee, 'link_date': prev_action.action_datetime.strftime('%Y%m%d'),
                                   'print_date': prev_action.action_datetime.strftime('%b %d, %Y %I:%M %p')})
                    error_detected = True
            prev_action = time_action
            updated_time_actions_list_times[employee['id']].append(time_action)

        """Attaching any errors to the employee"""
        return_dict['employees'][-1]['errors'] = errors
        return_dict['error'] = error_detected

    return return_dict, updated_time_actions_list_times


def get_date_range(week_start_day, begin_date, end_date):
    """This function expands the date range to fit the max number of weeks the range spans.
        This allows for accurate overtime calculations in regards to previous hours worked and overnight shifts"""

    week_start_day = week_start_day

    if week_start_day <= begin_date.weekday():
        new_begin_date = begin_date - timedelta(days=(begin_date.weekday() - week_start_day))
    else:
        new_begin_date = begin_date - timedelta(days=((7 - week_start_day) + begin_date.weekday()))

    if week_start_day > end_date.weekday():
        new_end_date = end_date + timedelta(days=(week_start_day - end_date.weekday() - 1))
    else:
        new_end_date = end_date - timedelta(days=(end_date.weekday() - (week_start_day + 6)))

    beg_time = datetime.min.time()
    end_time = datetime.max.time()

    return datetime.combine(new_begin_date, beg_time), datetime.combine(new_end_date, end_time)


def convert_minutes_to_hours_and_minutes(m):
    """This function receives minutes and converts it to hours and minutes in string format"""
    minute = m % 60
    hour = int(m / 60)
    return f"{hour}:{minute:02d}"
