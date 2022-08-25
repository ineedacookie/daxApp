import json
import logging
from datetime import datetime

import pytz
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from users.models import CustomUser  # this is correct syntax

from .forms import TimeActionForm, ReportsForm, BaseTimeActionFormSet
from .models import TimeActions
from .utils import generate_report, get_timezone, get_month_range_in_timezone, get_day_range_in_timezone, \
    convert_front_end_date_to_utc


@login_required
def reports(request):
    page = 'admin/reports.html'
    page_arguments = {'extended_file': 'admin.html', 'user_employee': False}
    role = request.user.role

    if request.user.is_staff:
        return redirect('/tc_admin')
    elif role == "c" or role == "r":
        correct_timezone = get_timezone(request.user)
        page_arguments['correct_timezone'] = correct_timezone
        if request.POST:
            return generate_report(request, page, page_arguments, correct_timezone)
        else:
            form = ReportsForm(company=request.user.company)
            page_arguments['form'] = form
            page_arguments['company'] = request.user.company
    else:
        logging.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')

    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def employee_reports(request):
    page = 'admin/reports.html'
    page_arguments = {'extended_file': 'employee.html', 'user_employee': True}
    role = request.user.role

    if request.user.is_staff:
        return redirect('/tc_admin')
    elif role == "c" or role == "r":
        redirect('home')
    elif role == "e":
        correct_timezone = get_timezone(request.user)
        page_arguments['correct_timezone'] = correct_timezone
        if request.POST:
            return generate_report(request, page, page_arguments, correct_timezone)
        else:
            form = ReportsForm(company=request.user.company, user=request.user)
            page_arguments['form'] = form
            page_arguments['company'] = request.user.company
    else:
        logging.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')

    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def modify_times_emp_list(request):
    page = 'admin/employee_list.html'
    page_arguments = {}
    role = request.user.role

    if request.user.is_staff:
        return redirect('/tc_admin')
    elif role == "c" or role == "r":
        page_arguments['employee_list'] = CustomUser.objects.filter(company=request.user.company).exclude(
            role="c").values('id', 'first_name', 'middle_name', 'last_name').order_by('last_name', 'first_name')
    else:
        logging.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')

    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def modify_times_table(request, employee_id, selected_date=timezone.now()):
    page = 'admin/modify_times_table.html'
    page_arguments = {'use_built_in_date': True}
    role = request.user.role

    if request.user.is_staff:
        return redirect('/tc_admin')
    elif role == "c" or role == "r":
        employee = CustomUser.objects.get(id=employee_id)
        correct_timezone = get_timezone(request.user, employee)
        if isinstance(selected_date, str):
            """Expecting a string of in the following format  YYYYmmdd"""
            selected_date = datetime.strptime(selected_date, '%Y%m%d')
            selected_date = selected_date.replace(tzinfo=correct_timezone)
        else:
            selected_date = correct_timezone.localize(selected_date.replace(tzinfo=None)).replace(hour=0, minute=0, second=0, microsecond=0)

        if employee.company == request.user.company:
            page_arguments['correct_timezone'] = correct_timezone.zone
            page_arguments['employee_id'] = employee_id
            page_arguments['name'] = employee.last_name + ', ' + employee.first_name
            page_arguments['selected_date'] = selected_date.date()

            month_range = get_month_range_in_timezone(selected_date, correct_timezone)
            day_range = get_day_range_in_timezone(selected_date, correct_timezone)
            time_actions = TimeActions.objects.filter(user=employee).filter(
                action_datetime__range=month_range).order_by(
                'action_datetime').values('action_datetime')
            dates_with_times = []
            # TODO check if this is broken
            for action in time_actions:
                action['action_datetime'].astimezone(correct_timezone)
                dates_with_times.append(action['action_datetime'].strftime("%d"))
            dates_with_times = list(dict.fromkeys(dates_with_times))
            page_arguments['dates_with_times'] = json.dumps(dates_with_times)

            if request.method == 'POST':
                queryset = TimeActions.objects.filter(user=employee).filter(
                    action_datetime__range=day_range).order_by(
                    'action_datetime')
                formset = BaseTimeActionFormSet(request.POST, queryset=queryset)
                if formset.is_valid():
                    for form in formset.forms:
                        mod_action = form.save(commit=False)
                        mod_action.action_datetime = convert_front_end_date_to_utc(mod_action.action_datetime,
                                                                                   correct_timezone)
                        mod_action.save()
                        if form in formset.deleted_forms:
                            mod_action.delete()
                    messages.success(request, 'Successfully updated time actions')
                else:
                    messages.warning(request, 'Please fix the error below')
            queryset = TimeActions.objects.filter(user=employee).filter(
                action_datetime__range=day_range).order_by(
                'action_datetime')
            formset = BaseTimeActionFormSet(queryset=queryset)
            page_arguments['formset'] = formset
        else:
            messages.warning(request, 'You cannot edit times for an employee that does not belong to your company')
            return redirect('home')
    else:
        logging.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')

    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def create_time_action(request, employee_id, selected_date=timezone.now().strftime("%Y%m%d")):
    page = 'admin/create_or_edit_time_action.html'
    page_arguments = {'use_built_in_date': True, 'entry_type': 'Add'}
    role = request.user.role

    if request.user.is_staff:
        return redirect('/tc_admin')
    elif role == "c" or role == "r":
        employee = CustomUser.objects.get(id=employee_id)
        if employee.company == request.user.company:
            correct_timezone = get_timezone(request.user, employee)
            page_arguments['correct_timezone'] = correct_timezone
            if isinstance(selected_date, str):
                """Expecting a string of in the following format  YYYYmmdd"""
                selected_date = datetime.strptime(selected_date, '%Y%m%d')
                selected_date.replace(hour=8)
            else:
                logging.error(
                    'Incorrect format used for submitting selected date' + str(
                        request))
                return redirect('home')
            if request.POST:
                form = TimeActionForm(request.POST)
                if form.is_valid():
                    time_action = form.save(commit=False)
                    time_action.user = employee
                    time_action.action_datetime = convert_front_end_date_to_utc(time_action.action_datetime,
                                                                                correct_timezone)
                    time_action.save()
                    messages.success(request, 'Successfully added time action')
                    if request.POST.get('_addanother'):
                        return redirect('admin_create_time_action', employee.id, selected_date.strftime('%Y%m%d'))
                    else:
                        return redirect(request.path.replace('time_action_create', 'modify_times'))
                else:
                    messages.warning(request, 'Please fix the error below')
            page_arguments['form'] = TimeActionForm(initial={'action_datetime': selected_date})
        else:
            messages.warning(request, 'You cannot add times for an employee that does not belong to your company')
            return redirect('home')
    else:
        logging.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')

    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def edit_time_action(request, time_action_id):
    page = 'admin/create_or_edit_time_action.html'
    page_arguments = {'use_built_in_date': True, 'entry_type': 'Edit'}
    role = request.user.role

    if request.user.is_staff:
        return redirect('/tc_admin')
    elif role == "c" or role == "r":
        time_action = TimeActions(id=time_action_id)
        if time_action.user.company == request.user.company:
            correct_timezone = get_timezone(request.user, time_action.user)
            page_arguments['correct_timezone'] = correct_timezone.zone
            if request.POST:
                form = TimeActionForm(request.POST, initial=time_action)
                if form.is_valid():
                    edited_action = form.save(commit=False)
                    edited_action.action_datetime = convert_front_end_date_to_utc(edited_action.action_datetime,
                                                                                  correct_timezone)
                    edited_action.save()
                    messages.success(request, 'Successfully adjusted this time action')
                    redirect('modify_times_table')
                else:
                    messages.warning(request, 'Please fix the error below')

            page_arguments['form'] = TimeActionForm(initial=time_action)
        else:
            messages.warning(request, 'You cannot edit times for an employee that does not belong to your company')
            return redirect('home')
    else:
        logging.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')

    return render(request, page, page_arguments)  # fill the {} with arguments


@login_required
def delete_time_action(request, time_action_id):
    page = 'admin/modify_times_table.html'
    page_arguments = {'use_built_in_date': True}
    role = request.user.role

    if request.user.is_staff:
        return redirect('/tc_admin')
    elif role == "c" or role == "r":
        time_action = TimeActions(id=time_action_id)
        if time_action.user.company == request.user.company:
            time_action.delete()
            messages.success(request, 'Deleted the time action successfully')
            redirect('modify_times_table')
        else:
            messages.warning(request, 'You cannot edit times for an employee that does not belong to your company')
            return redirect('home')
    else:
        logging.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')

    return render(request, page, page_arguments)  # fill the {} with arguments
