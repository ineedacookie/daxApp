import logging

from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .forms import CompanyForm, UserForm, OverriddenPasswordChangeForm, OverriddenAdminPasswordChangeForm, RegisterUserForm, InviteCombinedForm, InviteEmployeesForm
from .models import CustomUser, Company
from .tokens import account_activation_token
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes

from django.conf import settings
from .utils import urlsafe_base64_encode, check_employee_form, get_selectable_employees, send_email_with_link
from pytz import timezone
from daxApp.central_data import get_main_page_data

from time_tracker.models import TTUserInfo

logger = logging.getLogger("django.request")


def landing_page(request):
    page = 'general/landing.html'
    page_arguments = {}
    return render(request, page, page_arguments)


@login_required
def home(request):
    """Main page that is the root of the website"""
    """check that the user is logged in. if not send them to the log in page."""
    # if not request.user.password:
    #     return create_account(request)
    """Checks whether the user is part of the staff or a customer"""
    if request.user.is_staff:
        return redirect('/io_admin')
    else:
        page = 'general/home.html'
        page_arguments = get_main_page_data(request.user, get_tt_employees=True)
        return render(request, page, page_arguments)  # fill the {} with arguments


def register_account(request):
    """This view allows a new user to register for an account not linked to any company."""
    page = 'registration/register.html'
    page_arguments = {}
    form = None
    if request.method == 'POST':
        form = RegisterUserForm(request.POST)
        if form.is_valid():
            register_user = form.save(commit=False)
            register_user.is_active = False
            register_user.save()

            send_email_with_link(register_user, request)

            page = 'registration/account_created.html'
            page_arguments = {}
        else:
            page_arguments['form'] = form

    if not form:
        page_arguments['form'] = RegisterUserForm()
    return render(request, page, page_arguments)


@login_required
def manage_employees(request):
    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    else:
        page = 'general/employees.html'
        page_arguments = get_main_page_data(request.user, get_employee_list=True)
        return render(request, page, page_arguments)


@login_required
def invite_employees(request):
    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    else:
        if request.method == 'POST':
            company = request.user.company
            emails = request.POST.get('emails', '')
            if emails:
                emails = emails.split(',')
                for email in emails:
                    try:
                        form = InviteEmployeesForm({'email': email, 'company': company})
                        if form.is_valid():
                            form.save()
                    except Exception as e:
                        logger.error("Failed to invite an email, perhaps the email was invalid or already used.")
                        logger.error(e)


@login_required
def company_settings(request):
    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    else:
        page = 'settings/company_settings.html'
        page_arguments = get_main_page_data(request.user)
        if request.method == 'POST':
            form = CompanyForm(request.POST, instance=request.user.company)
            if form.is_valid():
                form.save()
        else:
            form = CompanyForm(instance=request.user.company)

        page_arguments['company_form'] = form
        return render(request, page, page_arguments)


@login_required
def selectable_employees(request):
    """
    Returns a list of selectable employees depending on who the user is and what their permissions are.
    """
    return_list = []
    more = False
    if request.GET:
        query = request.GET.get('q', '')
        page = request.GET.get('page', 1)
        if query:
            query = query.upper()
        user = request.user
        # TODO flesh this out so permissions are more exclusive
        return_list, more = get_selectable_employees(user, page, query)

    return JsonResponse({
        'results': return_list,
        'pagination': {
            'more': more
        }
    })


