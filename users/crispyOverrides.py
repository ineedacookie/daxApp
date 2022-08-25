"""This file is where custom crispy forms classes go"""
from crispy_forms.bootstrap import PrependedAppendedText


class CheckboxPrepend(PrependedAppendedText):
    """A input group with a checkbox to the left.

    WARNING: When last checked the method used in __init__ below wasn't always getting the correct
             value of the checkbox. It is supposed to be what the state of the checkbox is, as according to the
             database.

             Please update warning above if you have done so, along with this list of days & people who have checked
             them. If a solution is found, remove the warning, after verifying it.

             5/20/2020 by Nathan F.
    """

    template = "crispy-overrides/checkbox_prepend.html"  # This html is a modified version of what is being overloaded

    def __init__(self, field, checkbox, form, *args, **kwargs):
        kwargs.pop("prepended_text", None)
        self.checkbox = checkbox

        # TODO: This doesn't (always) get the right value. Find a better solution. (When you do, remove the warning from
        #  this class's docstring that this doesn't work)
        #  - look into form.initial
        status = form[checkbox].value()
        print(f"CheckboxPrepend status for {checkbox} is {status}")

        super().__init__(
            field,
            # As prepended_text is sent as the argument `crispy_prepended_text` but is not asserted as a string,
            # we can use this to send _any_ data to the form. In this case, a dictionary, where "checkbox" is the name
            # of the django field that is the checkbox, and status is a bool indicating if the checkbox is checked or
            # not.
            prepended_text={"checkbox": checkbox, "status": status},
            **kwargs  # Raise all other keyword args, just in case any are needed, such as css_class or appended_text
        )

# class UnsafePrependedAppendedText(PrependedAppendedText):
#    template = "crispy-overrides/checkbox_prepend.html"

# class CheckboxPrependedText(UnsafePrependedAppendedText):
#     def __init__(self, field, checkbox_widget, *args, **kwargs):
#         kwargs.pop("appended_text", None)
#         kwargs.pop("prepended_text", None)
#         print(checkbox_widget)
#         self.checkbox = checkbox_widget
#         super().__init__(field, prepended_text=self.checkbox, **kwargs)
