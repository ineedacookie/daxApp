import logging
from datetime import date, datetime, timezone
from .models import InOutAction
from middleware.timezone import get_timezone
from json import dumps
from daxApp.encryption import encrypt_id, decrypt_id
from .forms import SimpleClockForm

logger = logging.getLogger("django.request")

def combine_comments(first, second):
    final_comment = first
    if second:
        if first:
            final_comment += '. ' + second
        else:
            final_comment = second
    return final_comment


def get_events_by_month(user, in_date=date.today()):
    actions = InOutAction.objects.filter(user=user, action_lookup_datetime__year=in_date.year, action_lookup_datetime__month=in_date.month)
    user_timezone = get_timezone(user)
    action_list = []
    for action in actions:
        action_dict = {'id': encrypt_id(action.id)}
        start = action.start
        if start:
            action_dict['start'] = start.replace(tzinfo=user_timezone).strftime("%Y-%m-%d %H:%M:%S")
        end = action.end
        if end:
            action_dict['end'] = end.replace(tzinfo=user_timezone).strftime("%Y-%m-%d %H:%M:%S")
        comment = action.comment
        if comment:
            action_dict['comment'] = comment
        type = action.type
        if type == 't':
            action_dict['title'] = 'Clocked In'
            action_dict['className'] = 'bg-soft-success'
        elif type == 'b':
            action_dict['title'] = 'Break'
            action_dict['className'] = 'bg-soft-primary'
        action_list.append(action_dict)
    return dumps(action_list)


def add_edit_time(user, post):
    id = post.get('id', '')
    title = post.get('title', '')
    start = post.get('start', '')
    end = post.get('end', '')
    comment = post.get('description', '')
    user_timezone = get_timezone(user)

    errors = []

    if title == 'Clocked In':
        type = 't'
    elif title == 'Break':
        type = 'b'
    else:
        logger.error(f"An unexpected type was used when adding action title is ({title})")
        return ['Unexpected action selected']

    data = {'user': user, 'type': type, 'comment': comment}
    if start:
        start = datetime.strptime(start, '%I:%M%p %b %d, %Y')
        if user_timezone:
            start = start.astimezone(user_timezone)
        data['start'] = start
    if end:
        end = datetime.strptime(end, '%I:%M%p %b %d, %Y')
        if user_timezone:
            end = end.astimezone(user_timezone)
        data['end'] = end
        if end < start:
            return ['End date was before start date']

    if id:
        id = decrypt_id(id)
        form = SimpleClockForm(data, instance=InOutAction.objects.get(id=id))
    else:
        form = SimpleClockForm(data)

    if form.is_valid():
        action = form.save()
        id = encrypt_id(action.id)
    else:
        errors = form.errors

    return errors, id