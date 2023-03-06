import logging
import os
from io import BytesIO
from datetime import timedelta, date, datetime
from django.contrib import messages
from django.utils import timezone
from django.template.loader import get_template
from string import capwords

from django.shortcuts import render
from users.models import CustomUser
from middleware.timezone import get_timezone
from xhtml2pdf import pisa
from daxApp.settings import S3_CLIENT, S3_BUCKET_NAME

from .forms import ReportsForm
from .models import InOutAction, TTCompanyInfo, TTUserInfo, TTReports
from daxApp.encryption import encrypt_id, decrypt_id


SECONDS_IN_HOUR = 3600

from django.http import HttpResponse


def generate_report(request):
    # Get the template
    template = get_template('report_template.html')

    # Render the template with context
    context = {'foo': 'bar'}
    html = template.render(context)

def generate_report(request, page, page_arguments, override_timezone=None):
    if not override_timezone and request.user.company.use_company_timezone:
        override_timezone = get_timezone(request.user)

    original_form = ReportsForm(request.POST, company=request.user.company, user=request.user)
    if original_form.is_valid():
        form = original_form.cleaned_data
        """Grab employee list"""
        employee_list, employee_id_list = get_employee_list(request.user.company, form['selected_employees_list'])

        if not employee_list:
            logging.error("An invalid request to generate a report was received no employees selected")
            messages.warning(request, 'No employees selected')
            page_arguments['form'] = original_form
            return render(request, page, page_arguments)

        """Get the company time tracker info"""
        company_info = TTCompanyInfo.objects.get(company=request.user.company)

        """Grab time actions for date range"""
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(form, employee_id_list,
                                                                                company_info, override_timezone)

        report_engine = Report(employee_list, time_actions_list, form, full_beg_date, full_end_date,
                               request.user.company, company_info, override_timezone)

        page_arguments = report_engine.make_detailed_hours_report()

        """if there are no errors then pass link to the report and pass the page arguments. otherwise send errors to the forms page"""
        if not page_arguments.get('error', None):
            page = form['report_type']
        else:
            page_arguments['form'] = original_form
        template = get_template(page)
        html = template.render(page_arguments)
        pdf_file = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), pdf_file)
        with open('test.pdf', 'wb') as out_file:
            out_file.write(pdf_file.getvalue())
        if form['report_type'] == 'time_tracker/reports/detailed_hours.html':
            report_type = 'Detailed Hours Report'
            report_folder = 'detailed'
        else:
            report_type = 'Unknown'
            report_folder = 'unknown'

        rep_obj = TTReports.objects.create(user=request.user,
                                 report_name=report_type + ' ' + page_arguments['date-range'],
                                           folder=report_folder)
        rep_obj.save()
        report_path = rep_obj.report_path()

        pdf_file.seek(0)    # Reset the location to the beginning of the pdf_file
        S3_CLIENT.upload_fileobj(pdf_file, S3_BUCKET_NAME, report_path)
        presigned_url = S3_CLIENT.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': report_path
            },
            ExpiresIn=60*5 #5 minutes
        )
        print(presigned_url)

        return render(request, page, page_arguments)
    else:
        logging.error("An invalid request to generate a report was received")
        messages.warning(request, 'Please fix the error below')
        page_arguments['form'] = original_form
        return render(request, page, page_arguments)


def get_employee_list(company, employee_ids):
    if '-1' in employee_ids:
        employee_list = TTUserInfo.objects.filter(user__company=company).order_by('user__last_name', 'user__first_name')
    else:
        temp_id_list = []
        for i in employee_ids:
            temp_id_list.append(i)
        employee_list = TTUserInfo.objects.filter(user__company=company, user__id__in=temp_id_list).order_by('user__last_name', 'user__first_name')

    employee_id_list = []
    for employee in employee_list:
        employee_id_list.append(employee.user.id)

    return employee_list, employee_id_list


def get_time_actions_list(form, employee_id_list, company_info, override_timezone):
    full_beg_date, full_end_date = get_date_range(company_info.week_start_day, form['begin_date'], form['end_date'])
    filter_beg_date = convert_front_end_date_to_utc(full_beg_date, override_timezone)
    if not override_timezone:
        # grabbing one extra day so we can widen the scope and get all employees whose timezones say they are in the date range.
        filter_beg_date = filter_beg_date - timedelta(days=1)
    filter_end_date = convert_front_end_date_to_utc(full_end_date, override_timezone)
    if not override_timezone:
        # grabbing one extra day so we can widen the scope and get all employees whose timezones say they are in the date range.
        filter_end_date = filter_end_date + timedelta(days=1)
    time_actions_list = InOutAction.objects.filter(user__in=employee_id_list, action_lookup_datetime__range=[filter_beg_date, filter_end_date]).order_by('user', 'action_lookup_datetime')
    return full_beg_date.date(), full_end_date.date(), time_actions_list


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


