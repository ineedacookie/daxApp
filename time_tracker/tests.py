from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta, datetime

from users.models import CustomUser, Company
from .forms import ReportsForm
from .models import TTUserInfo, TTCompanyInfo, InOutAction
from .report import Report, get_time_actions_list
from .helpers import get_pay_period_dates
from middleware.timezone import get_timezone


class ModelsTest(TestCase):
    """
    Things to test:
        1. Creating a company creates TTCompanyInfo
        2. Creating a user with a company uses the set default TTCompanyInfo values in the TTUserInfo
        3. Creating a user without a company will create a company and create default TTCompanyInfo values and apply them to TTuserInfo
    """

    def test_user_without_company(self):
        # create user with company
        company = Company.objects.create(name='Test')
        c_info = TTCompanyInfo.objects.filter(company=company)
        self.assertTrue(c_info)
        c_info = c_info[0]
        c_info.default_daily_overtime_value = 12
        c_info.save()
        self.assertEqual(c_info.default_daily_overtime_value, 12)

        # user created with company uses default company info in TTuserinfo
        user = CustomUser.objects.create(first_name='temp', last_name='employee', email='temployee@test.com',
                                         company=company)
        u_info = TTUserInfo.objects.filter(user=user)
        self.assertTrue(u_info)
        self.assertEqual(u_info[0].daily_overtime_value, 12)

        # user created without company creates company and TTuserinfo is set to teh defaults defined by that company
        user = CustomUser.objects.create(first_name='mo', last_name='tou', email='moto@test.com')
        self.assertTrue(user.company)
        c_info = TTCompanyInfo.objects.filter(company=user.company)
        self.assertTrue(c_info)
        self.assertEqual(c_info[0].default_daily_overtime_value, 8)
        u_info = TTUserInfo.objects.filter(user=user)
        self.assertTrue(u_info)
        self.assertEqual(u_info[0].daily_overtime_value, 8)

    def test_user_with_clock_actions(self):
        company = Company.objects.create(name='Test')
        user = CustomUser.objects.create(first_name='temp', last_name='employee', email='temployee@test.com',
                                         company=company)

        clock_in = InOutAction.objects.create(type='t', user=user)
        self.assertEqual(clock_in.action_lookup_datetime, clock_in.start)
        self.assertEqual(clock_in.total_time, 0)

        user_info = TTUserInfo.objects.filter(user=user)[0]
        self.assertEqual(user_info.time_action, clock_in)

        clock_in.end = timezone.now()
        clock_in.save()

        self.assertEqual(clock_in.action_lookup_datetime, clock_in.end)
        self.assertTrue(clock_in.total_time > 0)

        user_info = TTUserInfo.objects.filter(user=user)[0]
        self.assertEqual(user_info.time_action, clock_in)

        break_in = InOutAction.objects.create(type='b', user=user)
        self.assertEqual(break_in.action_lookup_datetime, break_in.start)
        self.assertEqual(break_in.total_time, 0)

        user_info = TTUserInfo.objects.filter(user=user)[0]
        self.assertEqual(user_info.break_action, break_in)

        break_in.end = timezone.now()
        break_in.save()

        self.assertEqual(break_in.action_lookup_datetime, break_in.end)
        self.assertTrue(break_in.total_time > 0)

        user_info = TTUserInfo.objects.filter(user=user)[0]
        self.assertEqual(user_info.break_action, break_in)


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


