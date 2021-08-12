import json

from django.conf import settings
from django import forms
from django.forms import ModelForm, Form
from .models import SiteInfoUpdate
from . import utils

from datetime import datetime
import re
_this_year = datetime.today().year


class SiteInfoUpdateForm(ModelForm):
    class Meta:
        model = SiteInfoUpdate
        fields = ['release_lag',
                  'location',
                  'contact',
                  'site_reference',
                  'data_reference']

    @classmethod
    def fixed_fields(cls):
        return tuple(f for f in SiteInfoUpdate.standard_fields() if f not in cls.Meta.fields)

    # def save(self, user, site_info, commit=True):
    #     data = self.cleaned_data
    #     data['user_updated'] = user
    #     for field in self.fixed_fields():
    #         data[field] = site_info[field]
    #     super().save(commit=commit)

    def clean(self):
        cleaned_data = super().clean()
        contact_re = re.compile(r'.+<.+@.+>(\s*;.+<.+@.+>)*\s*$')
        if not contact_re.match(cleaned_data.get('contact', '')):
            self.add_error('contact', 'Must have format "Name <email>" (no quotes) or "Name1 <email1>; Name2 <email2>"')
        if cleaned_data['release_lag'] > utils.get_max_release_lag():
            self.add_error('release_lag', 'Release lag cannot be greater than {} days'.format(settings.MAX_RELEASE_LAG))


def _get_flag_name_choices():
    with open(settings.RELEASE_FLAGS_DEF_FILE) as f:
        definitions = tuple(json.load(f)['definitions'].keys())
    defs_long_form = {
        'ils': 'Problem with ILS',
        'tracking': 'Problem with solar tracker',
        'surface pressure': 'Error in surface pressure',
        'other': 'Other'
    }
    return [(k, defs_long_form[k]) for k in definitions]


def _get_flag_values():
    with open(settings.RELEASE_FLAGS_DEF_FILE) as f:
        return json.load(f)['definitions']


class ReleaseFlagUpdateForm(Form):
    start = forms.DateField(label='Start date', widget=forms.SelectDateWidget(years=tuple(range(2000, _this_year+1))))
    end = forms.DateField(label='End date', widget=forms.SelectDateWidget(years=tuple(range(2000, _this_year+1))))
    name = forms.ChoiceField(label='Flag reason', choices=_get_flag_name_choices)
    comment = forms.CharField(label='Comment', max_length=256)

    def clean(self):
        cleaned_data = super().clean()
        import pdb; pdb.set_trace()
        name = cleaned_data.get('name', None)
        flag_values = _get_flag_values()
        if name not in flag_values:
            # should never be the case, since the name has to be selected from a set of choices
            self.add_error('name', 'Error reason "{}" is not one of the allowed values'.format(name))


