from django import forms
from django.forms import HiddenInput, ModelForm, CharField, Form, DateInput
from users.models import CustomUser  # this is correct syntax

from .models import TimeActions


class NewDateInput(DateInput):
    input_type = 'date'


class ReportsForm(Form):
    # TODO attach employee pay rate and total
    # TODO account for rounding when hours format is hours and minutes
    begin_date = forms.DateField(widget=NewDateInput())
    end_date = forms.DateField(widget=NewDateInput())
    report_type = forms.ChoiceField(choices=(
        ('reports/detailed_hours.html', 'Detailed Hours Report'),
        ('reports/summary.html', 'Summary Report')), initial='reports/detailed_hours.html')
    selected_employees_list = forms.MultipleChoiceField(choices=((-1, 'All Employees'),),
                                                        required=False, widget=forms.CheckboxSelectMultiple(),
                                                        initial=[-1])
    display_clock_actions = forms.BooleanField(required=False, initial=True)  # TODO: style
    display_day_totals = forms.BooleanField(required=False, initial=True)  # TODO: style
    display_week_totals = forms.BooleanField(required=False, initial=True)  # TODO: style
    display_employee_totals = forms.BooleanField(required=False, initial=True)  # TODO: style
    display_grand_totals = forms.BooleanField(required=False, initial=True)  # TODO: style
    display_employee_pay_total = forms.BooleanField(required=False, initial=True)  # TODO: style
    display_employee_pay_rate = forms.BooleanField(required=False,
                                                   initial=True)  # should not be active unless employee_pay_total is active  # TODO: style
    display_grand_pay_total = forms.BooleanField(required=False, initial=True)  # TODO: style
    display_employee_comments = forms.BooleanField(required=False, initial=False)  # TODO: style
    add_employee_signature_line = forms.BooleanField(required=False, initial=False)  # TODO: style
    add_supervisor_signature_line = forms.BooleanField(required=False, initial=False)  # TODO: style
    add_other_signature_line = forms.BooleanField(required=False, initial=False)  # TODO: style
    other_new_page_for_each_employee = forms.BooleanField(required=False, initial=False)  # TODO: style
    other_rounding = forms.ChoiceField(
        choices=((1, '1 Minute'), (5, '5 Minutes'), (10, '10 Minutes'), (15, '15 Minutes')), initial=1)  # TODO: style
    other_hours_format = forms.ChoiceField(
        choices=(('decimal', 'Decimal (e.g. 8.25)'), ('hours_and_minutes', 'Hours and Minutes (e.g. 8:15)')),
        initial='decimal')  # TODO: style
    other_font_size = forms.ChoiceField(choices=(('medium', "Medium"), ('large', "Large"), ('small', "Small")),
                                        initial='medium')  # TODO: style
    other_memo = forms.BooleanField(required=False, initial=False)  # TODO: style
    other_space_on_right = forms.BooleanField(required=False, initial=False)  # TODO: style

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company")
        """Only pass user if the report is supposed to be restricted to an employee"""
        self.user = kwargs.pop('user', None)
        super(ReportsForm, self).__init__(*args, **kwargs)

        if not self.user:
            employee_list = CustomUser.objects.filter(company=self.company).exclude(
                role="c").values('id', 'last_name', 'first_name', 'middle_name').order_by('last_name', 'first_name')
            choice_list = [(-1, 'All Employees')]
            # print(self.fields['selected_employees_list'].widget.subwidgets())
            for employee in employee_list:
                name = employee['last_name'] + ', ' + employee['first_name']
                if employee['middle_name']:
                    name += ' ' + employee['middle_name']
                choice_list.append((employee['id'], name))
            choice_list = tuple(choice_list)
        else:
            name = self.user.last_name + ', ' + self.user.first_name
            if self.user.middle_name:
                name += ' ' + self.user.middle_name
            choice_list = ((self.user.id, name),)
        self.fields['selected_employees_list'].widget.choices = choice_list
        self.fields['selected_employees_list'].choices = choice_list
        if self.user:
            self.fields['selected_employees_list'].initial = [choice_list[0][0]]

        # print(self.fields["selected_employees_list"].widget_attrs())

        self.label_suffix = ""
        for name in ["begin_date", "end_date", "report_type", "other_rounding", "other_hours_format",
                     "other_font_size"]:
            self.fields[name].widget.attrs["class"] = "form-control"

        # Go through the checkboxes and give them this class
        for name in ["display_clock_actions", "display_day_totals", "display_week_totals", "display_employee_totals",
                     "display_grand_totals", "display_employee_pay_total", "display_employee_pay_rate",
                     "display_grand_pay_total", "display_employee_comments", "add_employee_signature_line",
                     "add_supervisor_signature_line", "add_other_signature_line", "other_new_page_for_each_employee",
                     "other_memo", "other_space_on_right"]:
            self.fields[name].widget.attrs["class"] = "custom-control-input"


class TimeActionForm(ModelForm):
    # TODO possibly create a clean up function and possibly a validation function
    action_datetime = forms.SplitDateTimeField(widget=forms.SplitDateTimeWidget(
        date_attrs=({'type': 'date'}),
        time_attrs=({'type': 'time'})
    ))

    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)

        self.label_suffix = ""
        for name in ["type", "action_datetime", "comment"]:
            self.fields[name].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3

    class Meta:
        model = TimeActions
        fields = ('type', 'action_datetime', 'comment')


class EmployeeTimeActionForm(ModelForm):
    """For the employee clock screen, Ideally buttons will determine the type of action that is available for the employee
    and when one is clicked the type field will be filled.

    The only thing that should be displayed automatically is the comment field."""

    def __init__(self, *args, **kwargs):
        super(EmployeeTimeActionForm, self).__init__(*args, **kwargs)
        self.fields['type'] = CharField(max_length=1, widget=HiddenInput())  # hides this from the user
        self.fields["comment"].widget.attrs = {
            "class": "form-control",
            "rows": "3",
        }

    class Meta:
        model = TimeActions
        fields = ('type', 'comment')


BaseTimeActionFormSet = forms.modelformset_factory(TimeActions, form=TimeActionForm, extra=0, can_delete=True)