class TestReport(TestCase):
    """
    Test the report generator
    """

    def test_report_engine(self):
        # test data is a representation of the database, we will use it create a temp database and then run a report on
        # it and verify the results against test_answers
        test_data = [
            {'company': {
                'data': {'name': 'Empire'},
                'tt_data': {'pay_period_type': 'b',
                            'week_start_day': 0,
                            'default_weekly_overtime': True,
                            'default_weekly_overtime_value': 40,
                            'default_daily_overtime': True,
                            'default_daily_overtime_value': 8,
                            'default_double_time': True,
                            'default_double_time_value': 12,
                            'default_enable_breaks': True,
                            'default_breaks_are_paid': False,
                            'default_include_breaks_in_overtime_calculation': False,
                            'use_company_defaults_for_all_employees': False,
                            'display_employee_times_with_timezone': True,
                            'california_overtime': False, },
                'employees': [
                    {
                        'data': {
                            'first_name': 'bill',
                            'last_name': 'caspy',
                            'email': 'billy@temp.com'
                        },
                        'tt_data': {'use_company_default_overtime_settings': False,
                                    'weekly_overtime': True,
                                    'weekly_overtime_value': 50,
                                    'daily_overtime': True,
                                    'daily_overtime_value': 9,
                                    'double_time': False,
                                    'double_time_value': 12,
                                    'use_company_default_break_settings': True},
                        'actions': [
                            {'start': datetime(year=2023, month=2, day=7, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=11, minute=00, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=12, minute=30, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=8, minute=15, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=8, minute=30, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=13, minute=20, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=13, minute=40, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=8, hour=4, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=8, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=9, hour=6, minute=30, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=9, hour=13, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=12, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=13, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=11, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=11, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=17, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=9, minute=50, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=11, minute=10, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=11, minute=45, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=13, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=13, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=14, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=14, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=15, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=15, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=15, hour=11, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=15, hour=11, minute=55, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=16, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=16, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=17, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=17, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=18, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=18, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=18, hour=10, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=18, hour=10, minute=59, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=19, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=19, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=20, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=21, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=20, hour=12, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=20, hour=12, minute=50, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=18, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=10, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=10, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=13, minute=0, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=13, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=24, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=24, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=25, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=25, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=26, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=26, hour=14, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=27, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=27, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'}]
                    },
                    {
                        'data': {
                            'first_name': 'darth',
                            'last_name': 'vader',
                            'middle_name': 'A',
                            'email': 'vader@temp.com',
                        },
                        'tt_data': {'use_company_default_overtime_settings': False,
                                    'weekly_overtime': True,
                                    'weekly_overtime_value': 30,
                                    'daily_overtime': True,
                                    'daily_overtime_value': 5,
                                    'double_time': True,
                                    'double_time_value': 7,
                                    'use_company_default_break_settings': False,
                                    'enable_breaks': True,
                                    'breaks_are_paid': True,
                                    'include_breaks_in_overtime_calculation': True,
                                    'california_overtime': False},
                        'actions': [
                            {'start': datetime(year=2023, month=2, day=7, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=11, minute=00, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=12, minute=30, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=8, minute=15, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=8, minute=30, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=13, minute=20, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=13, minute=40, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=8, hour=4, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=8, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=9, hour=6, minute=30, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=9, hour=13, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=12, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=13, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=11, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=11, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=17, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=9, minute=50, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=11, minute=10, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=11, minute=45, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=13, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=13, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=14, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=14, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=15, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=15, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=15, hour=11, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=15, hour=11, minute=55, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=16, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=16, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=17, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=17, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=18, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=18, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=18, hour=10, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=18, hour=10, minute=59, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=19, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=19, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=20, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=21, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=20, hour=12, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=20, hour=12, minute=50, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=18, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=10, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=10, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=13, minute=0, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=13, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=24, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=24, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=25, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=25, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=26, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=26, hour=14, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=27, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=27, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'}]
                    },
                    {
                        'data': {
                            'first_name': 'luke',
                            'last_name': 'skywalker',
                            'email': 'sith@temp.com'
                        },
                        'tt_data': {'use_company_default_overtime_settings': True,
                                    'use_company_default_break_settings': True},
                        'actions': [
                            {'start': datetime(year=2023, month=2, day=7, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=11, minute=00, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=12, minute=30, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=8, minute=15, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=8, minute=30, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=13, minute=20, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=13, minute=40, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=8, hour=4, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=8, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=9, hour=6, minute=30, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=9, hour=13, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=12, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=13, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=11, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=11, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=17, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=9, minute=50, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=11, minute=10, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=11, minute=45, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=13, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=13, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=14, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=14, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=15, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=15, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=15, hour=11, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=15, hour=11, minute=55, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=16, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=16, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=17, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=17, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=18, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=18, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=18, hour=10, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=18, hour=10, minute=59, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=19, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=19, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=20, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=21, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=20, hour=12, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=20, hour=12, minute=50, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=18, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=10, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=10, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=13, minute=0, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=13, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=24, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=24, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=25, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=25, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=26, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=26, hour=14, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=27, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=27, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'}]
                    },
                    {
                        'data': {
                            'first_name': 'darth',
                            'last_name': 'vader2',
                            'middle_name': 'A',
                            'email': 'vader2@temp.com',
                        },
                        'tt_data': {'use_company_default_overtime_settings': False,
                                    'weekly_overtime': True,
                                    'weekly_overtime_value': 30,
                                    'daily_overtime': True,
                                    'daily_overtime_value': 5,
                                    'double_time': True,
                                    'double_time_value': 7,
                                    'use_company_default_break_settings': False,
                                    'enable_breaks': True,
                                    'breaks_are_paid': True,
                                    'include_breaks_in_overtime_calculation': True,
                                    'california_overtime': True},
                        'actions': [
                            {'start': datetime(year=2023, month=2, day=7, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=11, minute=00, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=12, minute=30, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=8, minute=15, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=8, minute=30, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=7, hour=13, minute=20, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=7, hour=13, minute=40, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=8, hour=4, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=8, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=9, hour=6, minute=30, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=9, hour=13, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=12, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=13, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=10, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=10, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=11, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=11, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=17, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=9, minute=50, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=12, hour=11, minute=10, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=12, hour=11, minute=45, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=13, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=13, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=14, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=14, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=15, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=15, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=15, hour=11, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=15, hour=11, minute=55, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=16, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=16, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=17, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=17, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=18, hour=5, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=18, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=18, hour=10, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=18, hour=10, minute=59, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=19, hour=9, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=19, hour=15, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=20, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=21, hour=7, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=20, hour=12, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=20, hour=12, minute=50, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=6, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=18, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=10, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=10, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=23, hour=13, minute=0, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=23, hour=13, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 'b',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=24, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=24, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=25, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=25, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=26, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=26, hour=14, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'},
                            {'start': datetime(year=2023, month=2, day=27, hour=7, minute=23, second=36,
                                               tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'end': datetime(year=2023, month=2, day=27, hour=16, minute=31, second=7,
                                             tzinfo=timezone.timezone(timedelta(hours=-7))),
                             'type': 't',
                             'comment': 'Feeling regular'}]
                    },
                ]
            }}
        ]

        test_answers = [{'name': 'Caspy, Bill', 'timezone': 'UTC-07:00', 'paid_breaks': False, 'total': 114.23000000000002,
                         'break': 2.2, 'overtime': 22.360000000000014, 'previous_total': 17.26, 'previous_breaks': 0.0,
                         'weekly_overtime': 8.040000000000006, 'daily_overtime': 14.320000000000004, 'double_time': 0.0,
                         'regular': 91.87, 'total_with_break': 116.43000000000002, 'str_regular': '91.87',
                         'str_total_with_break': '116.43', 'str_total': '114.23', 'str_previous_total': '17.26',
                         'str_previous_breaks': '0.0', 'str_overtime': '22.36', 'str_daily_overtime': '14.32',
                         'str_weekly_overtime': '8.04', 'str_break': '2.2'},
                        {'name': 'Vader, Darth A', 'timezone': 'UTC-07:00', 'paid_breaks': True,
                         'total': 116.23000000000002, 'break': 2.2, 'overtime': 28.130000000000017,
                         'previous_total': 17.26, 'previous_breaks': 0.0, 'weekly_overtime': 5.000000000000018,
                         'daily_overtime': 23.13, 'double_time': 35.300000000000004, 'regular': 52.79999999999999,
                         'total_with_break': 118.43000000000002, 'str_regular': '52.8',
                         'str_total_with_break': '118.43', 'str_total': '116.23', 'str_previous_total': '17.26',
                         'str_previous_breaks': '0.0', 'str_overtime': '28.13', 'str_daily_overtime': '23.13',
                         'str_weekly_overtime': '5.0', 'str_break': '2.2'},
                        {'name': 'Skywalker, Luke', 'timezone': 'UTC-07:00', 'paid_breaks': False,
                         'total': 114.23000000000002, 'break': 2.2, 'overtime': 42.360000000000014,
                         'previous_total': 17.26, 'previous_breaks': 0.0, 'weekly_overtime': 42.360000000000014,
                         'daily_overtime': 0.0, 'double_time': 0.0, 'regular': 71.87,
                         'total_with_break': 116.43000000000002, 'str_regular': '71.87',
                         'str_total_with_break': '116.43', 'str_total': '114.23', 'str_previous_total': '17.26',
                         'str_previous_breaks': '0.0', 'str_overtime': '42.36', 'str_daily_overtime': '0.0',
                         'str_weekly_overtime': '42.36', 'str_break': '2.2'},
                        {'name': 'Vader2, Darth A', 'timezone': 'UTC-07:00', 'paid_breaks': True,
                         'total': 116.23000000000002, 'break': 2.2, 'overtime': 22.000000000000007,
                         'previous_total': 17.26, 'previous_breaks': 0.0, 'weekly_overtime': 7.105427357601002e-15,
                         'daily_overtime': 22.0, 'double_time': 41.43000000000001, 'regular': 52.80000000000001,
                         'total_with_break': 118.43000000000002, 'str_regular': '52.8',
                         'str_total_with_break': '118.43', 'str_total': '116.23', 'str_previous_total': '17.26',
                         'str_previous_breaks': '0.0', 'str_overtime': '22.0', 'str_daily_overtime': '22.0',
                         'str_weekly_overtime': '0.0', 'str_break': '2.2'}]

        company = Company(**test_data[0]['company']['data'])
        company.save()
        company_info = TTCompanyInfo.objects.get(company=company)

        tt_data = test_data[0]['company']['tt_data']
        for key in tt_data:
            setattr(company_info, key, tt_data[key])
        company_info.save()

        begin_date = date(year=2023, month=2, day=15)
        end_date = date(year=2023, month=2, day=28)

        real_emps = []
        emp_id_list = []
        real_tt_emps = []
        employees = test_data[0]['company']['employees']
        for employee in employees:
            temp_emp = CustomUser(**employee['data'])
            temp_emp.save()
            tt_emp_info = TTUserInfo.objects.get(user=temp_emp)
            for key in employee['tt_data']:
                setattr(tt_emp_info, key, employee['tt_data'][key])
            tt_emp_info.save()
            real_tt_emps.append(tt_emp_info)
            real_emps.append(temp_emp)
            emp_id_list.append(temp_emp.id)
            actions = employee['actions']
            for action in actions:
                new_action = InOutAction(**action, user=temp_emp)
                new_action.save()

        override_timezone = timezone.timezone(timedelta(hours=-7))

        form_settings = {
            'begin_date': begin_date,
            'end_date': end_date,
            'other_hours_format': 'decimal',
            'other_rounding': '5',
        }

        full_beg_date, full_end_date, time_actions_list = get_time_actions_list(form=form_settings,
                                                                                employee_id_list=emp_id_list,
                                                                                company_info=company_info,
                                                                                override_timezone=override_timezone)

        report_engine = Report(employee_list=real_tt_emps, time_actions_list=time_actions_list,
                               form=form_settings, full_beg_date=full_beg_date, full_end_date=full_end_date,
                               company=company, company_info=company_info, override_timezone=override_timezone)

        detailed_hours_report = report_engine.make_detailed_hours_report()

        for index, answer_employee in enumerate(test_answers):
            result_employee = detailed_hours_report['employees'][index]
            del result_employee['weeks']
            self.assertEqual(answer_employee, result_employee)


class TestPayPeriod(TestCase):
    def test_weekly(self):
        begin_date = date(2023, 3, 1)
        expected_begin_date = date(2023, 3, 8)
        expected_end_date = date(2023, 3, 14)
        self.assertEqual(get_pay_period_dates('w', begin_date), (expected_begin_date, expected_end_date))

        begin_date = date(2023, 2, 27)
        expected_begin_date = date(2023, 3, 6)
        expected_end_date = date(2023, 3, 12)
        self.assertEqual(get_pay_period_dates('w', begin_date), (expected_begin_date, expected_end_date))

        begin_date = date(2021, 3, 2)
        expected_begin_date = date(2023, 3, 7)
        expected_end_date = date(2023, 3, 13)
        self.assertEqual(get_pay_period_dates('w', begin_date), (expected_begin_date, expected_end_date))

    def test_biweekly(self):
        begin_date = date(2023, 2, 28)
        expected_begin_date = date(2023, 2, 28)
        expected_end_date = date(2023, 3, 13)
        self.assertEqual(get_pay_period_dates('b', begin_date), (expected_begin_date, expected_end_date))

        begin_date = date(2021, 3, 2)
        expected_begin_date = date(2023, 2, 28)
        expected_end_date = date(2023, 3, 13)
        self.assertEqual(get_pay_period_dates('b', begin_date), (expected_begin_date, expected_end_date))

        begin_date = date(2021, 3, 8)
        expected_begin_date = date(2023, 3, 6)
        expected_end_date = date(2023, 3, 19)
        self.assertEqual(get_pay_period_dates('b', begin_date), (expected_begin_date, expected_end_date))

    def test_semimonthly(self):
        begin_date = date(2023, 3, 1)
        expected_begin_date = date(2023, 3, 1)
        expected_end_date = date(2023, 3, 15)
        self.assertEqual(get_pay_period_dates('s', begin_date), (expected_begin_date, expected_end_date))

    def test_monthly(self):
        begin_date = date(2023, 2, 1)
        expected_begin_date = date(2023, 3, 1)
        expected_end_date = date(2023, 3, 31)
        self.assertEqual(get_pay_period_dates('m', begin_date), (expected_begin_date, expected_end_date))

        begin_date = date(2023, 2, 5)
        expected_begin_date = date(2023, 3, 5)
        expected_end_date = date(2023, 4, 4)
        self.assertEqual(get_pay_period_dates('m', begin_date), (expected_begin_date, expected_end_date))

        begin_date = date(2019, 12, 5)
        expected_begin_date = date(2023, 3, 5)
        expected_end_date = date(2023, 4, 4)
        self.assertEqual(get_pay_period_dates('m', begin_date), (expected_begin_date, expected_end_date))
