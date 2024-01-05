from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from .tokens import account_activation_token
from daxApp.encryption import encrypt_id, decrypt_id
from django.core.paginator import Paginator
from .models import CustomUser
from django.contrib.sites.shortcuts import get_current_site
from daxApp.settings import DOMAIN
import logging


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


def get_selectable_employees(user, page=1, query=''):
    return_list = []
    employees = CustomUser.objects.filter(company=user.company, full_name__contains=query).order_by('last_name',
                                                                                                    'first_name')
    p = Paginator(employees, 30)
    for employee in p.page(page).object_list:
        text = employee.last_name + ', ' + employee.first_name
        if employee.middle_name:
            text += ' ' + employee.middle_name
        return_list.append({
            'id': encrypt_id(employee.id),
            'text': text
        })
    more = page * 30 < p.count

    return return_list, more


def send_email_with_link(user, request=None, type='activation'):
    if request is None:
        current_site = DOMAIN
    else:
        current_site = get_current_site(request).domain

    if type == 'activation':
        mail_subject = 'Activate Account.'
        html_file = 'email/acc_active_email.html'
        url = f'http://{current_site}/activate/'
    elif type == 'invitation':
        mail_subject = 'Activate Account.'
        html_file = 'email/acc_invite_email.html'
        url = f'http://{current_site}/invited/'
    else:
        logging.error("send_email_with_link was passed a type it wasn't expecting. Type:" + str(type))
        return

    message = render_to_string(html_file, {
        'user': user,
        'domain': current_site,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': account_activation_token.make_token(user),
    })
    to_email = user.email
    print(url + urlsafe_base64_encode(
        force_bytes(user.pk)) + '/' + account_activation_token.make_token(user))

    # send_mail(
    #     mail_subject,
    #     message,
    #     settings.DEFAULT_FROM_EMAIL,
    #     [to_email],
    #     fail_silently=False,
    # )