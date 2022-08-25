from django.forms import ModelForm

from .models import Feedback


class FeedbackForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)
        """This is the place to add styles or classes"""

    class Meta:
        model = Feedback
        fields = ('type', 'subject', 'content')
