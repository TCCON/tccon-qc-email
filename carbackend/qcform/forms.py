from django.forms import Form, ModelForm, DateInput, DateField, modelformset_factory
from django.core.exceptions import ValidationError
from django import forms
from .models import QCReport, ISection, SiteReviewers
from tcconauth import utils

import copy
import re


class DatePickerWidget(DateInput):
    template_name = 'widgets/datepicker.html'


class DatePickerField(DateField):
    def __init__(self, *args, input_formats=('%Y-%m-%d', '%Y/%m/%d'), **kwargs):
        super().__init__(*args, input_formats=input_formats, **kwargs)


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return SiteReviewers.reviewer_name(obj)


class BaseReviewersFormset(forms.BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = SiteReviewers.objects.order_by('site')


class ReviewersForm(forms.ModelForm):
    class Meta:
        model = SiteReviewers
        fields = ['site', 'editor', 'reviewer1', 'reviewer2']
        field_classes = {
            'editor': UserChoiceField,
            'reviewer1': UserChoiceField,
            'reviewer2': UserChoiceField
        }

    def clean(self):
        cleaned_data = super().clean()
        # Because adding an error to a field removes that field from cleaned_data, we need to make
        # a copy to do all of the pairwise checks. Plus this is more readable.
        editor = cleaned_data['editor']
        rev1 = cleaned_data['reviewer1']
        rev2 = cleaned_data['reviewer2']

        if editor and rev1 and rev1 == editor:
            self.add_error('reviewer1', ValidationError('Reviewer 1 cannot be the same as the editor', 'dup_reviewer'))
        if editor and rev2 and rev2 == editor:
            self.add_error('reviewer2', ValidationError('Reviewer 2 cannot be the same as the editor', 'dup_reviewer'))
        if rev1 and rev2 and rev2 == rev1:
            self.add_error('reviewer2', ValidationError('Reviewer 2 cannot be the same as reviewer 1', 'dup_reviewer'))

        return cleaned_data


ReviewersFormset = modelformset_factory(SiteReviewers, extra=1, form=ReviewersForm, can_delete=True,
                                        formset=BaseReviewersFormset)


class QcFilterForm(Form):
    reviewer = forms.CharField(required=False)
    site = forms.ChoiceField(required=False, choices=utils.get_sites_as_choices(label_fmt='name+id', include_blank=True))
    modified_after = DatePickerField(required=False, widget=DatePickerWidget())
    modified_before = DatePickerField(required=False, widget=DatePickerWidget())


class QcReportForm(ModelForm, ISection):
    class Meta:
        model = QCReport
        fields = '__all__'
        widgets = dict()
        field_classes = dict()

        # Don't know if this is kosher, but it seems to work (as in
        # automatically makes all "*whenN{s,e}" or "*whenN" fields 
        # date pickers)
        for field in QCReport._meta.get_fields():
            key = field.name
            if key not in widgets and re.search(r'when[0-9]+[se]?$', key):
                widgets[key] = DatePickerWidget()
                field_classes[key] = DatePickerField

    def clean(self):
        cleaned_data = super().clean()
        # We'll need this later
        my_cleaned_data = copy.copy(cleaned_data)
        if cleaned_data.get('netcdf_files', '').strip() == '':
            self.add_error('netcdf_files', 'Must list at least one netCDF file')

        for mc_fieldname, date_fieldname in QCReport.yes_req_date.items():
            if cleaned_data[mc_fieldname] == 'n':
                # If these fields indicate no issues of note, then no data/date range is required
                continue

            # Otherwise, we need to check if any of the date fields has a value. As long as there is
            # one, we're okay. Note that some fields have paired dates and some just single dates.
            if date_fieldname.endswith(('s', 'e')):
                stem = date_fieldname[:-2]
                start_date_fields = [f'{stem}{i}s' for i in range(10)]
                date_descr = 'date range'
                all_date_fields = []
                for sdf in start_date_fields:
                    edf = sdf[:-1] + 'e'
                    start = cleaned_data.get(sdf, None)
                    end = cleaned_data.get(edf, None)
                    if (start is None) != (end is None):
                        self.add_error(sdf, 'Must provide a start and end date')
                    elif start is not None and end is not None and end < start:
                        self.add_error(sdf, 'Start date must be before end date')
                    all_date_fields.extend([sdf, edf])

            else:
                stem = date_fieldname[:-1]
                all_date_fields = [f'{stem}{i}' for i in range(10)]
                date_descr = 'date'

            # Adding an error to a field removes it from cleaned_data, so we check the copy we made to ensure
            # that we don't accidentally say that we need a date when there is one, but it disappeared from
            # cleaned_data because of another error
            if not any(my_cleaned_data[k] is not None for k in all_date_fields if k in my_cleaned_data):
                mc_label = self[mc_fieldname].label
                self.add_error(date_fieldname, f'If "{mc_label}" is not "No", at least one {date_descr} is required')

        return cleaned_data

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
