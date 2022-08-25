import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .forms import FeedbackForm

from users.utils import urlsafe_base64_encode


@login_required
def add_feedback(request):
    page = 'feedback.html'
    page_arguments = {}
    role = request.user.role

    """Make sure that this is a valid user, and can be used later to style pages differently. by user role"""
    if request.user.is_staff:
        return redirect('/tc_admin')
    elif role == "c" or role == "r":
        pass
    elif role == "e":
        pass
    else:
        logging.error(
            'Someone without a role that is not an admin was trying to access the site \n \n User Info:' + str(
                request.user))
        return redirect('home')

    if request.POST:
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feed = form.save(commit=False)
            feed.user = request.user
            feed.save()

            current_site = get_current_site(request)
            mail_subject = 'Feedback: ' + feed.subject
            message = render_to_string('email/feedback_submitted.html', {
                'user': request.user.first_name,
                'domain': current_site.domain,
                'subject': feed.subject,
                'content': feed.content,
            })
            send_mail(
                mail_subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                ['feedback@timeclick.com'],
                fail_silently=False,
            )
            messages.success(request, "Feedback submitted successfully")
            return redirect('home')
        else:
            messages.warning(request, "Please correct the error below")
            page_arguments['form'] = form
    else:
        form = FeedbackForm()
        page_arguments['form'] = form

    return render(request, page, page_arguments)