#
#
# @login_required
# def create_account(request):
#     """This view is for users that are creating their password for the first time"""
#     page = 'create_account.html'
#     page_arguments = {}
#     role = request.user.role
#
#     if role == 'r' or role == 'e':
#         form = None
#         if request.method == 'POST':
#             form = OverriddenAdminPasswordChangeForm(request.user, request.POST)
#             if form.is_valid():
#                 form.save()
#                 update_session_auth_hash(request, request.user)
#                 messages.success(request, 'Password created successfully')
#                 return redirect('home')
#             else:
#                 messages.warning(request, 'Please correct the error below')
#
#         if not form:
#             form = OverriddenAdminPasswordChangeForm(request.user)
#         page_arguments['form'] = form
#
#     return render(request, page, page_arguments)
#
#
# @login_required
# def dashboard(request):
#     """This view displays the admin dashboard which has the employee list."""
#     page = 'dashboard.html'
#     page_arguments = {}
#     role = request.user.role
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role == "c" or role == "r":
#         cur_page = request.GET.get('page')
#         query = request.GET.get('q')
#
#         # If information is being submitted or saved this will execute.
#         if query:
#             employee_list = CustomUser.objects.filter(company=request.user.company).exclude(
#                 role="c").filter(Q(first_name__icontains=query) | Q(last_name__icontains=query)).order_by(
#                 'last_name', 'first_name').values('id', 'first_name', 'middle_name', 'last_name', 'timezone',
#                                                   'time_action__type', 'time_action__action_datetime',
#                                                   'time_action__comment')
#         else:
#             employee_list = CustomUser.objects.filter(company=request.user.company).exclude(
#                 role="c").order_by('last_name', 'first_name').values('id', 'first_name', 'middle_name', 'last_name',
#                                                                      'timezone', 'time_action__type',
#                                                                      'time_action__action_datetime',
#                                                                      'time_action__comment')
#
#         # Not sure if the statement above needs these but values are accessible from this end
#         # .select_related('time_action')
#         # .values('id', 'last_login', 'email', 'first_name', 'middle_name', 'last_name', 'role',
#         #                                  'is_active', 'created_date')
#
#         possible_actions = {'i': 'In', 'o': 'Out', 'b': 'On Break', 'e': 'Ended Break'}
#
#         """Getting the timezone to use"""
#         timezone = None
#         company_timezone = request.user.company.timezone
#         dis_emp_time_in_their_timezone = request.user.company.display_employee_times_with_timezone
#         if request.user.company.use_company_timezone:
#             timezone = company_timezone
#         else:
#             timezone = request.user.timezone
#
#         if not dis_emp_time_in_their_timezone:
#             page_arguments['correct_timezone'] = timezone
#
#         """Splitting the datetime object"""
#         for employee in employee_list:
#             if dis_emp_time_in_their_timezone:
#                 timezone = employee['timezone']
#             if employee['time_action__action_datetime']:
#                 if not timezone:
#                     timezone = company_timezone
#                 if timezone:
#                     employee['time_action__action_datetime'] = employee['time_action__action_datetime'].astimezone(
#                         timezone)
#
#                 employee['date'] = employee['time_action__action_datetime'].strftime("%b %d")
#                 employee['time'] = employee['time_action__action_datetime'].strftime("%I:%M %p")
#                 employee['status'] = possible_actions[employee['time_action__type']]
#
#         """This creates a paginator that has a max of 25 employees per page."""
#         paginator = Paginator(employee_list, 25)
#         try:
#             page_arguments['paginator_view'] = paginator.page(cur_page)
#             page_arguments['paginator_cur_page'] = int(cur_page)
#         except PageNotAnInteger:
#             page_arguments['paginator_view'] = paginator.page(1)
#             page_arguments['paginator_cur_page'] = 1
#         except EmptyPage:
#             page_arguments['paginator_view'] = paginator.page(paginator.num_pages)
#             page_arguments['paginator_cur_page'] = int(paginator.num_pages)
#         # See why just the number wouldn't have worked here: https://code.djangoproject.com/ticket/5172
#         page_arguments['paginator_range_num_pages'] = range(1,
#                                                             paginator.num_pages + 1)  # The paginator is 1-indexed
#
#         # TODO Create and connect admin home screen
#         pass
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#     # check for a post call, and if so update information accordingly. Used for clock actions and others
#     return render(request, page, page_arguments)  # fill the {} with arguments
#
#
# @login_required
# def company_settings(request):
#     page = 'admin/company_settings.html'
#     page_arguments = {}
#     role = request.user.role
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role == "c" or role == "r":
#         form = None
#
#         # If information is being submitted or saved this will execute.
#         if request.method == 'POST':
#             form = CompanyForm(request.POST, instance=request.user.company)
#             if form.is_valid():
#                 form.save()
#                 messages.success(request, 'Company settings saved successfully')
#             else:
#                 messages.warning(request, 'Please correct the error below')
#
#         # TODO figure out about showing details in regards to subscription
#         page_arguments['company'] = request.user.company
#
#         # If someone already submitted a form the get the form object from before.
#         page_arguments['form'] = CompanyForm(instance=request.user.company)
#
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#     # check for a post call, and if so update information accordingly. Used for clock actions and others
#     return render(request, page, page_arguments)  # fill the {} with arguments
#
#
# @login_required
# def create_employee(request):
#     page = 'admin/create_or_edit_employee.html'
#     page_arguments = {}
#     role = request.user.role
#
#     form = None
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role == "c" or role == "r":
#         page_arguments['title_type'] = 'Add'
#
#         # If information is being submitted or saved this will execute.
#         if request.method == 'POST':
#             form = EmployeeForm(request.POST)
#             if form.is_valid():
#                 employee = form.save(commit=False)
#                 employee.company = request.user.company
#                 employee.is_active = False
#                 employee.save()
#
#                 current_site = get_current_site(request)
#                 mail_subject = 'Activate Online TimeClick Account.'
#                 message = render_to_string('acc_active_email.html', {
#                     'user': employee,
#                     'domain': current_site.domain,
#                     'uid': urlsafe_base64_encode(force_bytes(employee.pk)),
#                     'token': account_activation_token.make_token(employee),
#                 })
#                 to_email = form.cleaned_data.get('email')
#                 send_mail(
#                     mail_subject,
#                     message,
#                     settings.DEFAULT_FROM_EMAIL,
#                     [to_email],
#                     fail_silently=False,
#                 )
#
#                 messages.success(request, 'Employee created, and validation email sent to their email')
#                 if request.POST.get('_addanother'):
#                     return redirect('create_employee')
#                 else:
#                     return redirect('dashboard')
#             else:
#                 messages.warning(request, 'Please correct the error below')
#                 page_arguments['form'] = form
#
#         if not form:
#             page_arguments['form'] = EmployeeForm()
#
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#     # check for a post call, and if so update information accordingly. Used for clock actions and others
#     return render(request, page, page_arguments)  # fill the {} with arguments
#
#
# @login_required
# def edit_employee(request, employee_id):
#     page = 'admin/create_or_edit_employee.html'
#     page_arguments = {}
#     role = request.user.role
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role == "c" or role == "r":
#         page_arguments['title_type'] = 'Edit'
#         page_arguments['employee_id'] = employee_id
#         employee = CustomUser.objects.get(id=employee_id)
#         if employee.company == request.user.company:
#             page_arguments['can_delete'] = True
#             if employee.is_active:
#                 page_arguments['status'] = 'Active'
#             else:
#                 page_arguments['status'] = 'Confirmation Email Sent'
#             form = None
#
#             # If information is being submitted or saved this will execute.
#             if request.method == 'POST':
#                 initial_email = employee.email
#                 form = EmployeeForm(request.POST, instance=employee)
#                 response = check_employee_form(get_current_site(request), form, initial_email)
#                 if response['success']:
#                     if response['change_email']:
#                         messages.success(request, "Validation email sent to employee's email")
#                         pass
#                     messages.success(request, "Employee settings saved successfully")
#                     redirect('dashboard')
#                 else:
#                     messages.warning(request, "Please fix the error below")
#                     form = response['form']
#
#             # If someone already submitted a form the get the form object from before.
#             if form:
#                 page_arguments['form'] = form
#             else:
#                 page_arguments['form'] = EmployeeForm(instance=employee)
#
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#     # check for a post call, and if so update information accordingly. Used for clock actions and others
#     return render(request, page, page_arguments)  # fill the {} with arguments
#
#
# @login_required
# def delete_employee(request, employee_id):
#     role = request.user.role
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role == "c" or role == "r":
#         employee = CustomUser.objects.get(id=employee_id)
#         if not employee == request.user:
#             if not employee.role == "c":
#                 if employee.company == request.user.company:
#                     employee.delete()
#                     messages.success(request, 'Employee deleted successfully')
#                     return redirect('dashboard')
#                 else:
#                     messages.warning(request, 'You cannot delete an employee that does not belong to your company')
#                     logger.error(
#                         'No user with that id exists in your company \n \n User Info:' + str(
#                             request.user))
#             else:
#                 messages.warning(request, 'You cannot delete the company administrator')
#                 logger.error(
#                     'You cannot delete the company administrator \n \n User Info:' + str(
#                         request.user))
#         else:
#             messages.warning(request, 'You cannot delete yourself')
#             logger.error(
#                 'You cannot delete yourself \n \n User Info:' + str(
#                     request.user))
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#     # check for a post call, and if so update information accordingly. Used for clock actions and others
#     return redirect('dashboard')
#
#
# @login_required
# def send_confirmation_email(request, employee_id):
#     role = request.user.role
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role == "c" or role == "r":
#         employee = CustomUser.objects.get(id=employee_id)
#         if request.user.company == employee.company:
#             if employee.is_active:
#                 logger.error(
#                     'Employee is already marked as active \n \n User Info:' + str(
#                         request.user))
#                 messages.warning(request, 'Employee has already validated their email address')
#                 return redirect('home')
#             else:
#                 current_site = get_current_site(request)
#                 mail_subject = 'Activate Online TimeClick Account.'
#                 message = render_to_string('acc_active_email.html', {
#                     'user': employee,
#                     'domain': current_site.domain,
#                     'uid': urlsafe_base64_encode(force_bytes(employee.pk)),
#                     'token': account_activation_token.make_token(employee),
#                 })
#                 to_email = employee.email
#                 send_mail(
#                     mail_subject,
#                     message,
#                     settings.DEFAULT_FROM_EMAIL,
#                     [to_email],
#                     fail_silently=False,
#                 )
#                 messages.success(request, 'Validation email resent')
#                 return redirect('edit_employee', employee_id=employee_id)
#         else:
#             logger.error(
#                 'User does not belong to the company of the logged in admin \n \n User Info:' + str(
#                     request.user))
#             messages.warning(request, 'You do not have access to employees outside of your company')
#             return redirect('home')
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#
#
# @login_required
# def edit_account_settings(request):
#     page = 'edit_account_settings.html'
#     page_arguments = {}
#     role = request.user.role
#     initial_email = request.user.email
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role == "c" or role == "r":
#
#         page = 'admin/edit_account_settings.html'
#         # If information is being submitted or saved this will execute.
#         if request.method == 'POST':
#             form = AdminAccountForm(request.POST, instance=request.user, company=request.user.company)
#             response = check_employee_form(get_current_site(request), form, initial_email)
#             if response['success']:
#                 if response['change_email']:
#                     messages.success(request, 'Sent email to new email address for validation')
#                 messages.success(request, 'Saved your account settings')
#                 redirect('home')
#             else:
#                 messages.warning(request, 'Please fix the error below')
#                 form = response['form']
#         else:
#             form = AdminAccountForm(instance=request.user, company=request.user.company)
#
#         page_arguments['form'] = form
#
#     elif role == "e" or role == "r":
#         # If information is being submitted or saved this will execute.
#         if request.method == 'POST':
#             form = EmployeeAccountForm(request.POST, instance=request.user, company=request.user.company)
#             response = check_employee_form(get_current_site(request), form, initial_email)
#             if response['success']:
#                 if response['change_email']:
#                     messages.success(request, 'Sent email to new email address for validation')
#                 messages.success(request, 'Saved your account settings')
#                 return redirect('home')
#             else:
#                 messages.warning(request, 'Please fix the error below')
#                 form = response['form']
#         else:
#             form = EmployeeAccountForm(instance=request.user, company=request.user.company)
#
#         page_arguments['form'] = form
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#     # check for a post call, and if so update information accordingly. Used for clock actions and others
#     page_arguments['company'] = request.user.company
#     return render(request, page, page_arguments)  # fill the {} with arguments
#
#
# @login_required
# def change_password(request):
#     page = 'change_password.html'
#     page_arguments = {}
#     role = request.user.role
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role:
#         if role == 'c' or role == 'r':
#             page_arguments['template'] = 'admin.html'
#         else:
#             page_arguments['template'] = 'employee.html'
#
#         # If information is being submitted or saved this will execute.
#         if request.method == 'POST':
#             form = OverriddenPasswordChangeForm(request.user, request.POST)
#             if form.is_valid():
#                 form.save()
#                 update_session_auth_hash(request, form.user)
#                 messages.success(request, 'Updated password successfully')
#                 return redirect('account_settings')
#             else:
#                 messages.warning(request, 'Please fix the error below')
#         else:
#             form = OverriddenPasswordChangeForm(request.user)
#
#         page_arguments['form'] = form
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#     # check for a post call, and if so update information accordingly. Used for clock actions and others
#     return render(request, page, page_arguments)  # fill the {} with arguments
#
#
# @login_required
# def admin_change_password(request, employee_id):
#     page = 'change_password.html'
#     page_arguments = {'template': "admin.html"}
#     role = request.user.role
#
#     """Checks whether the user is a timeclick employee, an employee, or an admin"""
#     if request.user.is_staff:
#         return redirect('/io_admin')
#     elif role == "c" or role == "r":
#         form = None
#         employee = CustomUser.objects.get(id=employee_id)
#
#         if employee.company == request.user.company:
#             page_arguments['name'] = employee.last_name + ', ' + employee.first_name
#
#             # If information is being submitted or saved this will execute.
#             if request.method == 'POST':
#                 form = OverriddenAdminPasswordChangeForm(employee, request.POST)
#                 if form.is_valid():
#                     form.save()
#                     messages.success(request, 'Updated employee password successfully')
#                     return redirect('edit_employee', employee_id=employee_id)
#                 else:
#                     messages.warning(request, 'Please fix the error below')
#             else:
#                 form = OverriddenAdminPasswordChangeForm(employee)
#
#             page_arguments['form'] = form
#         else:
#             logger.error(
#                 'Someone that is an admin but not part of the same company is trying to change another users password \n \n User Info:' + str(
#                     request.user))
#             return redirect('home')
#
#     else:
#         logger.error(
#             'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
#                 request.user))
#         return redirect('home')
#     # check for a post call, and if so update information accordingly. Used for clock actions and others
#     return render(request, page, page_arguments)  # fill the {} with arguments
#
#
def activate_account(request, uidb64, token):
    """This page is for validating an email and getting the initial password set for a user."""
    page = 'registration/activation_link.html'
    page_arguments = {}
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        page = 'registration/set_initial_password.html'
        if request.POST:
            form = OverriddenAdminPasswordChangeForm(user, request.POST)
            if form.is_valid():
                form.save()
                user.is_active = True
                if user.change_email:
                    user.email = user.change_email
                    user.change_email = None
                user.save()
                login(request, user)
                return redirect('home')
        else:
            form = OverriddenAdminPasswordChangeForm(user)
        page_arguments['form'] = form
    return render(request, page, page_arguments)


def invited_account(request, uidb64, token):
    """This page is for validating an email and getting the initial info and password set for a user."""
    page = 'registration/activation_link.html'
    page_arguments = {}
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        page = 'registration/initial_info_collection.html'
        if request.POST:
            form = InviteCombinedForm(user, request.POST)
            if form.is_valid():
                form.save()
                user.is_active = True
                user.save()
                login(request, user)
                return redirect('home')
        else:
            form = InviteCombinedForm(user)
        page_arguments['form'] = form
    return render(request, page, page_arguments)


def handler404(request, *args, **argv):
    page = 'general/404.html'
    return render(request, page, {}, status=404)


def handler500(request, *args, **argv):
    page = 'general/500.html'
    return render(request, page, {}, status=500)