import csv
import datetime
import os
import random
import string

import pytz
from django.test import TestCase
from django.utils import timezone
from users.models import Company
from users.models import CustomUser

from .forms import ReportsForm, TimeActionForm, EmployeeTimeActionForm
from .models import TimeActions
from .utils import get_timezone, get_employee_list, get_time_actions_list, Report, check_for_errors, \
    convert_front_end_date_to_utc

EMPLOYEES = 7
END_DATE = datetime.datetime.utcnow() + datetime.timedelta(days=1)
BEGIN_DATE = datetime.datetime.utcnow() - datetime.timedelta(weeks=8)


def random_string(string_length=8):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))


class TestModels(TestCase):
    """
    Testing the TimeActions model
    """

    def setUp(self):
        self.employee = CustomUser.objects.create(first_name='Ben', last_name='Kenobi', email='kenobi@jediorder.com')

    def test_timeactions(self):
        """
        Test for:
            Can create time action and attach to employee
            TimeAction.Save function actually updates the employees current time action
            TimeAction.delete function actually updates the employees current time action
            deleting time action doesn't delete employee
            deleting an employee removes all time actions for that employee.
        :return:
        """
        num_actions = 5
        time_actions = []
        current_time = timezone.now() - datetime.timedelta(hours=1)
        for i in range(num_actions):
            t = TimeActions.objects.create(user=self.employee, type='i', action_datetime=current_time,
                                           comment=("Time Action " + str(i)))
            time_actions.append(t)
            current_time = current_time - datetime.timedelta(hours=2)
        self.assertEqual(TimeActions.objects.filter(user=self.employee).count(), num_actions)

        employee = CustomUser.objects.get(id=self.employee.id)
        self.assertEqual(employee.time_action.id, time_actions[0].id)
        update_time_action = time_actions[1]
        update_time_action.action_datetime = timezone.now()
        update_time_action.save()
        employee = CustomUser.objects.get(id=self.employee.id)
        self.assertEqual(employee.time_action.id, time_actions[1].id)
        old_id = update_time_action.id
        update_time_action.delete()
        employee = CustomUser.objects.get(id=self.employee.id)
        self.assertEqual(employee.time_action.id, time_actions[0].id)
        with self.assertRaises(TimeActions.DoesNotExist):
            TimeActions.objects.get(id=old_id)
        employee_id = self.employee.id
        self.employee.delete()
        self.assertEqual(TimeActions.objects.filter(user=employee_id).count(), 0)


class TestForms(TestCase):
    """
    Test the following forms
    ReportsForm, TimeActionForm, EmployeeTimeActionForm
    """

    def test_reportsform(self):
        """
        Testing validation of the reports form
        initial values test, company with no employees
        :return:
        """
        company = Company.objects.create(name='TimeClick')

        with self.assertRaises(KeyError):
            ReportsForm()

        form = ReportsForm(company=company)
        self.assertFalse(form.is_valid())
        form = ReportsForm(company=company, data={'begin_date': timezone.now(), 'end_date': timezone.now()})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors,
                         {'report_type': ['This field is required.'], 'other_rounding': ['This field is required.'],
                          'other_hours_format': ['This field is required.'],
                          'other_font_size': ['This field is required.']})
        form = ReportsForm(company=company, data={'begin_date': timezone.now(), 'end_date': timezone.now(),
                                                  'report_type': 'reports/summary.html', 'other_rounding': 5,
                                                  'other_hours_format': 'hours_and_minutes',
                                                  'other_font_size': 'large'})
        self.assertTrue(form.is_valid())
        form = ReportsForm(company=company, data={'begin_date': 'panda', 'end_date': 'kungfu',
                                                  'report_type': 0, 'other_rounding': 'junk',
                                                  'other_hours_format': 'im_not_an_option',
                                                  'other_font_size': 'Loud'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'begin_date': ['Enter a valid date.'], 'end_date': ['Enter a valid date.'],
                                       'report_type': ['Select a valid choice. 0 is not one of the available choices.'],
                                       'other_rounding': [
                                           'Select a valid choice. junk is not one of the available choices.'],
                                       'other_hours_format': [
                                           'Select a valid choice. im_not_an_option is not one of the available choices.'],
                                       'other_font_size': [
                                           'Select a valid choice. Loud is not one of the available choices.']})

        pass

    def test_timeactionform(self):
        """
        Test the following
        Creating a time action
        updating a time action
        put invalid type information
        put invalid date information
        :return:
        """
        form = TimeActionForm()
        self.assertFalse(form.is_valid())
        current_time = timezone.now()
        form = TimeActionForm(
            data={'type': 'i', 'action_datetime_0': current_time.date(), 'action_datetime_1': current_time.time(),
                  'comment': 'Working Time aCtion'})
        self.assertTrue(form.is_valid())
        time_action = form.save()
        self.assertTrue(time_action)
        self.assertEqual(time_action.comment, 'Working Time aCtion')
        self.assertEqual(time_action.type, 'i')
        self.assertEqual(time_action.action_datetime, current_time)
        form = TimeActionForm(instance=time_action, data={'type': 'o', 'action_datetime_0': current_time.date(),
                                                          'action_datetime_1': current_time.time()})
        self.assertTrue(form.is_valid())
        time_action = form.save()
        self.assertTrue(time_action)
        self.assertEqual(time_action.type, 'o')
        self.assertEqual(time_action.action_datetime, current_time)
        self.assertEqual(time_action.comment, '')
        form = TimeActionForm(data={'type': 'p'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'type': ['Select a valid choice. p is not one of the available choices.'],
                                       'action_datetime': ['This field is required.']})
        with self.assertRaises(ValueError):
            form.save()
        form = TimeActionForm(
            data={'type': 'p', 'action_datetime_0': 'break', 'action_datetime_1': 'time', 'comment': 1})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'type': ['Select a valid choice. p is not one of the available choices.'],
                                       'action_datetime': ['Enter a valid date.', 'Enter a valid time.']})
        pass

    def test_employeetimeactionform(self):
        """
        Test the following
        create form with null info
        creating a clock action without adding action time
        entering a clock action with incorrect type
        :return:
        """

        form = EmployeeTimeActionForm()
        self.assertFalse(form.is_valid())
        form = EmployeeTimeActionForm(data={'type': 'i', 'comment': 'junk really'})
        self.assertTrue(form.is_valid())
        time_action = form.save()
        self.assertTrue(time_action)
        self.assertEqual(time_action.type, 'i')
        self.assertEqual(time_action.comment, 'junk really')
        self.assertEqual(time_action.action_datetime.date(), timezone.now().date())
        form = EmployeeTimeActionForm(data={'type': 'p', 'comment': ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'type': ["Value 'p' is not a valid choice."]})


