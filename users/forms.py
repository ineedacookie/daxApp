from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AdminPasswordChangeForm, PasswordChangeForm
from django.forms import EmailField, ModelForm, DateInput

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div, HTML, Field
# from .crispyOverrides import CheckboxPrepend

from .models import CustomUser, Company


class NewDateInput(DateInput):
    input_type = 'date'


class CustomUserCreationForm(UserCreationForm):
    """This form is used for creating a user in django admin mode"""
    email = EmailField(max_length=200, help_text='Required')

    class Meta(UserCreationForm):
        model = CustomUser
        fields = ('email', 'password1', 'password2')


class CustomUserChangeForm(UserChangeForm):
    """This form is used for recovering a lost password"""
    email = EmailField(max_length=200, help_text='Required')

    class Meta:
        model = CustomUser
        fields = ('email',)


class OverriddenAdminPasswordChangeForm(AdminPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(OverriddenAdminPasswordChangeForm, self).__init__(*args, **kwargs)

        for name in ["password1", "password2"]:
            self.fields[name].widget.attrs["class"] = "form-control"


class OverriddenPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(OverriddenPasswordChangeForm, self).__init__(*args, **kwargs)

        for name in ["old_password", "new_password1", "new_password2"]:
            self.fields[name].widget.attrs["class"] = "form-control"


class CompanyForm(ModelForm):
    # TODO: See todos in corresponding template...
    # TODO: Make an interactive date-range picker that works more like the one in the desktop app for the period range
        # - I could approach this by keeping the two inputs, but below them show
    def __init__(self, *args, **kwargs):
        super(CompanyForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()  # Note: if the default layout would be fine, just pass self into this
        self.helper.form_id = "content"
        self.helper.layout = Layout(
            'name',
            Row(
                Column('timezone'),
                Column('use_company_timezone', css_class='pt-md-3'),
                css_class='align-items-center'
            ),
            Row(
                Column('pay_period_type'),
                Column(
                    # Only one of these two will be visible at a time
                    'period_begin_date',
                    HTML("""
                        <div class="semi_monthly pt-md-4" style="display:none;" id="semi_monthly_div">
                            <p>Period 1: 1st - 15th<br/>
                                Period 2: 16th - end</p>
                        </div>
                    """),
                ),
            ),
            'week_start_day',
            # TODO: these need to be item groups with the checkbox in the prefix
            #  What's preventing this from happening is CheckboxPrepend is not getting the correct current value
            Row(
                Column('weekly_overtime'),
                Column('weekly_overtime_value'),
            ),
            Row(
                Column('daily_overtime'),
                Column('daily_overtime_value'),
            ),
            Row(
                Column('double_time'),
                Column('double_time_value'),
            ),
            #CheckboxPrepend(
            #    'weekly_overtime_value',
            #    checkbox='weekly_overtime',
            #    form=self
            #),
            #CheckboxPrepend(
            #    'daily_overtime_value',
            #    checkbox='daily_overtime',
            #    form=self
            #),
            #CheckboxPrepend(
            #    'double_time_value',
            #    checkbox='double_time',
            #    form=self
            #),
            Div(
                'enable_breaks',
                Div(
                    'breaks_are_paid',
                    'include_breaks_in_overtime_calculation',
                    css_class='form-group ml-4'
                ),
                css_class="form-group"
            ),
            'default_theme',
            Row(
                HTML('<button type="submit" class="btn btn-primary col-6 col-sm-4 col-lg-3" id="save-btn">' +
                     '<i aria-hidden="true" class="fas fa-check mr-1 mr-sm-2"></i>Save Changes</button>'),
                HTML('<button type="reset" class="btn btn-danger col-6 col-sm-4 col-lg-3" id="undo-btn">' +
                     '<i aria-hidden="true" class="fas fa-undo mr-sm-2"></i>Undo Changes</button>'),
                css_class="justify-content-between",
            ),
        )
        # Go through each of these fields and give them the form-control class
        #for name in ["name", "pay_period_type", "week_start_day", "weekly_overtime_value", "daily_overtime_value",
        #             "double_time_value", "period_begin_date"]:
        #    self.fields[name].widget.attrs["class"] = "form-control"
        # Go through each of these fields that are the "last" of an input group and round their right side
        # Normally, bootstrap handles for this, but the div.invalid-feeback elements cause a problem
        #for name in ["weekly_overtime_value", "daily_overtime_value", "double_time_value"]:
        #    self.fields[name].widget.attrs["class"] += " rounded-right"
        # Go through the checkboxes and give them this class
        #for name in ["use_company_timezone", "weekly_overtime",
        #             "daily_overtime", "double_time", "enable_breaks",
        #             "breaks_are_paid", "include_breaks_in_overtime_calculation"]:
        #    self.fields[name].widget.attrs["class"] = "custom-control-input"
        #self.label_suffix = ""

    class Meta:
        model = Company
        fields = ('name', 'timezone', 'use_company_timezone',
                  'pay_period_type', 'period_begin_date',
                  'default_theme',
                  'week_start_day',
                  'weekly_overtime', 'weekly_overtime_value',
                  'daily_overtime', 'daily_overtime_value',
                  'double_time', 'double_time_value',
                  'enable_breaks',
                  'breaks_are_paid',
                  'include_breaks_in_overtime_calculation'
                  )
        widgets = {
            'period_begin_date': NewDateInput(attrs={}),
        }


class EmployeeForm(ModelForm):
    # TODO possibly create a clean up function and possibly a validation function
    # TODO make sure that the role field only displays the employee option and the restricted admin option when added.
    # TODO add role when restricted admin is created set up.
    def __init__(self, *args, **kwargs):
        super(EmployeeForm, self).__init__(*args, **kwargs)
        self.label_suffix = ""
        # Go through each of these fields and give them the form-control class
        for name in ["first_name", "middle_name", "last_name", "email", "pay_rate"]:
            self.fields[name].widget.attrs["class"] = "form-control"
        # Go through each of these fields that are the "last" of an input group and round their right side
        # Normally, bootstrap handles for this, but the div.invalid-feedback elements cause a problem
        for name in ["pay_rate"]:
            self.fields[name].widget.attrs["class"] += " rounded-right"

    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'middle_name',
            'last_name',
            'email',
            'pay_rate'  # TODO: specify minimum to be 0 (allow for null, still?)
        )


class AdminAccountForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super(AdminAccountForm, self).__init__(*args, **kwargs)

        if self.company and self.company.use_company_timezone:
            self.initial['timezone'] = self.company.timezone
            timezoneField = Field('timezone', type='hidden')
        else:
            timezoneField = 'timezone'

        self.helper = FormHelper()  # Note: if the default layout would be fine, just pass self into this
        self.helper.form_id = "content"
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column('first_name'),
                Column('middle_name'),
                Column('last_name'),
            ),
            'theme',
            timezoneField,
            'email',
            Div(
                Div(
                    HTML('<button type="submit" class="btn btn-primary col" id="save-btn">' +
                         '<i aria-hidden="true" class="fas fa-check mr-1 mr-sm-2"></i>Save Changes</button>'),
                    css_class="btn-toolbar col-12 col-sm-4 col-lg-3 mb-2 mb-sm-0 row"
                ),
                Div(
                    HTML('<a class="btn btn-outline-danger mr-1 col-12 col-sm" href="/change_password/">' +
                         '<i aria-hidden="true" class="fas fa-key mr-1 mr-sm-2"></i>Change Password</a>'),
                    HTML('<button type="reset" class="btn btn-danger col-12 col-sm" id="undo-btn">' +
                         '<i aria-hidden="true" class="fas fa-undo mr-sm-2"></i>Undo Changes</button>'),
                    css_class="btn-toolbar col-12 col-sm-8 col-lg-6 row"
                ),
                css_class="row justify-content-between p-2 pl-sm-0 pr-sm-3 ml-2 ml-sm-0",
            ),
        )

    class Meta:
        model = CustomUser
        fields = (
            'first_name',
            'middle_name',
            'last_name',
            'email',
            'theme',
            'timezone'
        )


class EmployeeAccountForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super(EmployeeAccountForm, self).__init__(*args, **kwargs)

        if self.company and self.company.use_company_timezone:
            self.initial['timezone'] = self.company.timezone

    class Meta:
        model = CustomUser
        fields = (
            'email',
            'theme',
            'timezone'
        )