def convert_front_end_date_to_utc(input_date, override_timezone):
    # TODO i don't know if I can trust this
    new_date = input_date.replace(tzinfo=override_timezone)
    new_date = new_date.astimezone(timezone.utc)
    return new_date


class Report:
    def __init__(self, employee_list, time_actions_list, form, full_beg_date, full_end_date, company, company_info,
                 override_timezone):
        self.employee_list = employee_list
        self.time_actions_list = time_actions_list
        self.form = form
        self.full_beg_date = full_beg_date
        self.full_end_date = full_end_date
        self.company = company
        self.company_info = company_info
        self.override_timezone = override_timezone
        self.auto_inserted = False

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
                                    actions: [
                                        {
                                            action_id: Str,
                                            type: Char,
                                            start: datetime,
                                            end: datetime,
                                            first_action: type + time string ex 'In 09:10 AM',
                                            second_action: type + time string ex 'Out 10:10 AM',
                                            comment: Str,
                                            temp_start: Bool,
                                            temp_end: Bool,
                                            total: Float,
                                            str_total: total stringified, if hour minute = 'H:MM' else 'H.hh'
                                        }
                                        ...   additional actions
                                    ],
                                    previous: Boolean,
                                    total: Float,
                                    break: Float,
                                    overtime: Float,
                                    daily_overtime: Float,
                                    double_time: Float,
                                    total_with_break: Float,
                                    str_* for all float fields, replace * with the name of the field
                                    date_str: str
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
                            str_* for all float fields, replace * with the name of the field,
                            begin_date: str,
                            end_date: str,
                            number: int   # the week number
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
                    str_* for all float fields, replace * with the name of the field,
                    timezone: str,
                    paid_breaks: Bool,
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
            total_with_break: Float,
            regular: Float,
            str_* for all float fields, replace * with the name of the field
            previous_begin_date: Str,
            begin_date: Str,
            end_date: Str,
            todays_date: Str,
            previous_date_range: Str,
            auto_inserted: Bool,
        }

        """

        return_dict = {
            'date-range': (self.form['begin_date'].strftime('%m/%d/%y') + " - " + self.form['end_date'].strftime(
                '%m/%d/%y')),
            'employees': [],
            'form': self.form,
            'company': {'name': self.company.name},
            'daily_overtime_s': self.company_info.default_daily_overtime,
            'double_time_s': self.company_info.default_double_time,
            'weekly_overtime_s': self.company_info.default_weekly_overtime,
            'paid_breaks': self.company_info.default_breaks_are_paid,
        }

        possible_weeks = []
        loop_date = self.full_beg_date
        while loop_date < self.full_end_date:
            possible_weeks.append({'start': loop_date, 'end': (loop_date + timedelta(days=6))})
            loop_date = loop_date + timedelta(days=7)

        for employee in self.employee_list:
            if self.override_timezone:
                employee_timezone = self.override_timezone
            else:
                employee_timezone = get_timezone(employee.user)

            # get employee specific settings if necessary
            tt_settings = self.get_tt_settings(employee)

            # toggle true on daily, weekly overtimes and double time so they show up on reports if they are ever used.
            if not self.company_info.use_company_defaults_for_all_employees:
                for i in ['daily_overtime_s', 'double_time_s', 'weekly_overtime_s', 'paid_breaks']:
                    if tt_settings[i]:
                        return_dict[i] = tt_settings[i]

            days, weeks = self.organize_days_weeks(employee, employee_timezone, possible_weeks, tt_settings)

            """Getting final totals for the employee"""
            emp_dict = {
                'name': capwords(employee.user.full_name),
                'timezone': str(employee_timezone),
                'weeks': weeks,
                'paid_breaks': tt_settings['paid_breaks']
            }
            return_dict['employees'].append(emp_dict)
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
                if tt_settings['weekly_overtime_s']:
                    emp_dict['weekly_overtime'] += week_info['weekly_overtime']
                if tt_settings['daily_overtime_s']:
                    emp_dict['daily_overtime'] += week_info['daily_overtime']
                if tt_settings['double_time_s']:
                    emp_dict['double_time'] += week_info['double_time']

            emp_dict['regular'] = emp_dict['total'] - emp_dict['overtime']
            if tt_settings['double_time_s']:
                emp_dict['regular'] = emp_dict['regular'] - emp_dict['double_time']
            emp_dict['total_with_break'] = emp_dict['total'] + emp_dict['break']

            self.convert_to_string(
                emp_dict, ['regular', 'total_with_break', 'total', 'previous_total',
                           'previous_breaks', 'overtime', 'daily_overtime',
                           'weekly_overtime', 'break'])

        """Getting the final values for the whole report"""
        if self.form['other_hours_format'] == 'decimal':
            return_dict['total'] = 0.0
            return_dict['break'] = 0.0
            return_dict['overtime'] = 0.0
            return_dict['previous_total'] = 0.0
            return_dict['previous_breaks'] = 0.0
            return_dict['weekly_overtime'] = 0.0
            return_dict['daily_overtime'] = 0.0
            return_dict['double_time'] = 0.0
            return_dict['total_with_break'] = 0.0
        else:
            return_dict['total'] = 0
            return_dict['break'] = 0
            return_dict['overtime'] = 0
            return_dict['previous_total'] = 0
            return_dict['previous_breaks'] = 0
            return_dict['weekly_overtime'] = 0
            return_dict['daily_overtime'] = 0
            return_dict['double_time'] = 0
            return_dict['total_with_break'] = 0

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
            if final_employee['paid_breaks']:
                return_dict['total_with_break'] += final_employee['total_with_break']
            else:
                return_dict['total_with_break'] += final_employee['total']
            if return_dict['weekly_overtime_s']:
                return_dict['weekly_overtime'] += final_employee['weekly_overtime']
            if return_dict['daily_overtime_s']:
                return_dict['daily_overtime'] += final_employee['daily_overtime']
            if return_dict['double_time_s']:
                return_dict['double_time'] += final_employee['double_time']
        return_dict['regular'] = return_dict['total'] - return_dict['overtime']
        if return_dict['double_time_s']:
            return_dict['regular'] = return_dict['regular'] - return_dict['double_time']

        self.convert_to_string(
            return_dict, ['regular', 'total_with_break', 'total', 'previous_total',
                          'previous_breaks', 'overtime', 'daily_overtime',
                          'weekly_overtime', 'break'])

        return_dict['auto_inserted'] = self.auto_inserted
        return return_dict

    def get_tt_settings(self, employee):
        """
        Get the overtime settings an any other time tracking settings that we need for each employee.
        """
        if self.company_info.use_company_defaults_for_all_employees:
            daily_overtime = self.company_info.default_daily_overtime
            daily_overtime_value = self.company_info.default_daily_overtime_value
            include_breaks_in_overtime_calculation = self.company_info.default_include_breaks_in_overtime_calculation
            double_time = self.company_info.default_double_time
            double_time_value = self.company_info.default_double_time_value
            weekly_overtime = self.company_info.default_weekly_overtime
            weekly_overtime_value = self.company_info.default_weekly_overtime_value
            breaks_are_paid = self.company_info.default_breaks_are_paid
            california_overtime = self.company_info.default_california_overtime
        else:
            daily_overtime = employee.daily_overtime
            daily_overtime_value = employee.daily_overtime_value
            include_breaks_in_overtime_calculation = employee.include_breaks_in_overtime_calculation
            double_time = employee.double_time
            double_time_value = employee.double_time_value
            weekly_overtime = employee.weekly_overtime
            weekly_overtime_value = employee.weekly_overtime_value
            breaks_are_paid = employee.breaks_are_paid
            california_overtime = employee.california_overtime
        return {
            'daily_overtime_s': daily_overtime,
            'daily_overtime_value': daily_overtime_value,
            'include_breaks_in_overtime_calculation': include_breaks_in_overtime_calculation,
            'double_time_s': double_time,
            'double_time_value': double_time_value,
            'weekly_overtime_s': weekly_overtime,
            'weekly_overtime_value': weekly_overtime_value,
            'california_overtime_s': california_overtime,
            'paid_breaks': breaks_are_paid,
        }

    def organize_days_weeks(self, employee, employee_timezone, possible_weeks, tt_settings):
        """Organize Time Actions into days, and weeks"""
        employee_actions = self.time_actions_list.filter(user=employee.user)
        cur_time = datetime.utcnow().astimezone(employee_timezone)
        day_info = {}
        days = []
        week = 0  # this keeps track of what week we are on for actions
        week_info = {}
        weeks = []

        action_objs = self.organize_employee_actions(cur_time, employee_actions, employee_timezone)

        for time_action in action_objs:
            """If day is already started"""
            ta_date = time_action['start'].date()
            if not (self.full_beg_date <= ta_date <= self.full_end_date):
                # skip this action since it is out of scope
                continue

            if day_info:
                """If the day has no changed then continue"""
                if day_info['date'] == ta_date:
                    day_info['actions'].append(time_action)
                else:
                    """Otherwise add the day to the days array and calculate totals"""
                    days, day_info = self.add_day(days, day_info, tt_settings)

                    """Do we need to switch to a new week?"""
                    while not (possible_weeks[week]['start'] <= ta_date <= possible_weeks[week]['end']):
                        """If days, and first day info exists in week then add the week, this prevents against errors when there are no clock actions for the first week"""
                        if days and (
                                possible_weeks[week]['start'] <= days[0]['date'] <= possible_weeks[week]['end']):
                            days, week_info, weeks = self.add_week(days, week_info, week, possible_weeks, weeks, tt_settings)
                        """Increment to a new week"""
                        week += 1
                    """Now add the existing clock action into the new day"""
                    day_info = self.create_new_day(ta_date, time_action)
            else:
                """Otherwise just add the clock action"""
                day_info = self.create_new_day(ta_date, time_action)

        """Apply the final day to our days array"""
        if day_info:
            days, day_info = self.add_day(days, day_info, tt_settings)

        """Apply the final week to our weeks array"""
        days, week_info, weeks, = self.add_week(days, week_info, week, possible_weeks, weeks, tt_settings)
        return days, weeks

    def create_new_day(self, ta_date, time_action):
        """
        Creates a new day object.
        """
        day_info = dict()
        day_info['date'] = ta_date
        day_info['actions'] = []
        day_info['actions'].append(time_action)

        """If the date is from the previous week then mark the day as previous"""
        if ta_date < self.form['begin_date']:
            day_info['previous'] = True
        else:
            day_info['previous'] = False
        return day_info

    def organize_employee_actions(self, cur_time, employee_actions, employee_timezone):
        """Organize action and handle for special cases like missing end dates or the start date and end date are on two different days."""
        action_objs = []
        employee_action_length = len(employee_actions)
        for index, time_action in enumerate(employee_actions):
            # handle if time action doesn't have an end date.
            action_id = encrypt_id(time_action.id)
            start = time_action.start
            end = time_action.end
            type = time_action.type
            total_time = time_action.total_time
            comment = time_action.comment

            # convert the times to the employees timezone or the company timezone if selected.
            start = start.astimezone(employee_timezone)
            if end:
                end = end.astimezone(employee_timezone)

            if start and end:
                if start.date() == end.date():
                    action_objs.append(self.create_action_entry(action_id, type, start, end, comment, None, False, False, total_time))
                else:
                    # the start and end dates are on two different days, we need to split at midnight
                    end2 = datetime.combine(start.date(), datetime.max.time()).replace(tzinfo=employee_timezone)
                    start2 = datetime.combine(end.date(), datetime.min.time()).replace(tzinfo=employee_timezone)
                    action_objs.append(
                        self.create_action_entry(action_id, type, start, end2, comment, '(Midnight Split)', False, True))
                    action_objs.append(
                        self.create_action_entry(action_id, type, start2, end, comment, '(Midnight Split)', True, False))
                    self.auto_inserted = True
            elif not end:
                temp_pos = index + 1
                while temp_pos < employee_action_length:
                    if type == employee_actions[temp_pos].type:
                        end = employee_actions[temp_pos].start.astimezone(employee_timezone)
                        break
                    temp_pos += 1
                if end:
                    if start.date() == end.date():
                        action_objs.append(
                            self.create_action_entry(action_id, type, start, end, comment, None, False, True, total_time))
                        self.auto_inserted = True
                    else:
                        # the start and end dates are on two different days, we need to split at midnight
                        end2 = datetime.combine(start.date(), datetime.max.time()).replace(tzinfo=employee_timezone)
                        start2 = datetime.combine(end.date(), datetime.min.time()).replace(tzinfo=employee_timezone)
                        action_objs.append(
                            self.create_action_entry(action_id, type, start, end2, comment, '(Midnight Split)', False,
                                                     True))
                        action_objs.append(
                            self.create_action_entry(action_id, type, start2, end, comment, '(Midnight Split)', True,
                                                     True))
                        self.auto_inserted = True
                else:
                    if start.date() == cur_time.date():
                        # use the cur time as the temporary end
                        end = cur_time
                        action_objs.append(
                            self.create_action_entry(action_id, type, start, end, comment, None, False, False))
                    else:
                        # the end date doesn't exist and the current date is not set. so lets generate two actions. one for the end of the day and one for the current day.
                        end_time = datetime.max.time()
                        end = datetime.combine(start.date(), end_time).replace(tzinfo=employee_timezone)
                        end2 = datetime.combine(cur_time.date(), end_time).replace(tzinfo=employee_timezone)
                        start2 = datetime.combine(cur_time.date(), datetime.min.time()).replace(
                            tzinfo=employee_timezone)
                        action_objs.append(
                            self.create_action_entry(action_id, type, start, end, comment, '(Midnight Split With Predicted End Date)', False,
                                                     True))
                        action_objs.append(
                            self.create_action_entry(action_id, type, start2, end2, comment, '(Midnight Split With Predicted End Date)', True,
                                                     True))
                        self.auto_inserted = True
            else:
                print("We shouldn't have gotten here")
        return sorted(action_objs, key=lambda x: x['start'])

    def create_action_entry(self, action_id, type, start, end, comment, additional_text, temp_start, temp_end, total_time=None):
        """
        Creates an action all formatted the way we need it to be.
        """
        type_dict = {
            'start': {
                't': "In",
                'b': "Start Break"
            },
            'end': {
                't': "Out",
                'b': "End Break"
            }
        }
        action_entry = {
            'action_id': action_id,
            'type': type,
            'start': start,
            'end': end,
            'first_action': type_dict['start'][type] + ' ' + start.strftime("%I:%M %p"),
            'second_action': type_dict['end'][type] + ' ' + end.strftime("%I:%M %p"),
            'comment': comment,
            'additional_text': additional_text,
            'temp_start': temp_start,
            'temp_end': temp_end
        }

        if total_time:
            # expecting it to be in seconds.
            total_time = total_time / SECONDS_IN_HOUR
        else:
            total_time = (end.timestamp() - start.timestamp()) / SECONDS_IN_HOUR

        if self.form['other_hours_format'] == 'decimal':
            action_entry['total'] = round(total_time, 2)
            action_entry['str_total'] = str(round(total_time, 2))
        else:
            action_entry['total'] = int(self.form['other_rounding']) * round(
                total_time * 60 / int(self.form['other_rounding']))
            action_entry['str_total'] = convert_minutes_to_hours_and_minutes(action_entry['total'])
        return action_entry

    def make_detailed_hours_report(self):
        """Creates a hours report"""
        return self.create_report_dict()

    def add_day(self, days, day_info, tt_settings):
        """Otherwise add the day to the days array"""
        """Calculate day totals"""
        cali_7th_day_qualified = False
        day_info['date_str'] = day_info['date'].strftime('%a %m/%d/%y')

        """If california overtime is enabled check if there are 7 consecutive days where the first 6 are more than 8 hours worked. If that is met then the first 8 hours of the 7th day is marked as double time."""
        if tt_settings['california_overtime_s'] and len(days) == 6:
            cali_7th_day_qualified = True
            hours = 8
            if self.form['other_hours_format'] == 'hours_and_minutes':
                hours = hours * 60
            for day in days:
                if not (day['total'] >= hours):
                    cali_7th_day_qualified = False
                    break
        if cali_7th_day_qualified:
            self.calc_day_totals(day_info, tt_settings, cal_overtime=8)
        else:
            self.calc_day_totals(day_info, tt_settings)

        days.append(day_info)
        day_info = {}
        return days, day_info

    def calc_day_totals(self, temp_day_info, tt_settings, cal_overtime=0):
        """Go through the actions and total up the daily total and break total for hourly and hour:minute"""
        if self.form['other_hours_format'] == 'decimal':
            temp_day_info['total'] = 0.0
            temp_day_info['break'] = 0.0
            temp_day_info['overtime'] = 0.0
            temp_day_info['daily_overtime'] = 0.0
            temp_day_info['double_time'] = 0.0
        else:
            temp_day_info['total'] = 0
            temp_day_info['break'] = 0
            temp_day_info['overtime'] = 0
            temp_day_info['daily_overtime'] = 0
            temp_day_info['double_time'] = 0

        for action in temp_day_info['actions']:
            if action['type'] == 't':
                temp_day_info['total'] += action['total']
            else:
                temp_day_info['break'] += action['total']
                temp_day_info['total'] -= action['total']

        """If daily overtime calculate overtime for the day, and possibly double time"""
        if tt_settings['daily_overtime_s']:
            """Adjust this if you want breaks to count towards overtime"""
            if tt_settings['include_breaks_in_overtime_calculation']:
                actual_time = temp_day_info['total'] + temp_day_info['break']
            else:
                actual_time = temp_day_info['total']

            if cal_overtime:
                if self.form['other_hours_format'] == 'hours_and_minutes':
                    cal_overtime = cal_overtime * 60
                if actual_time >= cal_overtime:
                    actual_time = actual_time - cal_overtime
                    temp_day_info['double_time'] = cal_overtime
                else:
                    temp_day_info['double_time'] = actual_time
                    actual_time = 0

            calc_daily_overtime_value = tt_settings['daily_overtime_value']
            if self.form['other_hours_format'] == 'hours_and_minutes':
                calc_daily_overtime_value = calc_daily_overtime_value * 60
            if actual_time > calc_daily_overtime_value:
                temp_day_info['overtime'] = actual_time - calc_daily_overtime_value
            if tt_settings['double_time_s']:
                calc_double_time_value = tt_settings['double_time_value']
                if self.form['other_hours_format'] == 'hours_and_minutes':
                    calc_double_time_value = calc_double_time_value * 60
                if actual_time > calc_double_time_value:
                    temp_day_info['double_time'] = actual_time - calc_double_time_value
                    temp_day_info['overtime'] = temp_day_info['overtime'] - temp_day_info['double_time']
            temp_day_info['daily_overtime'] = temp_day_info['overtime']

        temp_day_info['total_with_break'] = temp_day_info['total'] + temp_day_info['break']

        self.convert_to_string(temp_day_info, ['total', 'break', 'overtime', 'daily_overtime', 'double_time', 'total_with_break'])

    def convert_to_string(self, input_dict, list_of_keys):
        for key in list_of_keys:
            if self.form['other_hours_format'] == 'decimal':
                input_dict['str_' + key] = str(round(input_dict[key], 2))
            else:
                input_dict['str_' + key] = convert_minutes_to_hours_and_minutes(input_dict[key])

    def add_week(self, days, week_info, week, possible_weeks, weeks, tt_settings):
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
            if tt_settings['daily_overtime_s']:
                for day in days:
                    if not day['previous']:
                        week_info['overtime'] += day['overtime']
                        week_info['daily_overtime'] += day['overtime']
                    else:
                        week_info['previous_daily_overtime'] += day['overtime']
                if tt_settings['double_time_s']:
                    for day in days:
                        if not day['previous']:
                            week_info['double_time'] += day['double_time']
                        else:
                            week_info['previous_double_time'] += day['double_time']

            """If weekly overtime then calculate the total weekly overtime for the week"""
            if tt_settings['weekly_overtime_s']:
                if tt_settings['include_breaks_in_overtime_calculation']:
                    actual_time = week_info['total'] + week_info['previous_total'] + week_info['break'] + week_info[
                        'previous_breaks']
                else:
                    actual_time = week_info['total'] + week_info['previous_total']

                """If daily overtime selected as well then calculate according to california laws"""
                if tt_settings['daily_overtime_s']:
                    """If double time make sure to account for it."""
                    if tt_settings['double_time_s']:
                        actual_time = actual_time - week_info['daily_overtime'] - week_info['double_time'] - week_info[
                            'previous_daily_overtime'] - week_info['previous_double_time']
                    else:
                        actual_time = actual_time - week_info['daily_overtime'] - week_info['previous_daily_overtime']

                """If the total hours pass the overtime threshold after all our adjustments then calculate weekly overtime."""
                calc_weekly_overtime_value = tt_settings['weekly_overtime_value']
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
            if tt_settings['double_time_s']:
                week_info['regular'] = week_info['regular'] - week_info['double_time']
            week_info['total_with_break'] = week_info['total'] + week_info['break']

            self.convert_to_string(week_info, ['regular', 'total_with_break', 'total', 'previous_total',
                                                           'previous_breaks', 'previous_daily_overtime',
                                                           'previous_double_time', 'overtime', 'daily_overtime',
                                                           'weekly_overtime', 'break'])
            week_info['number'] = week + 1
            weeks.append(week_info)
            week_info = {}
        return days, week_info, weeks


def convert_minutes_to_hours_and_minutes(m):
    """This function receives minutes and converts it to hours and minutes in string format"""
    minute = m % 60
    hour = int(m / 60)
    return f"{hour}:{minute:02d}"