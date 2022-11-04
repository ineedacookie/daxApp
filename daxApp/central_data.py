from users.models import CompanyConnection
from time_tracker.models import TTUserInfo, TTCompanyInfo


def get_main_page_data(user):
    arguments = dict()
    arguments['company_connection'] = CompanyConnection.objects.filter(user=user)[0]
    arguments['tt_company_info'] = TTCompanyInfo.objects.filter(company=user.company)[0]
    arguments['tt_user_info'] = TTUserInfo.objects.filter(user=user)[0]
    arguments['user'] = user
    arguments['company'] = user.company

    return arguments