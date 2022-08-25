from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from .tokens import account_activation_token


def check_employee_form(current_site, form, initial_email, send=True):
    return_dict = {'change_email': False, 'success': True, 'form': form}
    if form.is_valid():
        if 'email' in form.changed_data and not form.cleaned_data['email'] == initial_email:
            employee = form.save(commit=False)
            changed_email = employee.email
            employee.change_email = changed_email
            employee.email = initial_email
            employee.save()
            uid = urlsafe_base64_encode(force_bytes(employee.pk))
            token = account_activation_token.make_token(employee)

            mail_subject = 'Validate email change'
            message = render_to_string('email/change_validation.html', {
                'user': employee.first_name,
                'domain': current_site.domain,
                'uid': uid,
                'token': token,
            })
            to_email = employee.change_email
            if not send:
                return {'change_email': True, 'success': True, 'user': employee.first_name, 'domain': current_site.domain, 'uid': uid, 'token': token}
            send_mail(
                mail_subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                fail_silently=False,
            )
            return_dict = {'change_email': True, 'success': True, 'form': form}
        else:
            form.save()
    else:
        return_dict = {'change_email': False, 'success': False, 'form': form}
    return return_dict