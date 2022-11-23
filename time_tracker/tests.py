from django.test import TestCase
from users.models import CustomUser, Company
from .models import TTUserInfo, TTCompanyInfo, InOutAction
from django.utils import timezone


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
        user = CustomUser.objects.create(first_name='temp', last_name='employee', email='temployee@test.com', company=company)
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
