import logging

from clock_actions.forms import EmployeeTimeActionForm  # Correct syntax
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .forms import CompanyForm, EmployeeForm, AdminAccountForm, EmployeeAccountForm, OverriddenPasswordChangeForm, \
    OverriddenAdminPasswordChangeForm
from .models import CustomUser
from .tokens import account_activation_token
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from .utils import urlsafe_base64_encode, check_employee_form
from clock_actions.utils import get_timezone


@login_required
def home(request):
    """Main page that is the root of the website"""
    """check that the user is logged in. if not send them to the log in page."""
    if not request.user.password:
        return create_account(request)

    page = 'employee_home_page.html'
    page_arguments = {}
    role = request.user.role

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == 'e':
        options = {'i': 'o', 'o': 'i', 'b': 'e', 'e': 'o'}
        type_options = {'i': 'In', 'o': 'Out', 'b': 'On Break', 'e': 'Ended Break'}
        cur_action = request.user.time_action
        emp_timezone = get_timezone(request.user)
        if cur_action:
            prep_cur_action = {
                'action': True,
                'date': cur_action.action_datetime.astimezone(emp_timezone).strftime('%b %d, %Y'),
                'time': cur_action.action_datetime.astimezone(emp_timezone).strftime('%I:%M %p'),
                'type': type_options[cur_action.type]
            }
        else:
            prep_cur_action = {
                'action': False
            }
        try:
            if cur_action:
                selected = options[cur_action.type]
            else:
                selected = 'i'
        except KeyError:
            selected = 'i'
        page_arguments['cur_action'] = prep_cur_action
        page_arguments['selected'] = selected
        page_arguments['user_time_zone'] = emp_timezone.zone
        page_arguments['breaks'] = request.user.company.enable_breaks
        """check for a post call which would happen if an employee is clocking in
        , and if so update information accordingly. Used for clock actions and others"""
        if request.method == 'POST':
            form = EmployeeTimeActionForm(request.POST)
            if form.is_valid():
                time_action = form.save(commit=False)
                time_action.user = request.user
                # TODO this is the time to enter the employees lon and lad
                time_action.save()
                messages.success(request, 'Submitted ' + type_options[time_action.type] + ' Successfully')
                return redirect('home')
            else:
                messages.warning(request, 'Please fix the error below')

        form = EmployeeTimeActionForm(data={'type': selected})
        page_arguments['form'] = form
        # TODO create and connect employee home screen

    elif role == "c" or role == "r":
        """this is the place to update if you want the admin to control where they go initally when opening admin mode."""
        return redirect('admin/dashboard')
    else:
        logger.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def create_account(request):
    """This view is for users that are creating their password for the first time"""
    page = 'create_account.html'
    page_arguments = {}
    role = request.user.role

    if role == 'r' or role == 'e':
        form = None
        if request.method == 'POST':
            form = OverriddenAdminPasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password created successfully')
                return redirect('home')
            else:
                messages.warning(request, 'Please correct the error below')

        if not form:
            form = OverriddenAdminPasswordChangeForm(request.user)
        page_arguments['form'] = form

    return render(request, page, page_arguments)


