import zoneinfo

from django.utils import timezone


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            used_timezone = get_timezone(request.user)
            if used_timezone:
                timezone.activate(used_timezone)
            else:
                timezone.deactivate()
        else:
            timezone.deactivate()
        return self.get_response(request)


def get_timezone(user):
    used_timezone = user.timezone
    company = user.company
    if company:
        if company.timezone and company.use_company_timezone:
            used_timezone = company.timezone
        elif not used_timezone:
            used_timezone = company.timezone
    if not used_timezone:
        used_timezone = timezone.timezone.utc
    return used_timezone