class TestUtils(TestCase):
    """Create Company
    Create employees and administrator for the company
    Create times for the employees"""

    def test_report_generator_with_csv_documents(self):
        """
        Using a csv document generated by TimeClick20 import employees, times.
        Generate a report and test its values against the csv documents values
        :return:
        """
        resource_path = 'clock_actions/test_resources/'
        test_resources = os.listdir(resource_path)
        for f in test_resources:
            begin_date = None
            end_date = None
            test_company = Company.objects.create(name="TimeClick Test", daily_overtime=True, double_time=True,
                                                  week_start_day=3)
            user = CustomUser.objects.create(first_name="Head", last_name="Admin",
                                             email="jace" + random_string(3) + "@gmail.com",
                                             timezone=pytz.timezone('America/Denver'), role='c', company=test_company)
            csv_dict = {'employees': []}
            correct_timezone = get_timezone(user)

            """Currently only reports with clock in and outs can work, breaks not included yet."""
            # TODO test with a report that has breaks
            with open('./' + resource_path + f, newline='') as csvfile:
                hours_file = csv.reader(csvfile, delimiter=',')

                header = next(hours_file)
                pos_name = header.index('Employee Name')
                pos_date = header.index('Date')
                pos_time = header.index('Time')
                pos_action = header.index('Action')
                pos_total_decimal = header.index('Total (Decimal)')
                pos_hours_type = header.index('Hours Type')
                pos_line_title = 0

                prev_emp = None
                emp = {'weeks': []}
                week = {'days': []}
                day = {}
                for row in hours_file:
                    if row[pos_name] and not row[pos_name] == 'Employee Name':
                        if not prev_emp == row[pos_name]:
                            name = row[pos_name]
                            email = random_string(12) + '@gmail.com'
                            pay_rate = 13.05
                            last_name, first_name = name.split(', ')
                            middle_name = 'junk'
                            employee = CustomUser.objects.create(company=test_company, email=email,
                                                                 first_name=first_name,
                                                                 last_name=last_name, verified=True, is_active=True,
                                                                 pay_rate=pay_rate)
                            prev_emp = row[pos_name]

                            if emp:
                                emp = {}
                            emp['name'] = prev_emp
                            emp['weeks'] = []

                        if row[pos_action]:
                            type = row[pos_action]
                            date = row[pos_date]
                            time = row[pos_time]
                            action_date = convert_front_end_date_to_utc(
                                datetime.datetime.strptime(date + ' ' + time, '%m/%d/%y %I:%M %p'), correct_timezone)
                            if type == 'Clock In':
                                TimeActions.objects.create(user=employee, type='i', action_datetime=action_date,
                                                           comment='test for the empire')
                            elif type == 'Clock Out':
                                TimeActions.objects.create(user=employee, type='o', action_datetime=action_date,
                                                           comment='test for the empire')
                        elif row[pos_total_decimal]:
                            if 'Week' in row[pos_line_title]:
                                if row[pos_hours_type] == 'Regular Hours':
                                    week['regular'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Previous Hours':
                                    week['previous_total'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Daily OT':
                                    week['daily_overtime'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Weekly OT':
                                    week['weekly_overtime'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Double Time':
                                    week['double_time'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Total OT':
                                    week['overtime'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Total':
                                    week['total'] = row[pos_total_decimal]
                                    emp['weeks'].append(week)
                                    week = {'days': []}
                            elif 'Report Totals' in row[pos_line_title]:
                                if row[pos_hours_type] == 'Regular Hours':
                                    emp['regular'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Daily OT':
                                    emp['daily_overtime'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Weekly OT':
                                    emp['weekly_overtime'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Double Time':
                                    emp['double_time'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Total OT':
                                    emp['overtime'] = row[pos_total_decimal]
                                elif row[pos_hours_type] == 'Total':
                                    emp['total'] = row[pos_total_decimal]
                                    csv_dict['employees'].append(emp)
                                    emp = {'weeks': []}
                            elif 'Total ' in row[pos_line_title] or 'Total (Previous Hours)' in row[pos_line_title]:
                                day['total'] = row[pos_total_decimal]
                                week['days'].append(day)
                                day = {}

                    if 'Grand' in row[0]:
                        if row[pos_hours_type] == 'Regular Hours':
                            csv_dict['regular'] = row[pos_total_decimal]
                        elif row[pos_hours_type] == 'Daily OT':
                            csv_dict['daily_overtime'] = row[pos_total_decimal]
                        elif row[pos_hours_type] == 'Weekly OT':
                            csv_dict['weekly_overtime'] = row[pos_total_decimal]
                        elif row[pos_hours_type] == 'Double Time':
                            csv_dict['double_time'] = row[pos_total_decimal]
                        elif row[pos_hours_type] == 'Total OT':
                            csv_dict['overtime'] = row[pos_total_decimal]
                        elif row[pos_hours_type] == 'Total':
                            csv_dict['total'] = row[pos_total_decimal]
                        begin_date, end_date = row[0][row[0].find("(") + 1:row[0].find(")")].split(' - ')
                        begin_date = datetime.datetime.strptime(begin_date, '%m/%d/%y').date()
                        end_date = datetime.datetime.strptime(end_date, '%m/%d/%y').date()

            form = ReportsForm(company=test_company,
                               data={'begin_date': begin_date,
                                     'end_date': end_date,
                                     'report_type': 'reports/detailed_hours.html',
                                     'selected_employees_list': (-1,),
                                     'display_clock_actions': True,
                                     'display_day_totals': True,
                                     'display_week_totals': True,
                                     'display_employee_totals': True,
                                     'display_grand_totals': True,
                                     'display_employee_pay_total': True,
                                     'display_employee_pay_rate': True,
                                     'display_grand_pay_total': True,
                                     'display_employee_comments': True,
                                     'add_employee_signature_line': True,
                                     'add_supervisor_signature_line': True,
                                     'add_other_signature_line': True,
                                     'other_new_page_for_each_employee': True,
                                     'other_rounding': 1,
                                     'other_hours_format': 'decimal',
                                     'other_font_size': 'medium',
                                     'other_memo': True,
                                     'other_space_on_right': True})
            self.assertTrue(form.is_valid())
            pass_form = form.cleaned_data
            employee_list, employee_id_list = get_employee_list(test_company, pass_form['selected_employees_list'])
            full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                    test_company, correct_timezone)
            temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, test_company,
                          correct_timezone)
            generated_dict = temp.create_report_dict()

            types = ['regular', 'total', 'overtime', 'daily_overtime', 'weekly_overtime', 'double_time']

            for employee in range(len(csv_dict['employees'])):
                csv_emp = csv_dict['employees'][employee]
                gen_emp = generated_dict['employees'][employee]
                for week in range(len(csv_emp['weeks'])):
                    csv_week = csv_emp['weeks'][week]
                    gen_week = gen_emp['weeks'][week]
                    for day in range(len(csv_week['days'])):
                        csv_day = csv_week['days'][day]
                        gen_day = gen_week['days'][day]
                        try:
                            self.assertTrue(is_close(csv_day['total'], gen_day['total']))
                        except:
                            pass

                    for hr_type in types:
                        try:
                            self.assertTrue(is_close(csv_week[hr_type], gen_week[hr_type]))
                        except KeyError:
                            pass
                for hr_type in types:
                    try:
                        self.assertTrue(is_close(csv_emp[hr_type], csv_emp[hr_type]))
                    except KeyError:
                        pass
            for hr_type in types:
                try:
                    self.assertTrue(is_close(csv_dict[hr_type], generated_dict[hr_type]))
                except KeyError:
                    pass
        pass

    def test_report_generator_predefined_values(self):
        """
        This test is to test outliers in the report generator
        Manually create company, employee, and time actions
        compare results with expected results

        week begin date: Wednesday
        report period: Apr 5 2020 - Apr 13
        times for Apr 1 2020 - Apr 13
        all overtime settings and double time settings are true

        then the second turns daily overtime and double time off, to test that overtime calculation.

        Both include breaks which is not tested in the csv tests
        :return:
        """

        expected_results = {
            'employees': [
                {
                    'name': 'zoolander, derrick',
                    'total': 40.9,
                    'break': 1.22,
                    'overtime': 1.83,
                    'daily_overtime': 1.83,
                    'double_time': 0.0,
                    'weekly_overtime': 0.0,
                    'total_with_break': 42.12,
                    'regular': 39.07,
                    'weeks': [
                        {
                            'total': 15.1,
                            'break': 1.0,
                            'overtime': 0.03,
                            'previous_total': 30.03,
                            'previous_break': 2.0,
                            'previous_daily_overtime': 5.10,
                            'previous_double_time': 1.08,
                            'daily_overtime': 0.03,
                            'weekly_overtime': 0.0,
                            'double_time': 0.0,
                            'regular': 14.97,
                            'total_with_break': 16.1,
                            'days': [
                                {
                                    'actions': [
                                        {
                                            'total': 2.00
                                        },
                                        {
                                            'total': 9.85
                                        }
                                    ],
                                    'total': 7.85,
                                    'break': 2.00,
                                    'previous': True,
                                    'overtime': 0.0,
                                    'daily_overtime': 0.0,
                                    'double_time': 0.0,
                                    'total_with_break': 9.85
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 9.1
                                        }
                                    ],
                                    'total': 9.1,
                                    'break': 0.00,
                                    'previous': True,
                                    'overtime': 1.1,
                                    'daily_overtime': 1.1,
                                    'double_time': 0.0,
                                    'total_with_break': 9.1
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 13.08
                                        }
                                    ],
                                    'total': 13.08,
                                    'break': 0.00,
                                    'previous': True,
                                    'overtime': 4.0,
                                    'daily_overtime': 4.0,
                                    'double_time': 1.08,
                                    'total_with_break': 13.08
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 1.0
                                        },
                                        {
                                            'total': 8.07
                                        }
                                    ],
                                    'total': 7.07,
                                    'break': 1.0,
                                    'previous': False,
                                    'overtime': 0.0,
                                    'daily_overtime': 0.0,
                                    'double_time': 0.0,
                                    'total_with_break': 8.07
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 8.03
                                        }
                                    ],
                                    'total': 8.03,
                                    'break': 0.00,
                                    'previous': False,
                                    'overtime': 0.03,
                                    'daily_overtime': 0.03,
                                    'double_time': 0.0,
                                    'total_with_break': 8.03
                                },
                            ]
                        },
                        {
                            'total': 25.80,
                            'break': 0.22,
                            'overtime': 1.80,
                            'previous_total': 0.0,
                            'previous_break': 0.0,
                            'daily_overtime': 1.80,
                            'weekly_overtime': 0.0,
                            'double_time': 0.0,
                            'regular': 24,
                            'total_with_break': 26.02,
                            'days': [
                                {
                                    'actions': [
                                        {
                                            'total': 8.03
                                        }
                                    ],
                                    'total': 8.03,
                                    'break': 0.00,
                                    'previous': False,
                                    'overtime': 0.03,
                                    'daily_overtime': 0.03,
                                    'double_time': 0.0,
                                    'total_with_break': 8.03
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 0.22
                                        },
                                        {
                                            'total': 8.92
                                        }
                                    ],
                                    'total': 8.70,
                                    'break': 0.22,
                                    'previous': True,
                                    'overtime': 0.7,
                                    'daily_overtime': 0.7,
                                    'double_time': 0.0,
                                    'total_with_break': 8.92
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 9.07
                                        }
                                    ],
                                    'total': 9.07,
                                    'break': 0.00,
                                    'previous': False,
                                    'overtime': 1.07,
                                    'daily_overtime': 1.07,
                                    'double_time': 0.0,
                                    'total_with_break': 9.07
                                }
                            ]
                        },
                    ]
                }
            ]
        }

        expected_results_only_weekly_ot = {
            'employees': [
                {
                    'name': 'zoolander, derrick',
                    'total': 40.9,
                    'break': 1.22,
                    'overtime': 5.13,
                    'daily_overtime': 0.0,
                    'double_time': 0.0,
                    'weekly_overtime': 5.13,
                    'total_with_break': 42.12,
                    'regular': 35.77,
                    'weeks': [
                        {
                            'total': 15.1,
                            'break': 1.0,
                            'overtime': 5.13,
                            'previous_total': 30.03,
                            'previous_break': 2.0,
                            'previous_daily_overtime': 0.0,
                            'previous_double_time': 0.0,
                            'daily_overtime': 0.00,
                            'weekly_overtime': 5.13,
                            'double_time': 0.0,
                            'regular': 9.97,
                            'total_with_break': 16.1,
                            'days': [
                                {
                                    'actions': [
                                        {
                                            'total': 2.00
                                        },
                                        {
                                            'total': 9.85
                                        }
                                    ],
                                    'total': 7.85,
                                    'break': 2.00,
                                    'previous': True,
                                    'overtime': 0.0,
                                    'daily_overtime': 0.0,
                                    'double_time': 0.0,
                                    'total_with_break': 9.85
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 9.1
                                        }
                                    ],
                                    'total': 9.1,
                                    'break': 0.00,
                                    'previous': True,
                                    'overtime': 0.0,
                                    'daily_overtime': 0.0,
                                    'double_time': 0.0,
                                    'total_with_break': 9.1
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 13.08
                                        }
                                    ],
                                    'total': 13.08,
                                    'break': 0.00,
                                    'previous': True,
                                    'overtime': 0.0,
                                    'daily_overtime': 0.0,
                                    'double_time': 0.0,
                                    'total_with_break': 13.08
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 1.0
                                        },
                                        {
                                            'total': 8.07
                                        }
                                    ],
                                    'total': 7.07,
                                    'break': 1.0,
                                    'previous': False,
                                    'overtime': 0.0,
                                    'daily_overtime': 0.0,
                                    'double_time': 0.0,
                                    'total_with_break': 8.07
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 8.03
                                        }
                                    ],
                                    'total': 8.03,
                                    'break': 0.00,
                                    'previous': False,
                                    'overtime': 0.00,
                                    'daily_overtime': 0.00,
                                    'double_time': 0.0,
                                    'total_with_break': 8.03
                                },
                            ]
                        },
                        {
                            'total': 25.80,
                            'break': 0.22,
                            'overtime': 0.0,
                            'previous_total': 0.0,
                            'previous_break': 0.0,
                            'daily_overtime': 0.0,
                            'weekly_overtime': 0.0,
                            'double_time': 0.0,
                            'regular': 25.80,
                            'total_with_break': 26.02,
                            'days': [
                                {
                                    'actions': [
                                        {
                                            'total': 8.03
                                        }
                                    ],
                                    'total': 8.03,
                                    'break': 0.00,
                                    'previous': False,
                                    'overtime': 0.00,
                                    'daily_overtime': 0.00,
                                    'double_time': 0.0,
                                    'total_with_break': 8.03
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 0.22
                                        },
                                        {
                                            'total': 8.92
                                        }
                                    ],
                                    'total': 8.70,
                                    'break': 0.22,
                                    'previous': False,
                                    'overtime': 0.0,
                                    'daily_overtime': 0.0,
                                    'double_time': 0.0,
                                    'total_with_break': 8.92
                                },
                                {
                                    'actions': [
                                        {
                                            'total': 9.07
                                        }
                                    ],
                                    'total': 9.07,
                                    'break': 0.00,
                                    'previous': False,
                                    'overtime': 0.0,
                                    'daily_overtime': 0.0,
                                    'double_time': 0.0,
                                    'total_with_break': 9.07
                                }
                            ]
                        },
                    ]
                }
            ]
        }

        begin_date = datetime.datetime.strptime("04/05/2020", "%m/%d/%Y")
        end_date = datetime.datetime.strptime("04/13/2020", "%m/%d/%Y")

        company = Company.objects.create(name='Test1', week_start_day=2, daily_overtime=True, double_time=True)
        employee = CustomUser.objects.create(first_name='derrick', last_name='zoolander', email='junk@test_reports.com',
                                             company=company)
        user = CustomUser.objects.create(first_name="Head", last_name="Admin",
                                         email="jace" + random_string(3) + "@gmail.com",
                                         timezone=pytz.timezone('America/Denver'), role='c',
                                         company=company)
        correct_timezone = get_timezone(user)

        """4/1/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/01/2020 07:05 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='b', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/01/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/01/2020 10:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/01/2020 04:56 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/2/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/02/2020 06:56 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/02/2020 04:02 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/3/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/03/2020 06:56 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/03/2020 08:01 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/6/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 07:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='b', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 09:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 03:04 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/7/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/07/2020 08:03 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/07/2020 04:05 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/8/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/08/2020 06:57 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/08/2020 02:59 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/9/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/09/2020 07:04 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='b', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/09/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/09/2020 08:13 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/09/2020 03:59 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/13/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/13/2020 07:47 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/13/2020 04:51 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))

        form = ReportsForm(company=company,
                           data={'begin_date': begin_date,
                                 'end_date': end_date,
                                 'report_type': 'reports/detailed_hours.html',
                                 'selected_employees_list': (-1,),
                                 'display_clock_actions': True,
                                 'display_day_totals': True,
                                 'display_week_totals': True,
                                 'display_employee_totals': True,
                                 'display_grand_totals': True,
                                 'display_employee_pay_total': True,
                                 'display_employee_pay_rate': True,
                                 'display_grand_pay_total': True,
                                 'display_employee_comments': True,
                                 'add_employee_signature_line': True,
                                 'add_supervisor_signature_line': True,
                                 'add_other_signature_line': True,
                                 'other_new_page_for_each_employee': True,
                                 'other_rounding': 1,
                                 'other_hours_format': 'decimal',
                                 'other_font_size': 'medium',
                                 'other_memo': True,
                                 'other_space_on_right': True})
        self.assertTrue(form.is_valid())
        pass_form = form.cleaned_data
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)
        temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, company,
                      correct_timezone)
        generated_dict = temp.create_report_dict()

        hr_type_list = ['total', 'overtime', 'break', 'previous_total', 'previous_breaks', 'previous_daily_overtime',
                        'previous_double_time', 'daily_overtime', 'weekly_overtime', 'double_time', 'total_with_break',
                        'regular']

        for employee in range(len(expected_results['employees'])):
            answer_emp = expected_results['employees'][employee]
            gen_emp = generated_dict['employees'][employee]
            for week in range(len(answer_emp['weeks'])):
                answer_week = answer_emp['weeks'][week]
                gen_week = gen_emp['weeks'][week]
                for day in range(len(answer_week['days'])):
                    answer_day = answer_week['days'][day]
                    gen_day = gen_week['days'][day]
                    for action in range(len(answer_day['actions'])):
                        answer_action = answer_day['actions'][action]
                        gen_action = gen_day['actions'][action]
                        self.assertTrue(is_close(answer_action['total'], gen_action['total']))

                    for hr_type in hr_type_list:
                        try:
                            self.assertTrue(is_close(answer_day[hr_type], gen_day[hr_type]))
                        except KeyError:
                            pass
                for hr_type in hr_type_list:
                    try:
                        self.assertTrue(is_close(answer_week[hr_type], gen_week[hr_type]))
                    except KeyError:
                        pass
            for hr_type in hr_type_list:
                try:
                    self.assertTrue(is_close(answer_emp[hr_type], gen_emp[hr_type]))
                except KeyError:
                    pass

        company.double_time = False
        company.daily_overtime = False
        company.save()

        form = ReportsForm(company=company,
                           data={'begin_date': begin_date,
                                 'end_date': end_date,
                                 'report_type': 'reports/detailed_hours.html',
                                 'selected_employees_list': (-1,),
                                 'display_clock_actions': True,
                                 'display_day_totals': True,
                                 'display_week_totals': True,
                                 'display_employee_totals': True,
                                 'display_grand_totals': True,
                                 'display_employee_pay_total': True,
                                 'display_employee_pay_rate': True,
                                 'display_grand_pay_total': True,
                                 'display_employee_comments': True,
                                 'add_employee_signature_line': True,
                                 'add_supervisor_signature_line': True,
                                 'add_other_signature_line': True,
                                 'other_new_page_for_each_employee': True,
                                 'other_rounding': 1,
                                 'other_hours_format': 'decimal',
                                 'other_font_size': 'medium',
                                 'other_memo': True,
                                 'other_space_on_right': True})
        self.assertTrue(form.is_valid())
        pass_form = form.cleaned_data
        user = CustomUser.objects.create(first_name="Head", last_name="Admin",
                                         email="jace" + random_string(3) + "@gmail.com",
                                         timezone=pytz.timezone('America/Denver'), role='c',
                                         company=company)
        correct_timezone = get_timezone(user)
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)
        temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, company,
                      correct_timezone)
        generated_dict = temp.create_report_dict()

        hr_type_list = ['total', 'overtime', 'break', 'previous_total', 'previous_breaks', 'previous_daily_overtime',
                        'previous_double_time', 'daily_overtime', 'weekly_overtime', 'double_time', 'total_with_break',
                        'regular']

        for employee in range(len(expected_results_only_weekly_ot['employees'])):
            answer_emp = expected_results_only_weekly_ot['employees'][employee]
            gen_emp = generated_dict['employees'][employee]
            for week in range(len(answer_emp['weeks'])):
                answer_week = answer_emp['weeks'][week]
                gen_week = gen_emp['weeks'][week]
                for day in range(len(answer_week['days'])):
                    answer_day = answer_week['days'][day]
                    gen_day = gen_week['days'][day]
                    for action in range(len(answer_day['actions'])):
                        answer_action = answer_day['actions'][action]
                        gen_action = gen_day['actions'][action]
                        self.assertTrue(is_close(answer_action['total'], gen_action['total']))
                    try:
                        self.assertEqual(answer_day['previous'], gen_day['previous'])
                    except KeyError:
                        pass
                    for hr_type in hr_type_list:
                        try:
                            self.assertTrue(is_close(answer_day[hr_type], gen_day[hr_type]))
                        except KeyError:
                            pass
                for hr_type in hr_type_list:
                    try:
                        self.assertTrue(is_close(answer_week[hr_type], gen_week[hr_type]))
                    except KeyError:
                        pass
            for hr_type in hr_type_list:
                try:
                    self.assertTrue(is_close(answer_emp[hr_type], gen_emp[hr_type]))
                except KeyError:
                    pass
        pass

    def test_assumed_actions(self):
        """
        These tests are built specifically to test the following:
        assumed clock in when first action of day is clock out
        assumed clock in when first action of day is break in
        assumed clock in and break in when first action of the day is end break
        assumed clock out when the last action of the day is clocked in
        assumed clock out when the last action of the day is end break
        assumed end break and clock out when the last action of the day is begin break

        This is part of that midnight threshold ideology
        :return:
        """

        company = Company.objects.create(name="test_assumed_actions", weekly_overtime=False)
        user = CustomUser.objects.create(first_name="Head", last_name="Admin",
                                         email="jace" + random_string(3) + "@gmail.com",
                                         timezone=pytz.timezone('America/Denver'), role='c',
                                         company=company)
        correct_timezone = get_timezone(user)

        begin_date = datetime.datetime.strptime("04/05/2020", "%m/%d/%Y")
        end_date = datetime.datetime.strptime("04/8/2020", "%m/%d/%Y")

        form = ReportsForm(company=company,
                           data={'begin_date': begin_date,
                                 'end_date': end_date,
                                 'report_type': 'reports/detailed_hours.html',
                                 'selected_employees_list': (-1,),
                                 'display_clock_actions': True,
                                 'display_day_totals': True,
                                 'display_week_totals': True,
                                 'display_employee_totals': True,
                                 'display_grand_totals': True,
                                 'display_employee_pay_total': True,
                                 'display_employee_pay_rate': True,
                                 'display_grand_pay_total': True,
                                 'display_employee_comments': True,
                                 'add_employee_signature_line': True,
                                 'add_supervisor_signature_line': True,
                                 'add_other_signature_line': True,
                                 'other_new_page_for_each_employee': True,
                                 'other_rounding': 1,
                                 'other_hours_format': 'decimal',
                                 'other_font_size': 'medium',
                                 'other_memo': True,
                                 'other_space_on_right': True})
        self.assertTrue(form.is_valid())
        pass_form = form.cleaned_data

        """Assumed clock in when first action of the day is clock out"""
        employee = CustomUser.objects.create(first_name="Ren", last_name="Kilo", email="Kilo@Darkside.com",
                                             company=company)

        """4/6/20"""
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 03:04 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)
        temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, company,
                      correct_timezone)
        generated_dict = temp.create_report_dict()

        expect_day = {
            'actions': [
                {
                    'total': 15.07
                }
            ],
            'total': 15.07,
            'break': 0.0
        }
        gen_day = generated_dict['employees'][0]['weeks'][0]['days'][0]

        for action in range(len(expect_day['actions'])):
            exp_action = expect_day['actions'][action]
            gen_action = gen_day['actions'][action]
            self.assertTrue(is_close(exp_action['total'], gen_action['total']))
        self.assertTrue(is_close(expect_day['total'], gen_day['total']))
        self.assertTrue(is_close(expect_day['break'], gen_day['break']))

        employee.delete()

        """assumed clock in when first action is begin break"""
        employee = CustomUser.objects.create(first_name="Ren", last_name="Kilo", email="Kilo@Darkside.com",
                                             company=company)
        """4/6/20"""
        TimeActions.objects.create(user=employee, type='b', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 09:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 03:04 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)
        temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, company,
                      correct_timezone)
        generated_dict = temp.create_report_dict()

        expect_day = {
            'actions': [
                {
                    'total': 1.00
                },
                {
                    'total': 15.07
                }
            ],
            'total': 14.07,
            'break': 1.0
        }
        gen_day = generated_dict['employees'][0]['weeks'][0]['days'][0]

        for action in range(len(expect_day['actions'])):
            exp_action = expect_day['actions'][action]
            gen_action = gen_day['actions'][action]
            self.assertTrue(is_close(exp_action['total'], gen_action['total']))
        self.assertTrue(is_close(expect_day['total'], gen_day['total']))
        self.assertTrue(is_close(expect_day['break'], gen_day['break']))

        employee.delete()

        """assumed clock in and break in when first action of the day is end break"""
        employee = CustomUser.objects.create(first_name="Ren", last_name="Kilo", email="Kilo@Darkside.com",
                                             company=company)
        """4/6/20"""
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 09:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 03:04 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)
        temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, company,
                      correct_timezone)
        generated_dict = temp.create_report_dict()

        expect_day = {
            'actions': [
                {
                    'total': 9.0
                },
                {
                    'total': 15.07
                }
            ],
            'total': 6.07,
            'break': 9.0
        }
        gen_day = generated_dict['employees'][0]['weeks'][0]['days'][0]

        for action in range(len(expect_day['actions'])):
            exp_action = expect_day['actions'][action]
            gen_action = gen_day['actions'][action]
            self.assertTrue(is_close(exp_action['total'], gen_action['total']))
        self.assertTrue(is_close(expect_day['total'], gen_day['total']))
        self.assertTrue(is_close(expect_day['break'], gen_day['break']))

        employee.delete()

        """assumed clock out when the last action of the day is clocked in"""
        employee = CustomUser.objects.create(first_name="Ren", last_name="Kilo", email="Kilo@Darkside.com",
                                             company=company)
        """4/6/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 07:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)
        temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, company,
                      correct_timezone)
        generated_dict = temp.create_report_dict()

        expect_day = {
            'actions': [
                {
                    'total': 17.0
                }
            ],
            'total': 17.0,
            'break': 0.0
        }
        gen_day = generated_dict['employees'][0]['weeks'][0]['days'][0]

        for action in range(len(expect_day['actions'])):
            exp_action = expect_day['actions'][action]
            gen_action = gen_day['actions'][action]
            self.assertTrue(is_close(exp_action['total'], gen_action['total']))
        self.assertTrue(is_close(expect_day['total'], gen_day['total']))
        self.assertTrue(is_close(expect_day['break'], gen_day['break']))

        employee.delete()

        """assumed clock out when the last action of the day is end break"""
        employee = CustomUser.objects.create(first_name="Ren", last_name="Kilo", email="Kilo@Darkside.com",
                                             company=company)
        """4/6/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 07:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='b', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 09:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)
        temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, company,
                      correct_timezone)
        generated_dict = temp.create_report_dict()

        expect_day = {
            'actions': [
                {
                    'total': 1.00
                },
                {
                    'total': 17.00
                }
            ],
            'total': 16.00,
            'break': 1.0
        }
        gen_day = generated_dict['employees'][0]['weeks'][0]['days'][0]

        for action in range(len(expect_day['actions'])):
            exp_action = expect_day['actions'][action]
            gen_action = gen_day['actions'][action]
            self.assertTrue(is_close(exp_action['total'], gen_action['total']))
        self.assertTrue(is_close(expect_day['total'], gen_day['total']))
        self.assertTrue(is_close(expect_day['break'], gen_day['break']))

        employee.delete()

        """assumed end break and clock out when the last action of the day is begin break"""
        employee = CustomUser.objects.create(first_name="Ren", last_name="Kilo", email="Kilo@Darkside.com",
                                             company=company)
        """4/6/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 07:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='b', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)
        temp = Report(employee_list, time_actions_list, pass_form, full_beg_date, full_end_date, company,
                      correct_timezone)
        generated_dict = temp.create_report_dict()

        expect_day = {
            'actions': [
                {
                    'total': 16.0
                },
                {
                    'total': 17.0
                }
            ],
            'total': 1.0,
            'break': 16.0
        }
        gen_day = generated_dict['employees'][0]['weeks'][0]['days'][0]

        for action in range(len(expect_day['actions'])):
            exp_action = expect_day['actions'][action]
            gen_action = gen_day['actions'][action]
            self.assertTrue(is_close(exp_action['total'], gen_action['total']))
        self.assertTrue(is_close(expect_day['total'], gen_day['total']))
        self.assertTrue(is_close(expect_day['break'], gen_day['break']))
        pass

    def test_check_for_errors(self):
        """
        Testing the following:
        Check if a single duplicate entry is caught.
        Check is multiple duplicate entries are caught.
        :return:
        """

        company = Company.objects.create(name="test_assumed_actions", weekly_overtime=False)
        user = CustomUser.objects.create(first_name="Head", last_name="Admin",
                                         email="jace" + random_string(3) + "@gmail.com",
                                         timezone=pytz.timezone('America/Denver'), role='c',
                                         company=company)
        correct_timezone = get_timezone(user)

        employee = CustomUser.objects.create(first_name="Ren", last_name="Kilo", email="ReyLover@tank.net",
                                             company=company)

        begin_date = datetime.datetime.strptime("04/05/2020", "%m/%d/%Y")
        end_date = datetime.datetime.strptime("04/08/2020", "%m/%d/%Y")

        form = ReportsForm(company=company,
                           data={'begin_date': begin_date,
                                 'end_date': end_date,
                                 'report_type': 'reports/detailed_hours.html',
                                 'selected_employees_list': (-1,),
                                 'display_clock_actions': True,
                                 'display_day_totals': True,
                                 'display_week_totals': True,
                                 'display_employee_totals': True,
                                 'display_grand_totals': True,
                                 'display_employee_pay_total': True,
                                 'display_employee_pay_rate': True,
                                 'display_grand_pay_total': True,
                                 'display_employee_comments': True,
                                 'add_employee_signature_line': True,
                                 'add_supervisor_signature_line': True,
                                 'add_other_signature_line': True,
                                 'other_new_page_for_each_employee': True,
                                 'other_rounding': 1,
                                 'other_hours_format': 'decimal',
                                 'other_font_size': 'medium',
                                 'other_memo': True,
                                 'other_space_on_right': True})
        self.assertTrue(form.is_valid())
        pass_form = form.cleaned_data

        """4/6/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 07:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))

        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)

        return_dict = {
            'date-range': (pass_form['begin_date'].strftime('%m/%d/%y') + " - " + pass_form['end_date'].strftime(
                '%m/%d/%y')),
            'employees': [],
            'form': pass_form,
            'company': {'name': company.name},
            'paid_breaks': company.breaks_are_paid,
        }

        return_dict, time_actions_list = check_for_errors(employee_list, time_actions_list, return_dict)

        self.assertTrue(return_dict['error'])
        self.assertEqual(len(return_dict['employees'][0]['errors']), 1)
        self.assertEqual(return_dict['employees'][0]['errors'][0]['Error'], 'Duplicate time actions')
        employee.delete()

        employee = CustomUser.objects.create(first_name="Ren", last_name="Kilo", email="ReyLover@tank.net",
                                             company=company)

        """4/1/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/01/2020 07:05 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/01/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/01/2020 10:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/01/2020 04:56 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/2/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/02/2020 06:56 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/02/2020 04:02 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/3/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/03/2020 06:56 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/03/2020 08:01 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/6/20"""
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 07:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='b', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 09:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/06/2020 03:04 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/7/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/07/2020 08:03 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/07/2020 04:05 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/8/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/08/2020 06:57 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/08/2020 02:59 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/9/20"""
        TimeActions.objects.create(user=employee, type='i', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/09/2020 07:04 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='b', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/09/2020 08:00 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='e', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/09/2020 08:13 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/09/2020 03:59 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        """4/13/20"""
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/13/2020 07:47 AM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        TimeActions.objects.create(user=employee, type='o', action_datetime=convert_front_end_date_to_utc(
            datetime.datetime.strptime("04/13/2020 04:51 PM", "%m/%d/%Y %I:%M %p"), correct_timezone))
        employee_list, employee_id_list = get_employee_list(company, pass_form['selected_employees_list'])
        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(pass_form, employee_id_list,
                                                                                company, correct_timezone)

        return_dict = {
            'date-range': (pass_form['begin_date'].strftime('%m/%d/%y') + " - " + pass_form['end_date'].strftime(
                '%m/%d/%y')),
            'employees': [],
            'form': pass_form,
            'company': {'name': company.name},
            'paid_breaks': company.breaks_are_paid,
        }

        return_dict, time_actions_list = check_for_errors(employee_list, time_actions_list, return_dict)

        expected_messages = ['Break ended when there was no break start', 'Duplicate time actions',
                             'Clocked in when employee was not clocked out', 'Duplicate time actions',
                             'Duplicate time actions', 'Break started when employee is not clocked in',
                             'Duplicate time actions', 'Duplicate time actions']

        self.assertTrue(return_dict['error'])
        self.assertEqual(len(return_dict['employees'][0]['errors']), 8)
        for error in range(len(return_dict['employees'][0]['errors'])):
            err_message = return_dict['employees'][0]['errors'][error]['Error']
            self.assertEqual(err_message, expected_messages[error])

    def test_get_date_range(self):
        pass

    def test_convert_minutes_to_hours_and_minutes(self):
        pass


def is_close(x, y):
    x = float(x)
    y = float(y)
    test = x - y
    if -0.1 < test < 0.1:
        return True
    else:
        print(str(x) + " != " + str(y))
        return False


""" Old code """

"""        for i in range(EMPLOYEES):
            if not prev_emp or prev_emp ==
            email = random_string(12) + '@gmail.com'
            first_name = random_string(20)
            middle_name = random_string(10)
            last_name = random_string(10)
            employee = CustomUser.objects.create(company=test_company, email=email, first_name=first_name,
                                                 last_name=last_name, verified=True, is_active=True)

            start_date = BEGIN_DATE
            end_date = END_DATE
            while start_date < end_date:
                number_of_clock_actions = 1
                for i in range(number_of_clock_actions):
                    hour = random.randint(7, 9)
                    minute = random.randint(0, 59)
                    second = random.randint(0, 59)
                    time_passed = random.randint(6, 10)
                    action_date = start_date
                    action_date = action_date.replace(hour=hour, minute=minute, second=second)
                    TimeActions.objects.create(user=employee, type='i', action_datetime=action_date,
                                               comment='test for the empire')
                    action_date = action_date + datetime.timedelta(hours=time_passed)
                    TimeActions.objects.create(user=employee, type='o', action_datetime=action_date,
                                               comment='test for the empire')
                start_date = start_date + datetime.timedelta(days=1)"""