@login_required
def admin_dashboard(request):
    """This view displays the admin dashboard which has the employee list."""
    page = 'admin/dashboard.html'
    page_arguments = {}
    role = request.user.role

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == "c" or role == "r":
        cur_page = request.GET.get('page')
        query = request.GET.get('q')

        # If information is being submitted or saved this will execute.
        if query:
            employee_list = CustomUser.objects.filter(company=request.user.company).exclude(
                role="c").filter(Q(first_name__icontains=query) | Q(last_name__icontains=query)).order_by(
                'last_name', 'first_name').values('id', 'first_name', 'middle_name', 'last_name', 'timezone',
                                                  'time_action__type', 'time_action__action_datetime',
                                                  'time_action__comment')
        else:
            employee_list = CustomUser.objects.filter(company=request.user.company).exclude(
                role="c").order_by('last_name', 'first_name').values('id', 'first_name', 'middle_name', 'last_name',
                                                                     'timezone', 'time_action__type',
                                                                     'time_action__action_datetime',
                                                                     'time_action__comment')

        # Not sure if the statement above needs these but values are accessible from this end
        # .select_related('time_action')
        # .values('id', 'last_login', 'email', 'first_name', 'middle_name', 'last_name', 'role',
        #                                  'is_active', 'created_date')

        possible_actions = {'i': 'In', 'o': 'Out', 'b': 'On Break', 'e': 'Ended Break'}

        """Getting the timezone to use"""
        timezone = None
        company_timezone = request.user.company.timezone
        dis_emp_time_in_their_timezone = request.user.company.display_employee_times_with_timezone
        if request.user.company.use_company_timezone:
            timezone = company_timezone
        else:
            timezone = request.user.timezone

        if not dis_emp_time_in_their_timezone:
            page_arguments['correct_timezone'] = timezone

        """Splitting the datetime object"""
        for employee in employee_list:
            if dis_emp_time_in_their_timezone:
                timezone = employee['timezone']
            if employee['time_action__action_datetime']:
                if not timezone:
                    timezone = company_timezone
                if timezone:
                    employee['time_action__action_datetime'] = employee['time_action__action_datetime'].astimezone(
                        timezone)

                employee['date'] = employee['time_action__action_datetime'].strftime("%b %d")
                employee['time'] = employee['time_action__action_datetime'].strftime("%I:%M %p")
                employee['status'] = possible_actions[employee['time_action__type']]

        """This creates a paginator that has a max of 25 employees per page."""
        paginator = Paginator(employee_list, 25)
        try:
            page_arguments['paginator_view'] = paginator.page(cur_page)
            page_arguments['paginator_cur_page'] = int(cur_page)
        except PageNotAnInteger:
            page_arguments['paginator_view'] = paginator.page(1)
            page_arguments['paginator_cur_page'] = 1
        except EmptyPage:
            page_arguments['paginator_view'] = paginator.page(paginator.num_pages)
            page_arguments['paginator_cur_page'] = int(paginator.num_pages)
        # See why just the number wouldn't have worked here: https://code.djangoproject.com/ticket/5172
        page_arguments['paginator_range_num_pages'] = range(1,
                                                            paginator.num_pages + 1)  # The paginator is 1-indexed

        # TODO Create and connect admin home screen
        pass
    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')
    # check for a post call, and if so update information accordingly. Used for clock actions and others
    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def company_settings(request):
    page = 'admin/company_settings.html'
    page_arguments = {}
    role = request.user.role

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == "c" or role == "r":
        form = None

        # If information is being submitted or saved this will execute.
        if request.method == 'POST':
            form = CompanyForm(request.POST, instance=request.user.company)
            if form.is_valid():
                form.save()
                messages.success(request, 'Company settings saved successfully')
            else:
                messages.warning(request, 'Please correct the error below')

        # TODO figure out about showing details in regards to subscription
        page_arguments['company'] = request.user.company

        # If someone already submitted a form the get the form object from before.
        page_arguments['form'] = CompanyForm(instance=request.user.company)

    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')
    # check for a post call, and if so update information accordingly. Used for clock actions and others
    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def create_employee(request):
    page = 'admin/create_or_edit_employee.html'
    page_arguments = {}
    role = request.user.role

    form = None

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == "c" or role == "r":
        page_arguments['title_type'] = 'Add'

        # If information is being submitted or saved this will execute.
        if request.method == 'POST':
            form = EmployeeForm(request.POST)
            if form.is_valid():
                employee = form.save(commit=False)
                employee.company = request.user.company
                employee.is_active = False
                employee.save()

                current_site = get_current_site(request)
                mail_subject = 'Activate Online TimeClick Account.'
                message = render_to_string('acc_active_email.html', {
                    'user': employee,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(employee.pk)),
                    'token': account_activation_token.make_token(employee),
                })
                to_email = form.cleaned_data.get('email')
                send_mail(
                    mail_subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [to_email],
                    fail_silently=False,
                )

                messages.success(request, 'Employee created, and validation email sent to their email')
                if request.POST.get('_addanother'):
                    return redirect('create_employee')
                else:
                    return redirect('admin_dashboard')
            else:
                messages.warning(request, 'Please correct the error below')
                page_arguments['form'] = form

        if not form:
            page_arguments['form'] = EmployeeForm()

    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')
    # check for a post call, and if so update information accordingly. Used for clock actions and others
    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def edit_employee(request, employee_id):
    page = 'admin/create_or_edit_employee.html'
    page_arguments = {}
    role = request.user.role

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == "c" or role == "r":
        page_arguments['title_type'] = 'Edit'
        page_arguments['employee_id'] = employee_id
        employee = CustomUser.objects.get(id=employee_id)
        if employee.company == request.user.company:
            page_arguments['can_delete'] = True
            if employee.is_active:
                page_arguments['status'] = 'Active'
            else:
                page_arguments['status'] = 'Confirmation Email Sent'
            form = None

            # If information is being submitted or saved this will execute.
            if request.method == 'POST':
                initial_email = employee.email
                form = EmployeeForm(request.POST, instance=employee)
                response = check_employee_form(get_current_site(request), form, initial_email)
                if response['success']:
                    if response['change_email']:
                        messages.success(request, "Validation email sent to employee's email")
                        pass
                    messages.success(request, "Employee settings saved successfully")
                    redirect('admin_dashboard')
                else:
                    messages.warning(request, "Please fix the error below")
                    form = response['form']

            # If someone already submitted a form the get the form object from before.
            if form:
                page_arguments['form'] = form
            else:
                page_arguments['form'] = EmployeeForm(instance=employee)

    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')
    # check for a post call, and if so update information accordingly. Used for clock actions and others
    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def delete_employee(request, employee_id):
    role = request.user.role

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == "c" or role == "r":
        employee = CustomUser.objects.get(id=employee_id)
        if not employee == request.user:
            if not employee.role == "c":
                if employee.company == request.user.company:
                    employee.delete()
                    messages.success(request, 'Employee deleted successfully')
                    return redirect('admin_dashboard')
                else:
                    messages.warning(request, 'You cannot delete an employee that does not belong to your company')
                    logger.error(
                        'No user with that id exists in your company \n \n User Info:' + str(
                            request.user))
            else:
                messages.warning(request, 'You cannot delete the company administrator')
                logger.error(
                    'You cannot delete the company administrator \n \n User Info:' + str(
                        request.user))
        else:
            messages.warning(request, 'You cannot delete yourself')
            logger.error(
                'You cannot delete yourself \n \n User Info:' + str(
                    request.user))
    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')
    # check for a post call, and if so update information accordingly. Used for clock actions and others
    return redirect('admin_dashboard')


