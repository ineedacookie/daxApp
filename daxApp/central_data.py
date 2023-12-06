from users.models import CompanyConnection, CustomUser
from time_tracker.models import TTUserInfo, TTCompanyInfo
from daxApp.encryption import encrypt_id


def get_main_page_data(user, get_tt_employees=False, get_employee_list=False):
    arguments = dict()
    arguments['company_connection'] = CompanyConnection.objects.filter(user=user)[0]
    arguments['tt_company_info'] = TTCompanyInfo.objects.filter(company=user.company)[0]
    arguments['tt_user_info'] = TTUserInfo.objects.filter(user=user)[0]
    arguments['user'] = user
    arguments['company'] = user.company
    arguments['tt_employees'] = []
    arguments['employees'] = []

    # if the user is the company owner and there are other employees then we should show the employees list
    if arguments['company_connection'].role == 'c':
        if get_tt_employees:
            tt_employees = TTUserInfo.objects.filter(user__company=user.company).exclude(user=user).order_by('user__full_name')
            for i in tt_employees:
                arguments['tt_employees'].append({'name': i.user.full_name, 'status': i.get_status_text_display(), 'time': i.status_time})

        if get_employee_list:
            employees = CustomUser.objects.filter(company=user.company).exclude(pk=user.pk).order_by('first_name')
            for i in employees:
                arguments['employees'].append({'pk': encrypt_id(i.pk), 'name': i.user.full_name, 'email': i.email, 'active': i.active})

    return arguments