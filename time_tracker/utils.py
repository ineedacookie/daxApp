import logging
from datetime import date, datetime, timezone, timedelta
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
            action_dict['start'] = start.astimezone(user_timezone).strftime("%Y-%m-%d %H:%M:%S")
        end = action.end
        if end:
            action_dict['end'] = end.astimezone(user_timezone).strftime("%Y-%m-%d %H:%M:%S")
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


def get_events_by_range(user, in_start, in_end):
    in_start = datetime.fromisoformat(in_start)
    in_end = datetime.fromisoformat(in_end)
    actions = InOutAction.objects.filter(user=user, action_lookup_datetime__gte=in_start, action_lookup_datetime__lte=in_end)
    user_timezone = get_timezone(user)
    action_list = []
    for action in actions:
        action_dict = {'id': encrypt_id(action.id)}
        start = action.start
        if start:
            action_dict['start'] = start.astimezone(user_timezone).strftime("%Y-%m-%d %H:%M:%S")
        end = action.end
        if end:
            action_dict['end'] = end.astimezone(user_timezone).strftime("%Y-%m-%d %H:%M:%S")
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
    return action_list


def add_edit_time(user, post):
    action_id = post.get('action_id', '')
    if action_id:
        action_id = decrypt_id(action_id)
    title = post.get('title', '')
    start = post.get('start', '')
    end = post.get('end', '')
    comment = post.get('description', '')
    user_timezone = get_timezone(user)
    type = None
    use_form = False

    errors = []

    if title == 'Clocked In':
        type = 't'
    elif title == 'Break':
        type = 'b'

    data = {'user': user}
    if type:
        data['type'] = type
        use_form = True
    if comment:
        data['comment'] = comment
    if start:
        try:
            start = datetime.fromisoformat(start)
        except:
            start = datetime.strptime(start, '%I:%M%p %b %d, %Y')
        start = start.replace(tzinfo=user_timezone)
        start = start.astimezone(timezone.utc)
        data['start'] = start
    if end:
        try:
            end = datetime.fromisoformat(end)
        except:
            end = datetime.strptime(end, '%I:%M%p %b %d, %Y')
        end = end.replace(tzinfo=user_timezone)
        end = end.astimezone(timezone.utc)
        data['end'] = end
        if end < start:
            return ['End date was before start date']
    else:
        end = None
    if use_form:
        if action_id:
            form = SimpleClockForm(data, instance=InOutAction.objects.get(id=action_id))
        else:
            form = SimpleClockForm(data)

        if form.is_valid():
            action = form.save()
            action_id = encrypt_id(action.id)
        else:
            errors = form.errors
    elif action_id:
        # this will be used in the event that actions are resized or moved and no other information is updated
        action = InOutAction.objects.get(id=action_id)
        action.start = start
        action.end = end
        action.save()
        action_id = encrypt_id(action_id)
    else:
        errors = ['Missing important information necessary to add or update an action.']

    return errors, action_id


def delete_event(user, action_id):
    """
    Handles deleting an existing action.
    """
    # TODO this should be updated to double check that the user has permissions to delete the other users action id. For now I will just assert that the users belong to the same company.
    try:
        event = InOutAction.objects.get(id=decrypt_id(action_id))
    except InOutAction.DoesNotExist:
        return {'errors': ['The action submitted does not exist'], 'Success': False}
    if event.user.company == user.company:
        event.delete()
    return {'errors': [], 'Success': True}


