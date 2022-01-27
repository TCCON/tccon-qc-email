from django.forms import ModelForm, DateInput, DateField
from .models import QCReport, ISection

import re


class DatePickerWidget(DateInput):
    template_name = 'widgets/datepicker.html'


class DatePickerField(DateField):
    def __init__(self, *args, input_formats=('%Y-%m-%d', '%Y/%m/%d'), **kwargs):
        super().__init__(*args, input_formats=input_formats, **kwargs)


class QcReportForm(ModelForm, ISection):
    class Meta:
        model = QCReport
        fields = '__all__'
        widgets = dict()
        field_classes = dict()

        # Don't know if this is kosher, but it seems to work (as in
        # automatically makes all "*whenN{s,e}" fields date pickers)
        for field in QCReport._meta.get_fields():
            key = field.name
            if key not in widgets and re.search(r'when[0-9]+[se]$', key):
                widgets[key] = DatePickerWidget()
                field_classes[key] = DatePickerField

    @classmethod
    def _get_question_message(cls, prefix):
        return QCReport._get_question_message(prefix)

    @classmethod
    def _get_question_title(cls, prefix):
        return QCReport._get_question_title(prefix)

    def _iter_fields_with_prefixes(self, *prefixes):
        for key in self.fields.keys():
            for prefix in prefixes:
                if key.startswith(prefix):
                    # Calling self[key] returns a BoundField, which is what we need for rendering
                    yield key, self[key]

    def _get_field_by_key(self, key):
        return self[key]