@login_required
def send_confirmation_email(request, employee_id):
    role = request.user.role

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == "c" or role == "r":
        employee = CustomUser.objects.get(id=employee_id)
        if request.user.company == employee.company:
            if employee.is_active:
                logger.error(
                    'Employee is already marked as active \n \n User Info:' + str(
                        request.user))
                messages.warning(request, 'Employee has already validated their email address')
                return redirect('home')
            else:
                current_site = get_current_site(request)
                mail_subject = 'Activate Online TimeClick Account.'
                message = render_to_string('acc_active_email.html', {
                    'user': employee,
                    'domain': current_site.domain,
                    'uid': urlsafe_base64_encode(force_bytes(employee.pk)),
                    'token': account_activation_token.make_token(employee),
                })
                to_email = employee.email
                send_mail(
                    mail_subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [to_email],
                    fail_silently=False,
                )
                messages.success(request, 'Validation email resent')
                return redirect('edit_employee', employee_id=employee_id)
        else:
            logger.error(
                'User does not belong to the company of the logged in admin \n \n User Info:' + str(
                    request.user))
            messages.warning(request, 'You do not have access to employees outside of your company')
            return redirect('home')
    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')


@login_required
def edit_account_settings(request):
    page = 'edit_account_settings.html'
    page_arguments = {}
    role = request.user.role
    initial_email = request.user.email

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == "c" or role == "r":

        page = 'admin/edit_account_settings.html'
        # If information is being submitted or saved this will execute.
        if request.method == 'POST':
            form = AdminAccountForm(request.POST, instance=request.user, company=request.user.company)
            response = check_employee_form(get_current_site(request), form, initial_email)
            if response['success']:
                if response['change_email']:
                    messages.success(request, 'Sent email to new email address for validation')
                messages.success(request, 'Saved your account settings')
                redirect('home')
            else:
                messages.warning(request, 'Please fix the error below')
                form = response['form']
        else:
            form = AdminAccountForm(instance=request.user, company=request.user.company)

        page_arguments['form'] = form

    elif role == "e" or role == "r":
        # If information is being submitted or saved this will execute.
        if request.method == 'POST':
            form = EmployeeAccountForm(request.POST, instance=request.user, company=request.user.company)
            response = check_employee_form(get_current_site(request), form, initial_email)
            if response['success']:
                if response['change_email']:
                    messages.success(request, 'Sent email to new email address for validation')
                messages.success(request, 'Saved your account settings')
                return redirect('home')
            else:
                messages.warning(request, 'Please fix the error below')
                form = response['form']
        else:
            form = EmployeeAccountForm(instance=request.user, company=request.user.company)

        page_arguments['form'] = form
    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')
    # check for a post call, and if so update information accordingly. Used for clock actions and others
    page_arguments['company'] = request.user.company
    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def change_password(request):
    page = 'change_password.html'
    page_arguments = {}
    role = request.user.role

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role:
        if role == 'c' or role == 'r':
            page_arguments['template'] = 'admin.html'
        else:
            page_arguments['template'] = 'employee.html'

        # If information is being submitted or saved this will execute.
        if request.method == 'POST':
            form = OverriddenPasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)
                messages.success(request, 'Updated password successfully')
                return redirect('account_settings')
            else:
                messages.warning(request, 'Please fix the error below')
        else:
            form = OverriddenPasswordChangeForm(request.user)

        page_arguments['form'] = form
    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')
    # check for a post call, and if so update information accordingly. Used for clock actions and others
    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def admin_change_password(request, employee_id):
    page = 'change_password.html'
    page_arguments = {'template': "admin.html"}
    role = request.user.role

    """Checks whether the user is a timeclick employee, an employee, or an admin"""
    if request.user.is_staff:
        return redirect('/io_admin')
    elif role == "c" or role == "r":
        form = None
        employee = CustomUser.objects.get(id=employee_id)

        if employee.company == request.user.company:
            page_arguments['name'] = employee.last_name + ', ' + employee.first_name

            # If information is being submitted or saved this will execute.
            if request.method == 'POST':
                form = OverriddenAdminPasswordChangeForm(employee, request.POST)
                if form.is_valid():
                    form.save()
                    messages.success(request, 'Updated employee password successfully')
                    return redirect('edit_employee', employee_id=employee_id)
                else:
                    messages.warning(request, 'Please fix the error below')
            else:
                form = OverriddenAdminPasswordChangeForm(employee)

            page_arguments['form'] = form
        else:
            logger.error(
                'Someone that is an admin but not part of the same company is trying to change another users password \n \n User Info:' + str(
                    request.user))
            return redirect('home')

    else:
        logger.error(
            'Someone without a role or is an employee that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')
    # check for a post call, and if so update information accordingly. Used for clock actions and others
    return render(request, page, page_arguments)  # fill the {} with arguments


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        if user.change_email:
            user.email = user.change_email
            user.change_email = None
        user.save()
        login(request, user)
        return redirect('home')
    else:
        return render(request, 'activation_link.html')
