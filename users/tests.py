from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from .forms import *
from .utils import check_employee_form
from .tokens import account_activation_token

class UsersManagersTests(TestCase):
    """
    Things to test:
        1. that built in function of model work
        2. creating super user works
        3. that defaults are being set
    """

    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(email='normal@user.com', password='foo')
        self.assertEqual(user.email, 'normal@user.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.theme == 1)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(user.username)
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(email='')
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password="foo")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email='normal@user.com', password='foo')

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser('super@user.com', 'foo')
        self.assertEqual(admin_user.email, 'super@user.com')
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='super@user.com', password='foo', is_superuser=False)


class CompanyModelTests(TestCase):
    """
    Things to Test:
        1. Can create company
        2. Defaults are being set
        3. Company can be deleted
        4. Employees can be connected to company
        5. When company is deleted so are the employee connections and the company is removed from the employees
        6. Assert that employees still exist as individuals  when a company is deleted.
    """

    def test_company(self):
        num_emps = 20

        new_com = Company.objects.create(name="Test Company")
        self.assertEqual(new_com.name, 'Test Company')
        self.assertFalse(new_com.use_company_timezone)

        for i in range(num_emps):
            new_user = CustomUser.objects.create(email=(str(i) + '@gmail.com'), password='foo', first_name=str(i), last_name=str(i), company=new_com)
            CompanyConnection.objects.create(company=new_com, user=new_user)

        employees = CustomUser.objects.filter(company=new_com)
        employee_connections = CompanyConnection.objects.filter(company=new_com)
        self.assertEqual(employees.count(), num_emps)
        self.assertEqual(employee_connections.count(), num_emps)
        company_id = new_com.id
        new_com.delete()
        with self.assertRaises(Company.DoesNotExist):
            Company.objects.get(id=company_id)
        employees = CustomUser.objects.filter(company=company_id)
        employee_connections = CompanyConnection.objects.filter(company=new_com)
        self.assertEqual(employees.count(), 0)
        self.assertEqual(employee_connections.count(), 0)

        # assert that employees still exist as individuals when the company is deleted.
        users = CustomUser.objects.all()
        self.assertEqual(users.count(), 20)



class FormTests(TestCase):
    """
    Forms to test:
        CustomUserCreationForm, CompanyForm, EmployeeForm, AdminAccountForm, EmployeeAccountForm
    """
    def setUp(self):
        self.company = Company.objects.create(name='initial company')

    def test_customusercreationform(self):
        form = CustomUserCreationForm(data={'email': 'junk@gmail.com', 'password1': 'hawkeye200', 'password2': 'hawkeye200'})
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(CustomUser.objects.get(email='junk@gmail.com'))
        form = CustomUserCreationForm(
            data={'email': 'junk@gmail.com', 'password1': 'foo', 'password2': 'foo'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'email': ['User with this Email already exists.'], 'password2': ['This password is too short. It must contain at least 8 characters.']})
        with self.assertRaises(ValueError):
            form.save()
        form = CustomUserCreationForm(
            data={'email': 'junk', 'password1': 'hawkeye200', 'password2': 'hawkeye200'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'email': ['Enter a valid email address.']})
        with self.assertRaises(ValueError):
            form.save()

    def test_companyform(self):
        company = Company.objects.create(name='initial company')
        form = CompanyForm(data={'name': 'replacement_name', 'timezone': 'America/Denver'}, instance=company)
        self.assertTrue(form.is_valid())
        form.save()
        fetch_company = Company.objects.get(id=company.id)
        self.assertTrue(fetch_company)
        self.assertEqual(fetch_company.name, 'replacement_name')
        form = CompanyForm(data={'name': 'replacement_name', 'timezone': 'AAAAAA', 'use_company_timezone': None},
                           instance=company)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'timezone': ['Select a valid choice. AAAAAA is not one of the available choices.']})
        with self.assertRaises(ValueError):
            form.save()
        form = CompanyForm(data={'name': 'a'*256, 'timezone': 'America/Denver'},
                           instance=company)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'name': ['Ensure this value has at most 255 characters (it has 256).']})

    def test_userform(self):
        form = UserForm(data={'first_name': 'gerald', 'last_name': 'bar', 'email': 'bar@gmail.com'})
        self.assertTrue(form.is_valid())
        form.save()
        temp_emp = CustomUser.objects.get(email='bar@gmail.com')
        self.assertTrue(temp_emp)
        form = UserForm(data={'first_name': 'golopogose', 'last_name': 'bar', 'email': 'bar@gmail.com'}, instance=temp_emp)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(CustomUser.objects.get(email='bar@gmail.com').first_name, 'golopogose')
        form = UserForm(data={'first_name': '', 'last_name': '', 'middle_name': 'a'*51, 'email': 'fakeemailsee'}, instance=temp_emp)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'first_name': ['This field is required.'], 'middle_name': ['Ensure this value has at most 50 characters (it has 51).'], 'last_name': ['This field is required.'], 'email': ['Enter a valid email address.']})
        form = UserForm(data={'first_name': 'different', 'last_name': 'foo', 'email': 'bar@gmail.com'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'email': ['User with this Email already exists.']})


class UtilsTests(TestCase):
    """
    These tests are for the functions within utils.py in this application
    """
    class Site:
        domain = 'junk.com'

    def setUp(self):
        self.employee = CustomUser.objects.create(first_name='Stan', last_name='Pines', email='stan@pineswoods.com')

    def test_check_employee_form(self):
        current_site = self.Site()
        initial_email = 'stan@pineswoods.com'
        form = UserForm(data={'first_name': 'Stan', 'last_name': 'Pinesworth', 'email': initial_email, 'timezone': 'America/Denver'}, instance=self.employee)
        response = check_employee_form(current_site, form, initial_email, send=False)
        self.assertTrue(response['success'])
        self.assertFalse(response['change_email'])
        form = UserForm(data={'first_name': 'Stan', 'last_name': 'Pines', 'email': 'stanford@pineswoods.com', 'timezone': 'America/Denver'},
                                   instance=self.employee)
        response = check_employee_form(current_site, form, initial_email, send=False)
        self.assertTrue(response['success'])
        self.assertTrue(response['change_email'])
        self.assertEqual(response['user'], 'Stan')
        self.assertEqual(response['domain'], current_site.domain)
        self.assertEqual(response['uid'], urlsafe_base64_encode(force_bytes(self.employee.pk)))
        self.assertTrue(account_activation_token.check_token(self.employee, response['token']))
        form = UserForm(data={'first_name': ''}, instance=self.employee)
        response = check_employee_form(current_site, form, initial_email, send=False)
        self.assertFalse(response['success'])
        self.assertFalse(response['change_email'])
