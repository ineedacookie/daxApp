from django import forms
from django.forms import HiddenInput, ModelForm, CharField, Form, DateInput
from users.models import CustomUser  # this is correct syntax
from daxApp.encryption import encrypt_id
from string import capwords


from .models import InOutAction


class SimpleClockForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(ModelForm, self).__init__(*args, **kwargs)

    class Meta:
        model = InOutAction
        fields = ('user', 'type', 'start', 'end', 'comment')


class NewDateInput(DateInput):
    input_type = 'date'


class ReportsForm(Form):
    begin_date = forms.DateField(widget=NewDateInput())
    end_date = forms.DateField(widget=NewDateInput())
    report_type = forms.ChoiceField(choices=(
        ('time_tracker/reports/detailed_hours.html', 'Detailed Hours Report'),
        ('reports/summary.html', 'Summary Report')), initial='reports/detailed_hours.html')
    selected_employees_list = forms.MultipleChoiceField(choices=((-1, 'All Employees'),),
                                                        required=False, widget=forms.CheckboxSelectMultiple(),
                                                        initial=[-1])
    display_clock_actions = forms.BooleanField(required=False, initial=True)
    display_day_totals = forms.BooleanField(required=False, initial=True)
    display_week_totals = forms.BooleanField(required=False, initial=True)
    display_employee_totals = forms.BooleanField(required=False, initial=True)
    display_grand_totals = forms.BooleanField(required=False, initial=True)
    display_employee_comments = forms.BooleanField(required=False, initial=False)
    add_employee_signature_line = forms.BooleanField(required=False, initial=False)
    add_supervisor_signature_line = forms.BooleanField(required=False, initial=False)
    add_other_signature_line = forms.BooleanField(required=False, initial=False)
    other_new_page_for_each_employee = forms.BooleanField(required=False, initial=False)
    other_rounding = forms.ChoiceField(
        choices=((1, '1 Minute'), (5, '5 Minutes'), (10, '10 Minutes'), (15, '15 Minutes')), initial=1)
    other_hours_format = forms.ChoiceField(
        choices=(('decimal', 'Decimal (e.g. 8.25)'), ('hours_and_minutes', 'Hours and Minutes (e.g. 8:15)')),
        initial='decimal')
    other_font_size = forms.ChoiceField(choices=(('medium', "Medium"), ('large', "Large"), ('small', "Small")),
                                        initial='medium')
    other_memo = forms.BooleanField(required=False, initial=False)
    other_space_on_right = forms.BooleanField(required=False, initial=False)

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company")
        """Only pass user if the report is supposed to be restricted to an employee"""
        self.user = kwargs.pop('user', None)
        super(ReportsForm, self).__init__(*args, **kwargs)

        if not self.user:
            employee_list = CustomUser.objects.filter(company=self.company).order_by('last_name', 'first_name').values('id', 'full_name')
            choice_list = [(-1, 'All Employees')]
            # print(self.fields['selected_employees_list'].widget.subwidgets())
            for employee in employee_list:
                choice_list.append((employee['id'], capwords(employee['full_name'])))
            choice_list = tuple(choice_list)
        else:
            choice_list = ((self.user.id, capwords(self.user.full_name)),)
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
                     "display_grand_totals", "display_employee_comments", "add_employee_signature_line",
                     "add_supervisor_signature_line", "add_other_signature_line", "other_new_page_for_each_employee",
                     "other_memo", "other_space_on_right"]:
            self.fields[name].widget.attrs["class"] = "custom-control-input"