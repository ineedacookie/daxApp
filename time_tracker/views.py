import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from .models import InOutAction, TTUserInfo
from .utils import combine_comments, get_events_by_range, add_edit_time, delete_event
from users.models import CustomUser
from daxApp.encryption import decrypt_id
from daxApp.central_data import get_main_page_data
from users.utils import get_selectable_employees
from .forms import ReportsForm
from .report import generate_report

logger = logging.getLogger("django.request")


@login_required
def simple_clock(request):
    if request.method == 'POST':
        action = request.POST.get('action', None)
        comment = request.POST.get('comment', '')
        if action:
            user_info = TTUserInfo.objects.filter(user=request.user)[0]
            if action == 'in':
                # add a clock action
                InOutAction.objects.create(user=request.user, type='t', comment=comment)
            elif action == 'out':
                # update the existing user clock action
                time_action = user_info.time_action
                if not time_action.end:
                    time_action.comment = combine_comments(time_action.comment, comment)
                    time_action.end = timezone.now()
                    time_action.save()
                else:
                    logger.error('Tried to set clock out but time action already has an end date. TimeAction:' + str(
                                    time_action.id))
            elif action == 'b_in':
                # create a break action
                InOutAction.objects.create(user=request.user, type='b', comment=comment)
            elif action == 'b_out':
                # Update the existing user break action
                break_action = user_info.break_action
                if not break_action.end:
                    break_action.comment = combine_comments(break_action.comment, comment)
                    break_action.end = timezone.now()
                    break_action.save()
                else:
                    logger.error('Tried to set break out but break action already has an end date. BreakAction:' + str(
                                    break_action.id))
    user_info = TTUserInfo.objects.filter(user=request.user)[0]
    page = 'time_tracker/widgets/simple_clock_in.html'
    page_arguments = {
        'tt_user_info': user_info
    }

    return render(request, page, page_arguments)


@login_required
def manage_times(request):
    page = 'time_tracker/manage_times.html'
    page_arguments = get_main_page_data(request.user)
    return_list, _ = get_selectable_employees(request.user)
    page_arguments['show_select_employee'] = len(return_list) > 1

    return render(request, page, page_arguments)


@login_required
def event_handler(request):
    if request.POST:
        event = request.POST.get('event', '')
        if event:
            if event == 'add_edit_time':
                # TODO possibly include some sort of check to make sure the user can access the other users information
                if request.POST.get('employee_id', ''):
                    user = CustomUser.objects.get(id=decrypt_id(request.POST['employee_id']))
                else:
                    user = request.user
                errors, action_id = add_edit_time(user, request.POST)
                return JsonResponse(data={'errors': errors, 'action_id': action_id}, status=201, safe=False)


@login_required
def fetch_actions(request):
    if request.POST:
        # TODO possibly include some sort of check to make sure the user can access the other users information
        if request.POST.get('employee_id', ''):
            user = CustomUser.objects.get(id=decrypt_id(request.POST['employee_id']))
        else:
            user = request.user
        return JsonResponse(data=get_events_by_range(user, in_start=request.POST.get('start'), in_end=request.POST.get('end')), status=201, safe=False)


@login_required
def delete_action(request):
    if request.POST:
        return JsonResponse(data=delete_event(request.user, request.POST.get('action_id', '')), status=201, safe=False)


@login_required
def report_center(request):
    """Manages the report center for time tracking"""
    page = 'time_tracker/report_center.html'
    page_arguments = get_main_page_data(request.user)

    if request.POST:
        return generate_report(request, page, page_arguments)
    else:
        form = ReportsForm(company=request.user.company)
        page_arguments['form'] = form
    return render(request, page, page_arguments)